<template>
  <div class="app-container">
    <div class="page-header">
      <div class="page-title-wrap">
        <h2>大屏管理</h2>
        <div class="sub">大屏配置 · 共 {{ total }} 条</div>
      </div>
    </div>
    <el-card shadow="never" class="search-card">
      <el-form :model="query" inline @submit.prevent>
        <el-form-item label="大屏名称">
          <el-input v-model="query.screen_name" placeholder="请输入名称" clearable style="width: 170px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="query.status" placeholder="全部" clearable style="width: 130px">
            <el-option label="草稿" :value="0" />
            <el-option label="已发布" :value="1" />
            <el-option label="停用" :value="2" />
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
            <el-button v-perm="'bi:create'" type="primary" :icon="Plus" @click="openCreate">新增</el-button>
            <el-button v-perm="'bi:delete'" type="danger" plain :icon="Delete" :disabled="!selection.length" @click="handleBatchDelete">批量删除</el-button>
          </div>
        </div>
      </template>
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据" @selection-change="onSelectionChange">
        <el-table-column type="index" label="序号" width="70" align="center" />
        <el-table-column type="selection" width="50" />
        <el-table-column label="大屏名称" prop="screen_name" min-width="180" show-overflow-tooltip />
        <el-table-column label="刷新秒" prop="refresh_sec" width="90" />
        <el-table-column label="分享链接" prop="share_url" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">{{ row.share_url || '-' }}</template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.status===0" size="small" type="info">草稿</el-tag>
            <el-tag v-else-if="row.status===1" size="small" type="success">已发布</el-tag>
            <el-tag v-else-if="row.status===2" size="small" type="warning">停用</el-tag>
            <span v-else>{{ row.status }}</span>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" prop="create_time" width="170" />
        <el-table-column label="操作" width="330" fixed="right" class-name="op-col">
          <template #default="{ row }">
            <el-button link type="warning" @click="handleView(row)">预览</el-button>
            <el-button v-perm="'bi:update'" link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button v-if="row.status===0" v-perm="'bi:publish'" link type="success" @click="handlePublish(row)">发布</el-button>
            <el-button v-if="row.status===1 && row.share_url" link type="success" @click="handleShare(row)">分享</el-button>
            <el-button v-perm="'bi:delete'" link type="danger" @click="handleDelete(row)">删除</el-button>
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
        <el-form-item label="大屏名称" prop="screen_name">
          <el-input v-model="form.screen_name" placeholder="请输入大屏名称" maxlength="100" />
        </el-form-item>
        <el-form-item label="大屏配置" prop="screen_config">
          <el-input v-model="form.screen_config" type="textarea" :rows="8" placeholder="大屏JSON配置" />
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <el-select v-model="form.status" style="width:100%">
            <el-option label="草稿" :value="0" />
            <el-option label="已发布" :value="1" />
            <el-option label="停用" :value="2" />
          </el-select>
        </el-form-item>
        <el-form-item label="刷新秒" prop="refresh_sec">
          <el-input-number v-model="form.refresh_sec" :min="0" :max="3600" />
        </el-form-item>
        <el-form-item label="分享密码" prop="share_password">
          <el-input v-model="form.share_password" placeholder="可留空，留空则无密码" maxlength="32" show-password />
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
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Refresh, Plus, Delete } from '@element-plus/icons-vue'
import request from '@/utils/request'

const router = useRouter()

const loading = ref(false)
const rows = ref([])
const total = ref(0)
const selection = ref([])
const saving = ref(false)
const dialogVisible = ref(false)
const dialogTitle = ref('新增')
const formRef = ref()

const query_orig = { page: 1, page_size: 10, screen_name: '', status: null }
const query = reactive({ ...query_orig })

const form_orig = {
  id: null, screen_name: '', screen_config: '', status: 0,
  share_url: '', share_password: '', refresh_sec: 60, remark: ''
}
const form = reactive({ ...form_orig })

const rules = {
  screen_name: [{ required: true, message: '请输入大屏名称', trigger: 'blur' }],
  screen_config: [{ required: true, message: '请输入大屏配置', trigger: 'blur' }]
}

function apiUrl(action) {
  const base = '/bi/screen'
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
  } finally { loading.value = false }
}
function handleSearch() { query.page = 1; fetchList() }
function handleReset() { Object.assign(query, query_orig); handleSearch() }
function onSelectionChange(r) { selection.value = r }

function openCreate() { Object.assign(form, form_orig); dialogTitle.value = '新增大屏'; dialogVisible.value = true }
function openEdit(row) { Object.assign(form, form_orig, row); dialogTitle.value = '编辑大屏'; dialogVisible.value = true }

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
  await ElMessageBox.confirm(`确定发布大屏「${row.screen_name}」？`, '提示', { type: 'warning' })
  await request.post(`/bi/screen/publish/${row.id}`)
  ElMessage.success('发布成功'); fetchList()
}

function handleView(row) {
  router.push(`/bi/view/${row.id}`)
}

function handleShare(row) {
  const path = row.share_url || `/bi/view/${row.id}`
  window.open(path, '_blank')
}

async function handleDelete(row) {
  await ElMessageBox.confirm('确定删除该大屏？', '提示', { type: 'warning' })
  await request.delete(apiUrl('delete'), { data: { ids: [row.id] } })
  ElMessage.success('删除成功'); fetchList()
}

async function handleBatchDelete() {
  await ElMessageBox.confirm(`确定删除选中的 ${selection.value.length} 条大屏？`, '提示', { type: 'warning' })
  await request.delete(apiUrl('delete'), { data: { ids: selection.value.map(r => r.id) } })
  ElMessage.success('批量删除成功'); fetchList()
}

onMounted(fetchList)
</script>
