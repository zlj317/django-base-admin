<template>
  <div class="app-container">
    <div class="page-header">
      <div class="page-title-wrap">
        <h2>待办任务</h2>
        <div class="sub">待我审批的流程任务 · 共 {{ total }} 条记录</div>
      </div>
    </div>

    <el-card shadow="never" class="table-card">
      <template #header>
        <div class="card-header">
          <span class="card-title">我的待办</span>
          <div class="card-actions">
            <el-button :icon="Refresh" @click="getList">刷新</el-button>
          </div>
        </div>
      </template>
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无待办任务">
        <el-table-column label="编号" prop="id" width="70" align="center" />
        <el-table-column label="任务节点" prop="task_name" min-width="140" show-overflow-tooltip />
        <el-table-column label="流程名称" prop="model_name" min-width="130" show-overflow-tooltip />
        <el-table-column label="业务单据号" prop="instance_key" min-width="160" show-overflow-tooltip />
        <el-table-column label="发起人" prop="start_user_name" width="100" align="center" />
        <el-table-column label="审批方式" prop="approve_mode_name" width="100" align="center" />
        <el-table-column label="生成时间" prop="start_time" width="170" />
        <el-table-column label="到期时间" prop="due_time" width="170">
          <template #default="scope">{{ scope.row.due_time || '-' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="300" align="center" fixed="right">
          <template #default="scope">
            <el-button v-perm="'wf:task:approve'" link type="success" :icon="Check" @click="openAction(scope.row, 'approve')">同意</el-button>
            <el-button v-perm="'wf:task:reject'" link type="danger" :icon="Close" @click="openAction(scope.row, 'reject')">驳回</el-button>
            <el-button v-perm="'wf:task:transfer'" link type="warning" :icon="Switch" @click="openAssign(scope.row, 'transfer')">转审</el-button>
            <el-button v-perm="'wf:task:addsign'" link type="primary" :icon="Plus" @click="openAssign(scope.row, 'addsign')">加签</el-button>
            <el-button v-perm="'wf:task:back'" link type="info" :icon="Back" @click="openAction(scope.row, 'back')">退回</el-button>
            <el-button link type="primary" :icon="View" @click="openDetail(scope.row)">查看</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination-wrap">
        <el-pagination background layout="total, sizes, prev, pager, next, jumper"
          :total="total" v-model:current-page="query.page" v-model:page-size="query.page_size"
          :page-sizes="[10, 20, 50, 100]" @change="getList" />
      </div>
    </el-card>

    <!-- 审批动作弹窗：同意/驳回/退回共用 -->
    <el-dialog v-model="actionVisible" :title="actionTitle" width="480px" :close-on-click-modal="false">
      <el-form label-width="80px">
        <el-form-item label="任务节点">
          <el-input :model-value="currentTask.task_name" disabled />
        </el-form-item>
        <el-form-item label="审批意见">
          <el-input v-model="actionComment" type="textarea" :rows="4"
            :placeholder="actionRequireComment ? '驳回必须填写审批意见' : '请输入审批意见（选填）'" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="actionVisible = false">取消</el-button>
        <el-button type="primary" :loading="actionSaving" @click="submitAction">确定</el-button>
      </template>
    </el-dialog>

    <!-- 转审/加签弹窗 -->
    <el-dialog v-model="assignVisible" :title="assignTitle" width="480px" :close-on-click-modal="false">
      <el-form label-width="80px">
        <el-form-item label="任务节点">
          <el-input :model-value="currentTask.task_name" disabled />
        </el-form-item>
        <el-form-item :label="assignLabel">
          <el-select v-model="assignUserId" filterable placeholder="请选择用户" style="width: 100%">
            <el-option v-for="u in users" :key="u.id" :label="userLabel(u)" :value="u.id"
              :disabled="u.id === currentTask.assignee" />
          </el-select>
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="assignComment" type="textarea" :rows="4" placeholder="请输入说明（选填）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="assignVisible = false">取消</el-button>
        <el-button type="primary" :loading="assignSaving" @click="submitAssign">确定</el-button>
      </template>
    </el-dialog>

    <WorkflowDetail v-model="detailVisible" :instance-id="currentInstanceId" />
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, View, Check, Close, Switch, Plus, Back } from '@element-plus/icons-vue'
import request from '@/utils/request'
import WorkflowDetail from '@/components/workflow/WorkflowDetail.vue'

const loading = ref(false)
const rows = ref([])
const total = ref(0)
const users = ref([])
const query = reactive({ page: 1, page_size: 10 })
const detailVisible = ref(false)
const currentInstanceId = ref(0)

// 审批动作弹窗状态
const actionVisible = ref(false)
const actionSaving = ref(false)
const actionType = ref('approve')
const actionComment = ref('')
const currentTask = reactive({ id: 0, task_name: '', assignee: 0 })
const actionRequireComment = ref(false)

// 转审/加签弹窗状态
const assignVisible = ref(false)
const assignSaving = ref(false)
const assignType = ref('transfer')
const assignUserId = ref()
const assignComment = ref('')

const actionTitles = { approve: '审批同意', reject: '审批驳回', back: '退回上一步' }
const assignTitles = { transfer: '转审任务', addsign: '加签任务' }
const actionTitle = ref('')
const assignTitle = ref('')
const assignLabel = ref('转审给')

function userLabel(user) {
  return user.nickname ? `${user.nickname}（${user.username}）` : user.username
}
async function getList() {
  loading.value = true
  try {
    const res = await request.get('/wf/task/todo', { params: query })
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
function openDetail(row) {
  currentInstanceId.value = row.instance_id
  detailVisible.value = true
}
function openAction(row, type) {
  Object.assign(currentTask, { id: row.id, task_name: row.task_name, assignee: row.assignee })
  actionType.value = type
  actionComment.value = ''
  actionTitle.value = actionTitles[type]
  actionRequireComment.value = type === 'reject'
  actionVisible.value = true
}
function openAssign(row, type) {
  Object.assign(currentTask, { id: row.id, task_name: row.task_name, assignee: row.assignee })
  assignType.value = type
  assignUserId.value = undefined
  assignComment.value = ''
  assignTitle.value = assignTitles[type]
  assignLabel.value = type === 'transfer' ? '转审给' : '加签人'
  assignVisible.value = true
}
async function submitAction() {
  if (actionRequireComment.value && !actionComment.value.trim()) {
    ElMessage.warning('请填写驳回意见')
    return
  }
  actionSaving.value = true
  try {
    await request.post(`/wf/task/${actionType.value}/${currentTask.id}`, { comment: actionComment.value })
    ElMessage.success(actionType.value === 'approve' ? '审批通过' : actionType.value === 'reject' ? '已驳回' : '已退回')
    actionVisible.value = false
    getList()
  } finally {
    actionSaving.value = false
  }
}
async function submitAssign() {
  if (!assignUserId.value) {
    ElMessage.warning(assignLabel.value === '加签人' ? '请选择加签人' : '请选择转审人')
    return
  }
  assignSaving.value = true
  try {
    await request.post(`/wf/task/${assignType.value}/${currentTask.id}`, {
      user_id: assignUserId.value,
      comment: assignComment.value
    })
    ElMessage.success(assignType.value === 'transfer' ? '转审成功' : '加签成功')
    assignVisible.value = false
    getList()
  } finally {
    assignSaving.value = false
  }
}

onMounted(async () => {
  await loadUsers()
  getList()
})
</script>
