<template>
  <!-- ============================================================
       组件：首页 7 日趋势折线图（纯 SVG，无图表库依赖）
       职责：用轻量 SVG 渲染 1~2 条时间序列，支持面积填充、网格线与图例。
       依赖：无第三方库；颜色由父组件传入 CSS 变量（如 var(--chart-1)）。
       说明：不引入 ECharts 是为了避免为首页增加数百 KB 依赖；
             3D/复杂报表再按需引入图表库，二者不冲突。
       ============================================================ -->
  <div ref="wrapRef" class="trend-chart">
    <!-- 有数据时才渲染图例与坐标系统；全 0 时改走空提示，避免画出无意义的平线 -->
    <template v-if="!isEmpty">
    <!-- 图例：仅当存在序列时显示，色点颜色直接使用传入的主题变量 -->
    <div v-if="series.length" class="chart-legend">
      <!-- 逐条序列渲染图例项，key 用名称保证稳定 -->
      <span v-for="s in series" :key="s.name" class="legend-item">
        <!-- 色点：背景色 = 该序列的主题色 -->
        <i class="legend-dot" :style="{ background: s.color }"></i>
        <!-- 序列名称：如“工单”“流程” -->
        <span class="legend-name">{{ s.name }}</span>
      </span>
    </div>

    <!-- 绘图区容器：宽度自适应（ResizeObserver 更新），高度由 height 属性决定 -->
    <div class="chart-body" :style="{ height: chartHeight + 'px' }">
      <!-- SVG 坐标系统按真实像素计算，避免拉伸导致文字/点变形 -->
      <svg class="chart-svg" :width="chartWidth" :height="chartHeight" role="img" :aria-label="ariaLabel">
        <!-- 横向网格线：4 条等分线，颜色取自主题边框令牌 -->
        <line
          v-for="(g, gi) in gridLines"
          :key="'g' + gi"
          :x1="pad.left"
          :x2="chartWidth - pad.right"
          :y1="g.y"
          :y2="g.y"
          class="grid-line"
        />
        <!-- Y 轴刻度文字：最大值、中值、0，使用主题弱化文字色 -->
        <text
          v-for="(g, gi) in gridLines"
          :key="'t' + gi"
          :x="pad.left - 6"
          :y="g.y + 3"
          text-anchor="end"
          class="axis-text"
        >{{ g.label }}</text>

        <!-- 每条序列：面积 + 折线 + 数据点；v-for 的 key 用序列名 -->
        <g v-for="line in lines" :key="line.name">
          <!-- 面积填充：仅在 area=true 时绘制，透明度由 fill-opacity 控制 -->
          <path
            v-if="area"
            :d="line.areaPath"
            :style="{ fill: line.color }"
            fill-opacity="0.12"
            stroke="none"
          />
          <!-- 折线主体：stroke 颜色跟随主题令牌 -->
          <polyline
            :points="line.points"
            fill="none"
            :style="{ stroke: line.color }"
            stroke-width="2.5"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
          <!-- 数据点：半径 2.5，hover 时通过 <title> 显示数值（原生提示，无额外依赖） -->
          <circle
            v-for="p in line.dots"
            :key="line.name + '-' + p.i"
            :cx="p.x"
            :cy="p.y"
            r="2.6"
            :style="{ fill: line.color }"
          >
            <!-- 原生 title 作为轻量 tooltip：显示“日期 序列名 值” -->
            <title>{{ p.label }} {{ line.name }} {{ p.value }}</title>
          </circle>
        </g>
      </svg>

      <!-- X 轴标签：用 HTML 渲染，避免 SVG 内文字被缩放；与绘图区左右内边距对齐 -->
      <div class="x-axis" :style="{ paddingLeft: pad.left + 'px', paddingRight: pad.right + 'px' }">
        <!-- 逐日显示 MM-DD，字号小、颜色弱化，保证 7 个标签在窄屏也能排下 -->
        <span v-for="(label, li) in labels" :key="'x' + li">{{ label }}</span>
      </div>
    </div>
    </template>
    <div v-else class="chart-empty" :style="{ height: height + 'px' }">近 7 天暂无新增数据</div>
  </div>
</template>

<script setup>
// ============================================================
// 脚本：纯 SVG 折线图的几何计算。
// 数据流：props.series / props.labels → lines（像素坐标）→ 模板输出。
// 无副作用：仅用 ResizeObserver 监听容器宽度变化并重算坐标。
// ============================================================
// Vue 基础 API：ref 存容器与宽度，computed 派生几何数据，生命周期管理观察器
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'

// 组件属性定义
const props = defineProps({
  // 序列数组：每项包含 name（图例名）、color（CSS 颜色/变量）、values（数值数组）
  series: { type: Array, default: () => [] },
  // X 轴标签数组，与 values 长度一致
  labels: { type: Array, default: () => [] },
  // 图表主体高度（含图例之外的绘图区），单位 px
  height: { type: Number, default: 140 },
  // 是否绘制面积填充
  area: { type: Boolean, default: true }
})

// 容器 DOM 引用：用于 ResizeObserver 监听实际宽度
const wrapRef = ref(null)
// 当前可用宽度：初始 600，挂载后由 ResizeObserver 修正为真实值
const chartWidth = ref(600)
// X 轴标签占用高度：固定 18px，从总高度中扣除
const X_AXIS_H = 18
// 绘图区高度 = 总高度 - X 轴标签高度（最小 60，防止极端小容器导致高度为负）
const chartHeight = computed(() => Math.max(60, props.height - X_AXIS_H))
// 绘图区内边距：左侧留 34px 给 Y 轴刻度，右侧 12px，上下各 12px
const pad = { left: 34, right: 12, top: 12, bottom: 10 }

// 是否存在有效数据：所有序列的数值总和为 0 时视为空
const isEmpty = computed(() => {
  // some 短路：任意序列存在非 0 值即认为有数据
  return !props.series.some(s => (s.values || []).some(v => Number(v) > 0))
})

// 图表的无障碍说明：拼出序列名，便于读屏软件播报
const ariaLabel = computed(() => `趋势图：${props.series.map(s => s.name).join('、') || '无数据'}`)

// 计算“漂亮”的纵轴最大值：把原始最大值的数量级向上取整，避免出现 7、13 这类刻度
function niceMax(values) {
  // 取所有序列的最大值，空数组回退 0
  const rawMax = Math.max(...values, 0)
  // 全 0 时给 1，避免除以 0
  if (rawMax <= 0) return 1
  // 数量级：例如 max=13 → 10；max=520 → 100
  const magnitude = Math.pow(10, Math.floor(Math.log10(rawMax)))
  // 按数量级向上取整：13 → 20，520 → 600
  return Math.ceil(rawMax / magnitude) * magnitude
}

// 纵轴刻度：4 条网格线（含顶部与底部），返回 y 坐标与文本
const gridLines = computed(() => {
  // 把全部序列摊平，求统一的纵轴上限，保证多条线共享刻度
  const all = props.series.flatMap(s => s.values || [])
  // 纵轴上限
  const max = niceMax(all)
  // 绘图区高度（去除上下内边距）
  const plotH = chartHeight.value - pad.top - pad.bottom
  // 生成 4 条线：i=0 顶部（max），i=3 底部（0）
  return [0, 1, 2, 3].map(i => {
    // 该刻度占总高度的比例（0 在顶部，1 在底部）
    const ratio = i / 3
    // 对应的数值：顶部为 max、底部为 0
    const value = max - max * ratio
    // 文本取整，避免出现小数刻度
    return { y: pad.top + plotH * ratio, label: String(Math.round(value)) }
  })
})

// 把每条序列转换为像素坐标（折线点串、面积路径、散点）
const lines = computed(() => {
  // 统一纵轴上限，与网格线保持一致
  const all = props.series.flatMap(s => s.values || [])
  const max = niceMax(all)
  // 绘图区宽高
  const plotW = Math.max(1, chartWidth.value - pad.left - pad.right)
  const plotH = Math.max(1, chartHeight.value - pad.top - pad.bottom)
  // 底部基线 y 坐标，面积路径会回落到这里
  const baseY = pad.top + plotH
  // 逐条序列映射
  return props.series.map(s => {
    // 数值数组；为空时按 0 处理，避免除零
    const values = s.values && s.values.length ? s.values : [0]
    // 单点序列固定画在中间；多点则按索引均分宽度
    const stepX = values.length > 1 ? plotW / (values.length - 1) : 0
    // 生成每个点的像素坐标与原始值
    const dots = values.map((v, i) => ({
      i,                                                          // 点的索引，作为 key
      x: pad.left + (values.length > 1 ? stepX * i : plotW / 2),   // 横坐标
      y: baseY - (Number(v || 0) / max) * plotH,                   // 纵坐标（值越大越靠上）
      value: Number(v || 0),                                       // 原始数值，供 tooltip
      label: props.labels[i] || ''                                 // 对应日期标签
    }))
    // 折线点串：SVG polyline 需要的 "x,y x,y" 格式
    const points = dots.map(d => `${d.x},${d.y}`).join(' ')
    // 面积路径：起点在左下方基线，沿折线走完，再回落到右下方基线形成闭合面
    const first = dots[0]
    const last = dots[dots.length - 1]
    const areaPath = `M ${first.x},${baseY} L ${dots.map(d => `${d.x},${d.y}`).join(' L ')} L ${last.x},${baseY} Z`
    // 返回该序列的完整几何数据，颜色原样透传
    return { name: s.name, color: s.color, points, dots, areaPath }
  })
})

// ResizeObserver 实例：组件卸载时必须断开，避免内存泄漏
let observer = null

// 挂载后监听容器宽度：容器宽度变化（如侧边栏折叠、窗口缩放）时重算图表
onMounted(() => {
  // 容器不存在时直接返回，防御性判断
  if (!wrapRef.value) return
  // 创建观察器：回调里取内容区宽度
  observer = new ResizeObserver(entries => {
    // 取第一条记录的内容宽度
    const width = entries[0]?.contentRect?.width || 0
    // 小于 240 时按 240 处理，避免窄屏把图表压扁到不可读
    chartWidth.value = Math.max(240, Math.round(width))
  })
  // 开始观察图表容器
  observer.observe(wrapRef.value)
  // 初始化一次宽度，避免首帧使用默认 600 导致闪烁
  chartWidth.value = Math.max(240, Math.round(wrapRef.value.clientWidth))
})

// 卸载前断开观察器，释放资源
onBeforeUnmount(() => {
  if (observer) observer.disconnect()
  observer = null
})
</script>

<style scoped>
/* 图表根容器：占满父级宽度，字体继承全局主题 */
.trend-chart {
  width: 100%;
  min-width: 0;
}

/* 图例行：右对齐，小圆点 + 名称 */
.chart-legend {
  display: flex;
  justify-content: flex-end;
  gap: 14px;
  margin-bottom: 4px;
  font-size: 12px;
}

/* 单个图例项：横向排列 */
.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: var(--app-text-2);
}

/* 图例色点：8px 圆形，背景由行内样式注入主题色 */
.legend-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}

/* 绘图区：相对定位，X 轴标签绝对定位在底部 */
.chart-body {
  position: relative;
  width: 100%;
}

/* SVG 画布：块级显示，避免行内元素底部留白 */
.chart-svg {
  display: block;
}

/* 网格线：使用主题边框色，暗色下自动变淡，不抢折线视觉 */
.grid-line {
  stroke: var(--app-border-light);
  stroke-width: 1;
}

/* 坐标文字：弱化文字色，字号 10px，数字等宽避免跳动 */
.axis-text {
  fill: var(--app-text-3);
  font-size: 10px;
  font-variant-numeric: tabular-nums;
}

/* X 轴标签行：与绘图区左右内边距对齐，两端分布 */
.x-axis {
  position: absolute;
  left: 0;
  right: 0;
  bottom: -2px;
  display: flex;
  justify-content: space-between;
  font-size: 10px;
  color: var(--app-text-3);
}

/* 空数据提示：居中弱化文字，保留图表区域高度但不再画坐标系 */
.chart-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 80px;
  font-size: 12px;
  color: var(--app-text-3);
}
</style>
