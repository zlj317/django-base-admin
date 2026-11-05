// 3D 可视化模块 API 封装：集中维护接口路径，页面只关心业务参数。
// 后端统一挂在 /api/scene3d/ 下，响应结构为 { code, msg, data }，由 request 拦截器统一处理。
import request from '@/utils/request'

// 通用 GET：params 为空时不额外传参，避免出现空对象查询串
const get = (url, params) => request.get(url, params ? { params } : undefined)
// 通用 POST：用于新增、保存、发布等动作
const post = (url, data) => request.post(url, data || {})
// 通用 PUT：用于编辑
const put = (url, data) => request.put(url, data || {})
// 通用 DELETE：axios 的 data 需放在 config 中，批量删除约定传 { ids }
const del = (url, data) => request.delete(url, { data })

// ---------------- 场景分类 ----------------
export const categoryApi = {
  list: params => get('/scene3d/category/list', params),
  create: data => post('/scene3d/category/create', data),
  update: (id, data) => put(`/scene3d/category/update/${id}`, data),
  remove: ids => del('/scene3d/category/delete', { ids })
}

// ---------------- 场景模板 ----------------
export const templateApi = {
  list: params => get('/scene3d/template/list', params),
  create: data => post('/scene3d/template/create', data),
  update: (id, data) => put(`/scene3d/template/update/${id}`, data),
  remove: ids => del('/scene3d/template/delete', { ids })
}

// ---------------- 3D 场景 ----------------
export const sceneApi = {
  list: params => get('/scene3d/list', params),
  detail: id => get(`/scene3d/${id}/detail`),
  create: data => post('/scene3d/create', data),
  update: (id, data) => put(`/scene3d/update/${id}`, data),
  remove: ids => del('/scene3d/delete', { ids }),
  save: (id, data) => post(`/scene3d/${id}/save`, data),
  publish: id => post(`/scene3d/${id}/publish`),
  offline: id => post(`/scene3d/${id}/offline`),
  copy: (id, data) => post(`/scene3d/${id}/copy`, data),
  versions: id => get(`/scene3d/${id}/versions`),
  rollback: (id, versionId) => post(`/scene3d/${id}/rollback`, { version_id: versionId }),
  share: (id, days) => post(`/scene3d/${id}/share`, { expire_days: days }),
  visitLogs: (id, params) => get(`/scene3d/${id}/visit-log`, params),
  exportConfig: id => get(`/scene3d/${id}/export`)
}

// ---------------- 模型资源 ----------------
export const modelApi = {
  list: params => get('/scene3d/model/list', params),
  create: data => post('/scene3d/model/create', data),
  update: (id, data) => put(`/scene3d/model/update/${id}`, data),
  remove: ids => del('/scene3d/model/delete', { ids }),
  preview: id => get(`/scene3d/model/${id}/preview`),
  // 上传使用 multipart/form-data，交给浏览器自动带 boundary
  upload: formData => request.post('/scene3d/model/upload', formData)
}

// ---------------- 场景对象 ----------------
export const objectApi = {
  list: params => get('/scene3d/object/list', params),
  create: data => post('/scene3d/object/create', data),
  update: (id, data) => put(`/scene3d/object/update/${id}`, data),
  remove: ids => del('/scene3d/object/delete', { ids })
}

// ---------------- 数据绑定 ----------------
export const bindingApi = {
  list: params => get('/scene3d/binding/list', params),
  create: data => post('/scene3d/binding/create', data),
  update: (id, data) => put(`/scene3d/binding/update/${id}`, data),
  remove: ids => del('/scene3d/binding/delete', { ids }),
  preview: id => get(`/scene3d/binding/${id}/preview`)
}

// ---------------- 告警规则 / 记录 ----------------
export const alarmApi = {
  rules: params => get('/scene3d/alarm/rule/list', params),
  ruleCreate: data => post('/scene3d/alarm/rule/create', data),
  ruleUpdate: (id, data) => put(`/scene3d/alarm/rule/update/${id}`, data),
  ruleRemove: ids => del('/scene3d/alarm/rule/delete', { ids }),
  records: params => get('/scene3d/alarm/records', params),
  stats: params => get('/scene3d/alarm/stats', params),
  confirm: (id, remark) => post(`/scene3d/alarm/${id}/confirm`, { remark })
}

// ---------------- 巡检路线 / 记录 ----------------
export const patrolApi = {
  list: params => get('/scene3d/route/list', params),
  create: data => post('/scene3d/route/create', data),
  update: (id, data) => put(`/scene3d/route/update/${id}`, data),
  remove: ids => del('/scene3d/route/delete', { ids }),
  play: id => post(`/scene3d/route/${id}/play`),
  records: params => get('/scene3d/route/record/list', params)
}

// ---------------- 访问授权 ----------------
export const permissionApi = {
  list: params => get('/scene3d/permission/list', params),
  create: data => post('/scene3d/permission/create', data),
  update: (id, data) => put(`/scene3d/permission/update/${id}`, data),
  remove: ids => del('/scene3d/permission/delete', { ids })
}

// ---------------- 大屏聚合与分享 ----------------
export const screenApi = {
  data: () => get('/scene3d/screen/data'),
  // 分享数据免登录，直接按 token 取场景详情
  share: token => get(`/scene3d/share/${token}`)
}
