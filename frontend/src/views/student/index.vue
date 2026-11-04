<template>
  <div class="app-container">
    <div class="page-header">
      <div class="page-title-wrap">
        <h2>学生信息表</h2>
        <div class="sub">数据维护 · 共 {{ total }} 条记录</div>
      </div>
    </div>
    <!-- 查询区域 -->
    <el-card shadow="never" class="search-card">
      <el-form :model="query" inline @submit.prevent>
        <el-form-item label="学生姓名">
          <el-input v-model="query.name" placeholder="请输入学生姓名" clearable style="width: 180px" @keyup.enter="handleQuery" />
        </el-form-item>
        <el-form-item label="年龄">
          <el-input v-model="query.age" placeholder="请输入年龄" clearable style="width: 180px" @keyup.enter="handleQuery" />
        </el-form-item>
        <el-form-item label="性别（字典sys_user_sex）">
          <el-select v-model="query.gender" placeholder="请选择" clearable style="width: 180px">
            <el-option v-for="d in dictList('sys_user_sex')" :key="d.dict_value" :label="d.dict_label" :value="d.dict_value" />
          </el-select>
        </el-form-item>
        <el-form-item label="手机号">
          <el-input v-model="query.phone" placeholder="请输入手机号" clearable style="width: 180px" @keyup.enter="handleQuery" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="query.email" placeholder="请输入邮箱" clearable style="width: 180px" @keyup.enter="handleQuery" />
        </el-form-item>
        <el-form-item label="入学日期">
          <el-input v-model="query.enroll_date" placeholder="请输入入学日期" clearable style="width: 180px" @keyup.enter="handleQuery" />
        </el-form-item>
        <el-form-item label="总分">
          <el-input v-model="query.score" placeholder="请输入总分" clearable style="width: 180px" @keyup.enter="handleQuery" />
        </el-form-item>
        <el-form-item label="家庭住址">
          <el-input v-model="query.address" placeholder="请输入家庭住址" clearable style="width: 180px" @keyup.enter="handleQuery" />
        </el-form-item>
        <el-form-item class="search-actions">
          <el-button type="primary" :icon="Search" @click="handleQuery">查询</el-button>
          <el-button :icon="Refresh" @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 数据表格 -->
    <el-card shadow="never" class="table-card">
      <template #header>
        <div class="card-header">
          <div class="card-actions">
            <el-button v-perm="'student:create'" type="primary" :icon="Plus" @click="openCreate">新增</el-button>
            <el-button v-perm="'student:import'" type="success" plain :icon="Upload" @click="importVisible = true">导入</el-button>
            <el-button v-perm="'student:export'" type="warning" plain :icon="Download" @click="handleExport">导出</el-button>
            <el-button v-perm="'student:delete'" type="danger" plain :icon="Delete" :disabled="!selectedIds.length" @click="handleBatchDelete">批量删除</el-button>
          </div>
        </div>
      </template>
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据" @selection-change="onSelectionChange">
        <el-table-column type="selection" width="50" align="center" />
        <el-table-column label="学生姓名" prop="name" align="center" show-overflow-tooltip />
        <el-table-column label="年龄" prop="age" align="center" show-overflow-tooltip />
        <el-table-column label="性别（字典sys_user_sex）" prop="gender" align="center">
          <template #default="scope">
            <el-tag :type="scope.row.gender === '0' ? 'primary' : 'info'">{{ dictLabel('sys_user_sex', scope.row.gender) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="手机号" prop="phone" align="center" show-overflow-tooltip />
        <el-table-column label="邮箱" prop="email" align="center" show-overflow-tooltip />
        <el-table-column label="入学日期" prop="enroll_date" align="center" show-overflow-tooltip />
        <el-table-column label="总分" prop="score" align="center" show-overflow-tooltip />
        <el-table-column label="家庭住址" prop="address" align="center" show-overflow-tooltip />
        <el-table-column label="操作" width="150" align="center" fixed="right">
          <template #default="scope">
            <el-button v-perm="'student:update'" link type="primary" :icon="Edit" @click="handleEdit(scope.row)">编辑</el-button>
            <el-button v-perm="'student:delete'" link type="danger" :icon="Delete" @click="handleDelete(scope.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination-wrap">
        <el-pagination background layout="total, sizes, prev, pager, next, jumper"
          :total="total" v-model:current-page="query.page" v-model:page-size="query.page_size"
          :page-sizes="[10, 20, 50, 100]" @change="getList" />
      </div>
    </el-card>
    <!-- 新增/编辑弹窗 -->
    <el-dialog :title="form.id ? '编辑学生信息表' : '新增学生信息表'" v-model="dialogVisible" width="640px" :close-on-click-modal="false" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="110px" class="dialog-form">
        <el-form-item label="学生姓名" prop="name">
          <el-input v-model="form.name" placeholder="请输入学生姓名" />
        </el-form-item>
        <el-form-item label="年龄" prop="age">
          <el-input-number v-model="form.age" :min="0" style="width: 100%" />
        </el-form-item>
        <el-form-item label="性别（字典sys_user_sex）" prop="gender">
          <el-select v-model="form.gender" placeholder="请输入性别（字典sys_user_sex）" clearable style="width: 100%">
            <el-option v-for="d in dictList('sys_user_sex')" :key="d.dict_value" :label="d.dict_label" :value="d.dict_value" />
          </el-select>
        </el-form-item>
        <el-form-item label="手机号" prop="phone">
          <el-input v-model="form.phone" placeholder="请输入手机号" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" placeholder="请输入邮箱" />
        </el-form-item>
        <el-form-item label="入学日期" prop="enroll_date">
          <el-date-picker v-model="form.enroll_date" type="datetime" placeholder="请输入入学日期" value-format="YYYY-MM-DD HH:mm:ss" style="width: 100%" />
        </el-form-item>
        <el-form-item label="总分" prop="score">
          <el-input-number v-model="form.score" :min="0" style="width: 100%" />
        </el-form-item>
        <el-form-item label="家庭住址" prop="address">
          <el-input v-model="form.address" placeholder="请输入家庭住址" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitForm">确定</el-button>
      </template>
    </el-dialog>
    <!-- 导入弹窗 -->
    <el-dialog title="导入学生信息表" v-model="importVisible" width="420px">
      <el-upload drag :auto-upload="false" :limit="1" accept=".xlsx,.xls" :on-change="onFileChange" :file-list="fileList">
        <el-icon size="40"><UploadFilled /></el-icon>
        <div>将 Excel 文件拖到此处，或点击选择</div>
      </el-upload>
      <div class="mt12">
        <el-button link type="primary" @click="downloadTemplate">下载导入模板</el-button>
      </div>
      <el-alert v-if="importErrors.length" type="error" :closable="false" class="mt12">
        <div v-for="e in importErrors" :key="e"> {{ e }}</div>
      </el-alert>
      <template #footer>
        <el-button @click="importVisible = false">取消</el-button>
        <el-button type="primary" :loading="importing" @click="submitImport">开始导入</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { UploadFilled, Plus, Edit, Delete, Search, Refresh, Upload, Download } from '@element-plus/icons-vue'
import { createApi, deleteApi, exportApi, importApi, listApi, templateApi, updateApi } from '@/api/student'
import { dictLabel, dictList, loadDicts } from '@/utils/dict'

loadDicts()

const loading = ref(false)
const saving = ref(false)
const rows = ref([])
const total = ref(0)
const selectedIds = ref([])
const dialogVisible = ref(false)
const formRef = ref()
const importVisible = ref(false)
const importing = ref(false)
const importFile = ref(null)
const importErrors = ref([])
const fileList = ref([])

const query = reactive({ page: 1, page_size: 10 })
query.name = ''
query.age = ''
query.gender = ''
query.phone = ''
query.email = ''
query.enroll_date = ''
query.score = ''
query.address = ''

const emptyForm = { id: null }
emptyForm.name = ''
emptyForm.age = null
emptyForm.gender = ''
emptyForm.phone = ''
emptyForm.email = ''
emptyForm.enroll_date = ''
emptyForm.score = null
emptyForm.address = ''
const form = reactive({ ...emptyForm })

const rules = {
  name: [{ required: true, message: '请输入学生姓名', trigger: 'blur' }],
}

async function getList() {
  loading.value = true
  try {
    const data = await listApi(query)
    rows.value = data.list
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function handleQuery() {
  query.page = 1
  getList()
}

function resetQuery() {
  Object.keys(query).forEach((key) => {
    if (!['page', 'page_size'].includes(key)) query[key] = ''
  })
  handleQuery()
}

function onSelectionChange(selection) {
  selectedIds.value = selection.map((item) => item.id)
}

function openCreate() {
  Object.assign(form, emptyForm)
  dialogVisible.value = true
}

function handleEdit(row) {
  Object.assign(form, emptyForm, row)
  dialogVisible.value = true
}

function submitForm() {
  formRef.value.validate(async (valid) => {
    if (!valid) return
    saving.value = true
    try {
      // 数值/日期字段空串转 null，避免后端校验失败
      const payload = { ...form }
      if (payload.age === '') payload.age = null
      if (payload.enroll_date === '') payload.enroll_date = null
      if (payload.score === '') payload.score = null
      if (form.id) {
        await updateApi(form.id, payload)
        ElMessage.success('修改成功')
      } else {
        await createApi(payload)
        ElMessage.success('新增成功')
      }
      dialogVisible.value = false
      getList()
    } finally {
      saving.value = false
    }
  })
}

function handleDelete(row) {
  ElMessageBox.confirm('确认删除该条记录？', '提示', { type: 'warning' }).then(async () => {
    await deleteApi([row.id])
    ElMessage.success('删除成功')
    getList()
  })
}

function handleBatchDelete() {
  ElMessageBox.confirm('确认删除选中的 %s 条记录？'.replace('%s', selectedIds.value.length), '提示', { type: 'warning' }).then(async () => {
    await deleteApi(selectedIds.value)
    ElMessage.success('删除成功')
    getList()
  })
}

async function handleExport() {
  const blob = await exportApi(query)
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = '学生信息表.xlsx'
  link.click()
  URL.revokeObjectURL(url)
}

function onFileChange(file) {
  importFile.value = file.raw
}

async function downloadTemplate() {
  const blob = await templateApi()
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = '学生信息表导入模板.xlsx'
  link.click()
  URL.revokeObjectURL(url)
}

async function submitImport() {
  if (!importFile.value) {
    ElMessage.warning('请选择要导入的文件')
    return
  }
  importing.value = true
  importErrors.value = []
  try {
    const result = await importApi(importFile.value)
    ElMessage.success(`成功导入 ${result.success_count} 条`)
    if (result.errors && result.errors.length) importErrors.value = result.errors
    else importVisible.value = false
    getList()
  } finally {
    importing.value = false
  }
}

getList()
</script>

<style scoped>
.page-title-wrap h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #1f2937;
  letter-spacing: 0.5px;
}
.page-title-wrap .sub {
  margin-top: 6px;
  font-size: 12px;
  color: #8a94a6;
}
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.card-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}
.card-actions .el-button + .el-button {
  margin-left: 0;
}
.dialog-form {
  padding-top: 4px;
}
.mb12 { margin-bottom: 12px }
.mt12 { margin-top: 12px }
</style>