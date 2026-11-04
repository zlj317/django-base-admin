<template>
  <div class="app-container">
    <div class="page-header">
      <div class="page-title-wrap">
        <h2>流程监听器</h2>
        <div class="sub">节点事件回调与通知配置 · 共 {{ total }} 条记录</div>
      </div>
    </div>

    <el-card shadow="never" class="search-card">
      <el-form :model="query" inline @submit.prevent>
        <el-form-item label="流程模型">
          <el-select v-model="query.model_id" placeholder="请选择" clearable style="width: 200px">
            <el-option v-for="m in modelOptions" :key="m.id" :label="m.model_name" :value="m.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="事件类型">
          <el-select v-model="query.event_type" placeholder="请选择" clearable style="width: 160px">
            <el-option v-for="item in eventTypes" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
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
          <div class="card-actions">
            <el-button v-perm="'wf:listener:create'" type="primary" :icon="Plus" @click="openCreate">新增</el-button>
            <el-button v-perm="'wf:listener:delete'" type="danger" plain :icon="Delete" :disabled="!selectedIds.length" @click="handleBatchDelete">批量删除</el-button>
          </div>
        </div>
      </template>
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据" @selection-change="onSelectionChange">
        <el-table-column type="selection" width="50" align="center" />
        <el-table-column label="编号" prop="id" width="70" align="center" />
        <el-table-column label="流程模型" prop="model_name" min-width="140" show-overflow-tooltip />
        <el-table-column label="事件类型" width="110" align="center">
          <template #default="scope">{{ typeName(eventTypes, scope.row.event_type) }}</template>
        </el-table-column>
        <el-table-column label="动作" width="110" align="center">
          <template #default="scope">{{ typeName(actionTypes, scope.row.action_type) }}</template>
        </el-table-column>
        <el-table-column label="回调地址" prop="callback_url" min-width="200" show-overflow-tooltip />
        <el-table-column label="状态" width="90" align="center">
          <template #default="scope">
            <el-tag :type="scope.row.status === 0 ? 'success' : 'info'">{{ scope.row.status === 0 ? '启用' : '停用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" prop="create_time" width="170" />
        <el-table-column label="操作" width="150" align="center" fixed="right">
          <template #default="scope">
            <el-button v-perm="'wf:listener:update'" link type="primary" :icon="Edit" @click="openEdit(scope.row)">编辑</el-button>
            <el-button v-perm="'wf:listener:delete'" link type="danger" :icon="Delete" @click="handleDelete(scope.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination-wrap">
        <el-pagination background layout="total, sizes, prev, pager, next, jumper"
          :total="total" v-model:current-page="query.page" v-model:page-size="query.page_size"
          :page-sizes="[10, 20, 50, 100]" @change="getList" />
      </div>
    </el-card>

    <el-dialog :title="form.id ? '编辑监听器' : '新增监听器'" v-model="dialogVisible" width="560px" :close-on-click-modal="false" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="流程模型" prop="model_id">
          <el-select v-model="form.model_id" placeholder="请选择流程模型" style="width: 100%">
            <el-option v-for="m in modelOptions" :key="m.id" :label="m.model_name" :value="m.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="事件类型" prop="event_type">
          <el-select v-model="form.event_type" style="width: 100%">
            <el-option v-for="item in eventTypes" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="动作类型" prop="action_type">
          <el-select v-model="form.action_type" style="width: 100%">
            <el-option v-for="item in actionTypes" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="回调地址" prop="callback_url">
          <el-input v-model="form.callback_url" placeholder="http://host/api/callback" :disabled="form.action_type !== 'callback'" />
        </el-form-item>
        <el-form-item label="回调参数" prop="callback_param">
          <el-input v-model="form.callback_param" type="textarea" :rows="3" placeholder='JSON 字符串，如 {"msg":"流程启动"}' />
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <el-radio-group v-model="form.status">
            <el-radio :label="0">启用</el-radio>
            <el-radio :label="1">停用</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitForm">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Refresh, Plus, Delete, Edit } from '@element-plus/icons-vue'
import request from '@/utils/request'

const eventTypes = [
  { label: '流程启动', value: 'start' },
  { label: '节点进入', value: 'enter' },
  { label: '节点完成', value: 'complete' },
  { label: '流程结束', value: 'end' },
  { label: '流程驳回', value: 'reject' }
]
const actionTypes = [
  { label: '回调接口', value: 'callback' },
  { label: '消息通知', value: 'notify' },
  { label: '修改数据', value: 'update_data' },
  { label: '写入日志', value: 'log' }
]

const loading = ref(false)
const saving = ref(false)
const rows = ref([])
const total = ref(0)
const selectedIds = ref([])
const dialogVisible = ref(false)
const formRef = ref()
const query = reactive({ page: 1, page_size: 10, model_id: '', event_type: '' })
const form = reactive({ id: 0, model_id: '', event_type: 'start', action_type: 'notify', callback_url: '', callback_param: '', status: 0 })
const modelOptions = ref([])
const rules = {
  model_id: [{ required: true, message: '请选择流程模型', trigger: 'change' }],
  event_type: [{ required: true, message: '请选择事件类型', trigger: 'change' }],
  action_type: [{ required: true, message: '请选择动作类型', trigger: 'change' }]
}

function typeName(options, value) {
  return options.find(item => item.value === value)?.label || value
}
async function getList() {
  loading.value = true
  try {
    const res = await request.get('/wf/listener/list', { params: query })
    rows.value = res.data.list
    total.value = res.data.total
  } finally {
    loading.value = false
  }
}
async function loadModels() {
  const res = await request.get('/wf/model/list', { params: { page: 1, page_size: 1000 } })
  modelOptions.value = res.data.list || []
}
function handleQuery() {
  query.page = 1
  getList()
}
function resetQuery() {
  Object.assign(query, { page: 1, model_id: '', event_type: '' })
  getList()
}
function onSelectionChange(rowsSelected) {
  selectedIds.value = rowsSelected.map(row => row.id)
}
function openCreate() {
  Object.assign(form, { id: 0, model_id: modelOptions.value[0]?.id || '', event_type: 'start', action_type: 'notify', callback_url: '', callback_param: '', status: 0 })
  dialogVisible.value = true
}
function openEdit(row) {
  Object.assign(form, {
    id: row.id, model_id: row.model_id, event_type: row.event_type, action_type: row.action_type,
    callback_url: row.callback_url || '', callback_param: row.callback_param || '', status: row.status
  })
  dialogVisible.value = true
}
async function submitForm() {
  await formRef.value.validate()
  saving.value = true
  try {
    if (form.id) {
      await request.put(`/wf/listener/update/${form.id}`, form)
      ElMessage.success('修改成功')
    } else {
      await request.post('/wf/listener/create', form)
      ElMessage.success('新增成功')
    }
    dialogVisible.value = false
    getList()
  } finally {
    saving.value = false
  }
}
async function handleDelete(row) {
  await ElMessageBox.confirm('确认删除该监听器吗？', '提示', { type: 'warning' })
  await request.delete('/wf/listener/delete', { data: { ids: [row.id] } })
  ElMessage.success('删除成功')
  getList()
}
async function handleBatchDelete() {
  await ElMessageBox.confirm(`确认删除选中的 ${selectedIds.value.length} 条监听器吗？`, '提示', { type: 'warning' })
  await request.delete('/wf/listener/delete', { data: { ids: selectedIds.value } })
  ElMessage.success('删除成功')
  getList()
}

onMounted(async () => {
  await loadModels()
  getList()
})
</script>
