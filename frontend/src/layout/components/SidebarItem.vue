<!--
  文件级说明：
  职责：侧边菜单项的递归渲染组件——目录类菜单渲染为可展开的子菜单，页面类菜单渲染为可点击的叶子项。
  依赖：resolveIcon（把后端图标字符串解析成 Element Plus 图标组件）、Sidebar/SidebarItem 自身递归。
  被谁使用：Sidebar.vue 渲染顶级菜单，SidebarItem 内部再递归渲染子级。
  说明：路径通过 base-path 逐级向下传递并拼接，保证任意深度的菜单都能生成正确的完整地址。
-->
<template>
  <!-- 目录且有可见子级 → 子菜单 -->
  <!-- index 用菜单 id（转字符串）而非路径：el-sub-menu 要求唯一字符串索引，
       用 id 可避免不同层级出现同路径目录时的冲突；class 中的 level 供样式做逐级缩进 -->
  <el-sub-menu v-if="isDir" :index="String(menu.id)" :class="`menu-level-${level}`">
    <!-- 子菜单标题插槽：图标 + 菜单名，点击标题即可展开/收起子级 -->
    <template #title>
      <!-- 仅当后台配置了图标且能解析到组件时才渲染，避免出现空白占位 -->
      <el-icon v-if="iconComp"><component :is="iconComp" /></el-icon>
      <span>{{ menu.menu_name }}</span>
    </template>
    <!-- 递归渲染可见子菜单：base-path 传入当前目录的完整路径，level+1 让层级样式继续下探 -->
    <sidebar-item
      v-for="child in visibleChildren"
      :key="child.id"
      :menu="child"
      :base-path="fullPath"
      :level="level + 1"
    />
  </el-sub-menu>
  <!-- 叶子菜单 → 菜单项 -->
  <!-- index 用完整路径（fullPath）：父级 el-menu 开启了 router 模式，index 会被直接当作跳转地址；
       因此这里必须是可访问的绝对路径，而不是菜单 id -->
  <el-menu-item v-else-if="menu.menu_type === 'C'" :index="fullPath" :class="`menu-level-${level}`">
    <!-- 图标可选：未配置或无法解析时不渲染，文字保持左对齐 -->
    <el-icon v-if="iconComp"><component :is="iconComp" /></el-icon>
    <span>{{ menu.menu_name }}</span>
  </el-menu-item>
</template>

<script setup>
// computed 用于派生可见子级、目录判定、完整路径与图标组件
import { computed } from 'vue'
// 图标解析工具：把后端存储的图标名字符串映射为可渲染的组件（解析不到时返回空值）
import { resolveIcon } from '@/utils/icon'

// 组件 props：
// · menu：当前菜单节点（后端菜单树中的一项，含 menu_type/path/icon/children 等字段）
// · basePath：父级已经拼接好的路径前缀，递归时由父组件传入
// · level：菜单层级：一级=1，二级=2，三级=3，用于逐级缩进
const props = defineProps({
  menu: { type: Object, required: true },
  basePath: { type: String, default: '' },
  // 菜单层级：一级=1，二级=2，三级=3，用于逐级缩进
  level: { type: Number, default: 1 }
})

// 当前菜单下真正可见的子级：过滤掉按钮权限(F)、隐藏菜单(visible='1')与停用菜单(status='1')，
// 若目录下所有子级都被过滤，则 isDir 为 false，该目录不会渲染成空子菜单
const visibleChildren = computed(() =>
  (props.menu.children || []).filter(
    c => c.menu_type !== 'F' && String(c.visible) !== '1' && String(c.status) !== '1'
  )
)

// 是否渲染为“目录”：必须同时满足类型为 M（目录）且存在至少一个可见子级
const isDir = computed(() => props.menu.menu_type === 'M' && visibleChildren.value.length > 0)

// 计算当前菜单的完整访问路径：
// · 去掉菜单 path 可能存在的前导斜杠，避免与父级前缀拼接后出现 '//' 双斜杠
// · 有父级前缀时拼成 `${basePath}/${p}`，否则视为一级菜单，补一个前导 '/' 得到绝对路径
const fullPath = computed(() => {
  const p = String(props.menu.path || '').replace(/^\//, '')
  return props.basePath ? `${props.basePath}/${p}` : `/${p}`
})

// 图标组件：由 resolveIcon 解析，失败返回空值，模板据此决定是否渲染 el-icon
const iconComp = computed(() => resolveIcon(props.menu.icon))
</script>
