<template>
  <div class="app-container">
    <div class="page-header">
      <div class="page-title-wrap">
        <h2>参数配置</h2>
        <div class="sub">系统运行参数维护</div>
      </div>
    </div>
    <!-- 查询栏 -->
    <el-card shadow="never" class="search-card">
      <el-form inline @submit.prevent>
        <el-form-item label="参数名称">
          <el-input v-model="query.config_name" placeholder="请输入参数名称" clearable style="width: 180px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="参数键名">
          <el-input v-model="query.config_key" placeholder="请输入参数键名" clearable style="width: 180px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="table-card">
      <div class="toolbar">
        <el-button v-perm="'system:config:create'" type="primary" :icon="Plus" @click="openCreate">新增</el-button>
        <el-button v-perm="'system:config:delete'" type="danger" plain :icon="Delete" :disabled="!selection.length" @click="handleBatchDelete">批量删除</el-button>
      </div>

      <el-table stripe empty-text="暂无数据" v-loading="loading" :data="list" @selection-change="onSelectionChange">
        <el-table-column type="index" label="序号" width="70" align="center" />
        <el-table-column type="selection" width="50" />
        <el-table-column label="参数名称" prop="config_name" min-width="150" show-overflow-tooltip />
        <el-table-column label="参数键名" prop="config_key" min-width="160" show-overflow-tooltip />
        <el-table-column label="参数键值" prop="config_value" min-width="140" show-overflow-tooltip />
        <el-table-column label="备注" prop="remark" min-width="140" show-overflow-tooltip>
          <template #default="{ row }">{{ row.remark || '-' }}</template>
        </el-table-column>
        <el-table-column label="创建时间" prop="create_time" width="170" />
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button v-perm="'system:config:update'" link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button v-perm="'system:config:delete'" link type="danger" @click="handleDelete(row)">删除</el-button>
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

    <!-- 新增/编辑弹窗 -->
    <el-dialog v-model="formVisible" :title="form.id ? '编辑参数' : '新增参数'" width="520px" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="参数名称" prop="config_name">
          <el-input v-model.trim="form.config_name" placeholder="如 系统标题" maxlength="50" />
        </el-form-item>
        <el-form-item label="参数键名" prop="config_key">
          <el-input v-model.trim="form.config_key" placeholder="如 sys.site.title" maxlength="50" />
        </el-form-item>
        <el-form-item label="参数键值" prop="config_value">
          <el-input v-model="form.config_value" type="textarea" :rows="3" placeholder="请输入参数键值" maxlength="500" />
        </el-form-item>
        <el-form-item label="备注" prop="remark">
          <el-input v-model="form.remark" type="textarea" :rows="3" maxlength="200" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="formVisible = false">取 消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">确 定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Refresh, Plus, Delete } from '@element-plus/icons-vue'
import request from '@/utils/request'

const loading = ref(false)
const saving = ref(false)
const list = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const query = reactive({ config_name: '', config_key: '' })
const selection = ref([])

// ---------- 列表 ----------
async function fetchList() {
  loading.value = true
  try {
    const res = await request.get('/system/config/list', {
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
  query.config_name = ''
  query.config_key = ''
  handleSearch()
}

function handleSizeChange() {
  page.value = 1
  fetchList()
}

function onSelectionChange(rows) {
  selection.value = rows
}

// ---------- 新增/编辑 ----------
const formVisible = ref(false)
const formRef = ref()
const form = reactive({
  id: null,
  config_name: '',
  config_key: '',
  config_value: '',
  remark: ''
})

const rules = {
  config_name: [{ required: true, message: '请输入参数名称', trigger: 'blur' }],
  config_key: [{ required: true, message: '请输入参数键名', trigger: 'blur' }],
  config_value: [{ required: true, message: '请输入参数键值', trigger: 'blur' }]
}

function openCreate() {
  form.id = null
  form.config_name = ''
  form.config_key = ''
  form.config_value = ''
  form.remark = ''
  formVisible.value = true
}

function openEdit(row) {
  form.id = row.id
  form.config_name = row.config_name
  form.config_key = row.config_key
  form.config_value = row.config_value
  form.remark = row.remark || ''
  formVisible.value = true
}

async function handleSave() {
  await formRef.value.validate()
  saving.value = true
  try {
    const payload = {
      config_key: form.config_key,
      config_value: form.config_value,
      config_name: form.config_name,
      remark: form.remark
    }
    if (form.id) {
      await request.put(`/system/config/update/${form.id}`, payload)
      ElMessage.success('修改成功')
    } else {
      await request.post('/system/config/create', payload)
      ElMessage.success('新增成功')
    }
    formVisible.value = false
    fetchList()
  } finally {
    saving.value = false
  }
}

// ---------- 删除 ----------
async function handleDelete(row) {
  await ElMessageBox.confirm(`确定删除参数「${row.config_name}」吗？`, '提示', { type: 'warning' })
  await request.delete('/system/config/delete', { data: { ids: [row.id] } })
  ElMessage.success('删除成功')
  fetchList()
}

async function handleBatchDelete() {
  await ElMessageBox.confirm(`确定删除选中的 ${selection.value.length} 个参数吗？`, '提示', { type: 'warning' })
  await request.delete('/system/config/delete', { data: { ids: selection.value.map(r => r.id) } })
  ElMessage.success('删除成功')
  fetchList()
}

onMounted(fetchList)
</script>
