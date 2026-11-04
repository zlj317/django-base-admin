<template>
  <div class="app-container">
    <div class="page-header">
      <div class="page-title-wrap">
        <h2>菜单管理</h2>
        <div class="sub">目录、菜单与按钮权限</div>
      </div>
    </div>
    <!-- 查询栏 -->
    <el-card shadow="never" class="search-card">
      <el-form inline @submit.prevent>
        <el-form-item label="菜单名称">
          <el-input v-model="query.menu_name" placeholder="请输入菜单名称" clearable style="width: 180px" @keyup.enter="fetchList" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="query.status" placeholder="全部" clearable style="width: 120px">
            <el-option label="正常" :value="0" />
            <el-option label="停用" :value="1" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="fetchList">查询</el-button>
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="table-card">
      <div class="toolbar">
        <el-button v-perm="'system:menu:create'" type="primary" :icon="Plus" @click="openCreate()">新增</el-button>
        <el-button plain :icon="expanded ? Minus : Expand" @click="toggleExpand">{{ expanded ? '全部折叠' : '全部展开' }}</el-button>
      </div>

      <el-table
        :key="tableKey"
        v-loading="loading"
        :data="list"
        row-key="id"
        :tree-props="{ children: 'children' }"
        :default-expand-all="expanded"
      >
        <el-table-column type="index" label="序号" width="70" align="center" />
        <el-table-column label="菜单名称" prop="menu_name" min-width="180" />
        <el-table-column label="图标" width="70" align="center">
          <template #default="{ row }">
            <el-icon v-if="resolveIcon(row.icon)" :size="16"><component :is="resolveIcon(row.icon)" /></el-icon>
          </template>
        </el-table-column>
        <el-table-column label="类型" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="typeTag(row.menu_type)" size="small">{{ typeLabel(row.menu_type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="路由地址" prop="path" min-width="120" show-overflow-tooltip />
        <el-table-column label="组件路径" prop="component" min-width="160" show-overflow-tooltip />
        <el-table-column label="权限标识" prop="perms" min-width="160" show-overflow-tooltip />
        <el-table-column label="排序" prop="order_num" width="70" align="center" />
        <el-table-column label="可见" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="String(row.visible) === '1' ? 'info' : 'success'" size="small">
              {{ String(row.visible) === '1' ? '隐藏' : '显示' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 0 ? 'success' : 'danger'" size="small">
              {{ row.status === 0 ? '正常' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="row.menu_type !== 'F' && hasPerm('system:menu:create')"
              link
              type="primary"
              @click="openCreate(row)"
            >新增</el-button>
            <el-button v-perm="'system:menu:update'" link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button v-perm="'system:menu:delete'" link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新增/编辑弹窗 -->
    <el-dialog v-model="formVisible" :title="form.id ? '编辑菜单' : '新增菜单'" width="600px" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="菜单类型" prop="menu_type">
          <el-radio-group v-model="form.menu_type">
            <el-radio-button value="M">目录</el-radio-button>
            <el-radio-button value="C">菜单</el-radio-button>
            <el-radio-button value="F">按钮</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="上级菜单" prop="parent_id">
          <el-tree-select
            v-model="form.parent_id"
            :data="parentTree"
            :props="{ label: 'menu_name', children: 'children' }"
            node-key="id"
            check-strictly
            filterable
            default-expand-all
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="菜单名称" prop="menu_name">
          <el-input v-model.trim="form.menu_name" placeholder="请输入菜单名称" maxlength="30" />
        </el-form-item>
        <el-form-item v-if="form.menu_type !== 'F'" label="图标" prop="icon">
          <el-input v-model.trim="form.icon" placeholder="Element Plus 图标名，如 User / Setting" clearable>
            <template #append>
              <el-icon v-if="iconComp"><component :is="iconComp" /></el-icon>
            </template>
          </el-input>
        </el-form-item>
        <el-form-item v-if="form.menu_type !== 'F'" label="路由地址" prop="path">
          <el-input v-model.trim="form.path" placeholder="如 system / user" />
        </el-form-item>
        <el-form-item v-if="form.menu_type === 'C'" label="组件路径" prop="component">
          <el-input v-model.trim="form.component" placeholder="相对 src/views，如 system/user/index" />
        </el-form-item>
        <el-form-item v-if="form.menu_type !== 'M'" label="权限标识" prop="perms">
          <el-input v-model.trim="form.perms" placeholder="如 system:user:list" />
        </el-form-item>
        <el-form-item label="显示排序" prop="order_num">
          <el-input-number v-model="form.order_num" :min="0" :max="999" controls-position="right" />
        </el-form-item>
        <el-form-item v-if="form.menu_type !== 'F'" label="是否显示" prop="visible">
          <el-radio-group v-model="form.visible">
            <el-radio :value="0">显示</el-radio>
            <el-radio :value="1">隐藏</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="form.menu_type !== 'F'" label="菜单状态" prop="status">
          <el-radio-group v-model="form.status">
            <el-radio :value="0">正常</el-radio>
            <el-radio :value="1">停用</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="formVisible = false">取 消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">确 定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Refresh, Plus, Expand, Minus } from '@element-plus/icons-vue'
import request from '@/utils/request'
import { resolveIcon } from '@/utils/icon'
import { hasPerm } from '@/store/auth'

const loading = ref(false)
const saving = ref(false)
const list = ref([])
const query = reactive({ menu_name: '', status: null })
const expanded = ref(false)
const tableKey = ref(0)

function typeLabel(t) {
  return t === 'M' ? '目录' : t === 'C' ? '菜单' : '按钮'
}
function typeTag(t) {
  return t === 'M' ? 'warning' : t === 'C' ? 'success' : 'info'
}

function toggleExpand() {
  expanded.value = !expanded.value
  tableKey.value++
}

// ---------- 列表 ----------
async function fetchList() {
  loading.value = true
  try {
    const res = await request.get('/system/menu/tree', { params: { ...query } })
    list.value = res.data || []
  } finally {
    loading.value = false
  }
}

function handleReset() {
  query.menu_name = ''
  query.status = null
  fetchList()
}

// ---------- 新增/编辑 ----------
const formVisible = ref(false)
const formRef = ref()
const form = reactive({
  id: null,
  parent_id: 0,
  menu_type: 'M',
  menu_name: '',
  icon: '',
  path: '',
  component: '',
  perms: '',
  order_num: 0,
  visible: 0,
  status: 0
})

const validatePath = (rule, value, callback) => {
  if (form.menu_type !== 'F' && !value) {
    return callback(new Error('请输入路由地址'))
  }
  callback()
}

const rules = {
  menu_type: [{ required: true, message: '请选择菜单类型', trigger: 'change' }],
  parent_id: [{ required: true, message: '请选择上级菜单', trigger: 'change' }],
  menu_name: [{ required: true, message: '请输入菜单名称', trigger: 'blur' }],
  path: [{ validator: validatePath, trigger: 'blur' }]
}

// 上级菜单树（顶部加“根目录”）
const parentTree = computed(() => [
  { id: 0, menu_name: '根目录', children: list.value }
])

const iconComp = computed(() => resolveIcon(form.icon))

function resetForm() {
  form.id = null
  form.parent_id = 0
  form.menu_type = 'M'
  form.menu_name = ''
  form.icon = ''
  form.path = ''
  form.component = ''
  form.perms = ''
  form.order_num = 0
  form.visible = 0
  form.status = 0
}

function openCreate(parent) {
  resetForm()
  if (parent) {
    form.parent_id = parent.id
    form.menu_type = parent.menu_type === 'M' ? 'C' : 'F'
  }
  formVisible.value = true
}

function openEdit(row) {
  resetForm()
  Object.assign(form, {
    id: row.id,
    parent_id: row.parent_id ?? 0,
    menu_type: row.menu_type,
    menu_name: row.menu_name,
    icon: row.icon || '',
    path: row.path || '',
    component: row.component || '',
    perms: row.perms || '',
    order_num: row.order_num,
    visible: row.visible,
    status: row.status
  })
  formVisible.value = true
}

async function handleSave() {
  await formRef.value.validate()
  saving.value = true
  try {
    const payload = {
      parent_id: form.parent_id,
      menu_type: form.menu_type,
      menu_name: form.menu_name,
      icon: form.icon,
      path: form.path,
      component: form.component,
      perms: form.perms,
      order_num: form.order_num,
      visible: form.visible,
      status: form.status
    }
    if (form.id) {
      await request.put(`/system/menu/update/${form.id}`, payload)
      ElMessage.success('修改成功')
    } else {
      await request.post('/system/menu/create', payload)
      ElMessage.success('新增成功')
    }
    formVisible.value = false
    fetchList()
  } finally {
    saving.value = false
  }
}

// ---------- 删除 ----------
async function handleDelete(row) {
  await ElMessageBox.confirm(`确定删除菜单「${row.menu_name}」吗？`, '提示', { type: 'warning' })
  await request.delete(`/system/menu/delete/${row.id}`)
  ElMessage.success('删除成功')
  fetchList()
}

onMounted(fetchList)
</script>
