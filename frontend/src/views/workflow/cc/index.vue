<template>
  <div class="app-container">
    <div class="page-header">
      <div class="page-title-wrap">
        <h2>抄送我的</h2>
        <div class="sub">抄送给我的流程通知 · 共 {{ total }} 条记录</div>
      </div>
    </div>

    <el-card shadow="never" class="table-card">
      <template #header>
        <div class="card-header">
          <span class="card-title">抄送列表</span>
          <div class="card-actions">
            <el-button :icon="Refresh" @click="getList">刷新</el-button>
          </div>
        </div>
      </template>
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无抄送记录">
        <el-table-column label="编号" prop="id" width="70" align="center" />
        <el-table-column label="流程名称" prop="model_name" min-width="140" show-overflow-tooltip />
        <el-table-column label="发起人" prop="start_user_name" width="110" align="center" />
        <el-table-column label="抄送节点" prop="node_id" min-width="140" show-overflow-tooltip>
          <template #default="scope">{{ scope.row.node_id || '-' }}</template>
        </el-table-column>
        <el-table-column label="流程状态" width="100" align="center">
          <template #default="scope">
            <el-tag :type="instanceTagType(scope.row.instance_status)">
              {{ instanceStatusName(scope.row.instance_status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="阅读状态" width="100" align="center">
          <template #default="scope">
            <el-tag :type="scope.row.status === 1 ? 'info' : 'warning'">{{ scope.row.status_name }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="抄送时间" prop="create_time" width="170" />
        <el-table-column label="操作" width="170" align="center" fixed="right">
          <template #default="scope">
            <el-button link type="primary" :icon="View" @click="openDetail(scope.row)">查看</el-button>
            <el-button v-if="scope.row.status !== 1" link type="success" :icon="Check" @click="markRead(scope.row)">标记已读</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination-wrap">
        <el-pagination background layout="total, sizes, prev, pager, next, jumper"
          :total="total" v-model:current-page="query.page" v-model:page-size="query.page_size"
          :page-sizes="[10, 20, 50, 100]" @change="getList" />
      </div>
    </el-card>

    <WorkflowDetail v-model="detailVisible" :instance-id="currentInstanceId" />
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, View, Check } from '@element-plus/icons-vue'
import request from '@/utils/request'
import WorkflowDetail from '@/components/workflow/WorkflowDetail.vue'

const loading = ref(false)
const rows = ref([])
const total = ref(0)
const query = reactive({ page: 1, page_size: 10 })
const detailVisible = ref(false)
const currentInstanceId = ref(0)

const instanceStatusMap = { 0: '运行中', 1: '已完成', 2: '已驳回', 3: '已终止' }
function instanceStatusName(status) {
  return instanceStatusMap[status] || '-'
}
function instanceTagType(status) {
  return { 0: 'warning', 1: 'success', 2: 'danger', 3: 'info' }[status] || 'info'
}
async function getList() {
  loading.value = true
  try {
    const res = await request.get('/wf/cc/mine', { params: query })
    rows.value = res.data.list
    total.value = res.data.total
  } finally {
    loading.value = false
  }
}
function openDetail(row) {
  currentInstanceId.value = row.instance_id
  detailVisible.value = true
  if (row.status !== 1) markRead(row, true)
}
async function markRead(row, silent = false) {
  await request.post(`/wf/cc/read/${row.id}`)
  if (!silent) ElMessage.success('已标记为已读')
  row.status = 1
  row.status_name = '已读'
}
</script>
