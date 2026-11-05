<!-- 流程模型列表页（workflow/model/index.vue）
     职责：分页查询/筛选流程模型，提供新增、编辑、设计、发布、复制、停用、删除等入口。
     依赖：Element Plus（表单/表格/分页/弹窗）、@/utils/request 统一请求、v-perm 权限指令。
     被谁使用：工作流管理菜单下的「流程模型」路由页面；「设计」按钮跳转到 workflow/model/design.vue。 -->
<template>
  <!-- 页面根容器：使用全局 app-container 样式提供统一内边距 -->
  <div class="app-container">
    <!-- 页面头部：标题 + 记录数概览 -->
    <div class="page-header">
      <div class="page-title-wrap">
        <h2>流程模型</h2>
        <!-- 副标题：说明模块用途并展示后端返回的总记录数 -->
        <div class="sub">BPMN2.0 流程设计与发布 · 共 {{ total }} 条记录</div>
      </div>
    </div>

    <!-- 查询条件卡片：轻量分隔，不显示阴影 -->
    <el-card shadow="never" class="search-card">
      <!-- @submit.prevent 阻止表单原生的回车提交/页面刷新，回车由各输入框单独处理 -->
      <el-form :model="query" inline @submit.prevent>
        <el-form-item label="模型名称">
          <!-- 名称模糊查询；clearable 一键清空，回车直接触发查询 -->
          <el-input v-model="query.model_name" placeholder="请输入模型名称" clearable style="width: 180px" @keyup.enter="handleQuery" />
        </el-form-item>
        <el-form-item label="流程分类">
          <!-- 分类筛选：选项来自 loadOptions 加载的分类列表 -->
          <el-select v-model="query.category_id" placeholder="请选择" clearable style="width: 180px">
            <el-option v-for="item in categories" :key="item.id" :label="item.name" :value="item.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <!-- 状态筛选，取值与后端定义保持一致：0 草稿 / 1 已发布 / 2 停用 -->
          <el-select v-model="query.status" placeholder="请选择" clearable style="width: 150px">
            <!-- 草稿：尚未发布，不能发起实例 -->
            <el-option label="草稿" :value="0" />
            <!-- 已发布：可被发起 -->
            <el-option label="已发布" :value="1" />
            <!-- 停用：不再允许新发起 -->
            <el-option label="停用" :value="2" />
          </el-select>
        </el-form-item>
        <el-form-item class="search-actions">
          <el-button type="primary" :icon="Search" @click="handleQuery">查询</el-button>
          <el-button :icon="Refresh" @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 数据表格卡片 -->
    <el-card shadow="never" class="table-card">
      <!-- 卡片头部：新增/批量删除等表格级操作 -->
      <template #header>
        <div class="card-header">
          <div class="card-actions">
            <!-- 新增模型：v-perm 控制创建权限，点击打开新增弹窗 -->
            <el-button v-perm="'wf:model:create'" type="primary" :icon="Plus" @click="openCreate">新增模型</el-button>
            <!-- 批量删除：未勾选任何行时禁用，避免无效确认弹窗 -->
            <el-button v-perm="'wf:model:delete'" type="danger" plain :icon="Delete" :disabled="!selectedIds.length" @click="handleBatchDelete">批量删除</el-button>
          </div>
        </div>
      </template>
      <!-- 表格：loading 覆盖加载态；stripe 斑马纹；勾选变化同步 selectedIds -->
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据" @selection-change="onSelectionChange">
        <!-- 序号列：由表格自动生成行号，仅用于阅读定位 -->
        <el-table-column type="index" label="序号" width="70" align="center" />
        <!-- 多选列：驱动批量删除 -->
        <el-table-column type="selection" width="50" align="center" />
        <!-- 模型名称：超长省略并以 tooltip 展示全文 -->
        <el-table-column label="模型名称" prop="model_name" min-width="150" show-overflow-tooltip />
        <!-- 模型 Key：流程唯一标识，发起接口以此定位流程定义 -->
        <el-table-column label="模型Key" prop="model_key" min-width="130" show-overflow-tooltip />
        <!-- 分类名称：由后端联表返回 -->
        <el-table-column label="分类" prop="category_name" width="120" align="center" />
        <!-- 绑定表单名称：流程发起时渲染该表单 -->
        <el-table-column label="绑定表单" prop="form_name" min-width="130" show-overflow-tooltip />
        <el-table-column label="版本" width="80" align="center">
          <!-- 版本号前缀 v，便于与后端 version 字段区分 -->
          <template #default="scope">v{{ scope.row.version }}</template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center">
          <template #default="scope">
            <!-- 状态标签：颜色由 statusType 映射，文案由后端 status_name 返回 -->
            <el-tag :type="statusType(scope.row.status)">{{ scope.row.status_name }}</el-tag>
          </template>
        </el-table-column>
        <!-- 实例数：该流程已发起的实例总数，删除/停用前的重要参考 -->
        <el-table-column label="实例数" prop="instance_count" width="85" align="center" />
        <!-- 更新时间：由后端格式化的时间字符串 -->
        <el-table-column label="更新时间" prop="update_time" width="170" />
        <!-- 操作列固定右侧，横向滚动时始终可见 -->
        <el-table-column label="操作" width="290" align="center" fixed="right">
          <template #default="scope">
            <!-- 设计：进入 bpmn 流程设计器页面 -->
            <el-button v-perm="'wf:model:list'" link type="primary" :icon="Share" @click="openDesign(scope.row)">设计</el-button>
            <!-- 发布：版本号递增并使流程可发起 -->
            <el-button v-perm="'wf:model:publish'" link type="success" :icon="Promotion" @click="publish(scope.row)">发布</el-button>
            <!-- 编辑：修改名称、分类、绑定表单等元信息 -->
            <el-button v-perm="'wf:model:update'" link type="primary" :icon="Edit" @click="openEdit(scope.row)">编辑</el-button>
            <!-- 更多操作下拉：command 会携带动作名与当前行数据 -->
            <el-dropdown trigger="click" @command="cmd => handleCommand(cmd, scope.row)">
              <el-button link type="primary" style="margin-left: 8px">更多<el-icon class="el-icon--right"><ArrowDown /></el-icon></el-button>
              <!-- 下拉菜单：复制/停用/删除 -->
              <template #dropdown>
                <el-dropdown-menu>
                  <!-- 复制模型：生成一份副本，便于在已有流程上改造 -->
                  <el-dropdown-item command="copy">复制模型</el-dropdown-item>
                  <!-- 停用：仅已发布（status=1）状态可用，避免对草稿/停用重复操作 -->
                  <el-dropdown-item command="disable" :disabled="scope.row.status !== 1">停用</el-dropdown-item>
                  <!-- 删除：divided 与上方操作加分隔线，降低误点风险 -->
                  <el-dropdown-item command="delete" divided>删除</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
        </el-table-column>
      </el-table>
      <!-- 分页：页码/每页条数使用 v-model 双向绑定到 query，变更后重新拉取列表 -->
      <div class="pagination-wrap">
        <el-pagination background layout="total, sizes, prev, pager, next, jumper"
          :total="total" v-model:current-page="query.page" v-model:page-size="query.page_size"
          :page-sizes="[10, 20, 50, 100]" @change="getList" />
      </div>
    </el-card>

    <!-- 新增/编辑弹窗：标题随 form.id 切换；destroy-on-close 关闭后销毁表单，避免校验残留 -->
    <el-dialog :title="form.id ? '编辑流程模型' : '新增流程模型'" v-model="dialogVisible" width="560px" :close-on-click-modal="false" destroy-on-close>
      <!-- 表单校验：rules 只约束名称与 Key 必填 -->
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="模型名称" prop="model_name">
          <!-- 展示用名称，发起时也用于列表识别 -->
          <el-input v-model="form.model_name" placeholder="如：请假流程" />
        </el-form-item>
        <el-form-item label="模型Key" prop="model_key">
          <!-- 唯一标识：编辑时禁用，因为已发起实例依赖该 Key，改动会破坏关联 -->
          <el-input v-model="form.model_key" placeholder="唯一标识，如 leave" :disabled="!!form.id" />
        </el-form-item>
        <el-form-item label="流程分类" prop="category_id">
          <!-- 分类归属，供列表筛选与发起页分组展示 -->
          <el-select v-model="form.category_id" placeholder="请选择分类" clearable style="width: 100%">
            <el-option v-for="item in categories" :key="item.id" :label="item.name" :value="item.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="绑定表单" prop="form_id">
          <!-- 绑定业务表单：流程发起时按此表单渲染填写页 -->
          <el-select v-model="form.form_id" placeholder="请选择表单" clearable style="width: 100%">
            <el-option v-for="item in forms" :key="item.id" :label="item.form_name" :value="item.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注" prop="remark">
          <!-- 备注：仅作说明，不影响流程执行 -->
          <el-input v-model="form.remark" type="textarea" :rows="3" placeholder="请输入备注" />
        </el-form-item>
      </el-form>
      <!-- 弹窗底部：取消关闭、确定提交（saving 防重复提交） -->
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitForm">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
// Vue 组合式 API：ref 基本状态、reactive 查询/表单对象、onMounted 首次加载数据
import { ref, reactive, onMounted } from 'vue'
// 路由器：跳转到流程设计器页面
import { useRouter } from 'vue-router'
// Element Plus：操作成功提示与危险操作二次确认
import { ElMessage, ElMessageBox } from 'element-plus'
// 按钮与列操作图标
import { Search, Refresh, Plus, Delete, Edit, Share, Promotion, ArrowDown } from '@element-plus/icons-vue'
// 统一请求实例：自动携带 token、统一错误提示
import request from '@/utils/request'

// 路由器实例，openDesign 使用
const router = useRouter()
// 列表加载状态：驱动表格 loading 遮罩
const loading = ref(false)
// 弹窗提交状态：驱动确定按钮 loading，防止重复提交
const saving = ref(false)
// 当前页表格数据
const rows = ref([])
// 记录总数：分页组件据此计算页数
const total = ref(0)
// 已勾选行的 id 集合：驱动批量删除按钮可用状态
const selectedIds = ref([])
// 新增/编辑弹窗可见性
const dialogVisible = ref(false)
// 表单实例引用：submitForm 中调用 validate 做校验
const formRef = ref()
// 分类下拉候选（loadOptions 加载）
const categories = ref([])
// 表单下拉候选（loadOptions 加载）
const forms = ref([])
// 查询条件：分页参数与筛选条件一起提交给后端；状态空串表示不过滤
const query = reactive({ page: 1, page_size: 10, model_name: '', category_id: '', status: '' })
// 新增/编辑表单数据；id=0 表示新增
const form = reactive({ id: 0, model_name: '', model_key: '', category_id: '', form_id: '', remark: '' })
// 表单校验规则：名称与 Key 必填
const rules = {
  model_name: [{ required: true, message: '请输入模型名称', trigger: 'blur' }],
  model_key: [{ required: true, message: '请输入模型Key', trigger: 'blur' }]
}

// 状态码 → el-tag 类型映射：草稿灰、已发布绿、停用红；未知状态回退为 info
function statusType(status) {
  return { 0: 'info', 1: 'success', 2: 'danger' }[status] || 'info'
}
// 拉取模型列表：query 作为查询参数（含分页），成功后回填 rows/total
async function getList() {
  // 进入加载态
  loading.value = true
  try {
    const res = await request.get('/wf/model/list', { params: query })
    rows.value = res.data.list
    total.value = res.data.total
  } finally {
    // 无论成功失败都关闭 loading，避免表格一直转圈
    loading.value = false
  }
}
// 加载分类与表单下拉：两个接口并行，减少等待；page_size 取大值以拿到全部候选
async function loadOptions() {
  const [cateRes, formRes] = await Promise.all([
    // 流程分类列表（仅取第一页大页容量，用于下拉）
    request.get('/wf/category/list', { params: { page: 1, page_size: 1000 } }),
    // 可用表单列表（供模型绑定）
    request.get('/wf/form/list', { params: { page: 1, page_size: 1000 } })
  ])
  // 用 || [] 兜底，避免后端返回空时下拉报错
  categories.value = cateRes.data.list || []
  forms.value = formRes.data.list || []
}
// 查询：重置到第一页再请求，保证筛选结果从首页开始展示
function handleQuery() {
  query.page = 1
  getList()
}
// 重置查询条件：保留 page_size，只清空筛选并回到第一页
function resetQuery() {
  Object.assign(query, { page: 1, model_name: '', category_id: '', status: '' })
  getList()
}
// 表格勾选变化：只保存 id，批量删除接口按 id 删除
function onSelectionChange(rowsSelected) {
  selectedIds.value = rowsSelected.map(row => row.id)
}
// 打开新增弹窗：重置表单为初始值，避免残留上次编辑内容
function openCreate() {
  Object.assign(form, { id: 0, model_name: '', model_key: '', category_id: '', form_id: '', remark: '' })
  dialogVisible.value = true
}
// 打开编辑弹窗：把行数据回填到表单（空值用空串兜底，避免 Select 显示异常）
function openEdit(row) {
  Object.assign(form, {
    id: row.id, model_name: row.model_name, model_key: row.model_key,
    category_id: row.category_id || '', form_id: row.form_id || '', remark: row.remark || ''
  })
  dialogVisible.value = true
}
// 提交表单：校验通过后按 id 判断新增/编辑，成功后关闭弹窗并刷新列表
async function submitForm() {
  // validate 失败会 reject，直接中断提交
  await formRef.value.validate()
  saving.value = true
  try {
    if (form.id) {
      // 编辑：模型 Key 在编辑态被禁用，这里提交的 key 不会变化
      await request.put(`/wf/model/update/${form.id}`, form)
      ElMessage.success('修改成功')
    } else {
      // 新增：后端创建草稿模型，随后可进入设计器绘制流程图
      await request.post('/wf/model/create', form)
      ElMessage.success('新增成功，请进入设计器绘制流程图')
    }
    dialogVisible.value = false
    // 刷新列表以展示最新数据
    getList()
  } finally {
    // 提交结束恢复按钮状态
    saving.value = false
  }
}
// 进入设计器：路由参数 id 用于加载该模型的 BPMN XML 与节点配置
function openDesign(row) {
  router.push(`/workflow/design/${row.id}`)
}
// 发布：二次确认后调用发布接口，返回新版本号并提示
async function publish(row) {
  // 用户取消会 reject，从而中断后续发布请求
  await ElMessageBox.confirm(`确认发布「${row.model_name}」吗？发布后版本号将递增。`, '发布确认', { type: 'warning' })
  const res = await request.post(`/wf/model/publish/${row.id}`)
  ElMessage.success(`发布成功，当前版本 v${res.data.version}`)
  getList()
}
// 行内“更多”下拉动作分发：复制/停用/删除
async function handleCommand(command, row) {
  if (command === 'copy') {
    // 复制：后端生成副本（含流程图与配置），成功后刷新列表
    await request.post(`/wf/model/copy/${row.id}`)
    ElMessage.success('复制成功')
    getList()
  } else if (command === 'disable') {
    // 停用：确认后执行，停用后发起页不再可选该流程
    await ElMessageBox.confirm('停用后新发起将不可选择该流程，确认停用吗？', '提示', { type: 'warning' })
    await request.post(`/wf/model/disable/${row.id}`)
    ElMessage.success('已停用')
    getList()
  } else if (command === 'delete') {
    // 删除：复用单行删除逻辑
    await handleDelete(row)
  }
}
// 删除单个模型：确认后按 ids 数组删除并刷新
async function handleDelete(row) {
  await ElMessageBox.confirm(`确认删除模型「${row.model_name}」吗？`, '提示', { type: 'warning' })
  await request.delete('/wf/model/delete', { data: { ids: [row.id] } })
  ElMessage.success('删除成功')
  getList()
}
// 批量删除：删除当前勾选的所有模型
async function handleBatchDelete() {
  await ElMessageBox.confirm(`确认删除选中的 ${selectedIds.value.length} 个模型吗？`, '提示', { type: 'warning' })
  await request.delete('/wf/model/delete', { data: { ids: selectedIds.value } })
  ElMessage.success('删除成功')
  getList()
}

// 页面挂载：先加载下拉候选，再拉取首屏列表
onMounted(async () => {
  await loadOptions()
  getList()
})
</script>
