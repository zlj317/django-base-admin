<!--
  文件级说明：
  职责：工作流实例详情抽屉——展示流程基本信息、审批轨迹、表单数据、流程图与任务记录。
  依赖：utils/request（GET /wf/instance/detail/{id}）、FormRenderer、ProcessViewer、Element Plus 组件。
  被谁使用：流程实例列表/待办/已办等页面，通过 v-model 控制抽屉显隐并传入 instanceId。
  说明：数据在抽屉每次打开时拉取（@open 触发），关闭即销毁内容；本组件只读，不提供审批操作。
-->
<template>
  <!-- 详情抽屉：v-model 双向绑定显隐；size=72% 保留左侧列表可见；
       title 随流程名称动态变化；destroy-on-close 关闭即销毁，避免大表格/流程图占用内存；
       @open 在抽屉展开动画开始时触发 load，保证用户看到内容时数据已就绪 -->
  <el-drawer v-model="visible" size="72%" :title="title" destroy-on-close @open="load">
    <!-- 内容容器：请求期间整块 loading 遮罩；min-height 在样式里限定，避免空态时抽屉过矮 -->
    <div v-loading="loading" class="wf-detail">
      <!-- detail 存在才渲染主体；为空时走下方空态分支 -->
      <template v-if="detail">
        <!-- 基础信息：三列布局 + 边框 + 小尺寸，最近似“表格化”的信息展示；
             各字段均用 || '-' 兜底，缺少数据时显示占位符而不是空白 -->
        <el-descriptions :column="3" border size="small" class="wf-desc">
          <!-- 流程名称：来自流程模型，可选链防止 model 缺失时报错 -->
          <el-descriptions-item label="流程名称">{{ detail.model?.model_name || '-' }}</el-descriptions-item>
          <!-- 业务单据号：由发起方传入，用于关联业务系统 -->
          <el-descriptions-item label="业务单据号">{{ detail.instance.biz_key || '-' }}</el-descriptions-item>
          <!-- 发起人姓名 -->
          <el-descriptions-item label="发起人">{{ detail.instance.start_user_name || '-' }}</el-descriptions-item>
          <!-- 发起时间 -->
          <el-descriptions-item label="发起时间">{{ detail.instance.start_time || '-' }}</el-descriptions-item>
          <!-- 结束时间：未结束时通常为空，显示 '-' -->
          <el-descriptions-item label="结束时间">{{ detail.instance.end_time || '-' }}</el-descriptions-item>
          <!-- 流程状态：tag 颜色由 statusType 按状态码映射，文字取后端 status_name -->
          <el-descriptions-item label="流程状态">
            <el-tag :type="statusType(detail.instance.status)">{{ detail.instance.status_name }}</el-tag>
          </el-descriptions-item>
        </el-descriptions>

        <!-- 详情标签页：trace 审批轨迹 / form 表单数据 / diagram 流程图 / tasks 任务记录 -->
        <el-tabs v-model="tab" class="wf-tabs">
          <!-- 页签一：审批轨迹 -->
          <el-tab-pane label="审批轨迹" name="trace">
            <!-- 时间线：仅当存在审批记录时渲染；length 判断依赖 audits 一定为数组 -->
            <el-timeline v-if="detail.audits.length" class="wf-timeline">
              <!-- 单条审批记录：timestamp 显示操作时间；type 由 auditType 映射为时间线节点颜色；
                   placement=top 让时间戳显示在节点上方 -->
              <el-timeline-item
                v-for="item in detail.audits"
                :key="item.id"
                :timestamp="item.create_time"
                :type="auditType(item.action)"
                placement="top"
              >
                <!-- 记录头部：节点名 + 动作标签 + 操作人 -->
                <div class="wf-audit-head">
                  <!-- 节点名称：缺失时用“流程”兜底（例如发起动作没有具体节点） -->
                  <span class="wf-audit-node">{{ item.node_name || '流程' }}</span>
                  <!-- 动作标签：action_name 由后端给出中文名，颜色与时间线节点保持一致 -->
                  <el-tag size="small" :type="auditType(item.action)">{{ item.action_name }}</el-tag>
                  <!-- 操作人姓名 -->
                  <span class="wf-audit-user">{{ item.operator_name }}</span>
                </div>
                <!-- 审批意见：仅有 comment 时渲染，pre-wrap 样式保留用户换行 -->
                <div v-if="item.comment" class="wf-audit-comment">{{ item.comment }}</div>
              </el-timeline-item>
            </el-timeline>
            <!-- 无审批记录时的空态 -->
            <el-empty v-else description="暂无审批记录" />
          </el-tab-pane>
          <!-- 页签二：表单数据（只读展示流程绑定的动态表单） -->
          <el-tab-pane label="表单数据" name="form">
            <!-- 动态表单：仅在流程绑定了表单时渲染；form_json 为字段配置，form_data 为已填数据，
                 readonly 统一禁用所有控件 -->
            <FormRenderer
              v-if="detail.form"
              :fields="detail.form.form_json || []"
              :data="detail.form_data || {}"
              readonly
            />
            <!-- 未绑定表单时的空态 -->
            <el-empty v-else description="该流程未绑定表单" />
          </el-tab-pane>
          <!-- 页签三：流程图（BPMN 只读渲染 + 节点高亮） -->
          <el-tab-pane label="流程图" name="diagram">
            <!-- 固定高度的画布容器（样式里 460px），避免 bpmn-js 在抽屉布局中高度塌陷 -->
            <div class="wf-diagram">
              <!-- 流程查看器：xml 取流程模型中的 bpmn_xml（缺失传空串以显示空态）；
                   active/completed 由计算属性从当前节点与审批记录中推导 -->
              <ProcessViewer
                :xml="detail.model?.bpmn_xml || ''"
                :active="activeNodes"
                :completed="completedNodes"
              />
            </div>
          </el-tab-pane>
          <!-- 页签四：任务记录（每个审批节点的处理情况） -->
          <el-tab-pane label="任务记录" name="tasks">
            <!-- 任务表：小尺寸 + 边框；header-cell-class-name 预留表头样式钩子 -->
            <el-table :data="detail.tasks" size="small" border header-cell-class-name="wf-th">
              <!-- 节点名称：列宽自适应，最小 140px 容纳较长节点名 -->
              <el-table-column label="节点" prop="task_name" min-width="140" />
              <!-- 处理人 -->
              <el-table-column label="处理人" prop="assignee_name" width="110" />
              <!-- 审批方式（或签/会签/依次等），居中显示 -->
              <el-table-column label="审批方式" prop="approve_mode_name" width="100" align="center" />
              <!-- 任务状态：用作用域插槽拿到当前行，按 status 映射 tag 颜色 -->
              <el-table-column label="状态" width="100" align="center">
                <template #default="scope">
                  <el-tag size="small" :type="taskTagType(scope.row.status)">{{ scope.row.status_name }}</el-tag>
                </template>
              </el-table-column>
              <!-- 任务生成时间：固定 170px 容纳完整日期时间 -->
              <el-table-column label="生成时间" prop="start_time" width="170" />
              <!-- 任务完成时间 -->
              <el-table-column label="完成时间" prop="end_time" width="170" />
            </el-table>
          </el-tab-pane>
        </el-tabs>
      </template>
      <!-- 空态：请求完成但仍无详情数据时显示；loading 中不显示，避免与遮罩重复 -->
      <el-empty v-else-if="!loading" description="未获取到流程详情" />
    </div>
  </el-drawer>
</template>

<script setup>
// ref 维护加载态与详情数据；computed 用于派生生抽屉显隐、标题与画布节点 id
import { ref, computed } from 'vue'
// 统一请求实例：/wf/instance/detail/{id} 拉取流程实例完整详情
import request from '@/utils/request'
// 动态表单渲染器：以只读方式展示流程绑定的表单字段
import FormRenderer from '@/components/workflow/FormRenderer.vue'
// BPMN 流程查看器：渲染流程图并高亮当前/已完成节点
import ProcessViewer from '@/components/workflow/ProcessViewer.vue'

// 组件 props：
// · modelValue：抽屉显隐（配合 v-model 使用）
// · instanceId：流程实例 id；为 0/空值时 load 不会发请求（避免打开时误查 id=0）
const props = defineProps({
  modelValue: { type: Boolean, default: false },
  instanceId: { type: [Number, String], default: 0 }
})
// 声明 update:modelValue 事件，用于把 el-drawer 的开关状态回传给父组件
const emit = defineEmits(['update:modelValue'])

// 抽屉显隐的可写计算属性：
// get 读父组件的 modelValue；set 把新值 emit 回去，实现标准 v-model 双向绑定
const visible = computed({
  get: () => props.modelValue,
  set: val => emit('update:modelValue', val)
})

// 详情请求中的加载态，用于 v-loading 遮罩
const loading = ref(false)
// 详情数据：接口返回的 { model, instance, audits, form, form_data, tasks } 等
const detail = ref(null)
// 当前激活的页签，默认展示审批轨迹；每次加载成功后复位，避免停留在上次查看的页签
const tab = ref('trace')

// 抽屉标题：拿到流程名称后拼接展示，否则退化为“流程详情”；
// 使用可选链，detail/model 未加载完成时不会报错
const title = computed(() => detail.value?.model?.model_name ? `流程详情 · ${detail.value.model.model_name}` : '流程详情')

// 当前激活节点 id 列表：后端把并行节点以逗号分隔存在 current_node 字段，
// 这里拆分并过滤空串；没有当前节点时返回空数组（画布不做任何高亮）
const activeNodes = computed(() => {
  const value = detail.value?.instance?.current_node || ''
  return value ? value.split(',').filter(Boolean) : []
})
// 已完成节点 id 集合：从审批轨迹中提取 node_id 并去重（同一节点可能多次审批）
const completedNodes = computed(() => {
  const ids = (detail.value?.audits || []).map(item => item.node_id).filter(Boolean)
  return [...new Set(ids)]
})

// 流程实例状态 -> el-tag 颜色映射：0 待审批/进行中，1 已完成，2 已驳回/终止，3 已撤回；
// 未知状态统一用 info 灰，保证不会传入非法 type
function statusType(status) {
  return { 0: 'warning', 1: 'success', 2: 'danger', 3: 'info' }[status] || 'info'
}
// 任务状态 -> el-tag 颜色映射：0 待处理，1 已通过，2 已跳过，3 处理中，4 已拒绝
function taskTagType(status) {
  return { 0: 'warning', 1: 'success', 2: 'info', 3: 'primary', 4: 'danger' }[status] || 'info'
}
// 审批动作 -> 时间线节点/tag 颜色映射：通过=绿、提交=蓝、驳回/终止=红、转办/加签/退回=橙、撤回=灰
function auditType(action) {
  return { approve: 'success', submit: 'primary', reject: 'danger', transfer: 'warning',
    addsign: 'warning', back: 'warning', withdraw: 'info', terminate: 'danger' }[action] || 'primary'
}

// 加载流程详情（由 el-drawer 的 @open 事件触发）：
// 每次打开先清空旧数据，保证切换实例时不会短暂看到上一个流程的信息
async function load() {
  // 没有实例 id 时直接返回，避免请求 /wf/instance/detail/0 这类无效地址
  if (!props.instanceId) return
  loading.value = true
  detail.value = null
  try {
    // 请求流程实例完整详情；拦截器已处理错误提示与登录失效
    const res = await request.get(`/wf/instance/detail/${props.instanceId}`)
    detail.value = res.data
    // 每次加载后回到审批轨迹页签，符合“先看进度”的阅读习惯
    tab.value = 'trace'
  } finally {
    // 无论成功失败都关闭 loading，避免抽屉一直处于遮罩状态
    loading.value = false
  }
}
</script>

<style scoped>
/* 详情容器最小高度：即使处于空态或加载中，抽屉也有稳定的主体高度，避免内容区突然塌陷 */
.wf-detail {
  min-height: 320px;
}
/* 基础信息表格：与下方标签页留出 12px 间距 */
.wf-desc {
  margin-bottom: 12px;
}
/* 审批时间线：顶部 8px、左右 4px 的微调内边距，让时间线不贴边且首项不会顶到标签栏 */
.wf-timeline {
  padding: 8px 4px 0;
}
/* 单条审批记录头部：节点名/动作标签/操作人水平排列，10px 间隔保证三者可区分 */
.wf-audit-head {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
}
/* 节点名称：加粗以突出“在哪一步”，与右侧动作标签形成主次 */
.wf-audit-node {
  font-weight: 600;
}
/* 操作人：次级文字色 + 13px，比节点名更弱，符合“谁做的不如做了什么重要”的阅读顺序 */
.wf-audit-user {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}
/* 审批意见气泡：浅色填充底 + 圆角；pre-wrap 保留用户输入中的换行与空格，避免意见挤成一行 */
.wf-audit-comment {
  margin-top: 6px;
  padding: 8px 10px;
  background: var(--el-fill-color-lighter);
  border-radius: 6px;
  color: var(--el-text-color-regular);
  font-size: 13px;
  white-space: pre-wrap;
}
/* 流程图容器：固定 460px 高度给 bpmn-js 提供确定尺寸；细边框 + 圆角 + 裁切，
   防止画布内容溢出到页签外；主题变量保证暗色模式下边框仍协调 */
.wf-diagram {
  height: 460px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  overflow: hidden;
}
</style>
