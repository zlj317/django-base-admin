<template>
  <Popover trigger="click" position="br" :content-style="{ padding: '0' }">
    <button class="theme-trigger" type="button" aria-label="主题设置" title="主题设置">
      <!-- 用内联 SVG 图标，避免额外图标包体积 -->
      <svg v-if="isDark" viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
        <path d="M12 2a1 1 0 0 1 1 1v1.5a1 1 0 1 1-2 0V3a1 1 0 0 1 1-1Zm0 17a6 6 0 1 0 0-12 6 6 0 0 0 0 12Zm0 1.5v1.5a1 1 0 1 1-2 0V21a1 1 0 1 1 2 0ZM2 12a1 1 0 0 1 1-1h1.5a1 1 0 1 1 0 2H3a1 1 0 0 1-1-1Zm17 0a1 1 0 0 1 1-1h1.5a1 1 0 1 1 0 2H20a1 1 0 0 1-1-1ZM4.9 4.9a1 1 0 0 1 1.4 0l1 1a1 1 0 1 1-1.4 1.4l-1-1a1 1 0 0 1 0-1.4Zm13.2 13.2a1 1 0 0 1 1.4 0l1 1a1 1 0 1 1-1.4 1.4l-1-1a1 1 0 0 1 0-1.4Zm2.4-13.2a1 1 0 0 1 0 1.4l-1 1a1 1 0 1 1-1.4-1.4l1-1a1 1 0 0 1 1.4 0ZM6.3 16.7a1 1 0 0 1 0 1.4l-1 1a1 1 0 1 1-1.4-1.4l1-1a1 1 0 0 1 1.4 0Z" />
      </svg>
      <svg v-else viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
        <path d="M20.7 14.2a1 1 0 0 0-1.2-1.2 7 7 0 0 1-8.4-8.4A1 1 0 0 0 9.9 3.4a9 9 0 1 0 10.8 10.8Z" />
      </svg>
    </button>
    <template #content>
      <div class="theme-panel">
        <div class="theme-section">
          <div class="theme-label">外观模式</div>
          <RadioGroup v-model="mode" type="button" size="small" class="mode-group">
            <Radio value="light">浅色</Radio>
            <Radio value="dark">深色</Radio>
          </RadioGroup>
        </div>
        <div class="theme-section">
          <div class="theme-label">主题色</div>
          <div class="palette-list">
            <button
              v-for="item in PALETTES"
              :key="item.key"
              class="palette-item"
              :class="{ active: themeState.palette === item.key }"
              type="button"
              @click="setPalette(item.key)"
            >
              <span class="palette-dot" :style="{ background: item.primary }"></span>
              <span class="palette-name">{{ item.name }}</span>
              <span v-if="themeState.palette === item.key" class="palette-check">✓</span>
            </button>
          </div>
        </div>
        <div class="theme-tip">选择会保存到本地，刷新后自动恢复</div>
      </div>
    </template>
  </Popover>
</template>

<script setup>
import { computed } from 'vue'
import { Popover, RadioGroup, Radio } from '@arco-design/web-vue'
import { PALETTES, themeState, setMode, setPalette } from '@/theme'

// 明暗模式双向绑定到 RadioGroup
const mode = computed({
  get: () => themeState.mode,
  set: value => setMode(value)
})

const isDark = computed(() => themeState.mode === 'dark')
</script>

<style scoped>
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

.theme-trigger:hover {
  color: var(--brand-primary);
  background: var(--brand-primary-soft);
}

.theme-panel {
  width: 232px;
  padding: 14px 16px 12px;
  color: var(--app-text-1);
}

.theme-section + .theme-section {
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid var(--app-border);
}

.theme-label {
  margin-bottom: 9px;
  font-size: 12px;
  color: var(--app-text-3);
  letter-spacing: 0.4px;
}

.mode-group {
  width: 100%;
}

.palette-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

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

.palette-item:hover {
  background: var(--app-surface-2);
}

.palette-item.active {
  color: var(--brand-primary);
  background: var(--brand-primary-soft);
  border-color: var(--brand-primary-border);
}

.palette-dot {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.65) inset;
}

.palette-name {
  flex: 1;
  text-align: left;
}

.palette-check {
  font-size: 12px;
  color: var(--brand-primary);
}

.theme-tip {
  margin-top: 12px;
  font-size: 11px;
  color: var(--app-text-3);
}
</style>
