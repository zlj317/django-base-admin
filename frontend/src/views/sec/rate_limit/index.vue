<!-- 文件级说明：安全策略 - 接口限流规则列表页。
     职责：维护 URL 维度的限流规则，规则 = 时间窗口(period_sec) + 窗口内最大次数(max_count)，超出阈值即被后端拒绝。
     依赖：Vue 3 <script setup>、Element Plus（表格/弹窗/消息提示/图标）、@/utils/request（统一请求封装，baseURL=/api）。
     被谁使用：由 sec（安全）模块的路由挂载，用于保护登录、报表等高消耗接口。
     注意：本文件不含 <style> 块，页面样式来自全局样式表。 -->
<template>
  <!-- 页面根容器：套用全局 app-container 布局，承载页头、查询卡片与表格卡片 -->
  <div class="app-container">
    <!-- 页头区域 -->
    <div class="page-header">
      <!-- 标题容器：主标题与统计信息横排 -->
      <div class="page-title-wrap">
        <!-- 页面主标题 -->
        <h2>限流规则</h2>
        <!-- 副标题：说明页面用途，并回显接口返回的总条数 -->
        <div class="sub">接口限流配置 · 共 {{ total }} 条</div>
      </div>
    </div>

    <!-- 查询条件卡片：shadow="never" 去掉阴影，保持后台列表页的扁平风格 -->
    <el-card shadow="never" class="search-card">
      <!-- 搜索表单：inline 横向排列；@submit.prevent 阻止回车触发默认提交刷新页面 -->
      <el-form :model="query" inline @submit.prevent>
        <!-- 规则名称筛选项：对应后端 rule_name，用于按业务名称快速定位规则 -->
        <el-form-item label="规则名称">
          <!-- 输入框：clearable 一键清空；回车即查询；固定宽度保证工具栏整齐 -->
          <el-input v-model="query.rule_name" placeholder="请输入规则名称" clearable style="width: 170px" @keyup.enter="handleSearch" />
        </el-form-item>
        <!-- 限流 URL 筛选项：对应后端 limit_url，可按具体路径或通配模式检索 -->
        <el-form-item label="限流URL">
          <!-- 输入框：支持输入部分路径做匹配，回车即查询 -->
          <el-input v-model="query.limit_url" placeholder="请输入URL" clearable style="width: 170px" @keyup.enter="handleSearch" />
        </el-form-item>
        <!-- 启用状态筛选项：对应后端 status（1 启用 / 0 停用） -->
        <el-form-item label="状态">
          <!-- 下拉框：clearable 后可查询全部状态 -->
          <el-select v-model="query.status" placeholder="全部" clearable style="width: 110px">
            <!-- 启用：规则生效，超过阈值会被限流 -->
            <el-option label="启用" :value="1" />
            <!-- 停用：规则保留但不参与限流判断，便于临时放开流量 -->
            <el-option label="停用" :value="0" />
          </el-select>
        </el-form-item>
        <!-- 操作按钮行 -->
        <el-form-item>
          <!-- 查询按钮：回第 1 页并重新拉取 -->
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <!-- 重置按钮：恢复默认条件后重新查询 -->
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 数据表格卡片：头部工具栏 + 表格 + 分页 -->
    <el-card shadow="never" class="table-card">
      <!-- 卡片头部插槽：承载新增/批量删除按钮 -->
      <template #header>
        <!-- 头部容器 -->
        <div class="card-header">
          <!-- 操作按钮组 -->
          <div class="card-actions">
            <!-- 新增按钮：打开弹窗，预填 60 秒 / 100 次的默认限流配置 -->
            <el-button type="primary" :icon="Plus" @click="openCreate">新增</el-button>
            <!-- 批量删除：无勾选时禁用，plain 弱化危险按钮视觉 -->
            <el-button type="danger" plain :icon="Delete" :disabled="!selection.length" @click="handleBatchDelete">批量删除</el-button>
          </div>
        </div>
      </template>
      <!-- 表格：v-loading 显示加载遮罩；stripe 斑马纹；selection-change 同步勾选行 -->
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据" @selection-change="onSelectionChange">
        <!-- 序号列：按当前页顺序自动编号 -->
        <el-table-column type="index" label="序号" width="70" align="center" />
        <!-- 多选列：提供批量删除入口 -->
        <el-table-column type="selection" width="50" />
        <!-- 规则名称列：业务可读名称，便于在告警/日志中对应到具体规则 -->
        <el-table-column label="规则名称" prop="rule_name" min-width="180" show-overflow-tooltip />
        <!-- 限流 URL 列：被限流的接口路径，可能使用通配（如 /api/**） -->
        <el-table-column label="限流URL" prop="limit_url" min-width="200" show-overflow-tooltip />
        <!-- 时间窗口列：统计窗口长度，单位为秒，与最大次数共同定义限流阈值 -->
        <el-table-column label="时间窗口(秒)" prop="period_sec" width="120" />
        <!-- 最大次数列：窗口内允许的最大请求数，超出即触发限流 -->
        <el-table-column label="最大次数" prop="max_count" width="100" />
        <!-- 状态列：规则是否参与限流判断 -->
        <el-table-column label="状态" width="90" align="center">
          <!-- 默认插槽：按 status 渲染启停标签 -->
          <template #default="{ row }">
            <!-- 启用：status=1 -->
            <el-tag v-if="row.status===1" size="small" type="success">启用</el-tag>
            <!-- 其余值统一按停用展示 -->
            <el-tag v-else size="small" type="info">停用</el-tag>
          </template>
        </el-table-column>
        <!-- 创建时间列：规则录入时间 -->
        <el-table-column label="创建时间" prop="create_time" width="170" />
        <!-- 操作列：横向滚动时固定在右侧 -->
        <el-table-column label="操作" width="180" fixed="right" class-name="op-col">
          <!-- 默认插槽：行级操作 -->
          <template #default="{ row }">
            <!-- 编辑：把当前行带入共用弹窗 -->
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <!-- 删除：单条删除前二次确认 -->
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <!-- 分页容器 -->
      <div class="pagination-wrap">
        <!-- 分页：current-page 与 page-size 双向绑定 query，变化触发 @change 重新查询 -->
        <el-pagination background layout="total, sizes, prev, pager, next, jumper"
          :total="total" v-model:current-page="query.page" v-model:page-size="query.page_size"
          :page-sizes="[10, 20, 50, 100]" @change="fetchList" />
        <!-- 说明：每页可选 10/20/50/100 条 -->
      </div>
    </el-card>

    <!-- 新增/编辑弹窗：共用一套表单，标题由 dialogTitle 动态切换 -->
    <el-dialog :title="dialogTitle" v-model="dialogVisible" width="520px" :close-on-click-modal="false" destroy-on-close>
      <!-- 表单：formRef 用于提交校验；label-width 110px 适配较长的"时间窗口(秒)"标签 -->
      <el-form ref="formRef" :model="form" :rules="rules" label-width="110px">
        <!-- 栅格布局：gutter=12 -->
        <el-row :gutter="12">
          <!-- 规则名称：整行 -->
          <el-col :span="24">
            <!-- 表单项：rule_name 必填 -->
            <el-form-item label="规则名称" prop="rule_name">
              <!-- 输入框：maxlength 与后端字段长度一致，防止超长入库 -->
              <el-input v-model="form.rule_name" placeholder="请输入规则名称" maxlength="100" />
            </el-form-item>
          </el-col>
          <!-- 限流 URL：整行 -->
          <el-col :span="24">
            <!-- 表单项：limit_url 必填 -->
            <el-form-item label="限流URL" prop="limit_url">
              <!-- 输入框：提示可用通配写法，实际匹配方式由后端实现 -->
              <el-input v-model="form.limit_url" placeholder="如 /api/**" maxlength="200" />
            </el-form-item>
          </el-col>
          <!-- 时间窗口：半行 -->
          <el-col :span="12">
            <!-- 表单项：period_sec 为窗口长度（秒） -->
            <el-form-item label="时间窗口(秒)" prop="period_sec">
              <!-- 数字输入：限制 1~3600 秒，避免 0 秒窗口或超过 1 小时的无意义配置 -->
              <el-input-number v-model="form.period_sec" :min="1" :max="3600" />
            </el-form-item>
          </el-col>
          <!-- 最大次数：半行 -->
          <el-col :span="12">
            <!-- 表单项：max_count 为窗口内允许的最大请求数 -->
            <el-form-item label="最大次数" prop="max_count">
              <!-- 数字输入：限制 1~10000 次，防止误填极端值导致接口不可用或限流失效 -->
              <el-input-number v-model="form.max_count" :min="1" :max="10000" />
            </el-form-item>
          </el-col>
          <!-- 状态：整行 -->
          <el-col :span="24">
            <!-- 表单项：status 取 1/0 -->
            <el-form-item label="状态" prop="status">
              <!-- 开关：显式指定 active/inactive 值，保证与后端整型字段一致 -->
              <el-switch v-model="form.status" :active-value="1" :inactive-value="0" active-text="启用" inactive-text="停用" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <!-- 底部插槽 -->
      <template #footer>
        <!-- 取消：仅关闭弹窗 -->
        <el-button @click="dialogVisible=false">取消</el-button>
        <!-- 确定：saving 期间禁用并转圈，防止重复提交 -->
        <el-button type="primary" :loading="saving" @click="submitForm">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
// 组合式 API：ref 管理状态值，reactive 管理查询/表单对象，onMounted 挂载后首次拉取
import { ref, reactive, onMounted } from 'vue'
// Element Plus 消息提示与确认框：结果反馈、删除前二次确认
import { ElMessage, ElMessageBox } from 'element-plus'
// 按钮图标：Search 查询、Refresh 重置、Plus 新增、Delete 删除
import { Search, Refresh, Plus, Delete } from '@element-plus/icons-vue'
// 统一请求实例：内置 baseURL=/api、token 注入与错误提示
import request from '@/utils/request'

// 表格加载态：请求期间显示遮罩
const loading = ref(false)
// 当前页规则数据
const rows = ref([])
// 总条数：供分页与页头统计
const total = ref(0)
// 已勾选行：控制批量删除可用性
const selection = ref([])
// 保存中标记：防止弹窗内重复提交
const saving = ref(false)
// 弹窗显隐开关
const dialogVisible = ref(false)
// 弹窗标题：新增/编辑动态切换
const dialogTitle = ref('新增限流规则')
// 表单实例：提交时触发校验
const formRef = ref()

// 查询条件默认值：作为重置基准
const query_orig = { page: 1, page_size: 10, rule_name: '', limit_url: '', status: null }
// 响应式查询对象：与基准解耦
const query = reactive({ ...query_orig })

// 表单默认值：默认 60 秒内最多 100 次，是常见的温和限流档位
const form_orig = {
  id: null, rule_name: '', limit_url: '', period_sec: 60, max_count: 100, status: 1
}
// 响应式表单对象
const form = reactive({ ...form_orig })

// 校验规则：规则名称与限流 URL 必填，失焦时校验
const rules = {
  rule_name: [{ required: true, message: '请输入规则名称', trigger: 'blur' }],
  limit_url: [{ required: true, message: '请输入限流URL', trigger: 'blur' }]
}

// 接口前缀：本模块所有接口都基于它
const apiBase = '/sec/rate_limit'

// 拉取列表：try/finally 保证失败时也能复位加载态，错误提示由 request 拦截器统一处理
async function fetchList() {
  loading.value = true
  try {
    // GET 分页查询：query 内含 page/page_size 与筛选条件
    const res = await request.get(apiBase + '/list', { params: query })
    // data.list 为当前页规则；null 时用 [] 兜底
    rows.value = res.data.list || []
    // data.total 为总条数；缺失时按 0 处理
    total.value = res.data.total || 0
  } finally { loading.value = false }
}

// 查询：条件变化回到第 1 页，避免停在超出的页码
function handleSearch() { query.page = 1; fetchList() }
// 重置：恢复默认条件（含分页参数）后重新查询
function handleReset() { Object.assign(query, query_orig); handleSearch() }
// 勾选变化：接收 el-table 回传的选中行，供批量删除
function onSelectionChange(r) { selection.value = r }

// 新增：铺默认值（id=null），避免上次编辑的 id 残留误走更新接口
function openCreate() { Object.assign(form, form_orig); dialogTitle.value = '新增限流规则'; dialogVisible.value = true }
// 编辑：默认值打底再覆盖当前行，避免后端缺字段时出现 undefined；标题同步切换
function openEdit(row) { Object.assign(form, form_orig, row); dialogTitle.value = '编辑限流规则'; dialogVisible.value = true }

// 提交表单：先校验，再按是否有 id 分流新增/更新
async function submitForm() {
  // 校验失败会 reject，后续保存逻辑不会执行
  await formRef.value.validate()
  saving.value = true
  try {
    // 有 id 视为编辑
    if (form.id) {
      // 剔除 id：id 已放到 URL，留在请求体会被当作主键字段
      const { id, ...data } = form
      // PUT 更新并提示成功
      await request.put(`${apiBase}/update/${id}`, data); ElMessage.success('更新成功')
    } else {
      // 无 id 视为新增
      await request.post(apiBase + '/create', form); ElMessage.success('新增成功')
    }
    // 成功后关闭弹窗并刷新列表
    dialogVisible.value = false; fetchList()
  } finally { saving.value = false }
}

// 单条删除：确认框取消会 reject，后续删除不会执行
async function handleDelete(row) {
  await ElMessageBox.confirm('确定删除该限流规则？', '提示', { type: 'warning' })
  // DELETE 带请求体用 data 传参；后端按 ids 数组处理，单条也传数组
  await request.delete(apiBase + '/delete', { data: { ids: [row.id] } })
  // 删除成功后提示并刷新
  ElMessage.success('删除成功'); fetchList()
}

// 批量删除：确认文案带选中数量
async function handleBatchDelete() {
  await ElMessageBox.confirm(`确定删除选中的 ${selection.value.length} 条？`, '提示', { type: 'warning' })
  // 只提交 id 集合，避免传输整行数据
  await request.delete(apiBase + '/delete', { data: { ids: selection.value.map(r => r.id) } })
  // 刷新后表格重新加载，选中态随之清空
  ElMessage.success('批量删除成功'); fetchList()
}

// 页面挂载后立即加载一次数据
onMounted(fetchList)
</script>
