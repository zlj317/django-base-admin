<template>
  <!-- 文件说明：请假示例流程查询页，只展示 model_key=leave 的流程实例，并按状态/业务单据号筛选。 -->
  <!-- 依赖后端接口 GET /wf/model/options（定位请假模型）、GET /wf/instance/list（实例列表），以及公共组件 WorkflowDetail。 -->
  <!-- 使用方：由后台动态菜单配置指向本组件，用户从“工作流-请假查询”菜单进入。 -->
  <!-- 页面根容器：复用全局 app-container 内边距，保持后台页面留白一致。 -->
  <div class="app-container">
    <!-- 页头区域：标题与请假实例总数。 -->
    <div class="page-header">
      <!-- 标题与副标题的排版容器。 -->
      <div class="page-title-wrap">
        <!-- 页面主标题。 -->
        <h2>请假查询</h2>
        <!-- 副标题：说明数据范围是 OA 请假流程实例，并实时展示总记录数。 -->
        <div class="sub">OA 请假流程实例 · 共 {{ total }} 条记录</div>
      </div>
    </div>

    <!-- 查询卡片：集中放置筛选条件；shadow="never" 保持扁平外观。 -->
    <el-card shadow="never" class="search-card">
      <!-- 查询表单：:model 绑定 query；inline 横向排列；@submit.prevent 阻止回车触发原生表单提交。 -->
      <el-form :model="query" inline @submit.prevent>
        <!-- 流程状态筛选项：按实例状态过滤请假记录。 -->
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
        <!-- 业务单据号筛选项：按请假单号检索。 -->
        <el-form-item label="业务单据号">
          <!-- 单据号输入框：回车触发查询，clearable 便于快速清空。 -->
          <el-input v-model="query.biz_key" placeholder="请输入业务单据号" clearable style="width: 180px" @keyup.enter="handleQuery" />
        </el-form-item>
        <!-- 查询操作项：右侧放置查询与重置按钮。 -->
        <el-form-item class="search-actions">
          <!-- 查询按钮：调用 handleQuery，先回到第一页再请求，避免页码越界出现空列表。 -->
          <el-button type="primary" :icon="Search" @click="handleQuery">查询</el-button>
          <!-- 重置按钮：清空状态和单据号并回到第一页，然后重新查询。 -->
          <el-button :icon="Refresh" @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 列表卡片：承载请假实例表格，shadow="never" 与其他列表页保持统一扁平风格。 -->
    <el-card shadow="never" class="table-card">
      <!-- 请假表格：loading 控制请求遮罩，rows 为实例数据，stripe 斑马纹，empty-text 提供空态文案。 -->
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无请假流程数据">
        <!-- 序号列：表格自动生成行号，不依赖后端字段。 -->
        <el-table-column type="index" label="序号" width="70" align="center" />
        <!-- 业务单据号列：显示请假流程对应的业务单号，便于与 OA 单据核对。 -->
        <el-table-column label="业务单据号" prop="biz_key" min-width="160" show-overflow-tooltip />
        <!-- 请假类型列：从流程实例的表单快照 form_data_obj 中读取，缺失时显示 '-' 避免空白。 -->
        <el-table-column label="请假类型" min-width="100" align="center">
          <template #default="scope">{{ scope.row.form_data_obj?.leaveType || '-' }}</template>
        </el-table-column>
        <!-- 开始日期列：同样读取表单快照，用可选链防止 form_data_obj 为空时报错。 -->
        <el-table-column label="开始日期" min-width="120" align="center">
          <template #default="scope">{{ scope.row.form_data_obj?.startDate || '-' }}</template>
        </el-table-column>
        <!-- 结束日期列：读取表单快照中的结束日期，缺失时显示占位符。 -->
        <el-table-column label="结束日期" min-width="120" align="center">
          <template #default="scope">{{ scope.row.form_data_obj?.endDate || '-' }}</template>
        </el-table-column>
        <!-- 请假天数列：使用 ?? 而非 ||，确保 0 天也能正常显示，不会被误判为空值。 -->
        <el-table-column label="请假天数" width="100" align="center">
          <template #default="scope">{{ scope.row.form_data_obj?.leaveDays ?? '-' }}</template>
        </el-table-column>
        <!-- 请假事由列：读取表单快照中的事由，超长省略并在悬浮时展示全文。 -->
        <el-table-column label="请假事由" min-width="180" show-overflow-tooltip>
          <template #default="scope">{{ scope.row.form_data_obj?.reason || '-' }}</template>
        </el-table-column>
        <!-- 发起人列：显示请假流程发起人姓名，固定宽度居中。 -->
        <el-table-column label="发起人" prop="start_user_name" width="100" align="center" />
        <!-- 流程状态列：展示请假实例当前状态。 -->
        <el-table-column label="流程状态" width="100" align="center">
          <template #default="scope">
            <!-- 状态标签：颜色由 statusType 按状态码映射，文案使用后端 status_name。 -->
            <el-tag :type="statusType(scope.row.status)">{{ scope.row.status_name }}</el-tag>
          </template>
        </el-table-column>
        <!-- 申请时间列：请假流程发起时间。 -->
        <el-table-column label="申请时间" prop="start_time" width="170" />
        <!-- 操作列：固定右侧，保证横向滚动时仍可查看详情。 -->
        <el-table-column label="操作" width="100" align="center" fixed="right">
          <template #default="scope">
            <!-- 查看按钮：打开请假流程实例详情，查看审批轨迹与完整表单。 -->
            <el-button link type="primary" :icon="View" @click="openDetail(scope.row)">查看</el-button>
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
    <WorkflowDetail v-model="detailVisible" :instance-id="currentInstanceId" />
  </div>
</template>

<script setup>
// 引入 Vue 组合式 API：ref 管理状态，reactive 管理查询条件，onMounted 用于进入页面时先定位请假模型再加载列表。
import { ref, reactive, onMounted } from 'vue'
// 引入图标：Search 查询、Refresh 重置、View 查看。
import { Search, Refresh, View } from '@element-plus/icons-vue'
// 引入统一请求实例：自动携带 token，并统一处理后端响应结构。
import request from '@/utils/request'
// 引入流程详情公共组件：查看请假实例的审批轨迹与完整表单。
import WorkflowDetail from '@/components/workflow/WorkflowDetail.vue'

// 表格加载态：请求期间置 true 驱动遮罩，防止重复查询。
const loading = ref(false)
// 请假实例列表：保存接口返回的 data.list，驱动表格渲染。
const rows = ref([])
// 总记录数：保存接口返回的 data.total，供分页器与页头统计使用。
const total = ref(0)
// 请假流程模型 ID：页面不提供模型筛选，需先按固定 model_key 定位；默认 0 表示尚未定位到。
const modelId = ref(0)
// 查询条件：分页参数 + 状态 + 业务单据号；status 默认空串表示不过滤，作为 params 传给后端。
const query = reactive({ page: 1, page_size: 10, status: '', biz_key: '' })
// 流程详情弹层显隐：查看时置 true，组件关闭时通过 v-model 回写 false。
const detailVisible = ref(false)
// 当前查看的实例 ID：点击查看时从行数据的 id 写入，再传给详情组件。
const currentInstanceId = ref(0)

// 将实例状态码映射为 el-tag 颜色：运行中黄、已完成绿、已驳回红、已终止灰，未知状态兜底灰色。
function statusType(status) {
  return { 0: 'warning', 1: 'success', 2: 'danger', 3: 'info' }[status] || 'info'
}
// 请假页只展示请假流程实例，因此需要先从模型选项中解析出 leave 模型的 id。
async function resolveModel() {
  // 通过模型选项定位请假流程（model_key = leave）
  // 调用轻量的模型选项接口，避免为一次筛选拉取完整分页数据。
  const res = await request.get('/wf/model/options')
  // 在选项列表中按固定标识 leave 查找，避免把模型 id 硬编码在前端。
  const target = (res.data || []).find(item => item.model_key === 'leave')
  // 找到则记录模型 id；找不到保持 0，后续查询会得到空结果（见疑似问题清单）。
  modelId.value = target ? target.id : 0
}
// 查询请假实例：把筛选条件与解析出的模型 id 合并后传给通用实例列表接口，保证只返回请假流程。
async function getList() {
  // 请求开始先打开加载态，避免上一次请求未完成时用户重复操作。
  loading.value = true
  try {
    // 展开 query 并追加 model_id，避免直接修改响应式查询对象。
    const params = { ...query, model_id: modelId.value }
    // 调用通用实例列表接口，用 model_id 限定请假模型。
    const res = await request.get('/wf/instance/list', { params })
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
// 重置：清空状态与单据号并回到第一页，然后重新查询。
function resetQuery() {
  // 只覆盖筛选相关字段，保留 page_size 等分页设置。
  Object.assign(query, { page: 1, status: '', biz_key: '' })
  // 立即按清空后的条件重新查询。
  getList()
}
// 查看详情：记录实例 ID 并打开详情弹层。
function openDetail(row) {
  // 详情组件按实例 ID 加载，这里取实例自身的 id。
  currentInstanceId.value = row.id
  // 打开弹层，触发组件内部请求详情。
  detailVisible.value = true
}

// 页面挂载：先解析请假模型 id，再查询列表。
// 顺序执行是因为 getList 依赖 modelId，若并行执行可能带着默认 0 请求而拿到空数据。
onMounted(async () => {
  // 等待模型定位完成。
  await resolveModel()
  // 加载第一页请假实例数据。
  getList()
})
</script>
