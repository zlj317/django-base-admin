import request from '@/utils/request'

// 学生信息表 模块接口（由代码生成器生成）
// request 封装已带 baseURL '/api'，这里只写业务前缀
const BASE = '/student'

export function listApi(params) {
  return request({ url: BASE + '/list', method: 'get', params }).then((res) => res.data)
}

export function createApi(data) {
  return request({ url: BASE + '/create', method: 'post', data })
}

export function updateApi(id, data) {
  return request({ url: `${BASE}/update/${id}`, method: 'put', data })
}

export function deleteApi(ids) {
  return request({ url: BASE + '/delete', method: 'delete', data: { ids } })
}

export function exportApi(params) {
  return request({ url: BASE + '/exportData', method: 'get', params, responseType: 'blob' })
}

export function templateApi() {
  return request({ url: BASE + '/importTemplate', method: 'get', responseType: 'blob' })
}

export function importApi(file) {
  const formData = new FormData()
  formData.append('file', file)
  return request({ url: BASE + '/importData', method: 'post', data: formData,
    headers: { 'Content-Type': 'multipart/form-data' } }).then((res) => res.data)
}
