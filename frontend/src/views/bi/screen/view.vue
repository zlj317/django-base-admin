<!--
  文件级说明：
  职责：BI 大屏「预览 / 分享」独立页面——按后端返回的 screen_config（width/height/background/widgets）
        渲染固定设计尺寸的画布，用 scale 等比缩放铺满可视区，并按 refresh_sec 定时静默刷新数据。
  两种入口：/bi/view/:id → 路由 BiScreenView，走 preview 接口（需登录）；
           /bi/screen/share/:token → 路由 BiScreenShare，走 share 接口（凭 token 免登录）。
  依赖：vue-router（route 判断入口、router 返回）、@/utils/request、@/components/chart/SimpleChart.vue。
  被谁使用：大屏管理页的“预览/分享”按钮跳转；分享链接也可直接对外分发。
  说明：本页脱离后台布局，是铺满视口的深色页面，颜色刻意写死（不随浅色主题变化），保证投屏效果一致。
-->
<template>
  <!-- 页面根：fixed 铺满视口；pageRef 供全屏 API 作用在整页（含顶栏），而不是只放大画布区域 -->
  <div class="screen-page" ref="pageRef">
    <!-- 顶栏：左侧返回/名称/状态，右侧时钟、自动刷新提示、手动刷新、全屏切换 -->
    <div class="screen-topbar">
      <div class="tb-left">
        <!-- 返回：分享模式回工作台，预览模式按浏览器历史回退（详见 goBack） -->
        <span class="tb-back" @click="goBack">‹ 返回</span>
        <!-- 大屏名称：数据未到达前显示兜底文案，避免顶栏出现空白 -->
        <span class="tb-name">{{ viewData.screen_name || '大屏预览' }}</span>
        <!-- 状态标记：草稿（黄）与已下线（灰）；已发布（status=1）不额外提示，保持顶栏干净 -->
        <el-tag v-if="viewData.status === 0" size="small" effect="dark" type="warning">草稿</el-tag>
        <el-tag v-else-if="viewData.status === 2" size="small" effect="dark" type="info">已下线</el-tag>
      </div>
      <div class="tb-right">
        <!-- 实时时钟：由 updateClock 每秒刷新，投屏时提供时间参照 -->
        <span class="tb-clock">{{ clock }}</span>
        <!-- 自动刷新提示：仅在配置了 refresh_sec（>0）时显示，让观看者知道数据会周期性更新 -->
        <span v-if="refreshSec" class="tb-refresh">自动刷新 {{ refreshSec }}s</span>
        <!-- 手动刷新：传 false 表示静默刷新，不弹 loading 遮罩，避免打断观看 -->
        <span class="tb-btn" @click="loadData(false)">刷新数据</span>
        <!-- 全屏切换：文案随 isFullscreen 变化；实际调用浏览器 Fullscreen API -->
        <span class="tb-btn" @click="toggleFullscreen">{{ isFullscreen ? '退出全屏' : '全屏展示' }}</span>
      </div>
    </div>

    <!-- 舞台：占满剩余高度并 overflow:hidden；stageRef 供 ResizeObserver 监听尺寸变化后重算缩放；
         v-loading 仅在首次/手动加载时显示，遮罩底色用深色以贴合大屏风格 -->
    <div ref="stageRef" class="screen-stage" v-loading="loading" element-loading-background="rgba(4, 12, 28, 0.8)">
      <!-- 画布：宽高取设计稿尺寸（默认 1920x1080）；transform 先 translate(-50%,-50%) 居中，
           再按 scale 等比缩放（transform-origin 在 CSS 中设为 center center）；
           背景优先使用配置里的 background，未配置时由 CSS 网格底纹兜底 -->
      <div class="screen-canvas" :style="canvasStyle">
        <!-- 画布标题：居中显示大屏名称与最近一次数据更新时间 -->
        <div class="canvas-title">
          <span class="canvas-title-text">{{ viewData.screen_name }}</span>
          <span class="canvas-title-sub">数据更新时间 {{ viewData.updated_at || '-' }}</span>
        </div>
        <!-- 图表组件循环：widgets 来自 screen_config；key=id 保证刷新数据时不复用错位的 DOM；
             widgetStyle 把 x/y/w/h 转成绝对定位，坐标基于画布设计尺寸（随父级 scale 一起缩放） -->
        <div v-for="widget in viewData.widgets || []" :key="widget.id" class="widget" :style="widgetStyle(widget)">
          <!-- 组件头：标题 + 数据源说明（优先显示数据集名称，其次配置里的 subtitle） -->
          <div class="widget-head">
            <span class="widget-title">{{ widget.title }}</span>
            <!-- data 由后端按图表类型拼装好（后端契约要求必传；若某组件缺 data，这里会抛异常） -->
            <span class="widget-sub">{{ widget.data.dataset_name || widget.subtitle }}</span>
          </div>
          <div class="widget-body">
            <!-- 分支一：KPI 单值卡。value 经 formatNumber 做万级压缩/千分位，单位优先取组件配置 -->
            <div v-if="widget.type === 'kpi'" class="kpi-box">
              <div class="kpi-value">{{ formatNumber(widget.data.value) }}<em>{{ widget.unit || widget.data.unit }}</em></div>
              <div class="kpi-label">{{ widget.title }}</div>
            </div>
            <!-- 分支二：表格。columns 决定表头与列顺序（label 显示、prop 取值），rows 为行数据；
                 v-for 的 key 用列 prop / 行索引，保证同名列不冲突 -->
            <div v-else-if="widget.type === 'table'" class="table-box">
              <table class="data-table">
                <thead>
                  <tr><th v-for="col in widget.data.columns" :key="col.prop">{{ col.label }}</th></tr>
                </thead>
                <tbody>
                  <tr v-for="(row, index) in widget.data.rows" :key="index">
                    <td v-for="col in widget.data.columns" :key="col.prop">{{ row[col.prop] }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <!-- 分支三：纯文本（公告/说明类），data.text 原样展示；
                 当前 .text-box 未设置 white-space: pre-wrap，多行文本中的换行会被折叠，需要多行请补样式 -->
            <div v-else-if="widget.type === 'text'" class="text-box">{{ widget.data.text }}</div>
            <!-- 其余类型统一交给 SimpleChart（line/bar/pie/rank/gauge 等）：
                 categories=类目轴，series=数值序列；unit 取组件配置或数据内单位；
                 value/max 供仪表盘/饼图使用；dark 让图表走大屏暗色配色；
                 height=420 是 SVG 内部坐标系高度（组件内按 1000xheight 绘制后等比铺满容器），
                 不是固定像素高度，因此不会撑破小组件 -->
            <SimpleChart v-else :type="widget.type" :categories="widget.data.categories"
              :series="widget.data.series" :unit="widget.unit || widget.data.unit"
              :value="widget.data.value" :max="widget.data.max" dark :height="420" />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
// 组合式 API：本页的状态与副作用（定时器/ResizeObserver/全屏监听）都集中在此
// computed 派生画布样式与刷新间隔；onMounted/onBeforeUnmount 负责监听器的注册与清理；ref 保存 DOM 引用
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
// useRoute 读取路由参数与路由名（区分预览/分享），useRouter 执行返回跳转
import { useRoute, useRouter } from 'vue-router'
// 统一请求实例：分享接口凭 token 访问，预览接口依赖登录态
import request from '@/utils/request'
// 手写 SVG 图表组件：承载大屏里除 kpi/table/text 之外的所有图表类型
import SimpleChart from '@/components/chart/SimpleChart.vue'

// 当前路由：params 里可能是 id（预览）或 token（分享）
const route = useRoute()
// 路由实例：goBack 使用
const router = useRouter()
// 页面根 DOM：全屏 API 的作用对象（包含顶栏）
const pageRef = ref()
// 画布舞台 DOM：ResizeObserver 监听它的尺寸，用于计算缩放比例
const stageRef = ref()
// 是否分享入口：路由名为 BiScreenShare 时走 /bi/screen/share/:token（免登录），否则走 preview/:id
const isShare = computed(() => route.name === 'BiScreenShare')

// 加载态：首次与手动刷新时显示遮罩；自动刷新走静默模式不显示
const loading = ref(false)
// 大屏数据：包含 screen_name/status/width/height/background/refresh_sec/updated_at/widgets
const viewData = ref({})
// 画布缩放比例：由 fitCanvas 计算，1 表示原始设计尺寸
const scale = ref(1)
// 顶栏时钟文案：updateClock 每秒更新
const clock = ref('')
// 是否处于浏览器全屏：决定按钮文案，由 fullscreenchange 事件同步
const isFullscreen = ref(false)
// 自动刷新间隔（秒）：从配置读取，非数字/空值统一为 0（表示不自动刷新）
const refreshSec = computed(() => Number(viewData.value.refresh_sec) || 0)

// 时钟定时器句柄（非响应式，仅用于卸载时清理）
let clockTimer = null
// 自动刷新定时器句柄：clear 后重建，避免配置变化后多个定时器叠加
let refreshTimer = null
// ResizeObserver 实例：监听舞台尺寸，窗口/全屏变化时重算缩放
let observer = null

// 画布内联样式：宽高取配置或默认 1920x1080；
// translate(-50%,-50%) 把画布中心对齐到舞台中心（配合 CSS 的 left/top:50%）；
// scale 再以中心为原点等比缩放，实现“设计稿坐标不变、整体适配屏幕”
const canvasStyle = computed(() => ({
  width: `${viewData.value.width || 1920}px`,
  height: `${viewData.value.height || 1080}px`,
  // 背景可由配置覆盖（如自定义图片/渐变色）；未配置时为 undefined，让 CSS 网格底纹生效
  background: viewData.value.background || undefined,
  transform: `translate(-50%, -50%) scale(${scale.value})`
}))

// 单个组件定位：x/y 为画布左上角坐标，w/h 为组件宽高，单位均为设计稿像素；
// 父级已整体缩放，这里无需再考虑实际屏幕尺寸，保证不同分辨率下布局比例一致
function widgetStyle(widget) {
  return {
    left: `${widget.x}px`, top: `${widget.y}px`,
    width: `${widget.w}px`, height: `${widget.h}px`
  }
}

// 数值格式化：绝对值 ≥1 万时折算为“x.x万”（大屏空间有限，避免长数字撑破 KPI 卡）；
// 其余走 zh-CN 千分位；非法值（null/字符串）按 0 处理
function formatNumber(value) {
  const number = Number(value) || 0
  if (Math.abs(number) >= 10000) return (number / 10000).toFixed(1) + '万'
  return number.toLocaleString('zh-CN')
}

// 更新顶栏时钟：手动拼接 YYYY-MM-DD HH:mm:ss 星期X；
// 不用 toLocaleString 是为了固定格式、避免不同浏览器/语言环境的差异
function updateClock() {
  const now = new Date()
  // 星期数组按 getDay()（0=周日）索引
  const week = ['日', '一', '二', '三', '四', '五', '六'][now.getDay()]
  // 补零：把 1 位数字变成 2 位，保证时间格式对齐
  const pad = num => String(num).padStart(2, '0')
  // getMonth() 从 0 开始，需要 +1
  clock.value = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())} `
    + `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())} 星期${week}`
}

// 计算缩放：取舞台宽/高与设计稿宽/高的较小比值（contain 策略），保证整块画布完整可见且不变形；
// “留边”优于裁切，符合投屏习惯。stage 未挂载或尺寸为 0 时兜底为 1，避免 scale=0 导致画布消失
function fitCanvas() {
  const stage = stageRef.value
  if (!stage) return
  const width = viewData.value.width || 1920
  const height = viewData.value.height || 1080
  scale.value = Math.min(stage.clientWidth / width, stage.clientHeight / height) || 1
}

// 加载大屏数据：showLoading=false 表示静默刷新（自动刷新/顶栏手动刷新），不显示遮罩以免打断观看；
// 每次加载后都重新 fitCanvas（宽高可能变化）并重建刷新定时器（refresh_sec 可能变化）
async function loadData(showLoading = true) {
  const silent = !showLoading
  if (!silent) loading.value = true
  try {
    // 分享入口用 token（免登录），预览入口用 id（依赖后台登录态）
    const res = isShare.value
      ? await request.get(`/bi/screen/share/${route.params.token}`)
      : await request.get(`/bi/screen/preview/${route.params.id}`)
    viewData.value = res.data || {}
    fitCanvas()
    setupRefresh()
  } finally {
    if (!silent) loading.value = false
  }
}

// 重建自动刷新定时器：先清旧定时器，避免配置变化后多个间隔同时触发；
// refreshSec<=0 时只清理不新建（手动刷新仍然可用）
function setupRefresh() {
  if (refreshTimer) clearInterval(refreshTimer)
  refreshTimer = null
  if (refreshSec.value > 0) {
    refreshTimer = setInterval(() => loadData(false), refreshSec.value * 1000)
  }
}

// 全屏切换：未全屏则对整页请求全屏，已全屏则退出；
// 浏览器可能因权限/不支持而 reject，用 catch 吞掉（按钮仍可点，不影响其他功能）
function toggleFullscreen() {
  if (!document.fullscreenElement) {
    pageRef.value?.requestFullscreen?.().catch(() => {})
  } else {
    document.exitFullscreen?.().catch(() => {})
  }
}

// 全屏状态同步：fullscreenchange（按 Esc 退出也会触发）后更新按钮文案，并重算缩放
function syncFullscreenState() {
  isFullscreen.value = Boolean(document.fullscreenElement)
  fitCanvas()
}

// 返回逻辑：分享页没有后台上下文，固定回工作台；
// 预览页优先浏览器后退（保留列表页的筛选状态），无历史记录时回 /bi 大屏列表
function goBack() {
  if (isShare.value) {
    router.push('/dashboard')
    return
  }
  const canBack = window.history.length > 1
  if (canBack) router.back()
  else router.push('/bi')
}

// 挂载：先立即渲染时钟再起定时器（避免首秒空白）；加载数据；监听舞台尺寸、全屏状态与窗口 resize。
// 同时监听 resize 是因为部分浏览器全屏切换时不一定触发 ResizeObserver
onMounted(() => {
  updateClock()
  clockTimer = setInterval(updateClock, 1000)
  loadData(true)
  observer = new ResizeObserver(fitCanvas)
  if (stageRef.value) observer.observe(stageRef.value)
  document.addEventListener('fullscreenchange', syncFullscreenState)
  window.addEventListener('resize', fitCanvas)
})

// 卸载清理：定时器、ResizeObserver、全局事件都要释放，避免页面切走后仍在后台刷新或占用内存
onBeforeUnmount(() => {
  clearInterval(clockTimer)
  clearInterval(refreshTimer)
  observer?.disconnect()
  document.removeEventListener('fullscreenchange', syncFullscreenState)
  window.removeEventListener('resize', fitCanvas)
})
</script>

<style scoped>
/* 页面根：fixed + inset:0 脱离后台布局铺满视口；纵向 flex 让顶栏固定、舞台吃满剩余高度；
   深蓝径向渐变底 + 浅蓝文字，全部为写死色值（大屏需要稳定的暗色观感，不随系统浅色主题变化） */
.screen-page {
  position: fixed;
  inset: 0;
  display: flex;
  flex-direction: column;
  color: #e8f1ff;
  background: radial-gradient(circle at 50% 0%, #16305f 0%, #0a1730 46%, #050d1c 100%);
}
/* 顶栏：z-index 5 保证浮在画布之上；半透明深底 + 蓝色下边框，与画布融合又不遮挡内容 */
.screen-topbar {
  position: relative;
  z-index: 5;
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 52px;
  padding: 0 22px;
  background: rgba(6, 16, 36, 0.72);
  border-bottom: 1px solid rgba(78, 168, 255, 0.22);
}
/* 顶栏左右分组：横向排列，gap 14px 保持控件间距 */
.tb-left, .tb-right { display: flex; align-items: center; gap: 14px; }
/* 返回按钮与操作按钮：字号 13px、蓝色描边胶囊，统一顶栏控件样式 */
.tb-back, .tb-btn {
  font-size: 13px;
  color: #8fc4ff;
  cursor: pointer;
  padding: 5px 12px;
  border: 1px solid rgba(78, 168, 255, 0.32);
  border-radius: 6px;
  transition: all 0.2s ease;
}
/* hover：文字变白 + 蓝色半透明底，提供明确的点击反馈 */
.tb-back:hover, .tb-btn:hover { color: #fff; background: rgba(78, 168, 255, 0.18); }
/* 大屏名称：16px 加粗 + 字距 1px，作为顶栏主信息 */
.tb-name { font-size: 16px; font-weight: 600; letter-spacing: 1px; }
/* 时钟：低对比度辅助信息，字距 0.5px 让数字更易读 */
.tb-clock { font-size: 13px; color: rgba(206, 226, 255, 0.72); letter-spacing: 0.5px; }
/* 自动刷新提示：绿色高亮，表示数据处于自动更新状态 */
.tb-refresh { font-size: 12px; color: #2ee6a8; }
/* 舞台：relative 作为画布绝对定位的参照；flex:1 占满顶栏以外区域；overflow:hidden 裁掉缩放后超出部分 */
.screen-stage { position: relative; flex: 1; overflow: hidden; }
/* 画布：绝对定位 + left/top 50% + transform-origin 中心，配合 JS 的 translate(-50%,-50%) scale() 实现居中缩放；
   background-image 用两组线性渐变画出 48px 网格底纹，作为未配置 background 时的默认大屏纹理 */
.screen-canvas {
  position: absolute;
  left: 50%;
  top: 50%;
  transform-origin: center center;
  background-image: linear-gradient(rgba(78, 168, 255, 0.06) 1px, transparent 1px),
    linear-gradient(90deg, rgba(78, 168, 255, 0.06) 1px, transparent 1px);
  background-size: 48px 48px;
}
/* 画布顶部氛围光：伪元素叠一层径向蓝光，pointer-events:none 保证不影响图表交互 */
.screen-canvas::before {
  content: '';
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at 50% 0%, rgba(32, 88, 190, 0.28), transparent 62%);
  pointer-events: none;
}
/* 画布标题区：绝对定位于画布顶部，纵向排列名称与更新时间 */
.canvas-title {
  position: absolute;
  top: 18px;
  left: 0;
  right: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}
/* 大屏主标题：28px 加粗、6px 字距 + 蓝色外发光，营造投屏标题效果 */
.canvas-title-text {
  font-size: 28px;
  font-weight: 700;
  letter-spacing: 6px;
  color: #dceeff;
  text-shadow: 0 0 18px rgba(78, 168, 255, 0.65);
}
/* 更新时间：12px 低透明度辅助文字 */
.canvas-title-sub { font-size: 12px; color: rgba(206, 226, 255, 0.55); }
/* 图表组件容器：绝对定位（坐标由 widgetStyle 注入），纵向 flex 让头部固定、内容区自适应；
   半透明渐变底 + 蓝色描边 + 内外阴影，形成“悬浮玻璃面板”的大屏质感 */
.widget {
  position: absolute;
  display: flex;
  flex-direction: column;
  padding: 12px 14px 10px;
  background: linear-gradient(180deg, rgba(18, 44, 92, 0.82), rgba(9, 24, 52, 0.72));
  border: 1px solid rgba(78, 168, 255, 0.26);
  border-radius: 10px;
  box-shadow: inset 0 0 30px rgba(78, 168, 255, 0.08), 0 10px 24px rgba(0, 0, 0, 0.35);
}
/* 组件头：标题与数据源说明两端对齐；baseline 对齐让不同字号文字底部齐平 */
.widget-head { display: flex; align-items: baseline; justify-content: space-between; gap: 10px; padding-bottom: 8px; }
/* 组件标题：15px 加粗，浅蓝白保证暗底可读 */
.widget-title { font-size: 15px; font-weight: 600; color: #cfe6ff; letter-spacing: 1px; }
/* 数据源说明：11px 更低透明度，弱化于标题 */
.widget-sub { font-size: 11px; color: rgba(206, 226, 255, 0.45); }
/* 内容区：relative 供图表内部定位；flex:1 + min-height:0 让子元素（如表格滚动区）正确收缩而不撑破组件 */
.widget-body { position: relative; flex: 1; min-height: 0; }
/* KPI 容器：纵向排列并垂直居中，数值在卡片中间 */
.kpi-box { display: flex; flex-direction: column; justify-content: center; height: 100%; }
/* KPI 数值：42px 主蓝色 + 外发光，作为大屏最醒目的数字 */
.kpi-value { font-size: 42px; font-weight: 700; color: #4ea8ff; text-shadow: 0 0 18px rgba(78, 168, 255, 0.5); }
/* KPI 单位：取消 em 默认斜体，缩小为 14px 并降低透明度，跟在数值后不抢视觉 */
.kpi-value em { margin-left: 6px; font-style: normal; font-size: 14px; color: rgba(206, 226, 255, 0.6); font-weight: 500; }
/* KPI 说明文字：13px 辅助色，位于数值下方 */
.kpi-label { margin-top: 8px; font-size: 13px; color: rgba(206, 226, 255, 0.55); }
/* 表格容器：占满高度并允许内部滚动，列多/行多时不会溢出组件 */
.table-box { height: 100%; overflow: auto; }
/* 数据表：铺满宽度、合并边框，12px 浅蓝文字适配暗底 */
.data-table { width: 100%; border-collapse: collapse; font-size: 12px; color: #cfe6ff; }
/* 表头：sticky 吸顶保证滚动时列名可见；深蓝底 + 蓝色下边框，与表体区分 */
.data-table th { position: sticky; top: 0; padding: 7px 10px; font-weight: 600; text-align: left; color: #8fc4ff; background: rgba(28, 62, 122, 0.9); border-bottom: 1px solid rgba(78, 168, 255, 0.25); }
/* 单元格：虚线分隔行，降低表格的厚重感 */
.data-table td { padding: 7px 10px; color: rgba(206, 226, 255, 0.82); border-bottom: 1px dashed rgba(78, 168, 255, 0.14); }
/* 行 hover：淡蓝底提示当前行，便于横向读数 */
.data-table tbody tr:hover td { background: rgba(78, 168, 255, 0.08); }
/* 文本组件：占满高度、垂直居中，14px 行高 1.9 提升长文案可读性 */
.text-box { display: flex; align-items: center; height: 100%; font-size: 14px; line-height: 1.9; color: rgba(206, 226, 255, 0.78); }
</style>
