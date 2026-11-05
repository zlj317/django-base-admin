<!-- 我的工单页（工单管理 / 我的工单）
     职责：只展示"与我相关"的工单，通过顶部单选在"我创建的"与"我处理的"两种视角之间切换，
           并提供查询、详情查看、解决、关闭等处理动作；不提供新建/编辑/指派/删除，避免越权操作他人工单。
     接口：GET /wo/order/list（按 creator_id 或 assignee_id 过滤）、GET /wo/type/list（类型字典）、
           GET /system/user/list（用户字典，用于把 ID 显示成姓名）、GET /wo/log/list（处理日志）、
           PUT /wo/order/solve/{id}、PUT /wo/order/close/{id}。
     依赖：utils/request（统一鉴权与错误提示）、store/auth（读取当前登录用户 id 作为过滤条件）、
           Element Plus 的卡片/表单/表格/分页/抽屉组件、@element-plus/icons-vue 图标。
     被谁使用：由后端菜单表配置的 path（如 /wo/mine）动态挂载；页面操作按钮未接 v-perm，
               最终能否解决/关闭由后端接口鉴权决定。 -->
<template>
  <!-- 页面根容器：复用全局 .app-container 的留白与进场动画，与其它业务页保持一致的版式 -->
  <div class="app-container">
    <!-- 页头：左侧标题与总数、右侧刷新按钮；本页无新建入口，刷新是唯一的页级操作 -->
    <div class="page-header">
      <!-- 标题组：全局样式统一控制标题/副标题的字号与间距 -->
      <div class="page-title-wrap">
        <!-- 主标题与菜单名称一致，强调这是"与我相关"的个人视图而非全量工单 -->
        <h2>我的工单</h2>
        <!-- 副标题展示当前范围下的总条数，total 随筛选/视角切换而变化 -->
        <div class="sub">与我相关 · 共 {{ total }} 条</div>
      </div>
      <!-- 页头操作区：刷新只重拉列表，不重拉类型/用户字典，省一次请求且字典数据基本不变 -->
      <div class="page-header-actions">
        <el-button :icon="Refresh" @click="fetchList">刷新</el-button>
      </div>
    </div>

    <!-- 查询区卡片：shadow="never" 弱化层级，让表格成为视觉主体 -->
    <el-card shadow="never" class="search-card">
      <!-- inline 横排筛选项；@submit.prevent 阻止回车触发表单默认提交导致整页刷新 -->
      <el-form :model="query" inline @submit.prevent>
        <!-- 筛选项：标题关键字，只透传给后端做匹配，前端不做本地过滤 -->
        <el-form-item label="标题">
          <!-- clearable 一键清空；回车直接查询；180px 比工单列表页略宽，因为本页筛选项更少、空间更充裕 -->
          <el-input v-model="query.title" placeholder="请输入工单标题" clearable style="width: 180px" @keyup.enter="handleSearch" />
        </el-form-item>
        <!-- 筛选项：状态，用下拉限定取值，避免手填非法状态 -->
        <el-form-item label="状态">
          <!-- 清空即"全部"（初始 null）；120px 足够容纳四种状态文案 -->
          <el-select v-model="query.status" placeholder="全部" clearable style="width: 120px">
            <!-- 与表格状态标签共用 statusOptions，保证筛选与展示文案一致 -->
            <el-option v-for="s in statusOptions" :key="s.value" :label="s.label" :value="s.value" />
          </el-select>
        </el-form-item>
        <!-- 筛选项：优先级，便于在个人待办里先看高优先级工单 -->
        <el-form-item label="优先级">
          <!-- 110px 容纳"全部/低/中/高"已足够，比状态框略窄以减少无效留白 -->
          <el-select v-model="query.priority" placeholder="全部" clearable style="width: 110px">
            <el-option v-for="p in priorityOptions" :key="p.value" :label="p.label" :value="p.value" />
          </el-select>
        </el-form-item>
        <!-- 操作按钮组无 label，紧跟筛选项之后 -->
        <el-form-item>
          <!-- 查询：handleSearch 先回到第一页，避免停留在越界页出现空列表 -->
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <!-- 重置：回填默认条件后重新查询；不弹二次确认，条件可随时重填 -->
          <el-button :icon="RefreshRight" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 表格卡片：头部放"视角切换"，表体放数据；与查询区拆开，切换/查询只刷新表体 -->
    <el-card shadow="never" class="table-card">
      <!-- 卡片头部插槽：只放一个单选组，因为"我创建的/我处理的"是本页最核心的视图切换 -->
      <template #header>
        <div class="card-header">
          <!-- 视角切换：change 触发 handleScopeChange，会把页码重置为 1 再按新视角请求 -->
          <el-radio-group v-model="scope" @change="handleScopeChange">
            <!-- 我创建的：后端按 creator_id=当前用户过滤，对应"我提单、我跟踪"的场景 -->
            <el-radio-button value="created">我创建的</el-radio-button>
            <!-- 我处理的：后端按 assignee_id=当前用户过滤，对应"待我处理"的个人工作台 -->
            <el-radio-button value="assigned">我处理的</el-radio-button>
          </el-radio-group>
        </div>
      </template>
      <!-- 表格：v-loading 防止请求期间重复操作；stripe 斑马纹辅助读行；empty-text 用"暂无工单"更贴合本页语义 -->
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无工单">
        <!-- 序号列：按当前页递增，仅用于阅读定位 -->
        <el-table-column type="index" label="序号" width="70" align="center" />
        <!-- 工单号：业务唯一标识，超长时省略并悬浮显示全文 -->
        <el-table-column label="工单号" prop="order_no" min-width="150" show-overflow-tooltip />
        <!-- 标题：工单核心信息，给更宽的最小宽度以减少省略 -->
        <el-table-column label="标题" prop="title" min-width="200" show-overflow-tooltip />
        <!-- 类型列：优先用后端名称；缺失时用 typeName 从本地类型字典反查，字典也未命中则显示 "-" -->
        <el-table-column label="类型" min-width="100">
          <template #default="{ row }">{{ row.type_name || typeName(row.order_type_id) }}</template>
        </el-table-column>
        <!-- 优先级列：居中彩色标签，颜色由 priorityTag 统一映射（低绿/中黄/高红） -->
        <el-table-column label="优先级" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="priorityTag(row.priority)" effect="light" size="small">{{ priorityLabel(row.priority) }}</el-tag>
          </template>
        </el-table-column>
        <!-- 状态列：标签色与全站一致，已解决 success、处理中 primary、待处理/已关闭 info -->
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="statusTag(row.status)" effect="light" size="small">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <!-- 创建人列：先查 userNames 字典显示昵称/用户名，字典未命中再退回显示 ID，避免出现空白 -->
        <el-table-column label="创建人" min-width="100">
          <template #default="{ row }">{{ userNames[row.creator_id] || row.creator_id || '-' }}</template>
        </el-table-column>
        <!-- 处理人列：同上；未指派时 assignee_id 为空，显示 "-" -->
        <el-table-column label="处理人" min-width="100">
          <template #default="{ row }">{{ userNames[row.assignee_id] || row.assignee_id || '-' }}</template>
        </el-table-column>
        <!-- 创建时间：本页不展示期望/关闭时间，只保留创建时间用于判断工单新旧 -->
        <el-table-column label="创建时间" prop="create_time" width="170" />
        <!-- 操作列：fixed="right" 固定右侧；190px 仅容纳"详情/解决/关闭"三个 link 按钮，不做越权操作 -->
        <el-table-column label="操作" width="190" fixed="right" class-name="op-col">
          <template #default="{ row }">
            <!-- 按钮容器：nowrap 保证窄屏时按钮单行不换行 -->
            <div class="op-btns">
              <!-- 详情：只读抽屉，任意状态可看，不改变工单状态 -->
              <el-button link type="primary" @click="openDetail(row)">详情</el-button>
              <!-- 解决：仅"处理中(1)"可标记已解决，待处理必须先被指派，已解决/已关闭不再重复操作 -->
              <el-button link type="success" v-if="row.status === 1" @click="handleSolve(row)">解决</el-button>
              <!-- 关闭：除"已关闭(3)"外均可见，用于终止不再处理的工单 -->
              <el-button link type="info" v-if="row.status !== 3" @click="handleClose(row)">关闭</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
      <!-- 分页条：background 底色块提升点击辨识度 -->
      <div class="pagination-wrap">
        <!-- v-model 直接改写 query.page/page_size；@change 在页码或页大小变化时重新请求 -->
        <el-pagination background layout="total, sizes, prev, pager, next, jumper"
          :total="total" v-model:current-page="query.page" v-model:page-size="query.page_size"
          :page-sizes="[10, 20, 50, 100]" @change="fetchList" />
      </div>
    </el-card>

    <!-- 详情抽屉：只读展示工单信息与处理日志；destroy-on-close 保证每次打开都重新初始化内容与时间线 -->
    <el-drawer v-model="detailVisible" :title="detailData.title || '工单详情'" size="540px" destroy-on-close>
      <!-- 数据未就绪（detailData.id 为空）时不渲染，避免出现满屏占位符 -->
      <div v-if="detailData.id" class="detail-body">
        <!-- 描述列表：单列 + border，在 540px 抽屉中纵向展示最易读 -->
        <el-descriptions :column="1" border>
          <!-- 工单号：无值时统一显示 "-"，避免空单元格 -->
          <el-descriptions-item label="工单号">{{ detailData.order_no || '-' }}</el-descriptions-item>
          <!-- 状态：复用全站状态映射，保证与列表标签同色同文案 -->
          <el-descriptions-item label="状态">
            <el-tag :type="statusTag(detailData.status)" effect="light">{{ statusLabel(detailData.status) }}</el-tag>
          </el-descriptions-item>
          <!-- 优先级：同样复用映射，形成绿/黄/红的统一语义 -->
          <el-descriptions-item label="优先级">
            <el-tag :type="priorityTag(detailData.priority)" effect="light">{{ priorityLabel(detailData.priority) }}</el-tag>
          </el-descriptions-item>
          <!-- 工单类型：名称缺失时用本地类型字典反查 ID -->
          <el-descriptions-item label="工单类型">{{ detailData.type_name || typeName(detailData.order_type_id) }}</el-descriptions-item>
          <!-- 创建人：字典反查姓名，未命中显示 ID，再空则 "-" -->
          <el-descriptions-item label="创建人">{{ userNames[detailData.creator_id] || detailData.creator_id || '-' }}</el-descriptions-item>
          <!-- 处理人：未指派时显示 "-" -->
          <el-descriptions-item label="处理人">{{ userNames[detailData.assignee_id] || detailData.assignee_id || '-' }}</el-descriptions-item>
          <!-- 期望时间：无值显示 "-" -->
          <el-descriptions-item label="期望时间">{{ detailData.expect_time || '-' }}</el-descriptions-item>
          <!-- 关闭时间：仅关闭后才有值 -->
          <el-descriptions-item label="关闭时间">{{ detailData.close_time || '-' }}</el-descriptions-item>
          <!-- 创建时间：用于判断工单存续时长 -->
          <el-descriptions-item label="创建时间">{{ detailData.create_time || '-' }}</el-descriptions-item>
        </el-descriptions>
        <!-- 工单内容区：独立分区，长文本换行展示 -->
        <div class="detail-section">
          <div class="detail-section-title">工单内容</div>
          <!-- 空内容用"（无内容）"占位，避免抽屉出现大片空白让用户误以为加载失败 -->
          <div class="detail-content">{{ detailData.content || '（无内容）' }}</div>
        </div>
        <!-- 处理日志区：时间线形式呈现流转轨迹 -->
        <div class="detail-section">
          <div class="detail-section-title">处理日志</div>
          <!-- 有日志才渲染时间线，否则走下方空态 -->
          <el-timeline v-if="workLogs.length">
            <!-- :key 用索引（日志无稳定唯一 id）；timestamp 只认 create_time，缺失时留空 -->
            <el-timeline-item v-for="(log, i) in workLogs" :key="i" :timestamp="log.create_time || ''">
              <div>
                <!-- 操作人：用 userNames 字典把 operator_id 显示为姓名，未命中退回 ID，再兜底"系统" -->
                <strong>{{ userNames[log.operator_id] || log.operator_id || '系统' }}</strong>
                <span class="muted"> 执行了 </span>
                <!-- 动作：经 actionLabel 映射为中文（assign/solve/close/create），未识别时原样展示 -->
                <el-tag effect="light" size="small">{{ actionLabel(log.action) }}</el-tag>
              </div>
              <!-- 备注：本页读取 log.comment；工单列表页读 remark/content，两页字段命名不一致，后端实际返回哪个需确认 -->
              <div class="log-remark">{{ log.comment || '' }}</div>
            </el-timeline-item>
          </el-timeline>
          <!-- 空态提示：语气与表格空态保持一致 -->
          <div v-else class="empty-tip">暂无处理日志</div>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
// 组合式 API：ref 用于原始值/数组，reactive 用于对象（表单类数据用 Object.assign 就地更新以保持响应式）
import { ref, reactive, onMounted } from 'vue'
// ElMessage 做成功/警告轻提示；ElMessageBox 做解决/关闭这类状态变更前的二次确认
import { ElMessage, ElMessageBox } from 'element-plus'
// 图标以组件对象传入 :icon；Refresh 用于页头刷新，RefreshRight 用于查询区重置，避免两处图标雷同
import { Search, Refresh, RefreshRight } from '@element-plus/icons-vue'
// 统一请求实例：内置 baseURL=/api、token 注入、统一错误提示与 401 跳登录
import request from '@/utils/request'
// 全局登录态：仅使用 auth.user.id 作为"与我相关"的过滤条件，不涉及登录/登出逻辑
import { auth } from '@/store/auth'

// 列表加载态：绑定 el-table 的 v-loading，避免请求期间重复操作
const loading = ref(false)
// 当前页数据：每次请求成功后整体替换，保证与后端分页一致
const rows = ref([])
// 总条数：供分页器 total 与页头"共 N 条"使用
const total = ref(0)
// 当前视角：created=我创建的（按 creator_id 过滤）、assigned=我处理的（按 assignee_id 过滤）
// 默认"我创建的"，与本页"我的工单"最常见的查看诉求一致
const scope = ref('created')
// 工单类型字典：用于把 order_type_id 反查成名称（列表接口可能只回 ID）
const typeOptions = ref([])
// 用户名字典：以用户 id 为键存昵称/用户名，避免每行再发请求查人名；用 reactive 保证模板读取时响应式
const userNames = reactive({})

// 查询条件默认值：不含 scope（视角由顶部单选独立控制），重置时只回填分页与筛选条件
const query_orig = { page: 1, page_size: 10, title: '', status: null, priority: null }
// 响应式查询对象：分页组件 v-model 直接改写 page/page_size，必须用 reactive
const query = reactive({ ...query_orig })

// 状态字典：与工单列表页保持完全一致，避免同一状态在不同页面文案/顺序不同
const statusOptions = [
  { value: 0, label: '待处理' },
  { value: 1, label: '处理中' },
  { value: 2, label: '已解决' },
  { value: 3, label: '已关闭' }
]
// 优先级字典：1/2/3 对应低/中/高，与后端 tinyint 取值一致
const priorityOptions = [
  { value: 1, label: '低' },
  { value: 2, label: '中' },
  { value: 3, label: '高' }
]

// 状态值 → 文案：未知值兜底"未知"，避免空标签
function statusLabel(v) { return statusOptions.find(x => x.value === v)?.label || '未知' }
// 状态值 → 标签类型：处理中 primary 强调进行中，已解决 success，待处理/已关闭 info 弱化
function statusTag(v) { return ({ 0: 'info', 1: 'primary', 2: 'success', 3: 'info' })[v] || 'info' }
// 优先级值 → 文案：未知值兜底"未知"
function priorityLabel(v) { return priorityOptions.find(x => x.value === v)?.label || '未知' }
// 优先级值 → 标签色：低绿/中黄/高红，形成直观的紧急度梯度
function priorityTag(v) { return ({ 1: 'success', 2: 'warning', 3: 'danger' })[v] || 'info' }
// 日志动作码 → 中文：覆盖后端常见动作；未识别的码原样显示，便于发现新动作类型
function actionLabel(v) { return ({ assign: '指派', solve: '解决', close: '关闭', create: '创建' })[v] || v || '处理' }
// 类型 ID → 类型名：查本地字典；字典未加载或未命中时返回 "-"，避免模板出现 undefined
function typeName(id) { return typeOptions.value.find(t => t.id === id)?.type_name || '-' }

// 详情抽屉显隐
const detailVisible = ref(false)
// 详情数据：由列表行摊平而来，打开抽屉即可展示，无需等待详情接口
const detailData = reactive({})
// 处理日志：打开详情后异步拉取，仅用于时间线展示
const workLogs = ref([])

// 拉取列表：先复制 query 作为请求参数，再按当前视角注入用户过滤条件
// myId 存在时才加条件；auth.user 尚未加载时先不加，避免传 undefined 把查询结果清空
// 失败不在此 catch：request 拦截器已统一提示并 reject，这里只负责复位 loading
async function fetchList() {
  loading.value = true
  try {
    const params = { ...query }
    const myId = auth.user?.id
    if (myId) {
      params[scope.value === 'created' ? 'creator_id' : 'assignee_id'] = myId
    }
    const res = await request.get('/wo/order/list', { params })
    rows.value = res.data.list || []
    total.value = res.data.total || 0
  } finally { loading.value = false }
}

// 加载页面辅助字典：类型字典 + 用户字典，二者串行请求（彼此无依赖，但都只需一次）
// 两段各自 try/catch 静默失败：字典只影响"名称展示"，不应阻断列表主流程
// 用户字典一次取 500 条，超过该规模的用户将无法反查到姓名，只能回落到显示 ID
async function loadOptions() {
  try {
    const res = await request.get('/wo/type/list', { params: { page: 1, page_size: 200 } })
    typeOptions.value = res.data.list || []
  } catch { /* ignore */ }
  try {
    const res = await request.get('/system/user/list', { params: { page: 1, page_size: 500 } })
    ;(res.data.list || []).forEach(u => { userNames[u.id] = u.nickname || u.username || u.id })
  } catch { /* ignore */ }
}

// 切换视角：重置到第 1 页再请求，避免沿用旧页码导致新视角下显示空列表
function handleScopeChange() { query.page = 1; fetchList() }
// 查询：同样先回到第 1 页
function handleSearch() { query.page = 1; fetchList() }
// 重置：回填默认条件后复用查询逻辑（不清空 scope，保持用户当前视角）
function handleReset() { Object.assign(query, query_orig); handleSearch() }

// 打开详情：先摊平列表行并打开抽屉（立即有内容可看），再异步补处理日志
// 日志失败静默，仅时间线为空，不影响基本信息阅读
async function openDetail(row) {
  Object.assign(detailData, { ...row })
  workLogs.value = []
  detailVisible.value = true
  try {
    const res = await request.get('/wo/log/list', { params: { order_id: row.id, page: 1, page_size: 50 } })
    workLogs.value = res.data?.list || []
  } catch { /* ignore */ }
}

// 解决工单：二次确认后才调用接口；confirm 取消会 reject，接口调用自然不执行
// 成功后刷新列表，使状态标签从"处理中"变为"已解决"
async function handleSolve(row) {
  await ElMessageBox.confirm(`确定将工单「${row.title}」标记为已解决？`, '提示', { type: 'warning' })
  await request.put(`/wo/order/solve/${row.id}`)
  ElMessage.success('工单已解决'); fetchList()
}

// 关闭工单：同样先确认再执行；关闭为终态，故用 warning 图标强调影响
async function handleClose(row) {
  await ElMessageBox.confirm(`确定关闭工单「${row.title}」？`, '提示', { type: 'warning' })
  await request.put(`/wo/order/close/${row.id}`)
  ElMessage.success('工单已关闭'); fetchList()
}

// 首次挂载：并行发起列表与字典请求，缩短首屏等待；两者互不依赖，无需串行 await
onMounted(() => { fetchList(); loadOptions() })
</script>

<style scoped>
/* scoped：样式仅作用于本页，避免与工单列表页的同名类互相影响；颜色统一使用 --app-* 变量，暗色主题自动适配 */
/* 详情抽屉主体：左右留 6px，让内容不贴边线，也不至于过度缩窄 */
.detail-body { padding: 0 6px; }
/* 详情分区：与上一块间隔 20px，区隔"基本信息 / 内容 / 日志"三层信息 */
.detail-section { margin-top: 20px; }
/* 分区标题：14px 加粗、主文本色 --app-text-1，底部细线使用 --app-border-light，跟随主题明暗切换 */
.detail-section-title {
  font-size: 14px; font-weight: 600; color: var(--app-text-1); margin-bottom: 10px;
  padding-bottom: 6px; border-bottom: 1px solid var(--app-border-light);
}
/* 内容块：浅底 --app-surface-2 做视觉容器；pre-wrap 保留换行；break-word 只在不破坏单词处换行，适合中文描述 */
.detail-content { font-size: 13px; color: var(--app-text-2); line-height: 1.8; padding: 12px 14px; background: var(--app-surface-2); border-radius: 8px; white-space: pre-wrap; word-break: break-word; }
/* 次要文字：三级弱化色 --app-text-3，用于"执行了"这类连接语 */
.muted { color: var(--app-text-3); }
/* 日志备注：与操作人行拉开 6px，12px 正文字色，保持时间线紧凑 */
.log-remark { margin-top: 6px; font-size: 12px; color: var(--app-text-2); }
/* 空态提示：同色系弱化，存在感低但能被看到 */
.empty-tip { color: var(--app-text-3); font-size: 12px; padding: 10px 0; }
/* 操作按钮容器：单行排列、不换行，防止固定在右侧的操作列行高抖动 */
.op-btns { display: flex; flex-wrap: nowrap; align-items: center; white-space: nowrap; }
/* 压缩按钮内边距并清零默认 margin，让 3 个 link 按钮在 190px 列宽内排布舒适 */
.op-btns .el-button { margin-left: 0; padding: 0 4px; }
</style>
