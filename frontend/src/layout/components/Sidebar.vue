<!--
  文件级说明：
  职责：后台左侧侧边栏——顶部品牌标识区 + 可滚动的菜单树，是系统功能导航的唯一入口。
  依赖：auth.menus（后端按角色下发的菜单树）、SidebarItem（递归渲染菜单）、vue-router（当前路由高亮）。
  被谁使用：layout/index.vue 的 el-aside 中，全站共用。
  说明：菜单的可见性与层级完全由后端数据决定，前端不做硬编码菜单。
-->
<template>
  <!-- 侧边栏根节点：纵向弹性布局，logo 固定高度、菜单区占满剩余高度 -->
  <div class="sidebar">
    <!-- 品牌标识区：渐变背景 + 系统名，与顶栏同高（56px）形成连续的顶部视觉带 -->
    <div class="sidebar-logo">
      <!-- 图标底框：半透明白色方块，保证图标在任何主题色下都有足够对比度 -->
      <div class="logo-mark">
        <!-- 平台图标：22px，使用 Element Plus 的 Platform 图标表达“系统平台”语义 -->
        <el-icon :size="22"><Platform /></el-icon>
      </div>
      <!-- 系统标题：固定文案，超长时可省略（white-space:nowrap 配合容器裁切） -->
      <span class="logo-title">后台管理系统</span>
    </div>
    <!-- 滚动容器：菜单过长时可独立滚动，不影响顶部 logo 与整页布局 -->
    <el-scrollbar class="sidebar-scroll">
      <!-- 菜单根节点：
           · default-active：当前高亮项，来自 activeMenu 计算属性（优先 meta.activeMenu，支持详情页高亮列表菜单）
           · background-color=transparent：背景交给外层 CSS 控制，避免 Element 内联底色覆盖主题变量
           · text-color / active-text-color：直接引用主题 CSS 变量，切换主题色或暗色时自动生效
           · unique-opened=false：允许多个父菜单同时展开，便于跨模块快速切换
           · router：开启路由模式，点击菜单项时以 index 作为路径进行跳转，无需手动绑定 click -->
      <el-menu
        :default-active="activeMenu"
        background-color="transparent"
        text-color="var(--app-text-2)"
        active-text-color="var(--brand-primary)"
        :unique-opened="false"
        router
      >
        <!-- 顶级菜单递归渲染：base-path 传空串，由 SidebarItem 内部逐级拼接完整路径；
             每个菜单用后端 id 作为 key，保证稳定性 -->
        <sidebar-item v-for="menu in visibleMenus" :key="menu.id" :menu="menu" base-path="" />
      </el-menu>
    </el-scrollbar>
  </div>
</template>

<script setup>
// computed 用于派生当前高亮菜单与可见菜单列表
import { computed } from 'vue'
// useRoute 获取当前路由，用于决定菜单高亮项
import { useRoute } from 'vue-router'
// Element Plus 图标：侧边栏顶部品牌图标
import { Platform } from '@element-plus/icons-vue'
// auth 为全局登录态，auth.menus 是后端按角色下发的菜单树
import { auth } from '@/store/auth'
// 递归菜单项组件：根据菜单类型渲染子菜单或页面菜单
import SidebarItem from './SidebarItem.vue'

// 当前路由对象（响应式）
const route = useRoute()
// 当前应高亮的菜单路径：
// · 允许页面通过 meta.activeMenu 指定高亮项（例如详情页希望高亮其列表页菜单，而不是详情地址本身）
// · 未指定时退回 route.path，与服务端菜单 path 保持一致
const activeMenu = computed(() => route.meta && route.meta.activeMenu ? route.meta.activeMenu : route.path)

// 仅展示 M/C 类型且未隐藏、未停用的菜单
// · menu_type='F' 是按钮级权限，不参与导航展示
// · visible 为 '1' 表示菜单隐藏（如配置页、调试页）
// · status 为 '1' 表示菜单已停用，不应出现在侧边栏
// 这里对 visible/status 做 String 转换，兼容后端返回数字或字符串两种类型
const visibleMenus = computed(() =>
  (auth.menus || []).filter(
    m => m.menu_type !== 'F' && String(m.visible) !== '1' && String(m.status) !== '1'
  )
)
</script>

<style scoped>
/* 侧边栏根节点：纵向布局，logo 固定、滚动区占剩余高度；背景与右边框均取主题变量 */
.sidebar {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--app-sidebar-bg);
  border-right: 1px solid var(--app-border-light);
}

/* 品牌区：品牌渐变背景贯穿顶部，白色文字保证在深色渐变上可读；
   flex-shrink:0 防止菜单过长时被压缩；投影与顶部 z-index 让 logo 区悬浮于滚动内容之上 */
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

/* 图标底框：30x30 居中容器，半透明白底+细边框让图标与渐变背景分离，柔和不抢色 */
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

/* 系统标题：15px 加粗 + 字距 1px，适合品牌名短文本；nowrap 防止换行破坏 56px 高度 */
.logo-title {
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 1px;
  white-space: nowrap;
}

/* 菜单滚动区：flex:1 占满 logo 以下全部高度；顶部 8px 内边距与 logo 拉开距离 */
.sidebar-scroll {
  flex: 1;
  padding-top: 8px;
}

/* 覆盖 el-menu 默认的右侧边框和白色背景，让菜单完全融入侧边栏主题底色 */
.sidebar-scroll :deep(.el-menu) {
  border-right: none;
  background: transparent;
}

/* 一级菜单项：圆角块 + 选中左侧色条 */
/* 统一一级“页面项”与“目录标题”的高度、外边距和字号；
   padding-left 用 !important 覆盖 Element Plus 内联样式；圆角+过渡为 hover 提供平滑反馈 */
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
/* 二级目录标题比一级多缩进 20px，字号略小，形成从属关系的视觉暗示 */
.sidebar-scroll :deep(.menu-level-2 > .el-sub-menu__title) {
  padding-left: 34px !important;
  font-size: 13.5px;
}

/* 二级叶子项比二级目录标题再多缩进 6px，避免标题与子项左边缘完全重合 */
.sidebar-scroll :deep(.menu-level-2.el-menu-item) {
  padding-left: 40px !important;
}

/* 三级菜单：在二级基础上继续右移，形成第三层从属关系 */
/* 三级目录标题缩进 58px，延续每层约 24px 的递增节奏 */
.sidebar-scroll :deep(.menu-level-3 > .el-sub-menu__title) {
  padding-left: 58px !important;
}

/* 三级叶子项缩进 64px，与三级标题保持 6px 的细微错位 */
.sidebar-scroll :deep(.menu-level-3.el-menu-item) {
  padding-left: 64px !important;
}

/* 折叠菜单下的叶子项通用样式 */
/* 兜底规则：任何嵌套在子菜单里的叶子项都使用更小的外边距与字号，避免深层菜单显得拥挤；
   min-width:0 允许窄屏下内容省略而不撑破侧边栏 */
.sidebar-scroll :deep(.el-sub-menu .el-menu-item) {
  min-width: 0;
  margin: 3px 10px 3px 0;
  border-radius: 8px;
  font-size: 13px;
}

/* 悬停态：品牌色浅底 + 品牌色文字，比默认灰色背景更明确地提示可点击 */
.sidebar-scroll :deep(.el-menu-item:hover),
.sidebar-scroll :deep(.el-sub-menu__title:hover) {
  background-color: var(--brand-primary-soft);
  color: var(--brand-primary);
}

/* 当前选中项：浅品牌底 + 加粗 + 左侧 3px 内阴影色条；
   inset 阴影不会占额外宽度，避免高亮时文字位置发生跳动 */
.sidebar-scroll :deep(.el-menu-item.is-active) {
  background: var(--brand-primary-soft);
  color: var(--brand-primary);
  font-weight: 600;
  box-shadow: inset 3px 0 0 var(--brand-primary);
}

/* 当某个子项被选中时，其父目录标题也使用品牌色并加粗，提示用户该分组内有当前页面 */
.sidebar-scroll :deep(.el-sub-menu.is-active > .el-sub-menu__title) {
  color: var(--brand-primary);
  font-weight: 600;
}

/* 子菜单容器背景置透明，避免 Element Plus 默认的浅色背景与主题底色叠加产生色块 */
.sidebar-scroll :deep(.el-sub-menu .el-menu) {
  background: transparent;
}
</style>
