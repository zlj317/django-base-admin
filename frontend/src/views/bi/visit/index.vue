<template>
  <div class="app-container">
    <div class="page-header">
      <div class="page-title-wrap">
        <h2>访问记录</h2>
        <div class="sub">只读 · 共 {{ total }} 条</div>
      </div>
    </div>
    <el-card shadow="never" class="search-card">
      <el-form :model="query" inline @submit.prevent>
        <el-form-item label="大屏名称">
          <el-input v-model="query.screen_name" placeholder="请输入大屏名称" clearable style="width: 180px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="访客ID">
          <el-input v-model="query.visitor_user_id" placeholder="请输入访客ID" clearable style="width: 160px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="table-card">
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据">
        <el-table-column label="记录ID" prop="id" width="80" />
        <el-table-column label="大屏ID" prop="screen_id" width="90" />
        <el-table-column label="大屏名称" min-width="180">
          <template #default="{ row }">{{ row.screen_name || '-' }}</template>
        </el-table-column>
        <el-table-column label="访客用户ID" prop="visitor_user_id" width="120" />
        <el-table-column label="访客IP" prop="visit_ip" min-width="160" show-overflow-tooltip />
        <el-table-column label="访问时间" prop="visit_time" width="170" />
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

const query_orig = { page: 1, page_size: 10, screen_name: '', visitor_user_id: '' }
const query = reactive({ ...query_orig })

async function fetchList() {
  loading.value = true
  try {
    const res = await request.get('/bi/visit/list', { params: query })
    rows.value = res.data.list || []
    total.value = res.data.total || 0
  } finally { loading.value = false }
}
function handleSearch() { query.page = 1; fetchList() }
function handleReset() { Object.assign(query, query_orig); handleSearch() }

onMounted(fetchList)
</script>
