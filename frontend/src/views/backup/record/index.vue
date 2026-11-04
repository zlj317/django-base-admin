<template>
  <div class="app-container">
    <div class="page-header">
      <div class="page-title-wrap">
        <h2>数据备份管理</h2>
        <div class="sub">数据库备份记录 · 共 {{ total }} 条</div>
      </div>
    </div>

    <el-card shadow="never" class="search-card">
      <el-form :model="query" inline @submit.prevent>
        <el-form-item label="备份名称">
          <el-input v-model="query.backup_name" placeholder="请输入备份名称" clearable style="width: 170px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="备份类型">
          <el-select v-model="query.backup_type" placeholder="全部" clearable style="width: 110px">
            <el-option label="全量" value="full" />
            <el-option label="增量" value="incremental" />
            <el-option label="手动" value="manual" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="query.backup_status" placeholder="全部" clearable style="width: 120px">
            <el-option label="备份中" :value="0" />
            <el-option label="成功" :value="1" />
            <el-option label="失败" :value="2" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="table-card">
      <template #header>
        <div class="card-header">
          <div class="card-actions">
            <el-button type="primary" :icon="Plus" @click="handleManualBackup">手动备份</el-button>
          </div>
        </div>
      </template>
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据" @selection-change="onSelectionChange">
        <el-table-column type="index" label="序号" width="70" align="center" />
        <el-table-column type="selection" width="50" />
        <el-table-column label="备份名称" prop="backup_name" min-width="180" show-overflow-tooltip />
        <el-table-column label="备份类型" width="90">
          <template #default="{ row }">
            <el-tag v-if="row.backup_type==='full'" size="small">全量</el-tag>
            <el-tag v-else-if="row.backup_type==='incremental'" size="small" type="success">增量</el-tag>
            <el-tag v-else-if="row.backup_type==='manual'" size="small" type="warning">手动</el-tag>
            <span v-else>{{ row.backup_type }}</span>
          </template>
        </el-table-column>
        <el-table-column label="数据库" prop="db_name" width="130" />
        <el-table-column label="文件大小" width="100">
          <template #default="{ row }">{{ formatSize(row.file_size) }}</template>
        </el-table-column>
        <el-table-column label="加密" width="70" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.encrypt_flag===1" size="small" type="warning">是</el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.backup_status===0" size="small">备份中</el-tag>
            <el-tag v-else-if="row.backup_status===1" size="small" type="success">成功</el-tag>
            <el-tag v-else-if="row.backup_status===2" size="small" type="danger">失败</el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="备份时间" prop="backup_time" width="170" />
        <el-table-column label="耗时(秒)" prop="cost_time" width="90">
          <template #default="{ row }">{{ row.cost_time ?? '-' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right" class-name="op-col">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleDownload(row)">下载</el-button>
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
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
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Refresh, Plus } from '@element-plus/icons-vue'
import request from '@/utils/request'

const loading = ref(false)
const rows = ref([])
const total = ref(0)
const selection = ref([])

const query_orig = { page: 1, page_size: 10, backup_name: '', backup_type: '', backup_status: null }
const query = reactive({ ...query_orig })

const apiBase = '/backup/record'

function formatSize(bytes) {
  if (!bytes) return '-'
  const units = ['B', 'KB', 'MB', 'GB']
  let i = 0
  let val = Number(bytes)
  while (val >= 1024 && i < units.length - 1) { val /= 1024; i++ }
  return val.toFixed(1) + ' ' + units[i]
}

async function fetchList() {
  loading.value = true
  try {
    const res = await request.get(apiBase + '/list', { params: query })
    rows.value = res.data.list || []
    total.value = res.data.total || 0
  } finally { loading.value = false }
}

function handleSearch() { query.page = 1; fetchList() }
function handleReset() { Object.assign(query, query_orig); handleSearch() }
function onSelectionChange(r) { selection.value = r }

async function handleManualBackup() {
  await ElMessageBox.confirm('确定立即执行手动备份？', '提示', { type: 'warning' })
  await request.post(apiBase + '/manual')
  ElMessage.success('备份任务已提交'); fetchList()
}

async function handleDownload(row) {
  try {
    const res = await request.get(`${apiBase}/download/${row.id}`, { responseType: 'blob' })
    const url = URL.createObjectURL(res.data)
    const a = document.createElement('a')
    a.href = url; a.download = row.backup_name || 'backup'
    a.click(); URL.revokeObjectURL(url)
  } catch (e) { /* handled */ }
}

async function handleDelete(row) {
  await ElMessageBox.confirm('确定删除该备份记录？', '提示', { type: 'warning' })
  await request.delete(apiBase + '/delete', { data: { ids: [row.id] } })
  ElMessage.success('删除成功'); fetchList()
}

onMounted(fetchList)
</script>
