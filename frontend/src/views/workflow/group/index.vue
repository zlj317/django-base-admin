<template>
  <div class="app-container">
    <div class="page-header">
      <div class="page-title-wrap">
        <h2>用户分组</h2>
        <div class="sub">固定审批小组管理 · 共 {{ total }} 条记录</div>
      </div>
    </div>

    <el-card shadow="never" class="search-card">
      <el-form :model="query" inline @submit.prevent>
        <el-form-item label="分组名称">
          <el-input v-model="query.group_name" placeholder="请输入分组名称" clearable style="width: 180px" @keyup.enter="handleQuery" />
        </el-form-item>
        <el-form-item label="分组编码">
          <el-input v-model="query.group_code" placeholder="请输入分组编码" clearable style="width: 180px" @keyup.enter="handleQuery" />
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
            <el-button v-perm="'wf:group:create'" type="primary" :icon="Plus" @click="openCreate">新增</el-button>
            <el-button v-perm="'wf:group:delete'" type="danger" plain :icon="Delete" :disabled="!selectedIds.length" @click="handleBatchDelete">批量删除</el-button>
          </div>
        </div>
      </template>
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据" @selection-change="onSelectionChange">
        <el-table-column type="index" label="序号" width="70" align="center" />
        <el-table-column type="selection" width="50" align="center" />
        <el-table-column label="分组名称" prop="group_name" min-width="150" show-overflow-tooltip />
        <el-table-column label="分组编码" prop="group_code" min-width="140" show-overflow-tooltip />
        <el-table-column label="成员数" prop="user_count" width="90" align="center" />
        <el-table-column label="成员" min-width="200">
          <template #default="scope">
            <el-tag v-for="name in scope.row.user_names" :key="name" size="small" class="member-tag">{{ name }}</el-tag>
            <span v-if="!scope.row.user_names?.length" class="text-muted">暂无成员</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90" align="center">
          <template #default="scope">
            <el-tag :type="scope.row.status === 0 ? 'success' : 'info'">{{ scope.row.status === 0 ? '启用' : '停用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" prop="create_time" width="170" />
        <el-table-column label="操作" width="230" align="center" fixed="right">
          <template #default="scope">
            <el-button v-perm="'wf:group:update'" link type="primary" :icon="UserFilled" @click="openMembers(scope.row)">成员</el-button>
            <el-button v-perm="'wf:group:update'" link type="primary" :icon="Edit" @click="openEdit(scope.row)">编辑</el-button>
            <el-button v-perm="'wf:group:delete'" link type="danger" :icon="Delete" @click="handleDelete(scope.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination-wrap">
        <el-pagination background layout="total, sizes, prev, pager, next, jumper"
          :total="total" v-model:current-page="query.page" v-model:page-size="query.page_size"
          :page-sizes="[10, 20, 50, 100]" @change="getList" />
      </div>
    </el-card>

    <el-dialog :title="form.id ? '编辑用户分组' : '新增用户分组'" v-model="dialogVisible" width="520px" :close-on-click-modal="false" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="分组名称" prop="group_name">
          <el-input v-model="form.group_name" placeholder="如：财务审批组" />
        </el-form-item>
        <el-form-item label="分组编码" prop="group_code">
          <el-input v-model="form.group_code" placeholder="唯一编码，如 finance_group" :disabled="!!form.id" />
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

    <el-dialog v-model="memberVisible" :title="`分组成员 · ${memberGroup.group_name}`" width="560px" :close-on-click-modal="false">
      <el-select v-model="selectedUsers" multiple filterable placeholder="请选择分组用户" style="width: 100%">
        <el-option v-for="user in userOptions" :key="user.id" :label="user.nickname ? `${user.nickname}（${user.username}）` : user.username" :value="user.id" />
      </el-select>
      <template #footer>
        <el-button @click="memberVisible = false">取消</el-button>
        <el-button type="primary" :loading="memberSaving" @click="saveMembers">保存成员</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Refresh, Plus, Delete, Edit, UserFilled } from '@element-plus/icons-vue'
import request from '@/utils/request'

const loading = ref(false)
const saving = ref(false)
const rows = ref([])
const total = ref(0)
const selectedIds = ref([])
const dialogVisible = ref(false)
const formRef = ref()
const query = reactive({ page: 1, page_size: 10, group_name: '', group_code: '' })
const form = reactive({ id: 0, group_name: '', group_code: '', status: 0, remark: '' })
const rules = {
  group_name: [{ required: true, message: '请输入分组名称', trigger: 'blur' }],
  group_code: [{ required: true, message: '请输入分组编码', trigger: 'blur' }]
}

const memberVisible = ref(false)
const memberSaving = ref(false)
const memberGroup = reactive({ id: 0, group_name: '' })
const selectedUsers = ref([])
const userOptions = ref([])

async function getList() {
  loading.value = true
  try {
    const res = await request.get('/wf/group/list', { params: query })
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
  Object.assign(query, { page: 1, group_name: '', group_code: '' })
  getList()
}
function onSelectionChange(rowsSelected) {
  selectedIds.value = rowsSelected.map(row => row.id)
}
function openCreate() {
  Object.assign(form, { id: 0, group_name: '', group_code: '', status: 0, remark: '' })
  dialogVisible.value = true
}
function openEdit(row) {
  Object.assign(form, { id: row.id, group_name: row.group_name, group_code: row.group_code, status: row.status, remark: row.remark || '' })
  dialogVisible.value = true
}
async function submitForm() {
  await formRef.value.validate()
  saving.value = true
  try {
    if (form.id) {
      await request.put(`/wf/group/update/${form.id}`, form)
      ElMessage.success('修改成功')
    } else {
      await request.post('/wf/group/create', form)
      ElMessage.success('新增成功')
    }
    dialogVisible.value = false
    getList()
  } finally {
    saving.value = false
  }
}
async function handleDelete(row) {
  await ElMessageBox.confirm(`确认删除分组「${row.group_name}」吗？`, '提示', { type: 'warning' })
  await request.delete('/wf/group/delete', { data: { ids: [row.id] } })
  ElMessage.success('删除成功')
  getList()
}
async function handleBatchDelete() {
  await ElMessageBox.confirm(`确认删除选中的 ${selectedIds.value.length} 个分组吗？`, '提示', { type: 'warning' })
  await request.delete('/wf/group/delete', { data: { ids: selectedIds.value } })
  ElMessage.success('删除成功')
  getList()
}

async function loadUserOptions() {
  const res = await request.get('/wf/option/users')
  userOptions.value = res.data || []
}
async function openMembers(row) {
  if (!userOptions.value.length) await loadUserOptions()
  memberGroup.id = row.id
  memberGroup.group_name = row.group_name
  const res = await request.get(`/wf/group/users/${row.id}`)
  selectedUsers.value = res.data.user_ids || []
  memberVisible.value = true
}
async function saveMembers() {
  memberSaving.value = true
  try {
    await request.put(`/wf/group/set_users/${memberGroup.id}`, { user_ids: selectedUsers.value })
    ElMessage.success('成员保存成功')
    memberVisible.value = false
    getList()
  } finally {
    memberSaving.value = false
  }
}

onMounted(getList)
</script>

<style scoped>
.member-tag {
  margin: 2px 6px 2px 0;
}
.text-muted {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}
</style>
