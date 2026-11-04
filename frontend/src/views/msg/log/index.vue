<template>
  <div class="app-container">
    <div class="page-header">
      <div class="page-title-wrap">
        <h2>推送记录</h2>
        <div class="sub">只读 · 共 {{ total }} 条</div>
      </div>
    </div>
    <el-card shadow="never" class="search-card">
      <el-form :model="query" inline @submit.prevent>
        <el-form-item label="接收人ID">
          <el-input v-model="query.receiver_id" placeholder="请输入接收人ID" clearable style="width: 160px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="推送状态">
          <el-select v-model="query.push_status" placeholder="全部" clearable style="width: 130px">
            <el-option label="待推送" :value="0" />
            <el-option label="成功" :value="1" />
            <el-option label="失败" :value="2" />
          </el-select>
        </el-form-item>
        <el-form-item label="渠道">
          <el-select v-model="query.channel" placeholder="全部" clearable style="width: 130px">
            <el-option label="站内信" value="site" />
            <el-option label="短信" value="sms" />
            <el-option label="邮件" value="email" />
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
        <el-table-column label="记录ID" prop="record_id" min-width="160" show-overflow-tooltip />
        <el-table-column label="接收人ID" prop="receiver_id" width="110" />
        <el-table-column label="渠道" prop="channel" width="100" />
        <el-table-column label="推送状态" width="110" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.push_status===0" size="small" type="info">待推送</el-tag>
            <el-tag v-else-if="row.push_status===1" size="small" type="success">成功</el-tag>
            <el-tag v-else-if="row.push_status===2" size="small" type="danger">失败</el-tag>
            <span v-else>{{ row.push_status }}</span>
          </template>
        </el-table-column>
        <el-table-column label="错误信息" prop="error_msg" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">{{ row.error_msg || '-' }}</template>
        </el-table-column>
        <el-table-column label="重试次数" prop="retry_count" width="90" />
        <el-table-column label="推送时间" prop="push_time" width="170" />
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

const query_orig = { page: 1, page_size: 10, receiver_id: '', push_status: null, channel: null }
const query = reactive({ ...query_orig })

async function fetchList() {
  loading.value = true
  try {
    const res = await request.get('/msg/push_log/list', { params: query })
    rows.value = res.data.list || []
    total.value = res.data.total || 0
  } finally { loading.value = false }
}
function handleSearch() { query.page = 1; fetchList() }
function handleReset() { Object.assign(query, query_orig); handleSearch() }

onMounted(fetchList)
</script>
