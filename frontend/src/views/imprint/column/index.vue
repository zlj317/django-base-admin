<template>
  <div class="app-container">
    <div class="page-header">
      <div class="page-title-wrap">
        <h2>模板字段</h2>
        <div class="sub">导入模板字段管理 · 共 {{ total }} 条</div>
      </div>
    </div>

    <el-card shadow="never" class="search-card">
      <el-form :model="query" inline @submit.prevent>
        <el-form-item label="所属模板">
          <el-select v-model="query.template_id" placeholder="全部" clearable style="width: 200px">
            <el-option v-for="t in templateOptions" :key="t.id" :label="t.template_name" :value="t.id" />
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
        <el-table-column label="所属模板" min-width="140">
          <template #default="{ row }">{{ getTemplateName(row.template_id) }}</template>
        </el-table-column>
        <el-table-column label="字段名" prop="column_name" min-width="140" show-overflow-tooltip />
        <el-table-column label="表头" prop="column_header" min-width="140" show-overflow-tooltip />
        <el-table-column label="必填" width="80" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.is_required===1" size="small" type="danger">必填</el-tag>
            <el-tag v-else size="small" type="info">可选</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="数据类型" prop="data_type" width="110" />
        <el-table-column label="最大长度" prop="max_length" width="90" />
        <el-table-column label="排序" prop="sort" width="70" />
        <el-table-column label="创建时间" prop="create_time" width="170" />
        <el-table-column label="操作" width="180" fixed="right" class-name="op-col">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
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

    <el-dialog :title="dialogTitle" v-model="dialogVisible" width="560px" :close-on-click-modal="false" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-row :gutter="12">
          <el-col :span="24">
            <el-form-item label="所属模板" prop="template_id">
              <el-select v-model="form.template_id" placeholder="请选择模板" style="width:100%">
                <el-option v-for="t in templateOptions" :key="t.id" :label="t.template_name" :value="t.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="字段名" prop="column_name">
              <el-input v-model="form.column_name" placeholder="如 user_name" maxlength="100" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="表头名称" prop="column_header">
              <el-input v-model="form.column_header" placeholder="如 用户名" maxlength="100" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="数据类型" prop="data_type">
              <el-select v-model="form.data_type" style="width:100%">
                <el-option label="字符串" value="string" />
                <el-option label="整数" value="integer" />
                <el-option label="小数" value="decimal" />
                <el-option label="日期" value="date" />
                <el-option label="布尔" value="boolean" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="最大长度" prop="max_length">
              <el-input-number v-model="form.max_length" :min="1" :max="2000" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="排序" prop="sort">
              <el-input-number v-model="form.sort" :min="0" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="是否必填" prop="is_required">
              <el-switch v-model="form.is_required" :active-value="1" :inactive-value="0" active-text="必填" inactive-text="可选" />
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
const dialogTitle = ref('新增模板字段')
const formRef = ref()
const templateOptions = ref([])

const query_orig = { page: 1, page_size: 10, template_id: null }
const query = reactive({ ...query_orig })

const form_orig = {
  id: null, template_id: null, column_name: '', column_header: '',
  is_required: 0, data_type: 'string', max_length: 100, sort: 0
}
const form = reactive({ ...form_orig })

const rules = {
  template_id: [{ required: true, message: '请选择所属模板', trigger: 'change' }],
  column_name: [{ required: true, message: '请输入字段名', trigger: 'blur' }]
}

const apiBase = '/imprint/column'

function getTemplateName(id) {
  if (!id) return '-'
  const t = templateOptions.value.find(x => x.id === id)
  return t ? t.template_name : id
}

async function loadTemplates() {
  try {
    const res = await request.get('/imprint/template/list', { params: { page: 1, page_size: 200 } })
    templateOptions.value = res.data.list || []
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

function openCreate() { Object.assign(form, form_orig); dialogTitle.value = '新增模板字段'; dialogVisible.value = true }
function openEdit(row) { Object.assign(form, form_orig, row); dialogTitle.value = '编辑模板字段'; dialogVisible.value = true }

async function submitForm() {
  await formRef.value.validate()
  saving.value = true
  try {
    if (form.id) {
      const { id, ...data } = form
      await request.put(`${apiBase}/update/${id}`, data); ElMessage.success('更新成功')
    } else {
      await request.post(apiBase + '/create', form); ElMessage.success('新增成功')
    }
    dialogVisible.value = false; fetchList()
  } finally { saving.value = false }
}

async function handleDelete(row) {
  await ElMessageBox.confirm('确定删除该字段？', '提示', { type: 'warning' })
  await request.delete(apiBase + '/delete', { data: { ids: [row.id] } })
  ElMessage.success('删除成功'); fetchList()
}

async function handleBatchDelete() {
  await ElMessageBox.confirm(`确定删除选中的 ${selection.value.length} 条？`, '提示', { type: 'warning' })
  await request.delete(apiBase + '/delete', { data: { ids: selection.value.map(r => r.id) } })
  ElMessage.success('批量删除成功'); fetchList()
}

onMounted(() => { loadTemplates(); fetchList() })
</script>
