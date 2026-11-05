<template>
  <div class="app-container">
    <div class="page-header">
      <div class="page-title-wrap">
        <h2>外部接口</h2>
        <div class="sub">接口管理 · 共 {{ total }} 条</div>
      </div>
    </div>
    <el-card shadow="never" class="search-card">
      <el-form :model="query" inline @submit.prevent>
        <el-form-item label="接口名称">
          <el-input v-model="query.api_name" placeholder="请输入名称" clearable style="width: 170px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="方法">
          <el-select v-model="query.method" placeholder="全部" clearable style="width: 110px">
            <el-option label="GET" value="GET" />
            <el-option label="POST" value="POST" />
            <el-option label="PUT" value="PUT" />
            <el-option label="DELETE" value="DELETE" />
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
            <el-button v-perm="'outer:create'" type="primary" :icon="Plus" @click="openCreate">新增</el-button>
            <el-button v-perm="'outer:delete'" type="danger" plain :icon="Delete" :disabled="!selection.length" @click="handleBatchDelete">批量删除</el-button>
          </div>
        </div>
      </template>
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据" @selection-change="onSelectionChange">
        <el-table-column type="index" label="序号" width="70" align="center" />
        <el-table-column type="selection" width="50" />
        <el-table-column label="接口名称" prop="api_name" min-width="160" show-overflow-tooltip />
        <el-table-column label="请求URL" prop="api_url" min-width="220" show-overflow-tooltip />
        <el-table-column label="方法" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="methodTagType(row.method)" size="small">{{ row.method }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="认证方式" prop="auth_type" width="100" />
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-switch v-model="row.status" :active-value="1" :inactive-value="0" v-perm="'outer:update'" @change="handleStatusChange(row)" />
          </template>
        </el-table-column>
        <el-table-column label="备注" prop="remark" min-width="160" show-overflow-tooltip />
        <el-table-column label="创建时间" prop="create_time" width="170" />
        <el-table-column label="操作" width="260" fixed="right" class-name="op-col">
          <template #default="{ row }">
            <el-button v-perm="'outer:update'" link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button v-perm="'outer:test'" link type="success" @click="handleTest(row)">测试</el-button>
            <el-button v-perm="'outer:delete'" link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination-wrap">
        <el-pagination background layout="total, sizes, prev, pager, next, jumper"
          :total="total" v-model:current-page="query.page" v-model:page-size="query.page_size"
          :page-sizes="[10, 20, 50, 100]" @change="fetchList" />
      </div>
    </el-card>

    <el-dialog :title="dialogTitle" v-model="dialogVisible" width="720px" :close-on-click-modal="false" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="110px">
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="接口名称" prop="api_name">
              <el-input v-model="form.api_name" placeholder="请输入接口名称" maxlength="100" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="请求方法" prop="method">
              <el-select v-model="form.method" style="width:100%">
                <el-option label="GET" value="GET" />
                <el-option label="POST" value="POST" />
                <el-option label="PUT" value="PUT" />
                <el-option label="DELETE" value="DELETE" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="请求URL" prop="api_url">
              <el-input v-model="form.api_url" placeholder="https://api.example.com/v1/data" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="Headers JSON" prop="headers_json">
              <el-input v-model="form.headers_json" type="textarea" :rows="3" placeholder='{"Content-Type":"application/json"}' />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="参数JSON" prop="params_json">
              <el-input v-model="form.params_json" type="textarea" :rows="3" placeholder='{"key":"val"}' />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="认证方式" prop="auth_type">
              <el-select v-model="form.auth_type" style="width:100%">
                <el-option label="无" value="none" />
                <el-option label="Token" value="token" />
                <el-option label="Basic" value="basic" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="状态" prop="status">
              <el-radio-group v-model="form.status">
                <el-radio :value="1">启用</el-radio>
                <el-radio :value="0">停用</el-radio>
              </el-radio-group>
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="认证配置" prop="auth_config">
              <el-input v-model="form.auth_config" type="textarea" :rows="3" placeholder="Token/Basic 认证配置JSON" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="备注" prop="remark">
              <el-input v-model="form.remark" type="textarea" :rows="2" placeholder="请输入备注" />
            </el-form-item>
          </el-col>
        </el-row>
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

const query_orig = { page: 1, page_size: 10, api_name: '', method: null, status: null }
const query = reactive({ ...query_orig })

const form_orig = {
  id: null, api_name: '', api_url: '', method: 'GET', headers_json: '', params_json: '',
  auth_type: 'none', auth_config: '', status: 1, remark: ''
}
const form = reactive({ ...form_orig })

const rules = {
  api_name: [{ required: true, message: '请输入接口名称', trigger: 'blur' }],
  api_url: [{ required: true, message: '请输入请求URL', trigger: 'blur' }],
  method: [{ required: true, message: '请选择方法', trigger: 'change' }],
  auth_type: [{ required: true, message: '请选择认证方式', trigger: 'change' }]
}

function methodTagType(m) {
  if (m === 'GET') return 'success'
  if (m === 'POST') return 'primary'
  if (m === 'PUT') return 'warning'
  if (m === 'DELETE') return 'danger'
  return ''
}

function apiUrl(action) {
  const base = '/outer/api'
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

function openCreate() { Object.assign(form, form_orig); dialogTitle.value = '新增接口'; dialogVisible.value = true }
function openEdit(row) { Object.assign(form, form_orig, row); dialogTitle.value = '编辑接口'; dialogVisible.value = true }

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

async function handleTest(row) {
  const h = ElMessage({ message: `正在测试接口「${row.api_name}」...`, type: 'info', duration: 0 })
  try {
    const res = await request.post(`/outer/api/test/${row.id}`)
    h.close()
    ElMessageBox.alert(
      `<p><b>HTTP状态码：</b> ${res.data?.http_code ?? '-'}</p>
       <p><b>耗时：</b> ${res.data?.cost_time ?? '-'} ms</p>
       <p><b>响应：</b></p>
       <pre style="max-height:300px;overflow:auto;white-space:pre-wrap;">${JSON.stringify(res.data?.response_body ?? res.data, null, 2)}</pre>`,
      '测试结果',
      { dangerouslyUseHTMLString: true }
    )
  } catch (e) {
    h.close()
    ElMessage.error('测试失败：' + (e.message || e))
  }
}

async function handleStatusChange(row) {
  await request.put(`/outer/api/status/${row.id}`, { status: row.status })
  ElMessage.success(row.status === 1 ? '已启用' : '已停用')
}

async function handleDelete(row) {
  await ElMessageBox.confirm('确定删除该接口？', '提示', { type: 'warning' })
  await request.delete(apiUrl('delete'), { data: { ids: [row.id] } })
  ElMessage.success('删除成功'); fetchList()
}

async function handleBatchDelete() {
  await ElMessageBox.confirm(`确定删除选中的 ${selection.value.length} 条接口？`, '提示', { type: 'warning' })
  await request.delete(apiUrl('delete'), { data: { ids: selection.value.map(r => r.id) } })
  ElMessage.success('批量删除成功'); fetchList()
}

onMounted(fetchList)
</script>
