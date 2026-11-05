<!--
  文件级说明：流程任务管理页（workflow/task/index.vue）
  职责：面向管理员的全局任务监控；按任务状态/处理人筛选人工任务，支持查看流程详情与把待办任务转派给他人。
  依赖：@/utils/request、workflow/WorkflowDetail.vue（流程详情抽屉/弹窗）、Element Plus、v-perm 权限指令。
  使用方：由工作流管理菜单下的「流程任务」路由加载，仅具备 wf:task:* 权限的管理员使用。
-->
<template>
  <!-- 页面根容器：套用全局布局样式 -->
  <div class="app-container">
    <!-- 页头：标题 + 任务总数 -->
    <div class="page-header">
      <div class="page-title-wrap">
        <h2>流程任务</h2>
        <!-- total 随查询条件变化，反映当前筛选下的任务规模 -->
        <div class="sub">全局人工任务监控与转派 · 共 {{ total }} 条记录</div>
      </div>
    </div>

    <!-- 搜索区：按任务状态与处理人过滤 -->
    <el-card shadow="never" class="search-card">
      <el-form :model="query" inline @submit.prevent>
        <!-- 任务状态筛选：选项来自 statusOptions 常量 -->
        <el-form-item label="任务状态">
          <el-select v-model="query.status" placeholder="请选择" clearable style="width: 150px">
            <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <!-- 处理人筛选：filterable 支持输入关键字快速定位人员 -->
        <el-form-item label="处理人">
          <el-select v-model="query.assignee" placeholder="请选择" clearable filterable style="width: 180px">
            <!-- 下拉标签显示「昵称（用户名）」，值与后端 assignee 用户 id 对齐 -->
            <el-option v-for="u in users" :key="u.id" :label="userLabel(u)" :value="u.id" />
          </el-select>
        </el-form-item>
        <el-form-item class="search-actions">
          <!-- 查询：回到第一页并按条件请求 -->
          <el-button type="primary" :icon="Search" @click="handleQuery">查询</el-button>
          <!-- 重置：清空状态与处理人条件 -->
          <el-button :icon="Refresh" @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 列表区卡片：本页无新增/批量操作，仅展示表格与分页 -->
    <el-card shadow="never" class="table-card">
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据">
        <!-- 自动序号列 -->
        <el-table-column type="index" label="序号" width="70" align="center" />
        <!-- 任务节点名称：如「部门经理审批」 -->
        <el-table-column label="任务节点" prop="task_name" min-width="140" show-overflow-tooltip />
        <!-- 流程名称：任务所属流程模型 -->
        <el-table-column label="流程名称" prop="model_name" min-width="130" show-overflow-tooltip />
        <!-- 业务单据号：实例 key，用于与业务系统对账 -->
        <el-table-column label="业务单据号" prop="instance_key" min-width="150" show-overflow-tooltip />
        <!-- 处理人姓名：后端已转换为名称 -->
        <el-table-column label="处理人" prop="assignee_name" width="110" align="center" />
        <!-- 审批方式：如或签/会签等，后端已给出中文名 -->
        <el-table-column label="审批方式" prop="approve_mode_name" width="100" align="center" />
        <!-- 任务状态列：用颜色区分待办/已办/转派等状态 -->
        <el-table-column label="任务状态" width="100" align="center">
          <template #default="scope">
            <!-- taskTagType 把状态码映射为标签颜色；文案直接取后端 status_name -->
            <el-tag :type="taskTagType(scope.row.status)">{{ scope.row.status_name }}</el-tag>
          </template>
        </el-table-column>
        <!-- 生成时间：任务创建时间 -->
        <el-table-column label="生成时间" prop="start_time" width="170" />
        <!-- 到期时间：超时提醒依据 -->
        <el-table-column label="到期时间" prop="due_time" width="170" />
        <!-- 操作列：查看详情 + 转派 -->
        <el-table-column label="操作" width="150" align="center" fixed="right">
          <template #default="scope">
            <!-- 查看：打开流程详情组件，无需额外权限（所有能进入本页的管理员都可看） -->
            <el-button link type="primary" :icon="View" @click="openDetail(scope.row)">查看</el-button>
            <!-- 转派：仅当任务仍为待办(0) 且所属流程实例仍在运行(0) 时可操作；实例已结束则转派无意义 -->
            <el-button v-perm="'wf:task:transfer'" link type="warning" :icon="Switch"
              :disabled="scope.row.status !== 0 || scope.row.instance_status !== 0" @click="openTransfer(scope.row)">转派</el-button>
          </template>
        </el-table-column>
      </el-table>
      <!-- 分页：绑定 query，页码或每页条数变化时重新请求 -->
      <div class="pagination-wrap">
        <el-pagination background layout="total, sizes, prev, pager, next, jumper"
          :total="total" v-model:current-page="query.page" v-model:page-size="query.page_size"
          :page-sizes="[10, 20, 50, 100]" @change="getList" />
      </div>
    </el-card>

    <!-- 转派弹窗：选择新处理人并填写说明 -->
    <el-dialog v-model="transferVisible" title="转派任务" width="460px" :close-on-click-modal="false">
      <el-form label-width="80px">
        <!-- 任务节点：只读展示，确认转派对象 -->
        <el-form-item label="任务节点">
          <el-input :model-value="transferTask.task_name" disabled />
        </el-form-item>
        <!-- 转派目标：filterable 便于在长用户列表中检索 -->
        <el-form-item label="转派给">
          <el-select v-model="transferUserId" filterable placeholder="请选择处理人" style="width: 100%">
            <el-option v-for="u in users" :key="u.id" :label="userLabel(u)" :value="u.id" />
          </el-select>
        </el-form-item>
        <!-- 转派说明：选填，会写入任务流转记录便于追溯 -->
        <el-form-item label="转派说明">
          <el-input v-model="transferComment" type="textarea" :rows="3" placeholder="请输入转派说明" />
        </el-form-item>
      </el-form>
      <!-- 底部按钮：确定走 submitTransfer，loading 防止重复提交 -->
      <template #footer>
        <el-button @click="transferVisible = false">取消</el-button>
        <el-button type="primary" :loading="transferSaving" @click="submitTransfer">确定</el-button>
      </template>
    </el-dialog>

    <!-- 流程详情组件：以 v-model 控制显隐，通过 instance-id 拉取对应实例详情 -->
    <WorkflowDetail v-model="detailVisible" :instance-id="currentInstanceId" />
  </div>
</template>

<script setup>
// 组合式 API：ref 管理状态，reactive 管理查询/转派任务信息，onMounted 首屏加载
import { ref, reactive, onMounted } from 'vue'
// 操作结果与校验提示
import { ElMessage } from 'element-plus'
// 搜索、刷新、查看、转派图标
import { Search, Refresh, View, Switch } from '@element-plus/icons-vue'
// 统一请求实例
import request from '@/utils/request'
// 流程详情组件：展示实例流转信息、审批记录与表单数据
import WorkflowDetail from '@/components/workflow/WorkflowDetail.vue'

// 任务状态枚举：与后端 status 字段一一对应，驱动筛选下拉与标签颜色
const statusOptions = [
  // 待办：当前处理人尚未审批
  { label: '待办', value: 0 },
  // 已办：该任务已被处理完成
  { label: '已办', value: 1 },
  // 已转派：任务被移交给他人
  { label: '已转派', value: 2 },
  // 已加签：任务新增了会签/加签人
  { label: '已加签', value: 3 },
  // 已驳回：任务被驳回
  { label: '已驳回', value: 4 }
]
// 列表加载中标记
const loading = ref(false)
// 当前页任务列表
const rows = ref([])
// 任务总数
const total = ref(0)
// 用户下拉候选（筛选处理人、转派目标共用）
const users = ref([])
// 查询条件：status/assignee 为空串表示不筛选
const query = reactive({ page: 1, page_size: 10, status: '', assignee: '' })
// 流程详情组件显隐
const detailVisible = ref(false)
// 当前查看的流程实例 id，传给详情组件
const currentInstanceId = ref(0)
// 转派弹窗显隐
const transferVisible = ref(false)
// 转派提交中标记
const transferSaving = ref(false)
// 转派目标用户 id；初始 undefined 便于校验“是否选择”
const transferUserId = ref()
// 转派说明（选填）
const transferComment = ref('')
// 当前转派任务信息：id 用于拼接口，task_name 用于弹窗只读展示
const transferTask = reactive({ id: 0, task_name: '' })

// 用户展示名：优先「昵称（用户名）」，无昵称时只用用户名
function userLabel(user) {
  return user.nickname ? `${user.nickname}（${user.username}）` : user.username
}
// 任务状态码转标签颜色：待办橙色提醒、已办绿色、已转派灰色、已加签蓝色、已驳回红色；未知状态兜底灰色
function taskTagType(status) {
  return { 0: 'warning', 1: 'success', 2: 'info', 3: 'primary', 4: 'danger' }[status] || 'info'
}
// 拉取任务列表：query 携带分页与筛选条件
async function getList() {
  loading.value = true
  try {
    // GET /api/wf/task/list，返回 { list, total }
    const res = await request.get('/wf/task/list', { params: query })
    rows.value = res.data.list
    total.value = res.data.total
  } finally {
    // 始终关闭加载遮罩
    loading.value = false
  }
}
// 加载用户下拉候选：筛选项与转派目标都复用这份数据
async function loadUsers() {
  const res = await request.get('/wf/option/users')
  // 兜底空数组，防止后端返回 null 导致下拉报错
  users.value = res.data || []
}
// 查询：回到第一页
function handleQuery() {
  query.page = 1
  getList()
}
// 重置：清空状态与处理人筛选
function resetQuery() {
  Object.assign(query, { page: 1, status: '', assignee: '' })
  getList()
}
// 查看详情：记录实例 id 后打开详情组件
function openDetail(row) {
  currentInstanceId.value = row.instance_id
  detailVisible.value = true
}
// 打开转派弹窗：记录任务 id/名称，并清空上次选择与说明
function openTransfer(row) {
  transferTask.id = row.id
  transferTask.task_name = row.task_name
  // 置 undefined 触发占位提示，避免残留上次的转派对象
  transferUserId.value = undefined
  transferComment.value = ''
  transferVisible.value = true
}
// 提交转派：必须选择目标用户，再调用转派接口
async function submitTransfer() {
  if (!transferUserId.value) {
    // 未选择用户时前端拦截，减少无效请求
    ElMessage.warning('请选择转派处理人')
    return
  }
  transferSaving.value = true
  try {
    // POST /api/wf/task/transfer/{taskId}，user_id 为新处理人，comment 为说明
    await request.post(`/wf/task/transfer/${transferTask.id}`, {
      user_id: transferUserId.value,
      comment: transferComment.value
    })
    ElMessage.success('转派成功')
    transferVisible.value = false
    // 刷新列表以展示新的处理人与任务状态
    getList()
  } finally {
    transferSaving.value = false
  }
}

// 挂载后先加载用户下拉，再拉任务列表
onMounted(async () => {
  await loadUsers()
  getList()
})
</script>
