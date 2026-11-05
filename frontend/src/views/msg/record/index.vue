<template>
  <div class="app-container">
    <div class="page-header">
      <div class="page-title-wrap">
        <h2>站内消息</h2>
        <div class="sub">消息记录 · 共 {{ total }} 条</div>
      </div>
    </div>
    <el-card shadow="never" class="search-card">
      <el-form :model="query" inline @submit.prevent>
        <el-form-item label="接收人ID">
          <el-input v-model="query.receiver_id" placeholder="请输入接收人ID" clearable style="width: 160px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="消息类型">
          <el-select v-model="query.msg_type" placeholder="全部" clearable style="width: 130px">
            <el-option label="待办" value="todo" />
            <el-option label="已办" value="done" />
            <el-option label="抄送" value="cc" />
            <el-option label="系统" value="system" />
            <el-option label="报表" value="report" />
            <el-option label="告警" value="alarm" />
            <el-option label="通知" value="notice" />
          </el-select>
        </el-form-item>
        <el-form-item label="是否已读">
          <el-select v-model="query.is_read" placeholder="全部" clearable style="width: 110px">
            <el-option label="已读" :value="1" />
            <el-option label="未读" :value="0" />
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
            <el-button v-perm="'msg:delete'" type="danger" plain :icon="Delete" :disabled="!selection.length" @click="handleBatchDelete">批量删除</el-button>
          </div>
        </div>
      </template>
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据" @selection-change="onSelectionChange">
        <el-table-column type="index" label="序号" width="70" align="center" />
        <el-table-column type="selection" width="50" />
        <el-table-column label="消息类型" prop="msg_type" width="100" />
        <el-table-column label="标题" prop="title" min-width="180" show-overflow-tooltip />
        <el-table-column label="内容" prop="content" min-width="260" show-overflow-tooltip />
        <el-table-column label="接收人ID" prop="receiver_id" width="110" />
        <el-table-column label="跳转链接" prop="link_url" min-width="180" show-overflow-tooltip />
        <el-table-column label="是否已读" width="90" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.is_read" size="small">已读</el-tag>
            <el-tag v-else size="small" type="danger">未读</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="阅读时间" prop="read_time" width="170">
          <template #default="{ row }">{{ row.read_time || '-' }}</template>
        </el-table-column>
        <el-table-column label="创建时间" prop="create_time" width="170" />
        <el-table-column label="操作" width="200" fixed="right" class-name="op-col">
          <template #default="{ row }">
            <el-button v-if="!row.is_read" v-perm="'msg:update'" link type="primary" @click="handleMarkRead(row)">标记已读</el-button>
            <el-button v-perm="'msg:delete'" link type="danger" @click="handleDelete(row)">删除</el-button>
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
import { Search, Refresh, Delete } from '@element-plus/icons-vue'
import request from '@/utils/request'

const loading = ref(false)
const rows = ref([])
const total = ref(0)
const selection = ref([])

const query_orig = { page: 1, page_size: 10, receiver_id: '', msg_type: null, is_read: null }
const query = reactive({ ...query_orig })

function apiUrl(action) {
  const base = '/msg/record'
  return {
    list: base + '/list',
    delete: base + '/delete',
    mark_read: base + '/read'
  }[action]
}

async function fetchList() {
  loading.value = true
  try {
    const res = await request.get(apiUrl('list'), { params: query })
    rows.value = res.data.list || []
    total.value = res.data.total || 0
  } finally { loading.value = false }
}
function handleSearch() { query.page = 1; fetchList() }
function handleReset() { Object.assign(query, query_orig); handleSearch() }
function onSelectionChange(r) { selection.value = r }

async function handleMarkRead(row) {
  await request.post(`${apiUrl('mark_read')}/${row.id}`)
  ElMessage.success('已标记为已读'); fetchList()
}

async function handleDelete(row) {
  await ElMessageBox.confirm('确定删除该消息？', '提示', { type: 'warning' })
  await request.delete(apiUrl('delete'), { data: { ids: [row.id] } })
  ElMessage.success('删除成功'); fetchList()
}

async function handleBatchDelete() {
  await ElMessageBox.confirm(`确定删除选中的 ${selection.value.length} 条消息？`, '提示', { type: 'warning' })
  await request.delete(apiUrl('delete'), { data: { ids: selection.value.map(r => r.id) } })
  ElMessage.success('批量删除成功'); fetchList()
}

onMounted(fetchList)
</script>
