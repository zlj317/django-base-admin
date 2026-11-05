<template>
  <!-- 文件说明：工作流“流程实例”监控页，按模型/状态/业务单据号筛选全部流程实例，并支持查看详情与管理员终止运行中的实例。 -->
  <!-- 依赖后端接口 GET /wf/instance/list、GET /wf/model/list、POST /wf/instance/terminate/{id}，以及公共组件 WorkflowDetail。 -->
  <!-- 使用方：由后台动态菜单配置指向本组件；终止按钮受 v-perm 权限指令控制，无权限用户看不到该入口。 -->
  <!-- 页面根容器：复用全局 app-container 内边距，保持后台页面留白一致。 -->
  <div class="app-container">
    <!-- 页头区域：标题与实例总数，总数随查询条件变化。 -->
    <div class="page-header">
      <!-- 标题与副标题的排版容器。 -->
      <div class="page-title-wrap">
        <!-- 页面主标题。 -->
        <h2>流程实例</h2>
        <!-- 副标题：说明这是全量实例监控视图，并展示当前条件下的总记录数。 -->
        <div class="sub">全部流程实例监控 · 共 {{ total }} 条记录</div>
      </div>
    </div>

    <!-- 查询卡片：集中放置筛选条件；shadow="never" 保持与列表卡片一致的扁平外观。 -->
    <el-card shadow="never" class="search-card">
      <!-- 查询表单：:model 绑定 query 使各控件双向同步；inline 让条件横向排列；@submit.prevent 阻止回车触发表单原生提交。 -->
      <el-form :model="query" inline @submit.prevent>
        <!-- 流程模型筛选项：按所属流程模型过滤实例。 -->
        <el-form-item label="流程模型">
          <!-- 模型下拉：选项来自 /wf/model/list；clearable 允许清空条件；固定宽度保证筛选栏整齐。 -->
          <el-select v-model="query.model_id" placeholder="请选择" clearable style="width: 190px">
            <!-- 动态选项：遍历后端模型列表，key 用模型 id 保证唯一，展示 model_name，选中值回填模型 id。 -->
            <el-option v-for="m in modelOptions" :key="m.id" :label="m.model_name" :value="m.id" />
          </el-select>
        </el-form-item>
        <!-- 流程状态筛选项：按实例状态过滤。 -->
        <el-form-item label="流程状态">
          <!-- 状态下拉：0-3 与后端实例状态枚举一一对应；clearable 支持清空状态条件。 -->
          <el-select v-model="query.status" placeholder="请选择" clearable style="width: 150px">
            <!-- 静态状态选项：与表格状态标签映射保持一致，避免前后端文案不一致。 -->
            <el-option label="运行中" :value="0" />
            <el-option label="已完成" :value="1" />
            <el-option label="已驳回" :value="2" />
            <el-option label="已终止" :value="3" />
          </el-select>
        </el-form-item>
        <!-- 业务单据号筛选项：按业务主键检索实例。 -->
        <el-form-item label="业务单据号">
          <!-- 单据号输入框：回车直接触发查询，符合表单检索习惯；clearable 便于快速清空。 -->
          <el-input v-model="query.biz_key" placeholder="请输入单据号" clearable style="width: 180px" @keyup.enter="handleQuery" />
        </el-form-item>
        <!-- 查询操作项：右侧放置查询与重置按钮。 -->
        <el-form-item class="search-actions">
          <!-- 查询按钮：调用 handleQuery，会先回到第一页再请求，避免停留在不存在的页码上。 -->
          <el-button type="primary" :icon="Search" @click="handleQuery">查询</el-button>
          <!-- 重置按钮：清空模型、状态、单据号并回到第一页，再重新查询。 -->
          <el-button :icon="Refresh" @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 列表卡片：承载实例表格，shadow="never" 与查询卡片保持统一扁平风格。 -->
    <el-card shadow="never" class="table-card">
      <!-- 实例表格：loading 控制请求遮罩，rows 为实例数据，stripe 斑马纹，empty-text 提供空态文案。 -->
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据">
        <!-- 序号列：表格自动生成行号，不依赖后端字段。 -->
        <el-table-column type="index" label="序号" width="70" align="center" />
        <!-- 业务单据号列：显示流程关联的业务主键，便于跨系统核对。 -->
        <el-table-column label="业务单据号" prop="biz_key" min-width="160" show-overflow-tooltip />
        <!-- 流程名称列：显示流程模型名称，超长省略并悬浮显示全文。 -->
        <el-table-column label="流程名称" prop="model_name" min-width="130" show-overflow-tooltip />
        <!-- 版本列：在版本号前加 v 前缀展示，方便区分同一流程模型的不同发布版本。 -->
        <el-table-column label="版本" width="70" align="center">
          <template #default="scope">v{{ scope.row.model_version }}</template>
        </el-table-column>
        <!-- 发起人列：显示流程发起人姓名，固定宽度居中。 -->
        <el-table-column label="发起人" prop="start_user_name" width="110" align="center" />
        <!-- 流程状态列：展示实例当前状态。 -->
        <el-table-column label="流程状态" width="100" align="center">
          <template #default="scope">
            <!-- 状态标签：颜色由 statusType 按状态码映射，文案使用后端 status_name。 -->
            <el-tag :type="statusType(scope.row.status)">{{ scope.row.status_name }}</el-tag>
          </template>
        </el-table-column>
        <!-- 当前节点列：显示实例当前停留的流程节点名称，便于快速定位卡点。 -->
        <el-table-column label="当前节点" prop="current_node" min-width="130" show-overflow-tooltip />
        <!-- 发起时间列：实例创建时间。 -->
        <el-table-column label="发起时间" prop="start_time" width="170" />
        <!-- 结束时间列：实例结束时间，运行中的实例通常为空。 -->
        <el-table-column label="结束时间" prop="end_time" width="170" />
        <!-- 操作列：固定在右侧，保证横向滚动时操作入口始终可见。 -->
        <el-table-column label="操作" width="150" align="center" fixed="right">
          <template #default="scope">
            <!-- 查看按钮：打开流程实例详情，查看审批轨迹与表单数据。 -->
            <el-button link type="primary" :icon="View" @click="openDetail(scope.row)">查看</el-button>
            <!-- 终止按钮：受 wf:instance:terminate 权限控制；仅运行中（status===0）可点击，避免对已结束实例误操作。 -->
            <el-button v-perm="'wf:instance:terminate'" link type="danger" :icon="CircleClose"
              :disabled="scope.row.status !== 0" @click="terminate(scope.row)">终止</el-button>
          </template>
        </el-table-column>
      </el-table>
      <!-- 分页容器：统一分页器外观与对齐。 -->
      <div class="pagination-wrap">
        <!-- 分页器：total 来自接口；当前页与每页条数双向绑定 query，切换后通过 @change 重新请求。 -->
        <el-pagination background layout="total, sizes, prev, pager, next, jumper"
          :total="total" v-model:current-page="query.page" v-model:page-size="query.page_size"
          :page-sizes="[10, 20, 50, 100]" @change="getList" />
      </div>
    </el-card>

    <!-- 流程详情组件：v-model 控制显隐，父组件只传实例 ID，详情数据由组件内部按需请求。 -->
    <WorkflowDetail v-model="detailVisible" :instance-id="currentId" />
  </div>
</template>

<script setup>
// 引入 Vue 组合式 API：ref 管理状态，reactive 管理查询条件，onMounted 用于进入页面时加载模型选项和列表。
import { ref, reactive, onMounted } from 'vue'
// 引入 Element Plus 组件：ElMessage 用于操作成功提示，ElMessageBox 用于终止前的输入确认弹窗。
import { ElMessage, ElMessageBox } from 'element-plus'
// 引入图标：Search 查询、Refresh 重置、View 查看、CircleClose 终止。
import { Search, Refresh, View, CircleClose } from '@element-plus/icons-vue'
// 引入统一请求实例：自动携带 token，并统一处理后端响应。
import request from '@/utils/request'
// 引入流程详情公共组件：查看实例的审批轨迹与表单详情。
import WorkflowDetail from '@/components/workflow/WorkflowDetail.vue'

// 表格加载态：请求期间置 true 驱动遮罩，防止重复查询。
const loading = ref(false)
// 实例列表：保存接口返回的 data.list，驱动表格渲染。
const rows = ref([])
// 总记录数：保存接口返回的 data.total，供分页器与页头统计使用。
const total = ref(0)
// 流程模型下拉选项：进入页面时一次性拉取，供筛选条件使用。
const modelOptions = ref([])
// 流程详情弹层显隐：查看时置 true，组件关闭时通过 v-model 回写 false。
const detailVisible = ref(false)
// 当前查看的实例 ID：点击查看时从行数据的 id 写入，再传给详情组件。
const currentId = ref(0)
// 查询条件：分页参数 + 模型/状态/单据号；model_id、status 默认空串表示不过滤，作为 params 直接传给后端。
const query = reactive({ page: 1, page_size: 10, model_id: '', status: '', biz_key: '' })

// 将实例状态码映射为 el-tag 颜色：运行中黄、已完成绿、已驳回红、已终止灰，未知状态兜底灰色。
function statusType(status) {
  return { 0: 'warning', 1: 'success', 2: 'danger', 3: 'info' }[status] || 'info'
}
// 查询实例列表：按当前筛选与分页参数请求后端，成功后刷新行数据与总数。
async function getList() {
  // 请求开始先打开加载态，避免上一次请求未完成时用户重复操作。
  loading.value = true
  try {
    // 调用实例列表接口，query 中所有筛选条件都会作为查询串发送。
    const res = await request.get('/wf/instance/list', { params: query })
    // 列表数据写入 ref 必须通过 .value 才能触发视图更新。
    rows.value = res.data.list
    // 同步总条数供分页器使用。
    total.value = res.data.total
  } finally {
    // 无论成功或失败都关闭加载态，防止遮罩卡死。
    loading.value = false
  }
}
// 加载流程模型下拉选项：一次取 1000 条，满足常见模型数量，避免下拉分页带来的额外交互。
async function loadModels() {
  // 调用模型列表接口，固定取第一页的大页容量。
  const res = await request.get('/wf/model/list', { params: { page: 1, page_size: 1000 } })
  // 后端未返回 list 时用空数组兜底，保证下拉遍历安全。
  modelOptions.value = res.data.list || []
}
// 查询：先重置到第一页再请求，避免筛选后停留在超出范围的页码导致空列表。
function handleQuery() {
  // 条件变化后页码归 1。
  query.page = 1
  // 按新条件重新查询。
  getList()
}
// 重置：清空模型、状态、单据号并回到第一页，然后重新查询全量数据。
function resetQuery() {
  // 只覆盖筛选相关字段，保留 page_size 等分页设置。
  Object.assign(query, { page: 1, model_id: '', status: '', biz_key: '' })
  // 立即按清空后的条件重新查询。
  getList()
}
// 查看详情：记录实例 ID 并打开详情弹层。
function openDetail(row) {
  // 详情组件按实例 ID 加载，这里取实例自身的 id。
  currentId.value = row.id
  // 打开弹层，触发组件内部请求详情。
  detailVisible.value = true
}
// 终止实例：先弹窗要求填写终止原因，再调用后端终止接口，成功后提示并刷新列表。
async function terminate(row) {
  // prompt 返回用户输入值；取消时 Promise 会 reject，函数在此中断，不会继续调用接口。
  const { value } = await ElMessageBox.prompt('请输入终止原因', '终止流程', {
    // 预填默认原因，减少管理员重复输入。
    inputValue: '管理员终止',
    // 校验原因不能为空或全空格，避免产生无法追溯的终止记录。
    inputValidator: val => (val && val.trim() ? true : '请输入终止原因'),
    // 使用警告图标，提示这是不可逆操作。
    type: 'warning'
  })
  // 以实例 id 调用终止接口，并把终止原因作为备注提交，便于审计。
  await request.post(`/wf/instance/terminate/${row.id}`, { comment: value })
  // 终止成功后给出反馈。
  ElMessage.success('已终止')
  // 重新拉取列表，让该行状态更新为已终止。
  getList()
}

// 页面挂载：先加载模型下拉选项，再查询列表。
// 顺序执行是为了保证用户看到列表时筛选下拉已经可用，不会出现空选项的短暂状态。
onMounted(async () => {
  // 等待模型选项加载完成。
  await loadModels()
  // 加载第一页实例数据。
  getList()
})
</script>
