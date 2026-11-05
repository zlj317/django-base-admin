// 统一请求封装：全项目所有 HTTP 调用都经由这里发出，集中处理鉴权、统一响应结构、错误提示与登录过期跳转。
// 约定后端响应体为 { code, msg, data }：code=200 成功；401 未登录/过期；403 无权限；500 业务失败。
// 副作用：会写入 token、弹出错误提示、在 401 时清空登录态并跳转登录页。
import axios from 'axios'
// 使用 Element Plus 的消息提示做统一报错（项目存量交互风格，保持与旧页面一致）
import { ElMessage } from 'element-plus'
// auth 提供当前 token；setToken 用于接收后端续签的 token；resetAuth 用于登录失效时清空状态
import { auth, setToken, resetAuth } from '@/store/auth'
// 路由实例用于 401 时跳转登录页；在这里引入不会形成循环依赖（router 只在守卫里用到 auth）
import router from '@/router'

// 统一响应结构：{ code, msg, data }；code=200 成功；401 未登录；403 无权限；500 失败
// baseURL 固定为 /api：开发期由 Vite 代理转发到 Django，生产期由 Nginx 同域转发
const service = axios.create({
  baseURL: '/api',
  // 30 秒超时：覆盖大部分报表/导入类接口，又不会让用户长时间无响应
  timeout: 30000
})

// 请求拦截：自动携带 token
// 统一在这里注入，业务代码就不必每次手写 Authorization，也避免漏写导致 401
service.interceptors.request.use(
  config => {
    if (auth.token) {
      config.headers.Authorization = 'Bearer ' + auth.token
    }
    // 必须返回 config，否则 axios 拿不到请求配置
    return config
  },
  // 请求在发出前就失败（如参数序列化异常）时直接透传，交由调用方 catch
  error => Promise.reject(error)
)

// 响应拦截
// 成功分支：把 axios 的 response 收敛成后端业务体；失败分支：统一提示并 reject，调用方只需处理业务成功路径
service.interceptors.response.use(
  response => {
    // 文件流（如代码生成 ZIP 下载）直接返回原始 response
    // 判断依据是调用方显式设置了 responseType='blob'，此时 response.data 是二进制而非 JSON
    if (response.config.responseType === 'blob') {
      return response
    }
    // axios 默认把 JSON 放在 response.data，这里取出后端的 { code, msg, data }
    const res = response.data

    // 静默续期：若响应头携带 X-Refresh-Token 则更新本地 token
    // 后端在临近过期时下发新 token，前端无感替换，避免用户操作中途被踢回登录页
    const newToken = response.headers && response.headers['x-refresh-token']
    if (newToken) {
      setToken(newToken)
    }

    // 业务成功：直接返回业务体，调用方拿到的 res.data 就是真实数据
    if (res.code === 200) {
      return res
    }

    // 登录态失效：清理内存与本地存储，提示后跳转登录页
    if (res.code === 401) {
      resetAuth()
      ElMessage.error(res.msg || '登录已过期，请重新登录')
      // 已经在登录页时不再跳转，避免重复导航造成的路由抖动
      if (router.currentRoute.value.path !== '/login') {
        router.push('/login')
      }
    } else {
      // 其余业务错误（403/500 等）只提示，不改变登录态
      ElMessage.error(res.msg || '操作失败')
    }
    // 统一 reject：调用方无需再判断 code，只要是 catch 就代表失败
    return Promise.reject(new Error(res.msg || 'Error'))
  },
  error => {
    // 网络层错误（HTTP 4xx/5xx）也尽量取出后端返回的业务体，保证提示文案与成功分支一致
    const resp = error.response
    // 排除二进制响应：下载失败的 blob 无法按 JSON 解析，直接走下面的通用提示
    if (resp && resp.data && !Blob.prototype.isPrototypeOf(resp.data) && resp.data.code !== undefined) {
      const res = resp.data
      if (res.code === 401) {
        // HTTP 状态码与业务码可能同时为 401，这里做同样的失效处理
        resetAuth()
        ElMessage.error(res.msg || '登录已过期，请重新登录')
        if (router.currentRoute.value.path !== '/login') {
          router.push('/login')
        }
      } else {
        ElMessage.error(res.msg || '请求失败')
      }
      return Promise.reject(new Error(res.msg || 'Error'))
    }
    // 无法解析业务体时按 axios 的错误信息提示；Network Error 单独翻译成更易懂的中文
    ElMessage.error(
      error.message === 'Network Error'
        ? '网络连接异常，请检查后端服务'
        : error.message || '请求失败'
    )
    return Promise.reject(error)
  }
)

// 导出配置好的实例：业务代码用 request.get/post/... 或 request({ url, method }) 两种写法均可
export default service
