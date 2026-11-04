<template>
  <div class="app-container">
    <div class="page-header">
      <div class="page-title-wrap">
        <h2>报表模板</h2>
        <div class="sub">模板管理 · 共 {{ total }} 条</div>
      </div>
    </div>
    <el-card shadow="never" class="search-card">
      <el-form :model="query" inline @submit.prevent>
        <el-form-item label="模板名称">
          <el-input v-model="query.template_name" placeholder="请输入模板名称" clearable style="width: 170px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="模板Key">
          <el-input v-model="query.template_key" placeholder="请输入模板Key" clearable style="width: 170px" @keyup.enter="handleSearch" />
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
            <el-button v-perm="'rp:template:create'" type="primary" :icon="Plus" @click="openCreate">新增</el-button>
            <el-button v-perm="'rp:template:delete'" type="danger" plain :icon="Delete" :disabled="!selection.length" @click="handleBatchDelete">批量删除</el-button>
          </div>
        </div>
      </template>
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据" @selection-change="onSelectionChange">
        <el-table-column type="index" label="序号" width="70" align="center" />
        <el-table-column type="selection" width="50" />
        <el-table-column label="模板名称" prop="template_name" min-width="180" show-overflow-tooltip />
        <el-table-column label="模板Key" prop="template_key" min-width="140" show-overflow-tooltip />
        <el-table-column label="分类" min-width="120">
          <template #default="{ row }">{{ row.category_name || row.category_id || '-' }}</template>
        </el-table-column>
        <el-table-column label="数据源" min-width="120">
          <template #default="{ row }">{{ row.ds_name || row.ds_id || '-' }}</template>
        </el-table-column>
        <el-table-column label="版本" prop="version" width="80" />
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-switch v-model="row.status" :active-value="1" :inactive-value="0" v-perm="'rp:template:update'" @change="handleStatusChange(row)" />
          </template>
        </el-table-column>
        <el-table-column label="创建时间" prop="create_time" width="170" />
        <el-table-column label="操作" width="320" fixed="right" class-name="op-col">
          <template #default="{ row }">
            <el-button link type="warning" @click="handlePreview(row)">预览</el-button>
            <el-button v-perm="'rp:template:update'" link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button v-perm="'rp:template:gen'" link type="success" @click="handleGenerate(row)">生成报表</el-button>
            <el-button v-perm="'rp:template:delete'" link type="danger" @click="handleDelete(row)">删除</el-button>
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
            <el-form-item label="模板名称" prop="template_name">
              <el-input v-model="form.template_name" placeholder="请输入模板名称" maxlength="100" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="模板Key" prop="template_key">
              <el-input v-model="form.template_key" placeholder="唯一标识" maxlength="64" :disabled="!!form.id" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="分类" prop="category_id">
              <el-select v-model="form.category_id" placeholder="请选择分类" style="width:100%">
                <el-option v-for="c in categoryOptions" :key="c.id" :label="c.category_name" :value="c.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="数据源" prop="ds_id">
              <el-select v-model="form.ds_id" placeholder="请选择数据源" style="width:100%">
                <el-option v-for="d in dsOptions" :key="d.id" :label="d.ds_name" :value="d.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="版本" prop="version">
              <el-input v-model="form.version" placeholder="如 1.0" maxlength="20" />
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
            <el-form-item label="模板JSON" prop="template_json">
              <el-input v-model="form.template_json" type="textarea" :rows="6" placeholder="低代码报表模板JSON" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="权限JSON" prop="permission_json">
              <el-input v-model="form.permission_json" type="textarea" :rows="3" placeholder="权限配置JSON" />
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

    <el-dialog :title="previewTitle" v-model="previewVisible" width="980px" top="4vh" destroy-on-close>
      <div v-loading="previewLoading" class="preview-body">
        <ReportPreview v-if="previewData" :payload="previewData" />
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Refresh, Plus, Delete } from '@element-plus/icons-vue'
import request from '@/utils/request'
import ReportPreview from '@/components/report/ReportPreview.vue'

const loading = ref(false)
const rows = ref([])
const total = ref(0)
const selection = ref([])
const saving = ref(false)
const dialogVisible = ref(false)
const dialogTitle = ref('新增')
const formRef = ref()
const categoryOptions = ref([])
const dsOptions = ref([])
const previewVisible = ref(false)
const previewLoading = ref(false)
const previewData = ref(null)
const previewTitle = ref('报表预览')

const query_orig = { page: 1, page_size: 10, template_name: '', template_key: '', status: null }
const query = reactive({ ...query_orig })

const form_orig = {
  id: null, template_name: '', template_key: '', category_id: null, ds_id: null,
  template_json: '', version: '1.0', status: 1, permission_json: '', remark: ''
}
const form = reactive({ ...form_orig })

const rules = {
  template_name: [{ required: true, message: '请输入模板名称', trigger: 'blur' }],
  template_key: [{ required: true, message: '请输入模板Key', trigger: 'blur' }],
  template_json: [{ required: true, message: '请输入模板JSON', trigger: 'blur' }]
}

function apiUrl(action) {
  const base = '/rp/template'
  return {
    list: base + '/list',
    create: base + '/create',
    update: base + '/update',
    delete: base + '/delete'
  }[action]
}

async function loadOptions() {
  try {
    const cRes = await request.get('/rp/category/list', { params: { page: 1, page_size: 200 } })
    categoryOptions.value = cRes.data.list || []
    const dRes = await request.get('/rp/datasource/list', { params: { page: 1, page_size: 200 } })
    dsOptions.value = dRes.data.list || []
  } catch (e) { /* ignore */ }
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

function openCreate() { Object.assign(form, form_orig); dialogTitle.value = '新增模板'; dialogVisible.value = true }
function openEdit(row) { Object.assign(form, form_orig, row); dialogTitle.value = '编辑模板'; dialogVisible.value = true }

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

async function handlePreview(row) {
  previewTitle.value = `报表预览 · ${row.template_name}`
  previewData.value = null
  previewVisible.value = true
  previewLoading.value = true
  try {
    const res = await request.get(`/rp/template/preview/${row.id}`)
    previewData.value = res.data
  } finally { previewLoading.value = false }
}

async function handleGenerate(row) {
  await ElMessageBox.confirm(`确定立即根据模板「${row.template_name}」生成报表？`, '提示', { type: 'warning' })
  const res = await request.post(`/rp/template/generate/${row.id}`)
  previewTitle.value = `报表预览 · 本次生成结果`
  previewData.value = res.data
  previewVisible.value = true
  ElMessage.success('报表生成成功')
  fetchList()
}

async function handleStatusChange(row) {
  await request.put(`/rp/template/status/${row.id}`, { status: row.status })
  ElMessage.success(row.status === 1 ? '已启用' : '已停用')
}

async function handleDelete(row) {
  await ElMessageBox.confirm('确定删除该模板？', '提示', { type: 'warning' })
  await request.delete(apiUrl('delete'), { data: { ids: [row.id] } })
  ElMessage.success('删除成功'); fetchList()
}

async function handleBatchDelete() {
  await ElMessageBox.confirm(`确定删除选中的 ${selection.value.length} 条模板？`, '提示', { type: 'warning' })
  await request.delete(apiUrl('delete'), { data: { ids: selection.value.map(r => r.id) } })
  ElMessage.success('批量删除成功'); fetchList()
}

onMounted(() => { fetchList(); loadOptions() })
</script>

<style scoped>
.preview-body { min-height: 320px; }
</style>
