<template>
<!-- ============================================================
     文件：系统首页 / 工作台（views/dashboard/index.vue）
     职责：登录后的默认落地页。聚合展示欢迎语与快捷入口、四项关键统计、
           待办事项、最新动态、系统监控和常用功能入口。
     依赖：@/store/auth（当前登录用户信息）、@/utils/request（/home/overview/
           与 /home/monitor/ 两个聚合接口）、Element Plus 图标。
     被谁使用：router/index.js 中以 /dashboard 静态注册，所有登录用户可见。
     主题：颜色全部使用 style 区中以 app、brand、chart 开头的 CSS 变量（定义在 tokens.css），
           因此多主题（含暗色）切换时本文件无需改动。
     ============================================================ -->
  <div class="app-container dashboard-wrap">
    <!-- 顶部渐变 Banner：整块以 brand-gradient 品牌渐变铺底，
         切换主题时随品牌色自动变化，作为首页的“封面”区 -->
    <div class="hero-banner">
      <!-- 三个装饰圆均为纯视觉点缀（半透明白色圆形），不承载信息也不参与交互；
           父级 overflow:hidden 会把溢出的部分裁掉，形成弧形色块避免 Banner 过于平直 -->
      <div class="hero-decor hero-decor-1"></div>
      <!-- 装饰圆 2：位于右下并大幅溢出，透明度更低，用于拉开前后景层次 -->
      <div class="hero-decor hero-decor-2"></div>
      <!-- 装饰圆 3：右上角小圆，部分超出边界后被裁切，制造“高光”质感 -->
      <div class="hero-decor hero-decor-3"></div>

      <!-- 左侧欢迎区：头像 + 问候语 + 当天日期，信息主体是当前登录用户 -->
      <div class="hero-left">
        <!-- 用户头像：优先使用 auth.user.avatar；`|| undefined` 很关键——
             传空字符串会让 <img src=""> 触发一次破图请求，传 undefined 时
             el-avatar 才会回退到默认插槽内容 -->
        <el-avatar :size="60" :src="auth.user.avatar || undefined" class="hero-avatar">
          <!-- 无头像时的兜底：取显示名首字符并转大写，渲染成文字头像 -->
          {{ displayName.slice(0, 1).toUpperCase() }}
        </el-avatar>
        <!-- 问候文字区 -->
        <div class="hero-text">
          <!-- 问候语：greeting 计算属性按当前小时返回“早上好/下午好”等，拼接展示名 -->
          <div class="hero-greeting">{{ greeting }}，{{ displayName }}！</div>
          <!-- 副标题：todayText 为「YYYY-MM-DD 星期X」形式的当天日期 -->
          <div class="hero-sub">
            今天是 {{ todayText }}，欢迎回到管理后台，祝您工作顺利 🚀
          </div>
        </div>
      </div>

      <!-- 右侧快捷入口：由 quickEntries 静态配置渲染，点击后跳转对应功能页 -->
      <div class="hero-right">
        <!-- v-for 渲染每个入口：key 用 title 保证唯一；@click 调用 go() 做路由跳转 -->
        <div class="quick-entry" v-for="entry in quickEntries" :key="entry.title" @click="go(entry.path)">
          <!-- 图标底板：背景色来自配置项 bg（主题变量渐变），随主题联动 -->
          <div class="quick-icon" :style="{ background: entry.bg }">
            <!-- 动态组件：entry.icon 存的是图标组件对象，由 <component :is> 渲染 -->
            <el-icon :size="20"><component :is="entry.icon" /></el-icon>
          </div>
          <!-- 入口名称 -->
          <div class="quick-label">{{ entry.title }}</div>
        </div>
      </div>
    </div>

    <!-- 四列统计卡片：ElRow 的 gutter 统一 16px 横向间距，小屏自动换行 -->
    <el-row :gutter="16" class="stat-row">
      <!-- 响应式栅格：手机 24（独占一行）、平板 12（两列）、桌面 6（四列）；
           v-for 渲染 statCards 的四项配置，idx 作为 key -->
      <el-col :xs="24" :sm="12" :md="6" v-for="(s, idx) in statCards" :key="idx">
        <!-- 单张统计卡：额外类名 stat-{color} 只用于给右下角迷你折线设色 -->
        <div class="stat-card" :class="'stat-' + s.color">
          <!-- 图标底板：背景为配置项的渐变，颜色取自主题图表色变量 -->
          <div class="stat-icon-wrap" :style="{ background: s.bg }">
            <!-- 动态渲染配置里的 Element Plus 图标 -->
            <el-icon :size="24"><component :is="s.icon" /></el-icon>
          </div>
          <!-- 数值与文案区 -->
          <div class="stat-info">
            <!-- 主数值：通过 getStatValue(s.key) 从 overview.stats 中取，
                 缺省回退 0，避免接口未返回时显示 undefined -->
            <div class="stat-value">{{ getStatValue(s.key) }}</div>
            <!-- 指标名称，如“今日待办”“未读消息” -->
            <div class="stat-label">{{ s.label }}</div>
            <!-- 指标说明行（趋势提示） -->
            <div class="stat-trend">
              <!-- 配置里的补充说明文字，例如统计口径 -->
              <span class="trend-tip">{{ s.tip }}</span>
            </div>
          </div>
          <!-- 右下角迷你折线图：静态装饰性数据，用 SVG 手绘以避免引入图表库 -->
          <div class="stat-spark">
            <!-- 80x36 的坐标系统，宽高由 CSS 固定 -->
            <svg viewBox="0 0 80 36" class="sparkline">
              <!-- points 来自配置项 s.spark；stroke 用 currentColor，
                   颜色由外层 .stat-{color} 类指定，因此可跟随主题变量 -->
              <polyline :points="s.spark" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- 中部两栏：左 14/24 为待办事项，右 10/24 为最新动态；
         两栏使用同一 .panel 样式，保证卡片高度一致 -->
    <el-row :gutter="16" class="content-row">
      <!-- 待办列：桌面占 14 格，小屏占满整行 -->
      <el-col :xs="24" :md="14">
        <!-- shadow="never" 关闭默认阴影，改由 CSS 用 app-shadow-sm 阴影变量控制，便于暗色适配 -->
        <el-card shadow="never" class="panel">
          <!-- 头部插槽：标题、色点与待办数量标签 -->
          <template #header>
            <div class="panel-header">
              <div class="panel-title">
                <!-- 左侧竖条色点：蓝色对应待办主题（chart-1） -->
                <span class="panel-dot dot-blue"></span>
                <span>待办事项</span>
                <!-- 数量标签：直接取 todoItems 长度，随接口数据刷新 -->
                <el-tag effect="light" size="small" type="primary" class="panel-count">{{ todoItems.length }}</el-tag>
              </div>
            </div>
          </template>
          <!-- v-loading 在请求期间显示遮罩，避免列表区域出现“空列表”的误导 -->
          <div v-loading="todoLoading" class="todo-list">
            <!-- 空状态：无待办时给出友好提示而不是空白区域 -->
            <div v-if="todoItems.length === 0" class="empty-hint">
              <el-icon :size="32" color="#c0c4cc"><Tickets /></el-icon>
              <div>暂无待办，真是清闲的一天~</div>
            </div>
            <!-- 待办列表：v-else 与空状态互斥；点击整行触发 handleTodoClick 跳转业务页 -->
            <div v-else v-for="(item, i) in todoItems" :key="i" class="todo-item" @click="handleTodoClick(item)">
              <!-- 左侧信息区 -->
              <div class="todo-left">
                <!-- 类型徽标：type-{item.type} 决定配色（流程/工单/日程） -->
                <div class="todo-type" :class="'type-' + item.type">{{ item.typeLabel }}</div>
                <!-- 待办标题 -->
                <div class="todo-title">{{ item.title }}</div>
                <!-- 次要信息：发起人、时间，各自按字段存在性显示 -->
                <div class="todo-meta">
                  <span v-if="item.creator">发起人：{{ item.creator }}</span>
                  <!-- 时间前面加了闹钟符号，纯展示用 -->
                  <span v-if="item.time" class="todo-time">⏰ {{ item.time }}</span>
                </div>
              </div>
              <!-- 右侧“处理”按钮：链接样式，点击事件实际由外层的行点击处理 -->
              <el-button link type="primary">处理 →</el-button>
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 动态列：桌面占 10 格 -->
      <el-col :xs="24" :md="10">
        <el-card shadow="never" class="panel">
          <!-- 动态卡片头：标题 + 紫色色点（对应 chart-4） -->
          <template #header>
            <div class="panel-header">
              <div class="panel-title">
                <span class="panel-dot dot-purple"></span>
                <span>最新动态</span>
              </div>
            </div>
          </template>
          <!-- 动态列表容器：加载中显示遮罩，数据来自 overview 接口的 activities -->
          <div class="activity-body" v-loading="activityLoading">
            <!-- 有时间轴数据时才渲染 el-timeline，否则走空状态 -->
            <el-timeline v-if="activities.length">
              <!-- 单条动态：timestamp 显示发生时间，type 控制节点颜色 -->
              <el-timeline-item
                v-for="(a, i) in activities"
                :key="i"
                :timestamp="a.time"
                :type="a.color || 'primary'"
                :hollow="false"
              >
                <!-- 一行内容：类型标签 + 动态文本 -->
                <div class="activity-item">
                  <!-- 类型标签：tagType 缺省用 info 灰色，避免未知类型报错 -->
                  <el-tag :type="a.tagType || 'info'" effect="light" size="small" class="activity-tag">{{ a.typeLabel }}</el-tag>
                  <!-- 动态描述文字 -->
                  <span class="activity-text">{{ a.text }}</span>
                </div>
              </el-timeline-item>
            </el-timeline>
            <!-- 空状态：无动态时显示时钟图标与提示语 -->
            <div v-else class="empty-hint">
              <el-icon :size="32" color="#c0c4cc"><Clock /></el-icon>
              <div>暂无动态记录</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 底部两栏：左侧系统监控（10 格），右侧常用功能（14 格） -->
    <el-row :gutter="16" class="bottom-row">
      <el-col :xs="24" :md="10">
        <!-- 监控面板：数据来自 /home/monitor/，只做只读展示 -->
        <el-card shadow="never" class="panel monitor-panel">
          <template #header>
            <div class="panel-header">
              <div class="panel-title">
                <!-- 绿色色点表示健康度主题 -->
                <span class="panel-dot dot-green"></span>
                <span>系统监控</span>
              </div>
              <!-- 右上角状态徽标：此处为固定文案，真实健康状态由下方各项体现 -->
              <el-tag effect="light" size="small" type="success" class="status-tag">● 运行正常</el-tag>
            </div>
          </template>
          <!-- 监控内容容器：请求期间显示 loading 遮罩 -->
          <div v-loading="monitorLoading" class="monitor-body">
            <!-- 监控项一：数据库连接 -->
            <div class="monitor-item">
              <div class="monitor-row">
                <div class="monitor-label">
                  <el-icon :size="16"><Monitor /></el-icon>
                  <span>数据库连接</span>
                </div>
                <div class="monitor-val">
                  <!-- 依据 db_status 是否为 ok 切换 success/danger 两种标签配色 -->
                  <el-tag :type="monitor.db_status === 'ok' ? 'success' : 'danger'" effect="light" size="small">
                    {{ monitor.db_status === 'ok' ? '正常' : '异常' }}
                  </el-tag>
                </div>
              </div>
              <!-- 进度条仅作“状态指示”：连接正常即满格绿色，异常为满格红色 -->
              <el-progress :percentage="100" :stroke-width="6" :show-text="false" :color="monitor.db_status === 'ok' ? '#22c55e' : '#ef4444'" />
            </div>

            <!-- 监控项二：磁盘空间占用 -->
            <div class="monitor-item">
              <div class="monitor-row">
                <div class="monitor-label">
                  <el-icon :size="16"><FolderOpened /></el-icon>
                  <span>磁盘空间</span>
                </div>
                <div class="monitor-val">{{ monitor.disk_total ? `${monitor.disk_used} / ${monitor.disk_total} GB` : '--' }}</div>
              </div>
              <!-- 占用比例来自接口 disk_percent；颜色由 diskColor 计算属性按阈值给出 -->
              <el-progress
                :percentage="monitor.disk_percent || 0"
                :stroke-width="6"
                :color="diskColor"
              />
            </div>

            <!-- 监控项三：系统运行状态 -->
            <div class="monitor-item">
              <div class="monitor-row">
                <div class="monitor-label">
                  <el-icon :size="16"><Cpu /></el-icon>
                  <span>系统状态</span>
                </div>
                <div class="monitor-val">Uptime {{ monitor.uptime || '--' }}</div>
              </div>
              <!-- 附加指标：内存百分比与磁盘可用空间，字段缺失时整段隐藏 -->
              <div class="monitor-meta">
                <span v-if="monitor.mem_percent !== null && monitor.mem_percent !== undefined">内存 {{ monitor.mem_percent }}%</span>
                <!-- 这里用 !== undefined 判断，允许 0 值正常显示 -->
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
                <!-- 橙色色点对应 chart-3 -->
                <span class="panel-dot dot-orange"></span>
                <span>常用功能</span>
              </div>
            </div>
          </template>
          <!-- 九宫格入口：3 列网格由 .common-grid 控制，小屏降为 2 列 -->
          <div class="common-grid">
            <!-- 单个功能入口：key 用 title；点击调用 go() 跳转到配置的 path -->
            <div class="common-item" v-for="item in commonEntries" :key="item.title" @click="go(item.path)">
              <!-- 图标底板：背景为配置项里的主题渐变 -->
              <div class="ci-icon" :style="{ background: item.bg }">
                <el-icon :size="22"><component :is="item.icon" /></el-icon>
              </div>
              <!-- 文案区：主标题 + 副描述 -->
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
// ============================================================
// 脚本入口：本页使用 <script setup> 组合式写法，所有顶层声明自动暴露给模板。
// 数据流：组件挂载时并行拉取 overview（统计/待办/动态）与 monitor（系统监控），
//       接口失败时静默降级为空数据并保留页面骨架，避免首页白屏。
// 注意：本页只读取后端聚合数据，不在此处做写操作。
// ============================================================
// Vue 基础 API：ref 存可变标量/数组，reactive 存对象，computed 派生只读展示值，
// onMounted 用于首次进入时触发数据加载
import { ref, reactive, computed, onMounted } from 'vue'
// 路由实例：快捷入口与常用功能点击后由它做编程式跳转
import { useRouter } from 'vue-router'
// 全局登录态（响应式）：取当前用户昵称、用户名、头像用于欢迎区展示
import { auth } from '@/store/auth'
// 统一请求封装：已内置 /api 前缀、token 注入与错误提示，这里直接调用即可
import request from '@/utils/request'
// 图标按需引入：只打包本页实际用到的 13 个图标，避免全量图标增大体积
import {
  // 用户、文档、趋势、日历、铃铛、文件、工单
  UserFilled, Document, TrendCharts, Calendar, Bell, Files, Tickets,
  // 监控、文件夹、魔术棒、数据分析、设置、时钟、处理器
  Monitor, FolderOpened, MagicStick, DataAnalysis, Setting, Clock,
  Cpu
} from '@element-plus/icons-vue'

// 创建路由实例，供 go() 使用
const router = useRouter()

// 显示名：优先昵称，其次用户名，均缺失时兜底“用户”，
// 用 computed 是因为 auth.user 可能在登录信息异步加载后变化
const displayName = computed(() => auth.user.nickname || auth.user.username || '用户')

// 问候语：按当前小时划分时段，纯前端计算，不依赖后端；
// 每个分支覆盖一个时间段，默认落到“晚上好”
const greeting = computed(() => {
  // 取本地时间的 0-23 小时
  const h = new Date().getHours()
  // 0:00-5:59 凌晨
  if (h < 6) return '凌晨好'
  // 6:00-8:59 早上
  if (h < 9) return '早上好'
  // 9:00-11:59 上午
  if (h < 12) return '上午好'
  // 12:00-13:59 中午
  if (h < 14) return '中午好'
  // 14:00-17:59 下午
  if (h < 18) return '下午好'
  // 18:00 之后为晚上
  return '晚上好'
})

// 当天日期文本：输出「YYYY-MM-DD 星期X」，用于 Banner 副标题
const todayText = computed(() => {
  // 每次求值取当前时间；页面停留跨天时不会自动刷新（无定时器）
  const d = new Date()
  // 中文星期数组，getDay() 返回 0-6，0 对应星期日
  const weekdays = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六']
  // 补零工具：把 1 位数字补成 2 位，保证日期格式统一
  const pad = n => String(n).padStart(2, '0')
  // 注意 getMonth() 从 0 开始，所以月份要 +1
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${weekdays[d.getDay()]}`
})

// 快捷入口配置：标题、图标组件、目标路由、图标底色（用主题变量渐变，跟随换肤）
const quickEntries = [
  // 新建用户：直达用户管理页，图标蓝（--chart-1）
  { title: '新建用户', icon: UserFilled, path: '/system/user', bg: 'linear-gradient(135deg, var(--chart-1), color-mix(in srgb, var(--chart-1) 72%, #ffffff))' },
  // 新建菜单：直达菜单配置页，图标青（--chart-5）
  { title: '新建菜单', icon: Setting, path: '/system/menu', bg: 'linear-gradient(135deg, var(--chart-5), color-mix(in srgb, var(--chart-5) 72%, #ffffff))' },
  // 任务调度：直达定时任务页，图标橙（--chart-3）
  { title: '任务调度', icon: Calendar, path: '/task', bg: 'linear-gradient(135deg, var(--chart-3), color-mix(in srgb, var(--chart-3) 72%, #ffffff))' },
  // 数据备份：本页实际跳转到操作记录页 /system/record（沿用现有配置，未改动）
  { title: '数据备份', icon: Files, path: '/system/record', bg: 'linear-gradient(135deg, var(--chart-4), color-mix(in srgb, var(--chart-4) 72%, #ffffff))' }
]

// 常用功能九宫格配置：title 为主标题，desc 为副说明，path 为跳转路由；
// bg 同样使用主题图表色与白色混合的渐变，暗色主题下也不会刺眼
const commonEntries = [
  // 文件上传：进入文件管理
  { title: '文件上传', desc: '文件管理', icon: FolderOpened, path: '/file', bg: 'linear-gradient(135deg, var(--chart-1), color-mix(in srgb, var(--chart-1) 72%, #ffffff))' },
  // 报表生成：进入报表模板
  { title: '报表生成', desc: '数据报表', icon: DataAnalysis, path: '/rp/template', bg: 'linear-gradient(135deg, var(--chart-2), color-mix(in srgb, var(--chart-2) 72%, #ffffff))' },
  // 大屏预览：进入 BI 可视化
  { title: '大屏预览', desc: 'BI可视化', icon: Monitor, path: '/bi', bg: 'linear-gradient(135deg, var(--chart-2), color-mix(in srgb, var(--chart-2) 72%, #ffffff))' },
  // 工单处理：进入工单列表
  { title: '工单处理', desc: '工单系统', icon: Tickets, path: '/wo/order', bg: 'linear-gradient(135deg, var(--chart-3), color-mix(in srgb, var(--chart-3) 72%, #ffffff))' },
  // 知识库：进入文档管理
  { title: '知识库', desc: '文档管理', icon: Document, path: '/kb/document', bg: 'linear-gradient(135deg, var(--chart-6), color-mix(in srgb, var(--chart-6) 72%, #ffffff))' },
  // 定时任务：与快捷入口同名，指向同一页面
  { title: '定时任务', desc: '任务调度', icon: Calendar, path: '/task', bg: 'linear-gradient(135deg, var(--chart-4), color-mix(in srgb, var(--chart-4) 72%, #ffffff))' },
  // 字典管理：进入数据字典维护
  { title: '字典管理', desc: '字典维护', icon: MagicStick, path: '/system/dict', bg: 'linear-gradient(135deg, var(--chart-1), color-mix(in srgb, var(--chart-1) 72%, #ffffff))' },
  // 角色权限：进入 RBAC 角色配置
  { title: '角色权限', desc: 'RBAC', icon: Bell, path: '/system/role', bg: 'linear-gradient(135deg, var(--chart-6), color-mix(in srgb, var(--chart-6) 72%, #ffffff))' },
  // 日志审计：进入操作日志，用中性文字色 --app-text-3 做图标底色以便区分
  { title: '日志审计', desc: '操作日志', icon: Clock, path: '/system/operlog', bg: 'linear-gradient(135deg, var(--app-text-3), color-mix(in srgb, var(--app-text-3) 72%, #ffffff))' }
]

// 统计卡片配置：key 必须与后端 overview.stats 的字段名一致；
// spark 是 80x36 坐标系内的折线点集，仅作视觉趋势示意，不代表真实时间序列
const statCards = [
  // 今日待办：蓝色主题，spark 走势整体下行后回升
  { key: 'todos', label: '今日待办', icon: Tickets, color: 'blue', bg: 'linear-gradient(135deg, var(--chart-1), color-mix(in srgb, var(--chart-1) 72%, #ffffff))', tip: '待办审批与工单', spark: '0,24 14,16 28,20 42,10 56,14 70,6 80,12' },
  // 未读消息：紫色主题
  { key: 'messages', label: '未读消息', icon: Bell, color: 'purple', bg: 'linear-gradient(135deg, var(--chart-4), color-mix(in srgb, var(--chart-4) 72%, #ffffff))', tip: '站内消息未读', spark: '0,18 14,22 28,14 42,18 56,10 70,14 80,8' },
  // 运行中工作流：绿色主题
  { key: 'workflows', label: '运行中工作流', icon: TrendCharts, color: 'green', bg: 'linear-gradient(135deg, var(--chart-5), color-mix(in srgb, var(--chart-5) 72%, #ffffff))', tip: '流程实例总数', spark: '0,14 14,10 28,18 42,12 56,16 70,14 80,20' },
  // 今日新增用户：橙色主题
  { key: 'new_users', label: '今日新增用户', icon: UserFilled, color: 'orange', bg: 'linear-gradient(135deg, var(--chart-3), color-mix(in srgb, var(--chart-3) 72%, #ffffff))', tip: '今日注册用户', spark: '0,22 14,18 28,20 42,14 56,18 70,8 80,10' }
]

// 概览数据容器：stats 由接口整体替换；greeting/now 为预留字段，当前模板未直接使用
const overview = reactive({ stats: {}, greeting: '', now: '' })
// 监控数据容器：给出一套安全默认值，接口失败时页面仍能显示“正常 / 0 值 / --”
const monitor = reactive({ db_status: 'ok', disk_used: 0, disk_total: 0, disk_percent: 0, disk_free: 0, mem_percent: null, uptime: '' })

// 三个独立的 loading 标记，分别控制待办、动态、监控区域的遮罩；
// 分开而不是共用一个，是因为三块数据由两个接口返回，加载时机不同
const todoLoading = ref(false)
const activityLoading = ref(false)
const monitorLoading = ref(false)

// 待办列表数据，模板中直接读取长度与循环
const todoItems = ref([])
// 最新动态列表数据，元素包含 time/typeLabel/text/tagType/color
const activities = ref([])

// 磁盘进度条颜色：按占用率分三档（>80 危险、>60 警告、其余安全），
// 使用主题变量而非硬编码色值，暗色主题下自动换成对应色板
const diskColor = computed(() => {
  // 空值兜底为 0，避免 undefined 参与比较
  const p = monitor.disk_percent || 0
  // 超过 80% 视为磁盘紧张
  if (p > 80) return 'var(--app-danger)'
  // 60%-80% 予以警示
  if (p > 60) return 'var(--app-warning)'
  // 其余视为健康
  return 'var(--app-success)'
})

// 读取统计值：`?? 0` 只在 null/undefined 时兜底，
// 因此数值 0 不会被误显示为空
function getStatValue(key) {
  return overview.stats[key] ?? 0
}

// 统一的站内跳转：目标路由不存在或重复导航时 catch 掉异常，防止控制台报错
function go(path) {
  router.push(path).catch(() => {})
}

// 待办行点击：仅当后端给了 path 时才跳转，避免跳到空地址
function handleTodoClick(item) {
  if (item.path) go(item.path)
}

// 拉取概览数据：一次请求同时拿到统计、待办、动态，减少首页请求数
// 副作用：切换两处 loading、覆盖 overview/todoItems/activities
async function loadOverview() {
  // 进入即置 loading，保证首次渲染有遮罩而不是空白
  todoLoading.value = true
  activityLoading.value = true
  try {
    // GET /home/overview/ 由 request 自动拼 /api 前缀并携带 token
    const res = await request.get('/home/overview/')
    // 后端统一结构为 { code, msg, data }，这里取 data；空响应兜底为空对象
    const data = res.data || {}
    // 先整体合并（保留 greeting/now 等扩展字段）
    Object.assign(overview, data)
    // stats 单独兜底为空对象，防止 getStatValue 访问 undefined 报错
    overview.stats = data.stats || {}
    // 待办与动态缺省为空数组，模板的 v-if 才能正常工作
    todoItems.value = data.todos || []
    activities.value = data.activities || []
  } catch (e) {
    // 请求失败时清空两块列表，配合空状态提示，不向用户抛错（拦截器已提示）
    todoItems.value = []
    activities.value = []
  } finally {
    // 无论成败都要关闭 loading，否则遮罩会一直停留
    todoLoading.value = false
    activityLoading.value = false
  }
}

// 拉取系统监控数据：独立接口，失败时保留默认值静默忽略
async function loadMonitor() {
  monitorLoading.value = true
  try {
    const res = await request.get('/home/monitor/')
    // 仅在拿到 data 时合并，避免把 monitor 覆盖成 undefined
    if (res.data) Object.assign(monitor, res.data)
  } catch (e) { /* ignore */ }
  // 这里未放在 finally 中，若上面抛错也会执行到这一行（catch 已吞掉异常）
  monitorLoading.value = false
}

// 组件挂载后触发两个接口，并行请求以缩短首屏等待
onMounted(() => {
  loadOverview()
  loadMonitor()
})
</script>

<style scoped>
/* ============================================================
   样式区说明：scoped 保证样式只作用于本页。
   颜色一律引用全局主题变量（--app-* 面板/文字/状态色、--brand-* 品牌色、
   --chart-* 图表色），不写死色值，因此换肤与暗色模式可自动跟随。
   ============================================================ */
/* 页面根容器：留出底部间距，避免最后一行卡片紧贴页面边缘 */
.dashboard-wrap {
  padding-bottom: 20px;
}

/* ============ Hero Banner ============ */
/* 顶部横幅：品牌渐变背景 + 大圆角 + 柔和光晕，构成首页主视觉 */
.hero-banner {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 28px 32px;
  margin-bottom: 18px;
  /* 品牌渐变随主题切换 */
  background: var(--brand-gradient);
  /* 使用主题化圆角变量，与整体设计语言一致 */
  border-radius: var(--app-radius-xl);
  /* 光晕阴影同样取品牌色，暗色下不会发黑 */
  box-shadow: 0 10px 36px var(--brand-glow);
  /* 裁掉装饰圆的溢出部分，形成弧形装饰 */
  overflow: hidden;
  color: #fff;
}

/* 装饰圆基础样式：绝对定位 + 圆形 + 低透明白，
   具体位置与大小由下面 -1/-2/-3 三个变体分别覆盖 */
.hero-decor {
  position: absolute;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.1);
}
/* 装饰圆 1：右上偏内，标准透明度，作为主要光斑 */
.hero-decor-1 { top: -60px; right: 10%; width: 200px; height: 200px; }
/* 装饰圆 2：底部大幅溢出，透明度更低，避免与主光斑抢视觉 */
.hero-decor-2 { bottom: -90px; right: 28%; width: 180px; height: 180px; background: rgba(255, 255, 255, 0.07); }
/* 装饰圆 3：右上角部分出界，透明度最高，模拟边缘高光 */
.hero-decor-3 { top: 30px; right: -30px; width: 120px; height: 120px; background: rgba(255, 255, 255, 0.12); }

/* 左侧欢迎区：相对定位并抬高层级，保证内容不被装饰圆遮挡 */
.hero-left {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 18px;
}

/* Banner 内的头像：白底反衬品牌色文字；letter-spacing 等由 el-avatar 内部处理 */
.hero-avatar {
  /* 文字头像使用品牌主色 */
  color: var(--brand-primary);
  /* 白底在渐变背景上更醒目 */
  background: #fff;
  font-size: 22px;
  font-weight: 700;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.18);
  /* 半透明白描边，让头像与背景之间有过渡 */
  border: 3px solid rgba(255, 255, 255, 0.6);
}

/* 问候语主文字：字号最大，承担欢迎区视觉重点 */
.hero-greeting {
  font-size: 22px;
  font-weight: 600;
  letter-spacing: 0.5px;
}
/* 副标题：半透明白色，弱化层级但保证在渐变上可读 */
.hero-sub {
  margin-top: 8px;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.85);
}

/* 右侧快捷入口容器：相对定位抬高层级，并允许小屏换行 */
.hero-right {
  position: relative;
  z-index: 1;
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

/* 单个快捷入口：半透明毛玻璃块，可点击；
   min-width 保证四个入口宽度一致，hover 时上浮增强可点感 */
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
/* 悬停：提高背景不透明度并上移 2px，给出即时反馈 */
.quick-entry:hover {
  background: rgba(255, 255, 255, 0.28);
  transform: translateY(-2px);
}
/* 入口图标底板：固定 38x38 的圆角方块，背景色由行内样式注入 */
.quick-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  border-radius: 10px;
  color: #fff;
}
/* 入口文字：小号居中，避免在窄屏下折行过多 */
.quick-label {
  font-size: 12px;
  font-weight: 500;
}

/* ============ 统计卡片 ============ */
/* 统计行与下方内容区的间距 */
.stat-row { margin-bottom: 18px; }
/* 统计列的下间距：小屏堆叠时避免两行卡片贴在一起 */
.stat-col { margin-bottom: 16px; }

/* 统计卡片主体：面板底色 + 主题圆角 + 轻阴影；
   overflow:hidden 用于裁掉右下角折线与卡片边界的溢出 */
.stat-card {
  position: relative;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 20px 22px;
  /* 使用面板背景变量，暗色主题自动变深 */
  background: var(--app-surface);
  border-radius: var(--app-radius-lg);
  box-shadow: var(--app-shadow-sm);
  border: 1px solid var(--app-border-light);
  overflow: hidden;
  transition: transform 0.2s, box-shadow 0.2s, border-color 0.2s;
}
/* 悬停：轻微上浮 + 加深阴影 + 品牌色描边，突出可交互感 */
.stat-card:hover {
  transform: translateY(-3px);
  box-shadow: var(--app-shadow-md);
  border-color: var(--brand-primary-border);
}
/* 图标底板：52x52 圆角方块，白字；背景色由配置项行内注入 */
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
/* 文字区：flex:1 占满剩余宽度；min-width:0 允许长文案被压缩而不撑破卡片 */
.stat-info { flex: 1; min-width: 0; }
/* 主数值：28px 加粗；tabular-nums 让数字等宽，数值变化时不产生横向抖动 */
.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--app-text-1);
  line-height: 1.1;
  font-variant-numeric: tabular-nums;
}
/* 指标名称：次级文字色 */
.stat-label {
  margin-top: 4px;
  font-size: 13px;
  color: var(--app-text-3);
}
/* 趋势说明行容器 */
.stat-trend {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 6px;
  font-size: 12px;
}
/* 上涨态文字：成功色，加粗强调 */
.trend-up { color: var(--app-success); font-weight: 600; }
/* 下跌态文字：危险色，加粗强调 */
.trend-down { color: var(--app-danger); font-weight: 600; }
/* 说明文字：弱化色，与涨跌标识区分 */
.trend-tip { color: var(--app-text-3); margin-left: 2px; }

/* 迷你折线容器：绝对定位到右下角，半透明以不干扰数值读取 */
.stat-spark {
  position: absolute;
  right: 12px;
  bottom: 12px;
  opacity: 0.5;
  width: 80px;
  height: 36px;
}
/* 四种卡片主题色：只影响折线颜色（polyline 用 currentColor），
   取值为主题图表色变量，换肤后自动同步 */
.stat-blue .stat-spark { color: var(--chart-1); }
.stat-purple .stat-spark { color: var(--chart-4); }
.stat-green .stat-spark { color: var(--chart-5); }
.stat-orange .stat-spark { color: var(--chart-3); }

/* ============ 面板通用 ============ */
/* 两行内容区与底部的行间距；底部行单独清零，避免页面尾部出现多余留白 */
.content-row, .bottom-row { margin-bottom: 18px; }
.bottom-row { margin-bottom: 0; }

/* 同一行卡片等高，消除短内容下方的空白 */
/* 让 el-col 自身成为 flex 容器，内部的 panel 才能通过 height:100% 撑满整行高度 */
.content-row > .el-col,
.bottom-row > .el-col,
.stat-row > .el-col { display: flex; }

/* 面板卡片：统一圆角、边框，并改造成纵向 flex 以便 body 区域撑满；
   height:100% 与上面的 flex 配合实现同一行等高 */
.panel { border-radius: var(--app-radius-lg); border: 1px solid var(--app-border-light); display: flex; flex-direction: column; height: 100%; }
/* 卡片头部内边距与分隔线：:deep 穿透 scoped，才能选中 Element Plus 内部节点；
   分隔线用主题边框色，暗色下自动调整 */
.panel :deep(.el-card__header) { padding: 14px 20px; border-bottom: 1px solid var(--app-border-light); }
/* 卡片主体：flex:1 占满剩余高度，内部再纵向排列 */
.panel :deep(.el-card__body) { padding: 16px 20px; flex: 1; display: flex; flex-direction: column; }
/* 统计卡片在栅格列内撑满宽度 */
.stat-card { width: 100%; }

/* 面板标题栏：左右两端对齐（标题靠左、状态标签靠右） */
.panel-header { display: flex; align-items: center; justify-content: space-between; }
/* 标题组合：色条 + 文字 + 计数标签横向排列 */
.panel-title {
  display: flex; align-items: center; gap: 8px; font-size: 15px; font-weight: 600; color: var(--app-text-1);
}
/* 标题左侧竖条：4x16 的小色块，起装饰与分区指示作用 */
.panel-dot { width: 4px; height: 16px; border-radius: 3px; }
/* 四种色条分别对应各面板的主题图表色，跟随换肤 */
.dot-blue { background: linear-gradient(180deg, var(--chart-1), var(--chart-1)); }
.dot-purple { background: linear-gradient(180deg, var(--chart-4), var(--chart-4)); }
.dot-green { background: linear-gradient(180deg, var(--chart-5), var(--chart-5)); }
.dot-orange { background: linear-gradient(180deg, var(--chart-3), var(--chart-3)); }
/* 计数标签与标题文字留一点间距 */
.panel-count { margin-left: 4px; }
/* 监控面板右上角的状态标签字重 */
.status-tag { font-weight: 500; }

/* ============ 待办事项 ============ */
/* 列表容器：撑满卡片剩余高度，纵向排列；min-height 保证空状态下也有足够留白 */
.todo-list { min-height: 120px; flex: 1; display: flex; flex-direction: column; }
/* 注意：此处先给 todo-item 设 flex:1，下面还有一条同名规则会覆盖它，
   实际生效的是后面那条完整定义（原状保留、未合并，仅作说明） */
.todo-item { flex: 1; }
/* 空状态：图标与文案纵向居中，弱化色，避免空白区域显得像加载失败 */
.empty-hint {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 10px; padding: 30px 0; color: var(--app-text-3); font-size: 13px;
}
/* 待办单行：左右布局（左侧信息、右侧操作按钮），次要背景色与主体区分；
   整行可点击，因此加 pointer 光标 */
.todo-item {
  display: flex; align-items: center; justify-content: space-between;
  gap: 12px; padding: 12px 14px; margin-bottom: 10px;
  background: var(--app-surface-2); border-radius: var(--app-radius-md); cursor: pointer;
  transition: background 0.15s, transform 0.15s;
}
/* 悬停：换用品牌浅色底并右移 2px，形成“可进入”的暗示 */
.todo-item:hover { background: var(--brand-primary-soft); transform: translateX(2px); }
/* 左侧信息列：flex:1 占据剩余空间，min-width:0 防止长标题溢出 */
.todo-left { flex: 1; min-width: 0; }
/* 类型徽标：小圆角胶囊样式，颜色由下面 type-* 类按业务类型区分 */
.todo-type {
  display: inline-block; padding: 2px 8px; border-radius: var(--app-radius-xs); font-size: 11px; font-weight: 600;
  margin-bottom: 6px;
}
/* 流程类待办：品牌主色系 */
.type-workflow { background: var(--brand-primary-soft); color: var(--brand-primary); }
/* 工单类待办：警告色系；用 color-mix 混出 14% 透明底，暗色下也不会过亮 */
.type-wo { background: color-mix(in srgb, var(--app-warning) 14%, transparent); color: var(--app-warning); }
/* 日程类待办：成功色系，同样用 color-mix 生成浅底 */
.type-cal { background: color-mix(in srgb, var(--app-success) 14%, transparent); color: var(--app-success); }
/* 待办标题：主文字色，稍加粗以在浅底上突出 */
.todo-title { font-size: 14px; color: var(--app-text-1); font-weight: 500; margin-bottom: 4px; }
/* 元信息行：发起人与时间横向排列，弱化色 */
.todo-meta { font-size: 12px; color: var(--app-text-3); display: flex; gap: 14px; }

/* ============ 最新动态 ============ */
/* 时间轴容器：撑满卡片剩余高度，使卡片与左侧待办等高 */
.activity-body { flex: 1; }
/* 单条动态：标签与文本水平排列并垂直居中 */
.activity-item { display: flex; align-items: center; gap: 8px; }
/* 类型标签不参与压缩，防止长文本把标签挤变形 */
.activity-tag { flex-shrink: 0; }
/* 动态正文：次级文字色，保证可读又不抢标题 */
.activity-text { font-size: 13px; color: var(--app-text-2); }

/* ============ 系统监控 ============ */
/* 监控主体：纵向等分剩余空间，三个监控项分布均匀 */
.monitor-body { padding: 4px 0; flex: 1; display: flex; flex-direction: column; justify-content: space-evenly; }
/* 单个监控项：项间留白，最后一项去掉下边距避免底部空白 */
.monitor-item { margin-bottom: 18px; }
.monitor-item:last-child { margin-bottom: 0; }
/* 监控项行：左标签右数值，两端对齐 */
.monitor-row {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 8px; font-size: 13px;
}
/* 左侧标签：图标 + 文字，次级文字色 */
.monitor-label { display: flex; align-items: center; gap: 6px; color: var(--app-text-2); }
/* 右侧数值：弱化色 + 等宽数字，避免百分比刷新时跳动 */
.monitor-val { color: var(--app-text-3); font-variant-numeric: tabular-nums; }
/* 附加指标行：内存、可用空间，小号弱化文字 */
.monitor-meta {
  display: flex; gap: 16px; margin-top: 8px; font-size: 12px; color: var(--app-text-3);
}

/* ============ 常用功能 ============ */
/* 九宫格：固定 3 列等宽网格，flex:1 让网格随卡片高度拉伸 */
.common-grid {
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; flex: 1;
}
/* 单个功能块：次要背景 + 圆角，可点击；hover 时上浮并加阴影 */
.common-item {
  display: flex; align-items: center; gap: 12px;
  padding: 14px 12px; background: var(--app-surface-2); border-radius: var(--app-radius-md);
  cursor: pointer; transition: background 0.15s, transform 0.15s, box-shadow 0.15s;
}
/* 悬停：底色回到面板主色 + 上浮 2px，并显式写出 transition 涉及的属性 */
.common-item:hover {
  background: var(--app-surface); transform: translateY(-2px);
  box-shadow: var(--app-shadow-md);
}
/* 功能图标底板：42x42 圆角方块，背景由行内样式注入，白字 */
.ci-icon {
  display: flex; align-items: center; justify-content: center;
  width: 42px; height: 42px; border-radius: var(--app-radius-md); color: #fff; flex-shrink: 0;
}
/* 文案区：占满剩余宽度，min-width:0 允许省略长描述 */
.ci-text { flex: 1; min-width: 0; }
/* 功能主标题 */
.ci-title { font-size: 13px; font-weight: 600; color: var(--app-text-1); }
/* 功能副描述：更小字号与弱化色 */
.ci-desc { font-size: 11px; color: var(--app-text-3); margin-top: 2px; }

/* 小屏适配 */
@media (max-width: 768px) {
  /* 横幅改为纵向排列，内容左对齐，避免快捷入口与问候区挤在一行 */
  .hero-banner {
    flex-direction: column; align-items: flex-start; padding: 22px;
  }
  /* 快捷入口整体换行后占满宽度并左对齐 */
  .hero-right { margin-top: 14px; width: 100%; justify-content: flex-start; }
  /* 九宫格降为 2 列，保证每个功能块仍有足够点击区域 */
  .common-grid { grid-template-columns: repeat(2, 1fr); }
}
</style>
