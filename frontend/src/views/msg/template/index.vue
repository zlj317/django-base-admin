<template>
  <div class="app-container">
    <div class="page-header">
      <div class="page-title-wrap">
        <h2>消息模板</h2>
        <div class="sub">模板管理 · 共 {{ total }} 条</div>
      </div>
    </div>
    <el-card shadow="never" class="search-card">
      <el-form :model="query" inline @submit.prevent>
        <el-form-item label="模板编码">
          <el-input v-model="query.template_code" placeholder="请输入编码" clearable style="width: 160px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="消息类型">
          <el-select v-model="query.msg_type" placeholder="全部" clearable style="width: 130px">
            <el-option label="待办" value="todo" />
            <el-option label="已办" value="done" />
            <el-option label="抄送" value="cc" />
            <el-option label="系统" value="system" />
            <el-option label="报表" value="report" />
            <el-option label="告警" value="alarm" />
            <el-option label="通知" value="notice" />
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
            <el-button v-perm="'msg:template:create'" type="primary" :icon="Plus" @click="openCreate">新增</el-button>
            <el-button v-perm="'msg:template:delete'" type="danger" plain :icon="Delete" :disabled="!selection.length" @click="handleBatchDelete">批量删除</el-button>
          </div>
        </div>
      </template>
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据" @selection-change="onSelectionChange">
        <el-table-column type="selection" width="50" />
        <el-table-column label="编号" prop="id" width="70" />
        <el-table-column label="模板编码" prop="template_code" min-width="140" show-overflow-tooltip />
        <el-table-column label="模板名称" prop="template_name" min-width="150" show-overflow-tooltip />
        <el-table-column label="消息类型" prop="msg_type" width="90" />
        <el-table-column label="模板内容" prop="template_content" min-width="220" show-overflow-tooltip />
        <el-table-column label="渠道" prop="channel" width="100" />
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-switch v-model="row.status" :active-value="1" :inactive-value="0" v-perm="'msg:template:update'" @change="handleStatusChange(row)" />
          </template>
        </el-table-column>
        <el-table-column label="创建时间" prop="create_time" width="170" />
        <el-table-column label="操作" width="180" fixed="right" class-name="op-col">
          <template #default="{ row }">
            <el-button v-perm="'msg:template:update'" link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button v-perm="'msg:template:delete'" link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination-wrap">
        <el-pagination background layout="total, sizes, prev, pager, next, jumper"
          :total="total" v-model:current-page="query.page" v-model:page-size="query.page_size"
          :page-sizes="[10, 20, 50, 100]" @change="fetchList" />
      </div>
    </el-card>

    <el-dialog :title="dialogTitle" v-model="dialogVisible" width="680px" :close-on-click-modal="false" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="110px">
        <el-form-item label="模板编码" prop="template_code">
          <el-input v-model="form.template_code" placeholder="请输入模板编码" maxlength="64" :disabled="!!form.id" />
        </el-form-item>
        <el-form-item label="模板名称" prop="template_name">
          <el-input v-model="form.template_name" placeholder="请输入模板名称" maxlength="100" />
        </el-form-item>
        <el-form-item label="消息类型" prop="msg_type">
          <el-select v-model="form.msg_type" placeholder="请选择消息类型" style="width:100%">
            <el-option label="待办" value="todo" />
            <el-option label="已办" value="done" />
            <el-option label="抄送" value="cc" />
            <el-option label="系统" value="system" />
            <el-option label="报表" value="report" />
            <el-option label="告警" value="alarm" />
            <el-option label="通知" value="notice" />
          </el-select>
        </el-form-item>
        <el-form-item label="模板内容" prop="template_content">
          <el-input v-model="form.template_content" type="textarea" :rows="4" placeholder="请输入模板内容，可用 ${变量} 占位" />
        </el-form-item>
        <el-form-item label="发送渠道" prop="channel">
          <el-select v-model="form.channel" placeholder="请选择渠道" style="width:100%">
            <el-option label="站内信" value="site" />
            <el-option label="短信" value="sms" />
            <el-option label="邮件" value="email" />
          </el-select>
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

const query_orig = { page: 1, page_size: 10, template_code: '', msg_type: null, status: null }
const query = reactive({ ...query_orig })

const form_orig = {
  id: null, template_code: '', template_name: '', msg_type: '', template_content: '',
  channel: '', status: 1, remark: ''
}
const form = reactive({ ...form_orig })

const rules = {
  template_code: [{ required: true, message: '请输入模板编码', trigger: 'blur' }],
  template_name: [{ required: true, message: '请输入模板名称', trigger: 'blur' }],
  msg_type: [{ required: true, message: '请选择消息类型', trigger: 'change' }],
  template_content: [{ required: true, message: '请输入模板内容', trigger: 'blur' }],
  channel: [{ required: true, message: '请选择发送渠道', trigger: 'change' }]
}

function apiUrl(action) {
  const base = '/msg/template'
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

async function handleStatusChange(row) {
  await request.put(`/msg/template/status/${row.id}`, { status: row.status })
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

onMounted(fetchList)
</script>
