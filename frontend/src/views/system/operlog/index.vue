<template>
  <div class="app-container">
    <div class="page-header">
      <div class="page-title-wrap">
        <h2>操作日志</h2>
        <div class="sub">系统操作行为审计</div>
      </div>
    </div>
    <!-- 查询栏 -->
    <el-card shadow="never" class="search-card">
      <el-form inline @submit.prevent>
        <el-form-item label="操作人员">
          <el-input v-model="query.oper_user" placeholder="请输入操作人员" clearable style="width: 170px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="模块名称">
          <el-input v-model="query.module_name" placeholder="请输入模块名称" clearable style="width: 170px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="操作类型">
          <el-input v-model="query.oper_type" placeholder="请输入操作类型" clearable style="width: 170px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="table-card">
      <div class="toolbar">
        <el-button v-perm="'system:operlog:delete'" type="danger" plain :icon="Delete" :disabled="!selection.length" @click="handleBatchDelete">批量删除</el-button>
        <el-button v-perm="'system:operlog:delete'" type="warning" plain :icon="Brush" @click="handleClear">清空日志</el-button>
      </div>

      <el-table stripe empty-text="暂无数据" v-loading="loading" :data="list" @selection-change="onSelectionChange">
        <el-table-column type="index" label="序号" width="70" align="center" />
        <el-table-column type="selection" width="50" />
        <el-table-column label="操作人员" prop="oper_user" min-width="110" show-overflow-tooltip />
        <el-table-column label="模块名称" prop="module_name" min-width="120" show-overflow-tooltip />
        <el-table-column label="操作类型" prop="oper_type" min-width="100">
          <template #default="{ row }">{{ row.oper_type || '-' }}</template>
        </el-table-column>
        <el-table-column label="请求地址" prop="request_url" min-width="200" show-overflow-tooltip />
        <el-table-column label="耗时(ms)" prop="cost_time" width="90" align="center" />
        <el-table-column label="操作时间" prop="oper_time" width="170" />
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
    <el-dialog v-model="detailVisible" title="操作日志详情" width="700px" destroy-on-close>
      <el-descriptions :column="2" border size="small">
        <el-descriptions-item label="操作人员">{{ detail.oper_user || '-' }}</el-descriptions-item>
        <el-descriptions-item label="模块名称">{{ detail.module_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="操作类型">{{ detail.oper_type || '-' }}</el-descriptions-item>
        <el-descriptions-item label="耗时">{{ detail.cost_time }} ms</el-descriptions-item>
        <el-descriptions-item label="请求地址" :span="2">{{ detail.request_url || '-' }}</el-descriptions-item>
        <el-descriptions-item label="操作时间" :span="2">{{ detail.oper_time || '-' }}</el-descriptions-item>
      </el-descriptions>
      <div class="detail-block">
        <div class="detail-label">请求参数</div>
        <pre class="plain-pre">{{ pretty(detail.request_param) }}</pre>
      </div>
      <div class="detail-block">
        <div class="detail-label">返回结果</div>
        <pre class="plain-pre">{{ pretty(detail.response_result) }}</pre>
      </div>
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
const query = reactive({ oper_user: '', module_name: '', oper_type: '' })
const selection = ref([])

// ---------- 列表 ----------
async function fetchList() {
  loading.value = true
  try {
    const res = await request.get('/system/operlog/list', {
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
  query.oper_user = ''
  query.module_name = ''
  query.oper_type = ''
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

function pretty(text) {
  if (text === null || text === undefined || text === '') return '-'
  try {
    return JSON.stringify(JSON.parse(text), null, 2)
  } catch (e) {
    return String(text)
  }
}

// ---------- 删除/清空 ----------
async function handleBatchDelete() {
  await ElMessageBox.confirm(`确定删除选中的 ${selection.value.length} 条操作日志吗？`, '提示', { type: 'warning' })
  await request.delete('/system/operlog/delete', { data: { ids: selection.value.map(r => r.id) } })
  ElMessage.success('删除成功')
  fetchList()
}

async function handleClear() {
  await ElMessageBox.confirm('确定清空全部操作日志吗？此操作不可恢复！', '警告', { type: 'warning' })
  await request.post('/system/operlog/clear')
  ElMessage.success('清空成功')
  fetchList()
}

onMounted(fetchList)
</script>

<style scoped>
.detail-block {
  margin-top: 14px;
}

.detail-label {
  margin-bottom: 6px;
  color: #909399;
  font-size: 13px;
}
</style>
