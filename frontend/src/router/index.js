// 路由中心：既定义“与权限无关的静态页面”，也负责把后端返回的菜单树翻译成动态路由。
// 静态路由覆盖登录、首页、隐藏的配置页、大屏、404；动态路由由登录后的菜单数据驱动，
// 因此同一个前端包可以通过不同角色/租户展示不同的菜单与页面。
// 依赖：layout/index.vue（后台整体布局）、store/auth（登录态与菜单数据）、utils/dict（字典缓存）。
import { createRouter, createWebHistory } from 'vue-router'
// 后台页面的统一外壳：侧边栏、顶栏、标签页等；所有菜单页面都作为它的 children 渲染
import Layout from '@/layout/index.vue'
// auth 是响应式登录态；ensureUserLoaded 用于首次进入时拉取用户信息；resetAuth 清空本地登录态
import { auth, ensureUserLoaded, resetAuth } from '@/store/auth'
// 字典是页面里大量下拉框/标签的数据来源，进入系统后统一预热一次
import { loadDicts } from '@/utils/dict'

// 使用 Vite 的 glob 预扫描所有页面组件，返回 { '../views/xxx.vue': () => Promise<组件> } 的映射。
// 这样后端只需返回 component 字符串（例如 'system/user/index'），前端即可按约定路径找到对应组件，
// 新增页面时不需要再手动维护一张“组件注册表”。
const viewModules = import.meta.glob('../views/**/*.vue')

// 把菜单里的 component 字符串解析成真正的异步组件加载函数；
// 返回 null 表示菜单配置写错了或页面不存在，调用方会跳过该菜单，避免路由指向空白页。
function resolveComponent(component) {
  // 空值直接判空，防止拼出 '../views/undefined.vue' 这类无效路径
  if (!component) return null
  // 与 glob 的 key 保持完全一致的路径格式（不带前导斜杠、带 .vue 后缀）
  return viewModules[`../views/${component}.vue`] || null
}

// 静态路由：无论用户拥有什么权限都必须存在的页面
export const constantRoutes = [
  {
    // 登录页：不挂 Layout，整页独立展示
    path: '/login',
    name: 'Login',
    component: () => import('@/views/login/index.vue'),
    meta: { title: '登录' }
  },
  // 根路径统一重定向到系统首页，避免访问 / 时出现空白
  { path: '/', redirect: '/dashboard' },
  {
    // 系统首页固定可用，不做权限控制（所有登录用户都应能看到工作台）
    path: '/dashboard',
    component: Layout,
    children: [
      {
        // 子路由使用空 path，最终地址就是 /dashboard
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
    // 大屏预览/展示页（不挂后台布局，铺满整个窗口）
    path: '/bi/view/:id',
    name: 'BiScreenView',
    component: () => import('@/views/bi/screen/view.vue'),
    meta: { title: '大屏预览' }
  },
  {
    // 大屏分享访问页（按 share_url 中的 token 打开）
    // 与预览页共用同一个组件，由组件内部根据路由参数决定加载方式
    path: '/bi/share/:token',
    name: 'BiScreenShare',
    component: () => import('@/views/bi/screen/view.vue'),
    meta: { title: '大屏分享' }
  },
  {
    // 通配兜底：任何未匹配的地址都进入 404，避免出现原生空白页
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/error/404.vue'),
    meta: { title: '404' }
  }
]

// 创建路由实例
const router = createRouter({
  // HTML5 History 模式：地址栏是 /system/user 这种干净路径，刷新需要后端做 index.html 回退
  history: createWebHistory(),
  // 初始只注册静态路由；动态菜单路由在守卫里登录成功后追加
  routes: constantRoutes
})

// 递归收集菜单树中的叶子页面（支持 工作流程 > 流程管理 > 页面 这种三级结构）。
// menus: 当前层级的菜单数组；prefix: 已累积的父级路径；leaves: 收集结果。
function collectLeaves(menus, prefix, leaves) {
  // 开头的分号是为了防止上一行以括号/数组结尾时被解析成函数调用，属于防御性写法
  ;(menus || []).forEach(menu => {
    // menu_type === 'C' 表示“页面/组件”类菜单，它才会真正生成一条可访问的路由
    if (menu.menu_type === 'C') {
      const comp = resolveComponent(menu.component)
      // 组件找不到说明菜单配置有误（或页面已删除），直接跳过，避免注册出打不开的路由
      if (!comp) return
      leaves.push({
        // 拼接完整访问路径：父目录路径 + 当前菜单 path；顶层页面则直接用自身 path
        path: prefix ? prefix + '/' + menu.path : menu.path,
        // 路由名带上菜单 id，保证唯一，便于后续按名字移除/重建
        name: 'menu-' + menu.id,
        // 懒加载组件，实现按页面拆分打包
        component: comp,
        // meta 中的 title/icon 会被侧边栏和面包屑复用
        meta: { title: menu.menu_name, icon: menu.icon }
      })
    } else if (menu.menu_type === 'M' && menu.children) {
      // 'M' 是目录节点：本身不产生页面，只把路径前缀往下传并继续递归
      collectLeaves(menu.children, prefix ? prefix + '/' + menu.path : menu.path, leaves)
    }
  })
}

// 根据 menus 树构建动态路由：顶级目录(M) 挂 Layout，递归找到所有页面菜单(C)
function buildDynamicRoutes(menus) {
  const routes = []
  // 再次使用前置分号，避免与上一句的数组字面量产生语法歧义
  ;(menus || []).forEach(top => {
    // 只有目录节点才作为 Layout 的直接子级；散落的页面菜单不单独建一级布局
    if (top.menu_type !== 'M') return
    const children = []
    // 从目录自身开始收集叶子页面，前缀从空字符串起步（目录路径在下面拼到父路由上）
    collectLeaves(top.children, '', children)
    // 目录下一个有效页面都没有时不注册该路由，防止出现只能看到空布局的菜单
    if (!children.length) return
    routes.push({
      // 去掉菜单路径可能携带的前导斜杠，再统一补一个 '/'，避免出现 '//system' 这样的双斜杠
      path: '/' + String(top.path || '').replace(/^\//, ''),
      // 目录路由名同样带 id，便于精确移除
      name: 'dir-' + top.id,
      component: Layout,
      // 目录级的标题/图标给侧边栏一级菜单使用
      meta: { title: top.menu_name, icon: top.icon },
      children
    })
  })
  return routes
}

// 记录当前已注入的动态路由名，用于切换账号/退出时精确清理，避免残留上一位用户的菜单
let addedNames = []
// 标记动态路由是否已注入，防止每次导航都重复添加
let dynamicAdded = false

// 注入动态路由：登录成功后或首次进入受保护页面时调用
export function addDynamicRoutes() {
  // 已注入则直接返回，保证幂等（守卫中可能会被多次触发）
  if (dynamicAdded) return
  // 先清理旧路由，防止热更新或重复调用造成同名路由冲突
  addedNames.forEach(name => {
    if (router.hasRoute(name)) router.removeRoute(name)
  })
  addedNames = []
  // 按当前用户的菜单树重新生成并逐条注册
  buildDynamicRoutes(auth.menus).forEach(route => {
    router.addRoute(route)
    addedNames.push(route.name)
  })
  dynamicAdded = true
}

// 清理动态路由：退出登录或切换账号时调用，保证下一位用户不会看到上一位的菜单
export function clearDynamicRoutes() {
  addedNames.forEach(name => {
    if (router.hasRoute(name)) router.removeRoute(name)
  })
  addedNames = []
  // 复位标记，使下次登录可以重新注入
  dynamicAdded = false
}

// 全局前置守卫：负责登录校验、用户信息预加载、字典预热与动态路由注入
router.beforeEach(async to => {
  // 已登录访问登录页 → 跳首页
  // 目的是避免登录成功后手动回退到 /login 时又出现登录表单
  if (to.path === '/login') {
    return auth.token ? { path: '/dashboard' } : true
  }
  // 未登录 → 跳登录页
  // 同时把原本要访问的完整地址放进 redirect，登录成功后可以回到原页面
  if (!auth.token) {
    return {
      path: '/login',
      query: to.fullPath && to.fullPath !== '/' ? { redirect: to.fullPath } : {}
    }
  }
  // 首次加载：拉取用户信息
  // 刷新页面后 token 还在内存外的 localStorage，但用户信息、权限、菜单都需要重新获取
  if (!auth.loaded) {
    try {
      await ensureUserLoaded()
    } catch (e) {
      // 拉取失败通常意味着 token 失效：清空本地状态并回登录页，避免带着脏状态继续访问
      resetAuth()
      return { path: '/login' }
    }
  }
  // 拉取字典缓存（不阻塞跳转，加载完成后响应式更新）
  // 这里不 await：字典加载失败不应阻塞页面进入，页面会先显示原始值，字典到位后自动刷新
  loadDicts()
  // 注册动态路由后重新解析当前目标（不能用 name，否则会停留在 404 匹配结果上）
  // 因为首次解析 to 时动态路由尚未注册，命中的是通配 404；添加路由后需按原 path 再匹配一次
  if (!dynamicAdded) {
    addDynamicRoutes()
    return { path: to.path, query: to.query, hash: to.hash, replace: true }
  }
  // 动态路由已就绪，正常放行
  return true
})

// 导出路由实例，供 main.js 安装以及 request.js 在 401 时跳转登录页
export default router
