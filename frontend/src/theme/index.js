/**
 * 主题系统：明暗模式 + 多主题色
 * 统一把主题色写入 CSS 变量，同时驱动 Element Plus、Arco Design 与自研样式，
 * 保证表格、弹窗、图表、暗色边框都跟随主题，避免页面里出现硬编码颜色。
 */
import { reactive, watch } from 'vue'

const STORAGE_KEY = 'app-theme'  // 本地持久化键

/** 可选主题色方案：主色 + 图表色板 + 展示名 */
export const PALETTES = [
  {
    key: 'blue',
    name: '深海蓝',
    primary: '#165dff',
    charts: ['#165dff', '#14c9c9', '#ff7d00', '#722ed1', '#00b42a', '#f53f3f']
  },
  {
    key: 'teal',
    name: '青碧绿',
    primary: '#0fc6c2',
    charts: ['#0fc6c2', '#165dff', '#ffb400', '#722ed1', '#00b42a', '#f53f3f']
  },
  {
    key: 'purple',
    name: '幻夜紫',
    primary: '#722ed1',
    charts: ['#722ed1', '#f5319d', '#14c9c9', '#ff7d00', '#165dff', '#00b42a']
  },
  {
    key: 'orange',
    name: '活力橙',
    primary: '#ff7d00',
    charts: ['#ff7d00', '#ffb400', '#165dff', '#14c9c9', '#722ed1', '#f53f3f']
  },
  {
    key: 'rose',
    name: '玫瑰红',
    primary: '#f5319d',
    charts: ['#f5319d', '#722ed1', '#ff7d00', '#14c9c9', '#165dff', '#00b42a']
  }
]

export const themeState = reactive({
  mode: 'light',  // light | dark
  palette: 'blue'
})

/** 十六进制颜色转 RGB 数组 */
function hexToRgb(hex) {
  const value = hex.replace('#', '')
  const full = value.length === 3 ? value.split('').map(c => c + c).join('') : value
  return [
    parseInt(full.slice(0, 2), 16),
    parseInt(full.slice(2, 4), 16),
    parseInt(full.slice(4, 6), 16)
  ]
}

/** 颜色混合：weight 表示向 target 靠拢的比例（0~1） */
function mix(color, target, weight) {
  const source = hexToRgb(color)
  const dest = hexToRgb(target)
  const ratio = Math.min(Math.max(weight, 0), 1)
  const values = source.map((item, index) => Math.round(item * (1 - ratio) + dest[index] * ratio))
  return `rgb(${values.join(', ')})`
}

/** 按 key 取主题色方案，找不到时回退到第一套 */
function getPalette(key) {
  return PALETTES.find(item => item.key === key) || PALETTES[0]
}

/** 把主题色写入根节点变量：覆盖 Element Plus、Arco 与自研变量 */
function applyPalette(palette, dark) {
  const root = document.documentElement  // 变量统一挂在根节点
  const base = dark ? '#141414' : '#ffffff'  // 暗色下浅色梯度向深底靠拢

  root.style.setProperty('--el-color-primary', palette.primary)  // Element Plus 主色
  ;[3, 5, 7, 8, 9].forEach(level => {
    root.style.setProperty(`--el-color-primary-light-${level}`, mix(palette.primary, base, level / 10))
  })
  root.style.setProperty('--el-color-primary-dark-2', mix(palette.primary, '#000000', 0.2))

  // Arco Design 主色梯度：1 最浅，6 为主色，10 最深
  ;[1, 2, 3, 4, 5].forEach(level => {
    root.style.setProperty(`--primary-${level}`, mix(palette.primary, base, (6 - level) / 6))
  })
  root.style.setProperty('--primary-6', palette.primary)
  ;[7, 8, 9, 10].forEach(level => {
    root.style.setProperty(`--primary-${level}`, mix(palette.primary, '#000000', (level - 6) / 12))
  })

  // 自研组件与业务页面使用的主色变量
  const rgb = hexToRgb(palette.primary)
  root.style.setProperty('--brand-primary', palette.primary)
  root.style.setProperty('--brand-primary-rgb', rgb.join(', '))
  root.style.setProperty('--brand-primary-hover', mix(palette.primary, '#000000', 0.18))
  root.style.setProperty('--brand-primary-soft', mix(palette.primary, base, dark ? 0.82 : 0.9))
  root.style.setProperty('--brand-primary-border', mix(palette.primary, base, dark ? 0.62 : 0.68))
  root.style.setProperty('--brand-gradient', `linear-gradient(135deg, ${palette.primary} 0%, ${mix(palette.primary, '#ffffff', 0.22)} 100%)`)
  root.style.setProperty('--brand-glow', `rgba(${rgb.join(', ')}, ${dark ? 0.35 : 0.28})`)

  // 图表配色：SVG 中直接引用这些变量即可跟随主题
  palette.charts.forEach((color, index) => {
    root.style.setProperty(`--chart-${index + 1}`, color)
  })
}

/** 应用当前主题：模式 + 主题色 + 第三方库的暗色标记 */
export function applyTheme() {
  const dark = themeState.mode === 'dark'
  const palette = getPalette(themeState.palette)
  const root = document.documentElement

  root.classList.toggle('dark', dark)  // Element Plus 暗色主题依赖 html.dark
  root.dataset.theme = palette.key  // 便于按主题色做额外微调
  document.body.setAttribute('arco-theme', dark ? 'dark' : 'light')  // Arco 暗色标记

  applyPalette(palette, dark)
}

/** 切换明暗模式 */
export function setMode(mode) {
  themeState.mode = mode === 'dark' ? 'dark' : 'light'
}

/** 切换主题色 */
export function setPalette(key) {
  if (PALETTES.some(item => item.key === key)) {
    themeState.palette = key
  }
}

/** 在明暗模式之间切换 */
export function toggleMode() {
  setMode(themeState.mode === 'dark' ? 'light' : 'dark')
}

/** 从本地缓存恢复主题，并在变化时写回 */
function restore() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}')
    if (saved.mode === 'dark' || saved.mode === 'light') themeState.mode = saved.mode
    if (PALETTES.some(item => item.key === saved.palette)) themeState.palette = saved.palette
  } catch (e) {
    // 缓存损坏时忽略，使用默认主题
  }
}

watch(
  themeState,
  value => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ mode: value.mode, palette: value.palette }))
    applyTheme()
  },
  { deep: true }
)

/** 初始化：先恢复缓存再应用，避免首屏闪烁 */
export function initTheme() {
  restore()
  applyTheme()
}
