<template>
  <div class="app-container">
    <div class="page-header">
      <div class="page-title-wrap">
        <h2>代码生成</h2>
        <div class="sub">数据表导入与代码生成配置</div>
      </div>
    </div>
    <!-- 查询栏 -->
    <el-card shadow="never" class="search-card">
      <el-form inline @submit.prevent>
        <el-form-item label="表名称">
          <el-input v-model="query.table_name" placeholder="请输入表名称" clearable style="width: 200px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="table-card">
      <div class="toolbar">
        <el-button v-perm="'gen:table:import'" type="primary" :icon="Upload" @click="openImport">导入数据表</el-button>
        <el-button v-perm="'gen:table:delete'" type="danger" plain :icon="Delete" :disabled="!selection.length" @click="handleBatchDelete">批量删除</el-button>
      </div>

      <el-table stripe empty-text="暂无数据" v-loading="loading" :data="list" @selection-change="onSelectionChange">
        <el-table-column type="selection" width="50" />
        <el-table-column label="表名" prop="table_name" min-width="160" show-overflow-tooltip />
        <el-table-column label="表注释" prop="table_comment" min-width="130" show-overflow-tooltip>
          <template #default="{ row }">{{ row.table_comment || '-' }}</template>
        </el-table-column>
        <el-table-column label="模块名" prop="module_name" min-width="110" show-overflow-tooltip>
          <template #default="{ row }">{{ row.module_name || '-' }}</template>
        </el-table-column>
        <el-table-column label="模块中文" prop="module_comment" min-width="110" show-overflow-tooltip>
          <template #default="{ row }">{{ row.module_comment || '-' }}</template>
        </el-table-column>
        <el-table-column label="路由前缀" prop="url_prefix" min-width="120" show-overflow-tooltip>
          <template #default="{ row }">{{ row.url_prefix || '-' }}</template>
        </el-table-column>
        <el-table-column label="字段数" prop="column_count" width="80" align="center" />
        <el-table-column label="创建时间" prop="create_time" width="170" />
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button v-perm="'gen:table:update'" link type="primary" @click="goEdit(row)">配置</el-button>
            <el-button v-perm="'gen:table:preview'" link type="primary" @click="previewRef.open(row.id)">预览</el-button>
            <el-button v-perm="'gen:table:download'" link type="success" @click="handleDownload(row)">下载</el-button>
            <el-button v-perm="'gen:table:delete'" link type="danger" @click="handleDelete(row)">删除</el-button>
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

    <!-- 导入数据表弹窗 -->
    <el-dialog v-model="importVisible" title="导入数据表" width="760px" destroy-on-close>
      <el-form inline @submit.prevent>
        <el-form-item label="表名称">
          <el-input v-model="importQuery.table_name" placeholder="请输入表名称" clearable style="width: 200px" @keyup.enter="fetchImportTables" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="fetchImportTables">查询</el-button>
        </el-form-item>
      </el-form>

      <el-table
        ref="importTableRef"
        v-loading="importLoading"
        :data="importList"
        max-height="380"
        @selection-change="onImportSelectionChange"
      >
        <el-table-column type="selection" width="50" :selectable="row => !row.imported" />
        <el-table-column label="表名" prop="table_name" min-width="170" show-overflow-tooltip />
        <el-table-column label="表注释" prop="table_comment" min-width="150" show-overflow-tooltip>
          <template #default="{ row }">{{ row.table_comment || '-' }}</template>
        </el-table-column>
        <el-table-column label="创建时间" prop="create_time" width="170" />
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="row.imported ? 'info' : 'success'" size="small">
              {{ row.imported ? '已导入' : '未导入' }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="importPage"
          v-model:page-size="importPageSize"
          :total="importTotal"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          @size-change="importPage = 1; fetchImportTables()"
          @current-change="fetchImportTables"
        />
      </div>

      <template #footer>
        <el-button @click="importVisible = false">取 消</el-button>
        <el-button type="primary" :loading="importing" :disabled="!importSelection.length" @click="handleImport">
          导入（{{ importSelection.length }}）
        </el-button>
      </template>
    </el-dialog>

    <!-- 代码预览弹窗 -->
    <CodePreviewDialog ref="previewRef" />
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Refresh, Upload, Delete } from '@element-plus/icons-vue'
import request from '@/utils/request'
import { saveBlob } from '@/utils/download'
import CodePreviewDialog from '@/components/CodePreviewDialog.vue'

const router = useRouter()

const loading = ref(false)
const list = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const query = reactive({ table_name: '' })
const selection = ref([])
const previewRef = ref()

// ---------- 列表 ----------
async function fetchList() {
  loading.value = true
  try {
    const res = await request.get('/gen/table/list', {
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
  query.table_name = ''
  handleSearch()
}

function handleSizeChange() {
  page.value = 1
  fetchList()
}

function onSelectionChange(rows) {
  selection.value = rows
}

function goEdit(row) {
  router.push(`/gen/edit/${row.id}`)
}

// ---------- 导入数据表 ----------
const importVisible = ref(false)
const importLoading = ref(false)
const importing = ref(false)
const importList = ref([])
const importTotal = ref(0)
const importPage = ref(1)
const importPageSize = ref(10)
const importQuery = reactive({ table_name: '' })
const importSelection = ref([])
const importTableRef = ref()

function openImport() {
  importQuery.table_name = ''
  importPage.value = 1
  importSelection.value = []
  importVisible.value = true
  fetchImportTables()
}

async function fetchImportTables() {
  importLoading.value = true
  try {
    const res = await request.get('/gen/db/tables', {
      params: { page: importPage.value, page_size: importPageSize.value, table_name: importQuery.table_name }
    })
    importList.value = res.data.list || []
    importTotal.value = res.data.total || 0
    // 保留已勾选且仍在当前页的数据
    nextTickSelection()
  } finally {
    importLoading.value = false
  }
}

function nextTickSelection() {
  Promise.resolve().then(() => {
    if (!importTableRef.value) return
    importList.value.forEach(row => {
      if (importSelection.value.some(item => item.table_name === row.table_name)) {
        importTableRef.value.toggleRowSelection(row, true)
      }
    })
  })
}

function onImportSelectionChange(rows) {
  importSelection.value = rows
}

async function handleImport() {
  const tables = importSelection.value.map(r => r.table_name)
  if (!tables.length) {
    ElMessage.warning('请选择要导入的数据表')
    return
  }
  importing.value = true
  try {
    await request.post('/gen/db/import', { tables })
    ElMessage.success(`成功导入 ${tables.length} 张表`)
    importVisible.value = false
    fetchList()
  } finally {
    importing.value = false
  }
}

// ---------- 下载 ----------
async function handleDownload(row) {
  const res = await request.get(`/gen/table/${row.id}/download`, { responseType: 'blob', timeout: 120000 })
  saveBlob(res.data, `${row.module_name || row.class_name || row.table_name}.zip`)
  ElMessage.success('下载成功')
}

// ---------- 删除 ----------
async function handleDelete(row) {
  await ElMessageBox.confirm(`确定删除表「${row.table_name}」的生成配置吗？`, '提示', { type: 'warning' })
  await request.delete('/gen/table/delete', { data: { ids: [row.id] } })
  ElMessage.success('删除成功')
  fetchList()
}

async function handleBatchDelete() {
  await ElMessageBox.confirm(`确定删除选中的 ${selection.value.length} 张表的生成配置吗？`, '提示', { type: 'warning' })
  await request.delete('/gen/table/delete', { data: { ids: selection.value.map(r => r.id) } })
  ElMessage.success('删除成功')
  fetchList()
}

onMounted(fetchList)
</script>
