<!--
  备份策略页（/backup/strategy）：
  职责：维护自动备份策略（Cron 执行周期、保留天数、是否加密、启停），支持新增/编辑/单删/批量删除与开关即时生效。
  依赖：@/utils/request 统一请求、Element Plus 表单/弹窗/表格组件与图标；样式来自全局 styles/index.css。
  使用方：后台"数据备份管理"菜单下的策略配置页，策略生效后由后端定时任务按 Cron 产出备份记录（见 backup/record）。
  注意：本页无 style 块，一切版式依赖全局样式；弹窗表单校验统一由 el-form rules 承担。
-->
<template>
  <!-- 页面根容器：沿用全局 .app-container 内边距与进场动画 -->
  <div class="app-container">
    <!-- 页面头部：标题 + 策略总数副标题 -->
    <div class="page-header">
      <!-- 标题容器：主标题与副标题纵向排列 -->
      <div class="page-title-wrap">
        <!-- 主标题 -->
        <h2>备份策略</h2>
        <!-- 副标题：total 取自列表接口，随筛选条件变化 -->
        <div class="sub">自动备份策略管理 · 共 {{ total }} 条</div>
      </div>
    </div>

    <!-- 搜索区卡片：扁平无阴影，与全局列表页风格统一 -->
    <el-card shadow="never" class="search-card">
      <!-- 查询表单：inline 横向排列；@submit.prevent 阻止回车时的原生表单提交与整页刷新 -->
      <el-form :model="query" inline @submit.prevent>
        <!-- 策略名称筛选：模糊匹配；回车即查询，减少鼠标操作 -->
        <el-form-item label="策略名称">
          <el-input v-model="query.strategy_name" placeholder="请输入策略名称" clearable style="width: 170px" @keyup.enter="handleSearch" />
        </el-form-item>
        <!-- 启用状态筛选：1=启用（定时任务会调度）；0=停用（保留配置但不执行）；清空表示全部 -->
        <el-form-item label="状态">
          <el-select v-model="query.status" placeholder="全部" clearable style="width: 110px">
            <!-- 状态枚举：1 启用、0 停用；用数字与后端 status 字段保持一致 -->
            <el-option label="启用" :value="1" />
            <el-option label="停用" :value="0" />
          </el-select>
        </el-form-item>
        <!-- 操作按钮：查询会回到第一页；重置还原全部条件 -->
        <el-form-item>
          <!-- 按当前条件查询 -->
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <!-- 清空筛选条件并重新查询 -->
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 列表区卡片：承载表格、批量操作与分页 -->
    <el-card shadow="never" class="table-card">
      <!-- 卡片头部插槽：放置新增与批量删除入口，与表格数据区分离 -->
      <template #header>
        <!-- 头部容器 -->
        <div class="card-header">
          <!-- 操作按钮组 -->
          <div class="card-actions">
            <!-- 新增策略：打开空白弹窗，提交前由表单 rules 校验 -->
            <el-button type="primary" :icon="Plus" @click="openCreate">新增</el-button>
            <!-- 批量删除：未勾选任何行时禁用，避免发出空 ids 请求；plain 样式表示危险但非主操作 -->
            <el-button type="danger" plain :icon="Delete" :disabled="!selection.length" @click="handleBatchDelete">批量删除</el-button>
          </div>
        </div>
      </template>
      <!-- 数据表格：loading 遮罩 + 斑马纹；勾选行同步到 selection 供批量删除使用 -->
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据" @selection-change="onSelectionChange">
        <!-- 序号列：前端行号，便于对照 -->
        <el-table-column type="index" label="序号" width="70" align="center" />
        <!-- 多选列：批量删除依赖其 selection-change 事件收集 id -->
        <el-table-column type="selection" width="50" />
        <!-- 策略名称列：自适应宽度，超长省略并用 tooltip 完整展示 -->
        <el-table-column label="策略名称" prop="strategy_name" min-width="180" show-overflow-tooltip />
        <!-- Cron 表达式列：Quartz 风格（秒 分 时 日 月 周），如 0 0 2 * * ? 表示每天 02:00 执行，是自动备份的调度依据 -->
        <el-table-column label="Cron表达式" prop="cron_expr" width="160" />
        <!-- 保留天数列：该策略产出的备份文件保留时长，超过天数后由后端自动清理，防止磁盘被历史备份占满 -->
        <el-table-column label="保留天数" prop="keep_days" width="100" />
        <!-- 加密列：encrypt_flag=1 表示备份文件落盘时加密，涉及敏感数据时应开启 -->
        <el-table-column label="加密" width="70" align="center">
          <template #default="{ row }">
            <!-- 仅 1 视为加密，用警示色提醒下载后需要解密流程 -->
            <el-tag v-if="row.encrypt_flag===1" size="small" type="warning">是</el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <!-- 状态列：用开关直接启停策略，改动即调接口，无需进入编辑弹窗 -->
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <!-- v-model 先改本地 row.status 再触发 handleStatusChange：交互即时，但接口失败时本地值不会自动回滚 -->
            <el-switch v-model="row.status" :active-value="1" :inactive-value="0" @change="handleStatusChange(row)" />
          </template>
        </el-table-column>
        <!-- 创建时间列：由后端格式化的时间串直接展示 -->
        <el-table-column label="创建时间" prop="create_time" width="170" />
        <!-- 操作列：固定在右侧，横向滚动时仍可见 -->
        <el-table-column label="操作" width="180" fixed="right" class-name="op-col">
          <template #default="{ row }">
            <!-- 编辑：把当前行数据合并进表单并打开弹窗 -->
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <!-- 删除：二次确认后调用删除接口 -->
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <!-- 分页容器：统一右对齐与留白 -->
      <div class="pagination-wrap">
        <!-- 分页器：layout 含总数/每页条数/翻页/跳页；@change 在页码或每页条数变动时刷新数据 -->
        <el-pagination background layout="total, sizes, prev, pager, next, jumper"
          :total="total" v-model:current-page="query.page" v-model:page-size="query.page_size"
          :page-sizes="[10, 20, 50, 100]" @change="fetchList" />
      </div>
    </el-card>

    <!-- 新增/编辑弹窗：标题随场景变化；close-on-click-modal=false 防止误点遮罩丢失已填内容；destroy-on-close 关闭后销毁子组件，避免下次打开残留校验错误 -->
    <el-dialog :title="dialogTitle" v-model="dialogVisible" width="560px" :close-on-click-modal="false" destroy-on-close>
      <!-- 策略表单：ref 供提交时调用 validate；rules 定义必填校验；label-width 固定标签宽度保持对齐 -->
      <el-form ref="formRef" :model="form" :rules="rules" label-width="110px">
        <!-- 栅格布局：gutter 为列间距；24 栅格制，整行字段 span=24，半行字段 span=12 -->
        <el-row :gutter="12">
          <!-- 策略名称占整行：名称较长，需要足够输入宽度 -->
          <el-col :span="24">
            <el-form-item label="策略名称" prop="strategy_name">
              <!-- maxlength=100 与后端字段长度一致，前端先做长度约束减少无效请求 -->
              <el-input v-model="form.strategy_name" placeholder="请输入策略名称" maxlength="100" />
            </el-form-item>
          </el-col>
          <!-- Cron 占整行：表达式较长且需要完整可见，便于核对 -->
          <el-col :span="24">
            <el-form-item label="Cron表达式" prop="cron_expr">
              <!-- 示例 0 0 2 * * ?：Quartz 六段式，秒=0、分=0、时=2，即每天凌晨 2 点执行；maxlength=64 限制异常超长输入 -->
              <el-input v-model="form.cron_expr" placeholder="如 0 0 2 * * ?" maxlength="64" />
            </el-form-item>
          </el-col>
          <!-- 保留天数占半行：数值字段，与加密开关同行节省纵向空间 -->
          <el-col :span="12">
            <el-form-item label="保留天数" prop="keep_days">
              <!-- 1~3650 天（约 10 年）：下限防止 0 天即删，上限避免不合理配置 -->
              <el-input-number v-model="form.keep_days" :min="1" :max="3650" />
            </el-form-item>
          </el-col>
          <!-- 加密开关占半行：1=加密落盘，0=明文存储 -->
          <el-col :span="12">
            <el-form-item label="加密备份" prop="encrypt_flag">
              <!-- 显式指定 active/inactive 值，与后端 0/1 数值字段对齐，避免布尔与数字混用 -->
              <el-switch v-model="form.encrypt_flag" :active-value="1" :inactive-value="0" />
            </el-form-item>
          </el-col>
          <!-- 状态占整行：带文字说明，明确开启后定时任务才会调度 -->
          <el-col :span="24">
            <el-form-item label="状态" prop="status">
              <!-- 启用/停用文字提示降低误操作概率；1=启用、0=停用 -->
              <el-switch v-model="form.status" :active-value="1" :inactive-value="0" active-text="启用" inactive-text="停用" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <!-- 弹窗底部插槽：取消仅关闭弹窗不改数据；确定走 submitForm 做校验与提交 -->
      <template #footer>
        <!-- 取消：直接关闭，不保留本次修改 -->
        <el-button @click="dialogVisible=false">取消</el-button>
        <!-- 确定：saving 期间禁用防止重复提交 -->
        <el-button type="primary" :loading="saving" @click="submitForm">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
// 组合式 API：ref 管理基本响应式状态，reactive 管理查询条件与表单对象，onMounted 做首次加载
import { ref, reactive, onMounted } from 'vue'
// 统一提示与确认框：保存成功提示、删除/批量删除二次确认
import { ElMessage, ElMessageBox } from 'element-plus'
// 图标：Search 查询、Refresh 重置、Plus 新增、Delete 批量删除
import { Search, Refresh, Plus, Delete } from '@element-plus/icons-vue'
// 统一 axios 实例：/api 前缀、自动带 token、统一错误提示
import request from '@/utils/request'

// 列表加载态：驱动表格遮罩，避免请求期间误操作
const loading = ref(false)
// 当前页数据：接口返回的本页策略列表
const rows = ref([])
// 策略总数：用于分页与副标题
const total = ref(0)
// 勾选行：批量删除时取 id 集合
const selection = ref([])
// 提交中状态：驱动"确定"按钮 loading，防止重复提交
const saving = ref(false)
// 弹窗显隐：新增与编辑共用同一弹窗
const dialogVisible = ref(false)
// 弹窗标题：新增/编辑场景文案不同，避免用户分不清当前模式
const dialogTitle = ref('新增备份策略')
// 表单组件实例：提交前调用 validate() 做整体校验
const formRef = ref()

// 查询条件初值：作为"重置"的还原基准；status 用 null 表示全部（0 为有效状态，不能用 falsy 判断）
const query_orig = { page: 1, page_size: 10, strategy_name: '', status: null }
// 查询条件响应式副本：展开拷贝，避免重置时把初值对象本身改掉
const query = reactive({ ...query_orig })

// 表单初值：keep_days=30 表示默认保留 30 天；encrypt_flag=0 默认不加密（按需开启，避免性能与解密成本）；status=1 默认启用
const form_orig = {
  id: null, strategy_name: '', cron_expr: '', keep_days: 30, encrypt_flag: 0, status: 1
}
// 表单响应式副本：新增/编辑都复用这一个对象，靠 Object.assign 覆写字段
const form = reactive({ ...form_orig })

// 表单校验规则：策略名称与 Cron 均必填；trigger=blur 表示失焦即校验，及时反馈
const rules = {
  strategy_name: [{ required: true, message: '请输入策略名称', trigger: 'blur' }],
  cron_expr: [{ required: true, message: '请输入Cron表达式', trigger: 'blur' }]
}

// 接口基址：策略相关接口统一前缀
const apiBase = '/backup/strategy'

// 拉取列表：携带查询条件（含分页）请求后端，返回 { list, total }
async function fetchList() {
  // 请求前开启 loading，明确数据正在刷新
  loading.value = true
  try {
    // GET /backup/strategy/list：空串/null 条件由后端忽略
    const res = await request.get(apiBase + '/list', { params: query })
    // 兜底空数组，保证无数据时表格正常显示"暂无数据"
    rows.value = res.data.list || []
    // 兜底 0，保证分页器 total 始终为数字
    total.value = res.data.total || 0
  // 成功失败都关闭 loading，避免遮罩卡死
  } finally { loading.value = false }
}

// 查询：条件变化后必须回到第一页，否则可能超出新结果集页码而显示空表
function handleSearch() { query.page = 1; fetchList() }
// 重置：还原查询初值（含分页）后重新查询
function handleReset() { Object.assign(query, query_orig); handleSearch() }
// 勾选变化：把表格当前选中行同步到 selection，供批量删除按钮的禁用态与 id 收集使用
function onSelectionChange(r) { selection.value = r }

// 打开新增：先把表单重置为初值（清掉上次编辑残留），再切换标题与显隐
function openCreate() { Object.assign(form, form_orig); dialogTitle.value = '新增备份策略'; dialogVisible.value = true }
// 打开编辑：先还原初值再合并当前行数据，保证后端未返回的字段有合理默认值（如 keep_days）
function openEdit(row) { Object.assign(form, form_orig, row); dialogTitle.value = '编辑备份策略'; dialogVisible.value = true }

// 提交表单：按 form.id 是否存在区分新增/更新，成功后关闭弹窗并刷新列表
async function submitForm() {
  // 先整体校验：不通过会抛异常，直接中断后续提交
  await formRef.value.validate()
  // 进入提交态，禁用按钮防止重复点击产生重复策略
  saving.value = true
  try {
    // 有 id 走更新：解构剔除 id，避免把 id 同时放进 URL 与请求体造成后端语义混淆
    if (form.id) {
      const { id, ...data } = form
      await request.put(`${apiBase}/update/${id}`, data); ElMessage.success('更新成功')
    } else {
      // 无 id 走新增：直接把表单提交，id 为 null 由后端生成主键
      await request.post(apiBase + '/create', form); ElMessage.success('新增成功')
    }
    // 成功后关闭弹窗并刷新列表，让表格及时体现最新配置
    dialogVisible.value = false; fetchList()
  // 无论成败都结束提交态，避免按钮一直转圈
  } finally { saving.value = false }
}

// 列表内开关切换状态：立即调用专用状态接口，让启停无需进入编辑弹窗
async function handleStatusChange(row) {
  // PUT /backup/strategy/status/{id}：只提交 status 字段，避免整行覆盖带来的并发覆盖风险
  await request.put(`${apiBase}/status/${row.id}`, { status: row.status })
  // 按最新值提示结果，让用户确认操作已生效
  ElMessage.success(row.status === 1 ? '已启用' : '已停用')
}

// 删除单条策略：二次确认后调用批量删除接口（ids 只含一条）
async function handleDelete(row) {
  // 删除后策略不再调度，用警告型确认框拦截误操作
  await ElMessageBox.confirm('确定删除该备份策略？', '提示', { type: 'warning' })
  // DELETE 通过 data 传请求体，与后端统一的 ids 数组约定一致
  await request.delete(apiBase + '/delete', { data: { ids: [row.id] } })
  // 成功后刷新列表，同步总数与分页
  ElMessage.success('删除成功'); fetchList()
}

// 批量删除：确认文案带上选中数量，让用户明确影响范围
async function handleBatchDelete() {
  // 危险操作二次确认；取消会抛异常并中断后续请求
  await ElMessageBox.confirm(`确定删除选中的 ${selection.value.length} 条？`, '提示', { type: 'warning' })
  // 从选中行提取 id 数组一次性提交，减少请求次数
  await request.delete(apiBase + '/delete', { data: { ids: selection.value.map(r => r.id) } })
  // 提示并刷新，勾选状态会随数据刷新自动清空
  ElMessage.success('批量删除成功'); fetchList()
}

// 首次进入页面加载第一页策略列表
onMounted(fetchList)
</script>
