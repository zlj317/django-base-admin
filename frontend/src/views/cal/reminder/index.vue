<!-- 文件级说明：日历模块 · 日程提醒页（cal/reminder） -->
<!-- 职责：按「关联日程 / 提醒状态」筛选提醒记录，支持新建、编辑、删除提醒。 -->
<!-- 数据模型：一条提醒 = 关联日程(schedule_id) + 被提醒人(remind_user_id) + 提醒时间(remind_time) + 状态(remind_status 0/1/2)。 -->
<!-- 依赖：Element Plus 组件库；@/utils/request 统一请求封装（自动带 token、统一错误提示、401 跳登录）。 -->
<!-- 被使用：由日历模块路由挂载为独立页面；无子组件，新建/编辑共用本页弹窗。 -->
<template>
  <!-- 页面根容器：app-container 是全项目统一的页面外层布局类（内边距、最大宽度等） -->
  <div class="app-container">
    <!-- 页头：左侧标题信息，右侧页面级主操作按钮 -->
    <div class="page-header">
      <!-- 标题区：主标题 + 副标题；副标题实时显示接口返回的总条数 total -->
      <div class="page-title-wrap">
        <!-- 页面主标题，标识当前菜单位置 -->
        <h2>日程提醒</h2>
        <!-- 副标题：total 由列表接口回填，查询/翻页后自动更新，让用户直观看到数据规模 -->
        <div class="sub">日历日程 · 共 {{ total }} 条提醒</div>
      </div>
      <!-- 页头操作区：存放页面级新增入口，放在右上角符合管理后台通用交互习惯 -->
      <div class="page-header-actions">
        <!-- 新建提醒：交给 openCreate 先重置表单再打开弹窗，避免复用弹窗时带出上一次的编辑数据 -->
        <el-button type="primary" :icon="Plus" @click="openCreate">新建提醒</el-button>
      </div>
    </div>

    <!-- 查询区卡片：shadow="never" 去掉阴影，与下方列表卡片保持扁平一致的视觉风格 -->
    <el-card shadow="never" class="search-card">
      <!-- 查询表单：model 绑定 query；@submit.prevent 阻止原生提交，避免按回车时刷新页面 -->
      <el-form :model="query" inline @submit.prevent>
        <!-- 筛选条件一：按关联日程过滤；clearable 清空即“全部”，filterable 便于日程较多时搜索 -->
        <el-form-item label="关联日程">
          <!-- 绑定 query.schedule_id，change 后需点“查询”才生效（与整页查询式交互保持一致） -->
          <el-select v-model="query.schedule_id" placeholder="全部" clearable filterable style="width: 220px">
            <!-- 选项来自 loadOptions 拉取的日程列表；label 用日程标题而非 id，便于用户识别 -->
            <el-option v-for="s in scheduleOptions" :key="s.id" :label="s.title" :value="s.id" />
          </el-select>
        </el-form-item>
        <!-- 筛选条件二：按提醒状态过滤（0 待发送 / 1 已发送 / 2 已忽略），清空即全部 -->
        <el-form-item label="提醒状态">
          <el-select v-model="query.remind_status" placeholder="全部" clearable style="width: 130px">
            <!-- 选项来自本地常量 statusOptions，与后端状态枚举一一对应 -->
            <el-option v-for="s in statusOptions" :key="s.value" :label="s.label" :value="s.value" />
          </el-select>
        </el-form-item>
        <!-- 操作按钮区：查询 / 重置，与筛选条件同一行排布 -->
        <el-form-item>
          <!-- 查询：handleSearch 会先把页码重置为 1，避免换了筛选条件却停在旧页码导致空列表 -->
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <!-- 重置：还原筛选条件（含页码）并重新请求，让页面回到初始状态 -->
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 列表卡片：承载表格与分页，同样使用无阴影样式 -->
    <el-card shadow="never" class="table-card">
      <!-- 表格：v-loading 用 loading 状态遮罩，stripe 斑马纹提升行可读性，empty-text 定制空态文案 -->
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无提醒">
        <!-- 序号列：type="index" 由 Element Plus 按当前页自动生成序号，无需后端返回 -->
        <el-table-column type="index" label="序号" width="70" align="center" />
        <!-- 关联日程列：后端只给 schedule_id，需经 scheduleTitle 映射成可读标题；超长时 tooltip 展示全文 -->
        <el-table-column label="关联日程" min-width="200" show-overflow-tooltip>
          <!-- 作用域插槽：拿到当前行 row，调用 scheduleTitle 完成 id → 标题转换 -->
          <template #default="{ row }">{{ scheduleTitle(row.schedule_id) }}</template>
        </el-table-column>
        <!-- 被提醒人列：userNames 是 id → 昵称 的映射；查不到时回退展示原始 id，最终兜底 '-' -->
        <el-table-column label="被提醒人" min-width="120">
          <template #default="{ row }">{{ userNames[row.remind_user_id] || row.remind_user_id || '-' }}</template>
        </el-table-column>
        <!-- 提醒时间列：后端已返回格式化好的字符串，直接用 prop 展示，避免前端二次转换引入误差 -->
        <el-table-column label="提醒时间" prop="remind_time" width="180" />
        <!-- 状态列：用标签颜色区分状态，比纯文字更易扫视 -->
        <el-table-column label="状态" width="110" align="center">
          <template #default="{ row }">
            <!-- statusTag 决定颜色（待发送 warning / 已发送 success / 已忽略 info），statusLabel 给中文文案 -->
            <el-tag :type="statusTag(row.remind_status)" effect="light" size="small">{{ statusLabel(row.remind_status) }}</el-tag>
          </template>
        </el-table-column>
        <!-- 创建时间列：后端返回的原始字符串直接展示，不做本地时区转换 -->
        <el-table-column label="创建时间" prop="create_time" width="180" />
        <!-- 操作列：fixed="right" 保证横向滚动时操作按钮始终可见；class-name 供列级样式扩展 -->
        <el-table-column label="操作" width="150" fixed="right" class-name="op-col">
          <template #default="{ row }">
            <!-- 操作按钮容器：flex 保证两个按钮不换行，固定列宽下布局稳定 -->
            <div class="op-btns">
              <!-- 编辑：把当前行回填进弹窗；openEdit 内先重置再合并，避免残留脏字段 -->
              <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
              <!-- 删除：handleDelete 内含二次确认；danger 色提示这是破坏性操作 -->
              <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
      <!-- 分页容器：统一留白/对齐，样式沿用全局约定 -->
      <div class="pagination-wrap">
        <!-- 分页器：total 为服务端总数；页码与每页条数双向绑定到 query，change 后重新拉取列表 -->
        <el-pagination background layout="total, sizes, prev, pager, next, jumper"
          :total="total" v-model:current-page="query.page" v-model:page-size="query.page_size"
          :page-sizes="[10, 20, 50, 100]" @change="fetchList" />
      </div>
    </el-card>

    <!-- 新建/编辑共用弹窗：标题由 dialogTitle 动态切换；close-on-click-modal=false 防止误点遮罩丢失已填内容 -->
    <!-- destroy-on-close 关闭时销毁表单子树，避免下次打开残留上一次的校验红字与滚动位置 -->
    <el-dialog :title="dialogTitle" v-model="dialogVisible" width="560px" :close-on-click-modal="false" destroy-on-close>
      <!-- 表单：formRef 供 submitForm 调用 validate；model/rules 驱动校验；label-width 对齐四个字段标签 -->
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <!-- 关联日程：必填，决定这条提醒挂在哪个日程下 -->
        <el-form-item label="关联日程" prop="schedule_id">
          <el-select v-model="form.schedule_id" placeholder="请选择日程" filterable style="width:100%">
            <!-- 与查询区共用 scheduleOptions，保证两处可选的日程范围一致 -->
            <el-option v-for="s in scheduleOptions" :key="s.id" :label="s.title" :value="s.id" />
          </el-select>
        </el-form-item>
        <!-- 被提醒人：非必填（后端允许不指定），clearable 可清空；候选来自 /system/user/list -->
        <el-form-item label="被提醒人" prop="remind_user_id">
          <el-select v-model="form.remind_user_id" placeholder="请选择用户" filterable clearable style="width:100%">
            <!-- label 用昵称优先、用户名兜底，与列表列的回显口径保持一致 -->
            <el-option v-for="u in userOptions" :key="u.id" :label="u.label" :value="u.id" />
          </el-select>
        </el-form-item>
        <!-- 提醒时间：必填；value-format 强制输出 'YYYY-MM-DD HH:mm:ss'，与后端 DateTimeField 入参格式对齐 -->
        <el-form-item label="提醒时间" prop="remind_time">
          <el-date-picker v-model="form.remind_time" type="datetime" placeholder="选择提醒时间"
            value-format="YYYY-MM-DD HH:mm:ss" style="width:100%" />
        </el-form-item>
        <!-- 提醒状态：默认 0（待发送）；编辑时允许手动调整，便于运营人工标记 -->
        <el-form-item label="提醒状态" prop="remind_status">
          <el-select v-model="form.remind_status" style="width:100%">
            <el-option v-for="s in statusOptions" :key="s.value" :label="s.label" :value="s.value" />
          </el-select>
        </el-form-item>
      </el-form>
      <!-- 弹窗底部：取消只关闭不改数据；确定走 submitForm（含校验 + 保存中转圈） -->
      <template #footer>
        <el-button @click="dialogVisible=false">取消</el-button>
        <!-- saving 为 true 时按钮 loading，防止连点造成重复创建/重复更新 -->
        <el-button type="primary" :loading="saving" @click="submitForm">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
// 组合式 API：ref 用于基础值/数组响应式，reactive 用于对象/映射，onMounted 用于页面初始化拉数据
import { ref, reactive, onMounted } from 'vue'
// 消息提示与确认框：增删改后给轻提示，删除前用确认框拦截误操作
import { ElMessage, ElMessageBox } from 'element-plus'
// 图标：查询/重置/新建按钮使用；按需引入便于构建期摇树，避免图标全量打包
import { Search, Refresh, Plus } from '@element-plus/icons-vue'
// 统一请求实例：baseURL=/api，自动带 token，业务失败统一弹错误，因此这里只需处理成功路径
import request from '@/utils/request'

// 列表请求中标记，传给表格 v-loading，避免请求期间误操作
const loading = ref(false)
// 当前页列表数据，直接喂给 el-table
const rows = ref([])
// 服务端返回的总条数，供分页器 total 与页头副标题使用
const total = ref(0)
// 保存（新建/更新）请求中标记，控制确定按钮 loading，防重复提交
const saving = ref(false)
// 新建/编辑弹窗显隐
const dialogVisible = ref(false)
// 弹窗标题，随新建/编辑切换，让用户清楚当前处于哪种操作
const dialogTitle = ref('新建提醒')
// 表单组件引用，submitForm 通过它调用 validate() 触发表单校验
const formRef = ref()
// 日程下拉选项（id + 标题），查询区与表单共用，避免重复请求
const scheduleOptions = ref([])
// 用户下拉选项（id + 展示名），用于“被提醒人”选择
const userOptions = ref([])
// 用户 id → 展示名 的映射：列表列 O(1) 回显昵称，避免每行都遍历一次用户数组
const userNames = reactive({})

// 查询参数“原始快照”：重置时用它恢复初始状态；单独保留一份，避免被 reactive 的 query 改动污染
const query_orig = { page: 1, page_size: 10, schedule_id: null, remind_status: null }
// 响应式查询对象：筛选控件与分页器直接绑定，请求时整体作为 params 下发
const query = reactive({ ...query_orig })

// 提醒状态枚举：与后端 remind_status 一一对应（0 待发送 / 1 已发送 / 2 已忽略），下拉与标签文案都复用这一份
const statusOptions = [
  { value: 0, label: '待发送' },
  { value: 1, label: '已发送' },
  { value: 2, label: '已忽略' }
]

// 表单初始值：新建时用它清空字段（默认状态 0 待发送），编辑时作为基础再合并行数据
const form_orig = { id: null, schedule_id: null, remind_user_id: null, remind_time: '', remind_status: 0 }
// 响应式表单对象：el-form 的 model，各字段通过 v-model 双向绑定
const form = reactive({ ...form_orig })
// 校验规则：关联日程与提醒时间必填；被提醒人允许为空，因此不加规则
const rules = {
  schedule_id: [{ required: true, message: '请选择关联日程', trigger: 'change' }],
  remind_time: [{ required: true, message: '请选择提醒时间', trigger: 'change' }]
}

// 状态值 → 中文文案：查表后取 label，未知值兜底“未知”，避免直接把数字暴露给用户
function statusLabel(v) { return statusOptions.find(x => x.value === v)?.label || '未知' }
// 状态值 → el-tag 类型：0 待发送用 warning（提示未完成），1 已发送用 success，2 已忽略用 info（弱化）
function statusTag(v) { return ({ 0: 'warning', 1: 'success', 2: 'info' })[v] || 'info' }
// 日程 id → 标题：优先在下拉选项里查；查不到时退化为“日程 #id”，保证列表不出现空白单元格
function scheduleTitle(id) { return scheduleOptions.value.find(s => s.id === id)?.title || (id ? `日程 #${id}` : '-') }

// 拉取提醒列表：query（含分页与筛选）整体作为 params，由后端负责过滤与分页
async function fetchList() {
  loading.value = true
  try {
    const res = await request.get('/cal/reminder/list', { params: query })
    // 统一响应为 { code, msg, data }，data 内含 { list, total }；字段缺失时给空数组/0 兜底
    rows.value = res.data.list || []
    total.value = res.data.total || 0
  // 无论成功失败都撤销 loading，避免请求异常时表格一直转圈
  } finally { loading.value = false }
}

// 预加载下拉选项：日程与用户两个接口互不依赖，各自 try/catch，任一失败不影响另一个与主列表
async function loadOptions() {
  try {
    // 日程候选：一次取 500 条，避免分页导致编辑时找不到已关联的日程标题
    const res = await request.get('/cal/schedule/list', { params: { page: 1, page_size: 500 } })
    scheduleOptions.value = res.data.list || []
  } catch { /* ignore */ }
  try {
    // 用户候选：同样取 500 条；后端字段可能是 nickname 或 username，统一收敛成 label
    const res = await request.get('/system/user/list', { params: { page: 1, page_size: 500 } })
    userOptions.value = (res.data.list || []).map(u => ({ id: u.id, label: u.nickname || u.username }))
    // 同步构建 id → 昵称 映射，供表格列快速回显
    userOptions.value.forEach(u => { userNames[u.id] = u.label })
  } catch { /* ignore */ }
}

// 查询：先把页码归 1 再请求，避免换筛选条件后仍停留在旧页码造成空列表
function handleSearch() { query.page = 1; fetchList() }
// 重置：用原始快照覆盖当前 query（保持响应式引用不变），再走查询流程
function handleReset() { Object.assign(query, query_orig); handleSearch() }

// 打开新建弹窗：先重置表单清除上一次编辑残留，再切标题并显示
function openCreate() { Object.assign(form, form_orig); dialogTitle.value = '新建提醒'; dialogVisible.value = true }
// 打开编辑弹窗：先重置再合并当前行，id 存在即代表提交时走更新分支
function openEdit(row) { Object.assign(form, form_orig, row); dialogTitle.value = '编辑提醒'; dialogVisible.value = true }

// 提交表单：先做前端校验（不通过会抛错并停在弹窗），再按有无 id 决定新增或更新
async function submitForm() {
  await formRef.value.validate()
  saving.value = true
  try {
    if (form.id) {
      // 更新：解构出 id 作为路径参数，其余字段作为 body，避免 id 重复出现在请求体
      const { id, ...data } = form
      await request.put(`/cal/reminder/update/${id}`, data); ElMessage.success('更新成功')
    } else {
      // 新建：提交整个表单对象（id 为 null，后端忽略该字段）
      await request.post('/cal/reminder/create', form); ElMessage.success('新建成功')
    }
    // 成功后关闭弹窗并刷新列表，保证页面数据与后端一致
    dialogVisible.value = false; fetchList()
  // 失败时也复位 loading，否则按钮会一直转圈
  } finally { saving.value = false }
}

// 删除：先二次确认（用户取消会 reject 并中断后续请求），确认后按后端约定用 body 传 ids 数组
async function handleDelete(row) {
  await ElMessageBox.confirm('确定删除该提醒？', '提示', { type: 'warning' })
  await request.delete('/cal/reminder/delete', { data: { ids: [row.id] } })
  ElMessage.success('删除成功'); fetchList()
}

// 页面初始化：首屏拉列表并并行加载下拉选项（两个请求独立，列表可先渲染）
onMounted(() => { fetchList(); loadOptions() })
</script>

<style scoped>
/* 操作列按钮容器：强制单行不换行，避免窄列里“编辑/删除”折行撑高表格行 */
.op-btns { display: flex; flex-wrap: nowrap; align-items: center; white-space: nowrap; }
/* 列内按钮：去掉 Element 默认左外边距并压缩内边距，让两个 link 按钮间距更紧凑 */
.op-btns .el-button { margin-left: 0; padding: 0 4px; }
</style>
