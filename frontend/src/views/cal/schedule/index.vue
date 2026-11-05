<!-- 文件级说明：日历模块 · 我的日程页（cal/schedule） -->
<!-- 职责：提供月/周/日三种视图的自定义日历（不用 el-calendar，便于按日程密度与主题色定制），以及新建/编辑日程弹窗、日程详情抽屉、单日全部日程弹窗。 -->
<!-- 关键数据流：/cal/schedule/list 拉取日程 → buildScheduleMap 按“开始日期”分桶 → monthCells/weekCells 计算格子 → 模板渲染事件块。 -->
<!-- 依赖：Element Plus 组件库；@/utils/request 统一请求封装；主题变量（--chart-* / --app-* / --brand-*）适配暗色与换肤。 -->
<!-- 被使用：由日历模块路由挂载为独立页面；无子组件，所有视图均在本文件内实现。 -->
<template>
  <!-- 页面根容器：cal-wrap 额外补底部留白，避免日历卡片贴住页面底边 -->
  <div class="app-container cal-wrap">
    <!-- 页头：仅标题与统计，不含操作按钮（新建入口放在工具栏，靠近筛选条件） -->
    <div class="page-header">
      <!-- 标题区：scheduleMap.size 是“有日程的日期数”，并非日程总条数，统计口径需注意 -->
      <div class="page-title-wrap">
        <h2>我的日程</h2>
        <div class="sub">日历视图 · 共 {{ scheduleMap.size }} 条日程</div>
      </div>
    </div>

    <!-- 工具栏：标题/负责人/日期范围筛选 + 新建入口 -->
    <el-card shadow="never" class="search-card">
      <!-- 查询表单：model 绑 query；@submit.prevent 阻止回车触发原生提交刷新页面 -->
      <el-form :model="query" inline @submit.prevent>
        <!-- 标题模糊筛选；keyup.enter 让用户输完直接回车即查询，不必再点按钮 -->
        <el-form-item label="标题">
          <el-input v-model="query.title" placeholder="请输入标题" clearable style="width: 170px" @keyup.enter="handleSearch" />
        </el-form-item>
        <!-- 负责人筛选：后端按 owner_id 精确匹配；当前是手填 id 的输入框，未提供用户下拉 -->
        <el-form-item label="负责人">
          <el-input v-model="query.owner_id" placeholder="owner_id" clearable style="width: 140px" @keyup.enter="handleSearch" />
        </el-form-item>
        <!-- 日期范围筛选：v-model 绑独立的 dateRange（不放进 query，因为它是数组且需转成两枚后端参数） -->
        <el-form-item label="日期范围">
          <!-- value-format 固定 YYYY-MM-DD；fetchList 里再拼上时分秒构造 __gte/__lte 查询条件 -->
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            style="width: 240px"
          />
        </el-form-item>
        <!-- 操作区：查询、重置、新建 -->
        <el-form-item>
          <!-- 查询：handleSearch 先回到第 1 页再请求，避免旧页码叠加新条件导致空列表 -->
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <!-- 重置：清空筛选条件（含 dateRange）后重新查询，恢复到页面初始状态 -->
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
          <!-- 新建日程：默认把开始/结束时间填成所选日期的 09:00-10:00，减少用户手填成本 -->
          <el-button type="primary" :icon="Plus" @click="openCreate">新建日程</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 日历视图卡片：自定义格子视图，使用主题边框与圆角，跟随整体设计规范 -->
    <el-card shadow="never" class="calendar-card">
      <!-- 卡片头部：左侧当前时间段标题，右侧视图切换与翻页控制 -->
      <template #header>
        <div class="cal-header">
          <!-- 左侧：主题色竖条 + 视图标题（如“2025 年 11 月”），让用户明确当前所在时间段 -->
          <div class="cal-header-left">
            <span class="panel-dot dot-blue"></span>
            <span class="cal-title">我的日程 · {{ calViewTitle }}</span>
          </div>
          <!-- 右侧：月/周/日切换 + 上一段/下一段/回到今天 -->
          <div class="cal-header-right">
            <!-- calMode 决定模板走哪套渲染分支与翻页步长；切换视图时保留 selectedDate，不丢失当前定位 -->
            <el-radio-group v-model="calMode" size="default">
              <el-radio-button value="month">月</el-radio-button>
              <el-radio-button value="week">周</el-radio-button>
              <el-radio-button value="day">日</el-radio-button>
            </el-radio-group>
            <!-- 上一段：按 calMode 分别减 1 月/1 周/1 天；按钮文案随 periodLabel 变化 -->
            <el-button :icon="RefreshLeft" @click="prevPeriod">上一{{ periodLabel }}</el-button>
            <el-button :icon="RefreshRight" @click="nextPeriod">下一{{ periodLabel }}</el-button>
            <!-- 今天：把 selectedDate 重置为当前时间，快速回到当前月/周/日 -->
            <el-button @click="goToday">今天</el-button>
          </div>
        </div>
      </template>

      <!-- 日历主体容器：min-height 保证空数据时卡片不塌陷 -->
      <div class="cal-wrapper">
        <!-- 自定义日历网格：不用 el-calendar，便于按“每天最多显示 N 条”的密度控制排版 -->
        <div class="cal-grid">
          <!-- 星期表头：固定 7 列，与下方月/周网格的 grid-template-columns 严格对齐 -->
          <div class="cal-weekdays">
            <!-- weekdays 按 JS getDay() 顺序（周日在前）排列，避免与日期索引错位 -->
            <div v-for="w in weekdays" :key="w" class="cal-weekday">{{ w }}</div>
          </div>
          <!-- 月视图：42 个格子（含上/下月补位），current=false 的补位格子做淡化处理 -->
          <div v-if="calMode === 'month'" class="cal-month">
            <!-- 遍历 monthCells；用索引作 key，因为补位日期可能与本月日期字符串重复 -->
            <div
              v-for="(day, idx) in monthCells"
              :key="idx"
              class="cal-cell"
              :class="{ 'other-month': !day.current, today: day.isToday, selected: selectedDateStr === day.str }"
              @click="selectDate(day.str)"
            >
              <!-- 格子头：显示日期数字；今天由 today 类做圆形主题色强调 -->
              <div class="cal-cell-head">
                <span class="cal-date-num">{{ day.day }}</span>
              </div>
              <!-- 格子事件区：最多 3 条，超出部分折叠，避免事件撑破固定最小高度 -->
              <div class="cal-cell-events">
                <!-- 取前 3 条；ev.color 由 buildScheduleMap 预先算好（全天紫 / 停用灰 / 默认蓝） -->
                <div
                  v-for="(ev, ei) in day.events.slice(0, 3)"
                  :key="ei"
                  class="cal-event"
                  :class="'ev-' + (ev.color || 'blue')"
                  @click.stop="openDetail(ev)"
                >
                  {{ ev.title }}
                </div>
                <!-- 溢出提示：click.stop 阻止冒泡到格子，否则会同时触发 selectDate 选中日期 -->
                <div v-if="day.events.length > 3" class="cal-more" @click.stop="dayEvents = day.events; dayDate = day.str; eventDialogVisible = true">
                  +{{ day.events.length - 3 }} 更多
                </div>
              </div>
            </div>
          </div>
          <!-- 周/日视图容器：与月视图 v-if/v-else 互斥，同一时间只渲染一种 -->
          <div v-else class="cal-compact">
            <!-- 周视图：7 列，周一为一周起点（weekCells 计算时已按 getDay 调整） -->
            <div v-if="calMode === 'week'" class="cal-week">
              <!-- day.str 作 key：一周内日期字符串唯一且稳定 -->
              <div
                v-for="day in weekCells"
                :key="day.str"
                class="cal-cell"
                :class="{ today: day.isToday, selected: selectedDateStr === day.str }"
                @click="selectDate(day.str)"
              >
                <!-- 周视图格子头：左侧星期文字（一/二/…），右侧日期数字 -->
                <div class="cal-cell-head">
                  <span class="cal-weekday-num">{{ day.weekdayLabel }}</span>
                  <span class="cal-date-num">{{ day.day }}</span>
                </div>
                <!-- 周视图事件区：空间比月视图大，最多展示 4 条 -->
                <div class="cal-cell-events">
                  <div
                    v-for="(ev, ei) in day.events.slice(0, 4)"
                    :key="ei"
                    class="cal-event"
                    :class="'ev-' + (ev.color || 'blue')"
                    @click.stop="openDetail(ev)"
                  >{{ ev.title }}</div>
                  <!-- 超过 4 条折叠为“+N 更多”，点击打开单日完整列表；stop 防止连带选中日期 -->
                  <div v-if="day.events.length > 4" class="cal-more" @click.stop="dayEvents = day.events; dayDate = day.str; eventDialogVisible = true">
                    +{{ day.events.length - 4 }} 更多
                  </div>
                </div>
              </div>
            </div>
            <!-- 日视图：列出选中日期的全部日程，信息最完整（含时间、内容摘要、全天标签） -->
            <div v-else class="cal-day">
              <!-- 日视图头：日期 + 星期，便于确认当前查看的是哪一天 -->
              <div class="day-header">{{ selectedDateStr }} · {{ weekdayLabel(selectedDateStr) }}</div>
              <div class="day-events">
                <!-- 直接取当天全部日程（已按开始时间升序），不做截断 -->
                <div
                  v-for="(ev, ei) in dayEventsOf(selectedDateStr)"
                  :key="ei"
                  class="cal-event-row"
                  :class="'ev-row-' + (ev.color || 'blue')"
                  @click="openDetail(ev)"
                >
                  <!-- 时间：取 start_time 的 11-16 位（HH:mm）；无具体时间的日程显示“全天” -->
                  <div class="ev-time">{{ ev.start_time?.slice(11, 16) || '全天' }}</div>
                  <!-- 主信息：标题 + 内容摘要（有内容才渲染，避免空行占位） -->
                  <div class="ev-main">
                    <div class="ev-title">{{ ev.title }}</div>
                    <div class="ev-sub" v-if="ev.content">{{ ev.content }}</div>
                  </div>
                  <!-- 全天标记：用 info 色标签，避免与状态色/事件色混淆 -->
                  <el-tag v-if="ev.all_day" size="small" effect="light" type="info">全天</el-tag>
                </div>
                <!-- 空态：当天无日程时给出明确提示，而不是留一片空白 -->
                <div v-if="dayEventsOf(selectedDateStr).length === 0" class="empty-day">当日暂无日程</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </el-card>

    <!-- 日程详情抽屉：右侧滑出，适合“查看而不编辑”的只读场景，关闭后仍保留日历上下文 -->
    <el-drawer v-model="detailVisible" :title="detailData.title || '日程详情'" size="440px" destroy-on-close>
      <!-- detailData.id 存在才渲染内容，避免打开瞬间闪现空字段 -->
      <div v-if="detailData.id" class="detail-body">
        <!-- 描述列表：单列 + 边框，适合窄抽屉里逐项展示字段 -->
        <el-descriptions :column="1" border>
          <el-descriptions-item label="标题">{{ detailData.title }}</el-descriptions-item>
          <!-- 时间字段直接展示后端字符串；空值兜底 '-'，保持版式整齐 -->
          <el-descriptions-item label="开始时间">{{ detailData.start_time || '-' }}</el-descriptions-item>
          <el-descriptions-item label="结束时间">{{ detailData.end_time || '-' }}</el-descriptions-item>
          <!-- 全天：只在为真时显示“是”，不展示“否”，减少无效信息 -->
          <el-descriptions-item label="全天" v-if="detailData.all_day">是</el-descriptions-item>
          <!-- 提前提醒：有分钟数则展示“N 分钟前”，为空即“不提醒”（null/0 均按不提醒处理） -->
          <el-descriptions-item label="提醒">{{ detailData.reminder_minutes ? detailData.reminder_minutes + ' 分钟前' : '不提醒' }}</el-descriptions-item>
          <el-descriptions-item label="负责人">{{ detailData.owner_id || '-' }}</el-descriptions-item>
          <!-- 状态：仅 1 视为启用（success），其余按停用展示，与表单开关取值口径一致 -->
          <el-descriptions-item label="状态">
            <el-tag :type="detailData.status === 1 ? 'success' : 'info'" effect="light">
              {{ detailData.status === 1 ? '启用' : '停用' }}
            </el-tag>
          </el-descriptions-item>
        </el-descriptions>
        <!-- 内容区单独成块：长文本保留换行（样式里 pre-wrap），比塞进 descriptions 更易读 -->
        <div class="detail-section">
          <div class="detail-section-title">📝 内容</div>
          <div class="detail-content">{{ detailData.content || '（无内容）' }}</div>
        </div>
      </div>
    </el-drawer>

    <!-- 新建/编辑共用弹窗：标题由 dialogTitle 切换；禁止点遮罩关闭，防止误触丢失填写内容 -->
    <!-- destroy-on-close 关闭时销毁表单子树，避免下次打开残留校验红字与滚动位置 -->
    <el-dialog :title="dialogTitle" v-model="dialogVisible" width="560px" :close-on-click-modal="false" destroy-on-close>
      <!-- 表单：formRef 供 submitForm 校验；rules 只约束标题、开始/结束时间 -->
      <el-form ref="formRef" :model="form" :rules="rules" label-width="110px">
        <!-- 标题：必填；maxlength=200 与后端字段长度一致，前端先做长度限制 -->
        <el-form-item label="标题" prop="title">
          <el-input v-model="form.title" placeholder="请输入日程标题" maxlength="200" />
        </el-form-item>
        <!-- 开始时间：必填；value-format 保证提交给后端的是 'YYYY-MM-DD HH:mm:ss' -->
        <el-form-item label="开始时间" prop="start_time">
          <el-date-picker v-model="form.start_time" type="datetime" placeholder="开始时间" value-format="YYYY-MM-DD HH:mm:ss" style="width:100%" />
        </el-form-item>
        <!-- 结束时间：同样必填；起止先后关系由后端校验，前端此处不重复做交叉校验 -->
        <el-form-item label="结束时间" prop="end_time">
          <el-date-picker v-model="form.end_time" type="datetime" placeholder="结束时间" value-format="YYYY-MM-DD HH:mm:ss" style="width:100%" />
        </el-form-item>
        <!-- 全天开关：开启后日历事件块用紫色区分，日视图的时间位置显示“全天” -->
        <el-form-item label="全天" prop="all_day">
          <el-switch v-model="form.all_day" />
        </el-form-item>
        <!-- 提前提醒：单位分钟，下拉值 5/15/30/60/1440（1440=1 天），clearable 可清空表示不提醒 -->
        <el-form-item label="提前提醒" prop="reminder_minutes">
          <el-select v-model="form.reminder_minutes" placeholder="不提醒" clearable style="width:100%">
            <el-option label="5 分钟" :value="5" />
            <el-option label="15 分钟" :value="15" />
            <el-option label="30 分钟" :value="30" />
            <el-option label="1 小时" :value="60" />
            <el-option label="1 天" :value="1440" />
          </el-select>
        </el-form-item>
        <!-- 负责人：后端 owner_id 为整型主键，这里用数字输入；min=1 排除 0/负数等非法主键 -->
        <el-form-item label="负责人" prop="owner_id">
          <el-input-number v-model="form.owner_id" :min="1" style="width:100%" />
        </el-form-item>
        <!-- 状态：active-value=1 / inactive-value=0，与详情抽屉和事件颜色判断保持一致 -->
        <el-form-item label="状态" prop="status">
          <el-switch v-model="form.status" :active-value="1" :inactive-value="0" active-text="启用" inactive-text="停用" />
        </el-form-item>
        <!-- 内容：多行文本，仅用于详情展示与日视图摘要 -->
        <el-form-item label="内容" prop="content">
          <el-input v-model="form.content" type="textarea" :rows="3" placeholder="日程详细说明" />
        </el-form-item>
      </el-form>
      <!-- 底部按钮：取消直接关闭；确定走 submitForm（校验 + 保存 loading） -->
      <template #footer>
        <el-button @click="dialogVisible=false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitForm">确定</el-button>
      </template>
    </el-dialog>

    <!-- 单日全部日程弹窗：月/周视图只显示前 N 条，点“+N 更多”后在此查看完整列表 -->
    <el-dialog :title="dayDate + ' 日程'" v-model="eventDialogVisible" width="500px" destroy-on-close>
      <!-- dayEvents 在点“更多”时被直接赋值为当天完整数组，length 为 0 时走下方空态 -->
      <div v-if="dayEvents.length">
        <div
          v-for="(ev, i) in dayEvents"
          :key="i"
          class="cal-event-row big"
          :class="'ev-row-' + (ev.color || 'blue')"
          @click="openDetail(ev); eventDialogVisible = false"
        >
          <!-- 与日视图一致的时间/内容展示规则，保证两处观感统一；点击后打开详情并关闭本弹窗 -->
          <div class="ev-time">{{ ev.start_time?.slice(11, 16) || '全天' }}</div>
          <div class="ev-main">
            <div class="ev-title">{{ ev.title }}</div>
            <div class="ev-sub" v-if="ev.content">{{ ev.content }}</div>
          </div>
        </div>
      </div>
      <!-- 兜底空态：理论上有“更多”才打开，但保留空提示避免极端情况下弹窗空白 -->
      <div v-else class="empty-tip">当日暂无日程</div>
    </el-dialog>
  </div>
</template>

<script setup>
// 组合式 API：ref 基础响应式，reactive 对象/Map 响应式，computed 派生网格，watch 预留监听，onMounted 初始化加载
import { ref, reactive, computed, onMounted, watch } from 'vue'
// 消息提示与删除确认框：保存成功提示；删除前二次确认（本页模板暂无删除入口，函数保留为预留能力）
import { ElMessage, ElMessageBox } from 'element-plus'
// 图标：查询/重置/新建/上一段/下一段，按需引入便于构建期摇树
import { Search, Refresh, Plus, RefreshLeft, RefreshRight } from '@element-plus/icons-vue'
// 统一请求封装：/api 前缀、自动带 token、统一错误提示
import request from '@/utils/request'

// 星期文案：顺序必须与 Date.getDay() 的 0-6（周日→周六）一致，否则格子的星期与日期会错位
const weekdays = ['日', '一', '二', '三', '四', '五', '六']
// 当前视图模式：month | week | day，决定模板走哪套分支与翻页步长
const calMode = ref('month') // month | week | day
// 日历聚焦日期：月份/周次/日视图的范围与标题都由它派生；翻页与“今天”改的就是它
const selectedDate = ref(new Date())
// 顶部日期范围筛选值（['YYYY-MM-DD','YYYY-MM-DD']），与 query 分开存放便于转成后端参数
const dateRange = ref([])

// 列表请求中标记（当前模板未绑定 loading 遮罩，保留以支持后续加载态）
const loading = ref(false)
// 接口返回的原始日程数组，保留数据源，便于切换视图时不重复请求
const allSchedules = ref([])
// 核心索引：dateStr('YYYY-MM-DD') → 当天日程数组；所有视图都从这里取数，避免每次渲染遍历全量
const scheduleMap = reactive(new Map()) // dateStr -> []

// 查询初始快照：重置时恢复；page_size=500 一次性取较多数据供整月/整周展示（后端仍分页）
const query_orig = { page: 1, page_size: 500, title: '', owner_id: '', status: null }
// 响应式查询对象：工具栏输入框直接绑定它
const query = reactive({ ...query_orig })

// 表单初始值：新建时用它清空（全天 false、状态 1 启用、提醒为空即不提醒）
const form_orig = { id: null, title: '', content: '', start_time: '', end_time: '', all_day: false, reminder_minutes: null, owner_id: null, status: 1 }
// 响应式表单对象：el-form 的 model
const form = reactive({ ...form_orig })
// 表单实例引用：submitForm 里调用 validate()
const formRef = ref()
// 新建/编辑弹窗显隐
const dialogVisible = ref(false)
// 弹窗标题（新建日程 / 编辑日程）
const dialogTitle = ref('新建日程')
// 保存请求中标记：控制确定按钮 loading，防重复提交
const saving = ref(false)

// 详情抽屉显隐
const detailVisible = ref(false)
// 详情数据：用 reactive 对象，openDetail 时 Object.assign 就地覆盖，模板无需 .value 访问
const detailData = reactive({})

// 单日全部日程弹窗显隐
const eventDialogVisible = ref(false)
// “更多”弹窗展示的当天完整日程数组
const dayEvents = ref([])
// “更多”弹窗对应的日期字符串，用作弹窗标题
const dayDate = ref('')

// 翻页按钮文案：随视图切换“月/周/日”，避免周视图下仍显示“上一月”的语义错误
const periodLabel = computed(() => ({ month: '月', week: '周', day: '日' }[calMode.value]))
// 日历卡片标题：按月给“年 月”、按周给“年 第N周”、按日给“年 月 日”，与格子范围保持一致
const calViewTitle = computed(() => {
  // selectedDate 是 ref，需 .value 取值；computed 会自动追踪依赖更新标题
  const d = selectedDate.value
  if (calMode.value === 'month') return `${d.getFullYear()} 年 ${d.getMonth() + 1} 月`
  if (calMode.value === 'week') return `${d.getFullYear()} 年第 ${weekNumber(d)} 周`
  return `${d.getFullYear()} 年 ${d.getMonth() + 1} 月 ${d.getDate()} 日`
})

// 日期字符串 → 星期文案：日视图头部展示“YYYY-MM-DD · 星期X”
function weekdayLabel(str) {
  // new Date('YYYY-MM-DD') 按 UTC 解析，再用 getDay() 在部分时区可能偏一天；此处沿用既有实现不改逻辑
  const d = new Date(str)
  return weekdays[d.getDay()]
}

// 选中日期的字符串形式（YYYY-MM-DD）：模板用它判断格子是否 selected，避免反复格式化
const selectedDateStr = computed(() => formatDate(selectedDate.value))

// 构建日程索引与颜色：一次遍历把全量日程按“开始日期”分桶，同时给每条补上 color 字段
// 按开始日期而非结束日期归属：日历格子以日程起始日为准，跨天日程只在开始日显示
function buildScheduleMap(list) {
  // 先清空：每次刷新都基于最新数据重建，避免已删除/改期的日程残留在旧索引里
  scheduleMap.clear()
  ;(list || []).forEach(s => {
    // start_time 形如 'YYYY-MM-DD HH:mm:ss'，前 10 位即日期；为空（脏数据）则跳过，避免落到 undefined 键
    const date = (s.start_time || '').slice(0, 10)
    if (!date) return
    // 颜色规则：默认蓝；全天→紫；停用(status=0)→灰（停用优先级最高，会覆盖全天色）
    let color = 'blue'
    if (s.all_day) color = 'purple'
    if (s.status === 0) color = 'gray'
    s.color = color
    // 分桶：首次遇到该日期先建数组，再把日程 push 进当天
    if (!scheduleMap.has(date)) scheduleMap.set(date, [])
    scheduleMap.get(date).push(s)
  })
  // 每天的日程按开始时间排序：时间字符串格式固定，可直接用 localeCompare 保证日历内事件顺序稳定
  scheduleMap.forEach(arr => arr.sort((a, b) => (a.start_time || '').localeCompare(b.start_time || '')))
}

// 拉取日程列表：把 query 与日期范围转换后的参数一并传给后端
async function fetchList() {
  loading.value = true
  try {
    // 浅拷贝 query，避免把 __gte/__lte 这类临时参数写回响应式对象（否则后续重置/请求会带上脏条件）
    const params = { ...query }
    if (dateRange.value?.length === 2) {
      // 后端按字符串比较时间：起始日补 00:00:00、结束日补 23:59:59，保证整天都被纳入范围
      params.start_time__gte = dateRange.value[0] + ' 00:00:00'
      params.end_time__lte = dateRange.value[1] + ' 23:59:59'
    }
    const res = await request.get('/cal/schedule/list', { params })
    allSchedules.value = res.data.list || []
    // 重建索引：所有视图都从这里派生，先清后建可确保页面与后端数据一致
    buildScheduleMap(allSchedules.value)
  // 请求结束撤销 loading（当前模板虽未使用，仍保证状态可被后续扩展消费）
  } finally { loading.value = false }
}

// 查询：页码归 1 再请求，避免换条件后停留在旧页码导致列表为空
function handleSearch() { query.page = 1; fetchList() }
// 重置：恢复查询快照并清空日期范围，再重新查询
function handleReset() { Object.assign(query, query_orig); dateRange.value = []; handleSearch() }

// 日期格式化：Date → 'YYYY-MM-DD'，作为 scheduleMap 的键与格子 str 值
// 用本地 getFullYear/getMonth/getDate 拼接，避免 toISOString 的 UTC 偏移导致跨时区差一天
function formatDate(d) {
  const y = d.getFullYear()
  // 月份需补 0：范围 1-12，padStart 保证固定两位，便于字符串比较与解析
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}
// 解析 'YYYY-MM-DD' → Date：月份减 1；用 new Date(y, m, d) 构造本地零点，避开 new Date(str) 的格式/时区差异
function parseDate(str) {
  const [y, m, d] = str.split('-').map(Number)
  return new Date(y, m - 1, d)
}
// 计算“年内第几周”：以 1 月 1 日为基准，按天数差 + 当年 1 月 1 日星期偏移向上取整
// 仅用于标题展示（近似 ISO 周，不做严格周起始日修正），沿用既有实现避免改变显示结果
function weekNumber(d) {
  const oneJan = new Date(d.getFullYear(), 0, 1)
  return Math.ceil(((d - oneJan) / 86400000 + oneJan.getDay() + 1) / 7)
}

// 判断两个 Date 是否同一天：逐项比较年月日，忽略时分秒；当前模板未使用，保留为工具函数
function isSameDay(a, b) {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate()
}
// 今天的日期字符串：模块加载时计算一次供格子 today 高亮；页面跨零点不重算（停留过夜时高亮会滞后）
const todayStr = formatDate(new Date())

// 月视图格子：固定 42 格（6 行 × 7 列），含上月尾部与下月补位，保证各月网格高度一致、翻月不跳动
const monthCells = computed(() => {
  const d = selectedDate.value
  const year = d.getFullYear()
  const month = d.getMonth()
  // 本月 1 号是星期几（0=周日），决定本月前面需要补多少格上月日期
  const firstDay = new Date(year, month, 1).getDay() // 0-6
  // 本月天数：取“下月第 0 天”即本月最后一天，自动处理大小月与闰年
  const daysInMonth = new Date(year, month + 1, 0).getDate()
  // 上月天数：取“本月第 0 天”即上月最后一天，用于算出上月尾部起始日
  const daysInPrevMonth = new Date(year, month, 0).getDate()

  const cells = []
  // 上月尾部：从本月 1 号前的 firstDay 格开始倒推，current=false 让模板淡化显示
  for (let i = firstDay - 1; i >= 0; i--) {
    const day = daysInPrevMonth - i
    const prev = new Date(year, month - 1, day)
    cells.push(buildCell(prev, false))
  }
  // 本月日期：current=true，正常显示并参与 today/selected 判定
  for (let day = 1; day <= daysInMonth; day++) {
    const cur = new Date(year, month, day)
    cells.push(buildCell(cur, true))
  }
  // 下月补齐到 42 格：month+1 且日期溢出会自动进位到下月，无需单独判断月份
  let next = 1
  while (cells.length < 42) {
    const n = new Date(year, month + 1, next++)
    cells.push(buildCell(n, false))
  }
  return cells
})

// 周视图格子：以周一为一周起点取连续 7 天
const weekCells = computed(() => {
  const d = selectedDate.value
  const dayOfWeek = d.getDay()
  const monday = new Date(d)
  // getDay 周日=0，公式 +1 会让周日落到“下周一”，因此选中周日时展示的是下一周（沿用既有逻辑）
  monday.setDate(d.getDate() - dayOfWeek + 1) // 周一
  const cells = []
  for (let i = 0; i < 7; i++) {
    const c = new Date(monday)
    // 始终基于 monday 副本加偏移，避免修改 monday 导致后续日期累计偏移
    c.setDate(monday.getDate() + i)
    cells.push(buildCell(c, true))
  }
  return cells
})

// 构造单个格子：把日期与当天日程打包成模板需要的结构
// current=false 表示“非本月日期”，模板据此加 other-month 淡化样式
function buildCell(dateObj, current) {
  const str = formatDate(dateObj)
  // 从索引取当天日程；无数据给空数组，模板可直接 .length / slice / 遍历
  const events = scheduleMap.get(str) || []
  return {
    date: dateObj,
    day: dateObj.getDate(),
    str,
    current,
    // 与 todayStr 比较，决定是否高亮“今天”
    isToday: str === todayStr,
    weekdayLabel: weekdays[dateObj.getDay()],
    events
  }
}

// 取某天的全部日程：日视图列表与空态判断共用；同样做空数组兜底
function dayEventsOf(str) { return scheduleMap.get(str) || [] }

// 点击格子选中日期：只改 selectedDate，模板通过 selectedDateStr 重新计算高亮与日视图内容
function selectDate(str) {
  selectedDate.value = parseDate(str)
}
// 上一段：按月直接构造上月 1 号（避免 31 号做减法溢出到隔月）；周/日按固定天数偏移，自动跨月跨年
function prevPeriod() {
  const d = selectedDate.value
  if (calMode.value === 'month') selectedDate.value = new Date(d.getFullYear(), d.getMonth() - 1, 1)
  else if (calMode.value === 'week') { d.setDate(d.getDate() - 7); selectedDate.value = new Date(d) }
  else { d.setDate(d.getDate() - 1); selectedDate.value = new Date(d) }
}
// 下一段：与 prevPeriod 对称；同样按月构造 1 号、周/日按天数推进
function nextPeriod() {
  const d = selectedDate.value
  if (calMode.value === 'month') selectedDate.value = new Date(d.getFullYear(), d.getMonth() + 1, 1)
  else if (calMode.value === 'week') { d.setDate(d.getDate() + 7); selectedDate.value = new Date(d) }
  else { d.setDate(d.getDate() + 1); selectedDate.value = new Date(d) }
}
// 回到今天：新建 Date 指向当前时刻，标题与格子随之刷新
function goToday() { selectedDate.value = new Date() }

// 打开详情抽屉：把行数据合并进 detailData 后显示
// 注意只做覆盖、不做清空：新行缺少的键会保留上一条的值（若各日程字段结构一致则无影响）
function openDetail(row) {
  Object.assign(detailData, { ...row })
  detailVisible.value = true
}

// 新建日程：以当前选中日期为基准，默认填 09:00-10:00，减少用户重复选时间
function openCreate() {
  Object.assign(form, form_orig, { start_time: formatDate(selectedDate.value) + ' 09:00:00', end_time: formatDate(selectedDate.value) + ' 10:00:00' })
  dialogTitle.value = '新建日程'; dialogVisible.value = true
}

// 提交表单：先前端校验；有 id 走更新（id 进路径、其余进 body），无 id 走新建；成功后关闭并刷新日历
async function submitForm() {
  await formRef.value.validate()
  saving.value = true
  try {
    if (form.id) {
      // 解构出 id 作为路径参数，避免 id 同时出现在请求体中
      const { id, ...data } = form
      await request.put(`/cal/schedule/update/${id}`, data); ElMessage.success('更新成功')
    } else {
      // 新建：直接提交整个表单（id 为 null，后端忽略）
      await request.post('/cal/schedule/create', form); ElMessage.success('新建成功')
    }
    // 关闭弹窗并重新拉取，保证日历索引与后端一致
    dialogVisible.value = false; fetchList()
  // 无论成功失败都复位 loading，防止确定按钮卡在转圈状态
  } finally { saving.value = false }
}

// 删除：当前模板未提供删除入口（日历仅做查看/新建/编辑），此函数保留为预留能力
// 若启用：先二次确认，再按后端约定用 body 传 ids 数组
async function handleDelete(row) {
  await ElMessageBox.confirm('确定删除该日程？', '提示', { type: 'warning' })
  await request.delete('/cal/schedule/delete', { data: { ids: [row.id] } })
  ElMessage.success('删除成功'); fetchList()
}

// 首屏加载日程列表；本页负责人是手填 id，无需额外拉取用户下拉
onMounted(fetchList)
</script>

<style scoped>
/* 页面外层：底部补 20px 留白，避免日历卡片紧贴页面底部显得拥挤 */
.cal-wrap { padding-bottom: 20px; }

/* 日历卡片：圆角 + 主题边框变量，暗色主题下边框色会随变量自动切换 */
.calendar-card { border-radius: 14px; border: 1px solid var(--app-border-light); }
/* 卡片头：:deep 穿透 scoped 作用域修改 Element 内部 header 的内边距与分隔线，使其与自定义头部高度匹配 */
.calendar-card :deep(.el-card__header) { padding: 14px 20px; border-bottom: 1px solid var(--app-border-light); }

/* 卡片头布局：左右两组两端对齐，窄屏时允许换行，避免按钮被裁切 */
.cal-header { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px; }
/* 左侧标题组：竖条与文案水平排列；主文字色 var(--app-text-1) 保证明暗主题下都有足够对比度 */
.cal-header-left { display: flex; align-items: center; gap: 8px; font-size: 15px; font-weight: 600; color: var(--app-text-1); }
/* 右侧控制组：视图切换与翻页按钮成行排列，空间不足时自动换行 */
.cal-header-right { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
/* 标题前装饰竖条：4px 宽主题渐变，引用 --brand-primary 使换肤时同步变色 */
.panel-dot { width: 4px; height: 16px; border-radius: 3px; background: linear-gradient(180deg, var(--brand-primary), #6366f1); }

/* 日历主体与星期表头 */
/* 最小高度：数据为空时也保持卡片高度，避免页面高度剧烈跳变 */
.cal-wrapper { min-height: 500px; }
/* 星期表头：7 等分网格，与下方月/周网格列宽严格一致；顶部圆角配合卡片内嵌的视觉层次 */
.cal-weekdays {
  display: grid; grid-template-columns: repeat(7, 1fr);
  background: var(--app-surface-2); border-radius: 8px 8px 0 0;
}
/* 单个星期单元格：居中、次级文字色（--app-text-2），与日期数字形成信息层级 */
.cal-weekday {
  padding: 10px; text-align: center; font-size: 13px; font-weight: 600; color: var(--app-text-2);
}

/* 月/周网格：同为 7 等分栅格，保证与星期表头逐列对齐 */
.cal-month, .cal-week {
  display: grid; grid-template-columns: repeat(7, 1fr);
}
/* 周视图额外内边距与间距：格子之间留 6px 空隙，与月视图“连续表格”观感区分 */
.cal-week { gap: 6px; padding-top: 6px; }

/* 日历格子：右/下描边构成网格线；min-height 保证每格至少放得下 3 条事件；背景用主题表面色 */
.cal-cell {
  border-right: 1px solid var(--app-border-light);
  border-bottom: 1px solid var(--app-border-light);
  min-height: 110px;
  padding: 6px 8px;
  cursor: pointer;
  transition: background 0.15s;
  position: relative;
  background: var(--app-surface);
}
/* 每行第 7 格去掉右描边，避免与卡片边框叠加成双线 */
.cal-cell:nth-child(7n) { border-right: none; }
/* 悬停：次级表面色轻微提亮，提示格子可点击选中 */
.cal-cell:hover { background: var(--app-surface-2); }
/* 选中态：品牌浅色底（--brand-primary-soft），比 today 更强调“用户当前选中” */
.cal-cell.selected { background: var(--brand-primary-soft); }
/* 非本月补位格：整体降一级底色，与本月日期区分 */
.cal-cell.other-month { background: var(--app-surface-2); }
/* 非本月内容再降透明度：弱化但不隐藏，保留跨月日程的可读性 */
.cal-cell.other-month .cal-date-num, .cal-cell.other-month .cal-event { opacity: 0.45; }
/* 今天：与选中态同底色（选中今天时视觉合并），并由日期数字做圆形强调 */
.cal-cell.today { background: var(--brand-primary-soft); }
.cal-cell.today .cal-date-num {
  background: var(--brand-primary); color: #fff; border-radius: 50%;
  display: inline-flex; align-items: center; justify-content: center;
  width: 24px; height: 24px; font-size: 12px; font-weight: 600;
}

/* 格子头：日期号（周视图还含星期）两端对齐，margin-bottom 与事件区拉开距离 */
.cal-cell-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
/* 日期数字：主文字色 + 加粗，是格子内的视觉主体 */
.cal-date-num { font-size: 13px; font-weight: 600; color: var(--app-text-1); }
/* 周视图星期文字：更小更浅（--app-text-3），作为日期数字的辅助说明 */
.cal-weekday-num { font-size: 11px; color: var(--app-text-3); margin-right: 4px; }

/* 事件容器：纵向排列；overflow hidden 防止事件溢出格子边界破坏网格 */
.cal-cell-events { display: flex; flex-direction: column; gap: 3px; overflow: hidden; }
/* 月/周视图事件块：白字 + 单行省略；宽度受格子约束，信息密度优先于展示全文 */
.cal-event {
  font-size: 12px;
  padding: 3px 6px;
  border-radius: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: #fff;
  cursor: pointer;
  transition: transform 0.1s;
}
/* 悬停轻微右移：给出“可点击打开详情”的动效反馈 */
.cal-event:hover { transform: translateX(2px); }

/* 事件色块统一引用主题色板，切换主题色时同步变化 */
/* 六种事件底色：渐变由 chart 变量与其 68% 白混合得到，白字配深色可保证可读性 */
.cal-event.ev-blue { background: linear-gradient(135deg, var(--chart-1), color-mix(in srgb, var(--chart-1) 68%, #ffffff)); }
.cal-event.ev-green { background: linear-gradient(135deg, var(--chart-5), color-mix(in srgb, var(--chart-5) 68%, #ffffff)); }
.cal-event.ev-orange { background: linear-gradient(135deg, var(--chart-3), color-mix(in srgb, var(--chart-3) 68%, #ffffff)); }
.cal-event.ev-purple { background: linear-gradient(135deg, var(--chart-4), color-mix(in srgb, var(--chart-4) 68%, #ffffff)); }
.cal-event.ev-red { background: linear-gradient(135deg, var(--chart-6), color-mix(in srgb, var(--chart-6) 68%, #ffffff)); }
.cal-event.ev-gray { background: linear-gradient(135deg, var(--app-text-3), color-mix(in srgb, var(--app-text-3) 68%, #ffffff)); }

/* “+N 更多”入口：品牌色文字 + 浅色底，弱于事件块但明显可点击 */
.cal-more {
  font-size: 11px; color: var(--brand-primary); padding: 2px 4px;
  background: var(--brand-primary-soft); border-radius: 4px; cursor: pointer;
}

/* 日视图 */
/* 日视图外层：与上方星期表头拉开距离，避免紧贴表头 */
.cal-day { padding-top: 12px; }
/* 日视图日期标题：大字加粗 + 底部分隔线，作为当天列表的标题栏 */
.day-header { font-size: 16px; font-weight: 600; color: var(--app-text-1); padding: 6px 0 14px; border-bottom: 1px solid var(--app-border-light); }
/* 日视图事件列表：纵向排列，8px 间距让每条日程块彼此可分辨 */
.day-events { display: flex; flex-direction: column; gap: 8px; margin-top: 12px; }
/* 日程行卡片：横向布局（时间 / 主信息 / 标签）；左侧 4px 色条呼应事件颜色；浅阴影做层次，暗色主题下阴影不可见但底色仍生效 */
.cal-event-row {
  display: flex; align-items: center; gap: 12px;
  padding: 12px 16px; border-radius: 10px; cursor: pointer;
  border-left: 4px solid var(--brand-primary);
  background: var(--app-surface); box-shadow: 0 2px 8px rgba(30, 41, 59, 0.04);
  transition: box-shadow 0.15s, transform 0.15s;
}
/* 悬停：阴影加深 + 右移 2px，给出可点击的反馈 */
.cal-event-row:hover { box-shadow: 0 6px 16px rgba(30, 41, 59, 0.08); transform: translateX(2px); }
/* 各类事件行的左侧色条与整行渐变底色：蓝色直接复用品牌浅色，其余用 chart 变量 14% 与表面色混合，保证与月/周事件块同一套配色 */
.cal-event-row.ev-row-blue { border-left-color: var(--chart-1); background: linear-gradient(90deg, var(--brand-primary-soft), var(--app-surface)); }
.cal-event-row.ev-row-green { border-left-color: var(--chart-5); background: linear-gradient(90deg, color-mix(in srgb, var(--chart-5) 14%, var(--app-surface)), var(--app-surface)); }
.cal-event-row.ev-row-purple { border-left-color: var(--chart-4); background: linear-gradient(90deg, color-mix(in srgb, var(--chart-4) 14%, var(--app-surface)), var(--app-surface)); }
.cal-event-row.ev-row-orange { border-left-color: var(--chart-3); background: linear-gradient(90deg, color-mix(in srgb, var(--chart-3) 14%, var(--app-surface)), var(--app-surface)); }
.cal-event-row.ev-row-gray { border-left-color: var(--app-text-3); background: linear-gradient(90deg, var(--app-surface-2), var(--app-surface)); }
/* 时间列：等宽数字（tabular-nums）保证不同时间字符串纵向对齐；min-width 防止“全天”等短文案导致列宽跳动 */
.ev-time { font-size: 13px; font-weight: 600; color: var(--app-text-2); font-variant-numeric: tabular-nums; min-width: 60px; }
/* 主信息区：flex:1 占满剩余宽度；min-width:0 允许内部文字正确触发省略号 */
.ev-main { flex: 1; min-width: 0; }
/* 日程标题：主文字色加粗 */
.ev-title { font-size: 14px; font-weight: 600; color: var(--app-text-1); }
/* 内容摘要：次级文字色、单行省略，避免长内容撑高卡片 */
.ev-sub { font-size: 12px; color: var(--app-text-3); margin-top: 3px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
/* “更多”弹窗内使用的大号行：加大内边距提升点击热区与可读性 */
.cal-event-row.big { padding: 14px 18px; }
/* 空态文案：日视图与弹窗共用，居中弱化提示，24px 上下留白避免显得空旷 */
.empty-day, .empty-tip { text-align: center; color: var(--app-text-3); padding: 24px 0; font-size: 13px; }

/* 详情抽屉 */
/* 详情外层：左右 4px 微调，让描述列表不贴死抽屉边缘 */
.detail-body { padding: 0 4px; }
/* 内容区块：与上方描述列表留 20px 间距，形成分区 */
.detail-section { margin-top: 20px; }
/* 区块标题：加粗 + 底部分隔线，与描述列表的边框风格保持一致 */
.detail-section-title { font-size: 14px; font-weight: 600; color: var(--app-text-1); margin-bottom: 10px; padding-bottom: 6px; border-bottom: 1px solid var(--app-border-light); }
/* 内容正文：次级底色卡片 + 1.8 行高；pre-wrap 保留用户输入的换行与空格 */
.detail-content { font-size: 13px; color: var(--app-text-2); line-height: 1.8; padding: 12px 14px; background: var(--app-surface-2); border-radius: 8px; white-space: pre-wrap; }
</style>
