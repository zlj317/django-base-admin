<template>
  <div class="app-container">
    <div class="page-header">
      <div class="page-title-wrap">
        <h2>角色数据权限</h2>
        <div class="sub">角色与数据权限关联 · 共 {{ total }} 条</div>
      </div>
    </div>

    <el-card shadow="never" class="search-card">
      <el-form :model="query" inline @submit.prevent>
        <el-form-item label="角色">
          <el-select v-model="query.role_id" placeholder="全部" clearable style="width: 180px">
            <el-option v-for="r in roleOptions" :key="r.id" :label="r.role_name" :value="r.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="权限">
          <el-select v-model="query.permission_id" placeholder="全部" clearable style="width: 180px">
            <el-option v-for="p in permOptions" :key="p.id" :label="p.permission_name" :value="p.id" />
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
            <el-button type="primary" :icon="Plus" @click="openCreate">新增</el-button>
            <el-button type="danger" plain :icon="Delete" :disabled="!selection.length" @click="handleBatchDelete">批量删除</el-button>
          </div>
        </div>
      </template>
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据" @selection-change="onSelectionChange">
        <el-table-column type="index" label="序号" width="70" align="center" />
        <el-table-column type="selection" width="50" />
        <el-table-column label="角色" min-width="160">
          <template #default="{ row }">{{ getRoleName(row.role_id) }}</template>
        </el-table-column>
        <el-table-column label="权限" min-width="180">
          <template #default="{ row }">{{ getPermName(row.permission_id) }}</template>
        </el-table-column>
        <el-table-column label="创建时间" prop="create_time" width="170" />
        <el-table-column label="操作" width="120" fixed="right" class-name="op-col">
          <template #default="{ row }">
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

    <el-dialog :title="dialogTitle" v-model="dialogVisible" width="480px" :close-on-click-modal="false" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="角色" prop="role_id">
          <el-select v-model="form.role_id" placeholder="请选择角色" style="width:100%">
            <el-option v-for="r in roleOptions" :key="r.id" :label="r.role_name" :value="r.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="数据权限" prop="permission_id">
          <el-select v-model="form.permission_id" placeholder="请选择权限" style="width:100%">
            <el-option v-for="p in permOptions" :key="p.id" :label="p.permission_name" :value="p.id" />
          </el-select>
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
const dialogTitle = ref('新增角色数据权限')
const formRef = ref()
const roleOptions = ref([])
const permOptions = ref([])

const query_orig = { page: 1, page_size: 10, role_id: null, permission_id: null }
const query = reactive({ ...query_orig })

const form_orig = { id: null, role_id: null, permission_id: null }
const form = reactive({ ...form_orig })

const rules = {
  role_id: [{ required: true, message: '请选择角色', trigger: 'change' }],
  permission_id: [{ required: true, message: '请选择数据权限', trigger: 'change' }]
}

const apiBase = '/dp/role_perm'

function getRoleName(id) {
  const r = roleOptions.value.find(x => x.id === id)
  return r ? r.role_name : id
}
function getPermName(id) {
  const p = permOptions.value.find(x => x.id === id)
  return p ? p.permission_name : id
}

async function loadOptions() {
  try {
    const [rRes, pRes] = await Promise.all([
      request.get('/system/role/list', { params: { page: 1, page_size: 200 } }).catch(() => null),
      request.get('/dp/permission/list', { params: { page: 1, page_size: 200 } }).catch(() => null)
    ])
    if (rRes) roleOptions.value = rRes.data.list || []
    if (pRes) permOptions.value = pRes.data.list || []
  } catch (e) { /* ignore */ }
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

function openCreate() { Object.assign(form, form_orig); dialogTitle.value = '新增角色数据权限'; dialogVisible.value = true }

async function submitForm() {
  await formRef.value.validate()
  saving.value = true
  try {
    await request.post(apiBase + '/create', form); ElMessage.success('新增成功')
    dialogVisible.value = false; fetchList()
  } finally { saving.value = false }
}

async function handleDelete(row) {
  await ElMessageBox.confirm('确定删除该关联？', '提示', { type: 'warning' })
  await request.delete(apiBase + '/delete', { data: { ids: [row.id] } })
  ElMessage.success('删除成功'); fetchList()
}

async function handleBatchDelete() {
  await ElMessageBox.confirm(`确定删除选中的 ${selection.value.length} 条？`, '提示', { type: 'warning' })
  await request.delete(apiBase + '/delete', { data: { ids: selection.value.map(r => r.id) } })
  ElMessage.success('批量删除成功'); fetchList()
}

onMounted(() => { loadOptions(); fetchList() })
</script>
