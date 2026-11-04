<template>
  <div class="app-container">
    <div class="page-header">
      <div class="page-title-wrap">
        <h2>登录尝试记录</h2>
        <div class="sub">登录安全日志 · 共 {{ total }} 条（只读）</div>
      </div>
    </div>

    <el-card shadow="never" class="search-card">
      <el-form :model="query" inline @submit.prevent>
        <el-form-item label="用户名">
          <el-input v-model="query.username" placeholder="请输入用户名" clearable style="width: 170px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="结果">
          <el-select v-model="query.success_flag" placeholder="全部" clearable style="width: 110px">
            <el-option label="成功" :value="1" />
            <el-option label="失败" :value="0" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="table-card">
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据">
        <el-table-column type="index" label="序号" width="70" align="center" />
        <el-table-column label="用户名" prop="username" min-width="140" show-overflow-tooltip />
        <el-table-column label="IP地址" prop="ip" width="140" />
        <el-table-column label="登录时间" prop="attempt_time" width="170" />
        <el-table-column label="结果" width="90" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.success_flag===1 || row.success_flag==='1'" size="small" type="success">成功</el-tag>
            <el-tag v-else size="small" type="danger">失败</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="User-Agent" prop="user_agent" min-width="200" show-overflow-tooltip />
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

const query_orig = { page: 1, page_size: 10, username: '', success_flag: null }
const query = reactive({ ...query_orig })

async function fetchList() {
  loading.value = true
  try {
    const res = await request.get('/sec/login_attempt/list', { params: query })
    rows.value = res.data.list || []
    total.value = res.data.total || 0
  } finally { loading.value = false }
}

function handleSearch() { query.page = 1; fetchList() }
function handleReset() { Object.assign(query, query_orig); handleSearch() }

onMounted(fetchList)
</script>
