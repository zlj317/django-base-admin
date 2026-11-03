<template>
  <div class="app-container">
    <div class="page-header">
      <div class="page-title-wrap">
        <h2>流程表达式</h2>
        <div class="sub">网关条件与动态审批人表达式 · 共 {{ total }} 条记录</div>
      </div>
    </div>

    <el-card shadow="never" class="search-card">
      <el-form :model="query" inline @submit.prevent>
        <el-form-item label="表达式名称">
          <el-input v-model="query.expr_name" placeholder="请输入表达式名称" clearable style="width: 180px" @keyup.enter="handleQuery" />
        </el-form-item>
        <el-form-item label="表达式编码">
          <el-input v-model="query.expr_code" placeholder="请输入表达式编码" clearable style="width: 180px" @keyup.enter="handleQuery" />
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="query.expr_type" placeholder="请选择" clearable style="width: 160px">
            <el-option label="条件判断" value="condition" />
            <el-option label="动态审批人" value="assignee" />
          </el-select>
        </el-form-item>
        <el-form-item class="search-actions">
          <el-button type="primary" :icon="Search" @click="handleQuery">查询</el-button>
          <el-button :icon="Refresh" @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="table-card">
      <template #header>
        <div class="card-header">
          <span class="card-title">表达式列表</span>
          <div class="card-actions">
            <el-button v-perm="'wf:expression:create'" type="primary" :icon="Plus" @click="openCreate">新增</el-button>
            <el-button v-perm="'wf:expression:delete'" type="danger" plain :icon="Delete" :disabled="!selectedIds.length" @click="handleBatchDelete">批量删除</el-button>
          </div>
        </div>
      </template>
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据" @selection-change="onSelectionChange">
        <el-table-column type="selection" width="50" align="center" />
        <el-table-column label="编号" prop="id" width="70" align="center" />
        <el-table-column label="表达式名称" prop="expr_name" min-width="150" show-overflow-tooltip />
        <el-table-column label="表达式编码" prop="expr_code" min-width="140" show-overflow-tooltip />
        <el-table-column label="表达式内容" prop="expr_content" min-width="220" show-overflow-tooltip />
        <el-table-column label="类型" width="110" align="center">
          <template #default="scope">
            <el-tag :type="scope.row.expr_type === 'condition' ? 'primary' : 'warning'">
              {{ scope.row.expr_type === 'condition' ? '条件判断' : '动态审批人' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="备注" prop="remark" min-width="180" show-overflow-tooltip />
        <el-table-column label="创建时间" prop="create_time" width="170" />
        <el-table-column label="操作" width="150" align="center" fixed="right">
          <template #default="scope">
            <el-button v-perm="'wf:expression:update'" link type="primary" :icon="Edit" @click="openEdit(scope.row)">编辑</el-button>
            <el-button v-perm="'wf:expression:delete'" link type="danger" :icon="Delete" @click="handleDelete(scope.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination-wrap">
        <el-pagination background layout="total, sizes, prev, pager, next, jumper"
          :total="total" v-model:current-page="query.page" v-model:page-size="query.page_size"
          :page-sizes="[10, 20, 50, 100]" @change="getList" />
      </div>
    </el-card>

    <el-dialog :title="form.id ? '编辑表达式' : '新增表达式'" v-model="dialogVisible" width="560px" :close-on-click-modal="false" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="表达式名称" prop="expr_name">
          <el-input v-model="form.expr_name" placeholder="如：请假天数大于3天" />
        </el-form-item>
        <el-form-item label="表达式编码" prop="expr_code">
          <el-input v-model="form.expr_code" placeholder="唯一编码，如 leave_days_gt3" :disabled="!!form.id" />
        </el-form-item>
        <el-form-item label="表达式类型" prop="expr_type">
          <el-radio-group v-model="form.expr_type">
            <el-radio label="condition">条件判断</el-radio>
            <el-radio label="assignee">动态审批人</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="表达式内容" prop="expr_content">
          <el-input v-model="form.expr_content" type="textarea" :rows="3" placeholder="如：${form.leaveDays > 3}" />
        </el-form-item>
        <el-form-item label="备注" prop="remark">
          <el-input v-model="form.remark" type="textarea" :rows="2" placeholder="请输入备注" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitForm">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Refresh, Plus, Delete, Edit } from '@element-plus/icons-vue'
import request from '@/utils/request'

const loading = ref(false)
const saving = ref(false)
const rows = ref([])
const total = ref(0)
const selectedIds = ref([])
const dialogVisible = ref(false)
const formRef = ref()
const query = reactive({ page: 1, page_size: 10, expr_name: '', expr_code: '', expr_type: '' })
const form = reactive({ id: 0, expr_name: '', expr_code: '', expr_content: '', expr_type: 'condition', remark: '' })
const rules = {
  expr_name: [{ required: true, message: '请输入表达式名称', trigger: 'blur' }],
  expr_code: [{ required: true, message: '请输入表达式编码', trigger: 'blur' }],
  expr_content: [{ required: true, message: '请输入表达式内容', trigger: 'blur' }]
}

async function getList() {
  loading.value = true
  try {
    const res = await request.get('/wf/expression/list', { params: query })
    rows.value = res.data.list
    total.value = res.data.total
  } finally {
    loading.value = false
  }
}
function handleQuery() {
  query.page = 1
  getList()
}
function resetQuery() {
  Object.assign(query, { page: 1, expr_name: '', expr_code: '', expr_type: '' })
  getList()
}
function onSelectionChange(rowsSelected) {
  selectedIds.value = rowsSelected.map(row => row.id)
}
function openCreate() {
  Object.assign(form, { id: 0, expr_name: '', expr_code: '', expr_content: '', expr_type: 'condition', remark: '' })
  dialogVisible.value = true
}
function openEdit(row) {
  Object.assign(form, {
    id: row.id, expr_name: row.expr_name, expr_code: row.expr_code,
    expr_content: row.expr_content || '', expr_type: row.expr_type, remark: row.remark || ''
  })
  dialogVisible.value = true
}
async function submitForm() {
  await formRef.value.validate()
  saving.value = true
  try {
    if (form.id) {
      await request.put(`/wf/expression/update/${form.id}`, form)
      ElMessage.success('修改成功')
    } else {
      await request.post('/wf/expression/create', form)
      ElMessage.success('新增成功')
    }
    dialogVisible.value = false
    getList()
  } finally {
    saving.value = false
  }
}
async function handleDelete(row) {
  await ElMessageBox.confirm(`确认删除表达式「${row.expr_name}」吗？`, '提示', { type: 'warning' })
  await request.delete('/wf/expression/delete', { data: { ids: [row.id] } })
  ElMessage.success('删除成功')
  getList()
}
async function handleBatchDelete() {
  await ElMessageBox.confirm(`确认删除选中的 ${selectedIds.value.length} 条表达式吗？`, '提示', { type: 'warning' })
  await request.delete('/wf/expression/delete', { data: { ids: selectedIds.value } })
  ElMessage.success('删除成功')
  getList()
}

onMounted(getList)
</script>
