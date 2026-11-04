<template>
  <div class="app-container">
    <div class="page-header">
      <div class="page-title-wrap">
        <h2>回收站</h2>
        <div class="sub">已删除文件 · 共 {{ total }} 条</div>
      </div>
    </div>
    <el-card shadow="never" class="search-card">
      <el-form :model="query" inline @submit.prevent>
        <el-form-item label="文件名">
          <el-input v-model="query.original_name" placeholder="请输入文件名" clearable style="width: 180px" @keyup.enter="handleSearch" />
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
            <el-button v-perm="'file:recycle:restore'" type="success" plain :icon="RefreshRight" :disabled="!selection.length" @click="handleBatchRestore">批量恢复</el-button>
            <el-button v-perm="'file:recycle:delete'" type="danger" plain :icon="Delete" :disabled="!selection.length" @click="handleBatchHardDelete">批量彻底删除</el-button>
          </div>
        </div>
      </template>
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据" @selection-change="onSelectionChange">
        <el-table-column type="selection" width="50" />
        <el-table-column label="编号" prop="id" width="70" />
        <el-table-column label="原始文件名" prop="original_name" min-width="180" show-overflow-tooltip />
        <el-table-column label="存储文件名" prop="file_name" min-width="180" show-overflow-tooltip />
        <el-table-column label="大小" width="110">
          <template #default="{ row }">{{ formatSize(row.file_size) }}</template>
        </el-table-column>
        <el-table-column label="存储类型" prop="storage_type" width="100" />
        <el-table-column label="业务类型" prop="biz_type" width="100" />
        <el-table-column label="删除时间" prop="delete_time" width="170" />
        <el-table-column label="操作" width="200" fixed="right" class-name="op-col">
          <template #default="{ row }">
            <el-button v-perm="'file:recycle:restore'" link type="success" @click="handleRestore(row)">恢复</el-button>
            <el-button v-perm="'file:recycle:delete'" link type="danger" @click="handleHardDelete(row)">彻底删除</el-button>
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
import { Search, Refresh, Delete, RefreshRight } from '@element-plus/icons-vue'
import request from '@/utils/request'

const loading = ref(false)
const rows = ref([])
const total = ref(0)
const selection = ref([])

const query_orig = { page: 1, page_size: 10, original_name: '' }
const query = reactive({ ...query_orig })

function apiUrl(action) {
  const base = '/file/recycle'
  return {
    list: base + '/list',
    restore: base + '/restore',
    hard_delete: base + '/hard_delete'
  }[action]
}

function formatSize(bytes) {
  if (!bytes && bytes !== 0) return '-'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB'
  if (bytes < 1024 * 1024 * 1024) return (bytes / 1024 / 1024).toFixed(2) + ' MB'
  return (bytes / 1024 / 1024 / 1024).toFixed(2) + ' GB'
}

async function fetchList() {
  loading.value = true
  try {
    const res = await request.get(apiUrl('list'), { params: query })
    rows.value = res.data.list || []
    total.value = res.data.total || 0
  } finally {
    loading.value = false
  }
}

function handleSearch() { query.page = 1; fetchList() }
function handleReset() { Object.assign(query, query_orig); handleSearch() }
function onSelectionChange(r) { selection.value = r }

async function handleRestore(row) {
  await ElMessageBox.confirm('确定恢复该文件？', '提示', { type: 'warning' })
  await request.post(`${apiUrl('restore')}/${row.id}`)
  ElMessage.success('恢复成功')
  fetchList()
}

async function handleBatchRestore() {
  await ElMessageBox.confirm(`确定恢复选中的 ${selection.value.length} 个文件？`, '提示', { type: 'warning' })
  for (const r of selection.value) {
    await request.post(`${apiUrl('restore')}/${r.id}`)
  }
  ElMessage.success('批量恢复成功')
  fetchList()
}

async function handleHardDelete(row) {
  await ElMessageBox.confirm('彻底删除不可恢复，确定执行？', '提示', { type: 'error' })
  await request.delete(`${apiUrl('hard_delete')}/${row.id}`)
  ElMessage.success('已彻底删除')
  fetchList()
}

async function handleBatchHardDelete() {
  await ElMessageBox.confirm(`彻底删除 ${selection.value.length} 个文件，不可恢复，确定执行？`, '提示', { type: 'error' })
  for (const r of selection.value) {
    await request.delete(`${apiUrl('hard_delete')}/${r.id}`)
  }
  ElMessage.success('已彻底删除')
  fetchList()
}

onMounted(fetchList)
</script>
