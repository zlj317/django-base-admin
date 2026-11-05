<!--
  文件级说明：
  职责：代码生成结果预览弹窗——按文件分 Tab 展示后端返回的代码内容，并支持一键复制。
  依赖：utils/request（GET /gen/table/{id}/preview）、utils/download 的 copyText、Element Plus 的
        ElMessage / 图标。
  被谁使用：代码生成相关页面通过组件 ref 调用 open(tableId) 打开（组件已 defineExpose）。
  说明：数据只在弹窗打开时按需拉取，关闭即销毁内容，不缓存上一次的代码。
-->
<template>
  <!-- 预览弹窗：v-model 控制显隐；宽度 920px、top 6vh 适配常见笔记本屏幕；
       destroy-on-close 关闭时销毁内部节点，避免残留上一次表格的代码内容 -->
  <el-dialog v-model="visible" title="代码预览" width="920px" top="6vh" destroy-on-close>
    <!-- 内容容器：请求期间整块显示 loading 遮罩，避免用户看到空白区域误以为无数据 -->
    <div v-loading="loading" class="preview-body">
      <!-- 文件标签页：只有拿到文件列表才渲染；v-model 记录当前激活文件，用于切回时保持选中 -->
      <el-tabs v-if="files.length" v-model="activeTab">
        <!-- 每个生成文件一个页签：label 显示文件名，name 用 path（唯一）作为页签标识；
             优先使用 path 保证不同目录下同名文件不会冲突 -->
        <el-tab-pane v-for="f in files" :key="f.path || f.name" :label="f.name" :name="f.path || f.name">
          <!-- 代码区头部：左侧显示文件相对路径，右侧复制按钮 -->
          <div class="code-header">
            <!-- 文件路径：便于用户确认代码要落到的实际位置 -->
            <span class="code-path">{{ f.path || f.name }}</span>
            <!-- 复制按钮：plain 次要样式降低视觉权重；点击调用 copyCode(f) 复制当前文件全文 -->
            <el-button size="small" type="primary" plain :icon="CopyDocument" @click="copyCode(f)">复制</el-button>
          </div>
          <!-- 代码滚动容器：固定 56vh 高度，避免长代码把弹窗撑出屏幕 -->
          <el-scrollbar height="56vh">
            <!-- 使用 pre 保留源码的换行与缩进；内容为纯文本插值，不会被当作 HTML 解析 -->
            <pre class="code-block">{{ f.content }}</pre>
          </el-scrollbar>
        </el-tab-pane>
      </el-tabs>
      <!-- 空态：请求结束且确实没有文件时展示；请求中（loading=true）不显示，避免与 loading 遮罩叠在一起 -->
      <el-empty v-else-if="!loading" description="暂无生成代码" />
    </div>
  </el-dialog>
</template>

<script setup>
// ref 用于维护弹窗显隐、加载态、文件列表与当前页签
import { ref } from 'vue'
// Element Plus 消息提示：复制成功/失败的用户反馈
import { ElMessage } from 'element-plus'
// 复制按钮图标
import { CopyDocument } from '@element-plus/icons-vue'
// 统一请求实例：已内置 token、错误提示与登录过期跳转
import request from '@/utils/request'
// 复制工具：内部处理 Clipboard API 与降级方案，组件不关心浏览器差异
import { copyText } from '@/utils/download'

// 弹窗是否可见（由 open() 置 true，由 el-dialog 的关闭按钮置 false）
const visible = ref(false)
// 请求加载中，用于 v-loading 遮罩
const loading = ref(false)
// 后端返回的文件数组：[{ name, path, content }]
const files = ref([])
// 当前激活的页签标识（取文件的 path 或 name）
const activeTab = ref('')

// 打开并加载指定表的代码预览
// tableId 为代码生成配置记录 id；每次打开都重置旧状态，避免用户先看到上一次的代码
async function open(tableId) {
  // 先显示弹窗并进入 loading，让点击“预览”后立即有反馈
  visible.value = true
  loading.value = true
  // 清空上一轮的文件与页签，防止请求失败时仍展示旧代码
  files.value = []
  activeTab.value = ''
  try {
    // 拉取该表的生成代码；响应拦截器已解包为 { code, msg, data }
    const res = await request.get(`/gen/table/${tableId}/preview`)
    // 防御性兜底：data 或 files 缺失时按空数组处理
    files.value = (res.data && res.data.files) || []
    // 默认选中第一个文件，打开即可看到内容
    const first = files.value[0]
    activeTab.value = first ? first.path || first.name : ''
  } finally {
    // 无论成功失败都关闭 loading（错误提示由 request 拦截器统一处理）
    loading.value = false
  }
}

// 复制单个文件内容到剪贴板
async function copyCode(file) {
  try {
    // content 可能为空，传空串给 copyText，避免 undefined 触发异常
    await copyText(file.content || '')
    ElMessage.success('已复制到剪贴板')
  } catch (e) {
    // 浏览器拒绝剪贴板权限等情况：提示用户手动选中复制，而不是静默失败
    ElMessage.error('复制失败，请手动选择复制')
  }
}

// 对外暴露 open，供父组件通过 ref 调用打开弹窗
defineExpose({ open })
</script>
