// 字典工具：把后端“字典类型 → 字典项列表”的数据缓存到前端，供表格翻译与下拉选项复用。
// 设计要点：全局只拉一次、并发去重、失败不阻塞页面；数据是响应式的，字典到位后页面会自动刷新显示。
// 依赖：utils/request。
import { reactive } from 'vue'
import request from '@/utils/request'

// 字典全局缓存：{ [dict_type]: [{ dict_label, dict_value }] }
// reactive 让所有引用 state.dicts 的模板在字典加载完成后自动重新渲染
const state = reactive({
  dicts: {},
  // 是否已完成一次成功加载，避免每次路由跳转都重复请求
  loaded: false
})

// 进行中的请求 Promise：并发场景（多个页面同时触发）下复用同一个请求，防止重复打后端
let loading = null

// 拉取全部字典并缓存
// 返回 Promise，调用方可以选择 await（如导出前需要翻译）或不 await（如路由守卫中的预热）
export function loadDicts() {
  // 已加载完成直接返回，保证幂等
  if (state.loaded) return Promise.resolve()
  // 已有请求在途则复用，避免并发重复请求
  if (loading) return loading
  loading = request
    .get('/system/dict/data/all')
    .then(res => {
      // 后端返回的是按类型分组的数据，这里转换成以 dict_type 为键的 Map，查询更快
      const map = {}
      for (const item of res.data || []) {
        map[item.dict_type] = item.list || []
      }
      state.dicts = map
      state.loaded = true
    })
    // 失败时静默：字典只影响展示文案，不应打断业务流程；loaded 保持 false，下次进入页面可重试
    .catch(() => {})
    .finally(() => {
      // 无论成功失败都清空在途标记，允许后续重试
      loading = null
    })
  return loading
}

// 字典翻译：label(dictType, value)，未匹配时回退显示原值
// 返回 '-' 表示“空值”，避免表格里出现空白单元格，视觉上更整齐
export function dictLabel(dictType, value) {
  if (value === undefined || value === null || value === '') return '-'
  const list = (state.dicts && state.dicts[dictType]) || []
  // 统一转字符串比较：后端可能返回数字型 value，而字典项通常是字符串
  const hit = list.find(d => String(d.dict_value) === String(value))
  // 找不到时返回原值而不是空白：便于排查是“字典未配置”还是“值本身为空”
  return hit ? hit.dict_label : String(value)
}

// 获取某类型的字典项列表（用于下拉选项）
// 返回值直接引用缓存数组，调用方只读使用，不要原地修改
export function dictOptions(dictType) {
  return (state.dicts && state.dicts[dictType]) || []
}

// 别名：代码生成器产出的页面使用 dictList
// 保留别名是为了让自动生成的代码无需改动即可运行
export const dictList = dictOptions

// 暴露加载状态：少数页面需要在字典加载完成后再渲染（如打印模板需要中文标签）
export function dictLoaded() {
  return state.loaded
}
