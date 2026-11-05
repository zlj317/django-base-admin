<!--
  文件级说明：
  职责：全局外观设置面板——切换明暗模式、选择品牌主题色，并把选择持久化到本地。
  依赖：@arco-design/web-vue 的 Popover/RadioGroup/Radio（仅本组件使用 Arco，其余界面为 Element Plus）、
        @/theme（PALETTES 调色板、themeState 当前主题状态、setMode/setPalette 写入并应用主题）。
  被谁使用：layout/components/Navbar.vue 顶栏右侧。
  说明：主题的实际应用与 localStorage 持久化都在 @/theme 内完成，本组件只负责交互层。
-->
<template>
  <!-- 触发式弹层：点击触发、位置在按钮右下（br）；content-style 去掉默认内边距，
       让面板内容可以自行控制留白 -->
  <Popover trigger="click" position="br" :content-style="{ padding: '0' }">
    <!-- 触发按钮：34px 方形无边框按钮；aria-label 与 title 提供无障碍名称与悬浮提示 -->
    <button class="theme-trigger" type="button" aria-label="主题设置" title="主题设置">
      <!-- 用内联 SVG 图标，避免额外图标包体积 -->
      <!-- 暗色模式下显示“太阳”图标：表示当前处于深色，点击可切回浅色（图标语义为可执行的动作） -->
      <svg v-if="isDark" viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
        <path d="M12 2a1 1 0 0 1 1 1v1.5a1 1 0 1 1-2 0V3a1 1 0 0 1 1-1Zm0 17a6 6 0 1 0 0-12 6 6 0 0 0 0 12Zm0 1.5v1.5a1 1 0 1 1-2 0V21a1 1 0 1 1 2 0ZM2 12a1 1 0 0 1 1-1h1.5a1 1 0 1 1 0 2H3a1 1 0 0 1-1-1Zm17 0a1 1 0 0 1 1-1h1.5a1 1 0 1 1 0 2H20a1 1 0 0 1-1-1ZM4.9 4.9a1 1 0 0 1 1.4 0l1 1a1 1 0 1 1-1.4 1.4l-1-1a1 1 0 0 1 0-1.4Zm13.2 13.2a1 1 0 0 1 1.4 0l1 1a1 1 0 1 1-1.4 1.4l-1-1a1 1 0 0 1 0-1.4Zm2.4-13.2a1 1 0 0 1 0 1.4l-1 1a1 1 0 1 1-1.4-1.4l1-1a1 1 0 0 1 1.4 0ZM6.3 16.7a1 1 0 0 1 0 1.4l-1 1a1 1 0 1 1-1.4-1.4l1-1a1 1 0 0 1 1.4 0Z" />
      </svg>
      <!-- 浅色模式下显示“月亮”图标：点击进入深色模式；与上面的太阳图标构成互斥状态 -->
      <svg v-else viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
        <path d="M20.7 14.2a1 1 0 0 0-1.2-1.2 7 7 0 0 1-8.4-8.4A1 1 0 0 0 9.9 3.4a9 9 0 1 0 10.8 10.8Z" />
      </svg>
    </button>
    <!-- 弹层内容插槽：固定宽度的设置面板，分“外观模式”与“主题色”两段 -->
    <template #content>
      <div class="theme-panel">
        <!-- 第一段：明暗模式 -->
        <div class="theme-section">
          <!-- 小节标题：小字号弱化颜色，只作分区说明 -->
          <div class="theme-label">外观模式</div>
          <!-- 分段按钮组：v-model 绑定可写计算属性 mode，选中即调用 setMode 应用并持久化；
               type=button 使用按钮样式，size=small 与面板紧凑布局匹配 -->
          <RadioGroup v-model="mode" type="button" size="small" class="mode-group">
            <!-- 浅色模式选项：value 必须与 themeState.mode 的取值（'light'/'dark'）一致 -->
            <Radio value="light">浅色</Radio>
            <!-- 深色模式选项 -->
            <Radio value="dark">深色</Radio>
          </RadioGroup>
        </div>
        <!-- 第二段：品牌主题色选择 -->
        <div class="theme-section">
          <!-- 小节标题：与“外观模式”保持一致的弱化样式 -->
          <div class="theme-label">主题色</div>
          <!-- 调色板列表：纵向排列，便于在弹层内快速扫视所有可选色 -->
          <div class="palette-list">
            <!-- 颜色项：遍历 @/theme 导出的 PALETTES；
                 key 用调色板唯一标识；active 类根据当前选中色实时切换高亮；
                 @click 把色板 key 交给 setPalette 完成应用与持久化 -->
            <button
              v-for="item in PALETTES"
              :key="item.key"
              class="palette-item"
              :class="{ active: themeState.palette === item.key }"
              type="button"
              @click="setPalette(item.key)"
            >
              <!-- 色点：直接使用调色板定义的主色 primary，作为该主题色的直观预览 -->
              <span class="palette-dot" :style="{ background: item.primary }"></span>
              <!-- 颜色名称：左对齐并占满剩余宽度，使勾选标记始终贴右 -->
              <span class="palette-name">{{ item.name }}</span>
              <!-- 选中勾：仅当前色板渲染，作为 active 底色之外的二次确认 -->
              <span v-if="themeState.palette === item.key" class="palette-check">✓</span>
            </button>
          </div>
        </div>
        <!-- 底部说明：向用户明确选择会被持久化（实际存储逻辑在 @/theme 的 setMode/setPalette 中） -->
        <div class="theme-tip">选择会保存到本地，刷新后自动恢复</div>
      </div>
    </template>
  </Popover>
</template>

<script setup>
// computed 用于创建可写计算属性与派生 isDark
import { computed } from 'vue'
// Arco Design Vue 的弹层与单选组件（项目内仅主题面板使用 Arco，保持面板视觉轻量）
import { Popover, RadioGroup, Radio } from '@arco-design/web-vue'
// 主题模块：PALETTES 可选调色板、themeState 当前主题响应式状态、setMode/setPalette 应用并持久化
import { PALETTES, themeState, setMode, setPalette } from '@/theme'

// 明暗模式双向绑定到 RadioGroup
// get 直接读取全局主题状态，保证面板与真实主题永远同步；
// set 交给 setMode 处理（内部负责写入 html class 与 localStorage），组件不直接改状态
const mode = computed({
  get: () => themeState.mode,
  set: value => setMode(value)
})

// 是否深色模式：用于在按钮上切换太阳/月亮图标
const isDark = computed(() => themeState.mode === 'dark')
</script>

<style scoped>
/* 触发按钮：固定 34x34 的方形热区，与顶栏其他图标按钮尺寸一致；
   透明背景+无边框融入顶栏，右侧 6px 外边距与用户下拉保持间距 */
.theme-trigger {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  margin-right: 6px;
  color: var(--app-text-2);
  cursor: pointer;
  background: transparent;
  border: none;
  border-radius: 8px;
  transition: background 0.18s ease, color 0.18s ease;
}

/* 悬停态：品牌色文字 + 品牌浅色底，反馈“可点击”；过渡 0.18s 让悬停不突兀 */
.theme-trigger:hover {
  color: var(--brand-primary);
  background: var(--brand-primary-soft);
}

/* 面板容器：固定 232px 宽度避免弹层随内容抖动；内边距略下紧上松，让底部说明更贴近边缘 */
.theme-panel {
  width: 232px;
  padding: 14px 16px 12px;
  color: var(--app-text-1);
}

/* 相邻小节之间：上外边距 + 顶部细线分隔；只作用于“第二个及之后”的 section，首段无分隔线 */
.theme-section + .theme-section {
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid var(--app-border);
}

/* 小节标题：12px、次级文字色 + 字距，作为分区标签而不与选项争夺注意力 */
.theme-label {
  margin-bottom: 9px;
  font-size: 12px;
  color: var(--app-text-3);
  letter-spacing: 0.4px;
}

/* 单选按钮组：占满面板宽度，让“浅色/深色”两个按钮等分排布 */
.mode-group {
  width: 100%;
}

/* 调色板列表：纵向排列，4px 间隙既区分各项又保持列表紧凑 */
.palette-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

/* 颜色项：整行可点击的透明按钮，默认透明边框用于预留 active 时的边框宽度，避免高亮抖动 */
.palette-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  font-size: 13px;
  color: var(--app-text-2);
  cursor: pointer;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 8px;
  transition: background 0.15s ease, border-color 0.15s ease;
}

/* 悬停态：使用比面板底色略深一层的 --app-surface-2，在深浅主题下都能看出反馈 */
.palette-item:hover {
  background: var(--app-surface-2);
}

/* 选中态：品牌色文字 + 品牌浅底 + 品牌色描边，三种手段叠加保证选中状态足够明显 */
.palette-item.active {
  color: var(--brand-primary);
  background: var(--brand-primary-soft);
  border-color: var(--brand-primary-border);
}

/* 色点：14px 圆形；内阴影一圈半透明白边，避免浅色色点在浅色背景上“消失” */
.palette-dot {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.65) inset;
}

/* 颜色名：flex:1 占满并左对齐，把勾选标记推到最右侧 */
.palette-name {
  flex: 1;
  text-align: left;
}

/* 选中勾：小字号品牌色，与选中项的文字颜色保持一致 */
.palette-check {
  font-size: 12px;
  color: var(--brand-primary);
}

/* 底部提示：11px 最弱文字色，只作补充说明，不干扰主要选项 */
.theme-tip {
  margin-top: 12px;
  font-size: 11px;
  color: var(--app-text-3);
}
</style>
