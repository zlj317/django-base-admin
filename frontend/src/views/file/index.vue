<template>
  <div class="app-container">
    <div class="page-header">
      <div class="page-title-wrap">
        <h2>附件列表</h2>
        <div class="sub">全部附件 · 共 {{ total }} 条</div>
      </div>
    </div>
    <el-card shadow="never" class="search-card">
      <el-form :model="query" inline @submit.prevent>
        <el-form-item label="文件名">
          <el-input v-model="query.original_name" placeholder="请输入文件名" clearable style="width: 180px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="业务类型">
          <el-input v-model="query.biz_type" placeholder="请输入业务类型" clearable style="width: 150px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="存储类型">
          <el-select v-model="query.storage_type" placeholder="全部" clearable style="width: 130px">
            <el-option label="本地" value="local" />
            <el-option label="OSS" value="oss" />
            <el-option label="COS" value="cos" />
            <el-option label="MinIO" value="minio" />
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
            <el-button v-perm="'file:upload'" type="primary" :icon="Upload" @click="triggerUpload">上传</el-button>
            <input ref="fileInputRef" type="file" style="display:none" @change="handleFileChange" multiple />
            <el-button v-perm="'file:delete'" type="danger" plain :icon="Delete" :disabled="!selection.length" @click="handleBatchDelete">批量删除</el-button>
          </div>
        </div>
      </template>
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据" @selection-change="onSelectionChange">
        <el-table-column type="selection" width="50" />
        <el-table-column label="编号" prop="id" width="70" />
        <el-table-column label="原始文件名" prop="original_name" min-width="180" show-overflow-tooltip />
        <el-table-column label="存储文件名" prop="file_name" min-width="180" show-overflow-tooltip />
        <el-table-column label="文件大小" width="110">
          <template #default="{ row }">{{ formatSize(row.file_size) }}</template>
        </el-table-column>
        <el-table-column label="存储类型" prop="storage_type" width="100" />
        <el-table-column label="业务类型" prop="biz_type" width="100" />
        <el-table-column label="业务ID" prop="biz_id" width="90" />
        <el-table-column label="上传用户ID" prop="upload_user_id" width="110" />
        <el-table-column label="创建时间" prop="create_time" width="170" />
        <el-table-column label="操作" width="240" fixed="right" class-name="op-col">
          <template #default="{ row }">
            <el-button link type="primary" @click="handlePreview(row)">预览</el-button>
            <el-button link type="primary" @click="handleDownload(row)">下载</el-button>
            <el-button v-perm="'file:delete'" link type="danger" @click="handleDelete(row)">删除</el-button>
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
import { Search, Refresh, Delete, Upload } from '@element-plus/icons-vue'
import request from '@/utils/request'

const loading = ref(false)
const rows = ref([])
const total = ref(0)
const selection = ref([])
const fileInputRef = ref(null)

const query_orig = { page: 1, page_size: 10, original_name: '', biz_type: '', storage_type: null }
const query = reactive({ ...query_orig })

function apiUrl(action) {
  const base = '/file'
  return {
    list: base + '/list',
    delete: base + '/delete',
    upload: base + '/upload'
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

function triggerUpload() { fileInputRef.value.click() }

async function handleFileChange(e) {
  const files = Array.from(e.target.files || [])
  if (!files.length) return
  for (const f of files) {
    const fd = new FormData()
    fd.append('file', f)
    try {
      await request.post(apiUrl('upload'), fd, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      ElMessage.success(`上传成功: ${f.name}`)
    } catch (err) {
      ElMessage.error(`上传失败: ${f.name}`)
    }
  }
  e.target.value = ''
  fetchList()
}

async function handlePreview(row) {
  try {
    const res = await request.get(`/file/preview_url/${row.id}`)
    if (res.data && res.data.url) {
      window.open(res.data.url, '_blank')
    } else {
      ElMessage.warning('暂无预览地址')
    }
  } catch (e) { /* 错误提示由请求拦截器统一处理 */ }
}

async function handleDownload(row) {
  const resp = await request.get(`/file/download/${row.id}`, { responseType: 'blob' })
  const url = window.URL.createObjectURL(new Blob([resp.data]))
  const a = document.createElement('a')
  a.href = url
  a.download = row.original_name || row.file_name || 'download'
  document.body.appendChild(a)
  a.click()
  a.remove()
  window.URL.revokeObjectURL(url)
}

function onSelectionChange(r) { selection.value = r }

async function handleDelete(row) {
  await ElMessageBox.confirm('确定删除该文件？', '提示', { type: 'warning' })
  await request.delete(apiUrl('delete'), { data: { ids: [row.id] } })
  ElMessage.success('删除成功')
  fetchList()
}

async function handleBatchDelete() {
  await ElMessageBox.confirm(`确定删除选中的 ${selection.value.length} 个文件？`, '提示', { type: 'warning' })
  await request.delete(apiUrl('delete'), { data: { ids: selection.value.map(r => r.id) } })
  ElMessage.success('批量删除成功')
  fetchList()
}

onMounted(fetchList)
</script>
