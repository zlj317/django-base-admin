<template>
  <div class="app-container">
    <div class="page-header">
      <div class="page-title-wrap">
        <h2>已办任务</h2>
        <div class="sub">我已处理过的审批任务 · 共 {{ total }} 条记录</div>
      </div>
    </div>

    <el-card shadow="never" class="table-card">
      <template #header>
        <div class="card-header">
          <div class="card-actions">
            <el-button :icon="Refresh" @click="getList">刷新</el-button>
          </div>
        </div>
      </template>
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无已办任务">
        <el-table-column type="index" label="序号" width="70" align="center" />
        <el-table-column label="任务节点" prop="task_name" min-width="140" show-overflow-tooltip />
        <el-table-column label="流程名称" prop="model_name" min-width="130" show-overflow-tooltip />
        <el-table-column label="业务单据号" prop="instance_key" min-width="160" show-overflow-tooltip />
        <el-table-column label="发起人" prop="start_user_name" width="100" align="center" />
        <el-table-column label="审批方式" prop="approve_mode_name" width="100" align="center" />
        <el-table-column label="处理结果" width="100" align="center">
          <template #default="scope">
            <el-tag :type="taskTagType(scope.row.status)">{{ scope.row.status_name }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="生成时间" prop="start_time" width="170" />
        <el-table-column label="完成时间" prop="end_time" width="170" />
        <el-table-column label="操作" width="100" align="center" fixed="right">
          <template #default="scope">
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

    <WorkflowDetail v-model="detailVisible" :instance-id="currentInstanceId" />
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { Refresh, View } from '@element-plus/icons-vue'
import request from '@/utils/request'
import WorkflowDetail from '@/components/workflow/WorkflowDetail.vue'

const loading = ref(false)
const rows = ref([])
const total = ref(0)
const query = reactive({ page: 1, page_size: 10 })
const detailVisible = ref(false)
const currentInstanceId = ref(0)

function taskTagType(status) {
  return { 0: 'warning', 1: 'success', 2: 'info', 3: 'primary', 4: 'danger' }[status] || 'info'
}
async function getList() {
  loading.value = true
  try {
    const res = await request.get('/wf/task/done', { params: query })
    rows.value = res.data.list
    total.value = res.data.total
  } finally {
    loading.value = false
  }
}
function openDetail(row) {
  currentInstanceId.value = row.instance_id
  detailVisible.value = true
}

onMounted(getList)
</script>
