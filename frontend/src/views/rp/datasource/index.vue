<template>
  <div class="app-container">
    <div class="page-header">
      <div class="page-title-wrap">
        <h2>数据源</h2>
        <div class="sub">数据源管理 · 共 {{ total }} 条</div>
      </div>
    </div>
    <el-card shadow="never" class="search-card">
      <el-form :model="query" inline @submit.prevent>
        <el-form-item label="数据源名称">
          <el-input v-model="query.ds_name" placeholder="请输入名称" clearable style="width: 170px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="query.ds_type" placeholder="全部" clearable style="width: 120px">
            <el-option label="MySQL" value="mysql" />
            <el-option label="API" value="api" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="query.status" placeholder="全部" clearable style="width: 110px">
            <el-option label="启用" :value="1" />
            <el-option label="停用" :value="0" />
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
            <el-button v-perm="'rp:datasource:create'" type="primary" :icon="Plus" @click="openCreate">新增</el-button>
            <el-button v-perm="'rp:datasource:delete'" type="danger" plain :icon="Delete" :disabled="!selection.length" @click="handleBatchDelete">批量删除</el-button>
          </div>
        </div>
      </template>
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据" @selection-change="onSelectionChange">
        <el-table-column type="selection" width="50" />
        <el-table-column label="编号" prop="id" width="70" />
        <el-table-column label="数据源名称" prop="ds_name" min-width="180" show-overflow-tooltip />
        <el-table-column label="类型" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.ds_type==='mysql'" size="small">MySQL</el-tag>
            <el-tag v-else-if="row.ds_type==='api'" size="small" type="success">API</el-tag>
            <span v-else>{{ row.ds_type }}</span>
          </template>
        </el-table-column>
        <el-table-column label="配置" prop="ds_config" min-width="240" show-overflow-tooltip />
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-switch v-model="row.status" :active-value="1" :inactive-value="0" v-perm="'rp:datasource:update'" @change="handleStatusChange(row)" />
          </template>
        </el-table-column>
        <el-table-column label="备注" prop="remark" min-width="180" show-overflow-tooltip />
        <el-table-column label="创建时间" prop="create_time" width="170" />
        <el-table-column label="操作" width="180" fixed="right" class-name="op-col">
          <template #default="{ row }">
            <el-button v-perm="'rp:datasource:update'" link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button v-perm="'rp:datasource:delete'" link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination-wrap">
        <el-pagination background layout="total, sizes, prev, pager, next, jumper"
          :total="total" v-model:current-page="query.page" v-model:page-size="query.page_size"
          :page-sizes="[10, 20, 50, 100]" @change="fetchList" />
      </div>
    </el-card>

    <el-dialog :title="dialogTitle" v-model="dialogVisible" width="640px" :close-on-click-modal="false" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="110px">
        <el-form-item label="数据源名称" prop="ds_name">
          <el-input v-model="form.ds_name" placeholder="请输入数据源名称" maxlength="100" />
        </el-form-item>
        <el-form-item label="类型" prop="ds_type">
          <el-select v-model="form.ds_type" style="width:100%">
            <el-option label="MySQL" value="mysql" />
            <el-option label="API" value="api" />
          </el-select>
        </el-form-item>
        <el-form-item label="配置JSON" prop="ds_config">
          <el-input v-model="form.ds_config" type="textarea" :rows="5" placeholder='MySQL: {"host":"127.0.0.1","port":3306,...} / API: {"url":"...","method":"GET"}' />
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <el-radio-group v-model="form.status">
            <el-radio :value="1">启用</el-radio>
            <el-radio :value="0">停用</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="备注" prop="remark">
          <el-input v-model="form.remark" type="textarea" :rows="2" placeholder="请输入备注" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible=false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitForm">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Refresh, Plus, Delete } from '@element-plus/icons-vue'
import request from '@/utils/request'

const loading = ref(false)
const rows = ref([])
const total = ref(0)
const selection = ref([])
const saving = ref(false)
const dialogVisible = ref(false)
const dialogTitle = ref('新增')
const formRef = ref()

const query_orig = { page: 1, page_size: 10, ds_name: '', ds_type: null, status: null }
const query = reactive({ ...query_orig })

const form_orig = {
  id: null, ds_name: '', ds_type: 'mysql', ds_config: '', status: 1, remark: ''
}
const form = reactive({ ...form_orig })

const rules = {
  ds_name: [{ required: true, message: '请输入数据源名称', trigger: 'blur' }],
  ds_type: [{ required: true, message: '请选择类型', trigger: 'change' }],
  ds_config: [{ required: true, message: '请输入配置JSON', trigger: 'blur' }]
}

function apiUrl(action) {
  const base = '/rp/datasource'
  return {
    list: base + '/list',
    create: base + '/create',
    update: base + '/update',
    delete: base + '/delete'
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

function openCreate() { Object.assign(form, form_orig); dialogTitle.value = '新增数据源'; dialogVisible.value = true }
function openEdit(row) { Object.assign(form, form_orig, row); dialogTitle.value = '编辑数据源'; dialogVisible.value = true }

async function submitForm() {
  await formRef.value.validate()
  saving.value = true
  try {
    if (form.id) {
      const { id, ...data } = form
      await request.put(`${apiUrl('update')}/${id}`, data); ElMessage.success('更新成功')
    } else {
      await request.post(apiUrl('create'), form); ElMessage.success('新增成功')
    }
    dialogVisible.value = false; fetchList()
  } finally { saving.value = false }
}

async function handleStatusChange(row) {
  await request.put(`/rp/datasource/status/${row.id}`, { status: row.status })
  ElMessage.success(row.status === 1 ? '已启用' : '已停用')
}

async function handleDelete(row) {
  await ElMessageBox.confirm('确定删除该数据源？', '提示', { type: 'warning' })
  await request.delete(apiUrl('delete'), { data: { ids: [row.id] } })
  ElMessage.success('删除成功'); fetchList()
}

async function handleBatchDelete() {
  await ElMessageBox.confirm(`确定删除选中的 ${selection.value.length} 条数据源？`, '提示', { type: 'warning' })
  await request.delete(apiUrl('delete'), { data: { ids: selection.value.map(r => r.id) } })
  ElMessage.success('批量删除成功'); fetchList()
}

onMounted(fetchList)
</script>
