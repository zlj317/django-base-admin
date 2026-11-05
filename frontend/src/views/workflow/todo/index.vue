<!--
  文件级说明：待办任务页（workflow/todo/index.vue）
  职责：展示「待我审批」的任务，提供同意、驳回、转审、加签、退回、查看详情等审批动作。
  依赖：@/utils/request、workflow/WorkflowDetail.vue 流程详情组件、Element Plus、v-perm 权限指令。
  使用方：由「待办任务」菜单路由加载，面向所有审批人；动作按钮按各自权限点控制显隐。
-->
<template>
  <!-- 页面根容器：套用全局布局样式 -->
  <div class="app-container">
    <!-- 页头：标题 + 当前待办总数 -->
    <div class="page-header">
      <div class="page-title-wrap">
        <h2>待办任务</h2>
        <!-- total 为后端返回的待办总数，任务处理后会随刷新减少 -->
        <div class="sub">待我审批的流程任务 · 共 {{ total }} 条记录</div>
      </div>
    </div>

    <!-- 表格卡片：无搜索条件，仅提供手动刷新 -->
    <el-card shadow="never" class="table-card">
      <template #header>
        <div class="card-header">
          <div class="card-actions">
            <!-- 刷新：重新拉取待办，确保看到他人转审/加签过来的新任务 -->
            <el-button :icon="Refresh" @click="getList">刷新</el-button>
          </div>
        </div>
      </template>
      <!-- 待办表格：空态文案明确说明当前没有待审批任务 -->
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无待办任务">
        <!-- 自动序号列 -->
        <el-table-column type="index" label="序号" width="70" align="center" />
        <!-- 任务节点名称 -->
        <el-table-column label="任务节点" prop="task_name" min-width="140" show-overflow-tooltip />
        <!-- 流程名称 -->
        <el-table-column label="流程名称" prop="model_name" min-width="130" show-overflow-tooltip />
        <!-- 业务单据号：实例 key -->
        <el-table-column label="业务单据号" prop="instance_key" min-width="160" show-overflow-tooltip />
        <!-- 发起人姓名：帮助审批人判断业务来源 -->
        <el-table-column label="发起人" prop="start_user_name" width="100" align="center" />
        <!-- 审批方式：或签/会签等 -->
        <el-table-column label="审批方式" prop="approve_mode_name" width="100" align="center" />
        <!-- 生成时间：任务到达时间 -->
        <el-table-column label="生成时间" prop="start_time" width="170" />
        <!-- 到期时间：无到期时间时显示短横线，避免空白 -->
        <el-table-column label="到期时间" prop="due_time" width="170">
          <template #default="scope">{{ scope.row.due_time || '-' }}</template>
        </el-table-column>
        <!-- 操作列：审批动作较多，宽度 300 并固定右侧 -->
        <el-table-column label="操作" width="300" align="center" fixed="right">
          <template #default="scope">
            <!-- 同意：需 wf:task:approve 权限；通过后流程流向下一节点 -->
            <el-button v-perm="'wf:task:approve'" link type="success" :icon="Check" @click="openAction(scope.row, 'approve')">同意</el-button>
            <!-- 驳回：需 wf:task:reject 权限；弹窗中审批意见为必填，驳回后流程回到发起人或上一节点 -->
            <el-button v-perm="'wf:task:reject'" link type="danger" :icon="Close" @click="openAction(scope.row, 'reject')">驳回</el-button>
            <!-- 转审：需 wf:task:transfer 权限；把当前任务移交给另一位处理人 -->
            <el-button v-perm="'wf:task:transfer'" link type="warning" :icon="Switch" @click="openAssign(scope.row, 'transfer')">转审</el-button>
            <!-- 加签：需 wf:task:addsign 权限；在当前节点追加审批人，原处理人仍保留 -->
            <el-button v-perm="'wf:task:addsign'" link type="primary" :icon="Plus" @click="openAssign(scope.row, 'addsign')">加签</el-button>
            <!-- 退回：需 wf:task:back 权限；把任务退回上一步，审批意见选填 -->
            <el-button v-perm="'wf:task:back'" link type="info" :icon="Back" @click="openAction(scope.row, 'back')">退回</el-button>
            <!-- 查看：打开流程详情，无权限点限制，仅阅读不改变流程 -->
            <el-button link type="primary" :icon="View" @click="openDetail(scope.row)">查看</el-button>
          </template>
        </el-table-column>
      </el-table>
      <!-- 分页：绑定 query 的 page/page_size，变化后重新请求 -->
      <div class="pagination-wrap">
        <el-pagination background layout="total, sizes, prev, pager, next, jumper"
          :total="total" v-model:current-page="query.page" v-model:page-size="query.page_size"
          :page-sizes="[10, 20, 50, 100]" @change="getList" />
      </div>
    </el-card>

    <!-- 审批动作弹窗：同意/驳回/退回共用，标题与必填策略由 openAction 按 type 动态设置 -->
    <el-dialog v-model="actionVisible" :title="actionTitle" width="480px" :close-on-click-modal="false">
      <el-form label-width="80px">
        <!-- 任务节点：只读，防止用户误以为可以在此修改节点 -->
        <el-form-item label="任务节点">
          <el-input :model-value="currentTask.task_name" disabled />
        </el-form-item>
        <!-- 审批意见：驳回时必填，其余动作选填；占位文案随 actionRequireComment 切换 -->
        <el-form-item label="审批意见">
          <el-input v-model="actionComment" type="textarea" :rows="4"
            :placeholder="actionRequireComment ? '驳回必须填写审批意见' : '请输入审批意见（选填）'" />
        </el-form-item>
      </el-form>
      <!-- 底部按钮：确定调用 submitAction，提交中禁用重复点击 -->
      <template #footer>
        <el-button @click="actionVisible = false">取消</el-button>
        <el-button type="primary" :loading="actionSaving" @click="submitAction">确定</el-button>
      </template>
    </el-dialog>

    <!-- 转审/加签弹窗：两种动作共用，选择目标用户并填写说明 -->
    <el-dialog v-model="assignVisible" :title="assignTitle" width="480px" :close-on-click-modal="false">
      <el-form label-width="80px">
        <!-- 任务节点：只读展示当前操作对象 -->
        <el-form-item label="任务节点">
          <el-input :model-value="currentTask.task_name" disabled />
        </el-form-item>
        <!-- 目标用户：label 随动作切换（转审给/加签人）；排除当前处理人，避免转给自己 -->
        <el-form-item :label="assignLabel">
          <el-select v-model="assignUserId" filterable placeholder="请选择用户" style="width: 100%">
            <el-option v-for="u in users" :key="u.id" :label="userLabel(u)" :value="u.id"
              :disabled="u.id === currentTask.assignee" />
          </el-select>
        </el-form-item>
        <!-- 说明：选填，记录转审/加签原因 -->
        <el-form-item label="说明">
          <el-input v-model="assignComment" type="textarea" :rows="4" placeholder="请输入说明（选填）" />
        </el-form-item>
      </el-form>
      <!-- 底部按钮：确定调用 submitAssign -->
      <template #footer>
        <el-button @click="assignVisible = false">取消</el-button>
        <el-button type="primary" :loading="assignSaving" @click="submitAssign">确定</el-button>
      </template>
    </el-dialog>

    <!-- 流程详情组件：v-model 控制显隐，instance-id 指定要查看的实例 -->
    <WorkflowDetail v-model="detailVisible" :instance-id="currentInstanceId" />
  </div>
</template>

<script setup>
// 组合式 API：ref 管理每个弹窗/请求状态，reactive 管理分页与当前任务，onMounted 首屏加载
import { ref, reactive, onMounted } from 'vue'
// 操作结果与校验提示
import { ElMessage } from 'element-plus'
// 刷新、查看、同意、驳回、转审、加签、退回图标
import { Refresh, View, Check, Close, Switch, Plus, Back } from '@element-plus/icons-vue'
// 统一请求实例
import request from '@/utils/request'
// 流程详情组件：展示流转轨迹与表单内容
import WorkflowDetail from '@/components/workflow/WorkflowDetail.vue'

// 列表加载中标记
const loading = ref(false)
// 当前页待办任务
const rows = ref([])
// 待办总数
const total = ref(0)
// 用户下拉候选（转审/加签目标）
const users = ref([])
// 分页条件：本页固定只查当前用户的待办，因此 query 不含筛选字段
const query = reactive({ page: 1, page_size: 10 })
// 流程详情组件显隐
const detailVisible = ref(false)
// 当前查看的流程实例 id
const currentInstanceId = ref(0)

// 审批动作弹窗状态
// 弹窗显隐
const actionVisible = ref(false)
// 提交中标记
const actionSaving = ref(false)
// 当前动作类型：approve/reject/back，决定请求路径与提示文案
const actionType = ref('approve')
// 审批意见
const actionComment = ref('')
// 当前操作的任务：id 用于拼接口，task_name 用于展示，assignee 用于排除当前处理人
const currentTask = reactive({ id: 0, task_name: '', assignee: 0 })
// 审批意见是否必填：仅驳回时必填
const actionRequireComment = ref(false)

// 转审/加签弹窗状态
// 弹窗显隐
const assignVisible = ref(false)
// 提交中标记
const assignSaving = ref(false)
// 当前动作类型：transfer/addsign，决定请求路径
const assignType = ref('transfer')
// 目标用户 id
const assignUserId = ref()
// 操作说明（选填）
const assignComment = ref('')

// 动作类型到弹窗标题的映射，避免在模板里写三元表达式
const actionTitles = { approve: '审批同意', reject: '审批驳回', back: '退回上一步' }
// 转审/加签的弹窗标题映射
const assignTitles = { transfer: '转审任务', addsign: '加签任务' }
// 当前审批弹窗标题（由 openAction 写入）
const actionTitle = ref('')
// 当前转审/加签弹窗标题（由 openAssign 写入）
const assignTitle = ref('')
// 目标用户表单项的标签文案：转审为「转审给」，加签为「加签人」
const assignLabel = ref('转审给')

// 用户展示名：优先「昵称（用户名）」，无昵称时只用用户名
function userLabel(user) {
  return user.nickname ? `${user.nickname}（${user.username}）` : user.username
}
// 拉取当前用户的待办任务
async function getList() {
  loading.value = true
  try {
    // GET /api/wf/task/todo，后端按当前登录人过滤，无需前端传用户 id
    const res = await request.get('/wf/task/todo', { params: query })
    rows.value = res.data.list
    total.value = res.data.total
  } finally {
    // 始终关闭加载遮罩
    loading.value = false
  }
}
// 加载用户下拉候选：转审与加签共用
async function loadUsers() {
  const res = await request.get('/wf/option/users')
  // 兜底空数组，防止后端返回 null 导致下拉报错
  users.value = res.data || []
}
// 查看详情：记录实例 id 后打开详情组件
function openDetail(row) {
  currentInstanceId.value = row.instance_id
  detailVisible.value = true
}
// 打开审批动作弹窗：type 为 approve/reject/back
function openAction(row, type) {
  // 记录任务信息，尤其 assignee 供加签时排除当前处理人
  Object.assign(currentTask, { id: row.id, task_name: row.task_name, assignee: row.assignee })
  actionType.value = type
  // 每次打开都清空上次意见，避免误提交旧内容
  actionComment.value = ''
  // 标题由动作类型映射得到
  actionTitle.value = actionTitles[type]
  // 只有驳回强制填写意见，同意/退回选填
  actionRequireComment.value = type === 'reject'
  actionVisible.value = true
}
// 打开转审/加签弹窗：type 为 transfer/addsign
function openAssign(row, type) {
  // 记录当前任务信息
  Object.assign(currentTask, { id: row.id, task_name: row.task_name, assignee: row.assignee })
  assignType.value = type
  // 清空上次选择与说明，reset 为 undefined 以显示占位提示
  assignUserId.value = undefined
  assignComment.value = ''
  assignTitle.value = assignTitles[type]
  // 按动作类型切换目标用户标签
  assignLabel.value = type === 'transfer' ? '转审给' : '加签人'
  assignVisible.value = true
}
// 提交审批动作：同意/驳回/退回共用一个接口前缀
async function submitAction() {
  // 驳回必须填写意见，trim 后为空视为未填写
  if (actionRequireComment.value && !actionComment.value.trim()) {
    ElMessage.warning('请填写驳回意见')
    return
  }
  actionSaving.value = true
  try {
    // POST /api/wf/task/{approve|reject|back}/{taskId}，请求体只带审批意见
    await request.post(`/wf/task/${actionType.value}/${currentTask.id}`, { comment: actionComment.value })
    // 按动作类型给出对应成功提示
    ElMessage.success(actionType.value === 'approve' ? '审批通过' : actionType.value === 'reject' ? '已驳回' : '已退回')
    actionVisible.value = false
    // 刷新待办列表：已处理的任务会从列表中消失
    getList()
  } finally {
    actionSaving.value = false
  }
}
// 提交转审/加签：必须选择目标用户
async function submitAssign() {
  if (!assignUserId.value) {
    // 提示文案随动作类型变化，帮助用户明确缺少什么
    ElMessage.warning(assignLabel.value === '加签人' ? '请选择加签人' : '请选择转审人')
    return
  }
  assignSaving.value = true
  try {
    // POST /api/wf/task/{transfer|addsign}/{taskId}，user_id 为目标用户
    await request.post(`/wf/task/${assignType.value}/${currentTask.id}`, {
      user_id: assignUserId.value,
      comment: assignComment.value
    })
    // 按动作类型提示结果
    ElMessage.success(assignType.value === 'transfer' ? '转审成功' : '加签成功')
    assignVisible.value = false
    getList()
  } finally {
    assignSaving.value = false
  }
}

// 挂载后先加载用户下拉，再拉待办列表
onMounted(async () => {
  await loadUsers()
  getList()
})
</script>
