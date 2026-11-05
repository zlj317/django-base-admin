<template>
  <div class="app-container">
    <div class="page-header">
      <div class="page-title-wrap">
        <h2>用户管理</h2>
        <div class="sub">账号维护与角色分配</div>
      </div>
    </div>
    <!-- 查询栏 -->
    <el-card shadow="never" class="search-card">
      <el-form inline @submit.prevent>
        <el-form-item label="用户名">
          <el-input v-model="query.username" placeholder="请输入用户名" clearable style="width: 170px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="昵称">
          <el-input v-model="query.nickname" placeholder="请输入昵称" clearable style="width: 170px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="手机号">
          <el-input v-model="query.phone" placeholder="请输入手机号" clearable style="width: 170px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="query.status" placeholder="全部" clearable style="width: 120px">
            <el-option label="正常" :value="0" />
            <el-option label="停用" :value="1" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="table-card">
      <div class="toolbar">
        <el-button v-perm="'system:user:create'" type="primary" :icon="Plus" @click="openCreate">新增</el-button>
        <el-button v-perm="'system:user:delete'" type="danger" plain :icon="Delete" :disabled="!selection.length" @click="handleBatchDelete">批量删除</el-button>
      </div>

      <el-table stripe empty-text="暂无数据" v-loading="loading" :data="list" @selection-change="onSelectionChange">
        <el-table-column type="index" label="序号" width="70" align="center" />
        <el-table-column type="selection" width="50" />
        <el-table-column label="用户名" prop="username" min-width="110" show-overflow-tooltip />
        <el-table-column label="昵称" prop="nickname" min-width="110" show-overflow-tooltip />
        <el-table-column label="部门" prop="dept_name" min-width="120" show-overflow-tooltip>
          <template #default="{ row }">{{ row.dept_name || '-' }}</template>
        </el-table-column>
        <el-table-column label="手机号" prop="phone" width="130">
          <template #default="{ row }">{{ row.phone || '-' }}</template>
        </el-table-column>
        <el-table-column label="角色" min-width="150">
          <template #default="{ row }">
            <template v-if="row.roles && row.roles.length">
              <el-tag v-for="r in row.roles" :key="r.id" size="small" class="mr4">{{ r.role_name }}</el-tag>
            </template>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tooltip :disabled="row.id !== auth.user.id" content="不能修改自己的状态" placement="top">
              <el-switch
                v-model="row.status"
                :active-value="0"
                :inactive-value="1"
                :disabled="row.id === auth.user.id"
                v-perm="'system:user:update'"
                @change="handleStatusChange(row)"
              />
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" prop="create_time" width="170" />
        <el-table-column label="操作" width="310" fixed="right" class-name="op-col">
          <template #default="{ row }">
            <el-button v-perm="'system:user:update'" link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button v-perm="'system:user:resetPwd'" link type="warning" @click="openResetPwd(row)">重置密码</el-button>
            <el-button v-perm="'system:user:assignRoles'" link type="primary" @click="openAssign(row)">分配角色</el-button>
            <el-button v-perm="'system:user:delete'" link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="fetchList"
        />
      </div>
    </el-card>

    <!-- 新增/编辑弹窗 -->
    <el-dialog v-model="formVisible" :title="form.id ? '编辑用户' : '新增用户'" width="640px" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="用户名" prop="username">
              <el-input v-model.trim="form.username" placeholder="请输入用户名" :disabled="!!form.id" maxlength="30" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="昵称" prop="nickname">
              <el-input v-model.trim="form.nickname" placeholder="请输入昵称" maxlength="30" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="所属部门" prop="dept_id">
              <el-tree-select
                v-model="form.dept_id"
                :data="deptTree"
                :props="{ label: 'dept_name', children: 'children' }"
                node-key="id"
                check-strictly
                clearable
                filterable
                placeholder="请选择部门"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="手机号" prop="phone">
              <el-input v-model.trim="form.phone" placeholder="请输入手机号" maxlength="11" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="邮箱" prop="email">
              <el-input v-model.trim="form.email" placeholder="请输入邮箱" maxlength="50" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="状态" prop="status">
              <el-radio-group v-model="form.status">
                <el-radio :value="0">正常</el-radio>
                <el-radio :value="1">停用</el-radio>
              </el-radio-group>
            </el-form-item>
          </el-col>
          <el-col v-if="!form.id" :span="12">
            <el-form-item label="初始密码" prop="password">
              <el-input v-model.trim="form.password" type="password" show-password placeholder="请输入初始密码" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="所属角色" prop="role_ids">
              <el-select v-model="form.role_ids" multiple filterable placeholder="请选择角色" style="width: 100%">
                <el-option v-for="r in roleOptions" :key="r.id" :label="r.role_name" :value="r.id" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="formVisible = false">取 消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">确 定</el-button>
      </template>
    </el-dialog>

    <!-- 重置密码弹窗 -->
    <el-dialog v-model="pwdVisible" title="重置密码" width="440px" destroy-on-close>
      <el-form ref="pwdFormRef" :model="pwdForm" :rules="pwdRules" label-width="80px">
        <el-form-item label="用户名">
          <el-input :model-value="pwdForm.username" disabled />
        </el-form-item>
        <el-form-item label="新密码" prop="password">
          <el-input v-model.trim="pwdForm.password" type="password" show-password placeholder="请输入新密码（不少于6位）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="pwdVisible = false">取 消</el-button>
        <el-button type="primary" :loading="saving" @click="handleResetPwd">确 定</el-button>
      </template>
    </el-dialog>

    <!-- 分配角色弹窗 -->
    <el-dialog v-model="assignVisible" :title="`分配角色 - ${assignForm.username || ''}`" width="440px" destroy-on-close>
      <el-checkbox-group v-model="assignForm.role_ids" class="role-checks">
        <el-checkbox v-for="r in roleOptions" :key="r.id" :value="r.id">{{ r.role_name }}</el-checkbox>
      </el-checkbox-group>
      <template #footer>
        <el-button @click="assignVisible = false">取 消</el-button>
        <el-button type="primary" :loading="saving" @click="handleAssign">确 定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Refresh, Plus, Delete } from '@element-plus/icons-vue'
import { auth } from '@/store/auth'
import request from '@/utils/request'

const loading = ref(false)
const saving = ref(false)
const list = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const query = reactive({ username: '', nickname: '', phone: '', status: null })
const selection = ref([])

const deptTree = ref([])
const roleOptions = ref([])

// ---------- 列表 ----------
async function fetchList() {
  loading.value = true
  try {
    const res = await request.get('/system/user/list', {
      params: { page: page.value, page_size: pageSize.value, ...query }
    })
    list.value = res.data.list || []
    total.value = res.data.total || 0
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  page.value = 1
  fetchList()
}

function handleReset() {
  query.username = ''
  query.nickname = ''
  query.phone = ''
  query.status = null
  handleSearch()
}

function handleSizeChange() {
  page.value = 1
  fetchList()
}

function onSelectionChange(rows) {
  selection.value = rows
}

// ---------- 基础数据 ----------
async function loadDeptTree() {
  const res = await request.get('/system/dept/tree')
  deptTree.value = res.data || []
}

async function loadRoleOptions() {
  const res = await request.get('/system/role/list', { params: { page: 1, page_size: 100 } })
  roleOptions.value = res.data.list || []
}

// ---------- 新增/编辑 ----------
const formVisible = ref(false)
const formRef = ref()
const form = reactive({
  id: null,
  username: '',
  nickname: '',
  phone: '',
  email: '',
  dept_id: null,
  status: 0,
  password: '',
  role_ids: []
})

const validatePhone = (rule, value, callback) => {
  if (value && !/^1[3-9]\d{9}$/.test(value)) {
    return callback(new Error('手机号格式不正确'))
  }
  callback()
}

const validateEmail = (rule, value, callback) => {
  if (value && !/^[\w.-]+@[\w-]+(\.[\w-]+)+$/.test(value)) {
    return callback(new Error('邮箱格式不正确'))
  }
  callback()
}

const rules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 2, max: 30, message: '长度 2 到 30 个字符', trigger: 'blur' }
  ],
  nickname: [{ required: true, message: '请输入昵称', trigger: 'blur' }],
  password: [
    { required: true, message: '请输入初始密码', trigger: 'blur' },
    { min: 6, max: 32, message: '密码长度 6 到 32 位', trigger: 'blur' }
  ],
  phone: [{ validator: validatePhone, trigger: 'blur' }],
  email: [{ validator: validateEmail, trigger: 'blur' }]
}

function resetForm() {
  form.id = null
  form.username = ''
  form.nickname = ''
  form.phone = ''
  form.email = ''
  form.dept_id = null
  form.status = 0
  form.password = ''
  form.role_ids = []
}

function openCreate() {
  resetForm()
  formVisible.value = true
}

async function openEdit(row) {
  resetForm()
  const res = await request.get(`/system/user/${row.id}`)
  const detail = res.data || {}
  Object.assign(form, {
    id: detail.id,
    username: detail.username,
    nickname: detail.nickname,
    phone: detail.phone,
    email: detail.email,
    dept_id: detail.dept_id ?? null,
    status: detail.status,
    password: '',
    role_ids: detail.role_ids || []
  })
  formVisible.value = true
}

async function handleSave() {
  await formRef.value.validate()
  saving.value = true
  try {
    if (form.id) {
      const { id, username, nickname, phone, email, dept_id, status, role_ids } = form
      await request.put(`/system/user/update/${id}`, {
        username, nickname, phone, email, dept_id, status, role_ids
      })
      ElMessage.success('修改成功')
    } else {
      const { username, nickname, phone, email, dept_id, status, password, role_ids } = form
      await request.post('/system/user/create', {
        username, nickname, phone, email, dept_id, status, password, role_ids
      })
      ElMessage.success('新增成功')
    }
    formVisible.value = false
    fetchList()
  } finally {
    saving.value = false
  }
}

// ---------- 重置密码 ----------
const pwdVisible = ref(false)
const pwdFormRef = ref()
const pwdForm = reactive({ id: null, username: '', password: '' })
const pwdRules = {
  password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, max: 32, message: '密码长度 6 到 32 位', trigger: 'blur' }
  ]
}

function openResetPwd(row) {
  pwdForm.id = row.id
  pwdForm.username = row.username
  pwdForm.password = ''
  pwdVisible.value = true
}

async function handleResetPwd() {
  await pwdFormRef.value.validate()
  saving.value = true
  try {
    await request.put(`/system/user/reset_pwd/${pwdForm.id}`, { password: pwdForm.password })
    ElMessage.success('密码重置成功')
    pwdVisible.value = false
  } finally {
    saving.value = false
  }
}

// ---------- 分配角色 ----------
const assignVisible = ref(false)
const assignForm = reactive({ id: null, username: '', role_ids: [] })

function openAssign(row) {
  assignForm.id = row.id
  assignForm.username = row.username
  assignForm.role_ids = (row.roles || []).map(r => r.id)
  assignVisible.value = true
}

async function handleAssign() {
  saving.value = true
  try {
    await request.put(`/system/user/assign_roles/${assignForm.id}`, { role_ids: assignForm.role_ids })
    ElMessage.success('分配角色成功')
    assignVisible.value = false
    fetchList()
  } finally {
    saving.value = false
  }
}

// ---------- 状态/删除 ----------
async function handleStatusChange(row) {
  const oldVal = row.status === 0 ? 1 : 0
  try {
    await request.put(`/system/user/status/${row.id}`, { status: row.status })
    ElMessage.success(row.status === 0 ? '已启用' : '已停用')
  } catch (e) {
    row.status = oldVal
  }
}

async function handleDelete(row) {
  await ElMessageBox.confirm(`确定删除用户「${row.username}」吗？`, '提示', { type: 'warning' })
  await request.delete('/system/user/delete', { data: { ids: [row.id] } })
  ElMessage.success('删除成功')
  fetchList()
}

async function handleBatchDelete() {
  await ElMessageBox.confirm(`确定删除选中的 ${selection.value.length} 个用户吗？`, '提示', { type: 'warning' })
  await request.delete('/system/user/delete', { data: { ids: selection.value.map(r => r.id) } })
  ElMessage.success('删除成功')
  fetchList()
}

onMounted(() => {
  fetchList()
  loadDeptTree()
  loadRoleOptions()
})
</script>

<style scoped>
.role-checks {
  display: flex;
  flex-direction: column;
}

:deep(.op-col .cell) {
  white-space: nowrap;
}
</style>
