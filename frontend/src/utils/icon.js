import * as Icons from '@element-plus/icons-vue'

const iconMap = {}
Object.entries(Icons).forEach(([name, comp]) => {
  iconMap[name] = comp
})

// 将菜单 icon 名称解析为 Element Plus 图标组件
// 支持：'User' / 'user' / 'el-icon-user' / 'system' 等常见写法
export function resolveIcon(name) {
  if (!name) return null
  if (iconMap[name]) return iconMap[name]
  const cleaned = String(name)
    .replace(/^el-icon-/i, '')
    .replace(/^icon-/, '')
    .replace(/[-_](\w)/g, (_, c) => c.toUpperCase())
  const pascal = cleaned.charAt(0).toUpperCase() + cleaned.slice(1)
  return iconMap[pascal] || null
}
