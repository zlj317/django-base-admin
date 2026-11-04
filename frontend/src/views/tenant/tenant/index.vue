<template>
  <div class="app-container">
    <div class="page-header">
      <div class="page-title-wrap">
        <h2>租户管理</h2>
        <div class="sub">多租户管理 · 共 {{ total }} 条</div>
      </div>
    </div>
    <el-card shadow="never" class="search-card">
      <el-form :model="query" inline @submit.prevent>
        <el-form-item label="租户名称">
          <el-input v-model="query.tenant_name" placeholder="请输入租户名称" clearable style="width: 170px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="租户编码">
          <el-input v-model="query.tenant_code" placeholder="请输入租户编码" clearable style="width: 170px" @keyup.enter="handleSearch" />
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
            <el-button type="primary" :icon="Plus" @click="openCreate">新建租户</el-button>
          </div>
        </div>
      </template>
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据">
        <el-table-column type="index" label="序号" width="70" align="center" />
        <el-table-column label="租户名称" prop="tenant_name" min-width="160" show-overflow-tooltip />
        <el-table-column label="租户编码" prop="tenant_code" min-width="140" show-overflow-tooltip />
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'info'" effect="light">
              {{ row.status === 1 ? '启用' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="到期时间" prop="expire_time" width="170" />
        <el-table-column label="最大用户数" prop="max_user_count" width="110" />
        <el-table-column label="最大存储(MB)" prop="max_storage_mb" width="130" />
        <el-table-column label="备注" prop="remark" min-width="140" show-overflow-tooltip />
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

    <el-dialog :title="dialogTitle" v-model="dialogVisible" width="680px" :close-on-click-modal="false" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="110px">
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="租户名称" prop="tenant_name">
              <el-input v-model="form.tenant_name" placeholder="请输入租户名称" maxlength="100" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="租户编码" prop="tenant_code">
              <el-input v-model="form.tenant_code" placeholder="唯一标识" maxlength="64" :disabled="!!form.id" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="到期时间" prop="expire_time">
              <el-date-picker v-model="form.expire_time" type="datetime" placeholder="选择到期时间" value-format="YYYY-MM-DD HH:mm:ss" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="状态" prop="status">
              <el-switch v-model="form.status" :active-value="1" :inactive-value="0" active-text="启用" inactive-text="停用" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="最大用户数" prop="max_user_count">
              <el-input-number v-model="form.max_user_count" :min="1" :max="99999" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="最大存储(MB)" prop="max_storage_mb">
              <el-input-number v-model="form.max_storage_mb" :min="1" :max="1048576" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="备注" prop="remark">
              <el-input v-model="form.remark" type="textarea" :rows="2" placeholder="请输入备注" />
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
import { Search, Refresh, Plus } from '@element-plus/icons-vue'
import request from '@/utils/request'

const loading = ref(false)
const rows = ref([])
const total = ref(0)
const saving = ref(false)
const dialogVisible = ref(false)
const dialogTitle = ref('新建租户')
const formRef = ref()

const query_orig = { page: 1, page_size: 10, tenant_name: '', tenant_code: '', status: null }
const query = reactive({ ...query_orig })

const form_orig = {
  id: null, tenant_name: '', tenant_code: '', expire_time: '',
  max_user_count: 100, max_storage_mb: 1024, status: 1, remark: ''
}
const form = reactive({ ...form_orig })

const rules = {
  tenant_name: [{ required: true, message: '请输入租户名称', trigger: 'blur' }],
  tenant_code: [{ required: true, message: '请输入租户编码', trigger: 'blur' }]
}

function apiUrl(action) {
  const base = '/tenant/tenant'
  return { list: base + '/list', create: base + '/create', update: base + '/update', delete: base + '/delete' }[action]
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

function openCreate() { Object.assign(form, form_orig); dialogTitle.value = '新建租户'; dialogVisible.value = true }
function openEdit(row) { Object.assign(form, form_orig, row); dialogTitle.value = '编辑租户'; dialogVisible.value = true }

async function submitForm() {
  await formRef.value.validate()
  saving.value = true
  try {
    if (form.id) {
      const { id, ...data } = form
      await request.put(`${apiUrl('update')}/${id}`, data); ElMessage.success('更新成功')
    } else {
      await request.post(apiUrl('create'), form); ElMessage.success('新建成功')
    }
    dialogVisible.value = false; fetchList()
  } finally { saving.value = false }
}

async function handleDelete(row) {
  await ElMessageBox.confirm(`确定删除租户「${row.tenant_name}」？`, '提示', { type: 'warning' })
  await request.delete(apiUrl('delete'), { data: { ids: [row.id] } })
  ElMessage.success('删除成功'); fetchList()
}

onMounted(fetchList)
</script>
