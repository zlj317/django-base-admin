<template>
  <!-- ============================================================
       组件：首页分布条（文件类型 / 告警级别等横向占比）
       职责：把一组 { label, count, color } 渲染成横向进度条列表。
       依赖：无第三方库；颜色由父组件传入主题变量，缺省按 --chart-* 轮转。
       ============================================================ -->
  <div class="dist-bar">
    <!-- 逐项渲染：label 左、进度条中、数值右 -->
    <div v-for="(item, i) in items" :key="item.label + i" class="dist-row">
      <!-- 左侧名称：超出省略，避免长文件名把进度条挤没 -->
      <span class="dist-label" :title="item.label">{{ item.label }}</span>
      <!-- 中间轨道：灰色底槽，内部填充条宽度 = 占比 -->
      <div class="dist-track">
        <div
          class="dist-fill"
          :style="{ width: widthOf(item) + '%', background: colorOf(item, i) }"
        ></div>
      </div>
      <!-- 右侧数值：等宽数字，避免刷新时宽度跳动 -->
      <span class="dist-value">{{ item.count }}</span>
    </div>
    <!-- 空数据提示：说明该维度暂无记录，而不是留白 -->
    <div v-if="!items.length" class="dist-empty">暂无数据</div>
  </div>
</template>

<script setup>
// ============================================================
// 脚本：计算每项的相对占比与配色。
// 数据流：props.items → 每行 width %；无副作用。
// ============================================================
// 组件属性：items 为数据数组，unit 仅用于说明（当前不显示单位）
const props = defineProps({
  // 数据项：label 名称、count 数值、color 可选（CSS 颜色/变量）
  items: { type: Array, default: () => [] }
})

// 最大计数：作为分母，至少为 1，避免全 0 时出现 NaN
function maxCount() {
  // map 取所有 count，Math.max 取最大；空数组时给出 1
  return Math.max(1, ...props.items.map(it => Number(it.count) || 0))
}

// 计算单项占比：最大项固定 100%，其余按比例缩放，视觉上更容易比较
function widthOf(item) {
  // 数值兜底为 0
  const value = Number(item.count) || 0
  // 百分比保留 1 位小数；为 0 时返回 0（不显示一点点色块）
  return value > 0 ? Math.max(2, Math.round((value / maxCount()) * 1000) / 10) : 0
}

// 计算单项颜色：优先用数据项自带的 color，否则按索引轮转主题图表色
function colorOf(item, index) {
  // 主题图表色共 6 个（--chart-1..6），用取模保证索引不越界
  return item.color || `var(--chart-${(index % 6) + 1})`
}
</script>

<style scoped>
/* 容器：纵向排列，行间距 8px */
.dist-bar {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
}

/* 单行：名称 72px + 自适应轨道 + 数值 36px */
.dist-row {
  display: grid;
  grid-template-columns: 72px 1fr 36px;
  align-items: center;
  gap: 10px;
}

/* 名称：小号次级文字，单行省略 */
.dist-label {
  font-size: 12px;
  color: var(--app-text-2);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 轨道：8px 高的浅色底槽，圆角 */
.dist-track {
  height: 8px;
  border-radius: 6px;
  background: var(--app-surface-2);
  overflow: hidden;
}

/* 填充条：高度占满轨道，圆角与轨道一致；宽度与背景由行内样式注入 */
.dist-fill {
  height: 100%;
  border-radius: 6px;
  transition: width 0.4s ease;
}

/* 数值：右对齐、等宽数字、弱化色 */
.dist-value {
  font-size: 12px;
  color: var(--app-text-3);
  text-align: right;
  font-variant-numeric: tabular-nums;
}

/* 空数据：弱化文字，保持行高与卡片节奏一致 */
.dist-empty {
  padding: 8px 0;
  font-size: 12px;
  color: var(--app-text-3);
}
</style>
