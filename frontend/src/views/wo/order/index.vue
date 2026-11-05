<template>
  <div class="app-container">
    <div class="page-header">
      <div class="page-title-wrap">
        <h2>工单列表</h2>
        <div class="sub">工单管理 · 共 {{ total }} 条</div>
      </div>
    </div>
    <el-card shadow="never" class="search-card">
      <el-form :model="query" inline @submit.prevent>
        <el-form-item label="标题">
          <el-input v-model="query.title" placeholder="请输入工单标题" clearable style="width: 170px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="工单号">
          <el-input v-model="query.order_no" placeholder="请输入工单号" clearable style="width: 170px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="query.status" placeholder="全部" clearable style="width: 120px">
            <el-option v-for="s in statusOptions" :key="s.value" :label="s.label" :value="s.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="优先级">
          <el-select v-model="query.priority" placeholder="全部" clearable style="width: 120px">
            <el-option v-for="p in priorityOptions" :key="p.value" :label="p.label" :value="p.value" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="table-card">
      <template #header>
        <div class="card-header">
          <div class="card-actions">
            <el-button type="primary" :icon="Plus" @click="openCreate">新建工单</el-button>
          </div>
        </div>
      </template>
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据">
        <el-table-column type="index" label="序号" width="70" align="center" />
        <el-table-column label="工单号" prop="order_no" min-width="160" show-overflow-tooltip />
        <el-table-column label="标题" prop="title" min-width="200" show-overflow-tooltip />
        <el-table-column label="类型" min-width="100">
          <template #default="{ row }">{{ row.type_name || row.order_type_id || '-' }}</template>
        </el-table-column>
        <el-table-column label="优先级" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="priorityTag(row.priority)" effect="light" size="small">
              {{ priorityLabel(row.priority) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="110" align="center">
          <template #default="{ row }">
            <el-tag :type="statusTag(row.status)" effect="light" size="small">
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="创建人" min-width="100">
          <template #default="{ row }">{{ row.creator_name || row.creator_id || '-' }}</template>
        </el-table-column>
        <el-table-column label="处理人" min-width="100">
          <template #default="{ row }">{{ row.assignee_name || row.assignee_id || '-' }}</template>
        </el-table-column>
        <el-table-column label="期望时间" prop="expect_time" width="170" />
        <el-table-column label="关闭时间" prop="close_time" width="170" />
        <el-table-column label="操作" width="300" fixed="right" class-name="op-col">
          <template #default="{ row }">
            <div class="op-btns">
              <el-button link type="primary" @click="openDetail(row)">详情</el-button>
              <el-button link type="warning" v-if="row.status === 0 || row.status === 1" @click="openAssign(row)">指派</el-button>
              <el-button link type="success" v-if="row.status === 1" @click="handleSolve(row)">解决</el-button>
              <el-button link type="info" v-if="row.status !== 3" @click="handleClose(row)">关闭</el-button>
              <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
              <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination-wrap">
        <el-pagination background layout="total, sizes, prev, pager, next, jumper"
          :total="total" v-model:current-page="query.page" v-model:page-size="query.page_size"
          :page-sizes="[10, 20, 50, 100]" @change="fetchList" />
      </div>
    </el-card>

    <!-- 新建/编辑 Dialog -->
    <el-dialog :title="dialogTitle" v-model="dialogVisible" width="720px" :close-on-click-modal="false" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-row :gutter="12">
          <el-col :span="24">
            <el-form-item label="标题" prop="title">
              <el-input v-model="form.title" placeholder="请输入工单标题" maxlength="200" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="工单类型" prop="order_type_id">
              <el-select v-model="form.order_type_id" placeholder="请选择类型" style="width:100%">
                <el-option v-for="t in typeOptions" :key="t.id" :label="t.type_name" :value="t.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="优先级" prop="priority">
              <el-select v-model="form.priority" placeholder="请选择" style="width:100%">
                <el-option v-for="p in priorityOptions" :key="p.value" :label="p.label" :value="p.value" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="创建人" prop="creator_id">
              <el-input-number v-model="form.creator_id" :min="1" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="处理人" prop="assignee_id">
              <el-input-number v-model="form.assignee_id" :min="0" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="期望时间" prop="expect_time">
              <el-date-picker v-model="form.expect_time" type="datetime" placeholder="选择期望时间" value-format="YYYY-MM-DD HH:mm:ss" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="附件ID" prop="attachment_ids">
              <el-input v-model="form.attachment_ids" placeholder="逗号分隔" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="工单内容" prop="content">
              <el-input v-model="form.content" type="textarea" :rows="5" placeholder="请详细描述工单内容" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible=false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitForm">确定</el-button>
      </template>
    </el-dialog>

    <!-- 详情抽屉 -->
    <el-drawer v-model="detailVisible" :title="detailData.title || '工单详情'" size="540px" destroy-on-close>
      <div v-if="detailData.id" class="detail-body">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="工单号">{{ detailData.order_no }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="statusTag(detailData.status)" effect="light">{{ statusLabel(detailData.status) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="优先级">
            <el-tag :type="priorityTag(detailData.priority)" effect="light">{{ priorityLabel(detailData.priority) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="工单类型">{{ detailData.type_name || detailData.order_type_id || '-' }}</el-descriptions-item>
          <el-descriptions-item label="创建人">{{ detailData.creator_name || detailData.creator_id || '-' }}</el-descriptions-item>
          <el-descriptions-item label="处理人">{{ detailData.assignee_name || detailData.assignee_id || '-' }}</el-descriptions-item>
          <el-descriptions-item label="期望时间">{{ detailData.expect_time || '-' }}</el-descriptions-item>
          <el-descriptions-item label="关闭时间">{{ detailData.close_time || '-' }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ detailData.create_time || '-' }}</el-descriptions-item>
        </el-descriptions>
        <div class="detail-section">
          <div class="detail-section-title">📝 工单内容</div>
          <div class="detail-content">{{ detailData.content || '（无内容）' }}</div>
        </div>
        <div class="detail-section" v-if="detailData.attachment_ids">
          <div class="detail-section-title">📎 附件</div>
          <div class="detail-content mono">{{ detailData.attachment_ids }}</div>
        </div>
        <div class="detail-section">
          <div class="detail-section-title">🕒 处理日志</div>
          <el-timeline v-if="workLogs.length">
            <el-timeline-item v-for="(log, i) in workLogs" :key="i" :timestamp="log.create_time || log.time || ''">
              <div>
                <strong>{{ log.operator_name || log.operator_id || '系统' }}</strong>
                <span class="muted"> 执行了 </span>
                <el-tag effect="light" size="small">{{ log.action || log.action_label || '处理' }}</el-tag>
              </div>
              <div class="log-remark">{{ log.remark || log.content || '' }}</div>
            </el-timeline-item>
          </el-timeline>
          <div v-else class="empty-tip">暂无处理日志</div>
        </div>
      </div>
    </el-drawer>

    <!-- 指派 Dialog -->
    <el-dialog title="指派工单" v-model="assignVisible" width="420px" destroy-on-close>
      <el-form label-width="90px">
        <el-form-item label="工单标题">
          <span>{{ assignData.title }}</span>
        </el-form-item>
        <el-form-item label="处理人ID" required>
          <el-input-number v-model="assignAssignee" :min="1" style="width:100%" placeholder="请输入处理人用户ID" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="assignVisible=false">取消</el-button>
        <el-button type="primary" :loading="assigning" @click="submitAssign">确定指派</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Refresh, Plus } from '@element-plus/icons-vue'
import request from '@/utils/request'

const loading = ref(false)
const rows = ref([])
const total = ref(0)
const saving = ref(false)
const dialogVisible = ref(false)
const dialogTitle = ref('新建工单')
const formRef = ref()
const typeOptions = ref([])

const query_orig = { page: 1, page_size: 10, title: '', order_no: '', status: null, priority: null }
const query = reactive({ ...query_orig })

const statusOptions = [
  { value: 0, label: '待处理' },
  { value: 1, label: '处理中' },
  { value: 2, label: '已解决' },
  { value: 3, label: '已关闭' }
]
const priorityOptions = [
  { value: 1, label: '低' },
  { value: 2, label: '中' },
  { value: 3, label: '高' }
]

function statusLabel(v) { return statusOptions.find(x => x.value === v)?.label || '未知' }
function statusTag(v) { return ({ 0: 'info', 1: 'primary', 2: 'success', 3: 'info' })[v] || 'info' }
function priorityLabel(v) { return priorityOptions.find(x => x.value === v)?.label || '未知' }
function priorityTag(v) { return ({ 1: 'success', 2: 'warning', 3: 'danger' })[v] || 'info' }

const form_orig = {
  id: null, title: '', content: '', order_type_id: null, priority: 2,
  creator_id: null, assignee_id: null, attachment_ids: '', expect_time: '', status: 0
}
const form = reactive({ ...form_orig })

const rules = {
  title: [{ required: true, message: '请输入工单标题', trigger: 'blur' }],
  priority: [{ required: true, message: '请选择优先级', trigger: 'change' }]
}

// 详情抽屉
const detailVisible = ref(false)
const detailData = reactive({})
const workLogs = ref([])

// 指派
const assignVisible = ref(false)
const assignData = reactive({ id: null, title: '' })
const assignAssignee = ref(null)
const assigning = ref(false)

function apiUrl(action) {
  const base = '/wo/order'
  return { list: base + '/list', create: base + '/create', update: base + '/update', delete: base + '/delete' }[action]
}

async function fetchList() {
  loading.value = true
  try {
    const res = await request.get(apiUrl('list'), { params: query })
    rows.value = res.data.list || []
    total.value = res.data.total || 0
  } finally { loading.value = false }
}

async function loadTypeOptions() {
  try {
    const res = await request.get('/wo/type/list', { params: { page: 1, page_size: 200 } })
    typeOptions.value = res.data.list || []
  } catch { /* ignore */ }
}

function handleSearch() { query.page = 1; fetchList() }
function handleReset() { Object.assign(query, query_orig); handleSearch() }

function openCreate() {
  Object.assign(form, form_orig)
  dialogTitle.value = '新建工单'
  dialogVisible.value = true
}
function openEdit(row) {
  Object.assign(form, form_orig, row)
  dialogTitle.value = '编辑工单'
  dialogVisible.value = true
}

async function submitForm() {
  await formRef.value.validate()
  saving.value = true
  try {
    if (form.id) {
      const { id, ...data } = form
      await request.put(`${apiUrl('update')}/${id}`, data); ElMessage.success('更新成功')
    } else {
      await request.post(apiUrl('create'), form); ElMessage.success('新建成功')
    }
    dialogVisible.value = false; fetchList()
  } finally { saving.value = false }
}

async function openDetail(row) {
  Object.assign(detailData, { ...row })
  workLogs.value = []
  try {
    const res = await request.get('/wo/log/list', { params: { order_id: row.id, page: 1, page_size: 50 } })
    workLogs.value = res.data?.list || []
  } catch { /* ignore */ }
  detailVisible.value = true
}

function openAssign(row) {
  assignData.id = row.id
  assignData.title = row.title
  assignAssignee.value = row.assignee_id || null
  assignVisible.value = true
}

async function submitAssign() {
  if (!assignAssignee.value) {
    ElMessage.warning('请输入处理人ID'); return
  }
  assigning.value = true
  try {
    await request.put(`/wo/order/assign/${assignData.id}`, { assignee_id: assignAssignee.value })
    ElMessage.success('指派成功')
    assignVisible.value = false; fetchList()
  } finally { assigning.value = false }
}

async function handleSolve(row) {
  await ElMessageBox.confirm(`确定将工单「${row.title}」标记为已解决？`, '提示', { type: 'warning' })
  await request.put(`/wo/order/solve/${row.id}`)
  ElMessage.success('工单已解决'); fetchList()
}

async function handleClose(row) {
  await ElMessageBox.confirm(`确定关闭工单「${row.title}」？`, '提示', { type: 'warning' })
  await request.put(`/wo/order/close/${row.id}`)
  ElMessage.success('工单已关闭'); fetchList()
}

async function handleDelete(row) {
  await ElMessageBox.confirm(`确定删除工单「${row.title}」？`, '提示', { type: 'warning' })
  await request.delete(apiUrl('delete'), { data: { ids: [row.id] } })
  ElMessage.success('删除成功'); fetchList()
}

onMounted(() => { fetchList(); loadTypeOptions() })
</script>

<style scoped>
.detail-body { padding: 0 6px; }
.detail-section { margin-top: 20px; }
.detail-section-title {
  font-size: 14px; font-weight: 600; color: var(--app-text-1); margin-bottom: 10px;
  padding-bottom: 6px; border-bottom: 1px solid var(--app-border-light);
}
.detail-content { font-size: 13px; color: var(--app-text-2); line-height: 1.8; padding: 12px 14px; background: var(--app-surface-2); border-radius: 8px; white-space: pre-wrap; word-break: break-all; }
.mono { font-family: Menlo, Monaco, Consolas, monospace; font-size: 12px; }
.muted { color: var(--app-text-3); }
.log-remark { margin-top: 6px; font-size: 12px; color: var(--app-text-2); }
.empty-tip { color: var(--app-text-3); font-size: 12px; padding: 10px 0; }
.op-btns { display: flex; flex-wrap: nowrap; align-items: center; white-space: nowrap; }
.op-btns .el-button { margin-left: 0; padding: 0 4px; }
</style>
