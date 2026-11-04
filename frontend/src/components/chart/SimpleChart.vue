<template>
  <div class="simple-chart" :class="{ dark }" :style="{ '--chart-hole': dark ? '#0d1f3f' : '#ffffff' }">
    <div v-if="type === 'rank'" class="rank-list">
      <div v-for="(item, index) in rankItems" :key="item.name" class="rank-row">
        <span class="rank-no" :class="{ top: index < 3 }">{{ index + 1 }}</span>
        <span class="rank-name" :title="item.name">{{ item.name }}</span>
        <span class="rank-value">{{ format(item.value) }}<em v-if="unit">{{ unit }}</em></span>
        <div class="rank-bar"><i :style="{ width: item.percent + '%', background: colorAt(0) }"></i></div>
      </div>
    </div>

    <div v-else-if="type === 'gauge'" class="gauge-wrap">
      <svg viewBox="0 0 500 320" preserveAspectRatio="xMidYMid meet">
        <path :d="gauge.track" fill="none" :stroke="trackColor" stroke-width="18" stroke-linecap="round" />
        <path :d="gauge.progress" fill="none" :stroke="colorAt(2)" stroke-width="18" stroke-linecap="round" />
        <text x="250" y="228" text-anchor="middle" class="gauge-value">{{ format(gauge.value) }}</text>
        <text x="250" y="256" text-anchor="middle" class="gauge-label">{{ unit || '完成率' }}</text>
      </svg>
      <div class="gauge-scale">
        <span>0</span>
        <span>{{ format(gauge.max) }}</span>
      </div>
    </div>

    <div v-else-if="type === 'pie'" class="pie-wrap">
      <svg viewBox="0 0 500 420" preserveAspectRatio="xMidYMid meet">
        <template v-if="pie.slices.length === 1">
          <circle cx="250" cy="210" :r="pie.outer" :fill="colorAt(0)" />
          <circle cx="250" cy="210" :r="pie.inner" fill="var(--chart-hole, #fff)" />
        </template>
        <template v-else>
          <path v-for="slice in pie.slices" :key="slice.name" :d="slice.path"
            :fill="slice.color" stroke="transparent" stroke-width="2" />
        </template>
        <text x="250" y="204" text-anchor="middle" class="pie-total">{{ format(pie.total) }}</text>
        <text x="250" y="228" text-anchor="middle" class="pie-total-label">{{ unit || '总量' }}</text>
      </svg>
      <div class="pie-legend">
        <div v-for="slice in pie.slices" :key="slice.name" class="legend-row">
          <i class="dot" :style="{ background: slice.color }"></i>
          <span class="legend-name" :title="slice.name">{{ slice.name }}</span>
          <span class="legend-value">{{ slice.percent }}%</span>
        </div>
      </div>
    </div>

    <div v-else class="axis-wrap">
      <div class="chart-legend">
        <span v-for="(item, index) in series" :key="item.name" class="legend-item">
          <i class="dot" :style="{ background: colorAt(index) }"></i>{{ item.name }}
        </span>
      </div>
      <svg :viewBox="`0 0 1000 ${height}`" preserveAspectRatio="xMidYMid meet">
        <line v-for="(y, index) in axis.grid" :key="'g' + index" x1="64" :y1="y" x2="976" :y2="y"
          :stroke="gridColor" stroke-width="1" />
        <text v-for="(y, index) in axis.grid" :key="'t' + index" x="56" :y="y + 4" text-anchor="end"
          class="axis-tick">{{ tickLabel(index) }}</text>
        <template v-if="type === 'line'">
          <template v-for="(item, index) in axis.lines" :key="'l' + index">
            <path :d="item.area" :fill="item.color" opacity="0.12" />
            <polyline :points="item.points" fill="none" :stroke="item.color" stroke-width="3" stroke-linejoin="round" />
            <circle v-for="(point, pIndex) in item.points2" :key="'c' + index + '-' + pIndex"
              :cx="point.x" :cy="point.y" r="4" :fill="item.color" />
          </template>
        </template>
        <template v-else>
          <rect v-for="(bar, index) in axis.bars" :key="'b' + index" :x="bar.x" :y="bar.y"
            :width="bar.w" :height="bar.h" :fill="bar.color" rx="4" />
        </template>
        <text v-for="(label, index) in axis.labels" :key="'x' + index" :x="label.x" :y="height - 16"
          text-anchor="middle" class="axis-label" :transform="label.transform">{{ label.text }}</text>
      </svg>
    </div>
    <div v-if="!categories.length && !series.length" class="empty-tip">暂无数据</div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

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

const LIGHT_COLORS = ['#4a6cf7', '#12b76a', '#f79009', '#8b5cf6', '#0ea5e9', '#ef4444']
const DARK_COLORS = ['#4ea8ff', '#2ee6a8', '#ffc53d', '#a78bfa', '#ff7a45', '#4ade80']
const WIDTH = 1000

const colors = computed(() => (props.dark ? DARK_COLORS : LIGHT_COLORS))
const gridColor = computed(() => (props.dark ? 'rgba(120, 170, 255, 0.16)' : '#eef1f6'))
const trackColor = computed(() => (props.dark ? 'rgba(120, 170, 255, 0.16)' : '#eef1f6'))

function colorAt(index) {
  return colors.value[index % colors.value.length]
}

function format(value) {
  const num = Number(value) || 0
  if (Math.abs(num) >= 10000) return (num / 10000).toFixed(1) + '万'
  return num.toLocaleString('zh-CN')
}

function niceCeil(value) {
  if (value <= 0) return 1
  const magnitude = Math.pow(10, Math.floor(Math.log10(value)))
  const steps = [1, 2, 2.5, 4, 5, 10]
  const target = value / magnitude
  const step = steps.find(item => item >= target) || 10
  return step * magnitude
}

// 柱状图/折线图几何：统一坐标区，保证同一页面多个图表视觉一致
const axis = computed(() => {
  const categories = props.categories || []
  const series = props.series || []
  const height = props.height
  const padL = 64
  const padR = 24
  const padT = 18
  const padB = 46
  const plotW = WIDTH - padL - padR
  const plotH = height - padT - padB
  const maxValue = Math.max(1, ...series.flatMap(item => (item.data || []).map(v => Number(v) || 0)))
  const scaleMax = niceCeil(maxValue)
  const grid = [0, 1, 2, 3, 4].map(index => padT + plotH - (plotH * index) / 4)
  const band = categories.length ? plotW / categories.length : plotW
  const barWidth = Math.min(46, (band * 0.66) / Math.max(1, series.length))
  const bars = []
  categories.forEach((category, cIndex) => {
    const startX = padL + band * cIndex + (band - barWidth * series.length) / 2
    series.forEach((item, sIndex) => {
      const value = Number(item.data?.[cIndex]) || 0
      const barHeight = (plotH * value) / scaleMax
      bars.push({
        x: startX + barWidth * sIndex,
        y: padT + plotH - barHeight,
        w: Math.max(barWidth - 4, 3),
        h: barHeight,
        color: colorAt(sIndex)
      })
    })
  })
  const lines = series.map((item, sIndex) => {
    const points = categories.map((category, cIndex) => ({
      x: padL + band * cIndex + band / 2,
      y: padT + plotH - (plotH * (Number(item.data?.[cIndex]) || 0)) / scaleMax
    }))
    const path = points.map(point => `${point.x},${point.y}`).join(' ')
    const area = points.length
      ? `M ${points[0].x} ${padT + plotH} L ${path.replace(/ /g, ' L ')} L ${points[points.length - 1].x} ${padT + plotH} Z`
      : ''
    return { points: path, points2: points, area, color: colorAt(sIndex) }
  })
  const rotate = categories.length > 8
  const labels = categories.map((category, index) => ({
    x: padL + band * index + band / 2,
    text: String(category),
    transform: rotate ? 'rotate(-35)' : 'none'
  }))
  return { grid, bars, lines, labels, scaleMax }
})

const pie = computed(() => {
  const categories = props.categories || []
  const data = (props.series[0]?.data || []).map(value => Number(value) || 0)
  const total = data.reduce((sum, value) => sum + value, 0)
  const centerX = 250
  const centerY = 210
  const outer = 150
  const inner = 58
  let angle = 0
  const slices = categories.map((category, index) => {
    const value = data[index] || 0
    const sweep = total ? (value / total) * 360 : 0
    const start = angle
    const end = angle + sweep
    angle = end
    return {
      name: String(category),
      color: colorAt(index),
      percent: total ? ((value / total) * 100).toFixed(1) : '0.0',
      path: donutPath(centerX, centerY, outer, inner, start, end)
    }
  })
  return { slices, total, outer, inner }
})

function donutPath(cx, cy, outer, inner, start, end) {
  const toRad = degree => ((degree - 90) * Math.PI) / 180
  const point = (radius, degree) => [cx + radius * Math.cos(toRad(degree)), cy + radius * Math.sin(toRad(degree))]
  const large = end - start > 180 ? 1 : 0
  const [ox1, oy1] = point(outer, start)
  const [ox2, oy2] = point(outer, end)
  const [ix1, iy1] = point(inner, start)
  const [ix2, iy2] = point(inner, end)
  return `M ${ox1} ${oy1} A ${outer} ${outer} 0 ${large} 1 ${ox2} ${oy2} L ${ix2} ${iy2} A ${inner} ${inner} 0 ${large} 0 ${ix1} ${iy1} Z`
}

const gauge = computed(() => {
  const max = props.max || 100
  const value = Math.min(Math.max(Number(props.value) || 0, 0), max)
  const cx = 250
  const cy = 240
  const radius = 150
  const endAngle = 180 + (180 * value) / max
  const toRad = degree => (degree * Math.PI) / 180
  const endX = cx + radius * Math.cos(toRad(endAngle))
  const endY = cy + radius * Math.sin(toRad(endAngle))
  return {
    value,
    max,
    track: `M ${cx - radius} ${cy} A ${radius} ${radius} 0 0 1 ${cx + radius} ${cy}`,
    progress: `M ${cx - radius} ${cy} A ${radius} ${radius} 0 0 1 ${endX} ${endY}`
  }
})

const rankItems = computed(() => {
  const categories = props.categories || []
  const values = (props.series[0]?.data || []).map(value => Number(value) || 0)
  const max = Math.max(1, ...values)
  return categories
    .map((category, index) => ({
      name: String(category),
      value: values[index] || 0,
      percent: Math.max(6, ((values[index] || 0) / max) * 100)
    }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 8)
})

function tickLabel(index) {
  const value = (axis.value.scaleMax * index) / 4
  return format(Math.round(value))
}
</script>

<style scoped>
.simple-chart { position: relative; width: 100%; height: 100%; }
.simple-chart svg { width: 100%; height: 100%; display: block; }
.axis-tick { font-size: 12px; fill: #98a2b3; }
.axis-label { font-size: 12px; fill: #667085; }
.pie-total { font-size: 22px; font-weight: 700; fill: #1f2937; }
.pie-total-label { font-size: 12px; fill: #98a2b3; }
.gauge-value { font-size: 30px; font-weight: 700; fill: #1f2937; }
.gauge-label { font-size: 13px; fill: #98a2b3; }
.chart-legend { display: flex; gap: 18px; padding: 4px 6px 0 64px; font-size: 12px; color: #667085; }
.legend-item { display: inline-flex; align-items: center; gap: 6px; }
.dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
.pie-wrap { display: flex; align-items: center; height: 100%; }
.pie-wrap svg { width: 58%; height: 100%; flex: 0 0 58%; }
.pie-legend { flex: 1; display: flex; flex-direction: column; gap: 10px; padding-right: 8px; font-size: 12px; color: #667085; }
.legend-row { display: flex; align-items: center; gap: 8px; }
.legend-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.legend-value { color: #1f2937; font-weight: 600; }
.gauge-wrap { position: relative; width: 100%; height: 100%; }
.gauge-scale { position: absolute; left: 18%; right: 18%; bottom: 4%; display: flex; justify-content: space-between; font-size: 12px; color: #98a2b3; }
.rank-list { display: flex; flex-direction: column; gap: 12px; padding: 6px 4px; height: 100%; overflow: hidden; }
.rank-row { display: grid; grid-template-columns: 26px 1fr auto; grid-template-areas: 'no name value' 'bar bar bar'; gap: 4px 8px; align-items: center; font-size: 12px; color: #667085; }
.rank-no { grid-area: no; display: inline-flex; align-items: center; justify-content: center; width: 20px; height: 20px; border-radius: 6px; background: #eef1f6; color: #667085; font-weight: 600; }
.rank-no.top { background: #fff4e5; color: #f79009; }
.rank-name { grid-area: name; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.rank-value { grid-area: value; color: #1f2937; font-weight: 600; }
.rank-value em { font-style: normal; font-size: 11px; color: #98a2b3; margin-left: 2px; }
.rank-bar { grid-area: bar; height: 6px; border-radius: 3px; background: #f2f4f7; overflow: hidden; }
.rank-bar i { display: block; height: 100%; border-radius: 3px; }
.empty-tip { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; font-size: 13px; color: #98a2b3; }
.simple-chart.dark .axis-tick,
.simple-chart.dark .axis-label { fill: rgba(206, 226, 255, 0.62); }
.simple-chart.dark .pie-total,
.simple-chart.dark .gauge-value,
.simple-chart.dark .legend-value,
.simple-chart.dark .rank-value { color: #e8f1ff; fill: #e8f1ff; }
.simple-chart.dark .pie-total-label,
.simple-chart.dark .gauge-label,
.simple-chart.dark .gauge-scale,
.simple-chart.dark .chart-legend,
.simple-chart.dark .pie-legend,
.simple-chart.dark .rank-row { color: rgba(206, 226, 255, 0.62); }
.simple-chart.dark .rank-no { background: rgba(78, 168, 255, 0.14); color: rgba(206, 226, 255, 0.8); }
.simple-chart.dark .rank-bar { background: rgba(78, 168, 255, 0.12); }
</style>
