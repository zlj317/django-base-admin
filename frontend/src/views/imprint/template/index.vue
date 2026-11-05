<template>
  <!-- 文件说明：水印(imprint)模块「导入模板」维护页，维护 Excel/CSV 导入模板的 key、目标表、文件类型与启停状态。
       依赖：@/utils/request 统一请求；后端接口 /imprint/template/*。
       被使用：由水印相关菜单路由加载；下载/导入业务按 template_key 取模板配置，字段结构在「模板字段」页维护。 -->
  <div class="app-container">
    <!-- 页面头部：标题与记录总数 -->
    <div class="page-header">
      <!-- 标题区：主标题 + 当前查询条件下的总条数 -->
      <div class="page-title-wrap">
        <h2>导入模板管理</h2>
        <!-- total 来自列表接口，便于快速了解模板数量 -->
        <div class="sub">导入模板管理 · 共 {{ total }} 条</div>
      </div>
    </div>

    <!-- 查询区：shadow="never" 与全站列表页保持统一的无阴影风格 -->
    <el-card shadow="never" class="search-card">
      <!-- inline 行内布局；@submit.prevent 阻止回车触发的原生提交 -->
      <el-form :model="query" inline @submit.prevent>
        <!-- 模板名称：模糊搜索，回车即查 -->
        <el-form-item label="模板名称">
          <el-input v-model="query.template_name" placeholder="请输入模板名称" clearable style="width: 170px" @keyup.enter="handleSearch" />
        </el-form-item>
        <!-- 模板Key：唯一标识，便于精确查找 -->
        <el-form-item label="模板Key">
          <el-input v-model="query.template_key" placeholder="请输入模板Key" clearable style="width: 170px" @keyup.enter="handleSearch" />
        </el-form-item>
        <!-- 状态筛选：1=启用可下载/导入，0=停用不可用；clearable 清空后查全部 -->
        <el-form-item label="状态">
          <el-select v-model="query.status" placeholder="全部" clearable style="width: 110px">
            <el-option label="启用" :value="1" />
            <el-option label="停用" :value="0" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <!-- 查询：重置到第一页后按当前条件请求 -->
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <!-- 重置：恢复默认条件后重新查询 -->
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 表格区：导入模板列表与分页 -->
    <el-card shadow="never" class="table-card">
      <!-- 卡片头部插槽：工具栏按钮 -->
      <template #header>
        <div class="card-header">
          <div class="card-actions">
            <!-- 新增：重置表单后打开弹窗 -->
            <el-button type="primary" :icon="Plus" @click="openCreate">新增</el-button>
            <!-- 批量删除：未勾选时禁用，避免空 ids 请求 -->
            <el-button type="danger" plain :icon="Delete" :disabled="!selection.length" @click="handleBatchDelete">批量删除</el-button>
          </div>
        </div>
      </template>
      <!-- v-loading 请求遮罩；stripe 斑马纹；empty-text 空数据文案 -->
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据" @selection-change="onSelectionChange">
        <!-- 自动序号，仅作阅读辅助 -->
        <el-table-column type="index" label="序号" width="70" align="center" />
        <!-- 勾选列：支撑批量删除 -->
        <el-table-column type="selection" width="50" />
        <!-- 模板名称：用户可读标题 -->
        <el-table-column label="模板名称" prop="template_name" min-width="180" show-overflow-tooltip />
        <!-- 模板Key：业务引用模板的唯一标识 -->
        <el-table-column label="模板Key" prop="template_key" min-width="140" show-overflow-tooltip />
        <!-- 目标表：导入数据最终写入的数据库表名 -->
        <el-table-column label="目标表" prop="table_name" min-width="140" show-overflow-tooltip />
        <!-- 文件类型：xlsx 用默认标签、csv 用绿色标签便于区分，其他值原样兜底显示 -->
        <el-table-column label="文件类型" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.file_type==='xlsx'" size="small">XLSX</el-tag>
            <el-tag v-else-if="row.file_type==='csv'" size="small" type="success">CSV</el-tag>
            <el-tag v-else size="small">{{ row.file_type }}</el-tag>
          </template>
        </el-table-column>
        <!-- 状态：1=启用（可下载/导入，绿色）；0=停用（灰色，不对外提供） -->
        <el-table-column label="状态" width="80" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.status===1" size="small" type="success">启用</el-tag>
            <el-tag v-else size="small" type="info">停用</el-tag>
          </template>
        </el-table-column>
        <!-- 备注：内部说明，过长时悬浮显示 -->
        <el-table-column label="备注" prop="remark" min-width="150" show-overflow-tooltip />
        <!-- 创建时间只展示，不参与编辑 -->
        <el-table-column label="创建时间" prop="create_time" width="170" />
        <!-- 操作列固定右侧，保证横向滚动时可见 -->
        <el-table-column label="操作" width="180" fixed="right" class-name="op-col">
          <template #default="{ row }">
            <!-- 编辑：整行回填表单 -->
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <!-- 删除：单条删除并二次确认 -->
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <!-- 分页：当前页与每页条数都通过 v-model 双向绑定到 query，@change 触发重新查询 -->
      <div class="pagination-wrap">
        <el-pagination background layout="total, sizes, prev, pager, next, jumper"
          :total="total" v-model:current-page="query.page" v-model:page-size="query.page_size"
          :page-sizes="[10, 20, 50, 100]" @change="fetchList" />
      </div>
    </el-card>

    <!-- 新增/编辑弹窗：标题动态切换；禁止点遮罩关闭避免填写丢失；destroy-on-close 保证每次打开表单全新 -->
    <el-dialog :title="dialogTitle" v-model="dialogVisible" width="640px" :close-on-click-modal="false" destroy-on-close>
      <!-- 表单绑定 model/rules，ref 用于提交前校验 -->
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-row :gutter="12">
          <el-col :span="12">
            <!-- 模板名称：必填的展示标题 -->
            <el-form-item label="模板名称" prop="template_name">
              <el-input v-model="form.template_name" placeholder="请输入模板名称" maxlength="100" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <!-- 模板Key：唯一标识，编辑时禁用，避免业务侧按 key 引用失效 -->
            <el-form-item label="模板Key" prop="template_key">
              <el-input v-model="form.template_key" placeholder="唯一标识" maxlength="64" :disabled="!!form.id" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <!-- 目标表：导入落库的物理表名，如 sys_user -->
            <el-form-item label="目标表" prop="table_name">
              <el-input v-model="form.table_name" placeholder="如 sys_user" maxlength="100" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <!-- 文件类型：决定模板下载/导入解析用 xlsx 还是 csv -->
            <el-form-item label="文件类型" prop="file_type">
              <el-select v-model="form.file_type" style="width:100%">
                <el-option label="XLSX" value="xlsx" />
                <el-option label="CSV" value="csv" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <!-- 状态：启用后模板才会出现在下载/导入入口 -->
            <el-form-item label="状态" prop="status">
              <el-switch v-model="form.status" :active-value="1" :inactive-value="0" active-text="启用" inactive-text="停用" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <!-- 备注：可选说明文字 -->
            <el-form-item label="备注" prop="remark">
              <el-input v-model="form.remark" type="textarea" :rows="2" placeholder="请输入备注" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <!-- 底部：取消不保存；确定走 submitForm 并显示 loading -->
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
// 消息提示与确认框（删除前二次确认）
import { ElMessage, ElMessageBox } from 'element-plus'
// 操作按钮图标，按需引入
import { Search, Refresh, Plus, Delete } from '@element-plus/icons-vue'
// 统一请求实例：内置 baseURL、鉴权与错误提示
import request from '@/utils/request'

// 列表加载状态，控制表格遮罩
const loading = ref(false)
// 当前页导入模板数据
const rows = ref([])
// 总记录数，用于分页与顶部统计
const total = ref(0)
// 勾选行，批量删除时取 id
const selection = ref([])
// 提交中状态，防止重复提交
const saving = ref(false)
// 弹窗显隐
const dialogVisible = ref(false)
// 弹窗标题，按新增/编辑切换
const dialogTitle = ref('新增导入模板')
// 表单实例，提交前校验用
const formRef = ref()

// 查询条件初始值：status 为 null 表示不限制状态
const query_orig = { page: 1, page_size: 10, template_name: '', template_key: '', status: null }
// 查询条件响应式副本
const query = reactive({ ...query_orig })

// 表单初始值：新增默认 xlsx + 启用；id 为 null 即新增态
const form_orig = {
  id: null, template_name: '', template_key: '', table_name: '', file_type: 'xlsx', status: 1, remark: ''
}
// 弹窗表单响应式副本
const form = reactive({ ...form_orig })

// 校验规则：名称与 Key 必填，失焦时提示，避免边输入边报错
const rules = {
  template_name: [{ required: true, message: '请输入模板名称', trigger: 'blur' }],
  template_key: [{ required: true, message: '请输入模板Key', trigger: 'blur' }]
}

// 本模块接口前缀
const apiBase = '/imprint/template'

// 拉取列表：query 含分页与筛选条件，整体作为 params 传递
async function fetchList() {
  loading.value = true
  try {
    const res = await request.get(apiBase + '/list', { params: query })
    // 无数据时 list 为 null，兜底成空数组让表格显示空状态
    rows.value = res.data.list || []
    // total 兜底为 0，避免分页组件异常
    total.value = res.data.total || 0
  // 无论成败都解除 loading，防止遮罩残留
  } finally { loading.value = false }
}

// 查询：回到第一页再请求
function handleSearch() { query.page = 1; fetchList() }
// 重置：整体还原查询条件后重新查询
function handleReset() { Object.assign(query, query_orig); handleSearch() }
// 勾选变化：同步选中行供批量删除使用
function onSelectionChange(r) { selection.value = r }

// 新增：恢复表单默认值并切换标题
function openCreate() { Object.assign(form, form_orig); dialogTitle.value = '新增导入模板'; dialogVisible.value = true }
// 编辑：先恢复默认值再回填整行，避免残留上次编辑内容
function openEdit(row) { Object.assign(form, form_orig, row); dialogTitle.value = '编辑导入模板'; dialogVisible.value = true }

// 提交：按 id 区分新增/更新；成功后关闭弹窗并刷新列表
async function submitForm() {
  // 校验失败会抛错并中止提交
  await formRef.value.validate()
  saving.value = true
  try {
    if (form.id) {
      // 编辑：剔除 id，只提交可更新字段
      const { id, ...data } = form
      await request.put(`${apiBase}/update/${id}`, data); ElMessage.success('更新成功')
    } else {
      // 新增：整份表单提交
      await request.post(apiBase + '/create', form); ElMessage.success('新增成功')
    }
    // 成功后收起弹窗并刷新列表
    dialogVisible.value = false; fetchList()
  // 失败时仅释放按钮 loading
  } finally { saving.value = false }
}

// 单条删除：二次确认后按 ids 数组提交
async function handleDelete(row) {
  await ElMessageBox.confirm('确定删除该导入模板？', '提示', { type: 'warning' })
  await request.delete(apiBase + '/delete', { data: { ids: [row.id] } })
  ElMessage.success('删除成功'); fetchList()
}

// 批量删除：勾选行 id 一次性提交
async function handleBatchDelete() {
  await ElMessageBox.confirm(`确定删除选中的 ${selection.value.length} 条？`, '提示', { type: 'warning' })
  await request.delete(apiBase + '/delete', { data: { ids: selection.value.map(r => r.id) } })
  ElMessage.success('批量删除成功'); fetchList()
}

// 挂载后立即加载第一页
onMounted(fetchList)
</script>
