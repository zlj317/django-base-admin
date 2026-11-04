<template>
  <div class="app-container">
    <div class="page-header">
      <div class="page-title-wrap">
        <h2>编码规则管理</h2>
        <div class="sub">编号规则管理 · 共 {{ total }} 条</div>
      </div>
    </div>

    <el-card shadow="never" class="search-card">
      <el-form :model="query" inline @submit.prevent>
        <el-form-item label="规则Key">
          <el-input v-model="query.rule_key" placeholder="请输入规则Key" clearable style="width: 170px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="规则名称">
          <el-input v-model="query.rule_name" placeholder="请输入规则名称" clearable style="width: 170px" @keyup.enter="handleSearch" />
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
            <el-button type="warning" :icon="MagicStick" :disabled="!selection.length" @click="handleGenerateBatch">生成编号</el-button>
            <el-button type="danger" plain :icon="Delete" :disabled="!selection.length" @click="handleBatchDelete">批量删除</el-button>
          </div>
        </div>
      </template>
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据" @selection-change="onSelectionChange">
        <el-table-column type="index" label="序号" width="70" align="center" />
        <el-table-column type="selection" width="50" />
        <el-table-column label="规则Key" prop="rule_key" min-width="140" show-overflow-tooltip />
        <el-table-column label="规则名称" prop="rule_name" min-width="180" show-overflow-tooltip />
        <el-table-column label="前缀" prop="prefix" width="100" />
        <el-table-column label="日期格式" prop="date_format" width="110" />
        <el-table-column label="序列长度" prop="seq_length" width="90" />
        <el-table-column label="步长" prop="step" width="70" />
        <el-table-column label="分隔符" prop="separator" width="90" />
        <el-table-column label="重置方式" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.reset_type==='day'" size="small">按日</el-tag>
            <el-tag v-else-if="row.reset_type==='month'" size="small" type="success">按月</el-tag>
            <el-tag v-else-if="row.reset_type==='year'" size="small" type="warning">按年</el-tag>
            <el-tag v-else-if="row.reset_type==='none'" size="small" type="info">不重置</el-tag>
            <span v-else>{{ row.reset_type }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.status===1" size="small" type="success">启用</el-tag>
            <el-tag v-else size="small" type="info">停用</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="备注" prop="remark" min-width="150" show-overflow-tooltip />
        <el-table-column label="创建时间" prop="create_time" width="170" />
        <el-table-column label="操作" width="240" fixed="right" class-name="op-col">
          <template #default="{ row }">
            <el-button link type="warning" :icon="MagicStick" @click="handleGenerate(row)">生成编号</el-button>
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
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="规则Key" prop="rule_key">
              <el-input v-model="form.rule_key" placeholder="唯一标识" maxlength="64" :disabled="!!form.id" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="规则名称" prop="rule_name">
              <el-input v-model="form.rule_name" placeholder="请输入规则名称" maxlength="100" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="前缀" prop="prefix">
              <el-input v-model="form.prefix" placeholder="如 NO" maxlength="20" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="日期格式" prop="date_format">
              <el-select v-model="form.date_format" style="width:100%">
                <el-option label="YYYYMMDD" value="YYYYMMDD" />
                <el-option label="YYYYMM" value="YYYYMM" />
                <el-option label="YYYY" value="YYYY" />
                <el-option label="无日期" value="" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="序列长度" prop="seq_length">
              <el-input-number v-model="form.seq_length" :min="1" :max="10" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="步长" prop="step">
              <el-input-number v-model="form.step" :min="1" :max="100" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="分隔符" prop="separator">
              <el-input v-model="form.separator" placeholder="如 -" maxlength="5" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="重置方式" prop="reset_type">
              <el-select v-model="form.reset_type" style="width:100%">
                <el-option label="按日" value="day" />
                <el-option label="按月" value="month" />
                <el-option label="按年" value="year" />
                <el-option label="不重置" value="none" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="状态" prop="status">
              <el-switch v-model="form.status" :active-value="1" :inactive-value="0" active-text="启用" inactive-text="停用" />
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
import { Search, Refresh, Plus, Delete, MagicStick } from '@element-plus/icons-vue'
import request from '@/utils/request'

const loading = ref(false)
const rows = ref([])
const total = ref(0)
const selection = ref([])
const saving = ref(false)
const dialogVisible = ref(false)
const dialogTitle = ref('新增编码规则')
const formRef = ref()

const query_orig = { page: 1, page_size: 10, rule_key: '', rule_name: '', status: null }
const query = reactive({ ...query_orig })

const form_orig = {
  id: null, rule_key: '', rule_name: '', prefix: '', date_format: 'YYYYMMDD',
  seq_length: 4, step: 1, separator: '-', reset_type: 'day', status: 1, remark: ''
}
const form = reactive({ ...form_orig })

const rules = {
  rule_key: [{ required: true, message: '请输入规则Key', trigger: 'blur' }],
  rule_name: [{ required: true, message: '请输入规则名称', trigger: 'blur' }]
}

const apiBase = '/sys_no/rule'

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

function openCreate() { Object.assign(form, form_orig); dialogTitle.value = '新增编码规则'; dialogVisible.value = true }
function openEdit(row) { Object.assign(form, form_orig, row); dialogTitle.value = '编辑编码规则'; dialogVisible.value = true }

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

async function handleGenerate(row) {
  try {
    const res = await request.post(`${apiBase}/generate/${row.id}`)
    ElMessage.success(`生成编号：${res.data?.number || res.data}`)
  } catch (e) { /* handled by interceptor */ }
}

async function handleGenerateBatch() {
  for (const row of selection.value) {
    try {
      const res = await request.post(`${apiBase}/generate/${row.id}`)
      ElMessage.success(`${row.rule_name} → ${res.data?.number || res.data}`)
    } catch (e) { /* skip */ }
  }
}

async function handleDelete(row) {
  await ElMessageBox.confirm('确定删除该编码规则？', '提示', { type: 'warning' })
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
