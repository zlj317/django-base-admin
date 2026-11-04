<template>
  <div class="app-container">
    <div class="page-header">
      <div class="page-title-wrap">
        <h2>打印模板管理</h2>
        <div class="sub">打印模板管理 · 共 {{ total }} 条</div>
      </div>
    </div>

    <el-card shadow="never" class="search-card">
      <el-form :model="query" inline @submit.prevent>
        <el-form-item label="模板名称">
          <el-input v-model="query.template_name" placeholder="请输入模板名称" clearable style="width: 170px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="模板Key">
          <el-input v-model="query.template_key" placeholder="请输入模板Key" clearable style="width: 170px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="业务类型">
          <el-input v-model="query.biz_type" placeholder="请输入业务类型" clearable style="width: 130px" @keyup.enter="handleSearch" />
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
        <el-table-column label="模板名称" prop="template_name" min-width="180" show-overflow-tooltip />
        <el-table-column label="模板Key" prop="template_key" min-width="140" show-overflow-tooltip />
        <el-table-column label="业务类型" prop="biz_type" width="120" />
        <el-table-column label="纸张尺寸" prop="paper_size" width="100" />
        <el-table-column label="默认" width="70" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.is_default===1" size="small" type="warning">默认</el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80" align="center">
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

    <el-dialog :title="dialogTitle" v-model="dialogVisible" width="760px" :close-on-click-modal="false" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="模板名称" prop="template_name">
              <el-input v-model="form.template_name" placeholder="请输入模板名称" maxlength="100" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="模板Key" prop="template_key">
              <el-input v-model="form.template_key" placeholder="唯一标识" maxlength="64" :disabled="!!form.id" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="业务类型" prop="biz_type">
              <el-input v-model="form.biz_type" placeholder="如 order" maxlength="64" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="纸张尺寸" prop="paper_size">
              <el-select v-model="form.paper_size" style="width:100%">
                <el-option label="A4" value="A4" />
                <el-option label="A5" value="A5" />
                <el-option label="B5" value="B5" />
                <el-option label="自定义" value="custom" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="是否默认" prop="is_default">
              <el-switch v-model="form.is_default" :active-value="1" :inactive-value="0" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="状态" prop="status">
              <el-switch v-model="form.status" :active-value="1" :inactive-value="0" active-text="启用" inactive-text="停用" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="HTML内容" prop="html_content">
              <el-input v-model="form.html_content" type="textarea" :rows="10" placeholder="请输入打印模板HTML内容" />
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
import { Search, Refresh, Plus, Delete } from '@element-plus/icons-vue'
import request from '@/utils/request'

const loading = ref(false)
const rows = ref([])
const total = ref(0)
const selection = ref([])
const saving = ref(false)
const dialogVisible = ref(false)
const dialogTitle = ref('新增打印模板')
const formRef = ref()

const query_orig = { page: 1, page_size: 10, template_name: '', template_key: '', biz_type: '' }
const query = reactive({ ...query_orig })

const form_orig = {
  id: null, template_name: '', template_key: '', biz_type: '', paper_size: 'A4',
  is_default: 0, status: 1, html_content: '', remark: ''
}
const form = reactive({ ...form_orig })

const rules = {
  template_name: [{ required: true, message: '请输入模板名称', trigger: 'blur' }],
  template_key: [{ required: true, message: '请输入模板Key', trigger: 'blur' }],
  html_content: [{ required: true, message: '请输入HTML内容', trigger: 'blur' }]
}

const apiBase = '/imprint/print'

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

function openCreate() { Object.assign(form, form_orig); dialogTitle.value = '新增打印模板'; dialogVisible.value = true }
function openEdit(row) { Object.assign(form, form_orig, row); dialogTitle.value = '编辑打印模板'; dialogVisible.value = true }

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
  await ElMessageBox.confirm('确定删除该打印模板？', '提示', { type: 'warning' })
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
