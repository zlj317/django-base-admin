<template>
  <div class="app-container">
    <div class="page-header">
      <div class="page-title-wrap">
        <h2>日程提醒</h2>
        <div class="sub">日历日程 · 共 {{ total }} 条提醒</div>
      </div>
      <div class="page-header-actions">
        <el-button type="primary" :icon="Plus" @click="openCreate">新建提醒</el-button>
      </div>
    </div>

    <el-card shadow="never" class="search-card">
      <el-form :model="query" inline @submit.prevent>
        <el-form-item label="关联日程">
          <el-select v-model="query.schedule_id" placeholder="全部" clearable filterable style="width: 220px">
            <el-option v-for="s in scheduleOptions" :key="s.id" :label="s.title" :value="s.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="提醒状态">
          <el-select v-model="query.remind_status" placeholder="全部" clearable style="width: 130px">
            <el-option v-for="s in statusOptions" :key="s.value" :label="s.label" :value="s.value" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="table-card">
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无提醒">
        <el-table-column type="index" label="序号" width="70" align="center" />
        <el-table-column label="关联日程" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">{{ scheduleTitle(row.schedule_id) }}</template>
        </el-table-column>
        <el-table-column label="被提醒人" min-width="120">
          <template #default="{ row }">{{ userNames[row.remind_user_id] || row.remind_user_id || '-' }}</template>
        </el-table-column>
        <el-table-column label="提醒时间" prop="remind_time" width="180" />
        <el-table-column label="状态" width="110" align="center">
          <template #default="{ row }">
            <el-tag :type="statusTag(row.remind_status)" effect="light" size="small">{{ statusLabel(row.remind_status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" prop="create_time" width="180" />
        <el-table-column label="操作" width="150" fixed="right" class-name="op-col">
          <template #default="{ row }">
            <div class="op-btns">
              <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
              <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
            </div>
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
        <el-form-item label="关联日程" prop="schedule_id">
          <el-select v-model="form.schedule_id" placeholder="请选择日程" filterable style="width:100%">
            <el-option v-for="s in scheduleOptions" :key="s.id" :label="s.title" :value="s.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="被提醒人" prop="remind_user_id">
          <el-select v-model="form.remind_user_id" placeholder="请选择用户" filterable clearable style="width:100%">
            <el-option v-for="u in userOptions" :key="u.id" :label="u.label" :value="u.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="提醒时间" prop="remind_time">
          <el-date-picker v-model="form.remind_time" type="datetime" placeholder="选择提醒时间"
            value-format="YYYY-MM-DD HH:mm:ss" style="width:100%" />
        </el-form-item>
        <el-form-item label="提醒状态" prop="remind_status">
          <el-select v-model="form.remind_status" style="width:100%">
            <el-option v-for="s in statusOptions" :key="s.value" :label="s.label" :value="s.value" />
          </el-select>
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
import { Search, Refresh, Plus } from '@element-plus/icons-vue'
import request from '@/utils/request'

const loading = ref(false)
const rows = ref([])
const total = ref(0)
const saving = ref(false)
const dialogVisible = ref(false)
const dialogTitle = ref('新建提醒')
const formRef = ref()
const scheduleOptions = ref([])
const userOptions = ref([])
const userNames = reactive({})

const query_orig = { page: 1, page_size: 10, schedule_id: null, remind_status: null }
const query = reactive({ ...query_orig })

const statusOptions = [
  { value: 0, label: '待发送' },
  { value: 1, label: '已发送' },
  { value: 2, label: '已忽略' }
]

const form_orig = { id: null, schedule_id: null, remind_user_id: null, remind_time: '', remind_status: 0 }
const form = reactive({ ...form_orig })
const rules = {
  schedule_id: [{ required: true, message: '请选择关联日程', trigger: 'change' }],
  remind_time: [{ required: true, message: '请选择提醒时间', trigger: 'change' }]
}

function statusLabel(v) { return statusOptions.find(x => x.value === v)?.label || '未知' }
function statusTag(v) { return ({ 0: 'warning', 1: 'success', 2: 'info' })[v] || 'info' }
function scheduleTitle(id) { return scheduleOptions.value.find(s => s.id === id)?.title || (id ? `日程 #${id}` : '-') }

async function fetchList() {
  loading.value = true
  try {
    const res = await request.get('/cal/reminder/list', { params: query })
    rows.value = res.data.list || []
    total.value = res.data.total || 0
  } finally { loading.value = false }
}

async function loadOptions() {
  try {
    const res = await request.get('/cal/schedule/list', { params: { page: 1, page_size: 500 } })
    scheduleOptions.value = res.data.list || []
  } catch { /* ignore */ }
  try {
    const res = await request.get('/system/user/list', { params: { page: 1, page_size: 500 } })
    userOptions.value = (res.data.list || []).map(u => ({ id: u.id, label: u.nickname || u.username }))
    userOptions.value.forEach(u => { userNames[u.id] = u.label })
  } catch { /* ignore */ }
}

function handleSearch() { query.page = 1; fetchList() }
function handleReset() { Object.assign(query, query_orig); handleSearch() }

function openCreate() { Object.assign(form, form_orig); dialogTitle.value = '新建提醒'; dialogVisible.value = true }
function openEdit(row) { Object.assign(form, form_orig, row); dialogTitle.value = '编辑提醒'; dialogVisible.value = true }

async function submitForm() {
  await formRef.value.validate()
  saving.value = true
  try {
    if (form.id) {
      const { id, ...data } = form
      await request.put(`/cal/reminder/update/${id}`, data); ElMessage.success('更新成功')
    } else {
      await request.post('/cal/reminder/create', form); ElMessage.success('新建成功')
    }
    dialogVisible.value = false; fetchList()
  } finally { saving.value = false }
}

async function handleDelete(row) {
  await ElMessageBox.confirm('确定删除该提醒？', '提示', { type: 'warning' })
  await request.delete('/cal/reminder/delete', { data: { ids: [row.id] } })
  ElMessage.success('删除成功'); fetchList()
}

onMounted(() => { fetchList(); loadOptions() })
</script>

<style scoped>
.op-btns { display: flex; flex-wrap: nowrap; align-items: center; white-space: nowrap; }
.op-btns .el-button { margin-left: 0; padding: 0 4px; }
</style>
