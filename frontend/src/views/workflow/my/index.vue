<template>
  <!-- 文件说明：工作流“我的流程”列表页，展示当前用户发起的流程实例，支持按状态筛选、发起新流程、查看详情与撤回运行中的流程。 -->
  <!-- 依赖后端接口 GET /wf/instance/my、POST /wf/instance/withdraw/{id}，以及公共组件 WorkflowDetail；发起按钮跳转流程中心。 -->
  <!-- 使用方：由后台动态菜单配置指向本组件；撤回按钮受 v-perm 权限指令控制，无权限用户看不到该入口。 -->
  <!-- 页面根容器：复用全局 app-container 内边距，保持后台页面留白一致。 -->
  <div class="app-container">
    <!-- 页头区域：标题与本人发起的实例总数。 -->
    <div class="page-header">
      <!-- 标题与副标题的排版容器。 -->
      <div class="page-title-wrap">
        <!-- 页面主标题。 -->
        <h2>我的流程</h2>
        <!-- 副标题：说明数据范围（本人发起），并实时展示总记录数。 -->
        <div class="sub">我发起的流程实例 · 共 {{ total }} 条记录</div>
      </div>
    </div>

    <!-- 查询卡片：集中放置筛选条件；shadow="never" 保持扁平外观。 -->
    <el-card shadow="never" class="search-card">
      <!-- 查询表单：:model 绑定 query；inline 横向排列；@submit.prevent 阻止回车触发原生表单提交。 -->
      <el-form :model="query" inline @submit.prevent>
        <!-- 流程状态筛选项：按实例状态过滤我的流程。 -->
        <el-form-item label="流程状态">
          <!-- 状态下拉：0-3 与后端状态枚举一致，clearable 支持清空条件。 -->
          <el-select v-model="query.status" placeholder="请选择" clearable style="width: 160px">
            <!-- 静态状态选项：与表格状态标签映射保持一致。 -->
            <el-option label="运行中" :value="0" />
            <el-option label="已完成" :value="1" />
            <el-option label="已驳回" :value="2" />
            <el-option label="已终止" :value="3" />
          </el-select>
        </el-form-item>
        <!-- 查询操作项：右侧放置查询与重置按钮。 -->
        <el-form-item class="search-actions">
          <!-- 查询按钮：调用 handleQuery，先回到第一页再请求，避免页码越界出现空列表。 -->
          <el-button type="primary" :icon="Search" @click="handleQuery">查询</el-button>
          <!-- 重置按钮：清空状态条件并回到第一页，然后重新查询。 -->
          <el-button :icon="Refresh" @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 列表卡片：承载发起入口与实例表格，shadow="never" 与查询卡片保持统一扁平风格。 -->
    <el-card shadow="never" class="table-card">
      <!-- 卡片头部插槽：只放右侧“发起流程”入口。 -->
      <template #header>
        <div class="card-header">
          <!-- 操作区：提供新建流程入口。 -->
          <div class="card-actions">
            <!-- 发起流程按钮：跳转到流程中心的发起页面，由用户选择流程模型并填写表单。 -->
            <el-button type="primary" :icon="Plus" @click="goStart">发起流程</el-button>
          </div>
        </div>
      </template>
      <!-- 实例表格：loading 控制请求遮罩，rows 为我的流程数据，stripe 斑马纹，empty-text 提供空态文案。 -->
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据">
        <!-- 序号列：表格自动生成行号，不依赖后端字段。 -->
        <el-table-column type="index" label="序号" width="70" align="center" />
        <!-- 业务单据号列：显示流程关联的业务主键，超长省略并悬浮显示全文。 -->
        <el-table-column label="业务单据号" prop="biz_key" min-width="170" show-overflow-tooltip />
        <!-- 流程名称列：显示流程模型名称，便于区分不同业务流程。 -->
        <el-table-column label="流程名称" prop="model_name" min-width="140" show-overflow-tooltip />
        <!-- 流程状态列：展示我发起的实例当前状态。 -->
        <el-table-column label="流程状态" width="100" align="center">
          <template #default="scope">
            <!-- 状态标签：颜色由 statusType 按状态码映射，文案使用后端 status_name。 -->
            <el-tag :type="statusType(scope.row.status)">{{ scope.row.status_name }}</el-tag>
          </template>
        </el-table-column>
        <!-- 当前节点列：显示实例当前停留的节点，便于发起人了解审批进度。 -->
        <el-table-column label="当前节点" prop="current_node" min-width="140" show-overflow-tooltip />
        <!-- 发起时间列：实例创建时间。 -->
        <el-table-column label="发起时间" prop="start_time" width="170" />
        <!-- 结束时间列：实例结束时间，运行中的实例通常为空。 -->
        <el-table-column label="结束时间" prop="end_time" width="170" />
        <!-- 操作列：固定右侧，保证横向滚动时操作入口始终可见。 -->
        <el-table-column label="操作" width="150" align="center" fixed="right">
          <template #default="scope">
            <!-- 查看按钮：打开流程实例详情，查看审批轨迹与表单数据。 -->
            <el-button link type="primary" :icon="View" @click="openDetail(scope.row)">查看</el-button>
            <!-- 撤回按钮：受 wf:instance:withdraw 权限控制；仅运行中（status===0）可点击，避免对已结束流程误操作。 -->
            <el-button v-perm="'wf:instance:withdraw'" link type="warning" :icon="RefreshLeft"
              :disabled="scope.row.status !== 0" @click="withdraw(scope.row)">撤回</el-button>
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
// 引入 Vue 组合式 API：ref 管理状态，reactive 管理查询条件，onMounted 首次加载，watch 监听详情弹层关闭。
import { ref, reactive, onMounted, watch } from 'vue'
// 引入路由钩子：用于“发起流程”按钮跳转到流程中心发起页。
import { useRouter } from 'vue-router'
// 引入 Element Plus 组件：ElMessage 操作成功提示，ElMessageBox 撤回前的二次确认。
import { ElMessage, ElMessageBox } from 'element-plus'
// 引入图标：Search 查询、Refresh 重置、Plus 发起、View 查看、RefreshLeft 撤回。
import { Search, Refresh, Plus, View, RefreshLeft } from '@element-plus/icons-vue'
// 引入统一请求实例：自动携带 token，并统一处理后端响应。
import request from '@/utils/request'
// 引入流程详情公共组件：查看我发起的实例详情。
import WorkflowDetail from '@/components/workflow/WorkflowDetail.vue'

// 当前路由实例：只用于 goStart 的编程式跳转。
const router = useRouter()
// 表格加载态：请求期间置 true 驱动遮罩，防止重复查询。
const loading = ref(false)
// 我的流程列表：保存接口返回的 data.list，驱动表格渲染。
const rows = ref([])
// 总记录数：保存接口返回的 data.total，供分页器与页头统计使用。
const total = ref(0)
// 流程详情弹层显隐：查看时置 true，组件关闭时通过 v-model 回写 false。
const detailVisible = ref(false)
// 当前查看的实例 ID：点击查看时从行数据的 id 写入，再传给详情组件。
const currentId = ref(0)
// 查询条件：分页参数 + 状态；status 默认空串表示不过滤，作为 params 传给后端。
const query = reactive({ page: 1, page_size: 10, status: '' })

// 将实例状态码映射为 el-tag 颜色：运行中黄、已完成绿、已驳回红、已终止灰，未知状态兜底灰色。
function statusType(status) {
  return { 0: 'warning', 1: 'success', 2: 'danger', 3: 'info' }[status] || 'info'
}
// 查询我的流程：按当前分页与状态条件请求后端，成功后刷新行数据与总数。
async function getList() {
  // 请求开始先打开加载态，避免上一次请求未完成时用户重复操作。
  loading.value = true
  try {
    // 调用我的流程接口，query 中的 page/page_size/status 作为查询串发送。
    const res = await request.get('/wf/instance/my', { params: query })
    // 列表数据写入 ref 必须通过 .value 才能触发视图更新。
    rows.value = res.data.list
    // 同步总条数供分页器使用。
    total.value = res.data.total
  } finally {
    // 无论成功或失败都关闭加载态，防止遮罩卡死。
    loading.value = false
  }
}
// 查询：先重置到第一页再请求，避免筛选后页码越界导致空列表。
function handleQuery() {
  // 条件变化后页码归 1。
  query.page = 1
  // 按新条件重新查询。
  getList()
}
// 重置：清空状态条件并回到第一页，然后重新查询。
function resetQuery() {
  // 只覆盖筛选与页码，保留 page_size 等分页设置。
  Object.assign(query, { page: 1, status: '' })
  // 立即按清空后的条件重新查询。
  getList()
}
// 发起流程：跳转到流程中心的发起页，由用户选择模型并填写业务表单。
function goStart() {
  // 使用路由 push 进入发起页；该路径需由路由/菜单配置提供，否则会落到 404。
  router.push('/workflow/center/start')
}
// 查看详情：记录实例 ID 并打开详情弹层。
function openDetail(row) {
  // 详情组件按实例 ID 加载，这里取实例自身的 id。
  currentId.value = row.id
  // 打开弹层，触发组件内部请求详情。
  detailVisible.value = true
}
// 撤回流程：先二次确认，再调用后端撤回接口；成功后提示并刷新列表。
async function withdraw(row) {
  // 确认框取消时 Promise 会 reject，函数在此中断，不会发起撤回请求。
  await ElMessageBox.confirm('确认撤回该流程吗？撤回后流程将终止。', '提示', { type: 'warning' })
  // 以实例 id 调用撤回接口。
  await request.post(`/wf/instance/withdraw/${row.id}`)
  // 撤回成功后给出反馈。
  ElMessage.success('撤回成功')
  // 重新拉取列表，让该行状态更新为已终止。
  getList()
}

// 监听详情弹层显隐：关闭后刷新列表，因为详情里可能发生了审批/状态变化，需要同步到表格。
watch(detailVisible, val => {
  // 只在关闭（val=false）时刷新，打开时无需请求。
  if (!val) getList()
})

// 页面挂载后立即加载第一页数据，保证进入页面就能看到列表而不必手动刷新。
onMounted(getList)
</script>
