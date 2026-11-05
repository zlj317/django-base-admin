<template>
  <div class="navbar">
    <el-breadcrumb separator="/" class="navbar-breadcrumb">
      <el-breadcrumb-item v-for="item in crumbs" :key="item.path">
        {{ item.title }}
      </el-breadcrumb-item>
    </el-breadcrumb>
    <div class="navbar-right">
      <ThemeSwitch />
      <el-dropdown trigger="click" @command="handleCommand">
        <span class="user-entry">
          <el-avatar :size="30" :src="auth.user.avatar || undefined" class="user-avatar">
            {{ initial }}
          </el-avatar>
          <span class="user-name">{{ displayName }}</span>
          <el-icon class="user-arrow"><ArrowDown /></el-icon>
        </span>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="logout">
              <el-icon><SwitchButton /></el-icon>退出登录
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { auth, logout } from '@/store/auth'
import { clearDynamicRoutes } from '@/router'
import { ArrowDown, SwitchButton } from '@element-plus/icons-vue'
import ThemeSwitch from '@/components/ThemeSwitch.vue'

const route = useRoute()
const router = useRouter()

const crumbs = computed(() =>
  (route.matched || [])
    .filter(item => item.meta && item.meta.title)
    .map(item => ({ path: item.path, title: item.meta.title }))
)

const displayName = computed(() => auth.user.nickname || auth.user.username || '用户')
const initial = computed(() => displayName.value.slice(0, 1).toUpperCase())

async function handleCommand(command) {
  if (command === 'logout') {
    await logout()
    clearDynamicRoutes()
    router.push('/login')
  }
}
</script>

<style scoped>
.navbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 56px;
  padding: 0 20px;
}

.navbar-breadcrumb {
  font-size: 14px;
}

.navbar-breadcrumb :deep(.el-breadcrumb__inner) {
  color: var(--app-text-3);
  font-weight: 500;
}

.navbar-breadcrumb :deep(.el-breadcrumb__item:last-child .el-breadcrumb__inner) {
  color: var(--app-text-1);
  font-weight: 600;
}

.navbar-breadcrumb :deep(.el-breadcrumb__separator) {
  color: var(--app-text-4);
}

.navbar-right {
  display: flex;
  align-items: center;
  gap: 4px;
}

.user-entry {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 5px 10px 5px 6px;
  border-radius: var(--app-radius-md);
  cursor: pointer;
  color: var(--app-text-1);
  outline: none;
  transition: background 0.2s ease;
}

.user-entry:hover {
  background: var(--brand-primary-soft);
}

.user-avatar {
  color: #fff;
  font-weight: 600;
  background: var(--brand-gradient);
  box-shadow: 0 2px 6px var(--brand-glow);
}

.user-name {
  font-size: var(--app-font-base);
  font-weight: 500;
}

.user-arrow {
  color: var(--app-text-3);
  font-size: 12px;
}
</style>
