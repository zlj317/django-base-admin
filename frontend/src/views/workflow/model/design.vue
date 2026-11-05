<template>
  <div class="design-page">
    <div class="design-top">
      <div class="design-left">
        <el-button :icon="ArrowLeft" @click="goBack">返回</el-button>
        <div class="design-title">
          <span>{{ model.model_name || '流程设计' }}</span>
          <el-tag size="small" type="info">Key：{{ model.model_key }}</el-tag>
          <el-tag size="small" type="success">v{{ model.version }}</el-tag>
        </div>
      </div>
      <div class="design-right">
        <span class="design-tip">选中节点后在右侧配置审批人；选中连线可设置网关条件</span>
        <el-button type="primary" :icon="DocumentChecked" :loading="saving" @click="save">保存设计</el-button>
      </div>
    </div>

    <div class="design-body">
      <div ref="canvasRef" class="designer-canvas"></div>
      <div class="props-panel">
        <div class="panel-title">节点属性</div>
        <template v-if="selectedElement">
          <el-form label-width="86px" size="small" class="panel-form">
            <el-form-item label="节点类型">
              <el-input :model-value="selectedElement.type" disabled />
            </el-form-item>
            <el-form-item label="节点ID">
              <el-input :model-value="selectedElement.id" disabled />
            </el-form-item>
            <el-form-item label="节点名称">
              <el-input v-model="elementName" @change="updateName" />
            </el-form-item>
          </el-form>

          <template v-if="selectedElement.type === 'bpmn:UserTask'">
            <div class="panel-subtitle">审批配置</div>
            <el-form label-width="86px" size="small" class="panel-form">
              <el-form-item label="审批人">
                <el-select v-model="taskConfig.assigneeType" style="width: 100%">
                  <el-option label="发起人本人" value="starter" />
                  <el-option label="指定用户" value="user" />
                  <el-option label="指定角色" value="role" />
                  <el-option label="指定部门" value="dept" />
                  <el-option label="用户分组" value="group" />
                  <el-option label="表达式" value="expression" />
                </el-select>
              </el-form-item>
              <el-form-item v-if="taskConfig.assigneeType === 'user'" label="选择用户">
                <el-select v-model="taskConfig.userIds" multiple filterable placeholder="请选择用户" style="width: 100%">
                  <el-option v-for="u in options.users" :key="u.id" :label="userLabel(u)" :value="u.id" />
                </el-select>
              </el-form-item>
              <el-form-item v-if="taskConfig.assigneeType === 'role'" label="选择角色">
                <el-select v-model="taskConfig.roleIds" multiple placeholder="请选择角色" style="width: 100%">
                  <el-option v-for="r in options.roles" :key="r.id" :label="r.role_name" :value="r.id" />
                </el-select>
              </el-form-item>
              <el-form-item v-if="taskConfig.assigneeType === 'dept'" label="选择部门">
                <el-select v-model="taskConfig.deptIds" multiple placeholder="请选择部门" style="width: 100%">
                  <el-option v-for="d in options.depts" :key="d.id" :label="d.dept_name" :value="d.id" />
                </el-select>
              </el-form-item>
              <el-form-item v-if="taskConfig.assigneeType === 'group'" label="选择分组">
                <el-select v-model="taskConfig.groupId" clearable placeholder="请选择用户分组" style="width: 100%">
                  <el-option v-for="g in options.groups" :key="g.id" :label="g.group_name" :value="g.id" />
                </el-select>
              </el-form-item>
              <el-form-item v-if="taskConfig.assigneeType === 'expression'" label="表达式">
                <el-input v-model="taskConfig.expr" placeholder="如：${form.managerId}" />
              </el-form-item>
              <el-form-item label="审批方式">
                <el-radio-group v-model="taskConfig.approveMode">
                  <el-radio :label="1">串行</el-radio>
                  <el-radio :label="2">或签</el-radio>
                  <el-radio :label="3">会签</el-radio>
                </el-radio-group>
              </el-form-item>
              <el-form-item label="超时(小时)">
                <el-input-number v-model="taskConfig.dueHours" :min="0" :max="720" controls-position="right" style="width: 100%" />
              </el-form-item>
              <el-form-item label="抄送人">
                <el-select v-model="taskConfig.ccUserIds" multiple filterable placeholder="到达节点时抄送" style="width: 100%">
                  <el-option v-for="u in options.users" :key="u.id" :label="userLabel(u)" :value="u.id" />
                </el-select>
              </el-form-item>
            </el-form>
          </template>

          <template v-else-if="selectedElement.type === 'bpmn:SequenceFlow'">
            <div class="panel-subtitle">连线条件</div>
            <el-form label-width="86px" size="small" class="panel-form">
              <el-form-item label="条件表达式">
                <el-input v-model="conditionText" type="textarea" :rows="3" placeholder="如：${form.leaveDays > 3}" @change="updateCondition" />
              </el-form-item>
            </el-form>
            <div class="panel-hint">
              条件成立时走该连线；网关的默认连线不填条件即可作为兜底分支。
            </div>
          </template>

          <template v-else-if="selectedElement.type === 'bpmn:ExclusiveGateway'">
            <div class="panel-hint">
              排他网关：请分别选中网关的每条出线，在「连线条件」中配置分支条件。
            </div>
          </template>
          <template v-else-if="selectedElement.type === 'bpmn:ParallelGateway'">
            <div class="panel-hint">
              并行网关：多条出线同时流转，多条入线需全部到达后汇合。
            </div>
          </template>
        </template>
        <el-empty v-else description="请选择画布中的节点" :image-size="70" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, DocumentChecked } from '@element-plus/icons-vue'
import BpmnModeler from 'bpmn-js/lib/Modeler'
import 'bpmn-js/dist/assets/diagram-js.css'
import 'bpmn-js/dist/assets/bpmn-js.css'
import 'bpmn-js/dist/assets/bpmn-font/css/bpmn.css'
import request from '@/utils/request'

const route = useRoute()
const router = useRouter()
const canvasRef = ref(null)
const saving = ref(false)
const dirty = ref(false)
const model = reactive({ id: 0, model_name: '', model_key: '', version: 0, status: 0 })
const selectedElement = ref(null)
const elementName = ref('')
const conditionText = ref('')
const nodeConfig = ref({})
const taskConfig = reactive({})
const options = reactive({ users: [], roles: [], depts: [], groups: [] })

let modeler = null

function defaultTask() {
  return {
    assigneeType: 'starter', userIds: [], roleIds: [], deptIds: [], groupId: '',
    expr: '', approveMode: 2, dueHours: 24, ccUserIds: []
  }
}
function userLabel(user) {
  return user.nickname ? `${user.nickname}（${user.username}）` : user.username
}

// 新建流程的默认流程图：开始 → 审批 → 结束
function defaultXml() {
  return `<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI" xmlns:dc="http://www.omg.org/spec/DD/20100524/DC" xmlns:di="http://www.omg.org/spec/DD/20100524/DI" id="Definitions_Design" targetNamespace="http://bpmn.io/schema/bpmn">
  <bpmn:process id="Process_Design" name="新建流程" isExecutable="true">
    <bpmn:startEvent id="StartEvent_1" name="开始">
      <bpmn:outgoing>Flow_1</bpmn:outgoing>
    </bpmn:startEvent>
    <bpmn:userTask id="Task_1" name="审批节点">
      <bpmn:incoming>Flow_1</bpmn:incoming>
      <bpmn:outgoing>Flow_2</bpmn:outgoing>
    </bpmn:userTask>
    <bpmn:endEvent id="EndEvent_1" name="结束">
      <bpmn:incoming>Flow_2</bpmn:incoming>
    </bpmn:endEvent>
    <bpmn:sequenceFlow id="Flow_1" sourceRef="StartEvent_1" targetRef="Task_1" />
    <bpmn:sequenceFlow id="Flow_2" sourceRef="Task_1" targetRef="EndEvent_1" />
  </bpmn:process>
  <bpmndi:BPMNDiagram id="BPMNDiagram_1">
    <bpmndi:BPMNPlane id="BPMNPlane_1" bpmnElement="Process_Design">
      <bpmndi:BPMNShape id="StartEvent_1_di" bpmnElement="StartEvent_1">
        <dc:Bounds x="170" y="222" width="36" height="36" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="Task_1_di" bpmnElement="Task_1">
        <dc:Bounds x="270" y="200" width="100" height="80" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="EndEvent_1_di" bpmnElement="EndEvent_1">
        <dc:Bounds x="430" y="222" width="36" height="36" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNEdge id="Flow_1_di" bpmnElement="Flow_1">
        <di:waypoint x="206" y="240" />
        <di:waypoint x="270" y="240" />
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="Flow_2_di" bpmnElement="Flow_2">
        <di:waypoint x="370" y="240" />
        <di:waypoint x="430" y="240" />
      </bpmndi:BPMNEdge>
    </bpmndi:BPMNPlane>
  </bpmndi:BPMNDiagram>
</bpmn:definitions>`
}

function selectElement(element) {
  selectedElement.value = element || null
  conditionText.value = ''
  if (!element) return
  elementName.value = element.businessObject?.name || ''
  if (element.type === 'bpmn:UserTask') {
    Object.assign(taskConfig, defaultTask(), JSON.parse(JSON.stringify(nodeConfig.value[element.id] || {})))
  }
  if (element.type === 'bpmn:SequenceFlow') {
    conditionText.value = element.businessObject?.conditionExpression?.body || ''
  }
}

function updateName() {
  if (!selectedElement.value) return
  modeler.get('modeling').updateProperties(selectedElement.value, { name: elementName.value })
}

function updateCondition() {
  if (!selectedElement.value || selectedElement.value.type !== 'bpmn:SequenceFlow') return
  const modeling = modeler.get('modeling')
  const moddle = modeler.get('moddle')
  const text = conditionText.value.trim()
  if (!text) {
    modeling.updateProperties(selectedElement.value, { conditionExpression: undefined })
    return
  }
  const expression = moddle.create('bpmn:FormalExpression', { body: text })
  modeling.updateProperties(selectedElement.value, { conditionExpression: expression })
}

async function loadOptions() {
  const [users, roles, depts, groups] = await Promise.all([
    request.get('/wf/option/users'),
    request.get('/wf/option/roles'),
    request.get('/wf/option/depts'),
    request.get('/wf/option/groups')
  ])
  options.users = users.data || []
  options.roles = roles.data || []
  options.depts = depts.data || []
  options.groups = groups.data || []
}

async function loadModel() {
  const res = await request.get(`/wf/model/design/${route.params.id}`)
  Object.assign(model, {
    id: res.data.id,
    model_name: res.data.model_name,
    model_key: res.data.model_key,
    version: res.data.version,
    status: res.data.status
  })
  nodeConfig.value = res.data.node_config || {}
  await modeler.importXML(res.data.bpmn_xml || defaultXml())
  modeler.get('canvas').zoom('fit-viewport')
  dirty.value = false
}

async function save() {
  saving.value = true
  try {
    const { xml } = await modeler.saveXML({ format: true })
    await request.post('/wf/model/save', {
      id: model.id,
      bpmn_xml: xml,
      node_config: nodeConfig.value
    })
    dirty.value = false
    ElMessage.success('流程设计保存成功')
  } finally {
    saving.value = false
  }
}

async function goBack() {
  if (dirty.value) {
    try {
      await ElMessageBox.confirm('当前设计尚未保存，确认离开吗？', '提示', { type: 'warning' })
    } catch (e) {
      return
    }
  }
  router.push('/workflow/manage/model')
}

watch(taskConfig, () => {
  const element = selectedElement.value
  if (element && element.type === 'bpmn:UserTask') {
    nodeConfig.value[element.id] = JSON.parse(JSON.stringify(taskConfig))
    dirty.value = true
  }
}, { deep: true })

onMounted(async () => {
  modeler = new BpmnModeler({ container: canvasRef.value })
  modeler.on('selection.changed', event => selectElement(event.newSelection[0]))
  modeler.on('commandStack.changed', () => { dirty.value = true })
  await loadOptions()
  await loadModel()
})

onBeforeUnmount(() => {
  if (modeler) modeler.destroy()
  modeler = null
})
</script>

<style scoped>
.design-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 96px);
  padding: 12px 16px 16px;
  box-sizing: border-box;
}
.design-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.design-left,
.design-right {
  display: flex;
  align-items: center;
  gap: 12px;
}
.design-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
}
.design-tip {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}
.design-body {
  flex: 1;
  display: flex;
  gap: 12px;
  min-height: 0;
}
.designer-canvas {
  flex: 1;
  min-width: 0;
  background: var(--app-surface);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  overflow: hidden;
}
.props-panel {
  width: 320px;
  flex: none;
  background: var(--app-surface);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  padding: 12px;
  overflow-y: auto;
}
.panel-title {
  font-weight: 600;
  font-size: 15px;
  margin-bottom: 10px;
}
.panel-subtitle {
  font-weight: 600;
  font-size: 13px;
  color: var(--el-color-primary);
  margin: 12px 0 8px;
  padding-left: 8px;
  border-left: 3px solid var(--el-color-primary);
}
.panel-hint {
  margin-top: 10px;
  padding: 10px 12px;
  background: var(--el-fill-color-lighter);
  border-radius: 6px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  line-height: 1.6;
}
</style>
