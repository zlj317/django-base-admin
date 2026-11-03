<template>
  <el-dialog v-model="visible" title="代码预览" width="920px" top="6vh" destroy-on-close>
    <div v-loading="loading" class="preview-body">
      <el-tabs v-if="files.length" v-model="activeTab">
        <el-tab-pane v-for="f in files" :key="f.path || f.name" :label="f.name" :name="f.path || f.name">
          <div class="code-header">
            <span class="code-path">{{ f.path || f.name }}</span>
            <el-button size="small" type="primary" plain :icon="CopyDocument" @click="copyCode(f)">复制</el-button>
          </div>
          <el-scrollbar height="56vh">
            <pre class="code-block">{{ f.content }}</pre>
          </el-scrollbar>
        </el-tab-pane>
      </el-tabs>
      <el-empty v-else-if="!loading" description="暂无生成代码" />
    </div>
  </el-dialog>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { CopyDocument } from '@element-plus/icons-vue'
import request from '@/utils/request'
import { copyText } from '@/utils/download'

const visible = ref(false)
const loading = ref(false)
const files = ref([])
const activeTab = ref('')

// 打开并加载指定表的代码预览
async function open(tableId) {
  visible.value = true
  loading.value = true
  files.value = []
  activeTab.value = ''
  try {
    const res = await request.get(`/gen/table/${tableId}/preview`)
    files.value = (res.data && res.data.files) || []
    const first = files.value[0]
    activeTab.value = first ? first.path || first.name : ''
  } finally {
    loading.value = false
  }
}

async function copyCode(file) {
  try {
    await copyText(file.content || '')
    ElMessage.success('已复制到剪贴板')
  } catch (e) {
    ElMessage.error('复制失败，请手动选择复制')
  }
}

defineExpose({ open })
</script>
