<template>
  <div class="wf-process-viewer-wrap">
    <div ref="container" class="wf-process-viewer"></div>
    <div v-if="!xml" class="wf-process-empty">暂无流程定义</div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import NavigatedViewer from 'bpmn-js/lib/NavigatedViewer'
import 'bpmn-js/dist/assets/diagram-js.css'
import 'bpmn-js/dist/assets/bpmn-font/css/bpmn.css'

const props = defineProps({
  xml: { type: String, default: '' },
  active: { type: Array, default: () => [] },
  completed: { type: Array, default: () => [] }
})

const container = ref(null)
let viewer = null
let marked = []

function applyMarkers() {
  if (!viewer) return
  const canvas = viewer.get('canvas')
  marked.forEach(id => canvas.removeMarker(id, 'wf-done-node'))
  marked.forEach(id => canvas.removeMarker(id, 'wf-active-node'))
  const activeSet = new Set(props.active || [])
  ;(props.completed || []).forEach(id => {
    if (id && !activeSet.has(id)) canvas.addMarker(id, 'wf-done-node')
  })
  ;(props.active || []).forEach(id => {
    if (id) canvas.addMarker(id, 'wf-active-node')
  })
  marked = [...new Set([...(props.completed || []), ...(props.active || [])])]
}

async function render() {
  if (!viewer || !props.xml) return
  try {
    await viewer.importXML(props.xml)
    await nextTick()
    resize()
    applyMarkers()
  } catch (e) {
    // 流程定义异常时不阻断详情查看，页面保持空白并提示在控制台
    console.warn('BPMN 渲染失败', e)
  }
}

function resize() {
  if (!viewer) return
  try {
    viewer.get('canvas').zoom('fit-viewport')
  } catch (e) {
    // 容器尺寸为 0 时忽略
  }
}

onMounted(() => {
  viewer = new NavigatedViewer({ container: container.value })
  render()
  setTimeout(resize, 120)
})

watch(() => props.xml, render)
watch(() => [props.active, props.completed], applyMarkers, { deep: true })

onBeforeUnmount(() => {
  if (viewer) viewer.destroy()
  viewer = null
})

defineExpose({ resize })
</script>

<style scoped>
.wf-process-viewer-wrap {
  position: relative;
  height: 100%;
  min-height: 320px;
}
.wf-process-viewer {
  width: 100%;
  height: 100%;
  min-height: 320px;
}
.wf-process-empty {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--el-text-color-secondary);
}
</style>

<style>
/* 当前节点/已完成节点的画布高亮（非 scoped，bpmn-js 动态添加的类名需要全局生效） */
.wf-active-node .djs-visual > :nth-child(1) {
  stroke: #409eff !important;
  stroke-width: 2.5px !important;
  fill: #ecf5ff !important;
}
.wf-done-node .djs-visual > :nth-child(1) {
  stroke: #67c23a !important;
  stroke-width: 2px !important;
  fill: #f0f9eb !important;
}
</style>
