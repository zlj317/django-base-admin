<template>
  <div class="app-container kb-wrap">
    <div class="page-header">
      <div class="page-title-wrap">
        <h2>文档分类</h2>
        <div class="sub">树结构管理 · 左侧分类树 + 右侧文档</div>
      </div>
    </div>

    <el-row :gutter="16" class="main-row">
      <!-- 左侧分类树 -->
      <el-col :xs="24" :md="7">
        <el-card shadow="never" class="tree-card">
          <template #header>
            <div class="card-header">
              <div class="card-title">
                <span class="panel-dot dot-purple"></span>
                分类目录
              </div>
              <el-button type="primary" size="small" :icon="Plus" @click="openCreate(null)">根级</el-button>
            </div>
          </template>
          <div class="tree-toolbar">
            <el-input v-model="treeKeyword" placeholder="搜索分类" clearable style="width: 180px" @input="handleFilterNode" />
            <el-button link type="primary" @click="refreshTree">刷新</el-button>
          </div>
          <div class="tree-wrap">
            <el-tree
              ref="treeRef"
              :data="treeData"
              :props="{ label: 'category_name', children: 'children' }"
              :filter-node-method="filterNode"
              node-key="id"
              default-expand-all
              highlight-current
              :expand-on-click-node="false"
              @node-click="handleNodeClick"
            >
              <template #default="{ node, data }">
                <div class="tree-node">
                  <div class="tn-left">
                    <el-icon v-if="data.children && data.children.length"><FolderOpened /></el-icon>
                    <el-icon v-else><Document /></el-icon>
                    <span class="tn-label">{{ node.label }}</span>
                  </div>
                  <div class="tn-actions" v-if="!data.hideOps">
                    <el-button link size="small" type="primary" @click.stop="openCreate(data.id)">子</el-button>
                    <el-button link size="small" type="primary" @click.stop="openEdit(data)">改</el-button>
                    <el-button link size="small" type="danger" @click.stop="handleDelete(data)">删</el-button>
                  </div>
                </div>
              </template>
            </el-tree>
          </div>
        </el-card>
      </el-col>

      <!-- 右侧表格：分类列表 -->
      <el-col :xs="24" :md="17">
        <el-card shadow="never" class="table-card">
          <template #header>
            <div class="card-header">
              <div class="card-title">
                <span class="panel-dot dot-blue"></span>
                分类列表
                <el-tag size="small" effect="light" type="info" v-if="selectedNode">
                  当前选中: {{ selectedNode.category_name || '根级' }}
                </el-tag>
              </div>
              <el-button type="primary" :icon="Plus" @click="openCreate(selectedNode?.id || null)">新增子分类</el-button>
            </div>
          </template>
          <el-table v-loading="loading" :data="tableRows" stripe empty-text="暂无数据">
            <el-table-column type="index" label="序号" width="70" align="center" />
            <el-table-column label="分类名称" prop="category_name" min-width="200" show-overflow-tooltip />
            <el-table-column label="父级" min-width="140">
              <template #default="{ row }">{{ row.parent_name || row.parent_id || '—' }}</template>
            </el-table-column>
            <el-table-column label="排序" prop="sort" width="80" />
            <el-table-column label="状态" width="90" align="center">
              <template #default="{ row }">
                <el-switch v-model="row.status" :active-value="1" :inactive-value="0" @change="handleStatusChange(row)" />
              </template>
            </el-table-column>
            <el-table-column label="创建时间" prop="create_time" width="170" />
            <el-table-column label="操作" width="180" fixed="right" class-name="op-col">
              <template #default="{ row }">
                <el-button link type="primary" @click="openCreate(row.id)">新增子</el-button>
                <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
                <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <!-- 新建/编辑 Dialog -->
    <el-dialog :title="dialogTitle" v-model="dialogVisible" width="500px" :close-on-click-modal="false" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="父级分类">
          <el-select v-model="form.parent_id" placeholder="根级（不选择）" clearable filterable style="width:100%">
            <el-option v-for="o in parentOptions" :key="o.id" :label="o.category_name" :value="o.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="分类名称" prop="category_name">
          <el-input v-model="form.category_name" placeholder="请输入分类名称" maxlength="100" />
        </el-form-item>
        <el-form-item label="排序" prop="sort">
          <el-input-number v-model="form.sort" :min="0" :max="9999" />
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <el-switch v-model="form.status" :active-value="1" :inactive-value="0" active-text="启用" inactive-text="停用" />
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
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, FolderOpened, Document } from '@element-plus/icons-vue'
import request from '@/utils/request'

const loading = ref(false)
const saving = ref(false)
const treeData = ref([])
const allNodes = ref([])
const treeRef = ref()
const treeKeyword = ref('')

const selectedNode = ref(null) // 当前选中的树节点
const tableRows = ref([])

const form_orig = { id: null, parent_id: null, category_name: '', sort: 0, status: 1, remark: '' }
const form = reactive({ ...form_orig })
const formRef = ref()
const dialogVisible = ref(false)
const dialogTitle = ref('新建分类')

const rules = { category_name: [{ required: true, message: '请输入分类名称', trigger: 'blur' }] }

const parentOptions = computed(() => flattenOptions(treeData.value))

function flattenOptions(tree, depth = 0, out = []) {
  ;(tree || []).forEach(n => {
    out.push({ id: n.id, category_name: `${'　'.repeat(depth)}${n.category_name}` })
    if (n.children?.length) flattenOptions(n.children, depth + 1, out)
  })
  return out
}

// 递归拉全量再构建树
function buildTree(list, parentId = null) {
  return list
    .filter(x => (x.parent_id || null) === parentId)
    .sort((a, b) => (a.sort || 0) - (b.sort || 0))
    .map(x => ({ ...x, children: buildTree(list, x.id) }))
}

async function loadAll() {
  loading.value = true
  try {
    const res = await request.get('/kb/category/list', { params: { page: 1, page_size: 1000 } })
    allNodes.value = res.data.list || []
    treeData.value = buildTree(allNodes.value, null)
    tableRows.value = [...allNodes.value]
    // 给表格加 parent_name
    const idMap = new Map(allNodes.value.map(n => [n.id, n.category_name]))
    tableRows.value = allNodes.value.map(n => ({
      ...n,
      parent_name: n.parent_id ? idMap.get(n.parent_id) : null
    }))
  } finally { loading.value = false }
}

function refreshTree() { loadAll() }

function handleNodeClick(data) {
  selectedNode.value = data
  // 筛选该节点及其子节点
  const descendants = collectIds(data)
  tableRows.value = allNodes.value
    .filter(n => descendants.has(n.id) || n.parent_id === data.id)
    .map(n => {
      const idMap = new Map(allNodes.value.map(x => [x.id, x.category_name]))
      return { ...n, parent_name: n.parent_id ? idMap.get(n.parent_id) : null }
    })
}

function collectIds(node) {
  const ids = new Set([node.id])
  const walk = (arr) => arr.forEach(n => { ids.add(n.id); walk(n.children || []) })
  walk(node.children || [])
  return ids
}

function filterNode(value, data) {
  if (!value) return true
  return (data.category_name || '').includes(value)
}
function handleFilterNode() { treeRef.value?.filter(treeKeyword.value) }

function openCreate(parentId) {
  Object.assign(form, form_orig, { parent_id: parentId ?? null })
  dialogTitle.value = '新建分类'
  dialogVisible.value = true
}

function openEdit(row) {
  Object.assign(form, form_orig, row)
  dialogTitle.value = '编辑分类'
  dialogVisible.value = true
}

async function submitForm() {
  await formRef.value.validate()
  saving.value = true
  try {
    if (form.id) {
      const { id, ...data } = form
      await request.put(`/kb/category/update/${id}`, data); ElMessage.success('更新成功')
    } else {
      await request.post('/kb/category/create', form); ElMessage.success('新建成功')
    }
    dialogVisible.value = false; loadAll()
  } finally { saving.value = false }
}

async function handleStatusChange(row) {
  try {
    await request.put(`/kb/category/update/${row.id}`, { status: row.status })
    ElMessage.success(row.status === 1 ? '已启用' : '已停用')
  } catch { row.status = row.status === 1 ? 0 : 1 }
}

async function handleDelete(row) {
  await ElMessageBox.confirm(`确定删除分类「${row.category_name}」？子分类将一并删除。`, '提示', { type: 'warning' })
  await request.delete('/kb/category/delete', { data: { ids: [row.id] } })
  ElMessage.success('删除成功'); loadAll(); selectedNode.value = null
}

onMounted(loadAll)
</script>

<style scoped>
.kb-wrap { padding-bottom: 20px; }
.main-row { margin-bottom: 16px; }

.tree-card, .table-card { border-radius: 14px; border: 1px solid #f1f5f9; }
.card-header { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.card-title { display: flex; align-items: center; gap: 8px; font-weight: 600; font-size: 14px; color: #1f2937; }
.panel-dot { width: 4px; height: 16px; border-radius: 3px; }
.dot-purple { background: linear-gradient(180deg, #8b5cf6, #a78bfa); }
.dot-blue { background: linear-gradient(180deg, #4a6cf7, #6366f1); }

.tree-toolbar { display: flex; justify-content: space-between; margin-bottom: 12px; }
.tree-wrap { max-height: 560px; overflow-y: auto; }

.tree-node {
  display: flex; align-items: center; justify-content: space-between;
  width: 100%; font-size: 13px;
}
.tn-left { display: flex; align-items: center; gap: 6px; }
.tn-label { color: #1f2937; }
.tn-actions { opacity: 0; transition: opacity 0.15s; }
.tree-node:hover .tn-actions { opacity: 1; }

:deep(.el-tree-node__content:hover) { background: #eef1ff; }
:deep(.el-tree-node.is-current > .el-tree-node__content) { background: #eef1ff; }
</style>
