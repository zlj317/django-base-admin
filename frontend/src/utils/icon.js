// 菜单图标解析工具：后端菜单表只存图标“名称字符串”，这里把它映射成 Element Plus 的图标组件。
// 依赖：@element-plus/icons-vue。
import * as Icons from '@element-plus/icons-vue'

// 以图标组件名为键建立索引，便于 O(1) 查找
const iconMap = {}
Object.entries(Icons).forEach(([name, comp]) => {
  iconMap[name] = comp
})

// 将菜单 icon 名称解析为 Element Plus 图标组件
// 支持：'User' / 'user' / 'el-icon-user' / 'system' 等常见写法
// 这样做是因为历史数据里图标命名风格不统一，兼容解析可避免改数据。
export function resolveIcon(name) {
  // 菜单没配图标时返回 null，调用方据此不渲染 <component :is>
  if (!name) return null
  // 先按原名精确命中，覆盖后端已按 PascalCase 存储的情况
  if (iconMap[name]) return iconMap[name]
  // 兼容旧命名：去掉 el-icon-/icon- 前缀，并把 kebab/snake 形式转成驼峰
  const cleaned = String(name)
    .replace(/^el-icon-/i, '')
    .replace(/^icon-/, '')
    .replace(/[-_](\w)/g, (_, c) => c.toUpperCase())
  // Element Plus 图标组件名是 PascalCase，这里再补齐首字母大写
  const pascal = cleaned.charAt(0).toUpperCase() + cleaned.slice(1)
  // 仍找不到就返回 null，让菜单退化为“无图标”而不是报错
  return iconMap[pascal] || null
}
