import axios from 'axios'
import { ElMessage } from 'element-plus'
import { auth, setToken, resetAuth } from '@/store/auth'
import router from '@/router'

// 统一响应结构：{ code, msg, data }；code=200 成功；401 未登录；403 无权限；500 失败
const service = axios.create({
  baseURL: '/api',
  timeout: 30000
})

// 请求拦截：自动携带 token
service.interceptors.request.use(
  config => {
    if (auth.token) {
      config.headers.Authorization = 'Bearer ' + auth.token
    }
    return config
  },
  error => Promise.reject(error)
)

// 响应拦截
service.interceptors.response.use(
  response => {
    // 文件流（如代码生成 ZIP 下载）直接返回原始 response
    if (response.config.responseType === 'blob') {
      return response
    }
    const res = response.data

    // 静默续期：若响应头携带 X-Refresh-Token 则更新本地 token
    const newToken = response.headers && response.headers['x-refresh-token']
    if (newToken) {
      setToken(newToken)
    }

    if (res.code === 200) {
      return res
    }

    if (res.code === 401) {
      resetAuth()
      ElMessage.error(res.msg || '登录已过期，请重新登录')
      if (router.currentRoute.value.path !== '/login') {
        router.push('/login')
      }
    } else {
      ElMessage.error(res.msg || '操作失败')
    }
    return Promise.reject(new Error(res.msg || 'Error'))
  },
  error => {
    const resp = error.response
    if (resp && resp.data && !Blob.prototype.isPrototypeOf(resp.data) && resp.data.code !== undefined) {
      const res = resp.data
      if (res.code === 401) {
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
    ElMessage.error(
      error.message === 'Network Error'
        ? '网络连接异常，请检查后端服务'
        : error.message || '请求失败'
    )
    return Promise.reject(error)
  }
)

export default service
