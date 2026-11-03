<template>
  <!-- 目录且有可见子级 → 子菜单 -->
  <el-sub-menu v-if="isDir" :index="String(menu.id)">
    <template #title>
      <el-icon v-if="iconComp"><component :is="iconComp" /></el-icon>
      <span>{{ menu.menu_name }}</span>
    </template>
    <sidebar-item
      v-for="child in visibleChildren"
      :key="child.id"
      :menu="child"
      :base-path="fullPath"
    />
  </el-sub-menu>
  <!-- 叶子菜单 → 菜单项 -->
  <el-menu-item v-else-if="menu.menu_type === 'C'" :index="fullPath">
    <el-icon v-if="iconComp"><component :is="iconComp" /></el-icon>
    <span>{{ menu.menu_name }}</span>
  </el-menu-item>
</template>

<script setup>
import { computed } from 'vue'
import { resolveIcon } from '@/utils/icon'

const props = defineProps({
  menu: { type: Object, required: true },
  basePath: { type: String, default: '' }
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
