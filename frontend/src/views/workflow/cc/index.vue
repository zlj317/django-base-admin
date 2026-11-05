<template>
  <!-- 文件说明：工作流“抄送我的”列表页，展示抄送给当前登录用户的流程记录，支持查看流程详情并自动/手动标记已读。 -->
  <!-- 依赖后端接口 GET /wf/cc/mine（分页列表）与 POST /wf/cc/read/{id}（标记已读），以及公共组件 WorkflowDetail。 -->
  <!-- 使用方：由后台动态菜单配置指向本组件，用户从“工作流-抄送我的”菜单进入。 -->
  <!-- 页面根容器：沿用全局 app-container 内边距样式，统一后台页面留白。 -->
  <div class="app-container">
    <!-- 页头区域：标题加记录总数，总数来自列表接口返回，让用户快速了解数据量。 -->
    <div class="page-header">
      <!-- 标题与副标题的排版容器。 -->
      <div class="page-title-wrap">
        <!-- 页面主标题。 -->
        <h2>抄送我的</h2>
        <!-- 副标题：说明数据范围，并实时显示总记录数。 -->
        <div class="sub">抄送给我的流程通知 · 共 {{ total }} 条记录</div>
      </div>
    </div>

    <!-- 表格卡片：承载工具栏与列表；shadow="never" 去掉阴影，与其他列表页保持一致的扁平风格。 -->
    <el-card shadow="never" class="table-card">
      <!-- 卡片头部插槽：只放右侧操作按钮。 -->
      <template #header>
        <div class="card-header">
          <!-- 操作区：目前仅提供刷新，用于重新拉取最新抄送数据。 -->
          <div class="card-actions">
            <!-- 刷新按钮：点击调用 getList，按当前分页参数重新请求列表。 -->
            <el-button :icon="Refresh" @click="getList">刷新</el-button>
          </div>
        </div>
      </template>
      <!-- 数据表格：loading 控制请求遮罩，rows 为列表数据，stripe 开启斑马纹，empty-text 提供空态文案。 -->
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无抄送记录">
        <!-- 序号列：由表格自动生成连续行号，不依赖后端字段。 -->
        <el-table-column type="index" label="序号" width="70" align="center" />
        <!-- 流程名称列：展示流程模型名称；超长时省略并在悬浮时显示完整内容。 -->
        <el-table-column label="流程名称" prop="model_name" min-width="140" show-overflow-tooltip />
        <!-- 发起人列：展示流程发起人姓名，固定宽度居中以保证列对齐。 -->
        <el-table-column label="发起人" prop="start_user_name" width="110" align="center" />
        <!-- 抄送节点列：展示抄送发生的节点标识，超长内容用悬浮提示展示。 -->
        <el-table-column label="抄送节点" prop="node_id" min-width="140" show-overflow-tooltip>
          <!-- 自定义单元格：node_id 为空时显示占位符，避免出现空白单元格。 -->
          <template #default="scope">{{ scope.row.node_id || '-' }}</template>
        </el-table-column>
        <!-- 流程状态列：展示抄送记录所属流程实例的状态（运行中/已完成/已驳回/已终止）。 -->
        <el-table-column label="流程状态" width="100" align="center">
          <template #default="scope">
            <!-- 状态标签：颜色由 instanceTagType 按状态码映射，文案由 instanceStatusName 转换，未知状态兜底为灰色 '-'。 -->
            <el-tag :type="instanceTagType(scope.row.instance_status)">
              {{ instanceStatusName(scope.row.instance_status) }}
            </el-tag>
          </template>
        </el-table-column>
        <!-- 阅读状态列：区分用户是否已读该条抄送。 -->
        <el-table-column label="阅读状态" width="100" align="center">
          <template #default="scope">
            <!-- 阅读状态标签：status===1 为已读（灰色），其余为未读（橙色），文案直接取后端 status_name。 -->
            <el-tag :type="scope.row.status === 1 ? 'info' : 'warning'">{{ scope.row.status_name }}</el-tag>
          </template>
        </el-table-column>
        <!-- 抄送时间列：直接展示后端返回的 create_time 字符串。 -->
        <el-table-column label="抄送时间" prop="create_time" width="170" />
        <!-- 操作列：固定在最右侧，保证表格横向滚动时操作入口始终可见。 -->
        <el-table-column label="操作" width="170" align="center" fixed="right">
          <template #default="scope">
            <!-- 查看按钮：打开流程详情弹层；若该条未读，openDetail 内部会顺带标记已读。 -->
            <el-button link type="primary" :icon="View" @click="openDetail(scope.row)">查看</el-button>
            <!-- 标记已读按钮：仅未读记录显示，避免对已读数据重复操作；点击后调用接口并就地更新行状态。 -->
            <el-button v-if="scope.row.status !== 1" link type="success" :icon="Check" @click="markRead(scope.row)">标记已读</el-button>
          </template>
        </el-table-column>
      </el-table>
      <!-- 分页容器：统一分页器的布局与对齐样式。 -->
      <div class="pagination-wrap">
        <!-- 分页器：total 来自接口；当前页与每页条数双向绑定 query，用户切换页码/条数后触发 change 重新查询。 -->
        <el-pagination background layout="total, sizes, prev, pager, next, jumper"
          :total="total" v-model:current-page="query.page" v-model:page-size="query.page_size"
          :page-sizes="[10, 20, 50, 100]" @change="getList" />
      </div>
    </el-card>

    <!-- 流程详情组件：v-model 控制显隐，父组件只传实例 ID，详情数据由组件内部按需请求。 -->
    <WorkflowDetail v-model="detailVisible" :instance-id="currentInstanceId" />
  </div>
</template>

<script setup>
// 引入 Vue 组合式 API：ref 管理基本类型状态，reactive 管理查询参数，onMounted 为挂载生命周期钩子（本文件未调用，见文末说明）。
import { ref, reactive, onMounted } from 'vue'
// 引入 Element Plus 消息提示：手动标记已读成功后给出轻提示。
import { ElMessage } from 'element-plus'
// 引入图标：Refresh 用于刷新按钮、View 用于查看、Check 用于标记已读。
import { Refresh, View, Check } from '@element-plus/icons-vue'
// 引入统一请求实例：自动携带 token，并把后端 { code, msg, data } 响应统一处理。
import request from '@/utils/request'
// 引入流程详情公共组件：查看抄送记录对应的流程实例审批详情。
import WorkflowDetail from '@/components/workflow/WorkflowDetail.vue'

// 表格加载态：请求期间置 true 驱动 v-loading 遮罩，防止重复点击。
const loading = ref(false)
// 抄送记录列表：保存接口返回的 data.list，驱动表格渲染。
const rows = ref([])
// 总记录数：保存接口返回的 data.total，供分页器和页头统计使用。
const total = ref(0)
// 列表查询参数：页码与每页条数，与分页器双向绑定，并作为 params 直接传给后端。
const query = reactive({ page: 1, page_size: 10 })
// 流程详情弹层显隐：点击查看置 true，由详情组件通过 v-model 关闭时置 false。
const detailVisible = ref(false)
// 当前查看的流程实例 ID：点击查看时取行数据的 instance_id 写入，再传给详情组件。
const currentInstanceId = ref(0)

// 流程实例状态码到中文文案的映射：0 运行中、1 已完成、2 已驳回、3 已终止，与后端枚举保持一致。
const instanceStatusMap = { 0: '运行中', 1: '已完成', 2: '已驳回', 3: '已终止' }
// 将状态码转换为中文文案：未知状态返回 '-'，避免页面显示 undefined。
function instanceStatusName(status) {
  return instanceStatusMap[status] || '-'
}
// 将状态码转换为 el-tag 颜色类型：进行中橙色提醒、完成绿色、驳回红色、终止灰色，未知兜底灰色。
function instanceTagType(status) {
  return { 0: 'warning', 1: 'success', 2: 'danger', 3: 'info' }[status] || 'info'
}
// 查询抄送列表：按当前分页参数请求后端，成功后同时刷新行数据与总数。
async function getList() {
  // 请求前先打开加载态，避免上一次请求未完成时用户重复操作。
  loading.value = true
  try {
    // 调用抄送我的列表接口，query 中的 page/page_size 会作为查询串发送。
    const res = await request.get('/wf/cc/mine', { params: query })
    // 列表数据写入 ref 必须通过 .value，才能触发视图更新。
    rows.value = res.data.list
    // 同步总条数，供分页器和页头统计使用。
    total.value = res.data.total
  } finally {
    // 无论成功或失败都关闭加载态，防止遮罩卡死。
    loading.value = false
  }
}
// 查看详情：记录实例 ID 并打开详情弹层；若该条抄送未读，则静默补标记已读。
function openDetail(row) {
  // 详情组件按实例 ID 加载，因此取 instance_id 而非抄送记录自身的 id。
  currentInstanceId.value = row.instance_id
  // 打开详情弹层。
  detailVisible.value = true
  // 未读时才补标记；silent=true 表示不弹提示，避免打断用户查看详情。
  if (row.status !== 1) markRead(row, true)
}
// 标记已读：调用后端接口后同步更新当前行数据，避免整表重新请求。
// silent 用于区分手动点击（需要成功提示）与打开详情时自动标记（保持安静）。
async function markRead(row, silent = false) {
  // 以抄送记录 id 调用标记已读接口。
  await request.post(`/wf/cc/read/${row.id}`)
  // 手动操作时给出成功提示；自动标记时不提示。
  if (!silent) ElMessage.success('已标记为已读')
  // 直接修改行对象状态码，让“标记已读”按钮立即消失、阅读状态变为已读。
  row.status = 1
  // 同步更新展示文案，避免只改状态码导致标签文字仍显示“未读”。
  row.status_name = '已读'
}
</script>
