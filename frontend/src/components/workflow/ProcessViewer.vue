<!--
  文件级说明：
  职责：工作流流程流转图预览——用 bpmn-js 的只读 NavigatedViewer 渲染 BPMN XML，
        并高亮当前审批节点（蓝色）与已完成节点（绿色）。
  依赖：bpmn-js 的 NavigatedViewer 及其 diagram-js / bpmn-font 样式。
  被谁使用：workflow/WorkflowDetail.vue 的“流程图”页签。
  说明：只做只读展示（NavigatedViewer 不支持建模），节点高亮通过 canvas marker + 全局 CSS 实现。
-->
<template>
  <!-- 外层定位容器：作为空态提示的定位基准，同时保证流程图区域有最小高度 -->
  <div class="wf-process-viewer-wrap">
    <!-- bpmn-js 画布挂载点：ref 供 onMounted 时初始化 NavigatedViewer 使用；
         bpmn-js 会在该节点内部生成 svg 画布 -->
    <div ref="container" class="wf-process-viewer"></div>
    <!-- 空态：没有流程 XML 时覆盖整个区域显示提示，避免只看到一片空白画布 -->
    <div v-if="!xml" class="wf-process-empty">暂无流程定义</div>
  </div>
</template>

<script setup>
// Vue 生命周期与响应式工具：onMounted 初始化画布，onBeforeUnmount 销毁实例，
// watch 监听 xml 与节点列表变化，nextTick 等待 DOM 更新后再重绘
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
// bpmn-js 只读查看器：支持缩放/拖拽导航，但不暴露建模能力（避免误改流程定义）
import NavigatedViewer from 'bpmn-js/lib/NavigatedViewer'
// bpmn-js 画布基础样式（节点、连线等 SVG 结构的外观）
import 'bpmn-js/dist/assets/diagram-js.css'
// bpmn-js 图标字体样式（任务/事件等节点的内置图标）
import 'bpmn-js/dist/assets/bpmn-font/css/bpmn.css'

// 组件 props：
// · xml：流程定义的 BPMN XML 字符串（为空时展示空态）
// · active：当前处于激活状态的节点 id 数组（可能同一时刻存在多个并行节点）
// · completed：已审批完成的节点 id 数组
const props = defineProps({
  xml: { type: String, default: '' },
  active: { type: Array, default: () => [] },
  completed: { type: Array, default: () => [] }
})

// bpmn-js 的挂载容器 DOM 引用
const container = ref(null)
// NavigatedViewer 实例（非响应式，避免 Vue 代理 bpmn-js 内部复杂对象导致性能与引用问题）
let viewer = null
// 上一次打过高亮的节点 id 集合：用于下次更新前精确清除旧 marker，避免样式残留
let marked = []

// 把 props 中的节点状态同步到 bpmn 画布：
// 1) 先清除上一次所有高亮；2) 已完成的节点标绿（若同时激活则不重复标绿，以激活态为准）；3) 激活节点标蓝
function applyMarkers() {
  // 画布尚未初始化时直接返回，防止调用 canvas API 报错
  if (!viewer) return
  // 通过 bpmn-js 依赖注入拿到 canvas 实例
  const canvas = viewer.get('canvas')
  // 清除旧的“已完成”与“激活”标记
  marked.forEach(id => canvas.removeMarker(id, 'wf-done-node'))
  marked.forEach(id => canvas.removeMarker(id, 'wf-active-node'))
  // active 转 Set 用于快速判断“某节点是否同时处于激活态”
  const activeSet = new Set(props.active || [])
  // 已完成节点：跳过空 id，且跳过仍在激活中的节点（激活优先展示蓝色）
  ;(props.completed || []).forEach(id => {
    if (id && !activeSet.has(id)) canvas.addMarker(id, 'wf-done-node')
  })
  // 激活节点：统一加蓝色 marker
  ;(props.active || []).forEach(id => {
    if (id) canvas.addMarker(id, 'wf-active-node')
  })
  // 记录本次已标记的节点集合（去重），供下一次清除使用
  marked = [...new Set([...(props.completed || []), ...(props.active || [])])]
}

// 渲染（或重新渲染）流程图：
// importXML 是异步的，需要等待解析完成后再调整缩放与高亮
async function render() {
  // 未初始化或没有 xml 时不做任何事（空态由模板负责）
  if (!viewer || !props.xml) return
  try {
    // 导入 BPMN XML：bpmn-js 会重建内部元素与画布
    await viewer.importXML(props.xml)
    // 等待 Vue 完成一次 DOM 更新，确保容器尺寸已稳定
    await nextTick()
    resize()
    applyMarkers()
  } catch (e) {
    // 流程定义异常时不阻断详情查看，页面保持空白并提示在控制台
    console.warn('BPMN 渲染失败', e)
  }
}

// 自适应缩放：让整张流程图完整显示在可视区域内
function resize() {
  if (!viewer) return
  try {
    viewer.get('canvas').zoom('fit-viewport')
  } catch (e) {
    // 容器尺寸为 0 时忽略
  }
}

// 挂载时初始化只读查看器，并立即渲染一次：
// 注意 container.value 必须已存在，因此放在 onMounted 而不是 setup 顶层
onMounted(() => {
  viewer = new NavigatedViewer({ container: container.value })
  render()
  // 延迟 120ms 再 fit-viewport：抽屉/弹窗打开时容器高度可能尚未最终确定，立即缩放会算错比例
  setTimeout(resize, 120)
})

// xml 变化（切换到另一个流程实例）时整体重新导入并渲染
watch(() => props.xml, render)
// 节点状态变化时只需重打 marker，无需重新导入 XML；deep 监听数组内部变化
watch(() => [props.active, props.completed], applyMarkers, { deep: true })

// 卸载前销毁 viewer，释放其内部事件监听与 DOM，避免内存泄漏
onBeforeUnmount(() => {
  if (viewer) viewer.destroy()
  viewer = null
})

// 对外暴露 resize，供父组件在容器尺寸变化（如抽屉宽度调整）后手动重新适配
defineExpose({ resize })
</script>

<style scoped>
/* 外层容器：relative 作为空态绝对定位的基准；高度继承父级，并用 min-height 保证画布有可用空间 */
.wf-process-viewer-wrap {
  position: relative;
  height: 100%;
  min-height: 320px;
}
/* bpmn-js 画布挂载点：铺满外层；min-height 与外层一致，防止父级未给高度时画布塌陷 */
.wf-process-viewer {
  width: 100%;
  height: 100%;
  min-height: 320px;
}
/* 空态层：inset:0 覆盖整个区域，flex 居中提示文字；使用次级文字色，避免看起来像报错 */
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
/* 激活节点：Element Plus 主色蓝描边 + 浅蓝填充；!important 用于覆盖 bpmn-js 内联的 SVG 属性；
   选择 .djs-visual 的第一个子元素，即节点图形本体（不含外部标签） */
.wf-active-node .djs-visual > :nth-child(1) {
  stroke: #409eff !important;
  stroke-width: 2.5px !important;
  fill: #ecf5ff !important;
}
/* 已完成节点：成功绿描边 + 浅绿填充；描边略细于激活节点，形成“进行中 > 已完成”的视觉强弱 */
.wf-done-node .djs-visual > :nth-child(1) {
  stroke: #67c23a !important;
  stroke-width: 2px !important;
  fill: #f0f9eb !important;
}
</style>
