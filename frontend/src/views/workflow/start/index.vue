<!--
  文件级说明：发起流程页（workflow/start/index.vue）
  职责：左侧列出当前用户可发起的流程模型，右侧动态渲染该流程的表单，校验必填后提交生成流程实例与待办任务。
  依赖：@/utils/request、vue-router（提交成功后跳转我的流程）、workflow/FormRenderer.vue 动态表单渲染组件。
  使用方：由「发起流程」菜单路由加载，面向所有有发起权限的业务用户。
-->
<template>
  <!-- 页面根容器：套用全局布局内边距与背景 -->
  <div class="app-container">
    <!-- 页头：说明页面用途，引导用户先选流程再填表 -->
    <div class="page-header">
      <div class="page-title-wrap">
        <h2>发起流程</h2>
        <div class="sub">选择流程并填写表单，提交后进入审批流转</div>
      </div>
    </div>

    <!-- 左右两栏布局：左栏固定宽度展示流程列表，右栏自适应展示表单 -->
    <div class="start-layout">
      <!-- 左栏：可发起流程列表卡片 -->
      <el-card shadow="never" class="model-card">
        <template #header>
          <div class="card-header"><span class="card-title">可发起流程</span></div>
        </template>
        <!-- 列表容器：loadingModels 为真时显示加载遮罩 -->
        <div v-loading="loadingModels" class="model-list">
          <!-- 遍历可发起流程；key 为流程模型 id -->
          <div
            v-for="item in models"
            :key="item.id"
            class="model-item"
            :class="{ active: selectedModel?.id === item.id }"
            @click="selectModel(item)"
          >
            <!-- 图标区：统一使用分享图标表示「发起」语义 -->
            <div class="model-icon"><el-icon :size="22"><Share /></el-icon></div>
            <!-- 文本区：展示流程名称与模型 Key，Key 便于与后台配置核对 -->
            <div class="model-info">
              <div class="model-name">{{ item.model_name }}</div>
              <div class="model-key">Key：{{ item.model_key }}</div>
            </div>
            <!-- 右侧箭头：暗示点击进入表单 -->
            <el-icon class="model-arrow"><ArrowRight /></el-icon>
          </div>
          <!-- 空态：仅在加载结束且确实没有可发起流程时显示，避免闪烁 -->
          <el-empty v-if="!models.length && !loadingModels" description="暂无可发起的流程" :image-size="80" />
        </div>
      </el-card>

      <!-- 右栏：表单卡片，标题随选中流程变化 -->
      <el-card shadow="never" class="form-card">
        <template #header>
          <div class="card-header">
            <!-- 选中流程时显示「填写表单 · 流程名」，否则提示先选择 -->
            <span class="card-title">{{ selectedModel ? `填写表单 · ${selectedModel.model_name}` : '请选择流程' }}</span>
            <!-- 提交按钮：未选流程时不渲染，避免无效提交；submitting 防止重复点击 -->
            <el-button v-if="selectedModel" type="primary" :icon="Promotion" :loading="submitting" @click="submit">
              提交流程
            </el-button>
          </div>
        </template>
        <!-- 已选流程时才渲染表单区；loadingForm 覆盖表单加载过程 -->
        <div v-if="selectedModel" v-loading="loadingForm">
          <!-- 有字段时交给通用渲染器按配置渲染；fields 来自流程绑定表单的 form_json_obj -->
          <FormRenderer v-if="fields.length" :fields="fields" :data="formData" />
          <!-- 无字段时提示可直接提交，避免用户误以为表单加载失败 -->
          <el-empty v-else description="该流程未配置表单字段，可直接提交" :image-size="80" />
          <el-divider />
          <!-- 提交后行为说明：解释流程提交会生成待办，降低用户困惑 -->
          <div class="submit-tip">
            <el-icon><InfoFilled /></el-icon>
            提交后将生成待办任务，审批人可在「待办任务」中处理。
          </div>
        </div>
        <!-- 未选择流程时的引导空态 -->
        <el-empty v-else description="请先在左侧选择要发起的流程" :image-size="90" />
      </el-card>
    </div>
  </div>
</template>

<script setup>
// 组合式 API：ref 管理加载/选中状态，reactive 管理动态表单数据，onMounted 首屏加载流程列表
import { ref, reactive, onMounted } from 'vue'
// 路由实例：提交成功后跳转到「我的流程」页面查看进度
import { useRouter } from 'vue-router'
// ElMessage 用于成功提示
import { ElMessage } from 'element-plus'
// 流程图标、箭头、发起图标、提示图标
import { Share, ArrowRight, Promotion, InfoFilled } from '@element-plus/icons-vue'
// 统一请求实例
import request from '@/utils/request'
// 动态表单渲染组件：按后端表单配置渲染字段，并把输入写回 formData
import FormRenderer from '@/components/workflow/FormRenderer.vue'

// 路由实例，供 submit 成功后跳转
const router = useRouter()
// 左侧流程列表加载中标记
const loadingModels = ref(false)
// 表单配置加载中标记（切换流程时会先清空再加载）
const loadingForm = ref(false)
// 提交中标记，防止重复提交产生多个实例
const submitting = ref(false)
// 可发起流程列表
const models = ref([])
// 当前选中的流程模型；null 表示尚未选择
const selectedModel = ref(null)
// 当前流程的表单字段配置
const fields = ref([])
// 动态表单数据：key 为字段 key，由 FormRenderer 双向写入
const formData = reactive({})

// 加载可发起流程列表
async function loadModels() {
  loadingModels.value = true
  try {
    // GET /api/wf/model/options 返回当前用户有权发起的模型
    const res = await request.get('/wf/model/options')
    models.value = res.data || []
    // 默认选中第一个流程，减少用户一次额外点击
    if (models.value.length) selectModel(models.value[0])
  } finally {
    loadingModels.value = false
  }
}
// 选择流程：清空旧表单数据后加载新流程的表单配置
async function selectModel(item) {
  selectedModel.value = item
  // 先清空字段，避免新流程尚未加载完时仍渲染旧字段
  fields.value = []
  // reactive 对象不能整体替换，只能逐个删除 key 来重置
  Object.keys(formData).forEach(key => delete formData[key])
  // 流程未绑定表单时直接返回，右侧展示「未配置表单」空态
  if (!item.form_id) return
  loadingForm.value = true
  try {
    // 按表单 id 获取表单定义，form_json_obj 为字段配置数组
    const res = await request.get(`/wf/form/detail/${item.form_id}`)
    fields.value = res.data.form_json_obj || []
    // 为每个字段初始化值：数字类型用 null（避免 0 被误当作已填写），其它用空串
    fields.value.forEach(field => {
      formData[field.key] = field.type === 'number' ? null : ''
    })
  } finally {
    loadingForm.value = false
  }
}
// 前端必填校验：提交前拦截未填的必填项，并给出具体字段名
function validate() {
  const missing = fields.value.filter(field =>
    // 空值包括 null、空串、undefined 三种情况
    field.required && (formData[field.key] === null || formData[field.key] === '' || formData[field.key] === undefined))
  if (missing.length) {
    // 汇总缺失字段的中文标签，提示更直观
    ElMessage.warning(`请填写必填项：${missing.map(item => item.label).join('、')}`)
    return false
  }
  return true
}
// 提交流程：先校验选中模型与必填项，再调用启动接口
async function submit() {
  // 理论上按钮只在有选中模型时显示，这里再防御一次
  if (!selectedModel.value) return
  // 必填校验未通过则不提交
  if (!validate()) return
  submitting.value = true
  try {
    // POST /api/wf/instance/start；form_data 展开拷贝，避免把响应式代理对象直接序列化
    await request.post('/wf/instance/start', {
      model_id: selectedModel.value.id,
      form_data: { ...formData }
    })
    ElMessage.success('流程发起成功')
    // 提交后跳转到「我的流程」，让用户立即看到刚发起的实例
    router.push('/workflow/center/my')
  } finally {
    submitting.value = false
  }
}

// 挂载后立即拉取可发起流程
onMounted(loadModels)
</script>

<style scoped>
/* 两栏容器：横向排列，顶部对齐，两栏间距 16px，右侧表单可与左侧列表独立伸缩 */
.start-layout {
  display: flex;
  gap: 16px;
  align-items: flex-start;
}
/* 左侧流程列表卡片：固定 340px 且不参与伸缩，保证每行流程信息完整可读 */
.model-card {
  width: 340px;
  flex: none;
}
/* 右侧表单卡片：占满剩余宽度；min-width:0 防止长内容撑破 flex 容器 */
.form-card {
  flex: 1;
  min-width: 0;
}
/* 流程列表容器：给空态一个最小高度，避免无数据时卡片塌陷 */
.model-list {
  min-height: 300px;
}
/* 单个流程项：横向布局 + 圆角边框，作为可点击卡片；transition 让 hover 状态平滑过渡 */
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
/* 悬停态：边框换主题浅色并加淡蓝阴影，提示该项可点击 */
.model-item:hover {
  border-color: var(--el-color-primary-light-5);
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.12);
}
/* 选中态：主色边框 + 最浅主色背景，明确标识当前正在填写哪个流程 */
.model-item.active {
  border-color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
}
/* 流程图标底座：42px 方块，浅主色背景配主色图标，尺寸固定不随文字伸缩 */
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
/* 文本区：占满剩余宽度；min-width:0 让过长名称能被省略/换行而不撑破卡片 */
.model-info {
  flex: 1;
  min-width: 0;
}
/* 流程名称：加粗放大，作为列表主信息 */
.model-name {
  font-weight: 600;
  font-size: 14px;
}
/* 模型 Key：次要文字色 + 小字号，弱化展示但便于核对 */
.model-key {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-top: 2px;
}
/* 右侧箭头：占位符色，视觉上弱于标题，仅作点击引导 */
.model-arrow {
  color: var(--el-text-color-placeholder);
}
/* 提交提示条：图标与文字横向居中对齐，使用次要文字色与较小字号 */
.submit-tip {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--el-text-color-secondary);
  font-size: 13px;
}
</style>
