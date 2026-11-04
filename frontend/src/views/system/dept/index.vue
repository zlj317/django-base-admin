<template>
  <div class="app-container">
    <div class="page-header">
      <div class="page-title-wrap">
        <h2>部门管理</h2>
        <div class="sub">组织架构层级维护</div>
      </div>
    </div>
    <el-card shadow="never" class="table-card">
      <div class="toolbar">
        <el-button v-perm="'system:dept:create'" type="primary" :icon="Plus" @click="openCreate()">新增</el-button>
        <el-button plain :icon="expanded ? Minus : Expand" @click="toggleExpand">{{ expanded ? '全部折叠' : '全部展开' }}</el-button>
        <el-button :icon="Refresh" @click="fetchList">刷新</el-button>
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
        <el-table-column label="部门名称" prop="dept_name" min-width="200" />
        <el-table-column label="排序" prop="order_num" width="80" align="center" />
        <el-table-column label="负责人" prop="leader" width="120">
          <template #default="{ row }">{{ row.leader || '-' }}</template>
        </el-table-column>
        <el-table-column label="联系电话" prop="phone" width="140">
          <template #default="{ row }">{{ row.phone || '-' }}</template>
        </el-table-column>
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 0 ? 'success' : 'danger'" size="small">
              {{ row.status === 0 ? '正常' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" prop="create_time" width="170" />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="hasPerm('system:dept:create')"
              link
              type="primary"
              @click="openCreate(row)"
            >新增</el-button>
            <el-button v-perm="'system:dept:update'" link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button v-perm="'system:dept:delete'" link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新增/编辑弹窗 -->
    <el-dialog v-model="formVisible" :title="form.id ? '编辑部门' : '新增部门'" width="560px" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="上级部门" prop="parent_id">
          <el-tree-select
            v-model="form.parent_id"
            :data="parentTree"
            :props="{ label: 'dept_name', children: 'children' }"
            node-key="id"
            check-strictly
            filterable
            default-expand-all
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="部门名称" prop="dept_name">
          <el-input v-model.trim="form.dept_name" placeholder="请输入部门名称" maxlength="30" />
        </el-form-item>
        <el-form-item label="显示排序" prop="order_num">
          <el-input-number v-model="form.order_num" :min="0" :max="999" controls-position="right" />
        </el-form-item>
        <el-form-item label="负责人" prop="leader">
          <el-input v-model.trim="form.leader" placeholder="请输入负责人" maxlength="20" />
        </el-form-item>
        <el-form-item label="联系电话" prop="phone">
          <el-input v-model.trim="form.phone" placeholder="请输入联系电话" maxlength="20" />
        </el-form-item>
        <el-form-item label="状态" prop="status">
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
import { Plus, Expand, Minus, Refresh } from '@element-plus/icons-vue'
import request from '@/utils/request'
import { hasPerm } from '@/store/auth'

const loading = ref(false)
const saving = ref(false)
const list = ref([])
const expanded = ref(true)
const tableKey = ref(0)

function toggleExpand() {
  expanded.value = !expanded.value
  tableKey.value++
}

// ---------- 列表 ----------
async function fetchList() {
  loading.value = true
  try {
    const res = await request.get('/system/dept/tree')
    list.value = res.data || []
  } finally {
    loading.value = false
  }
}

// ---------- 新增/编辑 ----------
const formVisible = ref(false)
const formRef = ref()
const form = reactive({
  id: null,
  parent_id: 0,
  dept_name: '',
  order_num: 0,
  leader: '',
  phone: '',
  status: 0
})

const rules = {
  parent_id: [{ required: true, message: '请选择上级部门', trigger: 'change' }],
  dept_name: [{ required: true, message: '请输入部门名称', trigger: 'blur' }]
}

const parentTree = computed(() => [
  { id: 0, dept_name: '顶级部门', children: list.value }
])

function resetForm() {
  form.id = null
  form.parent_id = 0
  form.dept_name = ''
  form.order_num = 0
  form.leader = ''
  form.phone = ''
  form.status = 0
}

function openCreate(parent) {
  resetForm()
  if (parent) {
    form.parent_id = parent.id
  }
  formVisible.value = true
}

function openEdit(row) {
  resetForm()
  Object.assign(form, {
    id: row.id,
    parent_id: row.parent_id ?? 0,
    dept_name: row.dept_name,
    order_num: row.order_num,
    leader: row.leader || '',
    phone: row.phone || '',
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
      dept_name: form.dept_name,
      order_num: form.order_num,
      leader: form.leader,
      phone: form.phone,
      status: form.status
    }
    if (form.id) {
      await request.put(`/system/dept/update/${form.id}`, payload)
      ElMessage.success('修改成功')
    } else {
      await request.post('/system/dept/create', payload)
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
  await ElMessageBox.confirm(`确定删除部门「${row.dept_name}」吗？`, '提示', { type: 'warning' })
  await request.delete(`/system/dept/delete/${row.id}`)
  ElMessage.success('删除成功')
  fetchList()
}

onMounted(fetchList)
</script>
