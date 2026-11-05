<!--
  文件说明：报表数据源（RP DataSource）管理页面。
  职责：维护报表模板取数所依赖的数据源，支持按名称/类型/状态筛选、分页列表、
        新增/编辑、启用停用切换、单条与批量删除。
  数据含义：ds_type=mysql 表示直连 MySQL（ds_config 存连接参数 JSON：host/port/database/user 等）；
            ds_type=api 表示占位的外部 HTTP 数据源（ds_config 存 url/method/headers 等 JSON）。
            本页不负责“测试连接”，仅做配置的增删改查，实际取数由报表生成/预览接口解析执行。
  依赖：Element Plus、@element-plus/icons-vue、@/utils/request 统一请求封装、v-perm 权限指令。
  被谁使用：rp 模块菜单路由加载本页；报表模板页（views/rp/template）通过
            /rp/datasource/list 拉取数据源下拉选项。
-->
<template>
  <!-- 页面根容器：复用全局 app-container 样式，统一页面内边距与背景 -->
  <div class="app-container">
    <!-- 页头：标题与统计信息 -->
    <div class="page-header">
      <!-- 标题包裹层：约束标题与副标题的垂直排布 -->
      <div class="page-title-wrap">
        <!-- 页面主标题 -->
        <h2>数据源</h2>
        <!-- 副标题：total 为列表接口返回的总条数，随筛选条件变化 -->
        <div class="sub">数据源管理 · 共 {{ total }} 条</div>
      </div>
    </div>
    <!-- 查询卡片：shadow="never" 与下方表格卡片保持扁平统一的视觉 -->
    <el-card shadow="never" class="search-card">
      <!-- 查询表单：inline 行内布局；@submit.prevent 阻止原生提交，避免回车刷新页面 -->
      <el-form :model="query" inline @submit.prevent>
        <!-- 查询项：按数据源名称模糊搜索 -->
        <el-form-item label="数据源名称">
          <!-- 双向绑定 query.ds_name；clearable 支持一键清空；回车即查询 -->
          <el-input v-model="query.ds_name" placeholder="请输入名称" clearable style="width: 170px" @keyup.enter="handleSearch" />
        </el-form-item>
        <!-- 查询项：按数据源类型筛选，null 表示不限制 -->
        <el-form-item label="类型">
          <!-- 与后端 ds_type 枚举一致：mysql / api；清空后查询参数为 null，后端视为全部 -->
          <el-select v-model="query.ds_type" placeholder="全部" clearable style="width: 120px">
            <el-option label="MySQL" value="mysql" />
            <el-option label="API" value="api" />
          </el-select>
        </el-form-item>
        <!-- 查询项：按启停状态筛选 -->
        <el-form-item label="状态">
          <!-- 值为数字 1/0，与数据库存储的状态枚举保持一致；clearable 清空即查全部 -->
          <el-select v-model="query.status" placeholder="全部" clearable style="width: 110px">
            <el-option label="启用" :value="1" />
            <el-option label="停用" :value="0" />
          </el-select>
        </el-form-item>
        <!-- 无标签操作项：查询与重置按钮 -->
        <el-form-item>
          <!-- 查询：handleSearch 内部会重置页码后请求 -->
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <!-- 重置：恢复默认筛选条件并重新加载第一页 -->
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 列表卡片：承载表格与分页 -->
    <el-card shadow="never" class="table-card">
      <!-- 卡片头部插槽：放置新增与批量删除入口 -->
      <template #header>
        <!-- 头部容器：flex 布局使操作按钮组靠右 -->
        <div class="card-header">
          <!-- 操作按钮组 -->
          <div class="card-actions">
            <!-- 新增：需 'rp:create' 权限；打开重置后的新增弹窗 -->
            <el-button v-perm="'rp:create'" type="primary" :icon="Plus" @click="openCreate">新增</el-button>
            <!-- 批量删除：未勾选时禁用，避免空 ids 请求；需 'rp:delete' 权限 -->
            <el-button v-perm="'rp:delete'" type="danger" plain :icon="Delete" :disabled="!selection.length" @click="handleBatchDelete">批量删除</el-button>
          </div>
        </div>
      </template>
      <!-- 数据表格：v-loading 请求遮罩；stripe 斑马纹；空数据文案；勾选变化同步 selection -->
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据" @selection-change="onSelectionChange">
        <!-- 序号列：type="index" 自动生成当前页行号 -->
        <el-table-column type="index" label="序号" width="70" align="center" />
        <!-- 多选列：勾选结果供批量删除使用 -->
        <el-table-column type="selection" width="50" />
        <!-- 数据源名称：超长时省略并悬浮显示全文 -->
        <el-table-column label="数据源名称" prop="ds_name" min-width="180" show-overflow-tooltip />
        <!-- 类型列：用不同颜色的 tag 区分 MySQL 与 API，未知类型回退展示原始值 -->
        <el-table-column label="类型" width="100">
          <template #default="{ row }">
            <!-- mysql 数据源：默认灰色标签 -->
            <el-tag v-if="row.ds_type==='mysql'" size="small">MySQL</el-tag>
            <!-- api 数据源：绿色标签以示区分 -->
            <el-tag v-else-if="row.ds_type==='api'" size="small" type="success">API</el-tag>
            <!-- 兜底：后端出现新类型时直接显示原值，避免信息丢失 -->
            <span v-else>{{ row.ds_type }}</span>
          </template>
        </el-table-column>
        <!-- 配置列：展示 ds_config 原始 JSON 字符串（含连接参数），超长省略便于悬浮查看 -->
        <el-table-column label="配置" prop="ds_config" min-width="240" show-overflow-tooltip />
        <!-- 状态列：行内开关切换启停 -->
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <!-- 开关值 1/0 与后端枚举一致；无 'rp:update' 权限时不可操作；
                 change 后立即调用独立状态接口，避免整条记录更新覆盖配置 -->
            <el-switch v-model="row.status" :active-value="1" :inactive-value="0" v-perm="'rp:update'" @change="handleStatusChange(row)" />
          </template>
        </el-table-column>
        <!-- 备注：补充说明，超长省略 -->
        <el-table-column label="备注" prop="remark" min-width="180" show-overflow-tooltip />
        <!-- 创建时间：后端已格式化字符串，前端直接展示 -->
        <el-table-column label="创建时间" prop="create_time" width="170" />
        <!-- 操作列：固定右侧，横向滚动时始终可见；op-col 复用全局操作列样式 -->
        <el-table-column label="操作" width="180" fixed="right" class-name="op-col">
          <template #default="{ row }">
            <!-- 编辑：回填当前行到弹窗表单 -->
            <el-button v-perm="'rp:update'" link type="primary" @click="openEdit(row)">编辑</el-button>
            <!-- 删除：二次确认后按 id 删除 -->
            <el-button v-perm="'rp:delete'" link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <!-- 分页容器：统一右对齐版式 -->
      <div class="pagination-wrap">
        <!-- 分页器：current-page / page-size 双向绑定 query，翻页即改查询参数；
             @change 页码或每页条数变化后重新请求列表 -->
        <el-pagination background layout="total, sizes, prev, pager, next, jumper"
          :total="total" v-model:current-page="query.page" v-model:page-size="query.page_size"
          :page-sizes="[10, 20, 50, 100]" @change="fetchList" />
      </div>
    </el-card>

    <!-- 新增/编辑弹窗：标题随操作变化；点遮罩不关闭，防止误触丢失配置；关闭即销毁表单 -->
    <el-dialog :title="dialogTitle" v-model="dialogVisible" width="640px" :close-on-click-modal="false" destroy-on-close>
      <!-- 弹窗表单：ref 供 submitForm 校验；rules 控制必填；label-width 统一标签宽度 -->
      <el-form ref="formRef" :model="form" :rules="rules" label-width="110px">
        <!-- 数据源名称：必填，长度 100 与后端字段约束一致 -->
        <el-form-item label="数据源名称" prop="ds_name">
          <el-input v-model="form.ds_name" placeholder="请输入数据源名称" maxlength="100" />
        </el-form-item>
        <!-- 类型：决定 ds_config 的结构与后续取数方式（mysql 直连 / api 走 HTTP） -->
        <el-form-item label="类型" prop="ds_type">
          <!-- 占满整行宽度，避免下拉在窄表单里被截断 -->
          <el-select v-model="form.ds_type" style="width:100%">
            <el-option label="MySQL" value="mysql" />
            <el-option label="API" value="api" />
          </el-select>
        </el-form-item>
        <!-- 配置JSON：以 JSON 文本保存连接信息；MySQL 至少包含 host/port/database/user/password，
              API 至少包含 url/method（可含 headers/params）；提交时后端按 ds_type 解析校验 -->
        <el-form-item label="配置JSON" prop="ds_config">
          <!-- 5 行文本域便于查看完整连接配置；placeholder 给出两种类型的字段示例 -->
          <el-input v-model="form.ds_config" type="textarea" :rows="5" placeholder='MySQL: {"host":"127.0.0.1","port":3306,...} / API: {"url":"...","method":"GET"}' />
        </el-form-item>
        <!-- 状态：1 启用 / 0 停用；停用后模板下拉通常不再提供该数据源 -->
        <el-form-item label="状态" prop="status">
          <el-radio-group v-model="form.status">
            <el-radio :value="1">启用</el-radio>
            <el-radio :value="0">停用</el-radio>
          </el-radio-group>
        </el-form-item>
        <!-- 备注：补充说明 -->
        <el-form-item label="备注" prop="remark">
          <el-input v-model="form.remark" type="textarea" :rows="2" placeholder="请输入备注" />
        </el-form-item>
      </el-form>
      <!-- 弹窗底部插槽：取消/确定 -->
      <template #footer>
        <!-- 取消：只关闭弹窗，不保存 -->
        <el-button @click="dialogVisible=false">取消</el-button>
        <!-- 确定：loading 防重复提交，点击后校验并新增/更新 -->
        <el-button type="primary" :loading="saving" @click="submitForm">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
// 组合式 API：顶层声明的变量与函数自动暴露给模板，无需显式 return
import { ref, reactive, onMounted } from 'vue'
// ElMessage 操作结果轻提示；ElMessageBox 删除前二次确认
import { ElMessage, ElMessageBox } from 'element-plus'
// 按钮图标：查询、重置、新增、批量删除
import { Search, Refresh, Plus, Delete } from '@element-plus/icons-vue'
// 统一请求实例：已封装 baseURL、Token 与错误提示
import request from '@/utils/request'

// 表格 loading：请求期间遮罩，避免重复操作
const loading = ref(false)
// 当前页数据
const rows = ref([])
// 总条数，驱动分页器与页头统计文案
const total = ref(0)
// 勾选行，控制批量删除按钮可用状态并提供 ids
const selection = ref([])
// 提交按钮 loading，防重复提交
const saving = ref(false)
// 新增/编辑弹窗显隐
const dialogVisible = ref(false)
// 弹窗标题，区分新增与编辑
const dialogTitle = ref('新增')
// 表单实例引用，用于 validate
const formRef = ref()

// 查询默认值：ds_type/status 默认 null 表示不筛选（清空下拉即为 null）
const query_orig = { page: 1, page_size: 10, ds_name: '', ds_type: null, status: null }
// reactive 包裹后模板可直接双向绑定字段，且分页组件改动会同步回 query
const query = reactive({ ...query_orig })

// 表单默认值：id=null 表示新增；默认类型 mysql；status=1 启用
const form_orig = {
  id: null, ds_name: '', ds_type: 'mysql', ds_config: '', status: 1, remark: ''
}
// 弹窗表单对象，展开拷贝避免与 form_orig 共享引用
const form = reactive({ ...form_orig })

// 校验规则：名称、类型、配置 JSON 均必填；类型用 change 触发（下拉选择即校验）
const rules = {
  ds_name: [{ required: true, message: '请输入数据源名称', trigger: 'blur' }],
  ds_type: [{ required: true, message: '请选择类型', trigger: 'change' }],
  ds_config: [{ required: true, message: '请输入配置JSON', trigger: 'blur' }]
}

// 按动作名返回数据源模块接口地址，避免路径硬编码散落各处
function apiUrl(action) {
  // 数据源模块统一前缀，后端路由挂载点为 /rp/datasource
  const base = '/rp/datasource'
  // 对象查表：list/create/update/delete 四种动作
  return {
    list: base + '/list',
    create: base + '/create',
    update: base + '/update',
    delete: base + '/delete'
  }[action]
}

// 拉取数据源列表：携带查询条件，回填 rows/total；finally 保证异常时也关闭 loading
async function fetchList() {
  loading.value = true
  try {
    // GET 请求，params 自动拼接查询字符串
    const res = await request.get(apiUrl('list'), { params: query })
    // 兜底空数组，防止接口返回 null 时表格报错
    rows.value = res.data.list || []
    // 兜底 0，避免分页器出现 NaN
    total.value = res.data.total || 0
  } finally { loading.value = false }
}
// 查询：先回到第一页，避免当前页超出新结果范围导致空列表
function handleSearch() { query.page = 1; fetchList() }
// 重置：用默认值覆盖 query（保留响应式引用），清空筛选后重新查询
function handleReset() { Object.assign(query, query_orig); handleSearch() }
// 勾选变化：回调参数为选中行数组，直接同步给 selection
function onSelectionChange(r) { selection.value = r }

// 打开新增：先还原默认表单，避免上次编辑残留；标题改为“新增数据源”
function openCreate() { Object.assign(form, form_orig); dialogTitle.value = '新增数据源'; dialogVisible.value = true }
// 打开编辑：默认值打底、当前行覆盖，保证缺失字段有默认值且不污染行数据
function openEdit(row) { Object.assign(form, form_orig, row); dialogTitle.value = '编辑数据源'; dialogVisible.value = true }

// 提交表单：先校验，再按 id 区分更新/新增
async function submitForm() {
  // 校验不通过会抛异常，中断后续提交
  await formRef.value.validate()
  saving.value = true
  try {
    // 有 id 表示编辑已有数据源
    if (form.id) {
      // 剔除 id：更新接口的 id 放在路径上，body 不重复携带
      const { id, ...data } = form
      // PUT 更新指定数据源，包括 ds_config 配置内容
      await request.put(`${apiUrl('update')}/${id}`, data); ElMessage.success('更新成功')
    } else {
      // 无 id 走新增，提交整份表单
      await request.post(apiUrl('create'), form); ElMessage.success('新增成功')
    }
    // 成功后关闭弹窗并刷新列表
    dialogVisible.value = false; fetchList()
  } finally { saving.value = false }
}

// 行内状态切换：调用独立状态接口，避免整条更新时用旧配置覆盖新配置
async function handleStatusChange(row) {
  // PUT 只提交 status 字段
  await request.put(`/rp/datasource/status/${row.id}`, { status: row.status })
  // 按新状态提示（1=已启用，0=已停用）
  ElMessage.success(row.status === 1 ? '已启用' : '已停用')
}

// 单条删除：先二次确认，取消会抛异常中断流程
async function handleDelete(row) {
  // warning 类型提示该操作不可恢复
  await ElMessageBox.confirm('确定删除该数据源？', '提示', { type: 'warning' })
  // DELETE 请求体放 data 字段；ids 数组便于复用批量接口
  await request.delete(apiUrl('delete'), { data: { ids: [row.id] } })
  // 提示并刷新列表
  ElMessage.success('删除成功'); fetchList()
}

// 批量删除：确认文案带数量，防止误删
async function handleBatchDelete() {
  await ElMessageBox.confirm(`确定删除选中的 ${selection.value.length} 条数据源？`, '提示', { type: 'warning' })
  // 收集勾选行 id 组成 ids 提交
  await request.delete(apiUrl('delete'), { data: { ids: selection.value.map(r => r.id) } })
  ElMessage.success('批量删除成功'); fetchList()
}

// 页面挂载后自动加载第一页
onMounted(fetchList)
</script>
