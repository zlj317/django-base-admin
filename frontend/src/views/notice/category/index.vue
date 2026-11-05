<template>
  <!-- 文件说明：通知公告模块「公告分类」维护页，管理公告的分类名称/编码/排序/启停状态。
       依赖：@/utils/request 统一请求；v-perm 权限指令（notice:create/update/delete）；后端接口 /notice/category/*。
       被使用：由公告相关菜单路由加载；「公告管理」页通过 /notice/category/list 取分类下拉数据。 -->
  <div class="app-container">
    <!-- 页面头部：标题与记录总数 -->
    <div class="page-header">
      <!-- 标题区：主标题 + 当前查询条件下的总条数 -->
      <div class="page-title-wrap">
        <h2>公告分类</h2>
        <!-- total 来自列表接口，随查询/删除刷新 -->
        <div class="sub">分类维护 · 共 {{ total }} 条</div>
      </div>
    </div>
    <!-- 查询区：shadow="never" 保持一致的无阴影卡片风格 -->
    <el-card shadow="never" class="search-card">
      <!-- inline 行内布局；@submit.prevent 阻止原生提交导致页面刷新 -->
      <el-form :model="query" inline @submit.prevent>
        <!-- 分类名称：模糊查询，回车触发搜索 -->
        <el-form-item label="分类名称">
          <el-input v-model="query.category_name" placeholder="请输入分类名称" clearable style="width: 170px" @keyup.enter="handleSearch" />
        </el-form-item>
        <!-- 状态筛选：1=启用（公告可选用该分类），0=停用（不再对外展示分类） -->
        <el-form-item label="状态">
          <el-select v-model="query.status" placeholder="全部" clearable style="width: 110px">
            <el-option label="启用" :value="1" />
            <el-option label="停用" :value="0" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <!-- 查询：重置到第一页后请求，避免页码越界 -->
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <!-- 重置：恢复默认筛选条件并重新查询 -->
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 表格区：公告分类列表 + 分页 -->
    <el-card shadow="never" class="table-card">
      <!-- 卡片头部插槽：工具栏按钮 -->
      <template #header>
        <div class="card-header">
          <div class="card-actions">
            <!-- 新增：v-perm 控制按钮显隐，无 notice:create 权限的用户看不到入口 -->
            <el-button v-perm="'notice:create'" type="primary" :icon="Plus" @click="openCreate">新增</el-button>
            <!-- 批量删除：同样受 notice:delete 权限控制，未勾选时禁用 -->
            <el-button v-perm="'notice:delete'" type="danger" plain :icon="Delete" :disabled="!selection.length" @click="handleBatchDelete">批量删除</el-button>
          </div>
        </div>
      </template>
      <!-- v-loading 请求遮罩；stripe 斑马纹；empty-text 空数据提示 -->
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据" @selection-change="onSelectionChange">
        <!-- 自动序号列 -->
        <el-table-column type="index" label="序号" width="70" align="center" />
        <!-- 勾选列：支撑批量删除 -->
        <el-table-column type="selection" width="50" />
        <!-- 分类名称：展示给用户看的中文名 -->
        <el-table-column label="分类名称" prop="category_name" min-width="160" show-overflow-tooltip />
        <!-- 分类编码：程序侧使用的唯一编码，便于对接/统计 -->
        <el-table-column label="分类编码" prop="category_code" min-width="140" show-overflow-tooltip />
        <!-- 排序：数值越小越靠前，控制分类展示顺序 -->
        <el-table-column label="排序" prop="sort" width="90" />
        <!-- 状态开关：直接在行内切换启停；v-model 会先改 row.status，再由 @change 提交给后端 -->
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-switch v-model="row.status" :active-value="1" :inactive-value="0" v-perm="'notice:update'" @change="handleStatusChange(row)" />
          </template>
        </el-table-column>
        <!-- 备注：补充说明，过长时悬浮显示 -->
        <el-table-column label="备注" prop="remark" min-width="180" show-overflow-tooltip />
        <!-- 创建时间只读展示 -->
        <el-table-column label="创建时间" prop="create_time" width="170" />
        <!-- 操作列固定右侧，横向滚动时始终可见 -->
        <el-table-column label="操作" width="180" fixed="right" class-name="op-col">
          <template #default="{ row }">
            <!-- 编辑：需要 notice:update 权限，整行回填表单 -->
            <el-button v-perm="'notice:update'" link type="primary" @click="openEdit(row)">编辑</el-button>
            <!-- 删除：需要 notice:delete 权限，删除前二次确认 -->
            <el-button v-perm="'notice:delete'" link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <!-- 分页：页码/每页条数双向绑定 query，变化后触发 fetchList -->
      <div class="pagination-wrap">
        <el-pagination background layout="total, sizes, prev, pager, next, jumper"
          :total="total" v-model:current-page="query.page" v-model:page-size="query.page_size"
          :page-sizes="[10, 20, 50, 100]" @change="fetchList" />
      </div>
    </el-card>

    <!-- 新增/编辑弹窗：标题动态；禁止点遮罩关闭防误触丢失；destroy-on-close 让表单每次重新创建 -->
    <el-dialog :title="dialogTitle" v-model="dialogVisible" width="560px" :close-on-click-modal="false" destroy-on-close>
      <!-- ref 用于提交校验；rules 控制必填项；label-width=110 保证标签对齐 -->
      <el-form ref="formRef" :model="form" :rules="rules" label-width="110px">
        <!-- 分类名称：必填、最长 64 字符 -->
        <el-form-item label="分类名称" prop="category_name">
          <el-input v-model="form.category_name" placeholder="请输入分类名称" maxlength="64" />
        </el-form-item>
        <!-- 分类编码：必填、最长 32 字符，建议英文/数字便于程序判断 -->
        <el-form-item label="分类编码" prop="category_code">
          <el-input v-model="form.category_code" placeholder="请输入分类编码" maxlength="32" />
        </el-form-item>
        <!-- 排序：0~9999，数值越小越靠前 -->
        <el-form-item label="排序" prop="sort">
          <el-input-number v-model="form.sort" :min="0" :max="9999" />
        </el-form-item>
        <!-- 状态：单选 1=启用 / 0=停用，与列表接口的枚举保持一致 -->
        <el-form-item label="状态" prop="status">
          <el-radio-group v-model="form.status">
            <el-radio :value="1">启用</el-radio>
            <el-radio :value="0">停用</el-radio>
          </el-radio-group>
        </el-form-item>
        <!-- 备注：可选说明 -->
        <el-form-item label="备注" prop="remark">
          <el-input v-model="form.remark" type="textarea" :rows="2" placeholder="请输入备注" />
        </el-form-item>
      </el-form>
      <!-- 底部按钮：取消仅关闭弹窗；确定提交并由 saving 防重复 -->
      <template #footer>
        <el-button @click="dialogVisible=false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitForm">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
// 响应式 API 与挂载钩子
import { ref, reactive, onMounted } from 'vue'
// 统一提示与二次确认框
import { ElMessage, ElMessageBox } from 'element-plus'
// 查询/重置/新增/删除按钮图标（按需引入）
import { Search, Refresh, Plus, Delete } from '@element-plus/icons-vue'
// 统一请求实例：内含鉴权、错误提示与 401 处理
import request from '@/utils/request'

// 列表加载状态，控制表格遮罩
const loading = ref(false)
// 当前页分类数据
const rows = ref([])
// 总记录数，用于分页与顶部统计
const total = ref(0)
// 勾选行，批量删除时取 id
const selection = ref([])
// 提交中状态，防止重复点击确定
const saving = ref(false)
// 弹窗显隐
const dialogVisible = ref(false)
// 弹窗标题，新增/编辑时切换
const dialogTitle = ref('新增')
// 表单实例，提交前调用 validate
const formRef = ref()

// 查询条件初始值；status 为 null 表示不过滤状态，重置时整体还原
const query_orig = { page: 1, page_size: 10, category_name: '', status: null }
// 查询条件响应式副本
const query = reactive({ ...query_orig })

// 表单初始值：新增默认排序 0、状态启用；id 为 null 表示新增
const form_orig = {
  id: null, category_name: '', category_code: '', sort: 0, status: 1, remark: ''
}
// 弹窗表单响应式副本
const form = reactive({ ...form_orig })

// 校验规则：名称与编码必填，blur 触发，避免输入过程中频繁报错
const rules = {
  category_name: [{ required: true, message: '请输入分类名称', trigger: 'blur' }],
  category_code: [{ required: true, message: '请输入分类编码', trigger: 'blur' }]
}

// 按动作名返回对应接口地址：集中维护 base 路径，避免各处硬编码字符串不一致
function apiUrl(action) {
  const base = '/notice/category'
  return {
    list: base + '/list',
    create: base + '/create',
    update: base + '/update',
    delete: base + '/delete'
  }[action]
}

// 查询列表：params 直接传响应式 query（含分页与筛选）
async function fetchList() {
  loading.value = true
  try {
    const res = await request.get(apiUrl('list'), { params: query })
    // 无数据时兜底空数组，表格显示空状态
    rows.value = res.data.list || []
    // 总数兜底 0，避免分页异常
    total.value = res.data.total || 0
  // 成功失败都解除 loading
  } finally { loading.value = false }
}
// 查询：回到第一页再请求
function handleSearch() { query.page = 1; fetchList() }
// 重置：还原全部查询条件（含分页）后再查询
function handleReset() { Object.assign(query, query_orig); handleSearch() }
// 勾选变化：同步选中行
function onSelectionChange(r) { selection.value = r }

// 新增：重置表单并切换标题
function openCreate() { Object.assign(form, form_orig); dialogTitle.value = '新增分类'; dialogVisible.value = true }
// 编辑：先重置默认值再回填整行，防止残留上次数据
function openEdit(row) { Object.assign(form, form_orig, row); dialogTitle.value = '编辑分类'; dialogVisible.value = true }

// 提交表单：有 id 走更新，无 id 走新增；成功后关闭弹窗并刷新
async function submitForm() {
  await formRef.value.validate()
  saving.value = true
  try {
    if (form.id) {
      // 剔除 id 后用路径参数传递，避免请求体与路径重复
      const { id, ...data } = form
      await request.put(`${apiUrl('update')}/${id}`, data); ElMessage.success('更新成功')
    } else {
      // 新增：整份表单提交
      await request.post(apiUrl('create'), form); ElMessage.success('新增成功')
    }
    // 成功后关闭弹窗并刷新列表
    dialogVisible.value = false; fetchList()
  // 失败时只释放按钮
  } finally { saving.value = false }
}

// 行内状态切换：开关已先改 row.status，这里把新状态提交到专用状态接口
// 注意：若接口失败，开关会保持已切换的视觉状态（无回滚），见问题清单
async function handleStatusChange(row) {
  await request.put(`/notice/category/status/${row.id}`, { status: row.status })
  // 按新状态给出对应提示，让用户确认操作已生效
  ElMessage.success(row.status === 1 ? '已启用' : '已停用')
}

// 单条删除：二次确认后按 ids 数组提交
async function handleDelete(row) {
  await ElMessageBox.confirm('确定删除该分类？', '提示', { type: 'warning' })
  await request.delete(apiUrl('delete'), { data: { ids: [row.id] } })
  ElMessage.success('删除成功'); fetchList()
}

// 批量删除：勾选行 id 一次性提交
async function handleBatchDelete() {
  await ElMessageBox.confirm(`确定删除选中的 ${selection.value.length} 条分类？`, '提示', { type: 'warning' })
  await request.delete(apiUrl('delete'), { data: { ids: selection.value.map(r => r.id) } })
  ElMessage.success('批量删除成功'); fetchList()
}

// 挂载后加载首屏数据
onMounted(fetchList)
</script>
