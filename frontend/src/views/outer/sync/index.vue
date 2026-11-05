<!--
  文件级说明：外部数据同步任务管理页。
  职责：配置“外部接口 -> 目标数据表”的同步任务，维护字段映射、同步方式（手动/定时）、关联定时任务与启停状态；
        支持筛选、分页、新增、编辑、启停、单条/批量删除。
  依赖：@/utils/request（统一 /api 前缀、Bearer token 与错误提示）；Element Plus（表格/表单/弹窗/消息）；
        @element-plus/icons-vue 的 Search、Refresh、Plus、Delete 图标；自定义指令 v-perm 控制按钮级权限。
  数据来源：GET /outer/sync/list；POST /outer/sync/create；PUT /outer/sync/update/{id}；DELETE /outer/sync/delete（body 传 ids）；
            PUT /outer/sync/status/{id} 切换启停；GET /outer/api/list 取前 200 个接口供“目标接口”下拉选择。
  业务含义：sync_field_json 描述接口返回字段到数据库表字段的映射（{"api_field":"db_field"}）；
            sync_type=manual 由用户手动触发，schedule 由 task_id 指向的定时任务周期性触发。
  被谁使用：由路由挂载在“数据同步”菜单，依赖 outer/api 中已配置且启用的接口。
-->
<template>
  <!-- 页面根容器：统一内边距与背景 -->
  <div class="app-container">
    <!-- 页头：标题 + 总条数副标题 -->
    <div class="page-header">
      <div class="page-title-wrap">
        <!-- 主标题：同步任务（配置项，不是执行记录） -->
        <h2>同步任务</h2>
        <!-- 副标题：实时展示同步配置总数 -->
        <div class="sub">同步配置 · 共 {{ total }} 条</div>
      </div>
    </div>
    <!-- 查询条件卡片：扁平样式，与表格卡片形成管理页布局 -->
    <el-card shadow="never" class="search-card">
      <!-- 行内表单；阻止原生提交，统一走查询按钮/回车 -->
      <el-form :model="query" inline @submit.prevent>
        <el-form-item label="同步名称">
          <!-- 名称模糊搜索：clearable 一键清空，回车即查询 -->
          <el-input v-model="query.sync_name" placeholder="请输入名称" clearable style="width: 170px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="同步类型">
          <!-- 同步类型筛选：manual=手动触发，schedule=定时任务触发 -->
          <el-select v-model="query.sync_type" placeholder="全部" clearable style="width: 120px">
            <!-- 手动：由用户在管理端主动执行 -->
            <el-option label="手动" value="manual" />
            <!-- 定时：依赖后端任务调度，按 task_id 关联 -->
            <el-option label="定时" value="schedule" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <!-- 1=启用（可被执行），0=停用（保留配置） -->
          <el-select v-model="query.status" placeholder="全部" clearable style="width: 110px">
            <!-- 启用：同步任务可被触发 -->
            <el-option label="启用" :value="1" />
            <!-- 停用：配置保留但不执行 -->
            <el-option label="停用" :value="0" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <!-- 查询：回到第 1 页按当前条件请求 -->
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <!-- 重置：恢复初始条件后重新查询 -->
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 表格卡片：头部为操作按钮，主体为同步任务列表，底部为分页 -->
    <el-card shadow="never" class="table-card">
      <!-- 卡片头部插槽：集中放置新增/批量删除 -->
      <template #header>
        <div class="card-header">
          <div class="card-actions">
            <!-- 新增：需要 outer:create 权限；重置表单后打开弹窗 -->
            <el-button v-perm="'outer:create'" type="primary" :icon="Plus" @click="openCreate">新增</el-button>
            <!-- 批量删除：需要 outer:delete 权限；未勾选时禁用，避免空提交 -->
            <el-button v-perm="'outer:delete'" type="danger" plain :icon="Delete" :disabled="!selection.length" @click="handleBatchDelete">批量删除</el-button>
          </div>
        </div>
      </template>
      <!-- 同步任务表格：selection-change 同步勾选行供批量删除使用 -->
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据" @selection-change="onSelectionChange">
        <!-- 序号列：前端自动编号 -->
        <el-table-column type="index" label="序号" width="70" align="center" />
        <!-- 多选列：批量删除依赖它收集 ids -->
        <el-table-column type="selection" width="50" />
        <!-- 同步名称：任务标识，超长省略并悬浮全文 -->
        <el-table-column label="同步名称" prop="sync_name" min-width="170" show-overflow-tooltip />
        <el-table-column label="目标接口" min-width="150">
          <!-- 优先显示接口名称；接口被删除或未联表时降级显示 api_id，保证可追溯 -->
          <template #default="{ row }">{{ row.api_name || row.api_id || '-' }}</template>
        </el-table-column>
        <!-- 目标表：数据写入的数据库表名，是同步落点 -->
        <el-table-column label="目标表" prop="target_table" min-width="140" show-overflow-tooltip />
        <el-table-column label="同步类型" width="100">
          <!-- manual 默认色、schedule 橙色，提示定时任务需要额外依赖 task_id -->
          <template #default="{ row }">
            <!-- 手动：用户主动触发 -->
            <el-tag v-if="row.sync_type==='manual'" size="small">手动</el-tag>
            <!-- 定时：由调度任务周期执行 -->
            <el-tag v-else-if="row.sync_type==='schedule'" size="small" type="warning">定时</el-tag>
            <!-- 兜底：未知类型显示原值 -->
            <span v-else>{{ row.sync_type }}</span>
          </template>
        </el-table-column>
        <el-table-column label="任务ID" prop="task_id" width="90">
          <!-- 关联的定时任务 id，手动同步时为空，用 “-” 占位 -->
          <template #default="{ row }">{{ row.task_id || '-' }}</template>
        </el-table-column>
        <el-table-column label="状态" width="90" align="center">
          <!-- 行内开关直接改 row.status 并调用启停接口；v-perm 限定 outer:update 权限 -->
          <template #default="{ row }">
            <el-switch v-model="row.status" :active-value="1" :inactive-value="0" v-perm="'outer:update'" @change="handleStatusChange(row)" />
          </template>
        </el-table-column>
        <!-- 备注：任务用途说明，超长省略 -->
        <el-table-column label="备注" prop="remark" min-width="160" show-overflow-tooltip />
        <!-- 创建时间：后端已格式化，直接展示 -->
        <el-table-column label="创建时间" prop="create_time" width="170" />
        <!-- 操作列：固定右侧，含编辑/删除 -->
        <el-table-column label="操作" width="180" fixed="right" class-name="op-col">
          <template #default="{ row }">
            <!-- 编辑：outer:update 权限；把当前行回填到表单 -->
            <el-button v-perm="'outer:update'" link type="primary" @click="openEdit(row)">编辑</el-button>
            <!-- 删除：outer:delete 权限；二次确认后删除 -->
            <el-button v-perm="'outer:delete'" link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <!-- 分页容器：统一右对齐布局 -->
      <div class="pagination-wrap">
        <!-- 分页器：页码/每页条数双向绑定 query，变化即重新请求 -->
        <el-pagination background layout="total, sizes, prev, pager, next, jumper"
          :total="total" v-model:current-page="query.page" v-model:page-size="query.page_size"
          :page-sizes="[10, 20, 50, 100]" @change="fetchList" />
      </div>
    </el-card>

    <!-- 新增/编辑弹窗：640px 宽适配字段映射文本域；禁点遮罩关闭防误触；destroy-on-close 保证表单实例干净 -->
    <el-dialog :title="dialogTitle" v-model="dialogVisible" width="640px" :close-on-click-modal="false" destroy-on-close>
      <!-- 同步配置表单：ref 用于校验；rules 约束名称/目标接口/目标表/同步类型必填 -->
      <el-form ref="formRef" :model="form" :rules="rules" label-width="110px">
        <el-form-item label="同步名称" prop="sync_name">
          <!-- 同步名称必填，作为任务的可读标识；maxlength=100 与后端字段长度一致 -->
          <el-input v-model="form.sync_name" placeholder="请输入同步名称" maxlength="100" />
        </el-form-item>
        <el-form-item label="目标接口" prop="api_id">
          <!-- 目标接口：取 outer/api 前 200 条，filterable 支持输入名称快速定位；选项文案附带请求方法便于区分同名接口 -->
          <el-select v-model="form.api_id" placeholder="请选择外部接口" style="width:100%" filterable>
            <!-- value 提交接口 id；label 拼上 method，避免同名 GET/POST 接口混淆 -->
            <el-option v-for="a in apiOptions" :key="a.id" :label="a.api_name + ' (' + a.method + ')'" :value="a.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="目标表" prop="target_table">
          <!-- 目标表名：接口数据最终写入的数据库表，必填以避免同步落点不明 -->
          <el-input v-model="form.target_table" placeholder="请输入目标表名" maxlength="100" />
        </el-form-item>
        <el-form-item label="同步字段JSON" prop="sync_field_json">
          <!-- 字段映射：JSON 对象，键为接口返回字段、值为数据库列名；后端按该映射落库，未列出的字段通常忽略 -->
          <el-input v-model="form.sync_field_json" type="textarea" :rows="4" placeholder='接口字段到表字段映射，如 {"api_field":"db_field"}' />
        </el-form-item>
        <el-form-item label="同步类型" prop="sync_type">
          <!-- 同步类型决定触发方式：手动依赖用户点击，定时依赖任务调度 -->
          <el-select v-model="form.sync_type" style="width:100%">
            <!-- 手动：管理端主动触发 -->
            <el-option label="手动" value="manual" />
            <!-- 定时：由 task_id 关联的调度任务周期触发 -->
            <el-option label="定时" value="schedule" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="form.sync_type==='schedule'" label="关联任务ID" prop="task_id">
          <!-- 仅定时类型显示：必须填写定时任务 id，否则后端无法调度；v-model.number 保证提交数值类型 -->
          <el-input v-model.number="form.task_id" placeholder="定时任务ID" />
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <!-- 启停用：停用后手动与定时触发都不再执行，配置保留 -->
          <el-radio-group v-model="form.status">
            <el-radio :value="1">启用</el-radio>
            <el-radio :value="0">停用</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="备注" prop="remark">
          <!-- 备注：记录同步频率/数据口径等说明，便于交接 -->
          <el-input v-model="form.remark" type="textarea" :rows="2" placeholder="请输入备注" />
        </el-form-item>
      </el-form>
      <!-- 弹窗底部：取消不落库；确定走 submitForm（先校验，再按 id 分流新增/更新） -->
      <template #footer>
        <el-button @click="dialogVisible=false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitForm">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
// 组合式 API：ref 管标量/数组，reactive 管查询与表单，onMounted 做首屏加载
import { ref, reactive, onMounted } from 'vue'
// ElMessage 轻提示操作结果；ElMessageBox 用于删除前二次确认
import { ElMessage, ElMessageBox } from 'element-plus'
// 工具栏与操作列图标，保持全站按钮视觉一致
import { Search, Refresh, Plus, Delete } from '@element-plus/icons-vue'
// 统一请求实例：自动带 token，失败由拦截器统一提示
import request from '@/utils/request'

// 表格加载态：请求期间显示遮罩
const loading = ref(false)
// 当前页同步任务列表，绑定 el-table 的 :data
const rows = ref([])
// 后端总条数：供分页与页头“共 N 条”使用
const total = ref(0)
// 表格勾选行：驱动批量删除按钮与 ids 收集
const selection = ref([])
// 保存中状态：控制“确定”按钮 loading，避免重复提交
const saving = ref(false)
// 弹窗显隐：新增/编辑共用
const dialogVisible = ref(false)
// 弹窗标题：新增与编辑复用弹窗时切换
const dialogTitle = ref('新增')
// 表单实例：提交前调用 validate()
const formRef = ref()
// 目标接口下拉缓存：进入页面时一次性拉取 outer/api 列表
const apiOptions = ref([])

// 查询条件快照：重置时整体覆盖 query
// sync_type/status 用 null 表示“全部”，sync_name 用空串表示不按名称过滤
const query_orig = { page: 1, page_size: 10, sync_name: '', sync_type: null, status: null }
// 响应式查询对象：与查询表单、分页双向绑定，直接作为列表接口 params
const query = reactive({ ...query_orig })

// 表单初始值快照：新增时重置用，避免残留上一次编辑的数据
// 默认“手动同步、启用”且 task_id 为空，符合最常见的轻量同步配置
const form_orig = {
  id: null, sync_name: '', api_id: null, target_table: '', sync_field_json: '',
  sync_type: 'manual', task_id: null, status: 1, remark: ''
}
// 响应式表单对象：弹窗内所有控件绑定到它
const form = reactive({ ...form_orig })

// 校验规则：名称/目标接口/目标表/同步类型必填；字段映射与备注允许为空
// task_id 未设必填，是因为只有 sync_type=schedule 时才展示该字段
const rules = {
  sync_name: [{ required: true, message: '请输入同步名称', trigger: 'blur' }],
  api_id: [{ required: true, message: '请选择目标接口', trigger: 'change' }],
  target_table: [{ required: true, message: '请输入目标表名', trigger: 'blur' }],
  sync_type: [{ required: true, message: '请选择同步类型', trigger: 'change' }]
}

// 接口地址映射表：集中管理 /outer/sync 下的基础端点，避免多处手写字符串不一致
// update 返回不带 id 的前缀，调用方自行拼接 /{id}
function apiUrl(action) {
  const base = '/outer/sync'
  return {
    list: base + '/list',
    create: base + '/create',
    update: base + '/update',
    delete: base + '/delete'
  }[action]
}

// 拉取目标接口下拉数据：接口数量有限，一次取 200 条足够，无需分页
async function loadApiOptions() {
  try {
    // 复用外部接口列表接口，只借用 id/名称/方法字段
    const res = await request.get('/outer/api/list', { params: { page: 1, page_size: 200 } })
    // 兜底空数组，避免后端返回 null 时下拉渲染异常
    apiOptions.value = res.data.list || []
  // 下拉失败不阻塞任务列表展示，静默忽略；错误提示由 request 拦截器统一处理
  } catch (e) { /* ignore */ }
}

// 列表查询：查询/重置/翻页/保存后刷新都复用
async function fetchList() {
  // 打开遮罩提示加载中
  loading.value = true
  try {
    // GET 分页查询，query 自动序列化为 URL 参数
    const res = await request.get(apiUrl('list'), { params: query })
    // list 兜底空数组、total 兜底 0，避免后端返回 null 时渲染异常
    rows.value = res.data.list || []
    total.value = res.data.total || 0
  // 成功失败都关闭遮罩
  } finally { loading.value = false }
}
// 查询：回到第 1 页再请求，避免旧页码越界
function handleSearch() { query.page = 1; fetchList() }
// 重置：用快照覆盖查询条件后重新查询
function handleReset() { Object.assign(query, query_orig); handleSearch() }
// 勾选变化：缓存选中行，供批量删除使用
function onSelectionChange(r) { selection.value = r }

// 新增：重置表单（id=null 保证走新增分支），切标题并打开弹窗
function openCreate() { Object.assign(form, form_orig); dialogTitle.value = '新增同步任务'; dialogVisible.value = true }
// 编辑：先铺默认值再覆盖行数据，保证缺失字段有兜底；id 决定后续走更新分支
function openEdit(row) { Object.assign(form, form_orig, row); dialogTitle.value = '编辑同步任务'; dialogVisible.value = true }

// 提交：先校验，再按 id 分流新增/更新，成功后关闭弹窗并刷新列表
async function submitForm() {
  // 校验失败会 reject 并中断，避免提交非法配置
  await formRef.value.validate()
  saving.value = true
  try {
    if (form.id) {
      // 更新：id 走路径，请求体只带业务字段
      const { id, ...data } = form
      await request.put(`${apiUrl('update')}/${id}`, data); ElMessage.success('更新成功')
    } else {
      // 新增：整表单提交，id 由后端生成
      await request.post(apiUrl('create'), form); ElMessage.success('新增成功')
    }
    // 成功后关闭弹窗并刷新当前页
    dialogVisible.value = false; fetchList()
  // 失败保留弹窗便于修改；无论如何解除 loading
  } finally { saving.value = false }
}

// 行内启停：开关已把新值写入 row.status，这里只同步 status 字段到后端
// 只提交单字段，避免用整行数据触发后端全量更新
async function handleStatusChange(row) {
  await request.put(`/outer/sync/status/${row.id}`, { status: row.status })
  // 按最新状态反馈，确认操作已生效
  ElMessage.success(row.status === 1 ? '已启用' : '已停用')
}

// 单条删除：二次确认后按 ids 数组提交（与批量删除共用接口）
async function handleDelete(row) {
  await ElMessageBox.confirm('确定删除该同步任务？', '提示', { type: 'warning' })
  await request.delete(apiUrl('delete'), { data: { ids: [row.id] } })
  ElMessage.success('删除成功'); fetchList()
}

// 批量删除：确认文案带数量，降低误删风险
async function handleBatchDelete() {
  await ElMessageBox.confirm(`确定删除选中的 ${selection.value.length} 条同步任务？`, '提示', { type: 'warning' })
  // 从选中行提取 id 组成数组提交
  await request.delete(apiUrl('delete'), { data: { ids: selection.value.map(r => r.id) } })
  ElMessage.success('批量删除成功'); fetchList()
}

// 首屏并行加载任务列表与接口下拉：二者互不依赖，保证弹窗打开时下拉已就绪
onMounted(() => { fetchList(); loadApiOptions() })
</script>
