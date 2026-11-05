<!--
  文件级说明：
  职责：后台顶栏，提供当前页面位置（面包屑）、主题外观切换入口、用户信息与退出登录。
  依赖：ThemeSwitch（主题面板）、store/auth（用户信息与 logout）、router（清理动态路由并跳转登录页）、
        @element-plus/icons-vue。
  被谁使用：layout/index.vue 的 el-header 中，全站所有后台页面共用。
  说明：只负责顶栏交互，不涉及业务数据请求（用户信息由全局登录态维护）。
-->
<template>
  <!-- 顶栏根节点：左右两端对齐（左侧面包屑、右侧操作区），高度由父级 el-header 限制为 56px -->
  <div class="navbar">
    <!-- 面包屑：按当前地址命中的路由记录动态生成“目录 / 页面”层级，给用户明确的当前位置感 -->
    <el-breadcrumb separator="/" class="navbar-breadcrumb">
      <!-- 逐条渲染 matched 路由；key 用 route 的 path 保证同级路径唯一；
           内容来自 crumbs 计算属性（已过滤掉无 meta.title 的记录） -->
      <el-breadcrumb-item v-for="item in crumbs" :key="item.path">
        {{ item.title }}
      </el-breadcrumb-item>
    </el-breadcrumb>
    <!-- 右侧操作区：主题按钮 + 用户下拉，横向紧密排列 -->
    <div class="navbar-right">
      <!-- 主题切换组件：点击弹出 Arco Popover 面板，切换明暗模式与主题色（写入 localStorage） -->
      <ThemeSwitch />
      <!-- 用户下拉：trigger=click 表示点击而非悬停展开，避免误触；
           @command 统一接收各菜单项的 command 值，避免为每项单独绑定点击事件 -->
      <el-dropdown trigger="click" @command="handleCommand">
        <!-- 下拉触发器：头像 + 昵称 + 箭头整体作为一个可点击入口 -->
        <span class="user-entry">
          <!-- 头像：有 avatar 地址时显示图片；无地址时传 undefined 以触发 el-avatar 的插槽回退渲染，
               即显示 initial（昵称首字母）的文字头像 -->
          <el-avatar :size="30" :src="auth.user.avatar || undefined" class="user-avatar">
            {{ initial }}
          </el-avatar>
          <!-- 昵称/账号：由 displayName 计算属性逐级兜底，确保永远有可读文本 -->
          <span class="user-name">{{ displayName }}</span>
          <!-- 下拉指示箭头：纯视觉提示，不单独响应点击（点击由父级 span 触发下拉） -->
          <el-icon class="user-arrow"><ArrowDown /></el-icon>
        </span>
        <!-- 下拉菜单内容：当前只有“退出登录”，后续扩展个人中心等项时可在此追加 -->
        <template #dropdown>
          <el-dropdown-menu>
            <!-- command="logout" 与 handleCommand 中的判断保持一致，作为唯一指令标识 -->
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
// computed 用于派生面包屑、展示名、头像首字母等响应式数据
import { computed } from 'vue'
// useRoute 读取当前匹配路由（响应式）；useRouter 提供编程式跳转能力
import { useRoute, useRouter } from 'vue-router'
// auth 为全局响应式登录态（含 user 信息）；logout 负责调用后端注销并清理本地状态
import { auth, logout } from '@/store/auth'
// 退出登录后必须清理本会话注入的动态菜单路由，避免路由残留被下一位用户复用
import { clearDynamicRoutes } from '@/router'
// Element Plus 图标：ArrowDown 下拉箭头，SwitchButton 退出登录图标
import { ArrowDown, SwitchButton } from '@element-plus/icons-vue'
// 主题切换面板组件（明暗模式 + 主题色）
import ThemeSwitch from '@/components/ThemeSwitch.vue'

// 当前路由对象：路由切换时引用本身更新，依赖它的 computed 会自动重算
const route = useRoute()
// 路由器实例：仅用于退出后的登录页跳转
const router = useRouter()

// 面包屑数据：取 route.matched（当前地址命中的完整路由链）
// 过滤掉没有 meta.title 的中间层（例如只做路径分组的空壳父路由），避免出现空白面包屑项；
// 最终只保留 path 与 title 两个字段，模板渲染无需关心原始路由对象结构
const crumbs = computed(() =>
  (route.matched || [])
    .filter(item => item.meta && item.meta.title)
    .map(item => ({ path: item.path, title: item.meta.title }))
)

// 顶栏展示名：优先昵称，其次登录账号，最后兜底“用户”，保证任何登录数据缺失时仍有文本
const displayName = computed(() => auth.user.nickname || auth.user.username || '用户')
// 文字头像内容：取展示名首字符并转大写；头像图片缺失时作为占位内容
const initial = computed(() => displayName.value.slice(0, 1).toUpperCase())

// 下拉菜单统一指令处理：command 来自 el-dropdown-item 的 command 属性
async function handleCommand(command) {
  // 只有退出登录需要处理，其余指令当前忽略
  if (command === 'logout') {
    // 先等待后端注销完成（logout 内部会清理登录态），再移除动态路由，最后跳转登录页
    await logout()
    // 移除本次会话通过 addDynamicRoutes 注入的路由，防止退出后仍能访问旧页面
    clearDynamicRoutes()
    // 跳转到登录页（不带 redirect，退出属于主动离开）
    router.push('/login')
  }
}
</script>

<style scoped>
/* 顶栏根节点：flex 两端对齐（面包屑靠左、操作区靠右）；高度与父级 el-header 一致 56px；
   左右 20px 内边距与页面内容的视觉边距保持一致 */
.navbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 56px;
  padding: 0 20px;
}

/* 面包屑基础字号：略小于正文，作为辅助定位信息不喧宾夺主 */
.navbar-breadcrumb {
  font-size: 14px;
}

/* 面包屑普通层级：使用次级文字色 --app-text-3 与中等字重，和最后一级形成对比；
   :deep 用于穿透 Element Plus 组件内部的私有类名（scoped 样式默认无法直达子组件内部） */
.navbar-breadcrumb :deep(.el-breadcrumb__inner) {
  color: var(--app-text-3);
  font-weight: 500;
}

/* 最后一级（当前页面）：提升为主文字色并加粗，让用户一眼确认当前所在页面 */
.navbar-breadcrumb :deep(.el-breadcrumb__item:last-child .el-breadcrumb__inner) {
  color: var(--app-text-1);
  font-weight: 600;
}

/* 分隔符：用最浅一级文字色 --app-text-4，弱化“/”的视觉重量 */
.navbar-breadcrumb :deep(.el-breadcrumb__separator) {
  color: var(--app-text-4);
}

/* 右侧操作区：水平居中排列，gap 4px 让主题按钮与用户入口间距紧凑 */
.navbar-right {
  display: flex;
  align-items: center;
  gap: 4px;
}

/* 用户入口：头像+昵称+箭头整体可点击，通过内边距和圆角构成一个“悬浮按钮”外形；
   outline:none 去掉获得焦点时的默认描边（点击后会由 hover 背景提供反馈） */
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

/* 悬停态：使用品牌色浅底 --brand-primary-soft，暗示整块可点击且与主题色呼应 */
.user-entry:hover {
  background: var(--brand-primary-soft);
}

/* 文字头像：品牌渐变作底色 + 白色首字母；投影使用 --brand-glow，使头像与主题色保持统一 */
.user-avatar {
  color: #fff;
  font-weight: 600;
  background: var(--brand-gradient);
  box-shadow: 0 2px 6px var(--brand-glow);
}

/* 昵称字号跟随全局基准变量 --app-font-base，保持和其他正文一致 */
.user-name {
  font-size: var(--app-font-base);
  font-weight: 500;
}

/* 下拉箭头：弱化为次级色并使用小字号，仅作为展开提示 */
.user-arrow {
  color: var(--app-text-3);
  font-size: 12px;
}
</style>
