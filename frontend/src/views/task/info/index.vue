<template>
  <div class="app-container">
    <div class="page-header">
      <div class="page-title-wrap">
        <h2>任务信息</h2>
        <div class="sub">定时调度任务 · 共 {{ total }} 条</div>
      </div>
    </div>
    <el-card shadow="never" class="search-card">
      <el-form :model="query" inline @submit.prevent>
        <el-form-item label="任务名称">
          <el-input v-model="query.task_name" placeholder="请输入任务名称" clearable style="width: 170px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="任务Key">
          <el-input v-model="query.task_key" placeholder="请输入任务Key" clearable style="width: 170px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="query.status" placeholder="全部" clearable style="width: 110px">
            <el-option label="运行" :value="1" />
            <el-option label="暂停" :value="0" />
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
            <el-button v-perm="'task:create'" type="primary" :icon="Plus" @click="openCreate">新增</el-button>
            <el-button v-perm="'task:delete'" type="danger" plain :icon="Delete" :disabled="!selection.length" @click="handleBatchDelete">批量删除</el-button>
          </div>
        </div>
      </template>
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据" @selection-change="onSelectionChange">
        <el-table-column type="index" label="序号" width="70" align="center" />
        <el-table-column type="selection" width="50" />
        <el-table-column label="任务名称" prop="task_name" min-width="160" show-overflow-tooltip />
        <el-table-column label="任务Key" prop="task_key" min-width="140" show-overflow-tooltip />
        <el-table-column label="类型" prop="task_type" width="90">
          <template #default="{ row }">
            <el-tag v-if="row.task_type==='cron'" size="small">Cron</el-tag>
            <el-tag v-else-if="row.task_type==='interval'" size="small" type="success">间隔</el-tag>
            <span v-else>{{ row.task_type }}</span>
          </template>
        </el-table-column>
        <el-table-column label="Cron表达式" prop="cron_expr" min-width="140" show-overflow-tooltip>
          <template #default="{ row }">{{ row.cron_expr || '-' }}</template>
        </el-table-column>
        <el-table-column label="间隔秒" prop="interval_sec" width="90">
          <template #default="{ row }">{{ row.interval_sec || '-' }}</template>
        </el-table-column>
        <el-table-column label="失败重试" prop="retry_count" width="90">
          <template #default="{ row }">{{ row.retry_on_fail ? (row.retry_count || 0) + '次' : '-' }}</template>
        </el-table-column>
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-switch v-model="row.status" :active-value="1" :inactive-value="0" v-perm="'task:update'" @change="handleStatusChange(row)" />
          </template>
        </el-table-column>
        <el-table-column label="创建时间" prop="create_time" width="170" />
        <el-table-column label="操作" width="260" fixed="right" class-name="op-col">
          <template #default="{ row }">
            <el-button v-perm="'task:update'" link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button v-perm="'task:runOnce'" link type="success" @click="handleRunNow(row)">立即执行</el-button>
            <el-button v-perm="'task:delete'" link type="danger" @click="handleDelete(row)">删除</el-button>
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
        <el-form-item label="任务名称" prop="task_name">
          <el-input v-model="form.task_name" placeholder="请输入任务名称" maxlength="100" />
        </el-form-item>
        <el-form-item label="任务Key" prop="task_key">
          <el-input v-model="form.task_key" placeholder="如 report_daily_sync" maxlength="100" :disabled="!!form.id" />
        </el-form-item>
        <el-form-item label="任务类型" prop="task_type">
          <el-select v-model="form.task_type" style="width:100%" @change="onTypeChange">
            <el-option label="Cron表达式" value="cron" />
            <el-option label="固定间隔" value="interval" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="form.task_type==='cron'" label="Cron表达式" prop="cron_expr">
          <el-input v-model="form.cron_expr" placeholder="如 0 0 2 * * ?" maxlength="64" />
        </el-form-item>
        <el-form-item v-if="form.task_type==='interval'" label="间隔秒" prop="interval_sec">
          <el-input-number v-model="form.interval_sec" :min="1" :max="8640000" />
        </el-form-item>
        <el-form-item label="参数" prop="params">
          <el-input v-model="form.params" type="textarea" :rows="3" placeholder='JSON字符串，如 {"key":"val"}' />
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <el-radio-group v-model="form.status">
            <el-radio :value="1">运行</el-radio>
            <el-radio :value="0">暂停</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="失败重试" prop="retry_on_fail">
          <el-switch v-model="form.retry_on_fail" :active-value="1" :inactive-value="0" />
        </el-form-item>
        <el-form-item v-if="form.retry_on_fail" label="重试次数" prop="retry_count">
          <el-input-number v-model="form.retry_count" :min="1" :max="10" />
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

const query_orig = { page: 1, page_size: 10, task_name: '', task_key: '', status: null }
const query = reactive({ ...query_orig })

const form_orig = {
  id: null, task_name: '', task_key: '', task_type: 'cron', cron_expr: '',
  interval_sec: 60, params: '', status: 1, retry_on_fail: 0, retry_count: 3, remark: ''
}
const form = reactive({ ...form_orig })

const rules = {
  task_name: [{ required: true, message: '请输入任务名称', trigger: 'blur' }],
  task_key: [{ required: true, message: '请输入任务Key', trigger: 'blur' }],
  task_type: [{ required: true, message: '请选择任务类型', trigger: 'change' }],
  cron_expr: [{ required: true, message: '请输入Cron表达式', trigger: 'blur' }]
}

function apiUrl(action) {
  const base = '/task/info'
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

function onTypeChange() {
  if (form.task_type === 'cron') form.interval_sec = 60
  else form.cron_expr = ''
}

function openCreate() { Object.assign(form, form_orig); dialogTitle.value = '新增任务'; dialogVisible.value = true }
function openEdit(row) { Object.assign(form, form_orig, row); dialogTitle.value = '编辑任务'; dialogVisible.value = true }

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

async function handleRunNow(row) {
  await ElMessageBox.confirm(`确定立即执行任务「${row.task_name}」？`, '提示', { type: 'warning' })
  await request.post(`/task/info/run_once/${row.id}`)
  ElMessage.success('已触发立即执行')
}

async function handleStatusChange(row) {
  await request.put(`/task/info/status/${row.id}`, { status: row.status })
  ElMessage.success(row.status === 1 ? '已启动' : '已暂停')
}

async function handleDelete(row) {
  await ElMessageBox.confirm('确定删除该任务？', '提示', { type: 'warning' })
  await request.delete(apiUrl('delete'), { data: { ids: [row.id] } })
  ElMessage.success('删除成功'); fetchList()
}

async function handleBatchDelete() {
  await ElMessageBox.confirm(`确定删除选中的 ${selection.value.length} 条任务？`, '提示', { type: 'warning' })
  await request.delete(apiUrl('delete'), { data: { ids: selection.value.map(r => r.id) } })
  ElMessage.success('批量删除成功'); fetchList()
}

onMounted(fetchList)
</script>
