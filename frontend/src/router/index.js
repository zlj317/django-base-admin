import { createRouter, createWebHistory } from 'vue-router'
import Layout from '@/layout/index.vue'
import { auth, ensureUserLoaded, resetAuth } from '@/store/auth'
import { loadDicts } from '@/utils/dict'

// views 组件映射：component 字符串（如 'system/user/index'）→ 动态组件
const viewModules = import.meta.glob('../views/**/*.vue')

function resolveComponent(component) {
  if (!component) return null
  return viewModules[`../views/${component}.vue`] || null
}

// 静态路由
export const constantRoutes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/login/index.vue'),
    meta: { title: '登录' }
  },
  { path: '/', redirect: '/dashboard' },
  {
    path: '/dashboard',
    component: Layout,
    children: [
      {
        path: '',
        name: 'Dashboard',
        component: () => import('@/views/dashboard/index.vue'),
        meta: { title: '系统首页' }
      }
    ]
  },
  {
    // 代码生成配置页（隐藏页面，由列表页跳转进入，不在菜单中显示）
    path: '/gen/edit/:id',
    component: Layout,
    children: [
      {
        path: '',
        name: 'GenEdit',
        component: () => import('@/views/gen/edit/index.vue'),
        meta: { title: '生成配置' }
      }
    ]
  },
  {
    // 流程设计器（隐藏页面，由流程模型列表跳转进入）
    path: '/workflow/design/:id',
    component: Layout,
    children: [
      {
        path: '',
        name: 'WorkflowDesign',
        component: () => import('@/views/workflow/model/design.vue'),
        meta: { title: '流程设计' }
      }
    ]
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/error/404.vue'),
    meta: { title: '404' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes: constantRoutes
})

// 递归收集菜单树中的叶子页面（支持 工作流程 > 流程管理 > 页面 这种三级结构）
function collectLeaves(menus, prefix, leaves) {
  ;(menus || []).forEach(menu => {
    if (menu.menu_type === 'C') {
      const comp = resolveComponent(menu.component)
      if (!comp) return
      leaves.push({
        path: prefix ? prefix + '/' + menu.path : menu.path,
        name: 'menu-' + menu.id,
        component: comp,
        meta: { title: menu.menu_name, icon: menu.icon }
      })
    } else if (menu.menu_type === 'M' && menu.children) {
      collectLeaves(menu.children, prefix ? prefix + '/' + menu.path : menu.path, leaves)
    }
  })
}

// 根据 menus 树构建动态路由：顶级目录(M) 挂 Layout，递归找到所有页面菜单(C)
function buildDynamicRoutes(menus) {
  const routes = []
  ;(menus || []).forEach(top => {
    if (top.menu_type !== 'M') return
    const children = []
    collectLeaves(top.children, '', children)
    if (!children.length) return
    routes.push({
      path: '/' + String(top.path || '').replace(/^\//, ''),
      name: 'dir-' + top.id,
      component: Layout,
      meta: { title: top.menu_name, icon: top.icon },
      children
    })
  })
  return routes
}

let addedNames = []
let dynamicAdded = false

export function addDynamicRoutes() {
  if (dynamicAdded) return
  addedNames.forEach(name => {
    if (router.hasRoute(name)) router.removeRoute(name)
  })
  addedNames = []
  buildDynamicRoutes(auth.menus).forEach(route => {
    router.addRoute(route)
    addedNames.push(route.name)
  })
  dynamicAdded = true
}

export function clearDynamicRoutes() {
  addedNames.forEach(name => {
    if (router.hasRoute(name)) router.removeRoute(name)
  })
  addedNames = []
  dynamicAdded = false
}

router.beforeEach(async to => {
  // 已登录访问登录页 → 跳首页
  if (to.path === '/login') {
    return auth.token ? { path: '/dashboard' } : true
  }
  // 未登录 → 跳登录页
  if (!auth.token) {
    return {
      path: '/login',
      query: to.fullPath && to.fullPath !== '/' ? { redirect: to.fullPath } : {}
    }
  }
  // 首次加载：拉取用户信息
  if (!auth.loaded) {
    try {
      await ensureUserLoaded()
    } catch (e) {
      resetAuth()
      return { path: '/login' }
    }
  }
  // 拉取字典缓存（不阻塞跳转，加载完成后响应式更新）
  loadDicts()
  // 注册动态路由后重新解析当前目标（不能用 name，否则会停留在 404 匹配结果上）
  if (!dynamicAdded) {
    addDynamicRoutes()
    return { path: to.path, query: to.query, hash: to.hash, replace: true }
  }
  return true
})

export default router
