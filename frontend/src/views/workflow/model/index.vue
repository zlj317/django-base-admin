<template>
  <div class="app-container">
    <div class="page-header">
      <div class="page-title-wrap">
        <h2>流程模型</h2>
        <div class="sub">BPMN2.0 流程设计与发布 · 共 {{ total }} 条记录</div>
      </div>
    </div>

    <el-card shadow="never" class="search-card">
      <el-form :model="query" inline @submit.prevent>
        <el-form-item label="模型名称">
          <el-input v-model="query.model_name" placeholder="请输入模型名称" clearable style="width: 180px" @keyup.enter="handleQuery" />
        </el-form-item>
        <el-form-item label="流程分类">
          <el-select v-model="query.category_id" placeholder="请选择" clearable style="width: 180px">
            <el-option v-for="item in categories" :key="item.id" :label="item.name" :value="item.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="query.status" placeholder="请选择" clearable style="width: 150px">
            <el-option label="草稿" :value="0" />
            <el-option label="已发布" :value="1" />
            <el-option label="停用" :value="2" />
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
            <el-button v-perm="'wf:model:create'" type="primary" :icon="Plus" @click="openCreate">新增模型</el-button>
            <el-button v-perm="'wf:model:delete'" type="danger" plain :icon="Delete" :disabled="!selectedIds.length" @click="handleBatchDelete">批量删除</el-button>
          </div>
        </div>
      </template>
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据" @selection-change="onSelectionChange">
        <el-table-column type="selection" width="50" align="center" />
        <el-table-column label="编号" prop="id" width="70" align="center" />
        <el-table-column label="模型名称" prop="model_name" min-width="150" show-overflow-tooltip />
        <el-table-column label="模型Key" prop="model_key" min-width="130" show-overflow-tooltip />
        <el-table-column label="分类" prop="category_name" width="120" align="center" />
        <el-table-column label="绑定表单" prop="form_name" min-width="130" show-overflow-tooltip />
        <el-table-column label="版本" width="80" align="center">
          <template #default="scope">v{{ scope.row.version }}</template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center">
          <template #default="scope">
            <el-tag :type="statusType(scope.row.status)">{{ scope.row.status_name }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="实例数" prop="instance_count" width="85" align="center" />
        <el-table-column label="更新时间" prop="update_time" width="170" />
        <el-table-column label="操作" width="290" align="center" fixed="right">
          <template #default="scope">
            <el-button v-perm="'wf:model:list'" link type="primary" :icon="Share" @click="openDesign(scope.row)">设计</el-button>
            <el-button v-perm="'wf:model:publish'" link type="success" :icon="Promotion" @click="publish(scope.row)">发布</el-button>
            <el-button v-perm="'wf:model:update'" link type="primary" :icon="Edit" @click="openEdit(scope.row)">编辑</el-button>
            <el-dropdown trigger="click" @command="cmd => handleCommand(cmd, scope.row)">
              <el-button link type="primary" style="margin-left: 8px">更多<el-icon class="el-icon--right"><ArrowDown /></el-icon></el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="copy">复制模型</el-dropdown-item>
                  <el-dropdown-item command="disable" :disabled="scope.row.status !== 1">停用</el-dropdown-item>
                  <el-dropdown-item command="delete" divided>删除</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination-wrap">
        <el-pagination background layout="total, sizes, prev, pager, next, jumper"
          :total="total" v-model:current-page="query.page" v-model:page-size="query.page_size"
          :page-sizes="[10, 20, 50, 100]" @change="getList" />
      </div>
    </el-card>

    <el-dialog :title="form.id ? '编辑流程模型' : '新增流程模型'" v-model="dialogVisible" width="560px" :close-on-click-modal="false" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="模型名称" prop="model_name">
          <el-input v-model="form.model_name" placeholder="如：请假流程" />
        </el-form-item>
        <el-form-item label="模型Key" prop="model_key">
          <el-input v-model="form.model_key" placeholder="唯一标识，如 leave" :disabled="!!form.id" />
        </el-form-item>
        <el-form-item label="流程分类" prop="category_id">
          <el-select v-model="form.category_id" placeholder="请选择分类" clearable style="width: 100%">
            <el-option v-for="item in categories" :key="item.id" :label="item.name" :value="item.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="绑定表单" prop="form_id">
          <el-select v-model="form.form_id" placeholder="请选择表单" clearable style="width: 100%">
            <el-option v-for="item in forms" :key="item.id" :label="item.form_name" :value="item.id" />
          </el-select>
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
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Refresh, Plus, Delete, Edit, Share, Promotion, ArrowDown } from '@element-plus/icons-vue'
import request from '@/utils/request'

const router = useRouter()
const loading = ref(false)
const saving = ref(false)
const rows = ref([])
const total = ref(0)
const selectedIds = ref([])
const dialogVisible = ref(false)
const formRef = ref()
const categories = ref([])
const forms = ref([])
const query = reactive({ page: 1, page_size: 10, model_name: '', category_id: '', status: '' })
const form = reactive({ id: 0, model_name: '', model_key: '', category_id: '', form_id: '', remark: '' })
const rules = {
  model_name: [{ required: true, message: '请输入模型名称', trigger: 'blur' }],
  model_key: [{ required: true, message: '请输入模型Key', trigger: 'blur' }]
}

function statusType(status) {
  return { 0: 'info', 1: 'success', 2: 'danger' }[status] || 'info'
}
async function getList() {
  loading.value = true
  try {
    const res = await request.get('/wf/model/list', { params: query })
    rows.value = res.data.list
    total.value = res.data.total
  } finally {
    loading.value = false
  }
}
async function loadOptions() {
  const [cateRes, formRes] = await Promise.all([
    request.get('/wf/category/list', { params: { page: 1, page_size: 1000 } }),
    request.get('/wf/form/list', { params: { page: 1, page_size: 1000 } })
  ])
  categories.value = cateRes.data.list || []
  forms.value = formRes.data.list || []
}
function handleQuery() {
  query.page = 1
  getList()
}
function resetQuery() {
  Object.assign(query, { page: 1, model_name: '', category_id: '', status: '' })
  getList()
}
function onSelectionChange(rowsSelected) {
  selectedIds.value = rowsSelected.map(row => row.id)
}
function openCreate() {
  Object.assign(form, { id: 0, model_name: '', model_key: '', category_id: '', form_id: '', remark: '' })
  dialogVisible.value = true
}
function openEdit(row) {
  Object.assign(form, {
    id: row.id, model_name: row.model_name, model_key: row.model_key,
    category_id: row.category_id || '', form_id: row.form_id || '', remark: row.remark || ''
  })
  dialogVisible.value = true
}
async function submitForm() {
  await formRef.value.validate()
  saving.value = true
  try {
    if (form.id) {
      await request.put(`/wf/model/update/${form.id}`, form)
      ElMessage.success('修改成功')
    } else {
      await request.post('/wf/model/create', form)
      ElMessage.success('新增成功，请进入设计器绘制流程图')
    }
    dialogVisible.value = false
    getList()
  } finally {
    saving.value = false
  }
}
function openDesign(row) {
  router.push(`/workflow/design/${row.id}`)
}
async function publish(row) {
  await ElMessageBox.confirm(`确认发布「${row.model_name}」吗？发布后版本号将递增。`, '发布确认', { type: 'warning' })
  const res = await request.post(`/wf/model/publish/${row.id}`)
  ElMessage.success(`发布成功，当前版本 v${res.data.version}`)
  getList()
}
async function handleCommand(command, row) {
  if (command === 'copy') {
    await request.post(`/wf/model/copy/${row.id}`)
    ElMessage.success('复制成功')
    getList()
  } else if (command === 'disable') {
    await ElMessageBox.confirm('停用后新发起将不可选择该流程，确认停用吗？', '提示', { type: 'warning' })
    await request.post(`/wf/model/disable/${row.id}`)
    ElMessage.success('已停用')
    getList()
  } else if (command === 'delete') {
    await handleDelete(row)
  }
}
async function handleDelete(row) {
  await ElMessageBox.confirm(`确认删除模型「${row.model_name}」吗？`, '提示', { type: 'warning' })
  await request.delete('/wf/model/delete', { data: { ids: [row.id] } })
  ElMessage.success('删除成功')
  getList()
}
async function handleBatchDelete() {
  await ElMessageBox.confirm(`确认删除选中的 ${selectedIds.value.length} 个模型吗？`, '提示', { type: 'warning' })
  await request.delete('/wf/model/delete', { data: { ids: selectedIds.value } })
  ElMessage.success('删除成功')
  getList()
}

onMounted(async () => {
  await loadOptions()
  getList()
})
</script>
