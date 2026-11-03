import { reactive } from 'vue'
import request from '@/utils/request'

const TOKEN_KEY = 'da_token'
const USER_KEY = 'da_user'

function readCachedUser() {
  try {
    return JSON.parse(localStorage.getItem(USER_KEY)) || {}
  } catch (e) {
    return {}
  }
}

// 轻量响应式全局登录态（不使用 pinia）
export const auth = reactive({
  token: localStorage.getItem(TOKEN_KEY) || '',
  user: readCachedUser(),
  perms: [],
  menus: [],
  loaded: false
})

export function setToken(token) {
  auth.token = token || ''
  if (token) {
    localStorage.setItem(TOKEN_KEY, token)
  } else {
    localStorage.removeItem(TOKEN_KEY)
  }
}

// 权限判断，支持 '*:*:*' 通配
export function hasPerm(perm) {
  if (!perm) return true
  const list = auth.perms || []
  if (list.includes('*:*:*')) return true
  if (Array.isArray(perm)) {
    return perm.some(p => list.includes(p))
  }
  return list.includes(perm)
}

export async function login(data) {
  const res = await request.post('/auth/login', data)
  const d = res.data || {}
  setToken(d.token)
  auth.user = d.user || {}
  auth.perms = d.perms || []
  auth.menus = d.menus || []
  auth.loaded = true
  localStorage.setItem(USER_KEY, JSON.stringify(auth.user))
  return d
}

// 刷新页面后拉取用户信息
export async function fetchUserinfo() {
  const res = await request.get('/auth/userinfo')
  const d = res.data || {}
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

export function ensureUserLoaded() {
  if (auth.loaded) return Promise.resolve()
  return fetchUserinfo()
}

export async function logout() {
  try {
    await request.post('/auth/logout')
  } catch (e) {
    // 忽略登出接口异常，本地状态照样清理
  }
  resetAuth()
}

export function resetAuth() {
  setToken('')
  auth.user = {}
  auth.perms = []
  auth.menus = []
  auth.loaded = false
  localStorage.removeItem(USER_KEY)
}
