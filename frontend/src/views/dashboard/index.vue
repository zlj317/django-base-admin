<template>
  <div class="app-container dashboard-wrap">
    <!-- 1. 顶部渐变 Banner -->
    <div class="hero-banner">
      <div class="hero-decor hero-decor-1"></div>
      <div class="hero-decor hero-decor-2"></div>
      <div class="hero-decor hero-decor-3"></div>

      <div class="hero-left">
        <el-avatar :size="60" :src="auth.user.avatar || undefined" class="hero-avatar">
          {{ displayName.slice(0, 1).toUpperCase() }}
        </el-avatar>
        <div class="hero-text">
          <div class="hero-greeting">{{ greeting }}，{{ displayName }}！</div>
          <div class="hero-sub">
            今天是 {{ todayText }}，欢迎回到管理后台，祝您工作顺利 🚀
          </div>
        </div>
      </div>

      <div class="hero-right">
        <div class="quick-entry" v-for="entry in quickEntries" :key="entry.title" @click="go(entry.path)">
          <div class="quick-icon" :style="{ background: entry.bg }">
            <el-icon :size="20"><component :is="entry.icon" /></el-icon>
          </div>
          <div class="quick-label">{{ entry.title }}</div>
        </div>
      </div>
    </div>

    <!-- 2. 四列统计卡片 -->
    <el-row :gutter="16" class="stat-row">
      <el-col :xs="24" :sm="12" :md="6" v-for="(s, idx) in statCards" :key="idx">
        <div class="stat-card" :class="'stat-' + s.color">
          <div class="stat-icon-wrap" :style="{ background: s.bg }">
            <el-icon :size="24"><component :is="s.icon" /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ getStatValue(s.key) }}</div>
            <div class="stat-label">{{ s.label }}</div>
            <div class="stat-trend">
              <span class="trend-tip">{{ s.tip }}</span>
            </div>
          </div>
          <div class="stat-spark">
            <svg viewBox="0 0 80 36" class="sparkline">
              <polyline :points="s.spark" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- 3. 下方两栏：左栏待办事项 + 右栏最新动态 -->
    <el-row :gutter="16" class="content-row">
      <el-col :xs="24" :md="14">
        <el-card shadow="never" class="panel">
          <template #header>
            <div class="panel-header">
              <div class="panel-title">
                <span class="panel-dot dot-blue"></span>
                <span>待办事项</span>
                <el-tag effect="light" size="small" type="primary" class="panel-count">{{ todoItems.length }}</el-tag>
              </div>
            </div>
          </template>
          <div v-loading="todoLoading" class="todo-list">
            <div v-if="todoItems.length === 0" class="empty-hint">
              <el-icon :size="32" color="#c0c4cc"><Tickets /></el-icon>
              <div>暂无待办，真是清闲的一天~</div>
            </div>
            <div v-else v-for="(item, i) in todoItems" :key="i" class="todo-item" @click="handleTodoClick(item)">
              <div class="todo-left">
                <div class="todo-type" :class="'type-' + item.type">{{ item.typeLabel }}</div>
                <div class="todo-title">{{ item.title }}</div>
                <div class="todo-meta">
                  <span v-if="item.creator">发起人：{{ item.creator }}</span>
                  <span v-if="item.time" class="todo-time">⏰ {{ item.time }}</span>
                </div>
              </div>
              <el-button link type="primary">处理 →</el-button>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :xs="24" :md="10">
        <el-card shadow="never" class="panel">
          <template #header>
            <div class="panel-header">
              <div class="panel-title">
                <span class="panel-dot dot-purple"></span>
                <span>最新动态</span>
              </div>
            </div>
          </template>
          <div class="activity-body" v-loading="activityLoading">
            <el-timeline v-if="activities.length">
              <el-timeline-item
                v-for="(a, i) in activities"
                :key="i"
                :timestamp="a.time"
                :type="a.color || 'primary'"
                :hollow="false"
              >
                <div class="activity-item">
                  <el-tag :type="a.tagType || 'info'" effect="light" size="small" class="activity-tag">{{ a.typeLabel }}</el-tag>
                  <span class="activity-text">{{ a.text }}</span>
                </div>
              </el-timeline-item>
            </el-timeline>
            <div v-else class="empty-hint">
              <el-icon :size="32" color="#c0c4cc"><Clock /></el-icon>
              <div>暂无动态记录</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 4. 底部两小栏：系统监控 + 常用功能 -->
    <el-row :gutter="16" class="bottom-row">
      <el-col :xs="24" :md="10">
        <el-card shadow="never" class="panel monitor-panel">
          <template #header>
            <div class="panel-header">
              <div class="panel-title">
                <span class="panel-dot dot-green"></span>
                <span>系统监控</span>
              </div>
              <el-tag effect="light" size="small" type="success" class="status-tag">● 运行正常</el-tag>
            </div>
          </template>
          <div v-loading="monitorLoading" class="monitor-body">
            <div class="monitor-item">
              <div class="monitor-row">
                <div class="monitor-label">
                  <el-icon :size="16"><Monitor /></el-icon>
                  <span>数据库连接</span>
                </div>
                <div class="monitor-val">
                  <el-tag :type="monitor.db_status === 'ok' ? 'success' : 'danger'" effect="light" size="small">
                    {{ monitor.db_status === 'ok' ? '正常' : '异常' }}
                  </el-tag>
                </div>
              </div>
              <el-progress :percentage="100" :stroke-width="6" :show-text="false" :color="monitor.db_status === 'ok' ? '#22c55e' : '#ef4444'" />
            </div>

            <div class="monitor-item">
              <div class="monitor-row">
                <div class="monitor-label">
                  <el-icon :size="16"><FolderOpened /></el-icon>
                  <span>磁盘空间</span>
                </div>
                <div class="monitor-val">{{ monitor.disk_total ? `${monitor.disk_used} / ${monitor.disk_total} GB` : '--' }}</div>
              </div>
              <el-progress
                :percentage="monitor.disk_percent || 0"
                :stroke-width="6"
                :color="diskColor"
              />
            </div>

            <div class="monitor-item">
              <div class="monitor-row">
                <div class="monitor-label">
                  <el-icon :size="16"><Cpu /></el-icon>
                  <span>系统状态</span>
                </div>
                <div class="monitor-val">Uptime {{ monitor.uptime || '--' }}</div>
              </div>
              <div class="monitor-meta">
                <span v-if="monitor.mem_percent !== null && monitor.mem_percent !== undefined">内存 {{ monitor.mem_percent }}%</span>
                <span v-if="monitor.disk_free !== undefined">可用 {{ monitor.disk_free }} GB</span>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :xs="24" :md="14">
        <el-card shadow="never" class="panel">
          <template #header>
            <div class="panel-header">
              <div class="panel-title">
                <span class="panel-dot dot-orange"></span>
                <span>常用功能</span>
              </div>
            </div>
          </template>
          <div class="common-grid">
            <div class="common-item" v-for="item in commonEntries" :key="item.title" @click="go(item.path)">
              <div class="ci-icon" :style="{ background: item.bg }">
                <el-icon :size="22"><component :is="item.icon" /></el-icon>
              </div>
              <div class="ci-text">
                <div class="ci-title">{{ item.title }}</div>
                <div class="ci-desc">{{ item.desc }}</div>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { auth } from '@/store/auth'
import request from '@/utils/request'
import {
  UserFilled, Document, TrendCharts, Calendar, Bell, Files, Tickets,
  Monitor, FolderOpened, MagicStick, DataAnalysis, Setting, Clock,
  Cpu
} from '@element-plus/icons-vue'

const router = useRouter()

const displayName = computed(() => auth.user.nickname || auth.user.username || '用户')

const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 6) return '凌晨好'
  if (h < 9) return '早上好'
  if (h < 12) return '上午好'
  if (h < 14) return '中午好'
  if (h < 18) return '下午好'
  return '晚上好'
})

const todayText = computed(() => {
  const d = new Date()
  const weekdays = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六']
  const pad = n => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${weekdays[d.getDay()]}`
})

// 快捷入口
const quickEntries = [
  { title: '新建用户', icon: UserFilled, path: '/system/user', bg: 'linear-gradient(135deg, var(--chart-1), color-mix(in srgb, var(--chart-1) 72%, #ffffff))' },
  { title: '新建菜单', icon: Setting, path: '/system/menu', bg: 'linear-gradient(135deg, var(--chart-5), color-mix(in srgb, var(--chart-5) 72%, #ffffff))' },
  { title: '任务调度', icon: Calendar, path: '/task', bg: 'linear-gradient(135deg, var(--chart-3), color-mix(in srgb, var(--chart-3) 72%, #ffffff))' },
  { title: '数据备份', icon: Files, path: '/system/record', bg: 'linear-gradient(135deg, var(--chart-4), color-mix(in srgb, var(--chart-4) 72%, #ffffff))' }
]

// 常用功能九宫格
const commonEntries = [
  { title: '文件上传', desc: '文件管理', icon: FolderOpened, path: '/file', bg: 'linear-gradient(135deg, var(--chart-1), color-mix(in srgb, var(--chart-1) 72%, #ffffff))' },
  { title: '报表生成', desc: '数据报表', icon: DataAnalysis, path: '/rp/template', bg: 'linear-gradient(135deg, var(--chart-2), color-mix(in srgb, var(--chart-2) 72%, #ffffff))' },
  { title: '大屏预览', desc: 'BI可视化', icon: Monitor, path: '/bi', bg: 'linear-gradient(135deg, var(--chart-2), color-mix(in srgb, var(--chart-2) 72%, #ffffff))' },
  { title: '工单处理', desc: '工单系统', icon: Tickets, path: '/wo/order', bg: 'linear-gradient(135deg, var(--chart-3), color-mix(in srgb, var(--chart-3) 72%, #ffffff))' },
  { title: '知识库', desc: '文档管理', icon: Document, path: '/kb/document', bg: 'linear-gradient(135deg, var(--chart-6), color-mix(in srgb, var(--chart-6) 72%, #ffffff))' },
  { title: '定时任务', desc: '任务调度', icon: Calendar, path: '/task', bg: 'linear-gradient(135deg, var(--chart-4), color-mix(in srgb, var(--chart-4) 72%, #ffffff))' },
  { title: '字典管理', desc: '字典维护', icon: MagicStick, path: '/system/dict', bg: 'linear-gradient(135deg, var(--chart-1), color-mix(in srgb, var(--chart-1) 72%, #ffffff))' },
  { title: '角色权限', desc: 'RBAC', icon: Bell, path: '/system/role', bg: 'linear-gradient(135deg, var(--chart-6), color-mix(in srgb, var(--chart-6) 72%, #ffffff))' },
  { title: '日志审计', desc: '操作日志', icon: Clock, path: '/system/operlog', bg: 'linear-gradient(135deg, var(--app-text-3), color-mix(in srgb, var(--app-text-3) 72%, #ffffff))' }
]

// 统计卡片配置
const statCards = [
  { key: 'todos', label: '今日待办', icon: Tickets, color: 'blue', bg: 'linear-gradient(135deg, var(--chart-1), color-mix(in srgb, var(--chart-1) 72%, #ffffff))', tip: '待办审批与工单', spark: '0,24 14,16 28,20 42,10 56,14 70,6 80,12' },
  { key: 'messages', label: '未读消息', icon: Bell, color: 'purple', bg: 'linear-gradient(135deg, var(--chart-4), color-mix(in srgb, var(--chart-4) 72%, #ffffff))', tip: '站内消息未读', spark: '0,18 14,22 28,14 42,18 56,10 70,14 80,8' },
  { key: 'workflows', label: '运行中工作流', icon: TrendCharts, color: 'green', bg: 'linear-gradient(135deg, var(--chart-5), color-mix(in srgb, var(--chart-5) 72%, #ffffff))', tip: '流程实例总数', spark: '0,14 14,10 28,18 42,12 56,16 70,14 80,20' },
  { key: 'new_users', label: '今日新增用户', icon: UserFilled, color: 'orange', bg: 'linear-gradient(135deg, var(--chart-3), color-mix(in srgb, var(--chart-3) 72%, #ffffff))', tip: '今日注册用户', spark: '0,22 14,18 28,20 42,14 56,18 70,8 80,10' }
]

// 概览数据
const overview = reactive({ stats: {}, greeting: '', now: '' })
const monitor = reactive({ db_status: 'ok', disk_used: 0, disk_total: 0, disk_percent: 0, disk_free: 0, mem_percent: null, uptime: '' })

const todoLoading = ref(false)
const activityLoading = ref(false)
const monitorLoading = ref(false)

const todoItems = ref([])
const activities = ref([])

const diskColor = computed(() => {
  const p = monitor.disk_percent || 0
  if (p > 80) return 'var(--app-danger)'
  if (p > 60) return 'var(--app-warning)'
  return 'var(--app-success)'
})

function getStatValue(key) {
  return overview.stats[key] ?? 0
}

function go(path) {
  router.push(path).catch(() => {})
}

function handleTodoClick(item) {
  if (item.path) go(item.path)
}

// 拉取概览数据（统计 + 待办 + 动态一次请求完成）
async function loadOverview() {
  todoLoading.value = true
  activityLoading.value = true
  try {
    const res = await request.get('/home/overview/')
    const data = res.data || {}
    Object.assign(overview, data)
    overview.stats = data.stats || {}
    todoItems.value = data.todos || []
    activities.value = data.activities || []
  } catch (e) {
    todoItems.value = []
    activities.value = []
  } finally {
    todoLoading.value = false
    activityLoading.value = false
  }
}

// 拉取监控数据
async function loadMonitor() {
  monitorLoading.value = true
  try {
    const res = await request.get('/home/monitor/')
    if (res.data) Object.assign(monitor, res.data)
  } catch (e) { /* ignore */ }
  monitorLoading.value = false
}

onMounted(() => {
  loadOverview()
  loadMonitor()
})
</script>

<style scoped>
.dashboard-wrap {
  padding-bottom: 20px;
}

/* ============ Hero Banner ============ */
.hero-banner {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 28px 32px;
  margin-bottom: 18px;
  background: var(--brand-gradient);
  border-radius: var(--app-radius-xl);
  box-shadow: 0 10px 36px var(--brand-glow);
  overflow: hidden;
  color: #fff;
}

.hero-decor {
  position: absolute;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.1);
}
.hero-decor-1 { top: -60px; right: 10%; width: 200px; height: 200px; }
.hero-decor-2 { bottom: -90px; right: 28%; width: 180px; height: 180px; background: rgba(255, 255, 255, 0.07); }
.hero-decor-3 { top: 30px; right: -30px; width: 120px; height: 120px; background: rgba(255, 255, 255, 0.12); }

.hero-left {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 18px;
}

.hero-avatar {
  color: var(--brand-primary);
  background: #fff;
  font-size: 22px;
  font-weight: 700;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.18);
  border: 3px solid rgba(255, 255, 255, 0.6);
}

.hero-greeting {
  font-size: 22px;
  font-weight: 600;
  letter-spacing: 0.5px;
}
.hero-sub {
  margin-top: 8px;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.85);
}

.hero-right {
  position: relative;
  z-index: 1;
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.quick-entry {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 12px 18px;
  background: rgba(255, 255, 255, 0.16);
  border: 1px solid rgba(255, 255, 255, 0.24);
  border-radius: 12px;
  cursor: pointer;
  transition: transform 0.2s, background 0.2s;
  min-width: 88px;
}
.quick-entry:hover {
  background: rgba(255, 255, 255, 0.28);
  transform: translateY(-2px);
}
.quick-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  border-radius: 10px;
  color: #fff;
}
.quick-label {
  font-size: 12px;
  font-weight: 500;
}

/* ============ 统计卡片 ============ */
.stat-row { margin-bottom: 18px; }
.stat-col { margin-bottom: 16px; }

.stat-card {
  position: relative;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 20px 22px;
  background: var(--app-surface);
  border-radius: var(--app-radius-lg);
  box-shadow: var(--app-shadow-sm);
  border: 1px solid var(--app-border-light);
  overflow: hidden;
  transition: transform 0.2s, box-shadow 0.2s, border-color 0.2s;
}
.stat-card:hover {
  transform: translateY(-3px);
  box-shadow: var(--app-shadow-md);
  border-color: var(--brand-primary-border);
}
.stat-icon-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 52px;
  height: 52px;
  color: #fff;
  border-radius: 14px;
  flex-shrink: 0;
  box-shadow: 0 6px 16px rgba(30, 41, 59, 0.14);
}
.stat-info { flex: 1; min-width: 0; }
.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--app-text-1);
  line-height: 1.1;
  font-variant-numeric: tabular-nums;
}
.stat-label {
  margin-top: 4px;
  font-size: 13px;
  color: var(--app-text-3);
}
.stat-trend {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 6px;
  font-size: 12px;
}
.trend-up { color: var(--app-success); font-weight: 600; }
.trend-down { color: var(--app-danger); font-weight: 600; }
.trend-tip { color: var(--app-text-3); margin-left: 2px; }

.stat-spark {
  position: absolute;
  right: 12px;
  bottom: 12px;
  opacity: 0.5;
  width: 80px;
  height: 36px;
}
.stat-blue .stat-spark { color: var(--chart-1); }
.stat-purple .stat-spark { color: var(--chart-4); }
.stat-green .stat-spark { color: var(--chart-5); }
.stat-orange .stat-spark { color: var(--chart-3); }

/* ============ 面板通用 ============ */
.content-row, .bottom-row { margin-bottom: 18px; }
.bottom-row { margin-bottom: 0; }

/* 同一行卡片等高，消除短内容下方的空白 */
.content-row > .el-col,
.bottom-row > .el-col,
.stat-row > .el-col { display: flex; }

.panel { border-radius: var(--app-radius-lg); border: 1px solid var(--app-border-light); display: flex; flex-direction: column; height: 100%; }
.panel :deep(.el-card__header) { padding: 14px 20px; border-bottom: 1px solid var(--app-border-light); }
.panel :deep(.el-card__body) { padding: 16px 20px; flex: 1; display: flex; flex-direction: column; }
.stat-card { width: 100%; }

.panel-header { display: flex; align-items: center; justify-content: space-between; }
.panel-title {
  display: flex; align-items: center; gap: 8px; font-size: 15px; font-weight: 600; color: var(--app-text-1);
}
.panel-dot { width: 4px; height: 16px; border-radius: 3px; }
.dot-blue { background: linear-gradient(180deg, var(--chart-1), var(--chart-1)); }
.dot-purple { background: linear-gradient(180deg, var(--chart-4), var(--chart-4)); }
.dot-green { background: linear-gradient(180deg, var(--chart-5), var(--chart-5)); }
.dot-orange { background: linear-gradient(180deg, var(--chart-3), var(--chart-3)); }
.panel-count { margin-left: 4px; }
.status-tag { font-weight: 500; }

/* ============ 待办事项 ============ */
.todo-list { min-height: 120px; flex: 1; display: flex; flex-direction: column; }
.todo-item { flex: 1; }
.empty-hint {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 10px; padding: 30px 0; color: var(--app-text-3); font-size: 13px;
}
.todo-item {
  display: flex; align-items: center; justify-content: space-between;
  gap: 12px; padding: 12px 14px; margin-bottom: 10px;
  background: var(--app-surface-2); border-radius: var(--app-radius-md); cursor: pointer;
  transition: background 0.15s, transform 0.15s;
}
.todo-item:hover { background: var(--brand-primary-soft); transform: translateX(2px); }
.todo-left { flex: 1; min-width: 0; }
.todo-type {
  display: inline-block; padding: 2px 8px; border-radius: var(--app-radius-xs); font-size: 11px; font-weight: 600;
  margin-bottom: 6px;
}
.type-workflow { background: var(--brand-primary-soft); color: var(--brand-primary); }
.type-wo { background: color-mix(in srgb, var(--app-warning) 14%, transparent); color: var(--app-warning); }
.type-cal { background: color-mix(in srgb, var(--app-success) 14%, transparent); color: var(--app-success); }
.todo-title { font-size: 14px; color: var(--app-text-1); font-weight: 500; margin-bottom: 4px; }
.todo-meta { font-size: 12px; color: var(--app-text-3); display: flex; gap: 14px; }

/* ============ 最新动态 ============ */
.activity-body { flex: 1; }
.activity-item { display: flex; align-items: center; gap: 8px; }
.activity-tag { flex-shrink: 0; }
.activity-text { font-size: 13px; color: var(--app-text-2); }

/* ============ 系统监控 ============ */
.monitor-body { padding: 4px 0; flex: 1; display: flex; flex-direction: column; justify-content: space-evenly; }
.monitor-item { margin-bottom: 18px; }
.monitor-item:last-child { margin-bottom: 0; }
.monitor-row {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 8px; font-size: 13px;
}
.monitor-label { display: flex; align-items: center; gap: 6px; color: var(--app-text-2); }
.monitor-val { color: var(--app-text-3); font-variant-numeric: tabular-nums; }
.monitor-meta {
  display: flex; gap: 16px; margin-top: 8px; font-size: 12px; color: var(--app-text-3);
}

/* ============ 常用功能 ============ */
.common-grid {
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; flex: 1;
}
.common-item {
  display: flex; align-items: center; gap: 12px;
  padding: 14px 12px; background: var(--app-surface-2); border-radius: var(--app-radius-md);
  cursor: pointer; transition: background 0.15s, transform 0.15s, box-shadow 0.15s;
}
.common-item:hover {
  background: var(--app-surface); transform: translateY(-2px);
  box-shadow: var(--app-shadow-md);
}
.ci-icon {
  display: flex; align-items: center; justify-content: center;
  width: 42px; height: 42px; border-radius: var(--app-radius-md); color: #fff; flex-shrink: 0;
}
.ci-text { flex: 1; min-width: 0; }
.ci-title { font-size: 13px; font-weight: 600; color: var(--app-text-1); }
.ci-desc { font-size: 11px; color: var(--app-text-3); margin-top: 2px; }

/* 小屏适配 */
@media (max-width: 768px) {
  .hero-banner {
    flex-direction: column; align-items: flex-start; padding: 22px;
  }
  .hero-right { margin-top: 14px; width: 100%; justify-content: flex-start; }
  .common-grid { grid-template-columns: repeat(2, 1fr); }
}
</style>
