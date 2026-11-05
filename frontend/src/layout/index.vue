<template>
  <el-container class="layout">
    <el-aside width="216px" class="layout-aside">
      <Sidebar />
    </el-aside>
    <el-container class="layout-body">
      <el-header height="56px" class="layout-header">
        <Navbar />
      </el-header>
      <el-main class="layout-main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import Sidebar from './components/Sidebar.vue'
import Navbar from './components/Navbar.vue'
</script>

<style scoped>
.layout {
  height: 100%;
}

.layout-aside {
  background-color: var(--app-sidebar-bg);
  transition: width 0.2s;
  box-shadow: 2px 0 12px rgba(29, 33, 41, 0.05);
  z-index: 3;
}

html.dark .layout-aside {
  box-shadow: 2px 0 16px rgba(0, 0, 0, 0.4);
}

.layout-body {
  min-width: 0;
}

.layout-header {
  padding: 0;
  background-color: var(--app-header-bg);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid var(--app-border-light);
  z-index: 5;
}

.layout-main {
  padding: 0;
  background: var(--app-bg);
  overflow: auto;
}
</style>
