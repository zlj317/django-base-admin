<template>
  <div class="app-container">
    <div class="page-header">
      <div class="page-title-wrap">
        <h2>脱敏规则配置</h2>
        <div class="sub">数据脱敏规则管理 · 共 {{ total }} 条</div>
      </div>
    </div>

    <el-card shadow="never" class="search-card">
      <el-form :model="query" inline @submit.prevent>
        <el-form-item label="规则名称">
          <el-input v-model="query.rule_name" placeholder="请输入规则名称" clearable style="width: 170px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="规则类型">
          <el-select v-model="query.rule_type" placeholder="全部" clearable style="width: 130px">
            <el-option label="手机号" value="phone" />
            <el-option label="身份证" value="id_card" />
            <el-option label="邮箱" value="email" />
            <el-option label="姓名" value="name" />
            <el-option label="银行卡" value="bank_card" />
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
        <el-table-column label="规则名称" prop="rule_name" min-width="180" show-overflow-tooltip />
        <el-table-column label="规则类型" width="110">
          <template #default="{ row }">
            <el-tag v-if="row.rule_type==='phone'" size="small">手机号</el-tag>
            <el-tag v-else-if="row.rule_type==='id_card'" size="small" type="success">身份证</el-tag>
            <el-tag v-else-if="row.rule_type==='email'" size="small" type="warning">邮箱</el-tag>
            <el-tag v-else-if="row.rule_type==='name'" size="small" type="info">姓名</el-tag>
            <el-tag v-else-if="row.rule_type==='bank_card'" size="small" type="danger">银行卡</el-tag>
            <el-tag v-else-if="row.rule_type==='custom'" size="small">自定义</el-tag>
            <span v-else>{{ row.rule_type }}</span>
          </template>
        </el-table-column>
        <el-table-column label="掩码样式" prop="mask_style" min-width="140" show-overflow-tooltip />
        <el-table-column label="正则" prop="regular" min-width="180" show-overflow-tooltip />
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

    <el-dialog :title="dialogTitle" v-model="dialogVisible" width="560px" :close-on-click-modal="false" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-row :gutter="12">
          <el-col :span="24">
            <el-form-item label="规则名称" prop="rule_name">
              <el-input v-model="form.rule_name" placeholder="请输入规则名称" maxlength="100" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="规则类型" prop="rule_type">
              <el-select v-model="form.rule_type" style="width:100%">
                <el-option label="手机号" value="phone" />
                <el-option label="身份证" value="id_card" />
                <el-option label="邮箱" value="email" />
                <el-option label="姓名" value="name" />
                <el-option label="银行卡" value="bank_card" />
                <el-option label="自定义" value="custom" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="掩码样式" prop="mask_style">
              <el-input v-model="form.mask_style" placeholder="如 *** **** ****" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="正则表达式" prop="regular">
              <el-input v-model="form.regular" type="textarea" :rows="2" placeholder="请输入匹配正则" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
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
const dialogTitle = ref('新增脱敏规则')
const formRef = ref()

const query_orig = { page: 1, page_size: 10, rule_name: '', rule_type: '', status: null }
const query = reactive({ ...query_orig })

const form_orig = {
  id: null, rule_name: '', rule_type: 'custom', mask_style: '', regular: '', status: 1
}
const form = reactive({ ...form_orig })

const rules = {
  rule_name: [{ required: true, message: '请输入规则名称', trigger: 'blur' }],
  rule_type: [{ required: true, message: '请选择规则类型', trigger: 'change' }]
}

const apiBase = '/dsm/rule'

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

function openCreate() { Object.assign(form, form_orig); dialogTitle.value = '新增脱敏规则'; dialogVisible.value = true }
function openEdit(row) { Object.assign(form, form_orig, row); dialogTitle.value = '编辑脱敏规则'; dialogVisible.value = true }

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
  await ElMessageBox.confirm('确定删除该脱敏规则？', '提示', { type: 'warning' })
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
