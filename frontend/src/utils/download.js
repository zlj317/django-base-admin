// 浏览器侧文件/剪贴板工具：导出文件与复制文本，避免每个页面重复实现这类 DOM 操作。
// 全部基于原生 API，无第三方依赖，因此可以安全地被任意页面引入。

// 将 Blob 保存为文件
// 使用临时 <a download> 触发浏览器下载，适用于后端返回的文件流（导出 Excel、下载 ZIP 等）
export function saveBlob(blob, filename) {
  // 为二进制内容创建一个可直接访问的临时 URL
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  // download 属性告诉浏览器“下载而不是打开”，同时指定默认文件名
  link.download = filename
  // 部分浏览器要求链接必须在文档中才能触发点击，因此先挂到 body 再移除
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  // 及时释放对象 URL，避免长时间占用内存（尤其大文件导出）
  window.URL.revokeObjectURL(url)
}

// 复制文本到剪贴板（含降级方案）
// 优先使用异步 Clipboard API；在 http 环境或旧浏览器中自动退回到 execCommand
export function copyText(text) {
  // clipboard API 只在安全上下文（https / localhost）可用，因此两个条件都要判断
  if (navigator.clipboard && window.isSecureContext) {
    return navigator.clipboard.writeText(text)
  }
  // 返回 Promise 让两种实现的调用方式保持一致
  return new Promise((resolve, reject) => {
    try {
      // 降级方案：创建不可见的 textarea，选中内容后执行复制命令
      const textarea = document.createElement('textarea')
      textarea.value = text
      // 固定定位 + 透明，保证不引起页面滚动或布局抖动
      textarea.style.position = 'fixed'
      textarea.style.opacity = '0'
      document.body.appendChild(textarea)
      // select 而不是 focus：移动端也能正确选中全部文本
      textarea.select()
      const ok = document.execCommand('copy')
      // 复制完成后立即清理临时节点
      document.body.removeChild(textarea)
      // resolve/reject 用三元表达式，保持分支紧凑
      ok ? resolve() : reject(new Error('copy failed'))
    } catch (e) {
      // 浏览器禁用 execCommand 等异常统一转成 Promise reject，调用方只需 catch
      reject(e)
    }
  })
}
