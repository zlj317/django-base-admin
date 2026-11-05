<template>
<!-- ============================================================
     文件：系统首页 / 工作台（views/dashboard/index.vue）
     职责：登录后的默认落地页。聚合展示欢迎语与快捷入口、四项关键统计、
           业务趋势、待办、公告、消息、工作流、系统监控、文件、任务、告警、
           报表/BI、知识库、日程、用户组织，以及按模块分组的常用功能索引。
     依赖：@/store/auth（当前用户）、@/utils/request（/home/rich/、
           /home/overview/ 兜底、/home/monitor/）、两个本地 SVG 图表组件。
     数据：优先使用 /home/rich/ 的真实聚合数据；接口不可用时回退到
           /home/overview/，保证首页不白屏。
     主题：除 Banner 品牌渐变上的反白色外，所有颜色均来自 tokens.css 的
           --app-* / --brand-* / --chart-* 变量，明暗 + 5 套配色自动适配。
     布局：栅格列统一 display:flex，面板统一 width:100% + min-width:0，
           从根上避免 flex 子项收缩导致的横向空洞。
     ============================================================ -->
  <div class="app-container dashboard-wrap">
    <!-- ---------- 顶部欢迎 Banner ---------- -->
    <div class="hero-banner">
      <!-- 三个装饰圆：纯视觉点缀，父级 overflow:hidden 裁切出弧形光斑 -->
      <div class="hero-decor hero-decor-1"></div>
      <div class="hero-decor hero-decor-2"></div>
      <div class="hero-decor hero-decor-3"></div>

      <!-- 左侧欢迎区：头像 + 问候语 + 日期与数据更新时间 -->
      <div class="hero-left">
        <!-- 头像：优先用户头像；空字符串会让 <img> 破图，因此回退为 undefined -->
        <el-avatar :size="60" :src="auth.user.avatar || undefined" class="hero-avatar">
          <!-- 无头像时取显示名首字符做大写文字头像 -->
          {{ displayName.slice(0, 1).toUpperCase() }}
        </el-avatar>
        <!-- 文案区 -->
        <div class="hero-text">
          <!-- 问候语：按小时计算，拼接当前用户显示名 -->
          <div class="hero-greeting">{{ greeting }}，{{ displayName }}！</div>
          <!-- 副标题：日期 + 数据更新时间（刷新后同步变化） -->
          <div class="hero-sub">
            今天是 {{ todayText }}，欢迎回到管理后台
            <span v-if="rich.generated_at" class="hero-updated">· 数据截至 {{ rich.generated_at.slice(11, 16) }}</span>
          </div>
        </div>
      </div>

      <!-- 右侧快捷入口：4 个高频操作，点击跳转对应页面 -->
      <div class="hero-right">
        <!-- 逐项渲染：图标底板使用主题图表色渐变 -->
        <div class="quick-entry" v-for="entry in quickEntries" :key="entry.title" @click="go(entry.path)">
          <div class="quick-icon" :style="{ background: entry.bg }">
            <el-icon :size="20"><component :is="entry.icon" /></el-icon>
          </div>
          <div class="quick-label">{{ entry.title }}</div>
        </div>
      </div>
    </div>

    <!-- ---------- 四项关键指标 ---------- -->
    <el-row :gutter="16" class="stat-row">
      <!-- 响应式：手机 24（整行）、平板 12（两列）、桌面 6（四列） -->
      <el-col :xs="24" :sm="12" :md="6" v-for="(s, idx) in statCards" :key="s.key">
        <!-- 统计卡：类名 stat-{color} 只控制迷你折线的 currentColor -->
        <div class="stat-card" :class="'stat-' + s.color">
          <!-- 图标底板：背景为配置项里的主题渐变 -->
          <div class="stat-icon-wrap" :style="{ background: s.bg }">
            <el-icon :size="24"><component :is="s.icon" /></el-icon>
          </div>
          <!-- 数值与文案 -->
          <div class="stat-info">
            <!-- 主数值：来自 rich.stats，缺失时回退 0 -->
            <div class="stat-value">{{ s.value }}</div>
            <!-- 指标名 -->
            <div class="stat-label">{{ s.label }}</div>
            <!-- 环比：较昨日差值，正负用不同颜色；0 显示“持平” -->
            <div class="stat-trend">
              <span :class="deltaClass(s.delta)">{{ deltaText(s.delta) }}</span>
              <span class="trend-tip">{{ s.tip }}</span>
            </div>
          </div>
          <!-- 右下角迷你折线：使用真实 7 日序列，而非静态装饰 -->
          <div class="stat-spark">
            <svg viewBox="0 0 84 28" class="sparkline" preserveAspectRatio="none">
              <polyline
                :points="sparkPoints(s.values)"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
            </svg>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- ---------- 第一行：业务趋势 + 待办 ---------- -->
    <el-row :gutter="16" class="grid-row">
      <!-- 趋势面板：占 14 格，两张折线图分别展示工单/流程、消息/文件 -->
      <el-col :xs="24" :md="14">
        <el-card shadow="never" class="panel">
          <template #header>
            <div class="panel-header">
              <div class="panel-title">
                <span class="panel-dot dot-blue"></span>
                <span>业务趋势</span>
                <el-tag effect="light" size="small" type="info" class="panel-count">近 7 天</el-tag>
              </div>
              <span class="panel-extra">新增数量 / 天</span>
            </div>
          </template>
          <!-- 图表容器：两张图上下排列，填满卡片高度 -->
          <div class="trend-stack" ref="trendStackRef">
            <!-- 图一：工单新增 vs 流程发起 -->
            <div class="trend-block">
              <div class="block-caption">
                <span class="caption-dot" :style="{ background: 'var(--chart-3)' }"></span>
                工单与流程
              </div>
              <TrendChart :labels="rich.trends.dates" :series="bizSeries" :height="trendChartHeight" />
            </div>
            <!-- 图二：消息 vs 文件 -->
            <div class="trend-block">
              <div class="block-caption">
                <span class="caption-dot" :style="{ background: 'var(--chart-4)' }"></span>
                消息与文件
              </div>
              <TrendChart :labels="rich.trends.dates" :series="docSeries" :height="trendChartHeight" />
            </div>
          </div>
          <!-- 底部速览：三个关键剩余量，进一步填充卡片底部空间 -->
          <div class="trend-foot">
            <div class="foot-metric">
              <span class="fm-value">{{ rich.stats.wo_open ?? 0 }}</span>
              <span class="fm-label">未完成工单</span>
            </div>
            <div class="foot-metric">
              <span class="fm-value">{{ rich.stats.alarm_open ?? 0 }}</span>
              <span class="fm-label">未处理告警</span>
            </div>
            <div class="foot-metric">
              <span class="fm-value">{{ formatBytes(rich.stats.file_size) }}</span>
              <span class="fm-label">文件占用</span>
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 待办面板：占 10 格，最多展示 8 条，超出滚动 -->
      <el-col :xs="24" :md="10">
        <el-card shadow="never" class="panel">
          <template #header>
            <div class="panel-header">
              <div class="panel-title">
                <span class="panel-dot dot-purple"></span>
                <span>待办事项</span>
                <!-- 数量标签：待办总数，而非当前列表长度 -->
                <el-tag effect="light" size="small" type="primary" class="panel-count">{{ rich.stats.todos ?? 0 }}</el-tag>
              </div>
              <!-- 查看全部：跳到流程待办页 -->
              <el-button link type="primary" @click="go('/workflow/todo')">全部待办</el-button>
            </div>
          </template>
          <div class="todo-list" v-loading="loading">
            <!-- 空数据：引导卡而不是空白 -->
            <div v-if="!rich.todos.length" class="guide-card">
              <el-icon :size="30"><Tickets /></el-icon>
              <div class="guide-title">当前没有待办</div>
              <div class="guide-desc">流程审批与工单待办会汇总到这里，可前往发起流程或提交工单。</div>
              <el-button type="primary" plain size="small" @click="go('/workflow/model')">发起流程</el-button>
            </div>
            <!-- 待办列表：整行可点击；用 template 包裹避免 v-else 与 v-for 同元素 -->
            <template v-else>
              <div
                v-for="(item, i) in rich.todos"
                :key="item.source + '-' + item.id + '-' + i"
                class="todo-item"
                @click="handleTodoClick(item)"
              >
                <div class="todo-left">
                  <!-- 类型徽标：按来源着色（流程/工单/日程） -->
                  <span class="todo-type" :class="typeClass(item.source)">{{ item.typeLabel }}</span>
                  <div class="todo-title">{{ item.title }}</div>
                  <div class="todo-meta">
                    <span v-if="item.creator">{{ item.creator }}</span>
                    <span v-if="item.time" class="todo-time">⏰ {{ item.time }}</span>
                  </div>
                </div>
                <el-button link type="primary">处理 →</el-button>
              </div>
            </template>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- ---------- 第二行：公告 + 消息 + 工作流 ---------- -->
    <el-row :gutter="16" class="grid-row">
      <!-- 公告通知 -->
      <el-col :xs="24" :md="8">
        <el-card shadow="never" class="panel">
          <template #header>
            <div class="panel-header">
              <div class="panel-title">
                <span class="panel-dot dot-orange"></span>
                <span>公告通知</span>
              </div>
              <el-button link type="primary" @click="go('/notice/info')">查看全部</el-button>
            </div>
          </template>
          <div class="list-body" v-loading="loading">
            <div v-if="!rich.notices.length" class="guide-card compact">
              <el-icon :size="26"><Document /></el-icon>
              <div class="guide-title">暂无公告</div>
              <div class="guide-desc">发布系统通知、制度文件后，会在此处展示。</div>
              <el-button type="primary" plain size="small" @click="go('/notice/info')">发布公告</el-button>
            </div>
            <!-- 公告条目：标题 + 摘要 + 时间 -->
            <template v-else>
              <div v-for="n in rich.notices" :key="'notice-' + n.id" class="list-item" @click="go('/notice/info')">
                <div class="li-main">
                  <div class="li-title">{{ n.title }}</div>
                  <div class="li-desc">{{ n.content || '暂无摘要' }}</div>
                </div>
                <span class="li-time">{{ n.time }}</span>
              </div>
            </template>
          </div>
        </el-card>
      </el-col>

      <!-- 站内消息 -->
      <el-col :xs="24" :md="8">
        <el-card shadow="never" class="panel">
          <template #header>
            <div class="panel-header">
              <div class="panel-title">
                <span class="panel-dot dot-green"></span>
                <span>站内消息</span>
                <!-- 未读数：来自 stats.messages -->
                <el-tag v-if="(rich.stats.messages ?? 0) > 0" effect="light" size="small" type="danger" class="panel-count">
                  {{ rich.stats.messages }} 未读
                </el-tag>
              </div>
              <el-button link type="primary" @click="go('/msg/record')">消息中心</el-button>
            </div>
          </template>
          <div class="list-body" v-loading="loading">
            <div v-if="!rich.messages.length" class="guide-card compact">
              <el-icon :size="26"><Bell /></el-icon>
              <div class="guide-title">暂无站内消息</div>
              <div class="guide-desc">报表完成、接口异常、流程提醒等消息会推送到这里。</div>
              <el-button type="primary" plain size="small" @click="go('/msg/record')">去配置消息</el-button>
            </div>
            <!-- 消息条目：未读圆点 + 标题 + 摘要 + 时间 -->
            <template v-else>
              <div v-for="m in rich.messages" :key="'msg-' + m.id" class="list-item" @click="go('/msg/record')">
                <div class="li-main">
                  <div class="li-title">
                    <span class="unread-dot" :class="{ 'is-read': m.read }"></span>
                    {{ m.title }}
                  </div>
                  <div class="li-desc">{{ m.content || '暂无摘要' }}</div>
                </div>
                <span class="li-time">{{ m.time }}</span>
              </div>
            </template>
          </div>
        </el-card>
      </el-col>

      <!-- 工作流实例 -->
      <el-col :xs="24" :md="8">
        <el-card shadow="never" class="panel">
          <template #header>
            <div class="panel-header">
              <div class="panel-title">
                <span class="panel-dot dot-blue"></span>
                <span>工作流实例</span>
              </div>
              <el-button link type="primary" @click="go('/workflow/instance')">流程中心</el-button>
            </div>
          </template>
          <div class="list-body" v-loading="loading">
            <div v-if="!rich.workflows.length" class="guide-card compact">
              <el-icon :size="26"><Connection /></el-icon>
              <div class="guide-title">暂无流程实例</div>
              <div class="guide-desc">在流程模型中发起审批后，实例会在此处实时展示。</div>
              <el-button type="primary" plain size="small" @click="go('/workflow/model')">去发起</el-button>
            </div>
            <!-- 实例条目：流程名 + 当前节点 + 状态 + 时间 -->
            <template v-else>
              <div v-for="w in rich.workflows" :key="'wf-' + w.id" class="list-item" @click="go('/workflow/instance')">
                <div class="li-main">
                  <div class="li-title">{{ w.model_name }}</div>
                  <div class="li-desc">当前节点：{{ w.node }}</div>
                </div>
                <div class="li-side">
                  <el-tag effect="light" size="small" :type="wfTagType(w.status)">{{ w.status_label }}</el-tag>
                  <span class="li-time">{{ w.time }}</span>
                </div>
              </div>
            </template>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- ---------- 第三行：系统监控 + 文件存储 + 定时任务 ---------- -->
    <el-row :gutter="16" class="grid-row">
      <!-- 系统监控：数据库、磁盘、内存、运行时长 -->
      <el-col :xs="24" :md="8">
        <el-card shadow="never" class="panel">
          <template #header>
            <div class="panel-header">
              <div class="panel-title">
                <span class="panel-dot dot-green"></span>
                <span>系统监控</span>
              </div>
              <!-- 服务状态标签：按数据库连通性切换成功/危险色 -->
              <el-tag effect="light" size="small" :type="monitor.db_status === 'ok' ? 'success' : 'danger'">
                ● {{ monitor.db_status === 'ok' ? '运行正常' : '服务异常' }}
              </el-tag>
            </div>
          </template>
          <div class="monitor-body" v-loading="monitorLoading">
            <!-- 数据库 -->
            <div class="meter">
              <div class="meter-row">
                <span class="meter-label"><el-icon :size="14"><Cpu /></el-icon> 数据库连接</span>
                <span class="meter-val">{{ monitor.db?.database_name || '--' }}</span>
              </div>
              <el-progress
                :percentage="monitor.db_status === 'ok' ? 100 : 0"
                :stroke-width="6"
                :show-text="false"
                :color="monitor.db_status === 'ok' ? 'var(--app-success)' : 'var(--app-danger)'"
              />
            </div>
            <!-- 磁盘 -->
            <div class="meter">
              <div class="meter-row">
                <span class="meter-label"><el-icon :size="14"><FolderOpened /></el-icon> 磁盘空间</span>
                <span class="meter-val">{{ monitor.disk_total ? `${monitor.disk_used} / ${monitor.disk_total} GB` : '--' }}</span>
              </div>
              <el-progress :percentage="monitor.disk_percent || 0" :stroke-width="6" :color="diskColor" />
            </div>
            <!-- 内存 -->
            <div class="meter">
              <div class="meter-row">
                <span class="meter-label"><el-icon :size="14"><Monitor /></el-icon> 内存占用</span>
                <span class="meter-val">{{ monitor.mem_percent ?? '--' }}%</span>
              </div>
              <el-progress :percentage="monitor.mem_percent || 0" :stroke-width="6" :color="memColor" />
            </div>
            <!-- 运行时长与服务器时间 -->
            <div class="meter-foot">
              <span>Uptime {{ monitor.uptime || '--' }}</span>
              <span>{{ monitor.server_time || '--' }}</span>
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 文件与存储 -->
      <el-col :xs="24" :md="8">
        <el-card shadow="never" class="panel">
          <template #header>
            <div class="panel-header">
              <div class="panel-title">
                <span class="panel-dot dot-purple"></span>
                <span>文件与存储</span>
              </div>
              <el-button link type="primary" @click="go('/file')">文件管理</el-button>
            </div>
          </template>
          <div class="stat-pairs">
            <div class="pair">
              <div class="pair-value">{{ rich.files.count ?? 0 }}</div>
              <div class="pair-label">文件总数</div>
            </div>
            <div class="pair">
              <div class="pair-value">{{ formatBytes(rich.files.size) }}</div>
              <div class="pair-label">占用空间</div>
            </div>
          </div>
          <!-- 按扩展名分布：无数据时提示上传 -->
          <div v-if="rich.files.by_ext?.length" class="dist-wrap">
            <div class="sub-title">按类型分布</div>
            <DistributionBar :items="fileExtItems" />
          </div>
          <div v-else class="guide-card compact">
            <el-icon :size="26"><FolderOpened /></el-icon>
            <div class="guide-title">还没有上传文件</div>
            <div class="guide-desc">上传后可统计类型分布与存储占用。</div>
            <el-button type="primary" plain size="small" @click="go('/file')">去上传</el-button>
          </div>
        </el-card>
      </el-col>

      <!-- 定时任务 -->
      <el-col :xs="24" :md="8">
        <el-card shadow="never" class="panel">
          <template #header>
            <div class="panel-header">
              <div class="panel-title">
                <span class="panel-dot dot-orange"></span>
                <span>定时任务</span>
              </div>
              <el-button link type="primary" @click="go('/task')">任务调度</el-button>
            </div>
          </template>
          <div class="stat-pairs">
            <div class="pair">
              <div class="pair-value">{{ rich.tasks.total ?? 0 }}</div>
              <div class="pair-label">任务总数</div>
            </div>
            <div class="pair">
              <div class="pair-value">{{ rich.tasks.enabled ?? 0 }}</div>
              <div class="pair-label">启用中</div>
            </div>
          </div>
          <div v-if="rich.tasks.recent?.length" class="mini-list">
            <div class="sub-title">最近执行</div>
            <div v-for="(t, i) in rich.tasks.recent" :key="'task-' + i" class="mini-row">
              <span class="mini-name">{{ t.name }}</span>
              <el-tag effect="light" size="small" :type="taskTagType(t.status)">{{ t.status_label }}</el-tag>
              <span class="mini-time">{{ t.time }}</span>
            </div>
          </div>
          <div v-else class="guide-card compact">
            <el-icon :size="26"><Stopwatch /></el-icon>
            <div class="guide-title">暂无执行记录</div>
            <div class="guide-desc">创建 Cron 或间隔任务后，执行结果会显示在这里。</div>
            <el-button type="primary" plain size="small" @click="go('/task')">去创建</el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- ---------- 第四行：监控告警 + 报表/BI + 知识库 ---------- -->
    <el-row :gutter="16" class="grid-row">
      <!-- 监控告警 -->
      <el-col :xs="24" :md="8">
        <el-card shadow="never" class="panel">
          <template #header>
            <div class="panel-header">
              <div class="panel-title">
                <span class="panel-dot dot-red"></span>
                <span>监控告警</span>
                <!-- 未处理数量：突出显示 -->
                <el-tag v-if="(rich.alarms.open ?? 0) > 0" effect="light" size="small" type="danger" class="panel-count">
                  {{ rich.alarms.open }} 待处理
                </el-tag>
              </div>
              <el-button link type="primary" @click="go('/mon/alarm/record')">告警中心</el-button>
            </div>
          </template>
          <div class="stat-pairs">
            <div class="pair">
              <div class="pair-value">{{ rich.alarms.open ?? 0 }}</div>
              <div class="pair-label">未处理</div>
            </div>
            <div class="pair">
              <div class="pair-value">{{ rich.alarms.total ?? 0 }}</div>
              <div class="pair-label">累计告警</div>
            </div>
          </div>
          <!-- 未处理告警按级别分布；无数据时给出引导 -->
          <div v-if="rich.alarms.by_level?.length" class="dist-wrap">
            <div class="sub-title">未处理级别分布</div>
            <DistributionBar :items="alarmItems" />
          </div>
          <div v-else class="guide-card compact">
            <el-icon :size="26"><WarningFilled /></el-icon>
            <div class="guide-title">当前无未处理告警</div>
            <div class="guide-desc">CPU、磁盘、接口等监控规则触发后会在此汇总。</div>
            <el-button type="primary" plain size="small" @click="go('/mon/rule')">配置规则</el-button>
          </div>
          <!-- 最近告警：最多两条，避免卡片过高 -->
          <div v-if="rich.alarms.recent?.length" class="mini-list">
            <div v-for="a in rich.alarms.recent.slice(0, 2)" :key="'alarm-' + a.id" class="mini-row">
              <span class="alarm-dot" :class="'lv-' + a.level"></span>
              <span class="mini-name">{{ a.content }}</span>
              <span class="mini-time">{{ a.time }}</span>
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 报表与 BI -->
      <el-col :xs="24" :md="8">
        <el-card shadow="never" class="panel">
          <template #header>
            <div class="panel-header">
              <div class="panel-title">
                <span class="panel-dot dot-blue"></span>
                <span>报表与 BI</span>
              </div>
              <el-button link type="primary" @click="go('/rp/template')">报表管理</el-button>
            </div>
          </template>
          <div class="stat-pairs four">
            <div class="pair">
              <div class="pair-value">{{ rich.reports.templates ?? 0 }}</div>
              <div class="pair-label">报表模板</div>
            </div>
            <div class="pair">
              <div class="pair-value">{{ rich.reports.generated ?? 0 }}</div>
              <div class="pair-label">生成记录</div>
            </div>
            <div class="pair">
              <div class="pair-value">{{ rich.bi.total ?? 0 }}</div>
              <div class="pair-label">BI 大屏</div>
            </div>
            <div class="pair">
              <div class="pair-value">{{ rich.bi.published ?? 0 }}</div>
              <div class="pair-label">已发布</div>
            </div>
          </div>
          <!-- 最近报表生成 -->
          <div v-if="rich.reports.recent?.length" class="mini-list">
            <div class="sub-title">最近生成</div>
            <div v-for="(r, i) in rich.reports.recent.slice(0, 3)" :key="'rpt-' + i" class="mini-row">
              <span class="mini-name">{{ r.name }}</span>
              <el-tag effect="light" size="small" :type="genTagType(r.status)">{{ r.status_label }}</el-tag>
              <span class="mini-time">{{ r.time }}</span>
            </div>
          </div>
          <!-- BI 大屏列表，作为报表无数据时的补充信息 -->
          <div v-else-if="rich.bi.list?.length" class="mini-list">
            <div class="sub-title">BI 大屏</div>
            <div v-for="b in rich.bi.list.slice(0, 3)" :key="'bi-' + b.id" class="mini-row">
              <span class="mini-name">{{ b.name }}</span>
              <el-tag effect="light" size="small" :type="b.status === 1 ? 'success' : 'info'">{{ b.status_label }}</el-tag>
            </div>
          </div>
          <div v-else class="guide-card compact">
            <el-icon :size="26"><DataAnalysis /></el-icon>
            <div class="guide-title">还没有报表</div>
            <div class="guide-desc">创建报表模板或 BI 大屏后，这里展示生成情况。</div>
            <el-button type="primary" plain size="small" @click="go('/rp/template')">去创建</el-button>
          </div>
        </el-card>
      </el-col>

      <!-- 知识库 -->
      <el-col :xs="24" :md="8">
        <el-card shadow="never" class="panel">
          <template #header>
            <div class="panel-header">
              <div class="panel-title">
                <span class="panel-dot dot-green"></span>
                <span>知识库</span>
              </div>
              <el-button link type="primary" @click="go('/kb/document')">文档管理</el-button>
            </div>
          </template>
          <div class="stat-pairs">
            <div class="pair">
              <div class="pair-value">{{ rich.kb.docs ?? 0 }}</div>
              <div class="pair-label">文档总数</div>
            </div>
            <div class="pair">
              <div class="pair-value">{{ rich.kb.categories ?? 0 }}</div>
              <div class="pair-label">分类数</div>
            </div>
          </div>
          <!-- 热门文档：按阅读量排序 -->
          <div v-if="rich.kb.hot?.length" class="mini-list">
            <div class="sub-title">热门文档</div>
            <div v-for="(d, i) in rich.kb.hot" :key="'kb-' + i" class="mini-row" @click="go('/kb/document')">
              <el-icon :size="14" class="mini-icon"><Reading /></el-icon>
              <span class="mini-name">{{ d.title }}</span>
              <span class="mini-time">{{ d.read_count }} 次</span>
            </div>
          </div>
          <div v-else class="guide-card compact">
            <el-icon :size="26"><Reading /></el-icon>
            <div class="guide-title">知识库还是空的</div>
            <div class="guide-desc">沉淀运维手册、常见问题，团队可快速检索。</div>
            <el-button type="primary" plain size="small" @click="go('/kb/document')">去新建文档</el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- ---------- 第五行：今日日程 + 用户组织 ---------- -->
    <el-row :gutter="16" class="grid-row">
      <!-- 今日日程 -->
      <el-col :xs="24" :md="8">
        <el-card shadow="never" class="panel">
          <template #header>
            <div class="panel-header">
              <div class="panel-title">
                <span class="panel-dot dot-orange"></span>
                <span>今日日程</span>
                <el-tag effect="light" size="small" type="info" class="panel-count">{{ rich.cal.today ?? 0 }} 项</el-tag>
              </div>
              <el-button link type="primary" @click="go('/cal/schedule')">日历</el-button>
            </div>
          </template>
          <div class="list-body cal-body">
            <div v-if="!rich.cal.list?.length" class="guide-card compact">
              <el-icon :size="26"><Calendar /></el-icon>
              <div class="guide-title">今天没有安排</div>
              <div class="guide-desc">创建会议、提醒或全天日程，到点自动提醒。</div>
              <el-button type="primary" plain size="small" @click="go('/cal/schedule')">新建日程</el-button>
            </div>
            <!-- 日程条目：时间范围 + 标题 -->
            <template v-else>
              <div v-for="c in rich.cal.list" :key="'cal-' + c.id" class="list-item" @click="go('/cal/schedule')">
                <div class="li-main">
                  <div class="li-title">{{ c.title }}</div>
                  <div class="li-desc">{{ c.all_day ? '全天' : `${c.start} - ${c.end}` }}</div>
                </div>
                <el-tag effect="light" size="small" type="warning">日程</el-tag>
              </div>
            </template>
          </div>
          <!-- 未来 7 天日程：补足今日只有一条时的空白，同时提供近期安排预览 -->
          <div v-if="rich.cal.week?.length" class="week-list">
            <div class="sub-title">未来 7 天</div>
            <div v-for="c in rich.cal.week" :key="'calw-' + c.id" class="mini-row" @click="go('/cal/schedule')">
              <span class="week-date">{{ c.date }}</span>
              <span class="mini-name">{{ c.title }}</span>
              <span class="mini-time">{{ c.all_day ? '全天' : c.start }}</span>
            </div>
          </div>
          <!-- 日程底部：说明 + 新建入口，填充卡片底部并给出下一步动作 -->
          <div class="cal-foot">
            <span>日程到点会通过站内消息提醒</span>
            <el-button link type="primary" @click="go('/cal/schedule')">新建日程 →</el-button>
          </div>
        </el-card>
      </el-col>

      <!-- 用户与组织 -->
      <el-col :xs="24" :md="8">
        <el-card shadow="never" class="panel">
          <template #header>
            <div class="panel-header">
              <div class="panel-title">
                <span class="panel-dot dot-purple"></span>
                <span>用户与组织</span>
              </div>
              <el-button link type="primary" @click="go('/system/user')">用户管理</el-button>
            </div>
          </template>
          <div class="stat-pairs four">
            <div class="pair">
              <div class="pair-value">{{ rich.users.total ?? 0 }}</div>
              <div class="pair-label">用户总数</div>
            </div>
            <div class="pair">
              <div class="pair-value">{{ rich.users.today ?? 0 }}</div>
              <div class="pair-label">今日新增</div>
            </div>
            <div class="pair">
              <div class="pair-value">{{ rich.users.roles ?? 0 }}</div>
              <div class="pair-label">角色数</div>
            </div>
            <div class="pair">
              <div class="pair-value">{{ rich.users.tenants ?? 0 }}</div>
              <div class="pair-label">租户数</div>
            </div>
          </div>
          <!-- 部门人员分布：真实统计，无数据时引导创建部门 -->
          <div v-if="rich.users.by_dept?.length" class="dist-wrap">
            <div class="sub-title">部门人员分布</div>
            <DistributionBar :items="deptItems" />
          </div>
          <div v-else class="guide-card compact">
            <el-icon :size="26"><OfficeBuilding /></el-icon>
            <div class="guide-title">尚未配置组织架构</div>
            <div class="guide-desc">创建部门并分配用户后，可在此查看人员分布。</div>
            <el-button type="primary" plain size="small" @click="go('/system/dept')">去配置</el-button>
          </div>
        </el-card>
      </el-col>

      <!-- 数据质量 / 运维提示：用真实统计组合的提示卡，避免该行出现空洞 -->
      <el-col :xs="24" :md="8">
        <el-card shadow="never" class="panel">
          <template #header>
            <div class="panel-header">
              <div class="panel-title">
                <span class="panel-dot dot-blue"></span>
                <span>运维速览</span>
              </div>
              <!-- 手动刷新：不新增定时器，点击后重新拉取聚合数据 -->
              <el-button link type="primary" @click="loadAll">
                <el-icon :size="14"><Refresh /></el-icon> 刷新
              </el-button>
            </div>
          </template>
          <div class="quick-facts">
            <!-- 系统状态：复用监控接口，填满卡片同时给运维提供即时判断依据 -->
            <div class="fact-row">
              <span class="fact-key">数据库连接</span>
              <span class="fact-value" :class="monitor.db_status === 'ok' ? 'ok' : 'bad'">{{ monitor.db_status === 'ok' ? '正常' : '异常' }}</span>
            </div>
            <div class="fact-row">
              <span class="fact-key">磁盘占用</span>
              <span class="fact-value">{{ monitor.disk_percent ?? 0 }}%</span>
            </div>
            <div class="fact-row">
              <span class="fact-key">内存占用</span>
              <span class="fact-value">{{ monitor.mem_percent ?? 0 }}%</span>
            </div>
            <div class="fact-row">
              <span class="fact-key">告警处理率</span>
              <span class="fact-value">{{ alarmHandleRate }}%</span>
            </div>
            <div class="fact-row">
              <span class="fact-key">定时任务启用率</span>
              <span class="fact-value">{{ taskEnableRate }}%</span>
            </div>
            <div class="fact-row">
              <span class="fact-key">报表生成成功率</span>
              <span class="fact-value">{{ reportSuccessRate }}%</span>
            </div>
            <div class="fact-row">
              <span class="fact-key">BI 发布率</span>
              <span class="fact-value">{{ biPublishRate }}%</span>
            </div>
            <div class="fact-tip">
              所有比例均由上方真实模块数据实时计算；数据截至 {{ rich.generated_at || '—' }}。
            </div>
            <div class="fact-actions">
              <el-button type="primary" plain size="small" @click="go('/system/operlog')">操作日志</el-button>
              <el-button plain size="small" @click="go('/system/loginlog')">登录日志</el-button>
              <el-button plain size="small" @click="go('/system/record')">数据备份</el-button>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- ---------- 第六行：常用功能（按模块分组） ---------- -->
    <el-row :gutter="16" class="grid-row last-row">
      <el-col :xs="24" :md="24">
        <el-card shadow="never" class="panel">
          <template #header>
            <div class="panel-header">
              <div class="panel-title">
                <span class="panel-dot dot-orange"></span>
                <span>常用功能</span>
                <el-tag effect="light" size="small" type="info" class="panel-count">按模块分组</el-tag>
              </div>
              <span class="panel-extra">共 {{ commonCount }} 个入口</span>
            </div>
          </template>
          <div class="common-groups">
            <!-- 四个模块分组，每组 4 个高频入口 -->
            <div v-for="group in commonGroups" :key="group.title" class="common-group">
              <div class="group-title">{{ group.title }}</div>
              <div class="group-items">
                <div v-for="item in group.items" :key="item.title" class="group-item" @click="go(item.path)">
                  <div class="gi-icon" :style="{ background: item.bg }">
                    <el-icon :size="16"><component :is="item.icon" /></el-icon>
                  </div>
                  <span class="gi-title">{{ item.title }}</span>
                </div>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 底部数据说明：明确数据来源与刷新方式，避免用户误以为实时推送 -->
    <div class="dashboard-foot">
      <span>数据来源：各业务模块实时聚合 · 更新于 {{ rich.generated_at || '—' }}</span>
      <el-button link type="primary" @click="loadAll">
        <el-icon :size="14"><Refresh /></el-icon> 重新加载
      </el-button>
    </div>
  </div>
</template>

<script setup>
// ============================================================
// 脚本：首页数据加载与展示计算。
// 数据流：/home/rich/（主）+ /home/overview/（兜底）+ /home/monitor/ → rich/monitor
//        → 计算属性 → 模板。
// 副作用：仅并发请求与 loading 状态切换；失败时静默降级为空数据。
// ============================================================
// Vue 基础 API：ref 存加载状态，reactive 存聚合数据，computed 派生展示数据
import { ref, reactive, computed, onMounted, onBeforeUnmount } from 'vue'
// 路由：所有入口卡片通过 go() 做编程式跳转
import { useRouter } from 'vue-router'
// 全局登录态：取当前用户的昵称/用户名/头像
import { auth } from '@/store/auth'
// 统一请求封装：已处理 baseURL、token 与错误提示
import request from '@/utils/request'
// 本地 SVG 图表组件：折线图与分布条，均无第三方依赖
import TrendChart from '@/components/dashboard/TrendChart.vue'
import DistributionBar from '@/components/dashboard/DistributionBar.vue'
// Element Plus 图标：按需引入，只打包本页实际使用的图标
import {
  UserFilled, Document, TrendCharts, Calendar, Bell, Files, Tickets,
  Monitor, FolderOpened, MagicStick, DataAnalysis, Setting, Clock,
  Cpu, Refresh, Connection, Stopwatch, WarningFilled, Reading, OfficeBuilding
} from '@element-plus/icons-vue'

// 路由实例：供 go() 使用
const router = useRouter()

// 显示名：昵称优先，其次用户名，最后兜底“用户”
const displayName = computed(() => auth.user.nickname || auth.user.username || '用户')

// 问候语：按本地小时划分时段，纯前端计算
const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 6) return '凌晨好'
  if (h < 9) return '早上好'
  if (h < 12) return '上午好'
  if (h < 14) return '中午好'
  if (h < 18) return '下午好'
  return '晚上好'
})

// 当天日期文本：YYYY-MM-DD 星期X
const todayText = computed(() => {
  const d = new Date()
  const weekdays = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六']
  const pad = n => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${weekdays[d.getDay()]}`
})

// 聚合数据容器：给所有块设置安全默认值，接口失败时模板也不会报错
const rich = reactive({
  generated_at: '',                                                    // 数据生成时间
  stats: { todos: 0, messages: 0, workflows: 0, new_users: 0, todo_delta: 0, message_delta: 0, workflow_delta: 0, user_delta: 0, file_count: 0, file_size: 0, wo_open: 0, alarm_open: 0 },
  trends: { dates: [], wo: [], wf: [], msg: [], file: [], user: [] },  // 7 日趋势
  todos: [],                                                           // 待办
  notices: [],                                                         // 公告
  messages: [],                                                        // 消息
  workflows: [],                                                       // 流程实例
  files: { count: 0, size: 0, by_ext: [] },                            // 文件
  tasks: { total: 0, enabled: 0, recent: [] },                         // 定时任务
  alarms: { total: 0, open: 0, by_level: [], recent: [] },             // 告警
  users: { total: 0, today: 0, by_dept: [], roles: 0, tenants: 0 },     // 用户
  reports: { templates: 0, generated: 0, recent: [] },                 // 报表
  bi: { total: 0, published: 0, list: [] },                            // BI
  kb: { docs: 0, categories: 0, hot: [] },                             // 知识库
  cal: { today: 0, list: [], week: [] }                                // 日程
})

// 监控数据容器：与既有 /home/monitor/ 字段保持一致
const monitor = reactive({
  db_status: 'ok',                                                     // 数据库状态
  server_time: '',                                                     // 服务器时间
  db: {},                                                              // 数据库详情
  disk_used: 0,                                                        // 磁盘已用 GB
  disk_total: 0,                                                       // 磁盘总量 GB
  disk_percent: 0,                                                     // 磁盘占用百分比
  mem_percent: null,                                                   // 内存占用百分比
  uptime: ''                                                           // 运行时长文本
})

// 加载状态：聚合数据与监控各自独立的遮罩
const loading = ref(false)
const monitorLoading = ref(false)

// 快捷入口配置：4 个高频操作，图标底色使用主题图表色渐变
const quickEntries = [
  { title: '新建用户', icon: UserFilled, path: '/system/user', bg: 'linear-gradient(135deg, var(--chart-1), color-mix(in srgb, var(--chart-1) 72%, var(--app-surface)))' },
  { title: '新建菜单', icon: Setting, path: '/system/menu', bg: 'linear-gradient(135deg, var(--chart-5), color-mix(in srgb, var(--chart-5) 72%, var(--app-surface)))' },
  { title: '任务调度', icon: Calendar, path: '/task', bg: 'linear-gradient(135deg, var(--chart-3), color-mix(in srgb, var(--chart-3) 72%, var(--app-surface)))' },
  { title: '数据备份', icon: Files, path: '/system/record', bg: 'linear-gradient(135deg, var(--chart-4), color-mix(in srgb, var(--chart-4) 72%, var(--app-surface)))' }
]

// 常用功能分组：按模块组织，避免入口堆成没有语义的九宫格
const commonGroups = [
  {
    title: '系统管理',
    items: [
      { title: '用户管理', icon: UserFilled, path: '/system/user', bg: 'linear-gradient(135deg, var(--chart-1), color-mix(in srgb, var(--chart-1) 72%, var(--app-surface)))' },
      { title: '角色权限', icon: Bell, path: '/system/role', bg: 'linear-gradient(135deg, var(--chart-4), color-mix(in srgb, var(--chart-4) 72%, var(--app-surface)))' },
      { title: '菜单配置', icon: Setting, path: '/system/menu', bg: 'linear-gradient(135deg, var(--chart-5), color-mix(in srgb, var(--chart-5) 72%, var(--app-surface)))' },
      { title: '数据字典', icon: MagicStick, path: '/system/dict', bg: 'linear-gradient(135deg, var(--chart-2), color-mix(in srgb, var(--chart-2) 72%, var(--app-surface)))' }
    ]
  },
  {
    title: '业务协作',
    items: [
      { title: '工单处理', icon: Tickets, path: '/wo/order', bg: 'linear-gradient(135deg, var(--chart-3), color-mix(in srgb, var(--chart-3) 72%, var(--app-surface)))' },
      { title: '流程待办', icon: Connection, path: '/workflow/todo', bg: 'linear-gradient(135deg, var(--chart-1), color-mix(in srgb, var(--chart-1) 72%, var(--app-surface)))' },
      { title: '日程安排', icon: Calendar, path: '/cal/schedule', bg: 'linear-gradient(135deg, var(--chart-5), color-mix(in srgb, var(--chart-5) 72%, var(--app-surface)))' },
      { title: '公告通知', icon: Document, path: '/notice/info', bg: 'linear-gradient(135deg, var(--chart-2), color-mix(in srgb, var(--chart-2) 72%, var(--app-surface)))' }
    ]
  },
  {
    title: '数据可视化',
    items: [
      { title: '报表模板', icon: DataAnalysis, path: '/rp/template', bg: 'linear-gradient(135deg, var(--chart-2), color-mix(in srgb, var(--chart-2) 72%, var(--app-surface)))' },
      { title: 'BI 大屏', icon: Monitor, path: '/bi', bg: 'linear-gradient(135deg, var(--chart-4), color-mix(in srgb, var(--chart-4) 72%, var(--app-surface)))' },
      { title: '文件管理', icon: FolderOpened, path: '/file', bg: 'linear-gradient(135deg, var(--chart-1), color-mix(in srgb, var(--chart-1) 72%, var(--app-surface)))' },
      { title: '消息中心', icon: Bell, path: '/msg/record', bg: 'linear-gradient(135deg, var(--chart-5), color-mix(in srgb, var(--chart-5) 72%, var(--app-surface)))' }
    ]
  },
  {
    title: '平台运维',
    items: [
      { title: '定时任务', icon: Stopwatch, path: '/task', bg: 'linear-gradient(135deg, var(--chart-3), color-mix(in srgb, var(--chart-3) 72%, var(--app-surface)))' },
      { title: '操作日志', icon: Clock, path: '/system/operlog', bg: 'linear-gradient(135deg, var(--chart-6), color-mix(in srgb, var(--chart-6) 72%, var(--app-surface)))' },
      { title: '登录日志', icon: Document, path: '/system/loginlog', bg: 'linear-gradient(135deg, var(--chart-2), color-mix(in srgb, var(--chart-2) 72%, var(--app-surface)))' },
      { title: '数据备份', icon: Files, path: '/system/record', bg: 'linear-gradient(135deg, var(--chart-4), color-mix(in srgb, var(--chart-4) 72%, var(--app-surface)))' }
    ]
  }
]

// 常用功能入口总数：显示在面板右上角
const commonCount = computed(() => commonGroups.reduce((sum, g) => sum + g.items.length, 0))

// 指标卡：数值取自 rich.stats，迷你折线取自 trends，实现“真实趋势”
const statCards = computed(() => [
  {
    key: 'todos',
    label: '待办事项',
    icon: Tickets,
    color: 'blue',
    bg: 'linear-gradient(135deg, var(--chart-1), color-mix(in srgb, var(--chart-1) 72%, var(--app-surface)))',
    tip: '流程 + 工单',
    value: rich.stats.todos ?? 0,
    delta: rich.stats.todo_delta ?? 0,
    values: rich.trends.wo
  },
  {
    key: 'messages',
    label: '未读消息',
    icon: Bell,
    color: 'purple',
    bg: 'linear-gradient(135deg, var(--chart-4), color-mix(in srgb, var(--chart-4) 72%, var(--app-surface)))',
    tip: '站内未读',
    value: rich.stats.messages ?? 0,
    delta: rich.stats.message_delta ?? 0,
    values: rich.trends.msg
  },
  {
    key: 'workflows',
    label: '运行中流程',
    icon: TrendCharts,
    color: 'green',
    bg: 'linear-gradient(135deg, var(--chart-5), color-mix(in srgb, var(--chart-5) 72%, var(--app-surface)))',
    tip: '流程实例',
    value: rich.stats.workflows ?? 0,
    delta: rich.stats.workflow_delta ?? 0,
    values: rich.trends.wf
  },
  {
    key: 'new_users',
    label: '今日新增用户',
    icon: UserFilled,
    color: 'orange',
    bg: 'linear-gradient(135deg, var(--chart-3), color-mix(in srgb, var(--chart-3) 72%, var(--app-surface)))',
    tip: '注册用户',
    value: rich.stats.new_users ?? 0,
    delta: rich.stats.user_delta ?? 0,
    values: rich.trends.user
  }
])

// 趋势图一：工单 + 流程
const bizSeries = computed(() => [
  { name: '工单', color: 'var(--chart-3)', values: rich.trends.wo || [] },
  { name: '流程', color: 'var(--chart-1)', values: rich.trends.wf || [] }
])
// 趋势图二：消息 + 文件
const docSeries = computed(() => [
  { name: '消息', color: 'var(--chart-4)', values: rich.trends.msg || [] },
  { name: '文件', color: 'var(--chart-5)', values: rich.trends.file || [] }
])

// 文件类型分布：颜色由分布条按索引轮转，无需额外指定
const fileExtItems = computed(() => (rich.files.by_ext || []).map(it => ({
  label: '.' + it.ext,          // 显示为 .txt / .json
  count: it.count
})))

// 告警级别分布：按级别使用状态色，保证严重级别一眼可辨
const alarmItems = computed(() => (rich.alarms.by_level || []).map(it => ({
  label: it.label,
  count: it.count,
  color: it.level === 3 ? 'var(--app-danger)' : it.level === 2 ? 'var(--app-warning)' : 'var(--brand-primary)'
})))

// 部门人员分布：颜色轮转
const deptItems = computed(() => (rich.users.by_dept || []).map(it => ({
  label: it.name,
  count: it.count
})))

// 告警处理率：已处理 / 总数，无数据时显示 100，避免出现 NaN
const alarmHandleRate = computed(() => {
  const total = Number(rich.alarms.total) || 0
  const open = Number(rich.alarms.open) || 0
  return total ? Math.round(((total - open) / total) * 100) : 100
})

// 定时任务启用率
const taskEnableRate = computed(() => {
  const total = Number(rich.tasks.total) || 0
  const enabled = Number(rich.tasks.enabled) || 0
  return total ? Math.round((enabled / total) * 100) : 0
})

// 报表生成成功率：最近记录中成功的比例（无记录时按 100 处理，避免误导）
const reportSuccessRate = computed(() => {
  const list = rich.reports.recent || []
  if (!list.length) return 100
  return Math.round((list.filter(r => r.status === 1).length / list.length) * 100)
})

// BI 发布率
const biPublishRate = computed(() => {
  const total = Number(rich.bi.total) || 0
  const published = Number(rich.bi.published) || 0
  return total ? Math.round((published / total) * 100) : 0
})

// 磁盘进度条颜色：>80 危险、>60 警告、其余成功，全部走主题令牌
const diskColor = computed(() => {
  const p = monitor.disk_percent || 0
  if (p > 80) return 'var(--app-danger)'
  if (p > 60) return 'var(--app-warning)'
  return 'var(--app-success)'
})

// 内存进度条颜色：阈值与磁盘一致
const memColor = computed(() => {
  const p = monitor.mem_percent || 0
  if (p > 85) return 'var(--app-danger)'
  if (p > 65) return 'var(--app-warning)'
  return 'var(--brand-primary)'
})

// 把字节数格式化为人类可读的单位
function formatBytes(bytes) {
  const n = Number(bytes) || 0
  if (n < 1024) return n + ' B'
  const units = ['KB', 'MB', 'GB', 'TB']
  let value = n / 1024
  let i = 0
  while (value >= 1024 && i < units.length - 1) {
    value /= 1024
    i += 1
  }
  return value.toFixed(value >= 100 ? 0 : 1) + ' ' + units[i]
}

// 迷你折线坐标：把 7 个真实数值映射到 84x28 的坐标系
function sparkPoints(values) {
  const arr = values && values.length ? values : [0]
  const max = Math.max(1, ...arr.map(v => Number(v) || 0))
  const w = 84
  const h = 28
  const step = arr.length > 1 ? w / (arr.length - 1) : 0
  return arr.map((v, i) => {
    const x = Math.round(step * i)
    const y = Math.round(h - (Number(v) || 0) / max * (h - 4) - 2)
    return `${x},${y}`
  }).join(' ')
}

// 环比文案：正数加 +，负数保留 -，0 显示“持平”
function deltaText(delta) {
  const n = Number(delta) || 0
  if (n === 0) return '较昨日持平'
  return `较昨日 ${n > 0 ? '+' : ''}${n}`
}

// 环比颜色：上涨用成功色，下降用危险色，持中用弱化色
function deltaClass(delta) {
  const n = Number(delta) || 0
  if (n > 0) return 'trend-up'
  if (n < 0) return 'trend-down'
  return 'trend-flat'
}

// 待办类型 → 徽标样式类
function typeClass(source) {
  if (source === 'workflow') return 'type-workflow'
  if (source === 'work_order') return 'type-wo'
  return 'type-cal'
}

// 流程状态 → Element Plus 标签类型
function wfTagType(status) {
  if (status === 0) return 'warning'
  if (status === 1) return 'success'
  if (status === 2) return 'danger'
  return 'info'
}

// 任务执行状态 → 标签类型（0 运行中、1 成功、2 失败）
function taskTagType(status) {
  if (status === 1) return 'success'
  if (status === 2) return 'danger'
  return 'warning'
}

// 报表生成状态 → 标签类型（0 生成中、1 成功、2 失败）
function genTagType(status) {
  if (status === 1) return 'success'
  if (status === 2) return 'danger'
  return 'warning'
}

// 统一跳转：吞掉重复导航/目标不存在导致的 Promise 异常，避免控制台报错
function go(path) {
  if (!path) return
  router.push(path).catch(() => {})
}

// 待办行点击：有 path 才跳转
function handleTodoClick(item) {
  if (item && item.path) go(item.path)
}

// 拉取增强聚合数据；失败时回退到旧版 overview，保证页面可用
async function loadRich() {
  loading.value = true
  try {
    const res = await request.get('/home/rich/')
    const data = res.data || {}
    // 逐块安全合并，避免接口少字段时覆盖默认值
    rich.generated_at = data.generated_at || ''
    rich.stats = { ...rich.stats, ...(data.stats || {}) }
    rich.trends = { ...rich.trends, ...(data.trends || {}) }
    rich.todos = data.todos || []
    rich.notices = data.notices || []
    rich.messages = data.messages || []
    rich.workflows = data.workflows || []
    rich.files = { ...rich.files, ...(data.files || {}) }
    rich.tasks = { ...rich.tasks, ...(data.tasks || {}) }
    rich.alarms = { ...rich.alarms, ...(data.alarms || {}) }
    rich.users = { ...rich.users, ...(data.users || {}) }
    rich.reports = { ...rich.reports, ...(data.reports || {}) }
    rich.bi = { ...rich.bi, ...(data.bi || {}) }
    rich.kb = { ...rich.kb, ...(data.kb || {}) }
    rich.cal = { ...rich.cal, ...(data.cal || {}) }
  } catch (e) {
    // 兜底：旧接口至少能提供统计、待办与动态（通常发生在后端未升级时）
    try {
      const res = await request.get('/home/overview/')
      const data = res.data || {}
      rich.stats = { ...rich.stats, ...(data.stats || {}) }
      rich.todos = data.todos || []
      rich.generated_at = data.current_datetime || ''
    } catch (err) { /* 两个接口都失败时保持骨架与引导卡 */ }
  } finally {
    loading.value = false
  }
}

// 拉取系统监控：独立接口，失败时保留默认值
async function loadMonitor() {
  monitorLoading.value = true
  try {
    const res = await request.get('/home/monitor/')
    if (res.data) Object.assign(monitor, res.data)
  } catch (e) { /* 监控失败不影响首页其他内容 */ }
  finally {
    monitorLoading.value = false
  }
}

// 统一刷新：两个接口并行请求，缩短等待时间
function loadAll() {
  loadRich()
  loadMonitor()
}

// ---------- 趋势图高度自适应 ----------
// 业务趋势卡与「待办」卡同行等高，而待办条数会随数据变化（最多 8 条可至 700px+）。
// 旧写法把两张图固定为 172px，卡片被拉伸出来的高度会全部变成底部空洞；
// 这里用 ResizeObserver 量出图表堆叠区的真实高度，再平摊给两张图，从根上消除留白。
const trendStackRef = ref(null)        // 折线图堆叠容器（模板上的 ref）
const trendChartHeight = ref(172)      // 单张图整体高度（图例 + 绘图区），传给 TrendChart
let trendObserver = null               // 观察器实例，组件卸载时必须断开

function syncTrendHeight() {
  const stack = trendStackRef.value
  if (!stack) return
  // 每块占 (总高 - 10px 间距) 的一半，再扣掉 16px 的小标题高度
  const raw = (stack.clientHeight - 10) / 2 - 16
  // 下限 140 保证 1280 下网格线仍可读，上限 300 防止超宽屏把图表拉得过分细长
  const next = Math.round(Math.min(300, Math.max(140, raw)))
  // 容差 1px：避免卡片由内容撑高时出现 ±1px 的反复测量抖动
  if (Math.abs(next - trendChartHeight.value) <= 1) return
  trendChartHeight.value = next
}

// 首次进入时加载数据，同时开始观察图表容器高度
onMounted(() => {
  loadAll()
  // 容器不存在时跳过（例如路由异常导致页面未完整渲染）
  if (trendStackRef.value) {
    trendObserver = new ResizeObserver(syncTrendHeight)
    trendObserver.observe(trendStackRef.value)
    // 立即同步一次，避免首帧仍使用 172 的默认值
    syncTrendHeight()
  }
})

// 页面卸载时断开观察器，避免残留回调造成内存泄漏
onBeforeUnmount(() => {
  if (trendObserver) trendObserver.disconnect()
  trendObserver = null
})
</script>

<style scoped>
/* ============================================================
   样式说明：scoped 仅作用于本页。
   颜色来源：--app-*（面板/文字/状态色）、--brand-*（品牌色）、
   --chart-*（图表色）。除 Banner 品牌渐变上的反白色外不写死颜色。
   布局修复：.panel 补 width:100% + min-width:0，栅格列 display:flex，
   从根上消除 flex 子项收缩导致的横向空洞。
   ============================================================ */
/* 页面根容器：底部留白，避免最后一行贴边 */
.dashboard-wrap {
  padding-bottom: 16px;
}

/* ============ 顶部 Banner ============ */
/* Banner：品牌渐变 + 大圆角 + 品牌光晕；overflow 裁掉装饰圆 */
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
  /* 品牌渐变上的反白色：与主题无关，保证渐变背景上的可读性 */
  color: #fff;
}

/* 装饰圆基础样式：低透明白，制造光斑层次（同上，属于品牌背景的一部分） */
.hero-decor {
  position: absolute;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.1);
}
.hero-decor-1 { top: -60px; right: 10%; width: 200px; height: 200px; }
.hero-decor-2 { bottom: -90px; right: 28%; width: 180px; height: 180px; background: rgba(255, 255, 255, 0.07); }
.hero-decor-3 { top: 30px; right: -30px; width: 120px; height: 120px; background: rgba(255, 255, 255, 0.12); }

/* 欢迎区：抬高层级，避免被装饰圆遮挡 */
.hero-left {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 18px;
  min-width: 0;
}

/* 头像：白底 + 品牌色文字，在渐变背景上更醒目 */
.hero-avatar {
  color: var(--brand-primary);
  background: #fff;
  font-size: 22px;
  font-weight: 700;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.18);
  border: 3px solid rgba(255, 255, 255, 0.6);
  flex-shrink: 0;
}

/* 问候语：22px 加粗 */
.hero-greeting {
  font-size: 22px;
  font-weight: 600;
  letter-spacing: 0.5px;
}

/* 副标题：半透明白，弱化层级 */
.hero-sub {
  margin-top: 8px;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.85);
}

/* 数据更新时间：略提高不透明度，与说明文字区分 */
.hero-updated {
  margin-left: 6px;
  color: rgba(255, 255, 255, 0.95);
  font-variant-numeric: tabular-nums;
}

/* 快捷入口容器 */
.hero-right {
  position: relative;
  z-index: 1;
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

/* 快捷入口：毛玻璃块，hover 上浮 */
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

/* ============ 栅格与面板（本次布局修复重点） ============ */
/* 每个栅格列都成为 flex 容器，内部面板才能用 height:100% 实现同行等高 */
.stat-row > .el-col,
.grid-row > .el-col {
  display: flex;
}
/* 行间距：最后一行不留间距，避免页尾空洞 */
.grid-row { margin-bottom: 18px; }
.stat-row { margin-bottom: 18px; }
.last-row { margin-bottom: 0; }

/* 面板：width:100% 是关键修复——之前 flex 子项按内容收缩，导致卡片只占列宽的一部分，
   右侧出现大片横向空洞；min-width:0 防止长文本撑破栅格 */
.panel {
  width: 100%;
  min-width: 0;
  border-radius: var(--app-radius-lg);
  border: 1px solid var(--app-border-light);
  display: flex;
  flex-direction: column;
  height: 100%;
}
/* 卡片头：统一内边距与分隔线 */
.panel :deep(.el-card__header) { padding: 13px 18px; border-bottom: 1px solid var(--app-border-light); }
/* 卡片主体：占满剩余高度并纵向排列，内容少的卡片用 space-between 填充 */
.panel :deep(.el-card__body) { padding: 16px 18px; flex: 1; display: flex; flex-direction: column; }

/* 面板标题栏：左右两端对齐 */
.panel-header { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
/* 标题组合 */
.panel-title { display: flex; align-items: center; gap: 8px; font-size: 15px; font-weight: 600; color: var(--app-text-1); min-width: 0; }
/* 标题左侧色条 */
.panel-dot { width: 4px; height: 16px; border-radius: 3px; flex-shrink: 0; }
.dot-blue { background: var(--chart-1); }
.dot-purple { background: var(--chart-4); }
.dot-green { background: var(--chart-5); }
.dot-orange { background: var(--chart-3); }
.dot-red { background: var(--app-danger); }
/* 计数标签：与标题紧贴 */
.panel-count { margin-left: 2px; }
/* 右上角说明文字 */
.panel-extra { font-size: 12px; color: var(--app-text-3); flex-shrink: 0; }

/* ============ 统计卡 ============ */
/* 统计卡：面板底色 + 主题圆角 + 轻阴影；overflow 裁掉折线溢出 */
.stat-card {
  position: relative;
  display: flex;
  align-items: center;
  gap: 14px;
  width: 100%;
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
/* 图标底板：52x52 圆角方块，白字 */
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
/* 文字区：占满剩余宽度，允许压缩 */
.stat-info { flex: 1; min-width: 0; }
/* 主数值 */
.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--app-text-1);
  line-height: 1.1;
  font-variant-numeric: tabular-nums;
}
/* 指标名 */
.stat-label { margin-top: 4px; font-size: 13px; color: var(--app-text-3); }
/* 环比行 */
.stat-trend { display: flex; align-items: center; gap: 6px; margin-top: 6px; font-size: 12px; }
/* 上涨：成功色 */
.trend-up { color: var(--app-success); font-weight: 600; }
/* 下降：危险色 */
.trend-down { color: var(--app-danger); font-weight: 600; }
/* 持平：弱化色 */
.trend-flat { color: var(--app-text-3); }
/* 说明文字 */
.trend-tip { color: var(--app-text-3); }
/* 迷你折线：右下角，半透明不干扰读数 */
.stat-spark { position: absolute; right: 12px; bottom: 12px; opacity: 0.55; width: 84px; height: 28px; }
/* 四种卡片主题色：只影响折线（polyline 用 currentColor） */
.stat-blue .stat-spark { color: var(--chart-1); }
.stat-purple .stat-spark { color: var(--chart-4); }
.stat-green .stat-spark { color: var(--chart-5); }
.stat-orange .stat-spark { color: var(--chart-3); }

/* ============ 趋势面板 ============ */
/* 两张图纵向排列，间距 10px */
.trend-stack { display: flex; flex-direction: column; gap: 10px; flex: 1; }
/* 单张图区块 */
.trend-block { min-width: 0; }
/* 图表小标题：色点 + 文案 */
.block-caption { display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--app-text-3); margin-bottom: 2px; }
.caption-dot { width: 6px; height: 6px; border-radius: 50%; }
/* 底部速览：三项指标横向铺满，填满卡片底部 */
.trend-foot {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px dashed var(--app-border-light);
}
/* 单个指标：数值 + 名称 */
.foot-metric { display: flex; flex-direction: column; align-items: center; gap: 2px; }
.fm-value { font-size: 18px; font-weight: 700; color: var(--app-text-1); font-variant-numeric: tabular-nums; }
.fm-label { font-size: 11px; color: var(--app-text-3); }

/* ============ 通用列表 ============ */
/* 列表容器：占满卡片剩余高度，内容多时可滚动 */
.list-body { flex: 1; min-height: 0; overflow: auto; }
/* 列表条目：左右布局，hover 高亮 */
.list-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 12px;
  margin-bottom: 8px;
  background: var(--app-surface-2);
  border-radius: var(--app-radius-md);
  cursor: pointer;
  transition: background 0.15s, transform 0.15s;
}
.list-item:hover { background: var(--brand-primary-soft); transform: translateX(2px); }
/* 左侧内容区：允许压缩 */
.li-main { flex: 1; min-width: 0; }
/* 标题：单行省略 */
.li-title { font-size: 13px; font-weight: 600; color: var(--app-text-1); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
/* 摘要：单行省略 */
.li-desc { margin-top: 3px; font-size: 12px; color: var(--app-text-3); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
/* 右侧状态列 */
.li-side { display: flex; flex-direction: column; align-items: flex-end; gap: 4px; flex-shrink: 0; }
/* 时间：等宽数字 */
.li-time { font-size: 11px; color: var(--app-text-3); white-space: nowrap; font-variant-numeric: tabular-nums; }

/* 待办列表：占满高度 */
.todo-list { flex: 1; min-height: 0; overflow: auto; }
/* 待办条目：与列表条目类似，支持整行点击 */
.todo-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 11px 13px;
  margin-bottom: 9px;
  background: var(--app-surface-2);
  border-radius: var(--app-radius-md);
  cursor: pointer;
  transition: background 0.15s, transform 0.15s;
}
.todo-item:hover { background: var(--brand-primary-soft); transform: translateX(2px); }
/* 待办左侧 */
.todo-left { flex: 1; min-width: 0; }
/* 类型徽标 */
.todo-type {
  display: inline-block;
  padding: 2px 8px;
  border-radius: var(--app-radius-xs);
  font-size: 11px;
  font-weight: 600;
  margin-bottom: 5px;
}
.type-workflow { background: var(--brand-primary-soft); color: var(--brand-primary); }
.type-wo { background: color-mix(in srgb, var(--app-warning) 14%, transparent); color: var(--app-warning); }
.type-cal { background: color-mix(in srgb, var(--app-success) 14%, transparent); color: var(--app-success); }
/* 待办标题 */
.todo-title { font-size: 13px; font-weight: 600; color: var(--app-text-1); margin-bottom: 3px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
/* 元信息 */
.todo-meta { display: flex; gap: 12px; font-size: 11px; color: var(--app-text-3); }

/* 未读圆点：未读为主题色，已读为灰色 */
.unread-dot { display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: var(--brand-primary); margin-right: 4px; vertical-align: middle; }
.unread-dot.is-read { background: var(--app-text-3); opacity: 0.5; }

/* ============ 引导卡（无数据时的占位，不留白） ============ */
.guide-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  flex: 1;
  min-height: 180px;
  padding: 18px;
  text-align: center;
  color: var(--app-text-3);
  background: var(--app-surface-2);
  border-radius: var(--app-radius-md);
}
/* 紧凑版：用于已有部分数据的卡片内 */
.guide-card.compact { min-height: 120px; margin-top: 10px; }
.guide-title { font-size: 13px; font-weight: 600; color: var(--app-text-2); }
.guide-desc { font-size: 12px; line-height: 1.6; max-width: 320px; }

/* ============ 系统监控 ============ */
/* 监控主体：三项仪表纵向均分 */
.monitor-body { flex: 1; display: flex; flex-direction: column; justify-content: space-evenly; gap: 10px; }
/* 单项：标签行 + 进度条 */
.meter { display: flex; flex-direction: column; gap: 6px; }
.meter-row { display: flex; align-items: center; justify-content: space-between; font-size: 12px; }
.meter-label { display: flex; align-items: center; gap: 5px; color: var(--app-text-2); }
.meter-val { color: var(--app-text-3); font-variant-numeric: tabular-nums; }
/* 底部附加信息 */
.meter-foot { display: flex; justify-content: space-between; font-size: 11px; color: var(--app-text-3); padding-top: 8px; border-top: 1px dashed var(--app-border-light); }

/* ============ 数值对 / 迷你列表 ============ */
/* 两个数字横排；四个数字时切换为四列 */
.stat-pairs { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; }
.stat-pairs.four { grid-template-columns: repeat(4, 1fr); }
/* 单个数字块 */
.pair { padding: 10px 12px; background: var(--app-surface-2); border-radius: var(--app-radius-md); text-align: center; min-width: 0; }
.pair-value { font-size: 20px; font-weight: 700; color: var(--app-text-1); font-variant-numeric: tabular-nums; overflow: hidden; text-overflow: ellipsis; }
.pair-label { margin-top: 2px; font-size: 11px; color: var(--app-text-3); }
/* 分布区块：与上方数字留出间距 */
.dist-wrap { margin-top: 12px; }
/* 子标题 */
.sub-title { font-size: 12px; color: var(--app-text-3); margin-bottom: 8px; }
/* 迷你列表：最近执行/告警等 */
.mini-list { margin-top: 10px; }
.mini-row { display: flex; align-items: center; gap: 8px; padding: 6px 0; border-bottom: 1px dashed var(--app-border-light); font-size: 12px; }
.mini-row:last-child { border-bottom: none; }
.mini-name { flex: 1; min-width: 0; color: var(--app-text-2); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.mini-time { color: var(--app-text-3); font-size: 11px; white-space: nowrap; font-variant-numeric: tabular-nums; }
.mini-icon { color: var(--app-text-3); }
/* 告警级别圆点：1 提示 / 2 警告 / 3 严重 */
.alarm-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
.alarm-dot.lv-1 { background: var(--brand-primary); }
.alarm-dot.lv-2 { background: var(--app-warning); }
.alarm-dot.lv-3 { background: var(--app-danger); }

/* ============ 运维速览 ============ */
.quick-facts { flex: 1; display: flex; flex-direction: column; gap: 10px; }
/* 单行比例：名称 + 数值 */
.fact-row { display: flex; align-items: center; justify-content: space-between; padding: 8px 12px; background: var(--app-surface-2); border-radius: var(--app-radius-md); font-size: 12px; }
.fact-key { color: var(--app-text-2); }
.fact-value { font-weight: 700; color: var(--brand-primary); font-variant-numeric: tabular-nums; }
/* 状态值：正常用成功色、异常用危险色，避免只靠数字判断 */
.fact-value.ok { color: var(--app-success); }
.fact-value.bad { color: var(--app-danger); }
/* 日程列表：内容较少时不再强行居中，改为顶部开始，由未来日程块填充剩余空间 */
.cal-body { display: flex; flex-direction: column; justify-content: flex-start; flex: 0 0 auto; }
/* 未来日程块：占满卡片剩余高度，避免今日只有一条时出现大片空白 */
.week-list { flex: 1; min-height: 0; overflow: auto; margin-top: 4px; }
/* 未来日程日期：固定宽度，弱化色 */
.week-date { width: 38px; color: var(--app-text-3); font-size: 11px; flex-shrink: 0; font-variant-numeric: tabular-nums; }
/* 日程底部：说明 + 新建入口，分隔线与卡片主体分开 */
.cal-foot { display: flex; align-items: center; justify-content: space-between; margin-top: 10px; padding-top: 10px; border-top: 1px dashed var(--app-border-light); font-size: 12px; color: var(--app-text-3); }
/* 说明文字 */
.fact-tip { font-size: 11px; line-height: 1.6; color: var(--app-text-3); }
/* 底部按钮组：自动换行 */
.fact-actions { display: flex; flex-wrap: wrap; gap: 8px; margin-top: auto; }

/* ============ 常用功能分组 ============ */
/* 四列分组，1280 下仍能保持一行 */
.common-groups { display: grid; grid-template-columns: repeat(4, 1fr); gap: 18px; }
/* 单个分组：纵向排列 */
.common-group { min-width: 0; }
/* 分组标题：底部细线分隔 */
.group-title { font-size: 12px; font-weight: 600; color: var(--app-text-3); padding-bottom: 8px; margin-bottom: 10px; border-bottom: 1px solid var(--app-border-light); }
/* 入口网格：两列 */
.group-items { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; }
/* 单个入口：图标 + 名称 */
.group-item { display: flex; align-items: center; gap: 8px; padding: 8px; border-radius: var(--app-radius-md); background: var(--app-surface-2); cursor: pointer; transition: background 0.15s, transform 0.15s; min-width: 0; }
.group-item:hover { background: var(--brand-primary-soft); transform: translateY(-1px); }
/* 入口图标：24x24 圆角块，白字 */
.gi-icon { width: 24px; height: 24px; border-radius: 7px; display: flex; align-items: center; justify-content: center; color: #fff; flex-shrink: 0; }
/* 入口名称：单行省略 */
.gi-title { font-size: 12px; color: var(--app-text-2); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* ============ 页脚 ============ */
.dashboard-foot { display: flex; align-items: center; justify-content: space-between; margin-top: 12px; font-size: 12px; color: var(--app-text-3); }

/* ============ 响应式 ============ */
/* 1200px 以下：常用功能降为 2 列，横幅改纵向排列 */
@media (max-width: 1200px) {
  .common-groups { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 768px) {
  .hero-banner { flex-direction: column; align-items: flex-start; padding: 22px; }
  .hero-right { margin-top: 14px; width: 100%; }
  .common-groups { grid-template-columns: 1fr; }
  .stat-pairs.four { grid-template-columns: repeat(2, 1fr); }
  .dashboard-foot { flex-direction: column; align-items: flex-start; gap: 6px; }
}
</style>
