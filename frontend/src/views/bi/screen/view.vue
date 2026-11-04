<template>
  <div class="screen-page" ref="pageRef">
    <div class="screen-topbar">
      <div class="tb-left">
        <span class="tb-back" @click="goBack">‹ 返回</span>
        <span class="tb-name">{{ viewData.screen_name || '大屏预览' }}</span>
        <el-tag v-if="viewData.status === 0" size="small" effect="dark" type="warning">草稿</el-tag>
        <el-tag v-else-if="viewData.status === 2" size="small" effect="dark" type="info">已下线</el-tag>
      </div>
      <div class="tb-right">
        <span class="tb-clock">{{ clock }}</span>
        <span v-if="refreshSec" class="tb-refresh">自动刷新 {{ refreshSec }}s</span>
        <span class="tb-btn" @click="loadData(false)">刷新数据</span>
        <span class="tb-btn" @click="toggleFullscreen">{{ isFullscreen ? '退出全屏' : '全屏展示' }}</span>
      </div>
    </div>

    <div ref="stageRef" class="screen-stage" v-loading="loading" element-loading-background="rgba(4, 12, 28, 0.8)">
      <div class="screen-canvas" :style="canvasStyle">
        <div class="canvas-title">
          <span class="canvas-title-text">{{ viewData.screen_name }}</span>
          <span class="canvas-title-sub">数据更新时间 {{ viewData.updated_at || '-' }}</span>
        </div>
        <div v-for="widget in viewData.widgets || []" :key="widget.id" class="widget" :style="widgetStyle(widget)">
          <div class="widget-head">
            <span class="widget-title">{{ widget.title }}</span>
            <span class="widget-sub">{{ widget.data.dataset_name || widget.subtitle }}</span>
          </div>
          <div class="widget-body">
            <div v-if="widget.type === 'kpi'" class="kpi-box">
              <div class="kpi-value">{{ formatNumber(widget.data.value) }}<em>{{ widget.unit || widget.data.unit }}</em></div>
              <div class="kpi-label">{{ widget.title }}</div>
            </div>
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
            <div v-else-if="widget.type === 'text'" class="text-box">{{ widget.data.text }}</div>
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
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import request from '@/utils/request'
import SimpleChart from '@/components/chart/SimpleChart.vue'

const route = useRoute()
const router = useRouter()
const pageRef = ref()
const stageRef = ref()
const isShare = computed(() => route.name === 'BiScreenShare')

const loading = ref(false)
const viewData = ref({})
const scale = ref(1)
const clock = ref('')
const isFullscreen = ref(false)
const refreshSec = computed(() => Number(viewData.value.refresh_sec) || 0)

let clockTimer = null
let refreshTimer = null
let observer = null

const canvasStyle = computed(() => ({
  width: `${viewData.value.width || 1920}px`,
  height: `${viewData.value.height || 1080}px`,
  background: viewData.value.background || undefined,
  transform: `translate(-50%, -50%) scale(${scale.value})`
}))

function widgetStyle(widget) {
  return {
    left: `${widget.x}px`, top: `${widget.y}px`,
    width: `${widget.w}px`, height: `${widget.h}px`
  }
}

function formatNumber(value) {
  const number = Number(value) || 0
  if (Math.abs(number) >= 10000) return (number / 10000).toFixed(1) + '万'
  return number.toLocaleString('zh-CN')
}

function updateClock() {
  const now = new Date()
  const week = ['日', '一', '二', '三', '四', '五', '六'][now.getDay()]
  const pad = num => String(num).padStart(2, '0')
  clock.value = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())} `
    + `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())} 星期${week}`
}

function fitCanvas() {
  const stage = stageRef.value
  if (!stage) return
  const width = viewData.value.width || 1920
  const height = viewData.value.height || 1080
  scale.value = Math.min(stage.clientWidth / width, stage.clientHeight / height) || 1
}

async function loadData(showLoading = true) {
  const silent = !showLoading
  if (!silent) loading.value = true
  try {
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

function setupRefresh() {
  if (refreshTimer) clearInterval(refreshTimer)
  refreshTimer = null
  if (refreshSec.value > 0) {
    refreshTimer = setInterval(() => loadData(false), refreshSec.value * 1000)
  }
}

function toggleFullscreen() {
  if (!document.fullscreenElement) {
    pageRef.value?.requestFullscreen?.().catch(() => {})
  } else {
    document.exitFullscreen?.().catch(() => {})
  }
}

function syncFullscreenState() {
  isFullscreen.value = Boolean(document.fullscreenElement)
  fitCanvas()
}

function goBack() {
  if (isShare.value) {
    router.push('/dashboard')
    return
  }
  const canBack = window.history.length > 1
  if (canBack) router.back()
  else router.push('/bi')
}

onMounted(() => {
  updateClock()
  clockTimer = setInterval(updateClock, 1000)
  loadData(true)
  observer = new ResizeObserver(fitCanvas)
  if (stageRef.value) observer.observe(stageRef.value)
  document.addEventListener('fullscreenchange', syncFullscreenState)
  window.addEventListener('resize', fitCanvas)
})

onBeforeUnmount(() => {
  clearInterval(clockTimer)
  clearInterval(refreshTimer)
  observer?.disconnect()
  document.removeEventListener('fullscreenchange', syncFullscreenState)
  window.removeEventListener('resize', fitCanvas)
})
</script>

<style scoped>
.screen-page {
  position: fixed;
  inset: 0;
  display: flex;
  flex-direction: column;
  color: #e8f1ff;
  background: radial-gradient(circle at 50% 0%, #16305f 0%, #0a1730 46%, #050d1c 100%);
}
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
.tb-left, .tb-right { display: flex; align-items: center; gap: 14px; }
.tb-back, .tb-btn {
  font-size: 13px;
  color: #8fc4ff;
  cursor: pointer;
  padding: 5px 12px;
  border: 1px solid rgba(78, 168, 255, 0.32);
  border-radius: 6px;
  transition: all 0.2s ease;
}
.tb-back:hover, .tb-btn:hover { color: #fff; background: rgba(78, 168, 255, 0.18); }
.tb-name { font-size: 16px; font-weight: 600; letter-spacing: 1px; }
.tb-clock { font-size: 13px; color: rgba(206, 226, 255, 0.72); letter-spacing: 0.5px; }
.tb-refresh { font-size: 12px; color: #2ee6a8; }
.screen-stage { position: relative; flex: 1; overflow: hidden; }
.screen-canvas {
  position: absolute;
  left: 50%;
  top: 50%;
  transform-origin: center center;
  background-image: linear-gradient(rgba(78, 168, 255, 0.06) 1px, transparent 1px),
    linear-gradient(90deg, rgba(78, 168, 255, 0.06) 1px, transparent 1px);
  background-size: 48px 48px;
}
.screen-canvas::before {
  content: '';
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at 50% 0%, rgba(32, 88, 190, 0.28), transparent 62%);
  pointer-events: none;
}
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
.canvas-title-text {
  font-size: 28px;
  font-weight: 700;
  letter-spacing: 6px;
  color: #dceeff;
  text-shadow: 0 0 18px rgba(78, 168, 255, 0.65);
}
.canvas-title-sub { font-size: 12px; color: rgba(206, 226, 255, 0.55); }
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
.widget-head { display: flex; align-items: baseline; justify-content: space-between; gap: 10px; padding-bottom: 8px; }
.widget-title { font-size: 15px; font-weight: 600; color: #cfe6ff; letter-spacing: 1px; }
.widget-sub { font-size: 11px; color: rgba(206, 226, 255, 0.45); }
.widget-body { position: relative; flex: 1; min-height: 0; }
.kpi-box { display: flex; flex-direction: column; justify-content: center; height: 100%; }
.kpi-value { font-size: 42px; font-weight: 700; color: #4ea8ff; text-shadow: 0 0 18px rgba(78, 168, 255, 0.5); }
.kpi-value em { margin-left: 6px; font-style: normal; font-size: 14px; color: rgba(206, 226, 255, 0.6); font-weight: 500; }
.kpi-label { margin-top: 8px; font-size: 13px; color: rgba(206, 226, 255, 0.55); }
.table-box { height: 100%; overflow: auto; }
.data-table { width: 100%; border-collapse: collapse; font-size: 12px; color: #cfe6ff; }
.data-table th { position: sticky; top: 0; padding: 7px 10px; font-weight: 600; text-align: left; color: #8fc4ff; background: rgba(28, 62, 122, 0.9); border-bottom: 1px solid rgba(78, 168, 255, 0.25); }
.data-table td { padding: 7px 10px; color: rgba(206, 226, 255, 0.82); border-bottom: 1px dashed rgba(78, 168, 255, 0.14); }
.data-table tbody tr:hover td { background: rgba(78, 168, 255, 0.08); }
.text-box { display: flex; align-items: center; height: 100%; font-size: 14px; line-height: 1.9; color: rgba(206, 226, 255, 0.78); }
</style>
