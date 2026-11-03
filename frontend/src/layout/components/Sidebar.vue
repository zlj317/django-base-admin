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
        text-color="#4b5563"
        active-text-color="#4a6cf7"
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
  background: linear-gradient(180deg, #ffffff 0%, #f7f9ff 100%);
  border-right: 1px solid #eef1f6;
}

.sidebar-logo {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 56px;
  padding: 0 18px;
  background: linear-gradient(135deg, #4a6cf7 0%, #6f8bff 100%);
  color: #fff;
  flex-shrink: 0;
  box-shadow: 0 4px 14px rgba(74, 108, 247, 0.28);
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
  border-radius: 8px;
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

.sidebar-scroll :deep(.el-sub-menu .el-menu-item) {
  min-width: 0;
  margin: 3px 10px 3px 0;
  border-radius: 8px;
  font-size: 13px;
  /* 折叠菜单下的子菜单统一向右缩进，强化父子从属关系 */
  padding-left: 40px !important;
}

.sidebar-scroll :deep(.el-menu-item:hover),
.sidebar-scroll :deep(.el-sub-menu__title:hover) {
  background-color: #eef1ff;
  color: #4a6cf7;
}

.sidebar-scroll :deep(.el-menu-item.is-active) {
  background: linear-gradient(90deg, #eef1ff 0%, #f6f8ff 100%);
  color: #4a6cf7;
  font-weight: 600;
  box-shadow: inset 3px 0 0 #4a6cf7;
}

.sidebar-scroll :deep(.el-sub-menu.is-active > .el-sub-menu__title) {
  color: #4a6cf7;
  font-weight: 600;
}

.sidebar-scroll :deep(.el-sub-menu .el-menu) {
  background: transparent;
}
</style>
