// 学生信息表模块的接口封装（由代码生成器生成的典型 CRUD 示例）。
// 所有函数最终都走 utils/request，因此自动获得 token 注入、统一错误提示与 blob 下载支持。
import request from '@/utils/request'

// 学生信息表 模块接口（由代码生成器生成）
// request 封装已带 baseURL '/api'，这里只写业务前缀
const BASE = '/student'

// 分页查询：params 通常包含 page、page_size 以及各查询条件
// 这里多一步 .then(res => res.data)：让调用方直接拿到 { list, total }，少写一层 res.data
export function listApi(params) {
  return request({ url: BASE + '/list', method: 'get', params }).then((res) => res.data)
}

// 新增：data 为表单对象；返回后端统一响应体（含新建记录 id）
export function createApi(data) {
  return request({ url: BASE + '/create', method: 'post', data })
}

// 修改：id 走路径参数，data 为待更新字段；后端据此定位记录
export function updateApi(id, data) {
  return request({ url: `${BASE}/update/${id}`, method: 'put', data })
}

// 批量删除：ids 数组放在请求体里（DELETE 也允许带 body，便于一次删除多条）
export function deleteApi(ids) {
  return request({ url: BASE + '/delete', method: 'delete', data: { ids } })
}

// 导出数据：responseType='blob' 让拦截器直接返回原始响应，
// 调用方再用 utils/download 的 saveBlob 保存为 Excel 文件
export function exportApi(params) {
  return request({ url: BASE + '/exportData', method: 'get', params, responseType: 'blob' })
}

// 下载导入模板：同样是文件流，供用户按模板格式填写后再上传
export function templateApi() {
  return request({ url: BASE + '/importTemplate', method: 'get', responseType: 'blob' })
}

// 导入数据：文件必须用 FormData 承载（multipart/form-data），不能直接传 JSON
export function importApi(file) {
  const formData = new FormData()
  // 字段名 'file' 需与后端接收参数名保持一致
  formData.append('file', file)
  // 显式设置 multipart 头（axios 会自动补 boundary）；成功分支直接返回业务数据
  return request({ url: BASE + '/importData', method: 'post', data: formData,
    headers: { 'Content-Type': 'multipart/form-data' } }).then((res) => res.data)
}
