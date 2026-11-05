<template>
  <!-- 文件说明：工作流“已办任务”列表页，展示当前用户已审批过的任务，支持按任务查看对应流程详情。 -->
  <!-- 依赖后端接口 GET /wf/task/done（分页查询已办任务）与公共组件 WorkflowDetail；无写操作接口。 -->
  <!-- 使用方：由后台动态菜单配置指向本组件，用户从“工作流-已办任务”菜单进入。 -->
  <!-- 页面根容器：复用全局 app-container 内边距，保持后台页面统一的留白。 -->
  <div class="app-container">
    <!-- 页头区域：标题与记录总数，总数来自列表接口返回。 -->
    <div class="page-header">
      <!-- 标题与副标题的排版容器。 -->
      <div class="page-title-wrap">
        <!-- 页面主标题。 -->
        <h2>已办任务</h2>
        <!-- 副标题：说明数据范围（本人已处理），并实时展示总记录数。 -->
        <div class="sub">我已处理过的审批任务 · 共 {{ total }} 条记录</div>
      </div>
    </div>

    <!-- 表格卡片：承载刷新工具栏和列表；shadow="never" 保持无阴影的扁平风格。 -->
    <el-card shadow="never" class="table-card">
      <!-- 卡片头部插槽：只放右侧操作按钮。 -->
      <template #header>
        <div class="card-header">
          <!-- 操作区：目前只提供刷新。 -->
          <div class="card-actions">
            <!-- 刷新按钮：按当前分页参数重新请求已办任务列表。 -->
            <el-button :icon="Refresh" @click="getList">刷新</el-button>
          </div>
        </div>
      </template>
      <!-- 数据表格：loading 控制请求遮罩，rows 为任务数据，stripe 斑马纹便于逐行阅读，empty-text 提供空态文案。 -->
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无已办任务">
        <!-- 序号列：表格自动生成行号，不依赖后端字段。 -->
        <el-table-column type="index" label="序号" width="70" align="center" />
        <!-- 任务节点列：显示已办任务所在的流程节点名称，超长省略并悬浮显示全文。 -->
        <el-table-column label="任务节点" prop="task_name" min-width="140" show-overflow-tooltip />
        <!-- 流程名称列：显示该任务所属的流程模型名称。 -->
        <el-table-column label="流程名称" prop="model_name" min-width="130" show-overflow-tooltip />
        <!-- 业务单据号列：对应流程实例的业务主键，便于与业务系统单据核对。 -->
        <el-table-column label="业务单据号" prop="instance_key" min-width="160" show-overflow-tooltip />
        <!-- 发起人列：显示流程发起人姓名，固定宽度居中。 -->
        <el-table-column label="发起人" prop="start_user_name" width="100" align="center" />
        <!-- 审批方式列：显示后端翻译后的审批方式名称（如或签/会签等）。 -->
        <el-table-column label="审批方式" prop="approve_mode_name" width="100" align="center" />
        <!-- 处理结果列：展示本次审批任务的处理结果。 -->
        <el-table-column label="处理结果" width="100" align="center">
          <template #default="scope">
            <!-- 结果标签：颜色由 taskTagType 按状态码映射，文案由后端 status_name 提供，避免前端重复维护枚举文案。 -->
            <el-tag :type="taskTagType(scope.row.status)">{{ scope.row.status_name }}</el-tag>
          </template>
        </el-table-column>
        <!-- 生成时间列：任务创建（生成待办）的时间。 -->
        <el-table-column label="生成时间" prop="start_time" width="170" />
        <!-- 完成时间列：任务处理完成的时间。 -->
        <el-table-column label="完成时间" prop="end_time" width="170" />
        <!-- 操作列：固定右侧，保证横向滚动时仍可点击。 -->
        <el-table-column label="操作" width="100" align="center" fixed="right">
          <template #default="scope">
            <!-- 查看按钮：打开该任务所属流程实例的详情，便于回溯审批过程。 -->
            <el-button link type="primary" :icon="View" @click="openDetail(scope.row)">查看</el-button>
          </template>
        </el-table-column>
      </el-table>
      <!-- 分页容器：统一分页器外观与对齐。 -->
      <div class="pagination-wrap">
        <!-- 分页器：total 来自接口；当前页与每页条数双向绑定 query，切换后通过 @change 重新请求列表。 -->
        <el-pagination background layout="total, sizes, prev, pager, next, jumper"
          :total="total" v-model:current-page="query.page" v-model:page-size="query.page_size"
          :page-sizes="[10, 20, 50, 100]" @change="getList" />
      </div>
    </el-card>

    <!-- 流程详情组件：v-model 控制显隐，父组件传入实例 ID，由组件内部请求详情。 -->
    <WorkflowDetail v-model="detailVisible" :instance-id="currentInstanceId" />
  </div>
</template>

<script setup>
// 引入 Vue 组合式 API：ref 管理基本状态，reactive 管理查询参数，onMounted 用于进入页面时首次加载列表。
import { ref, reactive, onMounted } from 'vue'
// 引入图标：Refresh 用于刷新按钮，View 用于查看按钮。
import { Refresh, View } from '@element-plus/icons-vue'
// 引入统一请求实例：自动携带 token，并统一处理后端响应结构。
import request from '@/utils/request'
// 引入流程详情公共组件：查看已办任务对应的流程实例详情。
import WorkflowDetail from '@/components/workflow/WorkflowDetail.vue'

// 表格加载态：请求期间置 true 驱动遮罩，防止重复查询。
const loading = ref(false)
// 已办任务列表：保存接口返回的 data.list，驱动表格渲染。
const rows = ref([])
// 总记录数：保存接口返回的 data.total，供分页器和页头统计使用。
const total = ref(0)
// 列表查询参数：页码与每页条数，与分页器双向绑定，并作为 params 传给后端。
const query = reactive({ page: 1, page_size: 10 })
// 流程详情弹层显隐：查看时置 true，详情组件关闭时通过 v-model 回写 false。
const detailVisible = ref(false)
// 当前查看的流程实例 ID：点击查看时从行数据的 instance_id 写入，再传给详情组件。
const currentInstanceId = ref(0)

// 将任务状态码映射为 el-tag 颜色：0 黄、1 绿、2 灰、3 蓝、4 红，未知状态兜底灰色。
// 只负责颜色，具体状态文案由后端 status_name 提供，避免前端与后端枚举文案重复维护。
function taskTagType(status) {
  return { 0: 'warning', 1: 'success', 2: 'info', 3: 'primary', 4: 'danger' }[status] || 'info'
}
// 查询已办任务列表：按当前分页参数请求后端，成功后刷新行数据与总数。
async function getList() {
  // 请求开始先打开加载态，避免用户在上一次请求未完成时重复操作。
  loading.value = true
  try {
    // 调用已办任务接口，query 中的 page/page_size 作为查询串发送。
    const res = await request.get('/wf/task/done', { params: query })
    // 列表数据写入 ref 必须通过 .value 才能触发视图更新。
    rows.value = res.data.list
    // 同步总条数供分页器使用。
    total.value = res.data.total
  } finally {
    // 无论成功或失败都关闭加载态，防止遮罩卡死。
    loading.value = false
  }
}
// 查看详情：记录任务所属的流程实例 ID，并打开详情弹层。
function openDetail(row) {
  // 详情组件按实例 ID 加载，因此取 instance_id 而不是任务 ID。
  currentInstanceId.value = row.instance_id
  // 打开弹层，触发组件内部请求详情。
  detailVisible.value = true
}

// 页面挂载后立即加载第一页数据，保证进入页面就能看到列表而不必手动刷新。
onMounted(getList)
</script>
