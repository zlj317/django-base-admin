<!--
  文件级说明：
  职责：轻量级 SVG 图表封装——用纯手写 SVG/几何计算渲染排行、仪表盘、环形饼图、折线/柱状图，
        不依赖 ECharts 等图表库，便于在报表/大屏中控制体积与主题一致性。
  依赖：仅 Vue 的 computed；颜色全部引用主题 CSS 变量（--chart-1..6），因此切换主题色/暗色自动跟随。
  被谁使用：report/ReportPreview.vue、BI 大屏与报表页面等。
  说明：组件是纯计算渲染，无网络请求、无副作用；type 决定渲染分支，其余 props 为数据与尺寸。
-->
<template>
  <!-- 图表根节点：dark 类用于局部暗色样式；通过内联 CSS 变量 --chart-hole 给环形图“挖孔”部分指定底色
       （暗色用固定深蓝、浅色用主题面板色），因为 SVG 圆不能真正做遮罩，只能用同心圆盖住中心 -->
  <div class="simple-chart" :class="{ dark }" :style="{ '--chart-hole': dark ? '#0d1f3f' : 'var(--app-surface)' }">
    <!-- 分支一：排行榜（横向条形列表），适合展示 TopN 维度对比 -->
    <div v-if="type === 'rank'" class="rank-list">
      <!-- 单行排行：rankItems 已按数值降序并截取前 8 项；key 用名称保证稳定 -->
      <div v-for="(item, index) in rankItems" :key="item.name" class="rank-row">
        <!-- 名次序号：前三名附加 top 类做高亮（样式里用 warning 色），index 从 0 开始故显示 index+1 -->
        <span class="rank-no" :class="{ top: index < 3 }">{{ index + 1 }}</span>
        <!-- 名称：title 属性让被省略的长名称可通过悬浮查看 -->
        <span class="rank-name" :title="item.name">{{ item.name }}</span>
        <!-- 数值：format 统一做千分位/万级压缩，单位存在时以 em 小字展示 -->
        <span class="rank-value">{{ format(item.value) }}<em v-if="unit">{{ unit }}</em></span>
        <!-- 比例条：宽度按最大值百分比计算（最小 6% 保证极小值仍可见），统一使用第一个图表色 -->
        <div class="rank-bar"><i :style="{ width: item.percent + '%', background: colorAt(0) }"></i></div>
      </div>
    </div>

    <!-- 分支二：仪表盘（半圆进度环），用于完成率/达成率类单值指标 -->
    <div v-else-if="type === 'gauge'" class="gauge-wrap">
      <!-- 固定 500x320 坐标系 + meet 等比缩放，保证不同容器尺寸下圆弧比例不变形 -->
      <svg viewBox="0 0 500 320" preserveAspectRatio="xMidYMid meet">
        <!-- 底层轨道：完整半圆，颜色取 trackColor（浅边框色），作为进度背景 -->
        <path :d="gauge.track" fill="none" :stroke="trackColor" stroke-width="18" stroke-linecap="round" />
        <!-- 进度弧：从 180° 画到 value 对应角度；颜色取第三个图表色以区别于其他图表 -->
        <path :d="gauge.progress" fill="none" :stroke="colorAt(2)" stroke-width="18" stroke-linecap="round" />
        <!-- 中心数值：位置略低于圆心，数值经 format 压缩（如 1.2万）避免溢出圆弧 -->
        <text x="250" y="228" text-anchor="middle" class="gauge-value">{{ format(gauge.value) }}</text>
        <!-- 数值下方说明：未传 unit 时默认显示“完成率” -->
        <text x="250" y="256" text-anchor="middle" class="gauge-label">{{ unit || '完成率' }}</text>
      </svg>
      <!-- 刻度：绝对定位在圆弧左右两端，分别显示 0 与最大值的格式化结果 -->
      <div class="gauge-scale">
        <span>0</span>
        <span>{{ format(gauge.max) }}</span>
      </div>
    </div>

    <!-- 分支三：环形饼图，左侧图形 + 右侧图例 -->
    <div v-else-if="type === 'pie'" class="pie-wrap">
      <!-- 500x420 坐标系：外半径 150 可容纳环形与中心汇总文字 -->
      <svg viewBox="0 0 500 420" preserveAspectRatio="xMidYMid meet">
        <!-- 单数据项特例：一个扇形会退化成 360° 整环，SVG 弧线起终点重合会失效，
             因此改用两个同心圆表达“整环 + 中心挖孔” -->
        <template v-if="pie.slices.length === 1">
          <!-- 外圆：整环主体色 -->
          <circle cx="250" cy="210" :r="pie.outer" :fill="colorAt(0)" />
          <!-- 内圆：用 --chart-hole（由根节点内联变量决定）覆盖中心，形成环形效果 -->
          <circle cx="250" cy="210" :r="pie.inner" fill="var(--chart-hole, #fff)" />
        </template>
        <!-- 多数据项：每项一个环形扇区路径（donutPath 已算好外弧+内弧） -->
        <template v-else>
          <!-- path d 由 pie 计算属性生成；transparent 描边 + 2px 宽度用于在扇区之间留出极细缝隙，
               避免相邻色块完全贴合导致边界模糊 -->
          <path v-for="slice in pie.slices" :key="slice.name" :d="slice.path"
            :fill="slice.color" stroke="transparent" stroke-width="2" />
        </template>
        <!-- 中心汇总数值：位于圆心稍上方 -->
        <text x="250" y="204" text-anchor="middle" class="pie-total">{{ format(pie.total) }}</text>
        <!-- 汇总说明：未传 unit 时默认“总量” -->
        <text x="250" y="228" text-anchor="middle" class="pie-total-label">{{ unit || '总量' }}</text>
      </svg>
      <!-- 右侧图例：列出每项的色点、名称与占比 -->
      <div class="pie-legend">
        <!-- 图例行：key 用名称；legend-row 纵向排列 -->
        <div v-for="slice in pie.slices" :key="slice.name" class="legend-row">
          <!-- 图例色点：与扇区填充色严格一致，保证图例与图形对应 -->
          <i class="dot" :style="{ background: slice.color }"></i>
          <!-- 名称：长名称省略显示，title 提供完整文本 -->
          <span class="legend-name" :title="slice.name">{{ slice.name }}</span>
          <!-- 占比：由 pie 计算属性保留一位小数 -->
          <span class="legend-value">{{ slice.percent }}%</span>
        </div>
      </div>
    </div>

    <!-- 分支四（兜底）：直角坐标系图表，type='line' 画折线、其余（默认 bar）画柱状图 -->
    <div v-else class="axis-wrap">
      <!-- 图例：按 series 顺序列出多系列名称与对应颜色；index 决定取哪个图表色 -->
      <div class="chart-legend">
        <!-- 图例项：色点 + 系列名；颜色由 colorAt(index) 与图形保持一致 -->
        <span v-for="(item, index) in series" :key="item.name" class="legend-item">
          <i class="dot" :style="{ background: colorAt(index) }"></i>{{ item.name }}
        </span>
      </div>
      <!-- 主画布：宽度固定 1000，高度取 props.height，保证多图表在同一页面横向对齐；
           meet 等比缩放，容器比例不同也不会拉伸变形 -->
      <svg :viewBox="`0 0 1000 ${height}`" preserveAspectRatio="xMidYMid meet">
        <!-- 水平网格线：axis.grid 提供 5 条 y 坐标（含 0 与最大值），x 从 64 到 976 覆盖绘图区 -->
        <line v-for="(y, index) in axis.grid" :key="'g' + index" x1="64" :y1="y" x2="976" :y2="y"
          :stroke="gridColor" stroke-width="1" />
        <!-- y 轴刻度文字：x=56 右对齐贴近绘图区；tickLabel 按网格序号换算对应数值并格式化 -->
        <text v-for="(y, index) in axis.grid" :key="'t' + index" x="56" :y="y + 4" text-anchor="end"
          class="axis-tick">{{ tickLabel(index) }}</text>
        <!-- 折线模式：逐系列绘制面积填充 + 折线 + 数据点 -->
        <template v-if="type === 'line'">
          <!-- 每个系列一组图形；key 带 series 序号避免不同系列同色名冲突 -->
          <template v-for="(item, index) in axis.lines" :key="'l' + index">
            <!-- 面积：折线下方到 x 轴的闭合路径，12% 透明度形成轻量填充，强调趋势又不过分抢眼 -->
            <path :d="item.area" :fill="item.color" opacity="0.12" />
            <!-- 折线：3px 圆角连接（stroke-linejoin=round）让拐点更柔和 -->
            <polyline :points="item.points" fill="none" :stroke="item.color" stroke-width="3" stroke-linejoin="round" />
            <!-- 数据点：每个数据位置画 4px 圆点，便于定位具体数值 -->
            <circle v-for="(point, pIndex) in item.points2" :key="'c' + index + '-' + pIndex"
              :cx="point.x" :cy="point.y" r="4" :fill="item.color" />
          </template>
        </template>
        <!-- 柱状模式：axis.bars 已把所有系列、所有类目的柱子位置算好，这里逐个绘制矩形 -->
        <template v-else>
          <!-- 柱子：rx=4 圆角，视觉更现代；宽高由计算属性中的 barWidth 与数值比例决定 -->
          <rect v-for="(bar, index) in axis.bars" :key="'b' + index" :x="bar.x" :y="bar.y"
            :width="bar.w" :height="bar.h" :fill="bar.color" rx="4" />
        </template>
        <!-- x 轴标签：y = height-16 靠近底部；类目超过 8 个时 label.transform 为 rotate(-35)，避免文字重叠 -->
        <text v-for="(label, index) in axis.labels" :key="'x' + index" :x="label.x" :y="height - 16"
          text-anchor="middle" class="axis-label" :transform="label.transform">{{ label.text }}</text>
      </svg>
    </div>
    <!-- 全局空态：无论哪种图表类型，类目与系列都为空时覆盖显示“暂无数据” -->
    <div v-if="!categories.length && !series.length" class="empty-tip">暂无数据</div>
  </div>
</template>

<script setup>
// computed 用于声明所有几何/统计派生数据（axis、pie、gauge、rankItems）
import { computed } from 'vue'

// 组件 props：
// · type：图表类型，bar（默认）/line/pie/gauge/rank
// · categories：类目轴数据（如月份、部门名）
// · series：数据系列数组，[{ name, data: number[] }]，饼图/排行/仪表盘只取第一项
// · unit：数值单位（如 %、件、元），显示在图例/标签/中心文字中
// · dark：是否暗色模式，控制环形图中心挖孔色
// · value / max：仪表盘专用，当前值与满量程
// · height：折线/柱状图 SVG 高度，宽度固定 1000 保持比例一致
const props = defineProps({
  type: { type: String, default: 'bar' },
  categories: { type: Array, default: () => [] },
  series: { type: Array, default: () => [] },
  unit: { type: String, default: '' },
  dark: { type: Boolean, default: false },
  value: { type: Number, default: 0 },
  max: { type: Number, default: 100 },
  height: { type: Number, default: 440 }
})

// 图表调色板：直接引用 6 个主题 CSS 变量，切换主题色/暗色时所有图形自动跟随，无需重算
const CHART_COLORS = [
  'var(--chart-1)', 'var(--chart-2)', 'var(--chart-3)',
  'var(--chart-4)', 'var(--chart-5)', 'var(--chart-6)'
]  // 直接引用主题变量，切换主题色/暗色时图表自动跟随
// 折线/柱状图的逻辑宽度常量：所有横向坐标按 1000 设计，配合 viewBox 等比缩放
const WIDTH = 1000

// 颜色列表（只是把常量包成 computed，模板/函数中统一通过 colors.value 访问）
const colors = computed(() => CHART_COLORS)
// 网格线颜色：取主题浅边框色，避免在深色主题下仍用固定浅灰而显得刺眼
const gridColor = computed(() => 'var(--app-border-light)')
// 仪表盘轨道颜色：同样取主题浅边框色，作为未完成部分的底色
const trackColor = computed(() => 'var(--app-border-light)')

// 按索引取颜色：取模循环，保证系列数超过 6 时仍能复用调色板而不出现 undefined
function colorAt(index) {
  return colors.value[index % colors.value.length]
}

// 数值格式化：
// · 非数字或 NaN 统一按 0 处理，避免图表出现 NaN 文本
// · 绝对值 ≥ 10000 时压缩为“x.x万”，控制坐标轴与标签宽度
// · 其余使用 zh-CN 千分位格式
function format(value) {
  const num = Number(value) || 0
  if (Math.abs(num) >= 10000) return (num / 10000).toFixed(1) + '万'
  return num.toLocaleString('zh-CN')
}

// 求“好看的”坐标轴上限：把最大值向上取整到 1/2/2.5/4/5/10 × 10^n，
// 这样 y 轴 5 等分后刻度值都是整齐数字（如 20、40、60…），而不是 17342 这类原始值
function niceCeil(value) {
  // 非法或非正数时给一个最小上限 1，保证后续比例计算不会除以 0
  if (value <= 0) return 1
  // 取数量级（如 1734 -> 1000），把估算转化为 1~10 之间的“尾数”
  const magnitude = Math.pow(10, Math.floor(Math.log10(value)))
  // 允许的尾数档位：优先用较小档位，让图表上方留白不至于过多
  const steps = [1, 2, 2.5, 4, 5, 10]
  const target = value / magnitude
  // 找到第一个不小于目标尾数的档位；全部不够时用 10 兜底（极少发生，防浮点误差）
  const step = steps.find(item => item >= target) || 10
  return step * magnitude
}

// 柱状图/折线图几何：统一坐标区，保证同一页面多个图表视觉一致
const axis = computed(() => {
  // 类目与系列做空值兜底，保证模板在数据未加载时也不会报错
  const categories = props.categories || []
  const series = props.series || []
  // 画布总高度由调用方控制（默认 440）
  const height = props.height
  // 绘图区内边距：左侧留给 y 轴刻度(64)，右侧留白(24)，上留白(18)，底部留给 x 轴标签(46)
  const padL = 64
  const padR = 24
  const padT = 18
  const padB = 46
  // 绘图区宽高：宽度基于常量 1000，高度基于传入 height
  const plotW = WIDTH - padL - padR
  const plotH = height - padT - padB
  // 所有系列中的最大值（至少为 1，避免空数据时除零；flatMap 展开各系列的 data 数组）
  const maxValue = Math.max(1, ...series.flatMap(item => (item.data || []).map(v => Number(v) || 0)))
  // y 轴上限取“好看刻度”，使 5 条网格线对应整数
  const scaleMax = niceCeil(maxValue)
  // 5 条水平网格线的 y 坐标：从绘图区底部(0)均匀分布到顶部(scaleMax)
  const grid = [0, 1, 2, 3, 4].map(index => padT + plotH - (plotH * index) / 4)
  // 每个类目占据的横向带宽；无类目时退化为整条绘图区宽度
  const band = categories.length ? plotW / categories.length : plotW
  // 单根柱子宽度：最多 46px，且只占类目带宽的 66%，剩余留给柱间/组间间隙；多系列时按系列数均分
  const barWidth = Math.min(46, (band * 0.66) / Math.max(1, series.length))
  // 所有柱子的几何信息集合，供模板逐个绘制
  const bars = []
  categories.forEach((category, cIndex) => {
    // 当前类目内第一根柱子的起始 x：类目左边界 + 居中偏移（组总宽小于带宽时左右各留一半）
    const startX = padL + band * cIndex + (band - barWidth * series.length) / 2
    series.forEach((item, sIndex) => {
      // 取该系列在当前类目的值，非数字按 0 处理（缺数据不画高度）
      const value = Number(item.data?.[cIndex]) || 0
      // 柱高按值与 y 轴上限的比例换算
      const barHeight = (plotH * value) / scaleMax
      bars.push({
        // 同一类目内多根柱子依次向右排列
        x: startX + barWidth * sIndex,
        // SVG 的 y 是矩形上边缘：用绘图区底部减去柱高得到顶部坐标
        y: padT + plotH - barHeight,
        // 柱子实际宽度比分配宽度少 4px 作为间隙；下限 3px 保证极小带宽下仍可见
        w: Math.max(barWidth - 4, 3),
        h: barHeight,
        // 颜色按系列索引取，保证同一系列在所有类目颜色一致
        color: colorAt(sIndex)
      })
    })
  })
  const lines = series.map((item, sIndex) => {
    // 折线数据点：x 取类目带宽中心，y 按值比例换算
    const points = categories.map((category, cIndex) => ({
      x: padL + band * cIndex + band / 2,
      y: padT + plotH - (plotH * (Number(item.data?.[cIndex]) || 0)) / scaleMax
    }))
    // polyline 需要的点串格式："x,y x,y ..."
    const path = points.map(point => `${point.x},${point.y}`).join(' ')
    // 面积路径：从第一个点下方的 x 轴起，沿折线走一遍，再回到最后一个点下方的 x 轴并闭合；
    // 依赖 path 中“空格分隔点对”的格式，用 replace 转成 SVG 的 L 指令
    const area = points.length
      ? `M ${points[0].x} ${padT + plotH} L ${path.replace(/ /g, ' L ')} L ${points[points.length - 1].x} ${padT + plotH} Z`
      : ''
    // points 给 polyline，points2 给圆点遍历，area 给填充路径
    return { points: path, points2: points, area, color: colorAt(sIndex) }
  })
  // x 轴标签是否旋转：类目过多（>8）时横排会重叠，改为 -35° 斜排
  const rotate = categories.length > 8
  const labels = categories.map((category, index) => ({
    // 与折线数据点使用同一横向中心，保证标签对齐
    x: padL + band * index + band / 2,
    text: String(category),
    transform: rotate ? 'rotate(-35)' : 'none'
  }))
  // 汇总返回，模板只依赖这几个派生字段
  return { grid, bars, lines, labels, scaleMax }
})

// 饼图数据：只取第一个系列（饼图语义上只有一组数据），把类目名作为扇区名
const pie = computed(() => {
  const categories = props.categories || []
  // 数据项统一转数字，非数字按 0；与类目按下标一一对应
  const data = (props.series[0]?.data || []).map(value => Number(value) || 0)
  // 所有扇区数值之和，用于计算占比与角度；为 0 时后面会走“全 0 角度”分支
  const total = data.reduce((sum, value) => sum + value, 0)
  // 圆心与半径：与 500x420 的 viewBox 匹配，外半径 150、内半径 58 形成环宽
  const centerX = 250
  const centerY = 210
  const outer = 150
  const inner = 58
  // 累加角度游标：每个扇区从上一个扇区的结束角开始画
  let angle = 0
  const slices = categories.map((category, index) => {
    // 当前类目对应的数值，缺数据按 0
    const value = data[index] || 0
    // 扇区扫过角度：值/总和 × 360；总和为 0 时给 0，避免 NaN
    const sweep = total ? (value / total) * 360 : 0
    const start = angle
    const end = angle + sweep
    // 更新游标，供下一个扇区使用
    angle = end
    return {
      name: String(category),
      // 颜色按类目索引循环取色
      color: colorAt(index),
      // 百分比保留一位小数；总和为 0 时固定 '0.0'，保证图例文本稳定
      percent: total ? ((value / total) * 100).toFixed(1) : '0.0',
      // 生成环形扇区的 SVG 路径
      path: donutPath(centerX, centerY, outer, inner, start, end)
    }
  })
  // 返回给模板：扇区列表、总和、以及单扇区特例需要的半径
  return { slices, total, outer, inner }
})

// 生成环形扇区路径：由外弧（顺时针）、内弧（逆时针）拼成闭合的“弯月环”形状
// 参数均为 SVG 坐标/角度（角度 0° 在 12 点方向，因此内部减 90° 转换到数学角度）
function donutPath(cx, cy, outer, inner, start, end) {
  // 角度转弧度，并整体旋转 -90°，让 0° 从 12 点方向开始
  const toRad = degree => ((degree - 90) * Math.PI) / 180
  // 极坐标转直角坐标：给定半径和角度返回 [x, y]
  const point = (radius, degree) => [cx + radius * Math.cos(toRad(degree)), cy + radius * Math.sin(toRad(degree))]
  // SVG 弧线的 large-arc-flag：跨度超过 180° 时必须置 1，否则弧线会走短边
  const large = end - start > 180 ? 1 : 0
  // 外弧起止点
  const [ox1, oy1] = point(outer, start)
  const [ox2, oy2] = point(outer, end)
  // 内弧起止点（内弧方向相反，large 也相应反用）
  const [ix1, iy1] = point(inner, start)
  const [ix2, iy2] = point(inner, end)
  // M 外弧起点 -> A 外弧到终点 -> L 连到内弧终点 -> A 内弧回到起点 -> Z 闭合
  return `M ${ox1} ${oy1} A ${outer} ${outer} 0 ${large} 1 ${ox2} ${oy2} L ${ix2} ${iy2} A ${inner} ${inner} 0 ${large} 0 ${ix1} ${iy1} Z`
}

// 仪表盘几何：半圆从 180° 到 360°（下半圈的左右两端在圆心水平线上，形成向上拱起的半环）
const gauge = computed(() => {
  // 满量程：传入 0 时兜底 100，避免除零
  const max = props.max || 100
  // 当前值先转数字，再夹在 [0, max] 区间内，防止圆弧画到半圆之外
  const value = Math.min(Math.max(Number(props.value) || 0, 0), max)
  // 圆心与半径：与 500x320 的 viewBox 匹配，圆心略低于画布中部，给上方圆弧留空间
  const cx = 250
  const cy = 240
  const radius = 150
  // 进度终点角度：180°（左端）起算，按 value/max 最多走到 360°（右端）
  const endAngle = 180 + (180 * value) / max
  // 角度转弧度（仪表盘以数学坐标为准，无需像饼图那样减 90°）
  const toRad = degree => (degree * Math.PI) / 180
  // 进度弧终点坐标
  const endX = cx + radius * Math.cos(toRad(endAngle))
  const endY = cy + radius * Math.sin(toRad(endAngle))
  return {
    value,
    max,
    // 轨道：从左端点 A 到右端点，sweep=1 顺时针画出上半圆
    track: `M ${cx - radius} ${cy} A ${radius} ${radius} 0 0 1 ${cx + radius} ${cy}`,
    // 进度：从左端点画到按比例算出的终点
    progress: `M ${cx - radius} ${cy} A ${radius} ${radius} 0 0 1 ${endX} ${endY}`
  }
})

// 排行榜数据：只取第一个系列，生成 { name, value, percent } 并按数值降序取前 8
const rankItems = computed(() => {
  const categories = props.categories || []
  // 数值统一转数字，非数字按 0
  const values = (props.series[0]?.data || []).map(value => Number(value) || 0)
  // 基准最大值至少为 1，防止全部为 0 时除零；用最大值而非总和，表达“相对最大值的比例”
  const max = Math.max(1, ...values)
  return categories
    .map((category, index) => ({
      name: String(category),
      value: values[index] || 0,
      // 比例下限 6%：极小值也保留一条可见的短条，避免看起来像没有数据
      percent: Math.max(6, ((values[index] || 0) / max) * 100)
    }))
    // 降序排列，把最大的放最上面，符合排行榜阅读习惯
    .sort((a, b) => b.value - a.value)
    // 只展示前 8 名，避免列表过长挤出容器（样式里 overflow:hidden）
    .slice(0, 8)
})

// y 轴刻度文案：axis 的 grid 从下到上对应 0 -> scaleMax 的 5 等分，
// 传入的 index 与 grid 顺序一致，因此刻度值 = scaleMax × index / 4
function tickLabel(index) {
  const value = (axis.value.scaleMax * index) / 4
  // 四舍五入后再格式化（万级压缩/千分位），保证刻度显示为整数
  return format(Math.round(value))
}
</script>

<style scoped>
/* 图表根容器：铺满父容器；relative 让空态提示可以绝对定位覆盖其上 */
.simple-chart { position: relative; width: 100%; height: 100%; }
/* 所有 SVG 画布：宽高 100% 随容器缩放；display:block 去掉行内元素的基线留白 */
.simple-chart svg { width: 100%; height: 100%; display: block; }
/* y 轴刻度文字：12px 次级色；SVG 文本用 fill 而不是 color */
.axis-tick { font-size: 12px; fill: var(--app-text-3); }
/* x 轴类目标签：比刻度稍强一级的文字色，方便对应类目名 */
.axis-label { font-size: 12px; fill: var(--app-text-2); }
/* 饼图中心汇总数值：22px 加粗主文字色，作为环内视觉焦点 */
.pie-total { font-size: 22px; font-weight: 700; fill: var(--app-text-1); }
/* 饼图中心说明文字：12px 次级色，标注汇总值的含义 */
.pie-total-label { font-size: 12px; fill: var(--app-text-3); }
/* 仪表盘中心数值：30px 加粗，半环内只放一个主要数字，需足够醒目 */
.gauge-value { font-size: 30px; font-weight: 700; fill: var(--app-text-1); }
/* 仪表盘说明文字：13px 次级色 */
.gauge-label { font-size: 13px; fill: var(--app-text-3); }
/* 直角坐标系图例：与绘图区左边界对齐（左内边距 64px 对应 padL），项间距 18px */
.chart-legend { display: flex; gap: 18px; padding: 4px 6px 0 64px; font-size: 12px; color: var(--app-text-2); }
/* 图例单项：色点与文字垂直居中，6px 间隔 */
.legend-item { display: inline-flex; align-items: center; gap: 6px; }
/* 图例色点：8px 圆形；inline-block 保证宽高生效 */
.dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
/* 饼图容器：图形与图例左右布局，垂直居中 */
.pie-wrap { display: flex; align-items: center; height: 100%; }
/* 饼图区：固定占 58% 宽度（flex:0 0 58% 防止被图例挤压），高度铺满 */
.pie-wrap svg { width: 58%; height: 100%; flex: 0 0 58%; }
/* 饼图图例：占剩余宽度，纵向排列；右侧内边距避免贴边 */
.pie-legend { flex: 1; display: flex; flex-direction: column; gap: 10px; padding-right: 8px; font-size: 12px; color: var(--app-text-2); }
/* 单行图例：色点/名称/占比水平排列，8px 间隔 */
.legend-row { display: flex; align-items: center; gap: 8px; }
/* 图例名称：flex:1 占满并把占比推到右侧；超长名称省略号截断 */
.legend-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
/* 图例占比：主文字色 + 加粗，让数值比名称更醒目 */
.legend-value { color: var(--app-text-1); font-weight: 600; }
/* 仪表盘容器：relative 作为 0/最大值刻度的绝对定位基准 */
.gauge-wrap { position: relative; width: 100%; height: 100%; }
/* 仪表盘刻度：绝对定位在圆弧两端（左右各缩进 18%），bottom 4% 贴近圆弧端点 */
.gauge-scale { position: absolute; left: 18%; right: 18%; bottom: 4%; display: flex; justify-content: space-between; font-size: 12px; color: var(--app-text-3); }
/* 排行榜列表：纵向排列，项间距 12px；overflow:hidden 防止超出行数时溢出卡片 */
.rank-list { display: flex; flex-direction: column; gap: 12px; padding: 6px 4px; height: 100%; overflow: hidden; }
/* 排行单行：三列网格布局（名次 26px / 名称自适应 / 数值自适应），
   第二行用 grid-template-areas 把进度条横跨三列，实现“上文字下条”的结构 */
.rank-row { display: grid; grid-template-columns: 26px 1fr auto; grid-template-areas: 'no name value' 'bar bar bar'; gap: 4px 8px; align-items: center; font-size: 12px; color: var(--app-text-2); }
/* 名次序号：20px 方形圆角块，浅色底 + 加粗，作为行首视觉锚点 */
.rank-no { grid-area: no; display: inline-flex; align-items: center; justify-content: center; width: 20px; height: 20px; border-radius: 6px; background: var(--app-surface-2); color: var(--app-text-2); font-weight: 600; }
/* 前三名：用 color-mix 调出 14% 透明度的警告色底，文字用警告色，突出头部排行 */
.rank-no.top { background: color-mix(in srgb, var(--app-warning) 14%, transparent); color: var(--app-warning); }
/* 名称：省略号截断，避免长名称把比例条挤到换行 */
.rank-name { grid-area: name; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
/* 数值：主文字色 + 加粗，与名称形成主次 */
.rank-value { grid-area: value; color: var(--app-text-1); font-weight: 600; }
/* 数值单位：11px 次级色，紧跟在数值后面（em 默认斜体在模板语义中仅作小字使用，这里取消斜体） */
.rank-value em { font-style: normal; font-size: 11px; color: var(--app-text-3); margin-left: 2px; }
/* 比例条底槽：6px 高、浅色底、圆角，overflow 裁掉内部填充的圆角溢出 */
.rank-bar { grid-area: bar; height: 6px; border-radius: 3px; background: var(--app-surface-3); overflow: hidden; }
/* 比例条填充：宽度由行内 style 控制（百分比），高度铺满底槽 */
.rank-bar i { display: block; height: 100%; border-radius: 3px; }
/* 空态覆盖层：inset:0 盖住整个图表区域，居中提示“暂无数据”，避免空白图表让人误以为加载失败 */
.empty-tip { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; font-size: 13px; color: var(--app-text-3); }
</style>
