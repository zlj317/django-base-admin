<template>
  <div class="app-container">
    <div class="page-header">
      <div class="page-title-wrap">
        <h2>公告管理</h2>
        <div class="sub">公告列表 · 共 {{ total }} 条</div>
      </div>
    </div>
    <el-card shadow="never" class="search-card">
      <el-form :model="query" inline @submit.prevent>
        <el-form-item label="公告标题">
          <el-input v-model="query.title" placeholder="请输入标题" clearable style="width: 180px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="query.category_id" placeholder="全部" clearable style="width: 150px">
            <el-option v-for="c in categoryOptions" :key="c.id" :label="c.category_name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="query.status" placeholder="全部" clearable style="width: 120px">
            <el-option label="草稿" :value="0" />
            <el-option label="已发布" :value="1" />
            <el-option label="已下线" :value="2" />
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
            <el-button v-perm="'notice:info:create'" type="primary" :icon="Plus" @click="openCreate">新增</el-button>
            <el-button v-perm="'notice:info:delete'" type="danger" plain :icon="Delete" :disabled="!selection.length" @click="handleBatchDelete">批量删除</el-button>
          </div>
        </div>
      </template>
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据" @selection-change="onSelectionChange">
        <el-table-column type="selection" width="50" />
        <el-table-column label="编号" prop="id" width="70" />
        <el-table-column label="标题" prop="title" min-width="220" show-overflow-tooltip />
        <el-table-column label="分类" min-width="120">
          <template #default="{ row }">{{ row.category_name || row.category_id || '-' }}</template>
        </el-table-column>
        <el-table-column label="置顶" width="70" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.is_top" size="small" type="warning">置顶</el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.status===0" size="small" type="info">草稿</el-tag>
            <el-tag v-else-if="row.status===1" size="small" type="success">已发布</el-tag>
            <el-tag v-else-if="row.status===2" size="small" type="warning">已下线</el-tag>
            <span v-else>{{ row.status }}</span>
          </template>
        </el-table-column>
        <el-table-column label="发布用户ID" prop="publish_user_id" width="110" />
        <el-table-column label="发布时间" prop="publish_time" width="170">
          <template #default="{ row }">{{ row.publish_time || '-' }}</template>
        </el-table-column>
        <el-table-column label="创建时间" prop="create_time" width="170" />
        <el-table-column label="操作" width="220" fixed="right" class-name="op-col">
          <template #default="{ row }">
            <el-button v-perm="'notice:info:update'" link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button v-if="row.status===0" v-perm="'notice:info:publish'" link type="success" @click="handlePublish(row)">发布</el-button>
            <el-button v-if="row.status===1" v-perm="'notice:info:offline'" link type="warning" @click="handleOffline(row)">下线</el-button>
            <el-button v-perm="'notice:info:delete'" link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination-wrap">
        <el-pagination background layout="total, sizes, prev, pager, next, jumper"
          :total="total" v-model:current-page="query.page" v-model:page-size="query.page_size"
          :page-sizes="[10, 20, 50, 100]" @change="fetchList" />
      </div>
    </el-card>

    <el-dialog :title="dialogTitle" v-model="dialogVisible" width="720px" :close-on-click-modal="false" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="110px">
        <el-row :gutter="12">
          <el-col :span="24">
            <el-form-item label="标题" prop="title">
              <el-input v-model="form.title" placeholder="请输入公告标题" maxlength="200" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="分类" prop="category_id">
              <el-select v-model="form.category_id" placeholder="请选择分类" style="width:100%">
                <el-option v-for="c in categoryOptions" :key="c.id" :label="c.category_name" :value="c.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="状态" prop="status">
              <el-select v-model="form.status" style="width:100%">
                <el-option label="草稿" :value="0" />
                <el-option label="已发布" :value="1" />
                <el-option label="已下线" :value="2" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="是否置顶" prop="is_top">
              <el-switch v-model="form.is_top" :active-value="1" :inactive-value="0" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="角色范围" prop="role_scope">
              <el-input v-model="form.role_scope" placeholder="role_id列表，逗号分隔" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="开始时间" prop="start_time">
              <el-date-picker v-model="form.start_time" type="datetime" placeholder="选择开始时间" style="width:100%" value-format="YYYY-MM-DD HH:mm:ss" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="结束时间" prop="end_time">
              <el-date-picker v-model="form.end_time" type="datetime" placeholder="选择结束时间" style="width:100%" value-format="YYYY-MM-DD HH:mm:ss" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="附件ID列表" prop="attachment_ids">
              <el-input v-model="form.attachment_ids" placeholder="附件ID逗号分隔" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="公告内容" prop="content">
              <el-input v-model="form.content" type="textarea" :rows="6" placeholder="请输入公告内容" />
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
const dialogTitle = ref('新增')
const formRef = ref()
const categoryOptions = ref([])

const query_orig = { page: 1, page_size: 10, title: '', category_id: null, status: null }
const query = reactive({ ...query_orig })

const form_orig = {
  id: null, title: '', category_id: null, content: '', attachment_ids: '',
  is_top: 0, status: 0, role_scope: '', start_time: '', end_time: '',
  publish_user_id: null, publish_time: ''
}
const form = reactive({ ...form_orig })

const rules = {
  title: [{ required: true, message: '请输入公告标题', trigger: 'blur' }],
  category_id: [{ required: true, message: '请选择分类', trigger: 'change' }],
  content: [{ required: true, message: '请输入公告内容', trigger: 'blur' }]
}

function apiUrl(action) {
  const base = '/notice/info'
  return {
    list: base + '/list',
    create: base + '/create',
    update: base + '/update',
    delete: base + '/delete'
  }[action]
}

async function loadCategories() {
  try {
    const res = await request.get('/notice/category/list', { params: { page: 1, page_size: 200 } })
    categoryOptions.value = res.data.list || []
  } catch (e) { /* ignore */ }
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
function onSelectionChange(r) { selection.value = r }

function openCreate() { Object.assign(form, form_orig); dialogTitle.value = '新增公告'; dialogVisible.value = true }
function openEdit(row) { Object.assign(form, form_orig, row); dialogTitle.value = '编辑公告'; dialogVisible.value = true }

async function submitForm() {
  await formRef.value.validate()
  saving.value = true
  try {
    if (form.id) {
      const { id, ...data } = form
      await request.put(`${apiUrl('update')}/${id}`, data); ElMessage.success('更新成功')
    } else {
      await request.post(apiUrl('create'), form); ElMessage.success('新增成功')
    }
    dialogVisible.value = false; fetchList()
  } finally { saving.value = false }
}

async function handlePublish(row) {
  await ElMessageBox.confirm('确定发布该公告？', '提示', { type: 'warning' })
  await request.put(`/notice/info/publish/${row.id}`)
  ElMessage.success('发布成功'); fetchList()
}

async function handleOffline(row) {
  await ElMessageBox.confirm('确定下线该公告？', '提示', { type: 'warning' })
  await request.put(`/notice/info/offline/${row.id}`)
  ElMessage.success('已下线'); fetchList()
}

async function handleDelete(row) {
  await ElMessageBox.confirm('确定删除该公告？', '提示', { type: 'warning' })
  await request.delete(apiUrl('delete'), { data: { ids: [row.id] } })
  ElMessage.success('删除成功'); fetchList()
}

async function handleBatchDelete() {
  await ElMessageBox.confirm(`确定删除选中的 ${selection.value.length} 条公告？`, '提示', { type: 'warning' })
  await request.delete(apiUrl('delete'), { data: { ids: selection.value.map(r => r.id) } })
  ElMessage.success('批量删除成功'); fetchList()
}

onMounted(() => { fetchList(); loadCategories() })
</script>
