<template>
  <div class="app-container">
    <div class="page-header">
      <div class="page-title-wrap">
        <h2>同步任务</h2>
        <div class="sub">同步配置 · 共 {{ total }} 条</div>
      </div>
    </div>
    <el-card shadow="never" class="search-card">
      <el-form :model="query" inline @submit.prevent>
        <el-form-item label="同步名称">
          <el-input v-model="query.sync_name" placeholder="请输入名称" clearable style="width: 170px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="同步类型">
          <el-select v-model="query.sync_type" placeholder="全部" clearable style="width: 120px">
            <el-option label="手动" value="manual" />
            <el-option label="定时" value="schedule" />
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
            <el-button v-perm="'outer:sync:create'" type="primary" :icon="Plus" @click="openCreate">新增</el-button>
            <el-button v-perm="'outer:sync:delete'" type="danger" plain :icon="Delete" :disabled="!selection.length" @click="handleBatchDelete">批量删除</el-button>
          </div>
        </div>
      </template>
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据" @selection-change="onSelectionChange">
        <el-table-column type="selection" width="50" />
        <el-table-column label="编号" prop="id" width="70" />
        <el-table-column label="同步名称" prop="sync_name" min-width="170" show-overflow-tooltip />
        <el-table-column label="目标接口" min-width="150">
          <template #default="{ row }">{{ row.api_name || row.api_id || '-' }}</template>
        </el-table-column>
        <el-table-column label="目标表" prop="target_table" min-width="140" show-overflow-tooltip />
        <el-table-column label="同步类型" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.sync_type==='manual'" size="small">手动</el-tag>
            <el-tag v-else-if="row.sync_type==='schedule'" size="small" type="warning">定时</el-tag>
            <span v-else>{{ row.sync_type }}</span>
          </template>
        </el-table-column>
        <el-table-column label="任务ID" prop="task_id" width="90">
          <template #default="{ row }">{{ row.task_id || '-' }}</template>
        </el-table-column>
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-switch v-model="row.status" :active-value="1" :inactive-value="0" v-perm="'outer:sync:update'" @change="handleStatusChange(row)" />
          </template>
        </el-table-column>
        <el-table-column label="备注" prop="remark" min-width="160" show-overflow-tooltip />
        <el-table-column label="创建时间" prop="create_time" width="170" />
        <el-table-column label="操作" width="180" fixed="right" class-name="op-col">
          <template #default="{ row }">
            <el-button v-perm="'outer:sync:update'" link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button v-perm="'outer:sync:delete'" link type="danger" @click="handleDelete(row)">删除</el-button>
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
        <el-form-item label="同步名称" prop="sync_name">
          <el-input v-model="form.sync_name" placeholder="请输入同步名称" maxlength="100" />
        </el-form-item>
        <el-form-item label="目标接口" prop="api_id">
          <el-select v-model="form.api_id" placeholder="请选择外部接口" style="width:100%" filterable>
            <el-option v-for="a in apiOptions" :key="a.id" :label="a.api_name + ' (' + a.method + ')'" :value="a.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="目标表" prop="target_table">
          <el-input v-model="form.target_table" placeholder="请输入目标表名" maxlength="100" />
        </el-form-item>
        <el-form-item label="同步字段JSON" prop="sync_field_json">
          <el-input v-model="form.sync_field_json" type="textarea" :rows="4" placeholder='接口字段到表字段映射，如 {"api_field":"db_field"}' />
        </el-form-item>
        <el-form-item label="同步类型" prop="sync_type">
          <el-select v-model="form.sync_type" style="width:100%">
            <el-option label="手动" value="manual" />
            <el-option label="定时" value="schedule" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="form.sync_type==='schedule'" label="关联任务ID" prop="task_id">
          <el-input v-model.number="form.task_id" placeholder="定时任务ID" />
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
const apiOptions = ref([])

const query_orig = { page: 1, page_size: 10, sync_name: '', sync_type: null, status: null }
const query = reactive({ ...query_orig })

const form_orig = {
  id: null, sync_name: '', api_id: null, target_table: '', sync_field_json: '',
  sync_type: 'manual', task_id: null, status: 1, remark: ''
}
const form = reactive({ ...form_orig })

const rules = {
  sync_name: [{ required: true, message: '请输入同步名称', trigger: 'blur' }],
  api_id: [{ required: true, message: '请选择目标接口', trigger: 'change' }],
  target_table: [{ required: true, message: '请输入目标表名', trigger: 'blur' }],
  sync_type: [{ required: true, message: '请选择同步类型', trigger: 'change' }]
}

function apiUrl(action) {
  const base = '/outer/sync'
  return {
    list: base + '/list',
    create: base + '/create',
    update: base + '/update',
    delete: base + '/delete'
  }[action]
}

async function loadApiOptions() {
  try {
    const res = await request.get('/outer/api/list', { params: { page: 1, page_size: 200 } })
    apiOptions.value = res.data.list || []
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

function openCreate() { Object.assign(form, form_orig); dialogTitle.value = '新增同步任务'; dialogVisible.value = true }
function openEdit(row) { Object.assign(form, form_orig, row); dialogTitle.value = '编辑同步任务'; dialogVisible.value = true }

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
  await request.put(`/outer/sync/status/${row.id}`, { status: row.status })
  ElMessage.success(row.status === 1 ? '已启用' : '已停用')
}

async function handleDelete(row) {
  await ElMessageBox.confirm('确定删除该同步任务？', '提示', { type: 'warning' })
  await request.delete(apiUrl('delete'), { data: { ids: [row.id] } })
  ElMessage.success('删除成功'); fetchList()
}

async function handleBatchDelete() {
  await ElMessageBox.confirm(`确定删除选中的 ${selection.value.length} 条同步任务？`, '提示', { type: 'warning' })
  await request.delete(apiUrl('delete'), { data: { ids: selection.value.map(r => r.id) } })
  ElMessage.success('批量删除成功'); fetchList()
}

onMounted(() => { fetchList(); loadApiOptions() })
</script>
