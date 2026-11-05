<template>
  <div class="sidebar">
    <div class="sidebar-logo">
      <div class="logo-mark">
        <el-icon :size="22"><Platform /></el-icon>
      </div>
      <span class="logo-title">后台管理系统</span>
    </div>
    <el-scrollbar class="sidebar-scroll">
      <el-menu
        :default-active="activeMenu"
        background-color="transparent"
        text-color="var(--app-text-2)"
        active-text-color="var(--brand-primary)"
        :unique-opened="false"
        router
      >
        <sidebar-item v-for="menu in visibleMenus" :key="menu.id" :menu="menu" base-path="" />
      </el-menu>
    </el-scrollbar>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { Platform } from '@element-plus/icons-vue'
import { auth } from '@/store/auth'
import SidebarItem from './SidebarItem.vue'

const route = useRoute()
const activeMenu = computed(() => route.meta && route.meta.activeMenu ? route.meta.activeMenu : route.path)

// 仅展示 M/C 类型且未隐藏、未停用的菜单
const visibleMenus = computed(() =>
  (auth.menus || []).filter(
    m => m.menu_type !== 'F' && String(m.visible) !== '1' && String(m.status) !== '1'
  )
)
</script>

<style scoped>
.sidebar {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--app-sidebar-bg);
  border-right: 1px solid var(--app-border-light);
}

.sidebar-logo {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 56px;
  padding: 0 18px;
  background: var(--brand-gradient);
  color: #fff;
  flex-shrink: 0;
  box-shadow: 0 4px 14px var(--brand-glow);
  z-index: 2;
}

.logo-mark {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  color: #fff;
  background: rgba(255, 255, 255, 0.18);
  border: 1px solid rgba(255, 255, 255, 0.28);
  border-radius: var(--app-radius-md);
}

.logo-title {
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 1px;
  white-space: nowrap;
}

.sidebar-scroll {
  flex: 1;
  padding-top: 8px;
}

.sidebar-scroll :deep(.el-menu) {
  border-right: none;
  background: transparent;
}

/* 一级菜单项：圆角块 + 选中左侧色条 */
.sidebar-scroll :deep(.el-menu-item),
.sidebar-scroll :deep(.el-sub-menu__title) {
  height: 44px;
  line-height: 44px;
  margin: 4px 10px;
  padding-left: 14px !important;
  border-radius: 8px;
  font-size: 14px;
  transition: background 0.2s ease, color 0.2s ease;
}

/* 二级菜单：标题与叶子统一右移，和一级形成明显层级 */
.sidebar-scroll :deep(.menu-level-2 > .el-sub-menu__title) {
  padding-left: 34px !important;
  font-size: 13.5px;
}

.sidebar-scroll :deep(.menu-level-2.el-menu-item) {
  padding-left: 40px !important;
}

/* 三级菜单：在二级基础上继续右移，形成第三层从属关系 */
.sidebar-scroll :deep(.menu-level-3 > .el-sub-menu__title) {
  padding-left: 58px !important;
}

.sidebar-scroll :deep(.menu-level-3.el-menu-item) {
  padding-left: 64px !important;
}

/* 折叠菜单下的叶子项通用样式 */
.sidebar-scroll :deep(.el-sub-menu .el-menu-item) {
  min-width: 0;
  margin: 3px 10px 3px 0;
  border-radius: 8px;
  font-size: 13px;
}

.sidebar-scroll :deep(.el-menu-item:hover),
.sidebar-scroll :deep(.el-sub-menu__title:hover) {
  background-color: var(--brand-primary-soft);
  color: var(--brand-primary);
}

.sidebar-scroll :deep(.el-menu-item.is-active) {
  background: var(--brand-primary-soft);
  color: var(--brand-primary);
  font-weight: 600;
  box-shadow: inset 3px 0 0 var(--brand-primary);
}

.sidebar-scroll :deep(.el-sub-menu.is-active > .el-sub-menu__title) {
  color: var(--brand-primary);
  font-weight: 600;
}

.sidebar-scroll :deep(.el-sub-menu .el-menu) {
  background: transparent;
}
</style>
