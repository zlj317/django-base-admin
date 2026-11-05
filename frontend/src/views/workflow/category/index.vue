<!--
  文件级说明：流程分类管理页（workflow/category/index.vue）
  职责：维护流程分类数据（列表查询、新增、编辑、删除、批量删除），为流程模型提供归类维度。
  依赖：@/utils/request 统一 HTTP 封装；Element Plus 表单/表格/弹窗组件；v-perm 权限指令。
  使用方：由工作流管理菜单下的「流程分类」路由加载，属于后台管理页面。
-->
<template>
  <!-- 页面根容器：套用全局布局的内边距与背景，保持与其它后台页面一致 -->
  <div class="app-container">
    <!-- 页头：标题 + 记录总数，便于管理员了解当前分类规模 -->
    <div class="page-header">
      <div class="page-title-wrap">
        <h2>流程分类</h2>
        <!-- total 为后端返回的总条数，随查询实时刷新，因此用插值展示 -->
        <div class="sub">流程归类管理 · 共 {{ total }} 条记录</div>
      </div>
    </div>

    <!-- 搜索区：以无阴影卡片承载筛选表单，弱化视觉层级，突出下方表格 -->
    <el-card shadow="never" class="search-card">
      <!-- 内联表单：@submit.prevent 阻止浏览器默认提交，避免回车刷新页面 -->
      <el-form :model="query" inline @submit.prevent>
        <!-- 分类名称筛选：v-model 直接写入查询对象，回车即触发查询提升录入效率 -->
        <el-form-item label="分类名称">
          <!-- clearable 允许一键清空；@keyup.enter 让键盘用户无需点击按钮即可搜索 -->
          <el-input v-model="query.name" placeholder="请输入分类名称" clearable style="width: 180px" @keyup.enter="handleQuery" />
        </el-form-item>
        <!-- 状态筛选：值为数字，与后端存储的 1/0 约定保持一致 -->
        <el-form-item label="状态">
          <el-select v-model="query.status" placeholder="请选择" clearable style="width: 160px">
            <!-- 启用对应 1，停用对应 0 -->
            <el-option label="启用" :value="1" />
            <el-option label="停用" :value="0" />
          </el-select>
        </el-form-item>
        <el-form-item class="search-actions">
          <!-- 查询：保留当前条件并从第一页重新请求 -->
          <el-button type="primary" :icon="Search" @click="handleQuery">查询</el-button>
          <!-- 重置：清空条件后重新查询，避免手写清空逻辑 -->
          <el-button :icon="Refresh" @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 列表区卡片：头部放操作按钮，主体放表格与分页 -->
    <el-card shadow="never" class="table-card">
      <!-- 卡片头部插槽：承载新增/批量删除等全局操作 -->
      <template #header>
        <div class="card-header">
          <div class="card-actions">
            <!-- 新增：v-perm 控制创建权限，无权限用户按钮不渲染 -->
            <el-button v-perm="'wf:category:create'" type="primary" :icon="Plus" @click="openCreate">新增</el-button>
            <!-- 批量删除：未勾选任何行时 disabled，避免发出空 ids 的无效请求 -->
            <el-button v-perm="'wf:category:delete'" type="danger" plain :icon="Delete" :disabled="!selectedIds.length" @click="handleBatchDelete">批量删除</el-button>
          </div>
        </div>
      </template>
      <!-- 数据表格：v-loading 控制请求态遮罩，stripe 提升行可读性，selection-change 汇总勾选 id -->
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据" @selection-change="onSelectionChange">
        <!-- 序号列：type=index 由表格自动生成，仅用于阅读时定位 -->
        <el-table-column type="index" label="序号" width="70" align="center" />
        <!-- 勾选列：供批量删除使用，宽度收窄以节省横向空间 -->
        <el-table-column type="selection" width="50" align="center" />
        <!-- 分类名称：主标识列，min-width 保证窄屏下仍有可读宽度 -->
        <el-table-column label="分类名称" prop="name" min-width="150" show-overflow-tooltip />
        <!-- 分类编码：程序内引用标识，show-overflow-tooltip 处理长文本 -->
        <el-table-column label="分类编码" prop="code" min-width="140" show-overflow-tooltip />
        <!-- 排序号：决定列表展示顺序，居中窄列 -->
        <el-table-column label="排序号" prop="sort" width="90" align="center" />
        <!-- 状态列：用标签着色区分启用/停用 -->
        <el-table-column label="状态" width="90" align="center">
          <!-- 作用域插槽拿到当前行数据 -->
          <template #default="scope">
            <!-- 该页约定 status=1 为启用（success 绿），其余按停用显示为灰色 -->
            <el-tag :type="scope.row.status === 1 ? 'success' : 'info'">{{ scope.row.status === 1 ? '启用' : '停用' }}</el-tag>
          </template>
        </el-table-column>
        <!-- 备注列：辅助说明，允许换行前省略显示 -->
        <el-table-column label="备注" prop="remark" min-width="180" show-overflow-tooltip />
        <!-- 创建时间：由后端直接返回格式化字符串，无需前端再处理 -->
        <el-table-column label="创建时间" prop="create_time" width="170" />
        <!-- 操作列：fixed=right 保证横向滚动时始终可见 -->
        <el-table-column label="操作" width="150" align="center" fixed="right">
          <!-- 行内操作插槽 -->
          <template #default="scope">
            <!-- 编辑：link 样式保持操作列轻量，权限由 v-perm 过滤 -->
            <el-button v-perm="'wf:category:update'" link type="primary" :icon="Edit" @click="openEdit(scope.row)">编辑</el-button>
            <!-- 删除：单条删除前会二次确认，避免误删 -->
            <el-button v-perm="'wf:category:delete'" link type="danger" :icon="Delete" @click="handleDelete(scope.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <!-- 分页容器：与表格底部对齐 -->
      <div class="pagination-wrap">
        <!-- 分页组件：页码与每页条数双向绑定到 query，change 时重新请求 -->
        <el-pagination background layout="total, sizes, prev, pager, next, jumper"
          :total="total" v-model:current-page="query.page" v-model:page-size="query.page_size"
          :page-sizes="[10, 20, 50, 100]" @change="getList" />
      </div>
    </el-card>

    <!-- 新增/编辑弹窗：标题随 form.id 切换；禁用点遮罩关闭，防止表单数据丢失 -->
    <el-dialog :title="form.id ? '编辑流程分类' : '新增流程分类'" v-model="dialogVisible" width="520px" :close-on-click-modal="false" destroy-on-close>
      <!-- 表单：绑定 form 与校验规则，label-width 统一标签宽度 -->
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <!-- 分类名称：必填，用于后台识别分类 -->
        <el-form-item label="分类名称" prop="name">
          <el-input v-model="form.name" placeholder="如：OA审批、财务审批" />
        </el-form-item>
        <!-- 分类编码：必填且编辑时禁用，因为编码会被流程配置引用，修改会破坏历史数据关联 -->
        <el-form-item label="分类编码" prop="code">
          <el-input v-model="form.code" placeholder="唯一编码，如 oa、finance" :disabled="!!form.id" />
        </el-form-item>
        <!-- 排序号：限制不小于 0，值越大越靠后 -->
        <el-form-item label="排序号" prop="sort">
          <el-input-number v-model="form.sort" :min="0" style="width: 100%" />
        </el-form-item>
        <!-- 状态：单选 1 启用 / 0 停用，与列表展示逻辑保持一致 -->
        <el-form-item label="状态" prop="status">
          <el-radio-group v-model="form.status">
            <el-radio :label="1">启用</el-radio>
            <el-radio :label="0">停用</el-radio>
          </el-radio-group>
        </el-form-item>
        <!-- 备注：选填多行文本，便于说明分类用途 -->
        <el-form-item label="备注" prop="remark">
          <el-input v-model="form.remark" type="textarea" :rows="3" placeholder="请输入备注" />
        </el-form-item>
      </el-form>
      <!-- 底部按钮插槽：取消直接关闭，确定走 submitForm 并展示保存 loading -->
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitForm">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
// 组合式 API 基础能力：ref 定义响应式标量/数组，reactive 定义查询与表单对象，onMounted 在挂载后首次拉取列表
import { ref, reactive, onMounted } from 'vue'
// ElMessage 轻提示用于操作结果反馈；ElMessageBox 用于删除前的确认对话框
import { ElMessage, ElMessageBox } from 'element-plus'
// 表格/按钮使用到的图标组件，供 template 中的 :icon 绑定
import { Search, Refresh, Plus, Delete, Edit } from '@element-plus/icons-vue'
// 统一请求实例：自动携带 token 并集中处理后端 { code, msg, data } 响应结构
import request from '@/utils/request'

// 列表加载中标记，驱动表格的 v-loading 遮罩
const loading = ref(false)
// 表单提交中标记，驱动弹窗确定按钮 loading，防止重复提交
const saving = ref(false)
// 当前页列表数据，来自后端 list 字段
const rows = ref([])
// 记录总数，用于分页组件与页头统计文案
const total = ref(0)
// 表格勾选行的 id 集合，供批量删除使用
const selectedIds = ref([])
// 新增/编辑弹窗显隐控制
const dialogVisible = ref(false)
// 表单组件实例引用，提交前调用 validate() 做整体校验
const formRef = ref()
// 查询条件：page/page_size 由分页组件双向绑定；name/status 为空串表示未筛选
const query = reactive({ page: 1, page_size: 10, name: '', status: '' })
// 表单数据：id=0 表示新增（后端据此走 create），status 默认 1（启用）
const form = reactive({ id: 0, name: '', code: '', sort: 0, status: 1, remark: '' })
// 表单校验规则：名称与编码必填，失焦时校验
const rules = {
  // 分类名称必填
  name: [{ required: true, message: '请输入分类名称', trigger: 'blur' }],
  // 分类编码必填
  code: [{ required: true, message: '请输入分类编码', trigger: 'blur' }]
}

// 拉取分类列表：把 query（含分页与筛选）作为 params 传给后端
async function getList() {
  // 请求开始先置 loading，避免用户看到旧数据误以为已刷新
  loading.value = true
  try {
    // GET /api/wf/category/list，后端返回 { list, total }
    const res = await request.get('/wf/category/list', { params: query })
    // 覆盖当前页数据
    rows.value = res.data.list
    // 同步总条数，供分页与页头展示
    total.value = res.data.total
  } finally {
    // 无论成功或失败都关闭 loading，避免失败后遮罩一直存在
    loading.value = false
  }
}
// 点击查询（或回车）：回到第一页再请求，避免停留在超出范围的页码
function handleQuery() {
  query.page = 1
  getList()
}
// 重置查询：清空筛选条件并回到第一页，保留 page_size
function resetQuery() {
  Object.assign(query, { page: 1, name: '', status: '' })
  getList()
}
// 表格勾选变化：只记录 id，删除接口需要的是 id 数组
function onSelectionChange(rowsSelected) {
  selectedIds.value = rowsSelected.map(row => row.id)
}
// 打开新增弹窗：把表单重置为初始值（id=0 标识新增）
function openCreate() {
  Object.assign(form, { id: 0, name: '', code: '', sort: 0, status: 1, remark: '' })
  dialogVisible.value = true
}
// 打开编辑弹窗：用当前行数据回填；remark 为空时补 '' 避免 null 渲染异常
function openEdit(row) {
  Object.assign(form, { id: row.id, name: row.name, code: row.code, sort: row.sort, status: row.status, remark: row.remark || '' })
  dialogVisible.value = true
}
// 提交表单：先整体校验，再按 id 判断新增或更新
async function submitForm() {
  // 校验不通过会抛出 Promise reject，后续逻辑不会执行（Element Plus 会在表单项上标红）
  await formRef.value.validate()
  saving.value = true
  try {
    if (form.id) {
      // 编辑：PUT /wf/category/update/{id}，请求体为整个 form
      await request.put(`/wf/category/update/${form.id}`, form)
      ElMessage.success('修改成功')
    } else {
      // 新增：POST /wf/category/create
      await request.post('/wf/category/create', form)
      ElMessage.success('新增成功')
    }
    // 成功后关闭弹窗并刷新列表，保证展示最新数据
    dialogVisible.value = false
    getList()
  } finally {
    // 提交结束释放 loading，失败时按钮可再次点击
    saving.value = false
  }
}
// 删除单条：先确认，再以 DELETE 请求体传递 ids 数组
async function handleDelete(row) {
  // 用户取消会 reject，函数在此中断，不会发出删除请求
  await ElMessageBox.confirm(`确认删除分类「${row.name}」吗？`, '提示', { type: 'warning' })
  // 删除接口统一接收 { ids: [...] }，单条删除也包成数组，复用批量删除接口
  await request.delete('/wf/category/delete', { data: { ids: [row.id] } })
  ElMessage.success('删除成功')
  getList()
}
// 批量删除：把当前勾选的 id 集合整体传给后端
async function handleBatchDelete() {
  await ElMessageBox.confirm(`确认删除选中的 ${selectedIds.value.length} 条分类吗？`, '提示', { type: 'warning' })
  await request.delete('/wf/category/delete', { data: { ids: selectedIds.value } })
  ElMessage.success('删除成功')
  getList()
}

// 组件挂载完成后立即加载首屏数据（此时表格与分页已渲染）
onMounted(getList)
</script>
