<template>
  <div class="app-container">
    <div class="page-header">
      <div class="page-title-wrap">
        <h2>上传配置</h2>
        <div class="sub">上传/预览配置 · 共 {{ total }} 条</div>
      </div>
    </div>
    <el-card shadow="never" class="search-card">
      <el-form :model="query" inline @submit.prevent>
        <el-form-item label="配置键">
          <el-input v-model="query.config_key" placeholder="请输入配置键" clearable style="width: 160px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="配置类型">
          <el-select v-model="query.config_type" placeholder="全部" clearable style="width: 140px">
            <el-option label="上传" value="upload" />
            <el-option label="预览" value="preview" />
            <el-option label="存储" value="storage" />
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
            <el-button v-perm="'file:config:create'" type="primary" :icon="Plus" @click="openCreate">新增</el-button>
            <el-button v-perm="'file:config:delete'" type="danger" plain :icon="Delete" :disabled="!selection.length" @click="handleBatchDelete">批量删除</el-button>
          </div>
        </div>
      </template>
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据" @selection-change="onSelectionChange">
        <el-table-column type="selection" width="50" />
        <el-table-column label="编号" prop="id" width="70" />
        <el-table-column label="配置键" prop="config_key" min-width="140" show-overflow-tooltip />
        <el-table-column label="配置名称" prop="config_name" min-width="160" show-overflow-tooltip />
        <el-table-column label="配置值" prop="config_value" min-width="200" show-overflow-tooltip />
        <el-table-column label="配置类型" prop="config_type" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.config_type==='upload'" size="small">上传</el-tag>
            <el-tag v-else-if="row.config_type==='preview'" size="small" type="success">预览</el-tag>
            <el-tag v-else-if="row.config_type==='storage'" size="small" type="warning">存储</el-tag>
            <span v-else>{{ row.config_type }}</span>
          </template>
        </el-table-column>
        <el-table-column label="备注" prop="remark" min-width="160" show-overflow-tooltip />
        <el-table-column label="创建时间" prop="create_time" width="170" />
        <el-table-column label="操作" width="180" fixed="right" class-name="op-col">
          <template #default="{ row }">
            <el-button v-perm="'file:config:update'" link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button v-perm="'file:config:delete'" link type="danger" @click="handleDelete(row)">删除</el-button>
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
        <el-form-item label="配置键" prop="config_key">
          <el-input v-model="form.config_key" placeholder="请输入配置键" maxlength="64" />
        </el-form-item>
        <el-form-item label="配置名称" prop="config_name">
          <el-input v-model="form.config_name" placeholder="请输入配置名称" maxlength="100" />
        </el-form-item>
        <el-form-item label="配置值" prop="config_value">
          <el-input v-model="form.config_value" type="textarea" :rows="3" placeholder="请输入配置值" />
        </el-form-item>
        <el-form-item label="配置类型" prop="config_type">
          <el-select v-model="form.config_type" placeholder="请选择配置类型" style="width:100%">
            <el-option label="上传" value="upload" />
            <el-option label="预览" value="preview" />
            <el-option label="存储" value="storage" />
          </el-select>
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

const query_orig = { page: 1, page_size: 10, config_key: '', config_type: null }
const query = reactive({ ...query_orig })

const form_orig = {
  id: null, config_key: '', config_name: '', config_value: '', config_type: '', remark: ''
}
const form = reactive({ ...form_orig })

const rules = {
  config_key: [{ required: true, message: '请输入配置键', trigger: 'blur' }],
  config_name: [{ required: true, message: '请输入配置名称', trigger: 'blur' }],
  config_type: [{ required: true, message: '请选择配置类型', trigger: 'change' }]
}

function apiUrl(action) {
  const base = '/file/config'
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
  } finally {
    loading.value = false
  }
}

function handleSearch() { query.page = 1; fetchList() }
function handleReset() { Object.assign(query, query_orig); handleSearch() }
function onSelectionChange(r) { selection.value = r }

function openCreate() {
  Object.assign(form, form_orig)
  dialogTitle.value = '新增配置'
  dialogVisible.value = true
}

function openEdit(row) {
  Object.assign(form, form_orig, row)
  dialogTitle.value = '编辑配置'
  dialogVisible.value = true
}

async function submitForm() {
  await formRef.value.validate()
  saving.value = true
  try {
    if (form.id) {
      const { id, ...data } = form
      await request.put(`${apiUrl('update')}/${id}`, data)
      ElMessage.success('更新成功')
    } else {
      await request.post(apiUrl('create'), form)
      ElMessage.success('新增成功')
    }
    dialogVisible.value = false
    fetchList()
  } finally {
    saving.value = false
  }
}

async function handleDelete(row) {
  await ElMessageBox.confirm('确定删除该配置？', '提示', { type: 'warning' })
  await request.delete(apiUrl('delete'), { data: { ids: [row.id] } })
  ElMessage.success('删除成功')
  fetchList()
}

async function handleBatchDelete() {
  await ElMessageBox.confirm(`确定删除选中的 ${selection.value.length} 条配置？`, '提示', { type: 'warning' })
  await request.delete(apiUrl('delete'), { data: { ids: selection.value.map(r => r.id) } })
  ElMessage.success('批量删除成功')
  fetchList()
}

onMounted(fetchList)
</script>
