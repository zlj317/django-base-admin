<template>
  <div class="app-container">
    <div class="page-header">
      <div class="page-title-wrap">
        <h2>请假查询</h2>
        <div class="sub">OA 请假流程实例 · 共 {{ total }} 条记录</div>
      </div>
    </div>

    <el-card shadow="never" class="search-card">
      <el-form :model="query" inline @submit.prevent>
        <el-form-item label="流程状态">
          <el-select v-model="query.status" placeholder="请选择" clearable style="width: 160px">
            <el-option label="运行中" :value="0" />
            <el-option label="已完成" :value="1" />
            <el-option label="已驳回" :value="2" />
            <el-option label="已终止" :value="3" />
          </el-select>
        </el-form-item>
        <el-form-item label="业务单据号">
          <el-input v-model="query.biz_key" placeholder="请输入业务单据号" clearable style="width: 180px" @keyup.enter="handleQuery" />
        </el-form-item>
        <el-form-item class="search-actions">
          <el-button type="primary" :icon="Search" @click="handleQuery">查询</el-button>
          <el-button :icon="Refresh" @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="table-card">
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无请假流程数据">
        <el-table-column type="index" label="序号" width="70" align="center" />
        <el-table-column label="业务单据号" prop="biz_key" min-width="160" show-overflow-tooltip />
        <el-table-column label="请假类型" min-width="100" align="center">
          <template #default="scope">{{ scope.row.form_data_obj?.leaveType || '-' }}</template>
        </el-table-column>
        <el-table-column label="开始日期" min-width="120" align="center">
          <template #default="scope">{{ scope.row.form_data_obj?.startDate || '-' }}</template>
        </el-table-column>
        <el-table-column label="结束日期" min-width="120" align="center">
          <template #default="scope">{{ scope.row.form_data_obj?.endDate || '-' }}</template>
        </el-table-column>
        <el-table-column label="请假天数" width="100" align="center">
          <template #default="scope">{{ scope.row.form_data_obj?.leaveDays ?? '-' }}</template>
        </el-table-column>
        <el-table-column label="请假事由" min-width="180" show-overflow-tooltip>
          <template #default="scope">{{ scope.row.form_data_obj?.reason || '-' }}</template>
        </el-table-column>
        <el-table-column label="发起人" prop="start_user_name" width="100" align="center" />
        <el-table-column label="流程状态" width="100" align="center">
          <template #default="scope">
            <el-tag :type="statusType(scope.row.status)">{{ scope.row.status_name }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="申请时间" prop="start_time" width="170" />
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
import { Search, Refresh, View } from '@element-plus/icons-vue'
import request from '@/utils/request'
import WorkflowDetail from '@/components/workflow/WorkflowDetail.vue'

const loading = ref(false)
const rows = ref([])
const total = ref(0)
const modelId = ref(0)
const query = reactive({ page: 1, page_size: 10, status: '', biz_key: '' })
const detailVisible = ref(false)
const currentInstanceId = ref(0)

function statusType(status) {
  return { 0: 'warning', 1: 'success', 2: 'danger', 3: 'info' }[status] || 'info'
}
async function resolveModel() {
  // 通过模型选项定位请假流程（model_key = leave）
  const res = await request.get('/wf/model/options')
  const target = (res.data || []).find(item => item.model_key === 'leave')
  modelId.value = target ? target.id : 0
}
async function getList() {
  loading.value = true
  try {
    const params = { ...query, model_id: modelId.value }
    const res = await request.get('/wf/instance/list', { params })
    rows.value = res.data.list
    total.value = res.data.total
  } finally {
    loading.value = false
  }
}
function handleQuery() {
  query.page = 1
  getList()
}
function resetQuery() {
  Object.assign(query, { page: 1, status: '', biz_key: '' })
  getList()
}
function openDetail(row) {
  currentInstanceId.value = row.id
  detailVisible.value = true
}

onMounted(async () => {
  await resolveModel()
  getList()
})
</script>
