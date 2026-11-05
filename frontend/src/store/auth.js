// 登录态store：用一个 reactive 对象承载 token、用户信息、权限码与菜单，替代引入 Pinia 的重量级方案。
// 之所以用轻量方案：项目只有这一份跨页面共享状态，reactive + localStorage 已足够，且更容易被旧代码直接引用。
// 依赖：utils/request（接口调用封装）。
import { reactive } from 'vue'
// 统一请求实例，已配置 baseURL、token 注入与错误提示
import request from '@/utils/request'

// localStorage 中 token 的键名；放在常量里避免各处手写字符串导致拼写不一致
const TOKEN_KEY = 'da_token'
// 用户信息的缓存键名，用于刷新时先展示上次的头像/昵称，减少“白屏等待用户信息”的观感
const USER_KEY = 'da_user'

// 读取本地缓存的用户信息；缓存可能被手动篡改或残留旧结构，因此用 try/catch 兜底返回空对象
function readCachedUser() {
  try {
    // JSON.parse 遇到非 JSON 字符串（例如旧版本存的纯字符串）会抛错，交给 catch 处理
    return JSON.parse(localStorage.getItem(USER_KEY)) || {}
  } catch (e) {
    return {}
  }
}

// 轻量响应式全局登录态（不使用 pinia）
// 直接导出 reactive 对象，任何组件 import 后访问 auth.xxx 都能自动追踪依赖并响应式更新
export const auth = reactive({
  // 初始化时同步读取 token：刷新页面后无需等待接口就能判断“是否已登录”
  token: localStorage.getItem(TOKEN_KEY) || '',
  // 先用本地缓存的用户信息占位，接口返回后再覆盖为最新数据
  user: readCachedUser(),
  // 权限码列表，形如 ['system:user:list', ...]；由登录/用户信息接口下发
  perms: [],
  // 菜单树，动态路由与侧边栏都依赖它渲染
  menus: [],
  // 是否已完成一次完整的用户信息拉取；路由守卫用它判断是否需要请求 /auth/userinfo
  loaded: false
})

// 写入/清除 token，并同步持久化到 localStorage，保证刷新后仍然生效
export function setToken(token) {
  // 内存态始终赋值为字符串，避免 null/undefined 混入后续请求头拼接
  auth.token = token || ''
  if (token) {
    localStorage.setItem(TOKEN_KEY, token)
  } else {
    localStorage.removeItem(TOKEN_KEY)
  }
}

// 权限判断，支持 '*:*:*' 通配
// 说明：perm 为空时返回 true，表示该处不要求权限（例如所有登录用户可见的按钮）
export function hasPerm(perm) {
  if (!perm) return true
  const list = auth.perms || []
  // 超级管理员约定使用 '*:*:*'，命中后无需再逐个比对
  if (list.includes('*:*:*')) return true
  // 数组形式表示“任一满足即可”，与后端注解的 hasAnyPerm 语义保持一致
  if (Array.isArray(perm)) {
    return perm.some(p => list.includes(p))
  }
  return list.includes(perm)
}

// 登录：调用后端换取 token，并一次性拿到用户、权限、菜单，减少登录后的串行请求
export async function login(data) {
  const res = await request.post('/auth/login', data)
  // res.data 是后端统一响应中的业务数据；兜底为空对象避免解构报错
  const d = res.data || {}
  // 先落 token，后续请求头才能自动携带
  setToken(d.token)
  auth.user = d.user || {}
  auth.perms = d.perms || []
  auth.menus = d.menus || []
  // 登录接口已经返回了完整信息，标记为已加载，路由守卫不必再请求 userinfo
  auth.loaded = true
  // 用户信息写入缓存，下次刷新可先展示
  localStorage.setItem(USER_KEY, JSON.stringify(auth.user))
  return d
}

// 刷新页面后拉取用户信息
// 与 login 的差别：这里不接收表单，只是用已存的 token 换取最新权限（权限变更后刷新即可生效）
export async function fetchUserinfo() {
  const res = await request.get('/auth/userinfo')
  const d = res.data || {}
  // 后端可能在响应中续签 token，此时同步更新本地，实现无感续期
  if (d.token) {
    setToken(d.token)
  }
  auth.user = d.user || {}
  auth.perms = d.perms || []
  auth.menus = d.menus || []
  auth.loaded = true
  localStorage.setItem(USER_KEY, JSON.stringify(auth.user))
  return d
}

// 确保用户信息只加载一次：已加载则直接 resolve，未加载则发起请求
// 返回 Promise 便于守卫 await，从而保证动态路由在菜单数据到位后才构建
export function ensureUserLoaded() {
  if (auth.loaded) return Promise.resolve()
  return fetchUserinfo()
}

// 退出登录
export async function logout() {
  try {
    // 通知后端注销会话（例如清理 Redis 中的 token）；后端失败不应阻止前端退出
    await request.post('/auth/logout')
  } catch (e) {
    // 忽略登出接口异常，本地状态照样清理
  }
  // 无论接口是否成功都清空本地，避免用户“点了退出却还处于登录态”
  resetAuth()
}

// 重置登录态：401 过期、主动退出、切换账号时统一调用
export function resetAuth() {
  // 传空字符串会同时清除内存 token 与 localStorage
  setToken('')
  auth.user = {}
  auth.perms = []
  auth.menus = []
  auth.loaded = false
  localStorage.removeItem(USER_KEY)
}
