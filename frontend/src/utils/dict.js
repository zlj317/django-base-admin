import { reactive } from 'vue'
import request from '@/utils/request'

// 字典全局缓存：{ [dict_type]: [{ dict_label, dict_value }] }
const state = reactive({
  dicts: {},
  loaded: false
})

let loading = null

// 拉取全部字典并缓存
export function loadDicts() {
  if (state.loaded) return Promise.resolve()
  if (loading) return loading
  loading = request
    .get('/system/dict/data/all')
    .then(res => {
      const map = {}
      for (const item of res.data || []) {
        map[item.dict_type] = item.list || []
      }
      state.dicts = map
      state.loaded = true
    })
    .catch(() => {})
    .finally(() => {
      loading = null
    })
  return loading
}

// 字典翻译：label(dictType, value)，未匹配时回退显示原值
export function dictLabel(dictType, value) {
  if (value === undefined || value === null || value === '') return '-'
  const list = (state.dicts && state.dicts[dictType]) || []
  const hit = list.find(d => String(d.dict_value) === String(value))
  return hit ? hit.dict_label : String(value)
}

// 获取某类型的字典项列表（用于下拉选项）
export function dictOptions(dictType) {
  return (state.dicts && state.dicts[dictType]) || []
}

// 别名：代码生成器产出的页面使用 dictList
export const dictList = dictOptions

export function dictLoaded() {
  return state.loaded
}
