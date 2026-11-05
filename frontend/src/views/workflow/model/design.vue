<!-- 流程设计器页面（workflow/model/design.vue）
     职责：基于 bpmn-js 提供 BPMN2.0 流程图的在线绘制、节点属性配置（审批人/审批方式/超时/抄送）与连线条件配置，
           并把画布导出为 XML 连同节点配置保存到后端。
     依赖：bpmn-js 的 Modeler（导入/导出 XML）、Element Plus 表单与消息组件、@/utils/request 统一请求实例。
     被谁使用：workflow/model/index.vue 的「设计」按钮跳转到 /workflow/design/:id 后进入本页。 -->
<template>
  <!-- 页面根容器：纵向排列顶部工具栏与画布区，并限制整页高度以适配全局布局 -->
  <div class="design-page">
    <!-- 顶部工具栏：左侧返回与模型信息，右侧操作提示与保存按钮 -->
    <div class="design-top">
      <!-- 左侧区域：返回列表页 + 当前模型标识信息 -->
      <div class="design-left">
        <!-- 返回流程模型列表；未保存时 goBack 会先弹确认框 -->
        <el-button :icon="ArrowLeft" @click="goBack">返回</el-button>
        <!-- 标题区：展示模型名称、Key、版本，便于确认当前正在设计的模型 -->
        <div class="design-title">
          <!-- 模型名称；新建/未加载时回退为“流程设计” -->
          <span>{{ model.model_name || '流程设计' }}</span>
          <!-- 模型唯一标识 Key，灰色标签仅作提示 -->
          <el-tag size="small" type="info">Key：{{ model.model_key }}</el-tag>
          <!-- 当前版本号，发布后由后端递增 -->
          <el-tag size="small" type="success">v{{ model.version }}</el-tag>
        </div>
      </div>
      <!-- 右侧区域：操作提示 + 保存按钮 -->
      <div class="design-right">
        <!-- 使用提示：说明属性面板与连线条件的操作方式 -->
        <span class="design-tip">选中节点后在右侧配置审批人；选中连线可设置网关条件</span>
        <!-- 保存设计：调用 save() 导出 XML 并提交节点配置；saving 控制 loading 防重复提交 -->
        <el-button type="primary" :icon="DocumentChecked" :loading="saving" @click="save">保存设计</el-button>
      </div>
    </div>

    <!-- 主体区域：左侧 bpmn 画布，右侧选中元素的属性面板 -->
    <div class="design-body">
      <!-- bpmn-js 画布挂载点：onMounted 时以该 DOM 创建 Modeler，尺寸由样式 flex:1 决定 -->
      <div ref="canvasRef" class="designer-canvas"></div>
      <!-- 右侧属性面板：根据当前选中元素类型展示不同配置项 -->
      <div class="props-panel">
        <!-- 面板主标题 -->
        <div class="panel-title">节点属性</div>
        <!-- 仅当画布中选中了元素时才渲染属性表单，否则显示下方空状态 -->
        <template v-if="selectedElement">
          <!-- 通用节点信息：类型与 ID 只读，名称可编辑 -->
          <el-form label-width="86px" size="small" class="panel-form">
            <el-form-item label="节点类型">
              <!-- bpmn 元素类型（如 bpmn:UserTask），只读展示，决定下方显示哪组配置 -->
              <el-input :model-value="selectedElement.type" disabled />
            </el-form-item>
            <el-form-item label="节点ID">
              <!-- 元素 ID 只读展示；它同时是 nodeConfig 中保存该节点配置的键 -->
              <el-input :model-value="selectedElement.id" disabled />
            </el-form-item>
            <el-form-item label="节点名称">
              <!-- 名称绑定临时值，change（失焦/回车）时调用 updateName 写回 bpmn 模型 -->
              <el-input v-model="elementName" @change="updateName" />
            </el-form-item>
          </el-form>

          <!-- 用户任务节点：展示审批人来源、审批方式、超时与抄送等业务配置 -->
          <template v-if="selectedElement.type === 'bpmn:UserTask'">
            <!-- 分组小标题 -->
            <div class="panel-subtitle">审批配置</div>
            <el-form label-width="86px" size="small" class="panel-form">
              <el-form-item label="审批人">
                <!-- 审批人来源类型：决定下方显示用户/角色/部门/分组/表达式中的哪种选择控件 -->
                <el-select v-model="taskConfig.assigneeType" style="width: 100%">
                  <!-- 由流程发起人本人处理 -->
                  <el-option label="发起人本人" value="starter" />
                  <!-- 指定具体用户（多选） -->
                  <el-option label="指定用户" value="user" />
                  <!-- 按角色取人（选择多个角色，后端展开为角色成员） -->
                  <el-option label="指定角色" value="role" />
                  <!-- 按部门取人（选择多个部门） -->
                  <el-option label="指定部门" value="dept" />
                  <!-- 指定用户分组，由后端按分组解析成员 -->
                  <el-option label="用户分组" value="group" />
                  <!-- 直接写表达式动态计算审批人 -->
                  <el-option label="表达式" value="expression" />
                </el-select>
              </el-form-item>
              <!-- 指定用户时显示用户多选；filterable 支持按姓名/账号搜索 -->
              <el-form-item v-if="taskConfig.assigneeType === 'user'" label="选择用户">
                <el-select v-model="taskConfig.userIds" multiple filterable placeholder="请选择用户" style="width: 100%">
                  <!-- 遍历已加载的用户候选，label 由 userLabel 拼接昵称与账号 -->
                  <el-option v-for="u in options.users" :key="u.id" :label="userLabel(u)" :value="u.id" />
                </el-select>
              </el-form-item>
              <!-- 指定角色时显示角色多选（label 展示角色名称） -->
              <el-form-item v-if="taskConfig.assigneeType === 'role'" label="选择角色">
                <el-select v-model="taskConfig.roleIds" multiple placeholder="请选择角色" style="width: 100%">
                  <el-option v-for="r in options.roles" :key="r.id" :label="r.role_name" :value="r.id" />
                </el-select>
              </el-form-item>
              <!-- 指定部门时显示部门多选（label 展示部门名称） -->
              <el-form-item v-if="taskConfig.assigneeType === 'dept'" label="选择部门">
                <el-select v-model="taskConfig.deptIds" multiple placeholder="请选择部门" style="width: 100%">
                  <el-option v-for="d in options.depts" :key="d.id" :label="d.dept_name" :value="d.id" />
                </el-select>
              </el-form-item>
              <!-- 指定分组时显示分组单选；clearable 允许清空已选分组 -->
              <el-form-item v-if="taskConfig.assigneeType === 'group'" label="选择分组">
                <el-select v-model="taskConfig.groupId" clearable placeholder="请选择用户分组" style="width: 100%">
                  <el-option v-for="g in options.groups" :key="g.id" :label="g.group_name" :value="g.id" />
                </el-select>
              </el-form-item>
              <!-- 表达式模式：直接填写动态审批人表达式，由后端运行时求值 -->
              <el-form-item v-if="taskConfig.assigneeType === 'expression'" label="表达式">
                <el-input v-model="taskConfig.expr" placeholder="如：${form.managerId}" />
              </el-form-item>
              <el-form-item label="审批方式">
                <!-- 1=串行（按顺序逐一审批）；2=或签（任一审批人通过即可）；3=会签（全部通过才流转） -->
                <el-radio-group v-model="taskConfig.approveMode">
                  <!-- 串行审批 -->
                  <el-radio :label="1">串行</el-radio>
                  <!-- 或签：任一审批人通过即流转 -->
                  <el-radio :label="2">或签</el-radio>
                  <!-- 会签：所有审批人都通过才流转 -->
                  <el-radio :label="3">会签</el-radio>
                </el-radio-group>
              </el-form-item>
              <el-form-item label="超时(小时)">
                <!-- 审批超时小时数，0 表示不限制；后端据此做超时提醒/自动流转 -->
                <el-input-number v-model="taskConfig.dueHours" :min="0" :max="720" controls-position="right" style="width: 100%" />
              </el-form-item>
              <el-form-item label="抄送人">
                <!-- 到达该节点时给这些用户发送抄送消息，不影响审批流转 -->
                <el-select v-model="taskConfig.ccUserIds" multiple filterable placeholder="到达节点时抄送" style="width: 100%">
                  <el-option v-for="u in options.users" :key="u.id" :label="userLabel(u)" :value="u.id" />
                </el-select>
              </el-form-item>
            </el-form>
          </template>

          <!-- 连线（SequenceFlow）：配置该分支的流转条件表达式 -->
          <template v-else-if="selectedElement.type === 'bpmn:SequenceFlow'">
            <div class="panel-subtitle">连线条件</div>
            <el-form label-width="86px" size="small" class="panel-form">
              <el-form-item label="条件表达式">
                <!-- 条件文本 change 时调用 updateCondition，转换为 BPMN FormalExpression 或清除条件 -->
                <el-input v-model="conditionText" type="textarea" :rows="3" placeholder="如：${form.leaveDays > 3}" @change="updateCondition" />
              </el-form-item>
            </el-form>
            <!-- 说明条件语义：条件为真才走该线，默认出线不填条件充当兜底分支 -->
            <div class="panel-hint">
              条件成立时走该连线；网关的默认连线不填条件即可作为兜底分支。
            </div>
          </template>

          <!-- 排他网关：本身不配置条件，需要分别选中每条出线设置条件 -->
          <template v-else-if="selectedElement.type === 'bpmn:ExclusiveGateway'">
            <div class="panel-hint">
              排他网关：请分别选中网关的每条出线，在「连线条件」中配置分支条件。
            </div>
          </template>
          <!-- 并行网关：不需要条件，所有出线同时流转，所有入线到齐后汇合 -->
          <template v-else-if="selectedElement.type === 'bpmn:ParallelGateway'">
            <div class="panel-hint">
              并行网关：多条出线同时流转，多条入线需全部到达后汇合。
            </div>
          </template>
        </template>
        <!-- 未选中任何元素时的空状态占位 -->
        <el-empty v-else description="请选择画布中的节点" :image-size="70" />
      </div>
    </div>
  </div>
</template>

<script setup>
// Vue 组合式 API：ref/reactive 管理状态，onMounted/onBeforeUnmount 管理 bpmn 实例生命周期，watch 同步审批配置
import { ref, reactive, onMounted, onBeforeUnmount, watch } from 'vue'
// 路由：useRoute 读取 URL 中的模型 id；useRouter 用于返回列表页
import { useRoute, useRouter } from 'vue-router'
// Element Plus：ElMessage 成功提示；ElMessageBox 离开前未保存确认
import { ElMessage, ElMessageBox } from 'element-plus'
// 顶部工具栏按钮图标（返回、保存）
import { ArrowLeft, DocumentChecked } from '@element-plus/icons-vue'
// bpmn-js 建模器：提供 importXML/saveXML/get 等能力，是画布的核心
import BpmnModeler from 'bpmn-js/lib/Modeler'
// bpmn-js 自带样式，必须引入，否则画布元素与连线无法正常显示
import 'bpmn-js/dist/assets/diagram-js.css'
// bpmn-js 基础样式（画布容器、调色板等）
import 'bpmn-js/dist/assets/bpmn-js.css'
// bpmn 图标字体（任务、网关等元素的图标依赖它）
import 'bpmn-js/dist/assets/bpmn-font/css/bpmn.css'
// 统一请求实例：自动携带 token，并统一处理业务错误提示
import request from '@/utils/request'

// 当前路由（需从 route.params.id 取模型 ID）
const route = useRoute()
// 路由器实例，返回列表页时使用
const router = useRouter()
// bpmn 画布容器的 DOM 引用，mounted 时传给 BpmnModeler
const canvasRef = ref(null)
// 保存中状态：驱动保存按钮 loading，避免重复提交
const saving = ref(false)
// 是否存在未保存改动：返回时提示，避免误丢设计
const dirty = ref(false)
// 当前模型的元信息，由 loadModel 从后端回填，用于顶部展示
const model = reactive({ id: 0, model_name: '', model_key: '', version: 0, status: 0 })
// 当前选中的 bpmn 元素，驱动右侧属性面板的条件渲染
const selectedElement = ref(null)
// 节点名称输入框的临时值，change 时同步回 bpmn 模型
const elementName = ref('')
// 连线条件表达式输入框的临时值
const conditionText = ref('')
// 全量节点配置：{ 元素ID: 审批配置 }，保存时整体提交，保证未选中过的节点配置也不丢
const nodeConfig = ref({})
// 当前选中用户任务的审批配置，watch 会把改动实时写回 nodeConfig
const taskConfig = reactive({})
// 审批人候选数据：用户/角色/部门/分组，mounted 时并行加载
const options = reactive({ users: [], roles: [], depts: [], groups: [] })

// bpmn-js 建模器实例：mounted 创建、卸载时销毁，避免内存泄漏
let modeler = null

// 用户任务的默认审批配置：默认发起人本人、或签、24 小时超时，所有选择项均为空
function defaultTask() {
  return {
    assigneeType: 'starter', userIds: [], roleIds: [], deptIds: [], groupId: '',
    expr: '', approveMode: 2, dueHours: 24, ccUserIds: []
  }
}
// 用户下拉显示名：有昵称时拼接“昵称（账号）”，否则直接用账号，避免同名用户难以区分
function userLabel(user) {
  return user.nickname ? `${user.nickname}（${user.username}）` : user.username
}

// 新建流程的默认流程图：开始 → 审批 → 结束
// 同时包含 BPMNDiagram 的图形坐标与连线路径，bpmn-js 导入后可直接渲染并编辑
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

// 选中变化回调：把选中的 bpmn 元素映射到右侧属性面板的临时状态
function selectElement(element) {
  // 保存选中元素；为 null 时面板显示空状态
  selectedElement.value = element || null
  // 先清空条件文本，避免上一次选中连线的内容残留
  conditionText.value = ''
  // 未选中任何元素时无需继续回填
  if (!element) return
  // 名称优先取 bpmn 业务对象里的 name，没有则为空串
  elementName.value = element.businessObject?.name || ''
  // 用户任务：先用默认配置打底，再覆盖为已保存配置（深拷贝避免直接引用 nodeConfig 中的对象）
  if (element.type === 'bpmn:UserTask') {
    Object.assign(taskConfig, defaultTask(), JSON.parse(JSON.stringify(nodeConfig.value[element.id] || {})))
  }
  // 连线：把已保存的条件表达式 body 回填到文本框
  if (element.type === 'bpmn:SequenceFlow') {
    conditionText.value = element.businessObject?.conditionExpression?.body || ''
  }
}

// 节点名称修改：通过 modeling 服务写回 bpmn 模型，保证画布显示与表单一致
function updateName() {
  // 防御：理论上仅在选中元素时才会触发
  if (!selectedElement.value) return
  // updateProperties 会同时更新画布文本并触发 commandStack.changed（从而标记 dirty）
  modeler.get('modeling').updateProperties(selectedElement.value, { name: elementName.value })
}

// 连线条件修改：文本为空则删除条件，否则创建 BPMN 形式表达式并挂到连线上
function updateCondition() {
  // 仅对连线元素生效，其他类型直接忽略
  if (!selectedElement.value || selectedElement.value.type !== 'bpmn:SequenceFlow') return
  // modeling 用于更新元素属性，moddle 用于创建 BPMN 模型对象
  const modeling = modeler.get('modeling')
  const moddle = modeler.get('moddle')
  // 去空格后判空，避免保存只有空白的无效条件
  const text = conditionText.value.trim()
  if (!text) {
    // 置为 undefined 表示移除条件，该连线成为无条件（网关默认）分支
    modeling.updateProperties(selectedElement.value, { conditionExpression: undefined })
    return
  }
  // 创建 FormalExpression，body 为条件原文（后端据此解析执行）
  const expression = moddle.create('bpmn:FormalExpression', { body: text })
  modeling.updateProperties(selectedElement.value, { conditionExpression: expression })
}

// 加载审批人候选数据：四个接口并行请求，缩短首屏等待
// 任一接口失败都会由 request 统一提示并 reject，从而中断后续初始化
async function loadOptions() {
  const [users, roles, depts, groups] = await Promise.all([
    // 可选用户列表（指定用户/抄送人使用）
    request.get('/wf/option/users'),
    // 可选角色列表
    request.get('/wf/option/roles'),
    // 可选部门列表
    request.get('/wf/option/depts'),
    // 可选用户分组列表
    request.get('/wf/option/groups')
  ])
  // 用 || [] 兜底，避免后端返回空值时下拉渲染报错
  options.users = users.data || []
  options.roles = roles.data || []
  options.depts = depts.data || []
  options.groups = groups.data || []
}

// 加载模型详情：回填元信息、节点配置，并把 BPMN XML 导入画布
async function loadModel() {
  // 设计接口返回 { 元信息, bpmn_xml, node_config }
  const res = await request.get(`/wf/model/design/${route.params.id}`)
  Object.assign(model, {
    id: res.data.id,
    model_name: res.data.model_name,
    model_key: res.data.model_key,
    version: res.data.version,
    status: res.data.status
  })
  // 节点配置整体替换（未配置过的节点在保存时保持原样）
  nodeConfig.value = res.data.node_config || {}
  // 新建模型尚无 XML 时使用默认“开始→审批→结束”流程图
  await modeler.importXML(res.data.bpmn_xml || defaultXml())
  // 自适应视口：保证整张流程图完整落在可视区域内
  modeler.get('canvas').zoom('fit-viewport')
  // 刚加载完成不算用户改动，避免返回时误报未保存
  dirty.value = false
}

// 保存设计：导出当前画布 XML，连同节点配置一次性提交后端
async function save() {
  // 进入保存态，按钮显示 loading 防重复点击
  saving.value = true
  try {
    // format: true 输出带缩进的 XML，便于后端排查与后续 diff
    const { xml } = await modeler.saveXML({ format: true })
    await request.post('/wf/model/save', {
      id: model.id,
      bpmn_xml: xml,
      node_config: nodeConfig.value
    })
    // 保存成功后清除脏标记
    dirty.value = false
    ElMessage.success('流程设计保存成功')
  } finally {
    // 无论成功失败都恢复按钮状态（失败提示由 request 统一处理）
    saving.value = false
  }
}

// 返回列表页：存在未保存改动时先二次确认，用户取消则留在当前页
async function goBack() {
  if (dirty.value) {
    try {
      await ElMessageBox.confirm('当前设计尚未保存，确认离开吗？', '提示', { type: 'warning' })
    } catch (e) {
      // ElMessageBox 取消会 reject，这里直接返回，防止继续跳转
      return
    }
  }
  router.push('/workflow/manage/model')
}

// 深度监听审批配置：任何字段变化都写回 nodeConfig 并标记为未保存
// 这样即使切换选中节点，已修改的配置也不会丢失
watch(taskConfig, () => {
  const element = selectedElement.value
  // 只有当前选中的是用户任务时才写回，避免把配置写到连线等元素上
  if (element && element.type === 'bpmn:UserTask') {
    // 深拷贝后存入，隔离 taskConfig 的后续变化
    nodeConfig.value[element.id] = JSON.parse(JSON.stringify(taskConfig))
    // 配置变更属于未保存改动
    dirty.value = true
  }
}, { deep: true })

// 页面挂载：创建 bpmn 建模器并绑定画布事件，再加载候选数据与模型
onMounted(async () => {
  // 以画布 DOM 为容器实例化 Modeler（默认带调色板，可拖拽创建节点）
  modeler = new BpmnModeler({ container: canvasRef.value })
  // 选中变化时同步右侧属性面板（newSelection 为空表示取消选中）
  modeler.on('selection.changed', event => selectElement(event.newSelection[0]))
  // 任何命令栈变化（移动、连线、改属性等）都视为画布有未保存改动
  modeler.on('commandStack.changed', () => { dirty.value = true })
  // 先加载下拉候选，再加载模型并渲染画布
  await loadOptions()
  await loadModel()
})

// 页面卸载：销毁建模器释放事件与 DOM，防止内存泄漏
onBeforeUnmount(() => {
  if (modeler) modeler.destroy()
  modeler = null
})
</script>

<style scoped>
/* 样式仅作用于本页，避免与 bpmn-js 自带类名冲突 */
.design-page {
  /* 页面根容器：纵向排列工具栏与画布区 */
  display: flex;
  flex-direction: column;
  /* 高度扣减 96px 以适配全局顶栏/面包屑，防止出现整页纵向滚动条 */
  height: calc(100vh - 96px);
  padding: 12px 16px 16px;
  box-sizing: border-box;
}
.design-top {
  /* 顶部工具栏：两端对齐，底部留白与画布区分隔 */
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.design-left,
.design-right {
  /* 左右分组内部横向排列，gap 统一子元素间距 */
  display: flex;
  align-items: center;
  gap: 12px;
}
.design-title {
  /* 模型标题区：名称与两个标签横向排列 */
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
}
.design-tip {
  /* 操作提示使用 Element Plus 次要文字色变量，自动适配暗色主题 */
  color: var(--el-text-color-secondary);
  font-size: 13px;
}
.design-body {
  /* 主体区占满剩余高度，横向排列画布与属性面板 */
  flex: 1;
  display: flex;
  gap: 12px;
  /* min-height:0 防止 flex 子项按内容撑高，保证画布内部滚动而不是整页滚动 */
  min-height: 0;
}
.designer-canvas {
  /* 画布占满剩余宽度；min-width:0 允许在窄屏下被压缩 */
  flex: 1;
  min-width: 0;
  /* 使用应用级表面色变量，与整体主题（含暗色）保持一致 */
  background: var(--app-surface);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  /* 裁掉 bpmn 画布可能溢出的内容，避免出现页面级滚动条 */
  overflow: hidden;
}
.props-panel {
  /* 属性面板固定宽度且不参与伸缩，内容超出时自身纵向滚动 */
  width: 320px;
  flex: none;
  background: var(--app-surface);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  padding: 12px;
  overflow-y: auto;
}
.panel-title {
  /* 面板主标题：加粗并留出下方间距 */
  font-weight: 600;
  font-size: 15px;
  margin-bottom: 10px;
}
.panel-subtitle {
  /* 分组小标题：主题色文字 + 左侧竖条，强化配置分组视觉层级 */
  font-weight: 600;
  font-size: 13px;
  color: var(--el-color-primary);
  margin: 12px 0 8px;
  padding-left: 8px;
  border-left: 3px solid var(--el-color-primary);
}
.panel-hint {
  /* 提示块：浅填充背景 + 次要文字色，承载网关/条件等说明文案 */
  margin-top: 10px;
  padding: 10px 12px;
  background: var(--el-fill-color-lighter);
  border-radius: 6px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  line-height: 1.6;
}
</style>
