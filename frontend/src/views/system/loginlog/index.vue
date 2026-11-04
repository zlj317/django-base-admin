<template>
  <div class="app-container">
    <div class="page-header">
      <div class="page-title-wrap">
        <h2>登录日志</h2>
        <div class="sub">账号登录记录审计</div>
      </div>
    </div>
    <!-- 查询栏 -->
    <el-card shadow="never" class="search-card">
      <el-form inline @submit.prevent>
        <el-form-item label="用户名">
          <el-input v-model="query.username" placeholder="请输入用户名" clearable style="width: 180px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="登录状态">
          <el-select v-model="query.status" placeholder="全部" clearable style="width: 140px">
            <el-option label="成功" :value="0" />
            <el-option label="失败" :value="1" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="table-card">
      <div class="toolbar">
        <el-button v-perm="'system:loginlog:delete'" type="danger" plain :icon="Delete" :disabled="!selection.length" @click="handleBatchDelete">批量删除</el-button>
        <el-button v-perm="'system:loginlog:delete'" type="warning" plain :icon="Brush" @click="handleClear">清空日志</el-button>
      </div>

      <el-table stripe empty-text="暂无数据" v-loading="loading" :data="list" @selection-change="onSelectionChange">
        <el-table-column type="index" label="序号" width="70" align="center" />
        <el-table-column type="selection" width="50" />
        <el-table-column label="用户名" prop="username" min-width="110" show-overflow-tooltip />
        <el-table-column label="登录IP" prop="ip" min-width="130" show-overflow-tooltip>
          <template #default="{ row }">{{ row.ip || '-' }}</template>
        </el-table-column>
        <el-table-column label="浏览器" prop="browser" min-width="130" show-overflow-tooltip>
          <template #default="{ row }">{{ row.browser || '-' }}</template>
        </el-table-column>
        <el-table-column label="登录状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 0 ? 'success' : 'danger'" size="small">
              {{ row.status === 0 ? '成功' : '失败' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="提示消息" prop="msg" min-width="160" show-overflow-tooltip />
        <el-table-column label="登录时间" prop="login_time" width="170" />
        <el-table-column label="操作" width="80" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDetail(row)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="fetchList"
        />
      </div>
    </el-card>

    <!-- 详情弹窗 -->
    <el-dialog v-model="detailVisible" title="登录日志详情" width="520px" destroy-on-close>
      <el-descriptions :column="1" border size="small">
        <el-descriptions-item label="用户名">{{ detail.username || '-' }}</el-descriptions-item>
        <el-descriptions-item label="登录IP">{{ detail.ip || '-' }}</el-descriptions-item>
        <el-descriptions-item label="浏览器">{{ detail.browser || '-' }}</el-descriptions-item>
        <el-descriptions-item label="登录状态">{{ detail.status === 0 ? '成功' : '失败' }}</el-descriptions-item>
        <el-descriptions-item label="提示消息">{{ detail.msg || '-' }}</el-descriptions-item>
        <el-descriptions-item label="登录时间">{{ detail.login_time || '-' }}</el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Refresh, Delete, Brush } from '@element-plus/icons-vue'
import request from '@/utils/request'

const loading = ref(false)
const list = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const query = reactive({ username: '', status: null })
const selection = ref([])

// ---------- 列表 ----------
async function fetchList() {
  loading.value = true
  try {
    const res = await request.get('/system/loginlog/list', {
      params: { page: page.value, page_size: pageSize.value, ...query }
    })
    list.value = res.data.list || []
    total.value = res.data.total || 0
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  page.value = 1
  fetchList()
}

function handleReset() {
  query.username = ''
  query.status = null
  handleSearch()
}

function handleSizeChange() {
  page.value = 1
  fetchList()
}

function onSelectionChange(rows) {
  selection.value = rows
}

// ---------- 详情 ----------
const detailVisible = ref(false)
const detail = ref({})

function openDetail(row) {
  detail.value = row
  detailVisible.value = true
}

// ---------- 删除/清空 ----------
async function handleBatchDelete() {
  await ElMessageBox.confirm(`确定删除选中的 ${selection.value.length} 条登录日志吗？`, '提示', { type: 'warning' })
  await request.delete('/system/loginlog/delete', { data: { ids: selection.value.map(r => r.id) } })
  ElMessage.success('删除成功')
  fetchList()
}

async function handleClear() {
  await ElMessageBox.confirm('确定清空全部登录日志吗？此操作不可恢复！', '警告', { type: 'warning' })
  await request.post('/system/loginlog/clear')
  ElMessage.success('清空成功')
  fetchList()
}

onMounted(fetchList)
</script>
