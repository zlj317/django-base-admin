<!--
  文件级说明：
  职责：后台管理系统的整体布局外壳——左侧固定侧边栏 + 顶部导航栏 + 右侧内容区，
        所有菜单页面都作为 router-view 的子内容渲染在其中。
  依赖：Sidebar（菜单树渲染）、Navbar（面包屑 / 主题切换 / 用户菜单）、vue-router 的 router-view。
  被谁使用：router/index.js 中所有挂在 Layout 下的静态路由与动态菜单路由。
  说明：本文件只承载结构与视觉框架，不包含任何业务逻辑。
-->
<template>
  <!-- 根容器：横向布局（左侧 aside + 右侧上下结构），height:100% 撑满整个可视区域 -->
  <el-container class="layout">
    <!-- 侧边栏占位容器：宽度由 Element Plus 的 width 属性锁定为 216px，具体菜单由 Sidebar 组件提供 -->
    <el-aside width="216px" class="layout-aside">
      <!-- 侧边菜单组件：logo 区 + 可滚动的菜单树（数据来源为 auth.menus） -->
      <Sidebar />
    </el-aside>
    <!-- 右侧主区：纵向排列（顶部 el-header + 下方 el-main）；min-width:0 防止内容溢出挤压缩放 -->
    <el-container class="layout-body">
      <!-- 顶部导航容器：固定 56px，与侧边栏 logo 区同高，保证两侧上边缘水平对齐 -->
      <el-header height="56px" class="layout-header">
        <!-- 顶栏内容：面包屑、主题切换面板、用户下拉菜单 -->
        <Navbar />
      </el-header>
      <!-- 内容区容器：padding 归零，留白交由各业务页面自行控制；滚动由本区域承担 -->
      <el-main class="layout-main">
        <!-- 路由出口：当前激活路由的页面组件在此渲染，切换菜单时只重绘这一块，侧边栏/顶栏保持稳定 -->
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
// 侧边菜单组件：读取登录用户菜单树渲染 el-menu，并通过 el-menu 的 router 模式完成跳转
import Sidebar from './components/Sidebar.vue'
// 顶栏组件：面包屑、主题/外观切换、用户下拉（含退出登录）
import Navbar from './components/Navbar.vue'
</script>

<style scoped>
/* 根容器：撑满 100% 高度，使侧边栏与主区能按 flex 规则占满视口 */
.layout {
  height: 100%;
}

/* 侧边栏容器：背景取主题变量 --app-sidebar-bg，随明暗/主题色切换自动变化；
   width 过渡让将来做折叠动画时宽度变化平滑；z-index 保证投影盖在内容区之上 */
.layout-aside {
  background-color: var(--app-sidebar-bg);
  transition: width 0.2s;
  box-shadow: 2px 0 12px rgba(29, 33, 41, 0.05);
  z-index: 3;
}

/* 暗色主题下加深投影：浅色阴影在深色背景上几乎不可见，需要更强的黑色阴影区分层次。
   html.dark 由主题模块在根元素上切换，因此这里用全局后代选择器 */
html.dark .layout-aside {
  box-shadow: 2px 0 16px rgba(0, 0, 0, 0.4);
}

/* 主区容器：min-width:0 覆盖 flex 子项默认的 min-width:auto，
   防止宽表格等子内容把主区撑出容器、压缩侧边栏 */
.layout-body {
  min-width: 0;
}

/* 顶栏容器：内边距归零（间距由 Navbar 内部控制）；背景取 --app-header-bg；
   backdrop-filter 让内容滚动到顶栏下方时呈现毛玻璃效果；底部细线用于分隔头部与内容 */
.layout-header {
  padding: 0;
  background-color: var(--app-header-bg);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid var(--app-border-light);
  z-index: 5;
}

/* 内容区：去掉 Element Plus 默认的 20px 内边距，背景使用主题底色 --app-bg；
   overflow:auto 让长页面在内容区内部滚动，不影响侧边栏与顶栏 */
.layout-main {
  padding: 0;
  background: var(--app-bg);
  overflow: auto;
}
</style>
