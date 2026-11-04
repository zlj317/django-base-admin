<template>
  <!-- 目录且有可见子级 → 子菜单 -->
  <el-sub-menu v-if="isDir" :index="String(menu.id)" :class="`menu-level-${level}`">
    <template #title>
      <el-icon v-if="iconComp"><component :is="iconComp" /></el-icon>
      <span>{{ menu.menu_name }}</span>
    </template>
    <sidebar-item
      v-for="child in visibleChildren"
      :key="child.id"
      :menu="child"
      :base-path="fullPath"
      :level="level + 1"
    />
  </el-sub-menu>
  <!-- 叶子菜单 → 菜单项 -->
  <el-menu-item v-else-if="menu.menu_type === 'C'" :index="fullPath" :class="`menu-level-${level}`">
    <el-icon v-if="iconComp"><component :is="iconComp" /></el-icon>
    <span>{{ menu.menu_name }}</span>
  </el-menu-item>
</template>

<script setup>
import { computed } from 'vue'
import { resolveIcon } from '@/utils/icon'

const props = defineProps({
  menu: { type: Object, required: true },
  basePath: { type: String, default: '' },
  // 菜单层级：一级=1，二级=2，三级=3，用于逐级缩进
  level: { type: Number, default: 1 }
})

const visibleChildren = computed(() =>
  (props.menu.children || []).filter(
    c => c.menu_type !== 'F' && String(c.visible) !== '1' && String(c.status) !== '1'
  )
)

const isDir = computed(() => props.menu.menu_type === 'M' && visibleChildren.value.length > 0)

const fullPath = computed(() => {
  const p = String(props.menu.path || '').replace(/^\//, '')
  return props.basePath ? `${props.basePath}/${p}` : `/${p}`
})

const iconComp = computed(() => resolveIcon(props.menu.icon))
</script>
