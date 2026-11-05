// 按钮级权限指令 v-perm：按当前用户的权限码决定按钮/链接是否展示。
// 与后端权限校验互补：前端隐藏只是体验优化，真正的安全边界仍在接口层。
// 依赖：store/auth 的 hasPerm。
import { hasPerm } from '@/store/auth'

// 按钮级权限指令：v-perm="'system:user:create'" 或 v-perm="['a','b']"
// 定义 mounted 与 updated 两个钩子：首次渲染与权限变化后都重新判断
export const perm = {
  mounted(el, binding) {
    // 元素刚插入 DOM 时立即判断一次，避免先显示再隐藏造成闪烁
    check(el, binding)
  },
  updated(el, binding) {
    // 权限列表可能在用户信息刷新后变化（例如切换租户），更新时再判断一次以同步状态
    check(el, binding)
  }
}

// 实际判断逻辑：无权限则隐藏元素，恢复权限时还原
function check(el, binding) {
  const value = binding.value
  // 未绑定权限值视为“不需要控制”，保持元素原样（常见于复制粘贴遗留的 v-perm）
  if (value === undefined || value === null || value === '') return
  if (!hasPerm(value)) {
    // 用 dataset 打标记而不是直接删除 DOM：
    // 1) 避免破坏 v-if/v-for 的父级结构；2) 便于在 updated 中精确还原 display
    el.dataset.permHidden = '1'
    el.style.display = 'none'
  } else if (el.dataset && el.dataset.permHidden === '1') {
    // 只有此前被本指令隐藏过的元素才还原，避免覆盖组件自身设置的 display 值
    delete el.dataset.permHidden
    el.style.display = ''
  }
}

// 同时提供默认导出，兼容 import perm from '@/directive/perm' 的写法
export default perm
