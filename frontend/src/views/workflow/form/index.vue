<template>
  <div class="app-container">
    <div class="page-header">
      <div class="page-title-wrap">
        <h2>流程表单</h2>
        <div class="sub">自定义业务表单设计与绑定 · 共 {{ total }} 条记录</div>
      </div>
    </div>

    <el-card shadow="never" class="search-card">
      <el-form :model="query" inline @submit.prevent>
        <el-form-item label="表单名称">
          <el-input v-model="query.form_name" placeholder="请输入表单名称" clearable style="width: 180px" @keyup.enter="handleQuery" />
        </el-form-item>
        <el-form-item label="表单标识">
          <el-input v-model="query.form_key" placeholder="请输入表单标识" clearable style="width: 180px" @keyup.enter="handleQuery" />
        </el-form-item>
        <el-form-item class="search-actions">
          <el-button type="primary" :icon="Search" @click="handleQuery">查询</el-button>
          <el-button :icon="Refresh" @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="table-card">
      <template #header>
        <div class="card-header">
          <span class="card-title">表单列表</span>
          <div class="card-actions">
            <el-button v-perm="'wf:form:create'" type="primary" :icon="Plus" @click="openCreate">新增</el-button>
            <el-button v-perm="'wf:form:delete'" type="danger" plain :icon="Delete" :disabled="!selectedIds.length" @click="handleBatchDelete">批量删除</el-button>
          </div>
        </div>
      </template>
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据" @selection-change="onSelectionChange">
        <el-table-column type="selection" width="50" align="center" />
        <el-table-column label="编号" prop="id" width="70" align="center" />
        <el-table-column label="表单名称" prop="form_name" min-width="160" show-overflow-tooltip />
        <el-table-column label="表单标识" prop="form_key" min-width="150" show-overflow-tooltip />
        <el-table-column label="字段数" width="90" align="center">
          <template #default="scope">{{ fieldCount(scope.row) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="90" align="center">
          <template #default="scope">
            <el-tag :type="scope.row.status === 0 ? 'success' : 'info'">{{ scope.row.status === 0 ? '启用' : '停用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="备注" prop="remark" min-width="150" show-overflow-tooltip />
        <el-table-column label="创建时间" prop="create_time" width="170" />
        <el-table-column label="操作" width="220" align="center" fixed="right">
          <template #default="scope">
            <el-button v-perm="'wf:form:update'" link type="primary" :icon="Grid" @click="openDesign(scope.row)">设计表单</el-button>
            <el-button v-perm="'wf:form:update'" link type="primary" :icon="Edit" @click="openEdit(scope.row)">编辑</el-button>
            <el-button v-perm="'wf:form:delete'" link type="danger" :icon="Delete" @click="handleDelete(scope.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination-wrap">
        <el-pagination background layout="total, sizes, prev, pager, next, jumper"
          :total="total" v-model:current-page="query.page" v-model:page-size="query.page_size"
          :page-sizes="[10, 20, 50, 100]" @change="getList" />
      </div>
    </el-card>

    <el-dialog :title="form.id ? '编辑流程表单' : '新增流程表单'" v-model="dialogVisible" width="540px" :close-on-click-modal="false" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="表单名称" prop="form_name">
          <el-input v-model="form.form_name" placeholder="如：请假申请单" />
        </el-form-item>
        <el-form-item label="表单标识" prop="form_key">
          <el-input v-model="form.form_key" placeholder="唯一标识，如 leave_form" :disabled="!!form.id" />
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <el-radio-group v-model="form.status">
            <el-radio :label="0">启用</el-radio>
            <el-radio :label="1">停用</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="备注" prop="remark">
          <el-input v-model="form.remark" type="textarea" :rows="3" placeholder="请输入备注" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitForm">确定</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="designVisible" :title="`表单设计 · ${design.form_name}`" width="1000px" top="5vh" :close-on-click-modal="false" destroy-on-close>
      <div class="design-layout">
        <div class="design-panel">
          <div class="design-toolbar">
            <el-button type="primary" :icon="Plus" @click="openFieldDialog()">添加字段</el-button>
            <el-button :icon="DocumentChecked" :loading="designSaving" @click="saveDesign">保存表单</el-button>
          </div>
          <el-table :data="design.fields" size="small" border empty-text="暂无字段，请添加">
            <el-table-column label="字段名称" prop="label" min-width="110" />
            <el-table-column label="字段标识" prop="key" min-width="110" />
            <el-table-column label="类型" width="100" align="center">
              <template #default="scope">{{ typeName(scope.row.type) }}</template>
            </el-table-column>
            <el-table-column label="必填" width="70" align="center">
              <template #default="scope">{{ scope.row.required ? '是' : '否' }}</template>
            </el-table-column>
            <el-table-column label="操作" width="140" align="center">
              <template #default="scope">
                <el-button link type="primary" @click="openFieldDialog(scope.$index)">编辑</el-button>
                <el-button link type="danger" @click="removeField(scope.$index)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
        <div class="design-preview">
          <div class="preview-title">表单预览</div>
          <FormRenderer :fields="design.fields" :data="previewData" />
        </div>
      </div>
      <template #footer>
        <el-button @click="designVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="fieldVisible" :title="fieldIndex >= 0 ? '编辑字段' : '添加字段'" width="520px" append-to-body :close-on-click-modal="false">
      <el-form :model="field" label-width="90px">
        <el-form-item label="字段名称">
          <el-input v-model="field.label" placeholder="如：请假天数" />
        </el-form-item>
        <el-form-item label="字段标识">
          <el-input v-model="field.key" placeholder="英文标识，如 leaveDays" :disabled="fieldIndex >= 0" />
        </el-form-item>
        <el-form-item label="字段类型">
          <el-select v-model="field.type" style="width: 100%">
            <el-option v-for="item in fieldTypes" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="field.type === 'select'" label="选项">
          <el-input v-model="field.optionsText" placeholder="多个选项用英文逗号分隔，如：事假,病假,年假" />
        </el-form-item>
        <el-form-item label="必填">
          <el-switch v-model="field.required" />
        </el-form-item>
        <el-form-item label="提示文字">
          <el-input v-model="field.placeholder" placeholder="输入框占位提示" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="fieldVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmField">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Refresh, Plus, Delete, Edit, Grid, DocumentChecked } from '@element-plus/icons-vue'
import request from '@/utils/request'
import FormRenderer from '@/components/workflow/FormRenderer.vue'

const fieldTypes = [
  { label: '单行文本', value: 'text' },
  { label: '多行文本', value: 'textarea' },
  { label: '数字', value: 'number' },
  { label: '日期', value: 'date' },
  { label: '下拉选择', value: 'select' },
  { label: '附件地址', value: 'file' }
]

const loading = ref(false)
const saving = ref(false)
const rows = ref([])
const total = ref(0)
const selectedIds = ref([])
const dialogVisible = ref(false)
const formRef = ref()
const query = reactive({ page: 1, page_size: 10, form_name: '', form_key: '' })
const form = reactive({ id: 0, form_name: '', form_key: '', status: 0, remark: '' })
const rules = {
  form_name: [{ required: true, message: '请输入表单名称', trigger: 'blur' }],
  form_key: [{ required: true, message: '请输入表单标识', trigger: 'blur' }]
}

const designVisible = ref(false)
const designSaving = ref(false)
const design = reactive({ id: 0, form_name: '', fields: [] })
const previewData = reactive({})

const fieldVisible = ref(false)
const fieldIndex = ref(-1)
const field = reactive({ label: '', key: '', type: 'text', required: false, placeholder: '', optionsText: '' })

function parseFields(row) {
  try {
    const list = JSON.parse(row.form_json || '[]')
    return Array.isArray(list) ? list : []
  } catch (e) {
    return []
  }
}
function fieldCount(row) {
  return parseFields(row).length
}
function typeName(type) {
  return fieldTypes.find(item => item.value === type)?.label || type
}

async function getList() {
  loading.value = true
  try {
    const res = await request.get('/wf/form/list', { params: query })
    rows.value = res.data.list
    total.value = res.data.total
  } finally {
    loading.value = false
  }
}
function handleQuery() {
  query.page = 1
  getList()
}
function resetQuery() {
  Object.assign(query, { page: 1, form_name: '', form_key: '' })
  getList()
}
function onSelectionChange(rowsSelected) {
  selectedIds.value = rowsSelected.map(row => row.id)
}
function openCreate() {
  Object.assign(form, { id: 0, form_name: '', form_key: '', status: 0, remark: '' })
  dialogVisible.value = true
}
function openEdit(row) {
  Object.assign(form, { id: row.id, form_name: row.form_name, form_key: row.form_key, status: row.status, remark: row.remark || '' })
  dialogVisible.value = true
}
async function submitForm() {
  await formRef.value.validate()
  saving.value = true
  try {
    if (form.id) {
      await request.put(`/wf/form/update/${form.id}`, form)
      ElMessage.success('修改成功')
    } else {
      await request.post('/wf/form/create', { ...form, form_json: '[]' })
      ElMessage.success('新增成功')
    }
    dialogVisible.value = false
    getList()
  } finally {
    saving.value = false
  }
}
async function handleDelete(row) {
  await ElMessageBox.confirm(`确认删除表单「${row.form_name}」吗？`, '提示', { type: 'warning' })
  await request.delete('/wf/form/delete', { data: { ids: [row.id] } })
  ElMessage.success('删除成功')
  getList()
}
async function handleBatchDelete() {
  await ElMessageBox.confirm(`确认删除选中的 ${selectedIds.value.length} 条表单吗？`, '提示', { type: 'warning' })
  await request.delete('/wf/form/delete', { data: { ids: selectedIds.value } })
  ElMessage.success('删除成功')
  getList()
}

async function openDesign(row) {
  const res = await request.get(`/wf/form/detail/${row.id}`)
  design.id = res.data.id
  design.form_name = res.data.form_name
  design.fields = res.data.form_json_obj || []
  Object.keys(previewData).forEach(key => delete previewData[key])
  design.fields.forEach(item => { previewData[item.key] = item.type === 'number' ? null : '' })
  designVisible.value = true
}
function openFieldDialog(index = -1) {
  fieldIndex.value = index
  if (index >= 0) {
    const item = design.fields[index]
    Object.assign(field, {
      label: item.label,
      key: item.key,
      type: item.type,
      required: !!item.required,
      placeholder: item.placeholder || '',
      optionsText: (item.options || []).join(',')
    })
  } else {
    Object.assign(field, { label: '', key: '', type: 'text', required: false, placeholder: '', optionsText: '' })
  }
  fieldVisible.value = true
}
function confirmField() {
  if (!field.label || !field.key) {
    ElMessage.warning('请填写字段名称与字段标识')
    return
  }
  if (design.fields.some((item, idx) => item.key === field.key && idx !== fieldIndex.value)) {
    ElMessage.warning('字段标识已存在')
    return
  }
  const item = {
    label: field.label,
    key: field.key,
    type: field.type,
    required: !!field.required,
    placeholder: field.placeholder,
    ...(field.type === 'select' ? { options: field.optionsText.split(',').map(s => s.trim()).filter(Boolean) } : {})
  }
  if (fieldIndex.value >= 0) {
    design.fields.splice(fieldIndex.value, 1, item)
  } else {
    design.fields.push(item)
    previewData[item.key] = item.type === 'number' ? null : ''
  }
  fieldVisible.value = false
}
function removeField(index) {
  const key = design.fields[index].key
  design.fields.splice(index, 1)
  delete previewData[key]
}
async function saveDesign() {
  if (!design.fields.length) {
    ElMessage.warning('请至少添加一个字段')
    return
  }
  designSaving.value = true
  try {
    await request.put(`/wf/form/update/${design.id}`, { form_json: JSON.stringify(design.fields) })
    ElMessage.success('表单保存成功')
    designVisible.value = false
    getList()
  } finally {
    designSaving.value = false
  }
}

onMounted(getList)
</script>

<style scoped>
.design-layout {
  display: flex;
  gap: 16px;
  align-items: flex-start;
}
.design-panel {
  flex: 1;
  min-width: 0;
}
.design-toolbar {
  display: flex;
  gap: 10px;
  margin-bottom: 12px;
}
.design-preview {
  width: 380px;
  flex: none;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  padding: 12px;
  background: var(--el-fill-color-lighter);
  min-height: 300px;
}
.preview-title {
  font-weight: 600;
  margin-bottom: 10px;
}
</style>
