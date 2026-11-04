<template>
  <div class="app-container">
    <div class="page-header">
      <div class="page-title-wrap">
        <h2>数据权限配置</h2>
        <div class="sub">数据权限规则管理 · 共 {{ total }} 条</div>
      </div>
    </div>

    <el-card shadow="never" class="search-card">
      <el-form :model="query" inline @submit.prevent>
        <el-form-item label="权限名称">
          <el-input v-model="query.permission_name" placeholder="请输入权限名称" clearable style="width: 170px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="权限类型">
          <el-select v-model="query.permission_type" placeholder="全部" clearable style="width: 130px">
            <el-option label="全部数据" value="all" />
            <el-option label="本部门" value="dept" />
            <el-option label="本部门及以下" value="dept_and_sub" />
            <el-option label="仅本人" value="self" />
            <el-option label="自定义" value="custom" />
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
            <el-button type="primary" :icon="Plus" @click="openCreate">新增</el-button>
            <el-button type="danger" plain :icon="Delete" :disabled="!selection.length" @click="handleBatchDelete">批量删除</el-button>
          </div>
        </div>
      </template>
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据" @selection-change="onSelectionChange">
        <el-table-column type="index" label="序号" width="70" align="center" />
        <el-table-column type="selection" width="50" />
        <el-table-column label="权限名称" prop="permission_name" min-width="180" show-overflow-tooltip />
        <el-table-column label="权限类型" width="120">
          <template #default="{ row }">
            <el-tag v-if="row.permission_type==='all'" size="small">全部数据</el-tag>
            <el-tag v-else-if="row.permission_type==='dept'" size="small" type="success">本部门</el-tag>
            <el-tag v-else-if="row.permission_type==='dept_and_sub'" size="small" type="warning">部门及以下</el-tag>
            <el-tag v-else-if="row.permission_type==='self'" size="small" type="info">仅本人</el-tag>
            <el-tag v-else-if="row.permission_type==='custom'" size="small" type="danger">自定义</el-tag>
            <span v-else>{{ row.permission_type }}</span>
          </template>
        </el-table-column>
        <el-table-column label="范围值" prop="scope_value" min-width="140" show-overflow-tooltip />
        <el-table-column label="SQL条件" prop="sql_condition" min-width="180" show-overflow-tooltip />
        <el-table-column label="排序" prop="sort" width="70" />
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.status===1" size="small" type="success">启用</el-tag>
            <el-tag v-else size="small" type="info">停用</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" prop="create_time" width="170" />
        <el-table-column label="操作" width="180" fixed="right" class-name="op-col">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
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
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="权限名称" prop="permission_name">
              <el-input v-model="form.permission_name" placeholder="请输入权限名称" maxlength="100" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="权限类型" prop="permission_type">
              <el-select v-model="form.permission_type" style="width:100%">
                <el-option label="全部数据" value="all" />
                <el-option label="本部门" value="dept" />
                <el-option label="本部门及以下" value="dept_and_sub" />
                <el-option label="仅本人" value="self" />
                <el-option label="自定义" value="custom" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="范围值" prop="scope_value">
              <el-input v-model="form.scope_value" placeholder="如 dept_id 列表" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="SQL条件" prop="sql_condition">
              <el-input v-model="form.sql_condition" type="textarea" :rows="3" placeholder="如 dept_id IN (...) AND create_by = #{userId}" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="排序" prop="sort">
              <el-input-number v-model="form.sort" :min="0" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="状态" prop="status">
              <el-switch v-model="form.status" :active-value="1" :inactive-value="0" active-text="启用" inactive-text="停用" />
            </el-form-item>
          </el-col>
        </el-row>
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
const dialogTitle = ref('新增数据权限')
const formRef = ref()

const query_orig = { page: 1, page_size: 10, permission_name: '', permission_type: '', status: null }
const query = reactive({ ...query_orig })

const form_orig = {
  id: null, permission_name: '', permission_type: 'all', scope_value: '', sql_condition: '', sort: 0, status: 1
}
const form = reactive({ ...form_orig })

const rules = {
  permission_name: [{ required: true, message: '请输入权限名称', trigger: 'blur' }],
  permission_type: [{ required: true, message: '请选择权限类型', trigger: 'change' }]
}

const apiBase = '/dp/permission'

async function fetchList() {
  loading.value = true
  try {
    const res = await request.get(apiBase + '/list', { params: query })
    rows.value = res.data.list || []
    total.value = res.data.total || 0
  } finally { loading.value = false }
}

function handleSearch() { query.page = 1; fetchList() }
function handleReset() { Object.assign(query, query_orig); handleSearch() }
function onSelectionChange(r) { selection.value = r }

function openCreate() { Object.assign(form, form_orig); dialogTitle.value = '新增数据权限'; dialogVisible.value = true }
function openEdit(row) { Object.assign(form, form_orig, row); dialogTitle.value = '编辑数据权限'; dialogVisible.value = true }

async function submitForm() {
  await formRef.value.validate()
  saving.value = true
  try {
    if (form.id) {
      const { id, ...data } = form
      await request.put(`${apiBase}/update/${id}`, data); ElMessage.success('更新成功')
    } else {
      await request.post(apiBase + '/create', form); ElMessage.success('新增成功')
    }
    dialogVisible.value = false; fetchList()
  } finally { saving.value = false }
}

async function handleDelete(row) {
  await ElMessageBox.confirm('确定删除该数据权限？', '提示', { type: 'warning' })
  await request.delete(apiBase + '/delete', { data: { ids: [row.id] } })
  ElMessage.success('删除成功'); fetchList()
}

async function handleBatchDelete() {
  await ElMessageBox.confirm(`确定删除选中的 ${selection.value.length} 条？`, '提示', { type: 'warning' })
  await request.delete(apiBase + '/delete', { data: { ids: selection.value.map(r => r.id) } })
  ElMessage.success('批量删除成功'); fetchList()
}

onMounted(fetchList)
</script>
