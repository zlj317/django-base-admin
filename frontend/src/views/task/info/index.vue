<!-- 文件级说明：任务调度 - 定时任务信息管理页。
     职责：维护定时任务（Cron 表达式或固定间隔两种触发方式），支持立即执行、启停与删除。
     依赖：Vue 3 <script setup>、Element Plus（表格/弹窗/消息提示/图标）、@/utils/request（统一请求封装，baseURL=/api）。
     权限：通过全局 v-perm 指令按权限码（task:create/update/delete/runOnce）控制按钮显示。
     被谁使用：由 task 模块的路由挂载，是定时调度中心的任务配置入口。
     注意：本文件不含 <style> 块，页面样式来自全局样式表。 -->
<template>
  <!-- 页面根容器：套用全局 app-container 布局 -->
  <div class="app-container">
    <!-- 页头区域 -->
    <div class="page-header">
      <!-- 标题容器：主标题与统计信息横排 -->
      <div class="page-title-wrap">
        <!-- 页面主标题 -->
        <h2>任务信息</h2>
        <!-- 副标题：说明页面用途，并回显接口返回的总条数 -->
        <div class="sub">定时调度任务 · 共 {{ total }} 条</div>
      </div>
    </div>
    <!-- 查询条件卡片：shadow="never" 去掉阴影，保持后台列表页的扁平风格 -->
    <el-card shadow="never" class="search-card">
      <!-- 搜索表单：inline 横向排列；@submit.prevent 阻止回车触发默认提交刷新页面 -->
      <el-form :model="query" inline @submit.prevent>
        <!-- 任务名称筛选项：对应后端 task_name -->
        <el-form-item label="任务名称">
          <!-- 输入框：clearable 一键清空；回车即查询；固定宽度保持工具栏整齐 -->
          <el-input v-model="query.task_name" placeholder="请输入任务名称" clearable style="width: 170px" @keyup.enter="handleSearch" />
        </el-form-item>
        <!-- 任务 Key 筛选项：task_key 是调度器中注册任务的唯一标识 -->
        <el-form-item label="任务Key">
          <!-- 输入框：回车即查询 -->
          <el-input v-model="query.task_key" placeholder="请输入任务Key" clearable style="width: 170px" @keyup.enter="handleSearch" />
        </el-form-item>
        <!-- 运行状态筛选项：对应后端 status（1 运行 / 0 暂停） -->
        <el-form-item label="状态">
          <!-- 下拉框：clearable 后可查询全部状态 -->
          <el-select v-model="query.status" placeholder="全部" clearable style="width: 110px">
            <!-- 运行：调度器按触发规则正常调度 -->
            <el-option label="运行" :value="1" />
            <!-- 暂停：任务保留但不触发，便于临时停用 -->
            <el-option label="暂停" :value="0" />
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

    <!-- 数据表格卡片：头部工具栏 + 任务表格 + 分页 -->
    <el-card shadow="never" class="table-card">
      <!-- 卡片头部插槽：承载新增/批量删除 -->
      <template #header>
        <!-- 头部容器 -->
        <div class="card-header">
          <!-- 操作按钮组 -->
          <div class="card-actions">
            <!-- 新增：v-perm 无 task:create 权限时按钮不渲染；点击打开弹窗 -->
            <el-button v-perm="'task:create'" type="primary" :icon="Plus" @click="openCreate">新增</el-button>
            <!-- 批量删除：同样由权限码控制；未勾选时禁用，plain 弱化危险按钮视觉 -->
            <el-button v-perm="'task:delete'" type="danger" plain :icon="Delete" :disabled="!selection.length" @click="handleBatchDelete">批量删除</el-button>
          </div>
        </div>
      </template>
      <!-- 表格：v-loading 显示加载遮罩；stripe 斑马纹；selection-change 同步勾选行 -->
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据" @selection-change="onSelectionChange">
        <!-- 序号列：按当前页顺序自动编号 -->
        <el-table-column type="index" label="序号" width="70" align="center" />
        <!-- 多选列：为批量删除提供目标集合 -->
        <el-table-column type="selection" width="50" />
        <!-- 任务名称列：业务可读的任务名 -->
        <el-table-column label="任务名称" prop="task_name" min-width="160" show-overflow-tooltip />
        <!-- 任务 Key 列：调度器注册任务的唯一标识，代码中按它定位任务 -->
        <el-table-column label="任务Key" prop="task_key" min-width="140" show-overflow-tooltip />
        <!-- 触发类型列：区分 Cron 与固定间隔两种调度方式 -->
        <el-table-column label="类型" prop="task_type" width="90">
          <!-- 默认插槽：按 task_type 渲染标签 -->
          <template #default="{ row }">
            <!-- Cron：按表达式在固定时刻触发 -->
            <el-tag v-if="row.task_type==='cron'" size="small">Cron</el-tag>
            <!-- 间隔：每隔固定秒数触发一次 -->
            <el-tag v-else-if="row.task_type==='interval'" size="small" type="success">间隔</el-tag>
            <!-- 兜底：未知类型直接展示原值，便于排查脏数据 -->
            <span v-else>{{ row.task_type }}</span>
          </template>
        </el-table-column>
        <!-- Cron 表达式列：如 0 0 2 * * ? 表示每天 02:00:00 执行；空值用 "-" 占位 -->
        <el-table-column label="Cron表达式" prop="cron_expr" min-width="140" show-overflow-tooltip>
          <!-- 默认插槽：空值（间隔型任务）统一显示短横线，保持表格对齐 -->
          <template #default="{ row }">{{ row.cron_expr || '-' }}</template>
        </el-table-column>
        <!-- 间隔秒列：间隔型任务的触发周期（秒），其他类型显示 "-" -->
        <el-table-column label="间隔秒" prop="interval_sec" width="90">
          <!-- 默认插槽：0/空值视为未配置，用短横线占位 -->
          <template #default="{ row }">{{ row.interval_sec || '-' }}</template>
        </el-table-column>
        <!-- 失败重试列：仅在开启重试时显示次数，否则显示 "-" -->
        <el-table-column label="失败重试" prop="retry_count" width="90">
          <!-- 默认插槽：retry_on_fail 为真时展示 N 次，retry_count 缺失按 0 次展示 -->
          <template #default="{ row }">{{ row.retry_on_fail ? (row.retry_count || 0) + '次' : '-' }}</template>
        </el-table-column>
        <!-- 状态列：开关直接控制任务启停 -->
        <el-table-column label="状态" width="90" align="center">
          <!-- 默认插槽：开关绑定当前行 status -->
          <template #default="{ row }">
            <!-- 开关：v-model 先改本地值，@change 再调后端启停接口；v-perm 无 task:update 权限时不可操作 -->
            <el-switch v-model="row.status" :active-value="1" :inactive-value="0" v-perm="'task:update'" @change="handleStatusChange(row)" />
          </template>
        </el-table-column>
        <!-- 创建时间列 -->
        <el-table-column label="创建时间" prop="create_time" width="170" />
        <!-- 操作列：横向滚动时固定在右侧 -->
        <el-table-column label="操作" width="260" fixed="right" class-name="op-col">
          <!-- 默认插槽：行级操作，均由权限码控制显示 -->
          <template #default="{ row }">
            <!-- 编辑：打开弹窗，任务 Key 在编辑态禁用 -->
            <el-button v-perm="'task:update'" link type="primary" @click="openEdit(row)">编辑</el-button>
            <!-- 立即执行：手动触发一次调度，不改变原有触发计划 -->
            <el-button v-perm="'task:runOnce'" link type="success" @click="handleRunNow(row)">立即执行</el-button>
            <!-- 删除：单条删除前二次确认 -->
            <el-button v-perm="'task:delete'" link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <!-- 分页容器 -->
      <div class="pagination-wrap">
        <!-- 分页：页码与每页条数双向绑定 query，变化触发 @change 重新查询 -->
        <el-pagination background layout="total, sizes, prev, pager, next, jumper"
          :total="total" v-model:current-page="query.page" v-model:page-size="query.page_size"
          :page-sizes="[10, 20, 50, 100]" @change="fetchList" />
        <!-- 说明：每页可选 10/20/50/100 条 -->
      </div>
    </el-card>

    <!-- 新增/编辑弹窗：共用一套表单，标题由 dialogTitle 动态切换 -->
    <el-dialog :title="dialogTitle" v-model="dialogVisible" width="640px" :close-on-click-modal="false" destroy-on-close>
      <!-- 表单：formRef 用于提交校验；label-width 110px 适配"Cron表达式"等较长标签 -->
      <el-form ref="formRef" :model="form" :rules="rules" label-width="110px">
        <!-- 任务名称：必填 -->
        <el-form-item label="任务名称" prop="task_name">
          <!-- 输入框：maxlength 与后端字段长度一致 -->
          <el-input v-model="form.task_name" placeholder="请输入任务名称" maxlength="100" />
        </el-form-item>
        <!-- 任务 Key：调度器内唯一标识，编辑态禁止修改 -->
        <el-form-item label="任务Key" prop="task_key">
          <!-- 输入框：提示命名示例；:disabled="!!form.id" 保证编辑时不改 Key，避免调度器找不到任务 -->
          <el-input v-model="form.task_key" placeholder="如 report_daily_sync" maxlength="100" :disabled="!!form.id" />
        </el-form-item>
        <!-- 任务类型：切换时触发 onTypeChange 清理另一套触发配置 -->
        <el-form-item label="任务类型" prop="task_type">
          <!-- 下拉框：宽度撑满；@change 用于清空不适用的字段，避免提交矛盾数据 -->
          <el-select v-model="form.task_type" style="width:100%" @change="onTypeChange">
            <!-- Cron：按表达式定时触发 -->
            <el-option label="Cron表达式" value="cron" />
            <!-- 固定间隔：按秒数周期性触发 -->
            <el-option label="固定间隔" value="interval" />
          </el-select>
        </el-form-item>
        <!-- Cron 表达式：仅 Cron 类型显示，v-if 保证切换类型后不提交无效字段 -->
        <el-form-item v-if="form.task_type==='cron'" label="Cron表达式" prop="cron_expr">
          <!-- 输入框：示例 0 0 2 * * ? 为 Quartz 六段写法（秒 分 时 日 月 周），即每天 02:00:00 执行 -->
          <el-input v-model="form.cron_expr" placeholder="如 0 0 2 * * ?" maxlength="64" />
        </el-form-item>
        <!-- 间隔秒：仅固定间隔类型显示 -->
        <el-form-item v-if="form.task_type==='interval'" label="间隔秒" prop="interval_sec">
          <!-- 数字输入：1 秒到 8640000 秒（100 天），防止误填超大间隔导致任务几乎不触发 -->
          <el-input-number v-model="form.interval_sec" :min="1" :max="8640000" />
        </el-form-item>
        <!-- 任务参数：传给任务函数的业务参数 -->
        <el-form-item label="参数" prop="params">
          <!-- 文本域：3 行；内容需为 JSON 字符串，由后端解析后注入任务 -->
          <el-input v-model="form.params" type="textarea" :rows="3" placeholder='JSON字符串，如 {"key":"val"}' />
        </el-form-item>
        <!-- 初始状态：决定保存后任务是否立即参与调度 -->
        <el-form-item label="状态" prop="status">
          <!-- 单选组：1 运行、0 暂停 -->
          <el-radio-group v-model="form.status">
            <!-- 运行：保存后调度器按触发规则开始调度 -->
            <el-radio :value="1">运行</el-radio>
            <!-- 暂停：保存后先不触发，后续可在列表中开启 -->
            <el-radio :value="0">暂停</el-radio>
          </el-radio-group>
        </el-form-item>
        <!-- 失败重试开关：关闭时无需填写重试次数 -->
        <el-form-item label="失败重试" prop="retry_on_fail">
          <!-- 开关：1/0 整型取值，与后端字段一致 -->
          <el-switch v-model="form.retry_on_fail" :active-value="1" :inactive-value="0" />
        </el-form-item>
        <!-- 重试次数：仅开启失败重试时显示 -->
        <el-form-item v-if="form.retry_on_fail" label="重试次数" prop="retry_count">
          <!-- 数字输入：1~10 次，避免无限重试放大故障 -->
          <el-input-number v-model="form.retry_count" :min="1" :max="10" />
        </el-form-item>
        <!-- 备注：非必填 -->
        <el-form-item label="备注" prop="remark">
          <!-- 文本域：2 行 -->
          <el-input v-model="form.remark" type="textarea" :rows="2" placeholder="请输入备注" />
        </el-form-item>
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
// Element Plus 消息提示与确认框：结果反馈、立即执行/删除前二次确认
import { ElMessage, ElMessageBox } from 'element-plus'
// 按钮图标：Search 查询、Refresh 重置、Plus 新增、Delete 删除
import { Search, Refresh, Plus, Delete } from '@element-plus/icons-vue'
// 统一请求实例：内置 baseURL=/api、token 注入与错误提示
import request from '@/utils/request'

// 表格加载态：请求期间显示遮罩
const loading = ref(false)
// 当前页任务数据
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
const dialogTitle = ref('新增')
// 表单实例：提交时触发校验
const formRef = ref()

// 查询条件默认值：作为重置基准
const query_orig = { page: 1, page_size: 10, task_name: '', task_key: '', status: null }
// 响应式查询对象：与基准解耦
const query = reactive({ ...query_orig })

// 表单默认值：默认 Cron 类型、每 60 秒间隔、运行状态、关闭失败重试
const form_orig = {
  id: null, task_name: '', task_key: '', task_type: 'cron', cron_expr: '',
  interval_sec: 60, params: '', status: 1, retry_on_fail: 0, retry_count: 3, remark: ''
}
// 响应式表单对象
const form = reactive({ ...form_orig })

// 校验规则：名称、Key、类型、Cron 表达式必填；Cron 规则常驻，由 v-if 保证只在 Cron 类型时校验
const rules = {
  task_name: [{ required: true, message: '请输入任务名称', trigger: 'blur' }],
  task_key: [{ required: true, message: '请输入任务Key', trigger: 'blur' }],
  task_type: [{ required: true, message: '请选择任务类型', trigger: 'change' }],
  cron_expr: [{ required: true, message: '请输入Cron表达式', trigger: 'blur' }]
}

// 接口地址映射：把动作名映射到具体 URL，避免每个函数里重复拼接字符串
function apiUrl(action) {
  // 本模块统一前缀
  const base = '/task/info'
  // 按动作返回对应地址；未知动作返回 undefined，便于尽早暴露拼写错误
  return {
    list: base + '/list',
    create: base + '/create',
    update: base + '/update',
    delete: base + '/delete'
  }[action]
}

// 拉取列表：try/finally 保证失败时也能复位加载态，错误提示由 request 拦截器统一处理
async function fetchList() {
  loading.value = true
  try {
    // GET 分页查询：query 内含分页与筛选条件
    const res = await request.get(apiUrl('list'), { params: query })
    // data.list 为当前页任务；null 时用 [] 兜底
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

// 切换任务类型：清空另一套触发配置，避免 form 同时带着 cron_expr 和 interval_sec 提交
function onTypeChange() {
  // 选 Cron 时重置间隔默认值 60 秒（间隔字段此时不展示，但保持合理默认）
  if (form.task_type === 'cron') form.interval_sec = 60
  // 选固定间隔时清空 Cron 表达式，防止后端按残留表达式调度
  else form.cron_expr = ''
}

// 新增：铺默认值（id=null），避免上次编辑的 id 残留误走更新接口
function openCreate() { Object.assign(form, form_orig); dialogTitle.value = '新增任务'; dialogVisible.value = true }
// 编辑：默认值打底再覆盖当前行，避免后端缺字段时出现 undefined；标题同步切换
function openEdit(row) { Object.assign(form, form_orig, row); dialogTitle.value = '编辑任务'; dialogVisible.value = true }

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
      await request.put(`${apiUrl('update')}/${id}`, data); ElMessage.success('更新成功')
    } else {
      // 无 id 视为新增
      await request.post(apiUrl('create'), form); ElMessage.success('新增成功')
    }
    // 成功后关闭弹窗并刷新列表
    dialogVisible.value = false; fetchList()
  } finally { saving.value = false }
}

// 立即执行：确认后手动触发一次，属于有副作用的写操作（会真实跑一遍任务）
async function handleRunNow(row) {
  await ElMessageBox.confirm(`确定立即执行任务「${row.task_name}」？`, '提示', { type: 'warning' })
  // POST /run_once/{id}：由后端立即投递一次执行，不改变原有调度计划
  await request.post(`/task/info/run_once/${row.id}`)
  // 只提示已触发，不刷新列表：任务是否成功需到"任务日志"页查看
  ElMessage.success('已触发立即执行')
}

// 状态开关变更：开关已先改本地值，这里再把新状态提交给后端
async function handleStatusChange(row) {
  // PUT /status/{id}：后端据此启动或暂停调度器中的任务
  await request.put(`/task/info/status/${row.id}`, { status: row.status })
  // 按当前值给出启动/暂停的明确反馈
  ElMessage.success(row.status === 1 ? '已启动' : '已暂停')
}

// 单条删除：确认框取消会 reject，后续删除不会执行
async function handleDelete(row) {
  await ElMessageBox.confirm('确定删除该任务？', '提示', { type: 'warning' })
  // DELETE 带请求体用 data 传参；后端按 ids 数组处理，单条也传数组
  await request.delete(apiUrl('delete'), { data: { ids: [row.id] } })
  // 删除成功后提示并刷新
  ElMessage.success('删除成功'); fetchList()
}

// 批量删除：确认文案带选中数量
async function handleBatchDelete() {
  await ElMessageBox.confirm(`确定删除选中的 ${selection.value.length} 条任务？`, '提示', { type: 'warning' })
  // 只提交 id 集合，避免传输整行数据
  await request.delete(apiUrl('delete'), { data: { ids: selection.value.map(r => r.id) } })
  // 刷新后表格重新加载，选中态随之清空
  ElMessage.success('批量删除成功'); fetchList()
}

// 页面挂载后立即加载一次数据
onMounted(fetchList)
</script>
