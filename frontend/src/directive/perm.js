import { hasPerm } from '@/store/auth'

// 按钮级权限指令：v-perm="'system:user:create'" 或 v-perm="['a','b']"
export const perm = {
  mounted(el, binding) {
    check(el, binding)
  },
  updated(el, binding) {
    check(el, binding)
  }
}

function check(el, binding) {
  const value = binding.value
  if (value === undefined || value === null || value === '') return
  if (!hasPerm(value)) {
    el.dataset.permHidden = '1'
    el.style.display = 'none'
  } else if (el.dataset && el.dataset.permHidden === '1') {
    delete el.dataset.permHidden
    el.style.display = ''
  }
}

export default perm
