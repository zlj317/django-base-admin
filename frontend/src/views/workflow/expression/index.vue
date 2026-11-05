<!-- 流程表达式管理页（workflow/expression/index.vue）
     职责：维护可复用的流程表达式（条件判断 / 动态审批人），以 expr_code 唯一标识，
           供流程网关条件与审批人动态取值引用。
     依赖：Element Plus（表单/表格/分页/弹窗）、@/utils/request 统一请求、v-perm 权限指令。
     被谁使用：工作流管理菜单下的「流程表达式」路由页面。 -->
<template>
  <!-- 页面根容器：沿用全局 app-container 内边距 -->
  <div class="app-container">
    <!-- 页面头部：标题与记录数 -->
    <div class="page-header">
      <div class="page-title-wrap">
        <h2>流程表达式</h2>
        <!-- 副标题：说明表达式用途（网关条件/动态审批人）并展示总数 -->
        <div class="sub">网关条件与动态审批人表达式 · 共 {{ total }} 条记录</div>
      </div>
    </div>

    <!-- 查询条件卡片 -->
    <el-card shadow="never" class="search-card">
      <!-- 内联表单；阻止原生提交，回车由输入框触发查询 -->
      <el-form :model="query" inline @submit.prevent>
        <el-form-item label="表达式名称">
          <!-- 名称模糊查询 -->
          <el-input v-model="query.expr_name" placeholder="请输入表达式名称" clearable style="width: 180px" @keyup.enter="handleQuery" />
        </el-form-item>
        <el-form-item label="表达式编码">
          <!-- 编码查询：编码是流程配置中实际引用的唯一标识 -->
          <el-input v-model="query.expr_code" placeholder="请输入表达式编码" clearable style="width: 180px" @keyup.enter="handleQuery" />
        </el-form-item>
        <el-form-item label="类型">
          <!-- 按表达式类型过滤 -->
          <el-select v-model="query.expr_type" placeholder="请选择" clearable style="width: 160px">
            <!-- 条件判断：用于网关分支条件 -->
            <el-option label="条件判断" value="condition" />
            <!-- 动态审批人：运行时计算审批人 -->
            <el-option label="动态审批人" value="assignee" />
          </el-select>
        </el-form-item>
        <el-form-item class="search-actions">
          <el-button type="primary" :icon="Search" @click="handleQuery">查询</el-button>
          <el-button :icon="Refresh" @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 表达式列表卡片 -->
    <el-card shadow="never" class="table-card">
      <template #header>
        <div class="card-header">
          <div class="card-actions">
            <!-- 新增表达式 -->
            <el-button v-perm="'wf:expression:create'" type="primary" :icon="Plus" @click="openCreate">新增</el-button>
            <!-- 批量删除：无勾选时禁用 -->
            <el-button v-perm="'wf:expression:delete'" type="danger" plain :icon="Delete" :disabled="!selectedIds.length" @click="handleBatchDelete">批量删除</el-button>
          </div>
        </div>
      </template>
      <!-- 表格：勾选变化同步 selectedIds -->
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据" @selection-change="onSelectionChange">
        <el-table-column type="index" label="序号" width="70" align="center" />
        <el-table-column type="selection" width="50" align="center" />
        <!-- 表达式名称：面向使用者的中文描述 -->
        <el-table-column label="表达式名称" prop="expr_name" min-width="150" show-overflow-tooltip />
        <!-- 表达式编码：唯一标识，流程配置按此引用 -->
        <el-table-column label="表达式编码" prop="expr_code" min-width="140" show-overflow-tooltip />
        <!-- 表达式内容：实际参与计算的表达式文本，可能较长，超长省略 -->
        <el-table-column label="表达式内容" prop="expr_content" min-width="220" show-overflow-tooltip />
        <el-table-column label="类型" width="110" align="center">
          <template #default="scope">
            <!-- 条件判断用主色、动态审批人用警告色区分；文案同步展示中文 -->
            <el-tag :type="scope.row.expr_type === 'condition' ? 'primary' : 'warning'">
              {{ scope.row.expr_type === 'condition' ? '条件判断' : '动态审批人' }}
            </el-tag>
          </template>
        </el-table-column>
        <!-- 备注：用途说明 -->
        <el-table-column label="备注" prop="remark" min-width="180" show-overflow-tooltip />
        <!-- 创建时间：后端格式化的时间字符串 -->
        <el-table-column label="创建时间" prop="create_time" width="170" />
        <!-- 操作列固定右侧 -->
        <el-table-column label="操作" width="150" align="center" fixed="right">
          <template #default="scope">
            <!-- 编辑：修改名称/类型/内容/备注，编码不可改 -->
            <el-button v-perm="'wf:expression:update'" link type="primary" :icon="Edit" @click="openEdit(scope.row)">编辑</el-button>
            <!-- 删除单条表达式 -->
            <el-button v-perm="'wf:expression:delete'" link type="danger" :icon="Delete" @click="handleDelete(scope.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <!-- 分页：页码/条数双向绑定 query，变化即重新请求 -->
      <div class="pagination-wrap">
        <el-pagination background layout="total, sizes, prev, pager, next, jumper"
          :total="total" v-model:current-page="query.page" v-model:page-size="query.page_size"
          :page-sizes="[10, 20, 50, 100]" @change="getList" />
      </div>
    </el-card>

    <!-- 新增/编辑表达式弹窗：关闭即销毁，避免校验状态残留 -->
    <el-dialog :title="form.id ? '编辑表达式' : '新增表达式'" v-model="dialogVisible" width="560px" :close-on-click-modal="false" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="表达式名称" prop="expr_name">
          <!-- 中文名称，便于在流程配置时识别 -->
          <el-input v-model="form.expr_name" placeholder="如：请假天数大于3天" />
        </el-form-item>
        <el-form-item label="表达式编码" prop="expr_code">
          <!-- 唯一编码：编辑时禁用，避免已引用该编码的流程失效 -->
          <el-input v-model="form.expr_code" placeholder="唯一编码，如 leave_days_gt3" :disabled="!!form.id" />
        </el-form-item>
        <el-form-item label="表达式类型" prop="expr_type">
          <!-- 类型决定表达式在流程中的使用场景：条件判断/动态审批人 -->
          <el-radio-group v-model="form.expr_type">
            <el-radio label="condition">条件判断</el-radio>
            <el-radio label="assignee">动态审批人</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="表达式内容" prop="expr_content">
          <!-- 表达式正文，如 ${form.leaveDays > 3}，后端按此求值 -->
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
// Vue 组合式 API：ref/reactive 管理列表与弹窗状态，onMounted 首次加载
import { ref, reactive, onMounted } from 'vue'
// Element Plus：成功提示与删除确认
import { ElMessage, ElMessageBox } from 'element-plus'
// 查询/操作按钮图标
import { Search, Refresh, Plus, Delete, Edit } from '@element-plus/icons-vue'
// 统一请求实例：携带 token 并统一错误提示
import request from '@/utils/request'

// 列表加载状态
const loading = ref(false)
// 弹窗提交状态
const saving = ref(false)
// 当前页数据
const rows = ref([])
// 总记录数
const total = ref(0)
// 勾选行 id，供批量删除
const selectedIds = ref([])
// 弹窗可见性
const dialogVisible = ref(false)
// 表单实例引用，用于 validate
const formRef = ref()
// 查询条件：分页 + 名称/编码/类型筛选
const query = reactive({ page: 1, page_size: 10, expr_name: '', expr_code: '', expr_type: '' })
// 表单数据；默认类型为条件判断，id=0 表示新增
const form = reactive({ id: 0, expr_name: '', expr_code: '', expr_content: '', expr_type: 'condition', remark: '' })
// 校验规则：名称、编码、内容必填（内容为空表达式无法执行）
const rules = {
  expr_name: [{ required: true, message: '请输入表达式名称', trigger: 'blur' }],
  expr_code: [{ required: true, message: '请输入表达式编码', trigger: 'blur' }],
  expr_content: [{ required: true, message: '请输入表达式内容', trigger: 'blur' }]
}

// 拉取表达式列表：query 含分页与筛选，成功后回填 rows/total
async function getList() {
  loading.value = true
  try {
    const res = await request.get('/wf/expression/list', { params: query })
    rows.value = res.data.list
    total.value = res.data.total
  } finally {
    // 成功失败都关闭 loading
    loading.value = false
  }
}
// 查询：回到第一页
function handleQuery() {
  query.page = 1
  getList()
}
// 重置筛选：清空名称/编码/类型（保留每页条数）
function resetQuery() {
  Object.assign(query, { page: 1, expr_name: '', expr_code: '', expr_type: '' })
  getList()
}
// 勾选变化：只记录 id
function onSelectionChange(rowsSelected) {
  selectedIds.value = rowsSelected.map(row => row.id)
}
// 打开新增弹窗：重置表单并恢复默认类型
function openCreate() {
  Object.assign(form, { id: 0, expr_name: '', expr_code: '', expr_content: '', expr_type: 'condition', remark: '' })
  dialogVisible.value = true
}
// 打开编辑弹窗：回填行数据，空值兜底为空串
function openEdit(row) {
  Object.assign(form, {
    id: row.id, expr_name: row.expr_name, expr_code: row.expr_code,
    expr_content: row.expr_content || '', expr_type: row.expr_type, remark: row.remark || ''
  })
  dialogVisible.value = true
}
// 提交：校验后按 id 判断新增/编辑，成功后关闭弹窗并刷新
async function submitForm() {
  await formRef.value.validate()
  saving.value = true
  try {
    if (form.id) {
      // 编辑：编码在编辑态禁用，不会被改动
      await request.put(`/wf/expression/update/${form.id}`, form)
      ElMessage.success('修改成功')
    } else {
      // 新增：编码需唯一，重复时由后端返回业务错误
      await request.post('/wf/expression/create', form)
      ElMessage.success('新增成功')
    }
    dialogVisible.value = false
    getList()
  } finally {
    saving.value = false
  }
}
// 删除单条表达式：确认后删除并刷新
async function handleDelete(row) {
  await ElMessageBox.confirm(`确认删除表达式「${row.expr_name}」吗？`, '提示', { type: 'warning' })
  await request.delete('/wf/expression/delete', { data: { ids: [row.id] } })
  ElMessage.success('删除成功')
  getList()
}
// 批量删除：删除所有勾选项
async function handleBatchDelete() {
  await ElMessageBox.confirm(`确认删除选中的 ${selectedIds.value.length} 条表达式吗？`, '提示', { type: 'warning' })
  await request.delete('/wf/expression/delete', { data: { ids: selectedIds.value } })
  ElMessage.success('删除成功')
  getList()
}

// 页面挂载后加载首屏列表
onMounted(getList)
</script>
