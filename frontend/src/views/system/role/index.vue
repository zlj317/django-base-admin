<template>
  <div class="app-container">
    <div class="page-header">
      <div class="page-title-wrap">
        <h2>角色管理</h2>
        <div class="sub">角色权限与数据范围</div>
      </div>
    </div>
    <!-- 查询栏 -->
    <el-card shadow="never" class="search-card">
      <el-form inline @submit.prevent>
        <el-form-item label="角色名称">
          <el-input v-model="query.role_name" placeholder="请输入角色名称" clearable style="width: 180px" @keyup.enter="handleSearch" />
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
        <el-button v-perm="'system:role:create'" type="primary" :icon="Plus" @click="openCreate">新增</el-button>
        <el-button v-perm="'system:role:delete'" type="danger" plain :icon="Delete" :disabled="!selection.length" @click="handleBatchDelete">批量删除</el-button>
      </div>

      <el-table stripe empty-text="暂无数据" v-loading="loading" :data="list" @selection-change="onSelectionChange">
        <el-table-column type="selection" width="50" />
        <el-table-column label="编号" prop="id" width="70" />
        <el-table-column label="角色名称" prop="role_name" min-width="130" show-overflow-tooltip />
        <el-table-column label="权限字符" prop="role_key" min-width="130" show-overflow-tooltip />
        <el-table-column label="显示顺序" prop="role_sort" width="90" align="center" />
        <el-table-column label="数据范围" width="150" align="center">
          <template #default="{ row }">{{ dataScopeLabel(row.data_scope) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 0 ? 'success' : 'danger'" size="small">
              {{ row.status === 0 ? '正常' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="备注" prop="remark" min-width="130" show-overflow-tooltip>
          <template #default="{ row }">{{ row.remark || '-' }}</template>
        </el-table-column>
        <el-table-column label="创建时间" prop="create_time" width="170" />
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button v-perm="'system:role:update'" link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button v-perm="'system:role:assignMenus'" link type="primary" @click="openAssign(row)">分配权限</el-button>
            <el-button v-perm="'system:role:delete'" link type="danger" @click="handleDelete(row)">删除</el-button>
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
    <el-dialog v-model="formVisible" :title="form.id ? '编辑角色' : '新增角色'" width="560px" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="角色名称" prop="role_name">
          <el-input v-model.trim="form.role_name" placeholder="请输入角色名称" maxlength="30" />
        </el-form-item>
        <el-form-item label="权限字符" prop="role_key">
          <el-input v-model.trim="form.role_key" placeholder="如 admin / common" maxlength="30" />
        </el-form-item>
        <el-form-item label="显示顺序" prop="role_sort">
          <el-input-number v-model="form.role_sort" :min="0" :max="999" controls-position="right" />
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <el-radio-group v-model="form.status">
            <el-radio :value="0">正常</el-radio>
            <el-radio :value="1">停用</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="数据范围" prop="data_scope">
          <el-select v-model="form.data_scope" style="width: 100%">
            <el-option v-for="d in dataScopeOptions" :key="d.value" :label="d.label" :value="d.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注" prop="remark">
          <el-input v-model="form.remark" type="textarea" :rows="3" placeholder="请输入备注" maxlength="200" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="formVisible = false">取 消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">确 定</el-button>
      </template>
    </el-dialog>

    <!-- 分配权限弹窗 -->
    <el-dialog v-model="assignVisible" :title="`分配权限 - ${assignForm.role_name || ''}`" width="460px" destroy-on-close>
      <el-scrollbar max-height="420px">
        <el-tree
          ref="menuTreeRef"
          :data="menuTree"
          :props="{ label: 'menu_name', children: 'children' }"
          node-key="id"
          show-checkbox
          default-expand-all
          :default-checked-keys="assignForm.checkedKeys"
        />
      </el-scrollbar>
      <template #footer>
        <el-button @click="assignVisible = false">取 消</el-button>
        <el-button type="primary" :loading="saving" @click="handleAssign">保 存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Refresh, Plus, Delete } from '@element-plus/icons-vue'
import request from '@/utils/request'

const loading = ref(false)
const saving = ref(false)
const list = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const query = reactive({ role_name: '', status: null })
const selection = ref([])

const dataScopeOptions = [
  { value: 1, label: '全部数据权限' },
  { value: 2, label: '自定义数据权限' },
  { value: 3, label: '本部门数据权限' },
  { value: 4, label: '本部门及以下数据权限' },
  { value: 5, label: '仅本人数据权限' }
]

function dataScopeLabel(v) {
  const hit = dataScopeOptions.find(d => String(d.value) === String(v))
  return hit ? hit.label : '-'
}

// ---------- 列表 ----------
async function fetchList() {
  loading.value = true
  try {
    const res = await request.get('/system/role/list', {
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
  query.role_name = ''
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

// ---------- 新增/编辑 ----------
const formVisible = ref(false)
const formRef = ref()
const form = reactive({
  id: null,
  role_name: '',
  role_key: '',
  role_sort: 0,
  status: 0,
  data_scope: 1,
  remark: ''
})

const rules = {
  role_name: [{ required: true, message: '请输入角色名称', trigger: 'blur' }],
  role_key: [{ required: true, message: '请输入权限字符', trigger: 'blur' }],
  role_sort: [{ required: true, message: '请输入显示顺序', trigger: 'blur' }]
}

function openCreate() {
  form.id = null
  form.role_name = ''
  form.role_key = ''
  form.role_sort = 0
  form.status = 0
  form.data_scope = 1
  form.remark = ''
  formVisible.value = true
}

function openEdit(row) {
  form.id = row.id
  form.role_name = row.role_name
  form.role_key = row.role_key
  form.role_sort = row.role_sort
  form.status = row.status
  form.data_scope = row.data_scope
  form.remark = row.remark
  formVisible.value = true
}

async function handleSave() {
  await formRef.value.validate()
  saving.value = true
  try {
    const payload = {
      role_name: form.role_name,
      role_key: form.role_key,
      role_sort: form.role_sort,
      status: form.status,
      data_scope: form.data_scope,
      remark: form.remark
    }
    if (form.id) {
      await request.put(`/system/role/update/${form.id}`, payload)
      ElMessage.success('修改成功')
    } else {
      await request.post('/system/role/create', payload)
      ElMessage.success('新增成功')
    }
    formVisible.value = false
    fetchList()
  } finally {
    saving.value = false
  }
}

// ---------- 分配权限 ----------
const assignVisible = ref(false)
const menuTreeRef = ref()
const menuTree = ref([])
const assignForm = reactive({ id: null, role_name: '', checkedKeys: [] })

// 收集叶子节点 id（父子联动模式下仅勾选叶子，父级自动半选/全选）
function collectLeafKeys(nodes, ids, acc) {
  nodes.forEach(node => {
    if (node.children && node.children.length) {
      collectLeafKeys(node.children, ids, acc)
    } else if (ids.includes(node.id)) {
      acc.push(node.id)
    }
  })
  return acc
}

async function openAssign(row) {
  assignForm.id = row.id
  assignForm.role_name = row.role_name
  assignForm.checkedKeys = []
  if (!menuTree.value.length) {
    const res = await request.get('/system/menu/tree')
    menuTree.value = res.data || []
  }
  const res = await request.get(`/system/role/menu_ids/${row.id}`)
  const ids = (res.data && res.data.menu_ids) || []
  assignForm.checkedKeys = collectLeafKeys(menuTree.value, ids, [])
  assignVisible.value = true
}

async function handleAssign() {
  const checked = menuTreeRef.value.getCheckedKeys()
  const halfChecked = menuTreeRef.value.getHalfCheckedKeys()
  const menuIds = Array.from(new Set([...checked, ...halfChecked]))
  saving.value = true
  try {
    await request.put(`/system/role/assign_menus/${assignForm.id}`, { menu_ids: menuIds })
    ElMessage.success('分配权限成功')
    assignVisible.value = false
  } finally {
    saving.value = false
  }
}

// ---------- 删除 ----------
async function handleDelete(row) {
  await ElMessageBox.confirm(`确定删除角色「${row.role_name}」吗？`, '提示', { type: 'warning' })
  await request.delete('/system/role/delete', { data: { ids: [row.id] } })
  ElMessage.success('删除成功')
  fetchList()
}

async function handleBatchDelete() {
  await ElMessageBox.confirm(`确定删除选中的 ${selection.value.length} 个角色吗？`, '提示', { type: 'warning' })
  await request.delete('/system/role/delete', { data: { ids: selection.value.map(r => r.id) } })
  ElMessage.success('删除成功')
  fetchList()
}

onMounted(fetchList)
</script>
