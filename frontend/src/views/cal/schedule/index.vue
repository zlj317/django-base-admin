<template>
  <div class="app-container cal-wrap">
    <div class="page-header">
      <div class="page-title-wrap">
        <h2>我的日程</h2>
        <div class="sub">日历视图 · 共 {{ scheduleMap.size }} 条日程</div>
      </div>
    </div>

    <!-- 工具栏 -->
    <el-card shadow="never" class="search-card">
      <el-form :model="query" inline @submit.prevent>
        <el-form-item label="标题">
          <el-input v-model="query.title" placeholder="请输入标题" clearable style="width: 170px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="负责人">
          <el-input v-model="query.owner_id" placeholder="owner_id" clearable style="width: 140px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="日期范围">
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            style="width: 240px"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
          <el-button type="primary" :icon="Plus" @click="openCreate">新建日程</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 日历视图 -->
    <el-card shadow="never" class="calendar-card">
      <template #header>
        <div class="cal-header">
          <div class="cal-header-left">
            <span class="panel-dot dot-blue"></span>
            <span class="cal-title">我的日程 · {{ calViewTitle }}</span>
          </div>
          <div class="cal-header-right">
            <el-radio-group v-model="calMode" size="default">
              <el-radio-button value="month">月</el-radio-button>
              <el-radio-button value="week">周</el-radio-button>
              <el-radio-button value="day">日</el-radio-button>
            </el-radio-group>
            <el-button :icon="RefreshLeft" @click="prevPeriod">上一{{ periodLabel }}</el-button>
            <el-button :icon="RefreshRight" @click="nextPeriod">下一{{ periodLabel }}</el-button>
            <el-button @click="goToday">今天</el-button>
          </div>
        </div>
      </template>

      <div class="cal-wrapper">
        <!-- 自定义日历格子 -->
        <div class="cal-grid">
          <div class="cal-weekdays">
            <div v-for="w in weekdays" :key="w" class="cal-weekday">{{ w }}</div>
          </div>
          <div v-if="calMode === 'month'" class="cal-month">
            <div
              v-for="(day, idx) in monthCells"
              :key="idx"
              class="cal-cell"
              :class="{ 'other-month': !day.current, today: day.isToday, selected: selectedDateStr === day.str }"
              @click="selectDate(day.str)"
            >
              <div class="cal-cell-head">
                <span class="cal-date-num">{{ day.day }}</span>
              </div>
              <div class="cal-cell-events">
                <div
                  v-for="(ev, ei) in day.events.slice(0, 3)"
                  :key="ei"
                  class="cal-event"
                  :class="'ev-' + (ev.color || 'blue')"
                  @click.stop="openDetail(ev)"
                >
                  {{ ev.title }}
                </div>
                <div v-if="day.events.length > 3" class="cal-more" @click.stop="dayEvents = day.events; dayDate = day.str; eventDialogVisible = true">
                  +{{ day.events.length - 3 }} 更多
                </div>
              </div>
            </div>
          </div>
          <div v-else class="cal-compact">
            <div v-if="calMode === 'week'" class="cal-week">
              <div
                v-for="day in weekCells"
                :key="day.str"
                class="cal-cell"
                :class="{ today: day.isToday, selected: selectedDateStr === day.str }"
                @click="selectDate(day.str)"
              >
                <div class="cal-cell-head">
                  <span class="cal-weekday-num">{{ day.weekdayLabel }}</span>
                  <span class="cal-date-num">{{ day.day }}</span>
                </div>
                <div class="cal-cell-events">
                  <div
                    v-for="(ev, ei) in day.events.slice(0, 4)"
                    :key="ei"
                    class="cal-event"
                    :class="'ev-' + (ev.color || 'blue')"
                    @click.stop="openDetail(ev)"
                  >{{ ev.title }}</div>
                  <div v-if="day.events.length > 4" class="cal-more" @click.stop="dayEvents = day.events; dayDate = day.str; eventDialogVisible = true">
                    +{{ day.events.length - 4 }} 更多
                  </div>
                </div>
              </div>
            </div>
            <div v-else class="cal-day">
              <div class="day-header">{{ selectedDateStr }} · {{ weekdayLabel(selectedDateStr) }}</div>
              <div class="day-events">
                <div
                  v-for="(ev, ei) in dayEventsOf(selectedDateStr)"
                  :key="ei"
                  class="cal-event-row"
                  :class="'ev-row-' + (ev.color || 'blue')"
                  @click="openDetail(ev)"
                >
                  <div class="ev-time">{{ ev.start_time?.slice(11, 16) || '全天' }}</div>
                  <div class="ev-main">
                    <div class="ev-title">{{ ev.title }}</div>
                    <div class="ev-sub" v-if="ev.content">{{ ev.content }}</div>
                  </div>
                  <el-tag v-if="ev.all_day" size="small" effect="light" type="info">全天</el-tag>
                </div>
                <div v-if="dayEventsOf(selectedDateStr).length === 0" class="empty-day">当日暂无日程</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </el-card>

    <!-- 日程详情抽屉 -->
    <el-drawer v-model="detailVisible" :title="detailData.title || '日程详情'" size="440px" destroy-on-close>
      <div v-if="detailData.id" class="detail-body">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="标题">{{ detailData.title }}</el-descriptions-item>
          <el-descriptions-item label="开始时间">{{ detailData.start_time || '-' }}</el-descriptions-item>
          <el-descriptions-item label="结束时间">{{ detailData.end_time || '-' }}</el-descriptions-item>
          <el-descriptions-item label="全天" v-if="detailData.all_day">是</el-descriptions-item>
          <el-descriptions-item label="提醒">{{ detailData.reminder_minutes ? detailData.reminder_minutes + ' 分钟前' : '不提醒' }}</el-descriptions-item>
          <el-descriptions-item label="负责人">{{ detailData.owner_id || '-' }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="detailData.status === 1 ? 'success' : 'info'" effect="light">
              {{ detailData.status === 1 ? '启用' : '停用' }}
            </el-tag>
          </el-descriptions-item>
        </el-descriptions>
        <div class="detail-section">
          <div class="detail-section-title">📝 内容</div>
          <div class="detail-content">{{ detailData.content || '（无内容）' }}</div>
        </div>
      </div>
    </el-drawer>

    <!-- 新建/编辑 Dialog -->
    <el-dialog :title="dialogTitle" v-model="dialogVisible" width="560px" :close-on-click-modal="false" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="110px">
        <el-form-item label="标题" prop="title">
          <el-input v-model="form.title" placeholder="请输入日程标题" maxlength="200" />
        </el-form-item>
        <el-form-item label="开始时间" prop="start_time">
          <el-date-picker v-model="form.start_time" type="datetime" placeholder="开始时间" value-format="YYYY-MM-DD HH:mm:ss" style="width:100%" />
        </el-form-item>
        <el-form-item label="结束时间" prop="end_time">
          <el-date-picker v-model="form.end_time" type="datetime" placeholder="结束时间" value-format="YYYY-MM-DD HH:mm:ss" style="width:100%" />
        </el-form-item>
        <el-form-item label="全天" prop="all_day">
          <el-switch v-model="form.all_day" />
        </el-form-item>
        <el-form-item label="提前提醒" prop="reminder_minutes">
          <el-select v-model="form.reminder_minutes" placeholder="不提醒" clearable style="width:100%">
            <el-option label="5 分钟" :value="5" />
            <el-option label="15 分钟" :value="15" />
            <el-option label="30 分钟" :value="30" />
            <el-option label="1 小时" :value="60" />
            <el-option label="1 天" :value="1440" />
          </el-select>
        </el-form-item>
        <el-form-item label="负责人" prop="owner_id">
          <el-input-number v-model="form.owner_id" :min="1" style="width:100%" />
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <el-switch v-model="form.status" :active-value="1" :inactive-value="0" active-text="启用" inactive-text="停用" />
        </el-form-item>
        <el-form-item label="内容" prop="content">
          <el-input v-model="form.content" type="textarea" :rows="3" placeholder="日程详细说明" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible=false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitForm">确定</el-button>
      </template>
    </el-dialog>

    <!-- 当日所有日程 Dialog -->
    <el-dialog :title="dayDate + ' 日程'" v-model="eventDialogVisible" width="500px" destroy-on-close>
      <div v-if="dayEvents.length">
        <div
          v-for="(ev, i) in dayEvents"
          :key="i"
          class="cal-event-row big"
          :class="'ev-row-' + (ev.color || 'blue')"
          @click="openDetail(ev); eventDialogVisible = false"
        >
          <div class="ev-time">{{ ev.start_time?.slice(11, 16) || '全天' }}</div>
          <div class="ev-main">
            <div class="ev-title">{{ ev.title }}</div>
            <div class="ev-sub" v-if="ev.content">{{ ev.content }}</div>
          </div>
        </div>
      </div>
      <div v-else class="empty-tip">当日暂无日程</div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Refresh, Plus, RefreshLeft, RefreshRight } from '@element-plus/icons-vue'
import request from '@/utils/request'

const weekdays = ['日', '一', '二', '三', '四', '五', '六']
const calMode = ref('month') // month | week | day
const selectedDate = ref(new Date())
const dateRange = ref([])

const loading = ref(false)
const allSchedules = ref([])
const scheduleMap = reactive(new Map()) // dateStr -> []

const query_orig = { page: 1, page_size: 500, title: '', owner_id: '', status: null }
const query = reactive({ ...query_orig })

const form_orig = { id: null, title: '', content: '', start_time: '', end_time: '', all_day: false, reminder_minutes: null, owner_id: null, status: 1 }
const form = reactive({ ...form_orig })
const formRef = ref()
const dialogVisible = ref(false)
const dialogTitle = ref('新建日程')
const saving = ref(false)

const detailVisible = ref(false)
const detailData = reactive({})

const eventDialogVisible = ref(false)
const dayEvents = ref([])
const dayDate = ref('')

const periodLabel = computed(() => ({ month: '月', week: '周', day: '日' }[calMode.value]))
const calViewTitle = computed(() => {
  const d = selectedDate.value
  if (calMode.value === 'month') return `${d.getFullYear()} 年 ${d.getMonth() + 1} 月`
  if (calMode.value === 'week') return `${d.getFullYear()} 年第 ${weekNumber(d)} 周`
  return `${d.getFullYear()} 年 ${d.getMonth() + 1} 月 ${d.getDate()} 日`
})

function weekdayLabel(str) {
  const d = new Date(str)
  return weekdays[d.getDay()]
}

const selectedDateStr = computed(() => formatDate(selectedDate.value))

// 构建日程颜色：根据状态/是否全天/提醒
function buildScheduleMap(list) {
  scheduleMap.clear()
  ;(list || []).forEach(s => {
    const date = (s.start_time || '').slice(0, 10)
    if (!date) return
    // 颜色规则
    let color = 'blue'
    if (s.all_day) color = 'purple'
    if (s.status === 0) color = 'gray'
    s.color = color
    if (!scheduleMap.has(date)) scheduleMap.set(date, [])
    scheduleMap.get(date).push(s)
  })
  // 每天的日程按开始时间排序
  scheduleMap.forEach(arr => arr.sort((a, b) => (a.start_time || '').localeCompare(b.start_time || '')))
}

async function fetchList() {
  loading.value = true
  try {
    const params = { ...query }
    if (dateRange.value?.length === 2) {
      params.start_time__gte = dateRange.value[0] + ' 00:00:00'
      params.end_time__lte = dateRange.value[1] + ' 23:59:59'
    }
    const res = await request.get('/cal/schedule/list', { params })
    allSchedules.value = res.data.list || []
    buildScheduleMap(allSchedules.value)
  } finally { loading.value = false }
}

function handleSearch() { query.page = 1; fetchList() }
function handleReset() { Object.assign(query, query_orig); dateRange.value = []; handleSearch() }

function formatDate(d) {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}
function parseDate(str) {
  const [y, m, d] = str.split('-').map(Number)
  return new Date(y, m - 1, d)
}
function weekNumber(d) {
  const oneJan = new Date(d.getFullYear(), 0, 1)
  return Math.ceil(((d - oneJan) / 86400000 + oneJan.getDay() + 1) / 7)
}

function isSameDay(a, b) {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate()
}
const todayStr = formatDate(new Date())

// 月份格子
const monthCells = computed(() => {
  const d = selectedDate.value
  const year = d.getFullYear()
  const month = d.getMonth()
  const firstDay = new Date(year, month, 1).getDay() // 0-6
  const daysInMonth = new Date(year, month + 1, 0).getDate()
  const daysInPrevMonth = new Date(year, month, 0).getDate()

  const cells = []
  // 上月尾部
  for (let i = firstDay - 1; i >= 0; i--) {
    const day = daysInPrevMonth - i
    const prev = new Date(year, month - 1, day)
    cells.push(buildCell(prev, false))
  }
  // 本月
  for (let day = 1; day <= daysInMonth; day++) {
    const cur = new Date(year, month, day)
    cells.push(buildCell(cur, true))
  }
  // 下月补齐 42 格
  let next = 1
  while (cells.length < 42) {
    const n = new Date(year, month + 1, next++)
    cells.push(buildCell(n, false))
  }
  return cells
})

// 周格子
const weekCells = computed(() => {
  const d = selectedDate.value
  const dayOfWeek = d.getDay()
  const monday = new Date(d)
  monday.setDate(d.getDate() - dayOfWeek + 1) // 周一
  const cells = []
  for (let i = 0; i < 7; i++) {
    const c = new Date(monday)
    c.setDate(monday.getDate() + i)
    cells.push(buildCell(c, true))
  }
  return cells
})

function buildCell(dateObj, current) {
  const str = formatDate(dateObj)
  const events = scheduleMap.get(str) || []
  return {
    date: dateObj,
    day: dateObj.getDate(),
    str,
    current,
    isToday: str === todayStr,
    weekdayLabel: weekdays[dateObj.getDay()],
    events
  }
}

function dayEventsOf(str) { return scheduleMap.get(str) || [] }

function selectDate(str) {
  selectedDate.value = parseDate(str)
}
function prevPeriod() {
  const d = selectedDate.value
  if (calMode.value === 'month') selectedDate.value = new Date(d.getFullYear(), d.getMonth() - 1, 1)
  else if (calMode.value === 'week') { d.setDate(d.getDate() - 7); selectedDate.value = new Date(d) }
  else { d.setDate(d.getDate() - 1); selectedDate.value = new Date(d) }
}
function nextPeriod() {
  const d = selectedDate.value
  if (calMode.value === 'month') selectedDate.value = new Date(d.getFullYear(), d.getMonth() + 1, 1)
  else if (calMode.value === 'week') { d.setDate(d.getDate() + 7); selectedDate.value = new Date(d) }
  else { d.setDate(d.getDate() + 1); selectedDate.value = new Date(d) }
}
function goToday() { selectedDate.value = new Date() }

function openDetail(row) {
  Object.assign(detailData, { ...row })
  detailVisible.value = true
}

function openCreate() {
  Object.assign(form, form_orig, { start_time: formatDate(selectedDate.value) + ' 09:00:00', end_time: formatDate(selectedDate.value) + ' 10:00:00' })
  dialogTitle.value = '新建日程'; dialogVisible.value = true
}

async function submitForm() {
  await formRef.value.validate()
  saving.value = true
  try {
    if (form.id) {
      const { id, ...data } = form
      await request.put(`/cal/schedule/update/${id}`, data); ElMessage.success('更新成功')
    } else {
      await request.post('/cal/schedule/create', form); ElMessage.success('新建成功')
    }
    dialogVisible.value = false; fetchList()
  } finally { saving.value = false }
}

async function handleDelete(row) {
  await ElMessageBox.confirm('确定删除该日程？', '提示', { type: 'warning' })
  await request.delete('/cal/schedule/delete', { data: { ids: [row.id] } })
  ElMessage.success('删除成功'); fetchList()
}

onMounted(fetchList)
</script>

<style scoped>
.cal-wrap { padding-bottom: 20px; }

.calendar-card { border-radius: 14px; border: 1px solid #f1f5f9; }
.calendar-card :deep(.el-card__header) { padding: 14px 20px; border-bottom: 1px solid #f1f5f9; }

.cal-header { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px; }
.cal-header-left { display: flex; align-items: center; gap: 8px; font-size: 15px; font-weight: 600; color: #1f2937; }
.cal-header-right { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.panel-dot { width: 4px; height: 16px; border-radius: 3px; background: linear-gradient(180deg, #4a6cf7, #6366f1); }

/* 格子 */
.cal-wrapper { min-height: 500px; }
.cal-weekdays {
  display: grid; grid-template-columns: repeat(7, 1fr);
  background: #f8fafc; border-radius: 8px 8px 0 0;
}
.cal-weekday {
  padding: 10px; text-align: center; font-size: 13px; font-weight: 600; color: #6b7280;
}

.cal-month, .cal-week {
  display: grid; grid-template-columns: repeat(7, 1fr);
}
.cal-week { gap: 6px; padding-top: 6px; }

.cal-cell {
  border-right: 1px solid #f1f5f9;
  border-bottom: 1px solid #f1f5f9;
  min-height: 110px;
  padding: 6px 8px;
  cursor: pointer;
  transition: background 0.15s;
  position: relative;
  background: #fff;
}
.cal-cell:nth-child(7n) { border-right: none; }
.cal-cell:hover { background: #f8fafc; }
.cal-cell.selected { background: #eef1ff; }
.cal-cell.other-month { background: #fafbfc; }
.cal-cell.other-month .cal-date-num, .cal-cell.other-month .cal-event { opacity: 0.45; }
.cal-cell.today { background: #eef1ff; }
.cal-cell.today .cal-date-num {
  background: #4a6cf7; color: #fff; border-radius: 50%;
  display: inline-flex; align-items: center; justify-content: center;
  width: 24px; height: 24px; font-size: 12px; font-weight: 600;
}

.cal-cell-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
.cal-date-num { font-size: 13px; font-weight: 600; color: #1f2937; }
.cal-weekday-num { font-size: 11px; color: #9ca3af; margin-right: 4px; }

.cal-cell-events { display: flex; flex-direction: column; gap: 3px; overflow: hidden; }
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
.cal-event:hover { transform: translateX(2px); }

.cal-event.ev-blue { background: linear-gradient(135deg, #4a6cf7, #6366f1); }
.cal-event.ev-green { background: linear-gradient(135deg, #22c55e, #4ade80); }
.cal-event.ev-orange { background: linear-gradient(135deg, #f59e0b, #fbbf24); }
.cal-event.ev-purple { background: linear-gradient(135deg, #8b5cf6, #a78bfa); }
.cal-event.ev-red { background: linear-gradient(135deg, #ef4444, #f87171); }
.cal-event.ev-gray { background: linear-gradient(135deg, #64748b, #94a3b8); }

.cal-more {
  font-size: 11px; color: #4a6cf7; padding: 2px 4px;
  background: rgba(74, 108, 247, 0.08); border-radius: 4px; cursor: pointer;
}

/* 日视图 */
.cal-day { padding-top: 12px; }
.day-header { font-size: 16px; font-weight: 600; color: #1f2937; padding: 6px 0 14px; border-bottom: 1px solid #f1f5f9; }
.day-events { display: flex; flex-direction: column; gap: 8px; margin-top: 12px; }
.cal-event-row {
  display: flex; align-items: center; gap: 12px;
  padding: 12px 16px; border-radius: 10px; cursor: pointer;
  border-left: 4px solid #4a6cf7;
  background: #fff; box-shadow: 0 2px 8px rgba(30, 41, 59, 0.04);
  transition: box-shadow 0.15s, transform 0.15s;
}
.cal-event-row:hover { box-shadow: 0 6px 16px rgba(30, 41, 59, 0.08); transform: translateX(2px); }
.cal-event-row.ev-row-blue { border-left-color: #4a6cf7; background: linear-gradient(90deg, #eef1ff, #fff); }
.cal-event-row.ev-row-green { border-left-color: #22c55e; background: linear-gradient(90deg, #dcfce7, #fff); }
.cal-event-row.ev-row-purple { border-left-color: #8b5cf6; background: linear-gradient(90deg, #f3e8ff, #fff); }
.cal-event-row.ev-row-orange { border-left-color: #f59e0b; background: linear-gradient(90deg, #fef3c7, #fff); }
.cal-event-row.ev-row-gray { border-left-color: #64748b; background: linear-gradient(90deg, #f1f5f9, #fff); }
.ev-time { font-size: 13px; font-weight: 600; color: #4b5563; font-variant-numeric: tabular-nums; min-width: 60px; }
.ev-main { flex: 1; min-width: 0; }
.ev-title { font-size: 14px; font-weight: 600; color: #1f2937; }
.ev-sub { font-size: 12px; color: #9ca3af; margin-top: 3px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.cal-event-row.big { padding: 14px 18px; }
.empty-day, .empty-tip { text-align: center; color: #9ca3af; padding: 24px 0; font-size: 13px; }

/* 详情 */
.detail-body { padding: 0 4px; }
.detail-section { margin-top: 20px; }
.detail-section-title { font-size: 14px; font-weight: 600; color: #1f2937; margin-bottom: 10px; padding-bottom: 6px; border-bottom: 1px solid #f1f5f9; }
.detail-content { font-size: 13px; color: #4b5563; line-height: 1.8; padding: 12px 14px; background: #f8fafc; border-radius: 8px; white-space: pre-wrap; }
</style>
