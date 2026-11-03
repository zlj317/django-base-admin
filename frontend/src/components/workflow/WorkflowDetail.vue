<template>
  <el-drawer v-model="visible" size="72%" :title="title" destroy-on-close @open="load">
    <div v-loading="loading" class="wf-detail">
      <template v-if="detail">
        <el-descriptions :column="3" border size="small" class="wf-desc">
          <el-descriptions-item label="流程名称">{{ detail.model?.model_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="业务单据号">{{ detail.instance.biz_key || '-' }}</el-descriptions-item>
          <el-descriptions-item label="发起人">{{ detail.instance.start_user_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="发起时间">{{ detail.instance.start_time || '-' }}</el-descriptions-item>
          <el-descriptions-item label="结束时间">{{ detail.instance.end_time || '-' }}</el-descriptions-item>
          <el-descriptions-item label="流程状态">
            <el-tag :type="statusType(detail.instance.status)">{{ detail.instance.status_name }}</el-tag>
          </el-descriptions-item>
        </el-descriptions>

        <el-tabs v-model="tab" class="wf-tabs">
          <el-tab-pane label="审批轨迹" name="trace">
            <el-timeline v-if="detail.audits.length" class="wf-timeline">
              <el-timeline-item
                v-for="item in detail.audits"
                :key="item.id"
                :timestamp="item.create_time"
                :type="auditType(item.action)"
                placement="top"
              >
                <div class="wf-audit-head">
                  <span class="wf-audit-node">{{ item.node_name || '流程' }}</span>
                  <el-tag size="small" :type="auditType(item.action)">{{ item.action_name }}</el-tag>
                  <span class="wf-audit-user">{{ item.operator_name }}</span>
                </div>
                <div v-if="item.comment" class="wf-audit-comment">{{ item.comment }}</div>
              </el-timeline-item>
            </el-timeline>
            <el-empty v-else description="暂无审批记录" />
          </el-tab-pane>
          <el-tab-pane label="表单数据" name="form">
            <FormRenderer
              v-if="detail.form"
              :fields="detail.form.form_json || []"
              :data="detail.form_data || {}"
              readonly
            />
            <el-empty v-else description="该流程未绑定表单" />
          </el-tab-pane>
          <el-tab-pane label="流程图" name="diagram">
            <div class="wf-diagram">
              <ProcessViewer
                :xml="detail.model?.bpmn_xml || ''"
                :active="activeNodes"
                :completed="completedNodes"
              />
            </div>
          </el-tab-pane>
          <el-tab-pane label="任务记录" name="tasks">
            <el-table :data="detail.tasks" size="small" border header-cell-class-name="wf-th">
              <el-table-column label="节点" prop="task_name" min-width="140" />
              <el-table-column label="处理人" prop="assignee_name" width="110" />
              <el-table-column label="审批方式" prop="approve_mode_name" width="100" align="center" />
              <el-table-column label="状态" width="100" align="center">
                <template #default="scope">
                  <el-tag size="small" :type="taskTagType(scope.row.status)">{{ scope.row.status_name }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="生成时间" prop="start_time" width="170" />
              <el-table-column label="完成时间" prop="end_time" width="170" />
            </el-table>
          </el-tab-pane>
        </el-tabs>
      </template>
      <el-empty v-else-if="!loading" description="未获取到流程详情" />
    </div>
  </el-drawer>
</template>

<script setup>
import { ref, computed } from 'vue'
import request from '@/utils/request'
import FormRenderer from '@/components/workflow/FormRenderer.vue'
import ProcessViewer from '@/components/workflow/ProcessViewer.vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  instanceId: { type: [Number, String], default: 0 }
})
const emit = defineEmits(['update:modelValue'])

const visible = computed({
  get: () => props.modelValue,
  set: val => emit('update:modelValue', val)
})

const loading = ref(false)
const detail = ref(null)
const tab = ref('trace')

const title = computed(() => detail.value?.model?.model_name ? `流程详情 · ${detail.value.model.model_name}` : '流程详情')

const activeNodes = computed(() => {
  const value = detail.value?.instance?.current_node || ''
  return value ? value.split(',').filter(Boolean) : []
})
const completedNodes = computed(() => {
  const ids = (detail.value?.audits || []).map(item => item.node_id).filter(Boolean)
  return [...new Set(ids)]
})

function statusType(status) {
  return { 0: 'warning', 1: 'success', 2: 'danger', 3: 'info' }[status] || 'info'
}
function taskTagType(status) {
  return { 0: 'warning', 1: 'success', 2: 'info', 3: 'primary', 4: 'danger' }[status] || 'info'
}
function auditType(action) {
  return { approve: 'success', submit: 'primary', reject: 'danger', transfer: 'warning',
    addsign: 'warning', back: 'warning', withdraw: 'info', terminate: 'danger' }[action] || 'primary'
}

async function load() {
  if (!props.instanceId) return
  loading.value = true
  detail.value = null
  try {
    const res = await request.get(`/wf/instance/detail/${props.instanceId}`)
    detail.value = res.data
    tab.value = 'trace'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.wf-detail {
  min-height: 320px;
}
.wf-desc {
  margin-bottom: 12px;
}
.wf-timeline {
  padding: 8px 4px 0;
}
.wf-audit-head {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
}
.wf-audit-node {
  font-weight: 600;
}
.wf-audit-user {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}
.wf-audit-comment {
  margin-top: 6px;
  padding: 8px 10px;
  background: var(--el-fill-color-lighter);
  border-radius: 6px;
  color: var(--el-text-color-regular);
  font-size: 13px;
  white-space: pre-wrap;
}
.wf-diagram {
  height: 460px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  overflow: hidden;
}
</style>
