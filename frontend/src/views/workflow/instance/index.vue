<template>
  <div class="app-container">
    <div class="page-header">
      <div class="page-title-wrap">
        <h2>流程实例</h2>
        <div class="sub">全部流程实例监控 · 共 {{ total }} 条记录</div>
      </div>
    </div>

    <el-card shadow="never" class="search-card">
      <el-form :model="query" inline @submit.prevent>
        <el-form-item label="流程模型">
          <el-select v-model="query.model_id" placeholder="请选择" clearable style="width: 190px">
            <el-option v-for="m in modelOptions" :key="m.id" :label="m.model_name" :value="m.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="流程状态">
          <el-select v-model="query.status" placeholder="请选择" clearable style="width: 150px">
            <el-option label="运行中" :value="0" />
            <el-option label="已完成" :value="1" />
            <el-option label="已驳回" :value="2" />
            <el-option label="已终止" :value="3" />
          </el-select>
        </el-form-item>
        <el-form-item label="业务单据号">
          <el-input v-model="query.biz_key" placeholder="请输入单据号" clearable style="width: 180px" @keyup.enter="handleQuery" />
        </el-form-item>
        <el-form-item class="search-actions">
          <el-button type="primary" :icon="Search" @click="handleQuery">查询</el-button>
          <el-button :icon="Refresh" @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="table-card">
      <template #header>
        <div class="card-header">
          <span class="card-title">实例列表</span>
        </div>
      </template>
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据">
        <el-table-column label="编号" prop="id" width="70" align="center" />
        <el-table-column label="业务单据号" prop="biz_key" min-width="160" show-overflow-tooltip />
        <el-table-column label="流程名称" prop="model_name" min-width="130" show-overflow-tooltip />
        <el-table-column label="版本" width="70" align="center">
          <template #default="scope">v{{ scope.row.model_version }}</template>
        </el-table-column>
        <el-table-column label="发起人" prop="start_user_name" width="110" align="center" />
        <el-table-column label="流程状态" width="100" align="center">
          <template #default="scope">
            <el-tag :type="statusType(scope.row.status)">{{ scope.row.status_name }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="当前节点" prop="current_node" min-width="130" show-overflow-tooltip />
        <el-table-column label="发起时间" prop="start_time" width="170" />
        <el-table-column label="结束时间" prop="end_time" width="170" />
        <el-table-column label="操作" width="150" align="center" fixed="right">
          <template #default="scope">
            <el-button link type="primary" :icon="View" @click="openDetail(scope.row)">查看</el-button>
            <el-button v-perm="'wf:instance:terminate'" link type="danger" :icon="CircleClose"
              :disabled="scope.row.status !== 0" @click="terminate(scope.row)">终止</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination-wrap">
        <el-pagination background layout="total, sizes, prev, pager, next, jumper"
          :total="total" v-model:current-page="query.page" v-model:page-size="query.page_size"
          :page-sizes="[10, 20, 50, 100]" @change="getList" />
      </div>
    </el-card>

    <WorkflowDetail v-model="detailVisible" :instance-id="currentId" />
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Refresh, View, CircleClose } from '@element-plus/icons-vue'
import request from '@/utils/request'
import WorkflowDetail from '@/components/workflow/WorkflowDetail.vue'

const loading = ref(false)
const rows = ref([])
const total = ref(0)
const modelOptions = ref([])
const detailVisible = ref(false)
const currentId = ref(0)
const query = reactive({ page: 1, page_size: 10, model_id: '', status: '', biz_key: '' })

function statusType(status) {
  return { 0: 'warning', 1: 'success', 2: 'danger', 3: 'info' }[status] || 'info'
}
async function getList() {
  loading.value = true
  try {
    const res = await request.get('/wf/instance/list', { params: query })
    rows.value = res.data.list
    total.value = res.data.total
  } finally {
    loading.value = false
  }
}
async function loadModels() {
  const res = await request.get('/wf/model/list', { params: { page: 1, page_size: 1000 } })
  modelOptions.value = res.data.list || []
}
function handleQuery() {
  query.page = 1
  getList()
}
function resetQuery() {
  Object.assign(query, { page: 1, model_id: '', status: '', biz_key: '' })
  getList()
}
function openDetail(row) {
  currentId.value = row.id
  detailVisible.value = true
}
async function terminate(row) {
  const { value } = await ElMessageBox.prompt('请输入终止原因', '终止流程', {
    inputValue: '管理员终止',
    inputValidator: val => (val && val.trim() ? true : '请输入终止原因'),
    type: 'warning'
  })
  await request.post(`/wf/instance/terminate/${row.id}`, { comment: value })
  ElMessage.success('已终止')
  getList()
}

onMounted(async () => {
  await loadModels()
  getList()
})
</script>
