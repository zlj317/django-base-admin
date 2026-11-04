<template>
  <div class="app-container">
    <div class="page-header">
      <div class="page-title-wrap">
        <h2>流程任务</h2>
        <div class="sub">全局人工任务监控与转派 · 共 {{ total }} 条记录</div>
      </div>
    </div>

    <el-card shadow="never" class="search-card">
      <el-form :model="query" inline @submit.prevent>
        <el-form-item label="任务状态">
          <el-select v-model="query.status" placeholder="请选择" clearable style="width: 150px">
            <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="处理人">
          <el-select v-model="query.assignee" placeholder="请选择" clearable filterable style="width: 180px">
            <el-option v-for="u in users" :key="u.id" :label="userLabel(u)" :value="u.id" />
          </el-select>
        </el-form-item>
        <el-form-item class="search-actions">
          <el-button type="primary" :icon="Search" @click="handleQuery">查询</el-button>
          <el-button :icon="Refresh" @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="table-card">
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据">
        <el-table-column type="index" label="序号" width="70" align="center" />
        <el-table-column label="任务节点" prop="task_name" min-width="140" show-overflow-tooltip />
        <el-table-column label="流程名称" prop="model_name" min-width="130" show-overflow-tooltip />
        <el-table-column label="业务单据号" prop="instance_key" min-width="150" show-overflow-tooltip />
        <el-table-column label="处理人" prop="assignee_name" width="110" align="center" />
        <el-table-column label="审批方式" prop="approve_mode_name" width="100" align="center" />
        <el-table-column label="任务状态" width="100" align="center">
          <template #default="scope">
            <el-tag :type="taskTagType(scope.row.status)">{{ scope.row.status_name }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="生成时间" prop="start_time" width="170" />
        <el-table-column label="到期时间" prop="due_time" width="170" />
        <el-table-column label="操作" width="150" align="center" fixed="right">
          <template #default="scope">
            <el-button link type="primary" :icon="View" @click="openDetail(scope.row)">查看</el-button>
            <el-button v-perm="'wf:task:transfer'" link type="warning" :icon="Switch"
              :disabled="scope.row.status !== 0 || scope.row.instance_status !== 0" @click="openTransfer(scope.row)">转派</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination-wrap">
        <el-pagination background layout="total, sizes, prev, pager, next, jumper"
          :total="total" v-model:current-page="query.page" v-model:page-size="query.page_size"
          :page-sizes="[10, 20, 50, 100]" @change="getList" />
      </div>
    </el-card>

    <el-dialog v-model="transferVisible" title="转派任务" width="460px" :close-on-click-modal="false">
      <el-form label-width="80px">
        <el-form-item label="任务节点">
          <el-input :model-value="transferTask.task_name" disabled />
        </el-form-item>
        <el-form-item label="转派给">
          <el-select v-model="transferUserId" filterable placeholder="请选择处理人" style="width: 100%">
            <el-option v-for="u in users" :key="u.id" :label="userLabel(u)" :value="u.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="转派说明">
          <el-input v-model="transferComment" type="textarea" :rows="3" placeholder="请输入转派说明" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="transferVisible = false">取消</el-button>
        <el-button type="primary" :loading="transferSaving" @click="submitTransfer">确定</el-button>
      </template>
    </el-dialog>

    <WorkflowDetail v-model="detailVisible" :instance-id="currentInstanceId" />
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Refresh, View, Switch } from '@element-plus/icons-vue'
import request from '@/utils/request'
import WorkflowDetail from '@/components/workflow/WorkflowDetail.vue'

const statusOptions = [
  { label: '待办', value: 0 },
  { label: '已办', value: 1 },
  { label: '已转派', value: 2 },
  { label: '已加签', value: 3 },
  { label: '已驳回', value: 4 }
]
const loading = ref(false)
const rows = ref([])
const total = ref(0)
const users = ref([])
const query = reactive({ page: 1, page_size: 10, status: '', assignee: '' })
const detailVisible = ref(false)
const currentInstanceId = ref(0)
const transferVisible = ref(false)
const transferSaving = ref(false)
const transferUserId = ref()
const transferComment = ref('')
const transferTask = reactive({ id: 0, task_name: '' })

function userLabel(user) {
  return user.nickname ? `${user.nickname}（${user.username}）` : user.username
}
function taskTagType(status) {
  return { 0: 'warning', 1: 'success', 2: 'info', 3: 'primary', 4: 'danger' }[status] || 'info'
}
async function getList() {
  loading.value = true
  try {
    const res = await request.get('/wf/task/list', { params: query })
    rows.value = res.data.list
    total.value = res.data.total
  } finally {
    loading.value = false
  }
}
async function loadUsers() {
  const res = await request.get('/wf/option/users')
  users.value = res.data || []
}
function handleQuery() {
  query.page = 1
  getList()
}
function resetQuery() {
  Object.assign(query, { page: 1, status: '', assignee: '' })
  getList()
}
function openDetail(row) {
  currentInstanceId.value = row.instance_id
  detailVisible.value = true
}
function openTransfer(row) {
  transferTask.id = row.id
  transferTask.task_name = row.task_name
  transferUserId.value = undefined
  transferComment.value = ''
  transferVisible.value = true
}
async function submitTransfer() {
  if (!transferUserId.value) {
    ElMessage.warning('请选择转派处理人')
    return
  }
  transferSaving.value = true
  try {
    await request.post(`/wf/task/transfer/${transferTask.id}`, {
      user_id: transferUserId.value,
      comment: transferComment.value
    })
    ElMessage.success('转派成功')
    transferVisible.value = false
    getList()
  } finally {
    transferSaving.value = false
  }
}

onMounted(async () => {
  await loadUsers()
  getList()
})
</script>
