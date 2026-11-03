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
  background-color: #ffffff;
  transition: width 0.2s;
  box-shadow: 2px 0 12px rgba(30, 41, 59, 0.04);
  z-index: 3;
}

.layout-body {
  min-width: 0;
}

.layout-header {
  padding: 0;
  background-color: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(8px);
  border-bottom: 1px solid #eef1f6;
  z-index: 5;
}

.layout-main {
  padding: 0;
  background: var(--app-bg);
  overflow: auto;
}
</style>
