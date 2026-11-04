<template>
  <div class="app-container kb-wrap">
    <div class="page-header">
      <div class="page-title-wrap">
        <h2>文档列表</h2>
        <div class="sub">知识库文档 · 共 {{ total }} 篇</div>
      </div>
    </div>

    <!-- 顶部统计卡片 + 标签云 -->
    <el-row :gutter="16" class="stat-row">
      <el-col :xs="12" :sm="6" v-for="(s, i) in statCards" :key="i">
        <div class="mini-stat" :class="'ms-' + s.color">
          <div class="ms-icon" :style="{ background: s.bg }">
            <el-icon :size="20"><component :is="s.icon" /></el-icon>
          </div>
          <div class="ms-info">
            <div class="ms-value">{{ getStat(s.key) }}</div>
            <div class="ms-label">{{ s.label }}</div>
          </div>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="16" class="tag-row">
      <el-col :span="24">
        <el-card shadow="never" class="tags-card">
          <div class="tags-header">
            <span class="panel-dot dot-purple"></span>
            <span class="tags-title">🏷️ 热门标签</span>
          </div>
          <div class="tags-cloud">
            <el-tag
              v-for="(t, i) in hotTags"
              :key="t.name"
              :color="tagColors[i % tagColors.length]"
              effect="light"
              class="tag-cloud-item"
            >{{ t.name }} × {{ t.count }}</el-tag>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 搜索 -->
    <el-card shadow="never" class="search-card">
      <el-form :model="query" inline @submit.prevent>
        <el-form-item label="标题">
          <el-input v-model="query.doc_title" placeholder="请输入标题" clearable style="width: 180px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="query.category_id" placeholder="全部" clearable filterable style="width: 160px">
            <el-option v-for="c in categoryOptions" :key="c.id" :label="c.category_name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="query.status" placeholder="全部" clearable style="width: 120px">
            <el-option label="发布" :value="1" />
            <el-option label="草稿" :value="0" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
          <el-button type="primary" :icon="Plus" @click="openCreate">新建文档</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 表格 -->
    <el-card shadow="never" class="table-card">
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据">
        <el-table-column type="index" label="序号" width="70" align="center" />
        <el-table-column label="标题" prop="doc_title" min-width="220" show-overflow-tooltip />
        <el-table-column label="分类" min-width="120">
          <template #default="{ row }">{{ row.category_name || row.category_id || '-' }}</template>
        </el-table-column>
        <el-table-column label="标签" min-width="160">
          <template #default="{ row }">
            <div class="tag-cell">
              <el-tag v-for="(t, i) in parseTags(row.tags)" :key="i" size="small" effect="plain" class="mini-tag">{{ t }}</el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="作者" min-width="100">
          <template #default="{ row }">{{ row.author_name || row.author_id || '-' }}</template>
        </el-table-column>
        <el-table-column label="权限" width="110" align="center">
          <template #default="{ row }">
            <el-tag :type="row.permission_type === 'public' ? 'success' : (row.permission_type === 'private' ? 'info' : 'warning')" effect="light" size="small">
              {{ { public: '公开', internal: '内部', private: '私有' }[row.permission_type] || row.permission_type || '-' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="阅读" prop="read_count" width="80" />
        <el-table-column label="版本" prop="version" width="80" />
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'info'" effect="light" size="small">
              {{ row.status === 1 ? '发布' : '草稿' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right" class-name="op-col">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button link type="success" @click="handleRead(row)">阅读</el-button>
            <el-button link type="warning" @click="handleVersion(row)">版本</el-button>
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

    <!-- 新建/编辑 Dialog -->
    <el-dialog :title="dialogTitle" v-model="dialogVisible" width="760px" top="5vh" :close-on-click-modal="false" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-row :gutter="12">
          <el-col :span="24">
            <el-form-item label="标题" prop="doc_title">
              <el-input v-model="form.doc_title" placeholder="请输入文档标题" maxlength="200" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="分类" prop="category_id">
              <el-select v-model="form.category_id" placeholder="请选择分类" filterable clearable style="width:100%">
                <el-option v-for="c in categoryOptions" :key="c.id" :label="c.category_name" :value="c.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="状态" prop="status">
              <el-radio-group v-model="form.status">
                <el-radio :value="1">发布</el-radio>
                <el-radio :value="0">草稿</el-radio>
              </el-radio-group>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="权限类型" prop="permission_type">
              <el-select v-model="form.permission_type" placeholder="请选择" style="width:100%">
                <el-option label="公开 public" value="public" />
                <el-option label="内部 internal" value="internal" />
                <el-option label="私有 private" value="private" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="标签">
              <el-input v-model="form.tags" placeholder="逗号分隔，如：教程,常见问题" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="附件ID">
              <el-input v-model="form.file_id" placeholder="file_id" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="版本号">
              <el-input v-model="form.version" placeholder="如 1.0" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="文档内容" prop="doc_content">
              <el-input v-model="form.doc_content" type="textarea" :rows="12" placeholder="请输入文档正文（后续可升级为富文本编辑器）" class="doc-textarea" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="权限配置">
              <el-input v-model="form.role_json" type="textarea" :rows="3" placeholder="角色权限 JSON，如 {&quot;roles&quot;: [&quot;admin&quot;]}" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible=false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitForm">确定</el-button>
      </template>
    </el-dialog>

    <!-- 阅读抽屉 -->
    <el-drawer v-model="readVisible" :title="readData.doc_title || '文档阅读'" size="600px" destroy-on-close>
      <div v-if="readData.id" class="read-body">
        <div class="read-meta">
          <span class="rm-item">📁 {{ readData.category_name || readData.category_id || '-' }}</span>
          <span class="rm-item">👤 {{ readData.author_name || readData.author_id || '-' }}</span>
          <span class="rm-item">👁️ {{ readData.read_count || 0 }} 次</span>
          <span class="rm-item">📅 {{ readData.create_time }}</span>
        </div>
        <div class="read-content">{{ readData.doc_content || '（暂无内容）' }}</div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Refresh, Plus, Document, TrendCharts, View, Tickets } from '@element-plus/icons-vue'
import request from '@/utils/request'

const loading = ref(false)
const rows = ref([])
const total = ref(0)
const saving = ref(false)
const dialogVisible = ref(false)
const dialogTitle = ref('新建文档')
const formRef = ref()
const categoryOptions = ref([])

const query_orig = { page: 1, page_size: 10, doc_title: '', category_id: null, status: null }
const query = reactive({ ...query_orig })

const form_orig = {
  id: null, doc_title: '', category_id: null, tags: '', author_id: null,
  permission_type: 'public', version: '1.0', status: 0, doc_content: '', file_id: '', role_json: ''
}
const form = reactive({ ...form_orig })

const rules = { doc_title: [{ required: true, message: '请输入标题', trigger: 'blur' }] }

// 统计
const stats = reactive({ total_documents: 0, total_reads: 0, today_new: 0, published: 0 })
const statCards = [
  { key: 'total_documents', label: '总文档数', icon: Document, color: 'blue', bg: 'linear-gradient(135deg, #4a6cf7, #6366f1)' },
  { key: 'total_reads', label: '总阅读数', icon: View, color: 'purple', bg: 'linear-gradient(135deg, #8b5cf6, #a78bfa)' },
  { key: 'today_new', label: '今日新增', icon: TrendCharts, color: 'green', bg: 'linear-gradient(135deg, #22c55e, #4ade80)' },
  { key: 'published', label: '已发布', icon: Tickets, color: 'orange', bg: 'linear-gradient(135deg, #f59e0b, #fbbf24)' }
]

const tagColors = ['#4a6cf7', '#8b5cf6', '#22c55e', '#f59e0b', '#ef4444', '#06b6d4', '#ec4899', '#64748b']
const hotTags = ref([
  { name: '教程', count: 24 },
  { name: 'API', count: 18 },
  { name: '配置', count: 16 },
  { name: '最佳实践', count: 12 },
  { name: 'FAQ', count: 10 },
  { name: '架构', count: 9 },
  { name: '部署', count: 8 },
  { name: '运维', count: 6 }
])

const readVisible = ref(false)
const readData = reactive({})

function getStat(key) { return stats[key] ?? 0 }

function parseTags(tags) {
  if (!tags) return []
  if (Array.isArray(tags)) return tags
  return String(tags).split(/[,，]/).map(t => t.trim()).filter(Boolean)
}

async function fetchList() {
  loading.value = true
  try {
    const res = await request.get('/kb/document/list', { params: query })
    rows.value = res.data.list || []
    total.value = res.data.total || 0
    // 更新统计
    stats.total_documents = res.data.total || stats.total_documents
  } finally { loading.value = false }
}

async function loadCategoryOptions() {
  try {
    const res = await request.get('/kb/category/list', { params: { page: 1, page_size: 500 } })
    categoryOptions.value = (res.data.list || []).map(x => ({ id: x.id, category_name: x.category_name }))
  } catch { /* ignore */ }
}

async function loadStats() {
  try {
    const res = await request.get('/kb/document/stats')
    if (res.data) Object.assign(stats, res.data)
  } catch { /* 统计接口异常时保留已有数值 */ }
}

function handleSearch() { query.page = 1; fetchList() }
function handleReset() { Object.assign(query, query_orig); handleSearch() }

function openCreate() { Object.assign(form, form_orig); dialogTitle.value = '新建文档'; dialogVisible.value = true }
function openEdit(row) { Object.assign(form, form_orig, row); dialogTitle.value = '编辑文档'; dialogVisible.value = true }

async function submitForm() {
  await formRef.value.validate()
  saving.value = true
  try {
    if (form.id) {
      const { id, ...data } = form
      await request.put(`/kb/document/update/${id}`, data); ElMessage.success('更新成功')
    } else {
      await request.post('/kb/document/create', form); ElMessage.success('新建成功')
    }
    dialogVisible.value = false; fetchList(); loadStats()
  } finally { saving.value = false }
}

function handleRead(row) {
  Object.assign(readData, { ...row })
  readVisible.value = true
}

function handleVersion(row) {
  ElMessage.info(`查看「${row.doc_title}」版本 v${row.version || '1.0'}（版本历史功能待实现）`)
}

async function handleDelete(row) {
  await ElMessageBox.confirm(`确定删除文档「${row.doc_title}」？`, '提示', { type: 'warning' })
  await request.delete('/kb/document/delete', { data: { ids: [row.id] } })
  ElMessage.success('删除成功'); fetchList(); loadStats()
}

onMounted(() => { fetchList(); loadCategoryOptions(); loadStats() })
</script>

<style scoped>
.kb-wrap { padding-bottom: 20px; }
.stat-row { margin-bottom: 14px; }
.tag-row { margin-bottom: 14px; }

.mini-stat {
  display: flex; align-items: center; gap: 12px;
  padding: 16px 18px; background: #fff; border-radius: 12px;
  border: 1px solid #f1f5f9; box-shadow: 0 2px 8px rgba(30, 41, 59, 0.04);
  transition: transform 0.15s;
}
.mini-stat:hover { transform: translateY(-2px); }
.ms-icon {
  display: flex; align-items: center; justify-content: center;
  width: 44px; height: 44px; border-radius: 12px; color: #fff; flex-shrink: 0;
}
.ms-info { flex: 1; min-width: 0; }
.ms-value { font-size: 22px; font-weight: 700; color: #1f2937; font-variant-numeric: tabular-nums; }
.ms-label { font-size: 12px; color: #6b7280; margin-top: 2px; }

.tags-card { border-radius: 14px; border: 1px solid #f1f5f9; }
.tags-header { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; font-weight: 600; font-size: 14px; color: #1f2937; }
.panel-dot { width: 4px; height: 16px; border-radius: 3px; background: linear-gradient(180deg, #8b5cf6, #a78bfa); }
.tags-cloud { display: flex; flex-wrap: wrap; gap: 8px; }
.tag-cloud-item { cursor: pointer; transition: transform 0.15s; font-size: 13px; height: 28px; padding: 0 12px; line-height: 26px; }
.tag-cloud-item:hover { transform: scale(1.05); }

.search-card, .table-card { border-radius: 14px; border: 1px solid #f1f5f9; }

.tag-cell { display: flex; flex-wrap: wrap; gap: 3px; }
.mini-tag { max-width: 120px; }

.doc-textarea :deep(textarea) {
  font-family: Menlo, Monaco, Consolas, monospace; font-size: 13px; line-height: 1.8;
}

.read-body { padding: 0 6px; }
.read-meta { display: flex; flex-wrap: wrap; gap: 14px; margin-bottom: 20px; padding: 12px 14px; background: #f8fafc; border-radius: 8px; }
.rm-item { font-size: 12px; color: #6b7280; }
.read-content { font-size: 14px; color: #374151; line-height: 1.9; white-space: pre-wrap; word-break: break-word; }
</style>
