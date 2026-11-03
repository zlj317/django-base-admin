<template>
  <div class="app-container">
    <div class="page-header">
      <div class="page-title-wrap">
        <h2>发起流程</h2>
        <div class="sub">选择流程并填写表单，提交后进入审批流转</div>
      </div>
    </div>

    <div class="start-layout">
      <el-card shadow="never" class="model-card">
        <template #header>
          <div class="card-header"><span class="card-title">可发起流程</span></div>
        </template>
        <div v-loading="loadingModels" class="model-list">
          <div
            v-for="item in models"
            :key="item.id"
            class="model-item"
            :class="{ active: selectedModel?.id === item.id }"
            @click="selectModel(item)"
          >
            <div class="model-icon"><el-icon :size="22"><Share /></el-icon></div>
            <div class="model-info">
              <div class="model-name">{{ item.model_name }}</div>
              <div class="model-key">Key：{{ item.model_key }}</div>
            </div>
            <el-icon class="model-arrow"><ArrowRight /></el-icon>
          </div>
          <el-empty v-if="!models.length && !loadingModels" description="暂无可发起的流程" :image-size="80" />
        </div>
      </el-card>

      <el-card shadow="never" class="form-card">
        <template #header>
          <div class="card-header">
            <span class="card-title">{{ selectedModel ? `填写表单 · ${selectedModel.model_name}` : '请选择流程' }}</span>
            <el-button v-if="selectedModel" type="primary" :icon="Promotion" :loading="submitting" @click="submit">
              提交流程
            </el-button>
          </div>
        </template>
        <div v-if="selectedModel" v-loading="loadingForm">
          <FormRenderer v-if="fields.length" :fields="fields" :data="formData" />
          <el-empty v-else description="该流程未配置表单字段，可直接提交" :image-size="80" />
          <el-divider />
          <div class="submit-tip">
            <el-icon><InfoFilled /></el-icon>
            提交后将生成待办任务，审批人可在「待办任务」中处理。
          </div>
        </div>
        <el-empty v-else description="请先在左侧选择要发起的流程" :image-size="90" />
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Share, ArrowRight, Promotion, InfoFilled } from '@element-plus/icons-vue'
import request from '@/utils/request'
import FormRenderer from '@/components/workflow/FormRenderer.vue'

const router = useRouter()
const loadingModels = ref(false)
const loadingForm = ref(false)
const submitting = ref(false)
const models = ref([])
const selectedModel = ref(null)
const fields = ref([])
const formData = reactive({})

async function loadModels() {
  loadingModels.value = true
  try {
    const res = await request.get('/wf/model/options')
    models.value = res.data || []
    if (models.value.length) selectModel(models.value[0])
  } finally {
    loadingModels.value = false
  }
}
async function selectModel(item) {
  selectedModel.value = item
  fields.value = []
  Object.keys(formData).forEach(key => delete formData[key])
  if (!item.form_id) return
  loadingForm.value = true
  try {
    const res = await request.get(`/wf/form/detail/${item.form_id}`)
    fields.value = res.data.form_json_obj || []
    fields.value.forEach(field => {
      formData[field.key] = field.type === 'number' ? null : ''
    })
  } finally {
    loadingForm.value = false
  }
}
function validate() {
  const missing = fields.value.filter(field =>
    field.required && (formData[field.key] === null || formData[field.key] === '' || formData[field.key] === undefined))
  if (missing.length) {
    ElMessage.warning(`请填写必填项：${missing.map(item => item.label).join('、')}`)
    return false
  }
  return true
}
async function submit() {
  if (!selectedModel.value) return
  if (!validate()) return
  submitting.value = true
  try {
    await request.post('/wf/instance/start', {
      model_id: selectedModel.value.id,
      form_data: { ...formData }
    })
    ElMessage.success('流程发起成功')
    router.push('/workflow/center/my')
  } finally {
    submitting.value = false
  }
}

onMounted(loadModels)
</script>

<style scoped>
.start-layout {
  display: flex;
  gap: 16px;
  align-items: flex-start;
}
.model-card {
  width: 340px;
  flex: none;
}
.form-card {
  flex: 1;
  min-width: 0;
}
.model-list {
  min-height: 300px;
}
.model-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  margin-bottom: 10px;
  cursor: pointer;
  transition: all 0.2s;
}
.model-item:hover {
  border-color: var(--el-color-primary-light-5);
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.12);
}
.model-item.active {
  border-color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
}
.model-icon {
  width: 42px;
  height: 42px;
  border-radius: 8px;
  background: var(--el-color-primary-light-8);
  color: var(--el-color-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  flex: none;
}
.model-info {
  flex: 1;
  min-width: 0;
}
.model-name {
  font-weight: 600;
  font-size: 14px;
}
.model-key {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-top: 2px;
}
.model-arrow {
  color: var(--el-text-color-placeholder);
}
.submit-tip {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}
</style>
