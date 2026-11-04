<template>
  <div class="app-container">
    <div class="page-header">
      <div class="page-title-wrap">
        <h2>请求日志</h2>
        <div class="sub">只读 · 共 {{ total }} 条</div>
      </div>
    </div>
    <el-card shadow="never" class="search-card">
      <el-form :model="query" inline @submit.prevent>
        <el-form-item label="接口名称">
          <el-input v-model="query.api_name" placeholder="请输入接口名称" clearable style="width: 180px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="HTTP状态">
          <el-input v-model="query.http_code" placeholder="如 200" clearable style="width: 120px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="table-card">
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据">
        <el-table-column label="日志ID" prop="id" width="80" />
        <el-table-column label="接口ID" prop="api_id" width="90" />
        <el-table-column label="接口名称" min-width="150">
          <template #default="{ row }">{{ row.api_name || '-' }}</template>
        </el-table-column>
        <el-table-column label="请求URL" prop="request_url" min-width="220" show-overflow-tooltip />
        <el-table-column label="请求参数" prop="request_param" min-width="200" show-overflow-tooltip />
        <el-table-column label="响应" prop="response_body" min-width="200" show-overflow-tooltip />
        <el-table-column label="HTTP状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.http_code>=200 && row.http_code<300" size="small" type="success">{{ row.http_code }}</el-tag>
            <el-tag v-else-if="row.http_code>=400" size="small" type="danger">{{ row.http_code }}</el-tag>
            <el-tag v-else size="small">{{ row.http_code || '-' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="耗时(ms)" prop="cost_time" width="100" />
        <el-table-column label="错误信息" prop="error_msg" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">{{ row.error_msg || '-' }}</template>
        </el-table-column>
        <el-table-column label="请求时间" prop="request_time" width="170" />
      </el-table>
      <div class="pagination-wrap">
        <el-pagination background layout="total, sizes, prev, pager, next, jumper"
          :total="total" v-model:current-page="query.page" v-model:page-size="query.page_size"
          :page-sizes="[10, 20, 50, 100]" @change="fetchList" />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { Search, Refresh } from '@element-plus/icons-vue'
import request from '@/utils/request'

const loading = ref(false)
const rows = ref([])
const total = ref(0)

const query_orig = { page: 1, page_size: 10, api_name: '', http_code: '' }
const query = reactive({ ...query_orig })

async function fetchList() {
  loading.value = true
  try {
    const res = await request.get('/outer/log/list', { params: query })
    rows.value = res.data.list || []
    total.value = res.data.total || 0
  } finally { loading.value = false }
}
function handleSearch() { query.page = 1; fetchList() }
function handleReset() { Object.assign(query, query_orig); handleSearch() }

onMounted(fetchList)
</script>
