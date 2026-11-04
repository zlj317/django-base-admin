<template>
  <div class="app-container">
    <div class="page-header">
      <div class="page-title-wrap">
        <h2>我的工单</h2>
        <div class="sub">与我相关 · 共 {{ total }} 条</div>
      </div>
      <div class="page-header-actions">
        <el-button :icon="Refresh" @click="fetchList">刷新</el-button>
      </div>
    </div>

    <el-card shadow="never" class="search-card">
      <el-form :model="query" inline @submit.prevent>
        <el-form-item label="标题">
          <el-input v-model="query.title" placeholder="请输入工单标题" clearable style="width: 180px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="query.status" placeholder="全部" clearable style="width: 120px">
            <el-option v-for="s in statusOptions" :key="s.value" :label="s.label" :value="s.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="优先级">
          <el-select v-model="query.priority" placeholder="全部" clearable style="width: 110px">
            <el-option v-for="p in priorityOptions" :key="p.value" :label="p.label" :value="p.value" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <el-button :icon="RefreshRight" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="table-card">
      <template #header>
        <div class="card-header">
          <el-radio-group v-model="scope" @change="handleScopeChange">
            <el-radio-button value="created">我创建的</el-radio-button>
            <el-radio-button value="assigned">我处理的</el-radio-button>
          </el-radio-group>
        </div>
      </template>
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无工单">
        <el-table-column type="index" label="序号" width="70" align="center" />
        <el-table-column label="工单号" prop="order_no" min-width="150" show-overflow-tooltip />
        <el-table-column label="标题" prop="title" min-width="200" show-overflow-tooltip />
        <el-table-column label="类型" min-width="100">
          <template #default="{ row }">{{ row.type_name || typeName(row.order_type_id) }}</template>
        </el-table-column>
        <el-table-column label="优先级" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="priorityTag(row.priority)" effect="light" size="small">{{ priorityLabel(row.priority) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="statusTag(row.status)" effect="light" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="创建人" min-width="100">
          <template #default="{ row }">{{ userNames[row.creator_id] || row.creator_id || '-' }}</template>
        </el-table-column>
        <el-table-column label="处理人" min-width="100">
          <template #default="{ row }">{{ userNames[row.assignee_id] || row.assignee_id || '-' }}</template>
        </el-table-column>
        <el-table-column label="创建时间" prop="create_time" width="170" />
        <el-table-column label="操作" width="190" fixed="right" class-name="op-col">
          <template #default="{ row }">
            <div class="op-btns">
              <el-button link type="primary" @click="openDetail(row)">详情</el-button>
              <el-button link type="success" v-if="row.status === 1" @click="handleSolve(row)">解决</el-button>
              <el-button link type="info" v-if="row.status !== 3" @click="handleClose(row)">关闭</el-button>
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

    <el-drawer v-model="detailVisible" :title="detailData.title || '工单详情'" size="540px" destroy-on-close>
      <div v-if="detailData.id" class="detail-body">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="工单号">{{ detailData.order_no || '-' }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="statusTag(detailData.status)" effect="light">{{ statusLabel(detailData.status) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="优先级">
            <el-tag :type="priorityTag(detailData.priority)" effect="light">{{ priorityLabel(detailData.priority) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="工单类型">{{ detailData.type_name || typeName(detailData.order_type_id) }}</el-descriptions-item>
          <el-descriptions-item label="创建人">{{ userNames[detailData.creator_id] || detailData.creator_id || '-' }}</el-descriptions-item>
          <el-descriptions-item label="处理人">{{ userNames[detailData.assignee_id] || detailData.assignee_id || '-' }}</el-descriptions-item>
          <el-descriptions-item label="期望时间">{{ detailData.expect_time || '-' }}</el-descriptions-item>
          <el-descriptions-item label="关闭时间">{{ detailData.close_time || '-' }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ detailData.create_time || '-' }}</el-descriptions-item>
        </el-descriptions>
        <div class="detail-section">
          <div class="detail-section-title">工单内容</div>
          <div class="detail-content">{{ detailData.content || '（无内容）' }}</div>
        </div>
        <div class="detail-section">
          <div class="detail-section-title">处理日志</div>
          <el-timeline v-if="workLogs.length">
            <el-timeline-item v-for="(log, i) in workLogs" :key="i" :timestamp="log.create_time || ''">
              <div>
                <strong>{{ userNames[log.operator_id] || log.operator_id || '系统' }}</strong>
                <span class="muted"> 执行了 </span>
                <el-tag effect="light" size="small">{{ actionLabel(log.action) }}</el-tag>
              </div>
              <div class="log-remark">{{ log.comment || '' }}</div>
            </el-timeline-item>
          </el-timeline>
          <div v-else class="empty-tip">暂无处理日志</div>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Refresh, RefreshRight } from '@element-plus/icons-vue'
import request from '@/utils/request'
import { auth } from '@/store/auth'

const loading = ref(false)
const rows = ref([])
const total = ref(0)
const scope = ref('created')
const typeOptions = ref([])
const userNames = reactive({})

const query_orig = { page: 1, page_size: 10, title: '', status: null, priority: null }
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
function actionLabel(v) { return ({ assign: '指派', solve: '解决', close: '关闭', create: '创建' })[v] || v || '处理' }
function typeName(id) { return typeOptions.value.find(t => t.id === id)?.type_name || '-' }

const detailVisible = ref(false)
const detailData = reactive({})
const workLogs = ref([])

async function fetchList() {
  loading.value = true
  try {
    const params = { ...query }
    const myId = auth.user?.id
    if (myId) {
      params[scope.value === 'created' ? 'creator_id' : 'assignee_id'] = myId
    }
    const res = await request.get('/wo/order/list', { params })
    rows.value = res.data.list || []
    total.value = res.data.total || 0
  } finally { loading.value = false }
}

async function loadOptions() {
  try {
    const res = await request.get('/wo/type/list', { params: { page: 1, page_size: 200 } })
    typeOptions.value = res.data.list || []
  } catch { /* ignore */ }
  try {
    const res = await request.get('/system/user/list', { params: { page: 1, page_size: 500 } })
    ;(res.data.list || []).forEach(u => { userNames[u.id] = u.nickname || u.username || u.id })
  } catch { /* ignore */ }
}

function handleScopeChange() { query.page = 1; fetchList() }
function handleSearch() { query.page = 1; fetchList() }
function handleReset() { Object.assign(query, query_orig); handleSearch() }

async function openDetail(row) {
  Object.assign(detailData, { ...row })
  workLogs.value = []
  detailVisible.value = true
  try {
    const res = await request.get('/wo/log/list', { params: { order_id: row.id, page: 1, page_size: 50 } })
    workLogs.value = res.data?.list || []
  } catch { /* ignore */ }
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

onMounted(() => { fetchList(); loadOptions() })
</script>

<style scoped>
.detail-body { padding: 0 6px; }
.detail-section { margin-top: 20px; }
.detail-section-title {
  font-size: 14px; font-weight: 600; color: #1f2937; margin-bottom: 10px;
  padding-bottom: 6px; border-bottom: 1px solid #f1f5f9;
}
.detail-content { font-size: 13px; color: #4b5563; line-height: 1.8; padding: 12px 14px; background: #f8fafc; border-radius: 8px; white-space: pre-wrap; word-break: break-word; }
.muted { color: #9ca3af; }
.log-remark { margin-top: 6px; font-size: 12px; color: #6b7280; }
.empty-tip { color: #9ca3af; font-size: 12px; padding: 10px 0; }
.op-btns { display: flex; flex-wrap: nowrap; align-items: center; white-space: nowrap; }
.op-btns .el-button { margin-left: 0; padding: 0 4px; }
</style>
