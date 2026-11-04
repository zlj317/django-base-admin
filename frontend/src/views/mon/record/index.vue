<template>
  <div class="app-container">
    <div class="page-header">
      <div class="page-title-wrap">
        <h2>告警记录</h2>
        <div class="sub">告警历史 · 共 {{ total }} 条（只读）</div>
      </div>
    </div>

    <el-card shadow="never" class="search-card">
      <el-form :model="query" inline @submit.prevent>
        <el-form-item label="规则名称">
          <el-select v-model="query.rule_id" placeholder="全部" clearable style="width: 200px">
            <el-option v-for="r in ruleOptions" :key="r.id" :label="r.rule_name" :value="r.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="告警级别">
          <el-select v-model="query.alarm_level" placeholder="全部" clearable style="width: 110px">
            <el-option label="提示" value="info" />
            <el-option label="警告" value="warning" />
            <el-option label="严重" value="critical" />
          </el-select>
        </el-form-item>
        <el-form-item label="处理状态">
          <el-select v-model="query.handle_status" placeholder="全部" clearable style="width: 110px">
            <el-option label="待处理" :value="0" />
            <el-option label="已处理" :value="1" />
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
        <el-table-column label="规则名称" min-width="160">
          <template #default="{ row }">{{ getRuleName(row.rule_id) }}</template>
        </el-table-column>
        <el-table-column label="告警级别" width="100" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.alarm_level==='info'" size="small">提示</el-tag>
            <el-tag v-else-if="row.alarm_level==='warning'" size="small" type="warning">警告</el-tag>
            <el-tag v-else-if="row.alarm_level==='critical'" size="small" type="danger">严重</el-tag>
            <span v-else>{{ row.alarm_level }}</span>
          </template>
        </el-table-column>
        <el-table-column label="告警内容" prop="alarm_content" min-width="220" show-overflow-tooltip />
        <el-table-column label="告警时间" prop="alarm_time" width="170" />
        <el-table-column label="处理状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.handle_status===1" size="small" type="success">已处理</el-tag>
            <el-tag v-else size="small" type="warning">待处理</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="处理人" prop="handler_id" width="100">
          <template #default="{ row }">{{ row.handler_id || '-' }}</template>
        </el-table-column>
        <el-table-column label="处理时间" prop="handle_time" width="170">
          <template #default="{ row }">{{ row.handle_time || '-' }}</template>
        </el-table-column>
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
const ruleOptions = ref([])

const query_orig = { page: 1, page_size: 10, rule_id: null, alarm_level: '', handle_status: null }
const query = reactive({ ...query_orig })

function getRuleName(id) {
  if (!id) return '-'
  const r = ruleOptions.value.find(x => x.id === id)
  return r ? r.rule_name : id
}

async function loadRules() {
  try {
    const res = await request.get('/mon/rule/list', { params: { page: 1, page_size: 200 } })
    ruleOptions.value = res.data.list || []
  } catch (e) { /* ignore */ }
}

async function fetchList() {
  loading.value = true
  try {
    const res = await request.get('/mon/record/list', { params: query })
    rows.value = res.data.list || []
    total.value = res.data.total || 0
  } finally { loading.value = false }
}

function handleSearch() { query.page = 1; fetchList() }
function handleReset() { Object.assign(query, query_orig); handleSearch() }

onMounted(() => { loadRules(); fetchList() })
</script>
