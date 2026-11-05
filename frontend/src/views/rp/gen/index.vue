<!--
  文件说明：报表生成记录（RP Gen）只读列表页。
  职责：查询报表模板的历史生成记录（可执行/定时生成），查看单条记录生成的报表结果。
        本页不提供新增、编辑、删除，生成动作由报表模板页（views/rp/template）触发。
  关键字段：gen_status 0=生成中、1=成功、2=失败；gen_type manual=手动触发、schedule=定时任务触发；
            file_id 为生成产物文件 ID（成功时才有值）；error_msg 为失败原因；cost_time 为耗时毫秒数。
  依赖：Element Plus、@element-plus/icons-vue、@/utils/request 统一请求封装、
        @/components/report/ReportPreview.vue（低代码报表渲染组件）。
  被谁使用：rp 模块菜单路由加载本页，供运维/业务回溯生成结果与排查失败原因。
-->
<template>
  <!-- 页面根容器：复用全局 app-container 样式，统一页面内边距与背景 -->
  <div class="app-container">
    <!-- 页头：标题与总数 -->
    <div class="page-header">
      <!-- 标题包裹层：约束标题与副标题的垂直排布 -->
      <div class="page-title-wrap">
        <!-- 页面主标题 -->
        <h2>生成记录</h2>
        <!-- 副标题：标注“只读”，明确本页没有增删操作；total 为列表接口返回总条数 -->
        <div class="sub">只读 · 共 {{ total }} 条</div>
      </div>
    </div>
    <!-- 查询卡片：shadow="never" 与下方表格卡片保持扁平统一的视觉 -->
    <el-card shadow="never" class="search-card">
      <!-- 查询表单：inline 行内布局；@submit.prevent 阻止原生提交，避免回车刷新页面 -->
      <el-form :model="query" inline @submit.prevent>
        <!-- 查询项：按模板名称模糊搜索生成记录 -->
        <el-form-item label="模板名称">
          <!-- 双向绑定 query.template_name；clearable 一键清空；回车即查询 -->
          <el-input v-model="query.template_name" placeholder="请输入模板名称" clearable style="width: 180px" @keyup.enter="handleSearch" />
        </el-form-item>
        <!-- 查询项：按生成状态筛选 -->
        <el-form-item label="生成状态">
          <!-- 数值枚举与后端一致：0 生成中、1 成功、2 失败；clearable 清空即查全部 -->
          <el-select v-model="query.gen_status" placeholder="全部" clearable style="width: 130px">
            <el-option label="生成中" :value="0" />
            <el-option label="成功" :value="1" />
            <el-option label="失败" :value="2" />
          </el-select>
        </el-form-item>
        <!-- 无标签操作项：查询与重置按钮 -->
        <el-form-item>
          <!-- 查询：handleSearch 会先重置页码再请求 -->
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <!-- 重置：恢复默认查询条件并加载第一页 -->
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 列表卡片：只读展示生成记录，无批量操作头部 -->
    <el-card shadow="never" class="table-card">
      <!-- 数据表格：v-loading 请求遮罩；stripe 斑马纹；空数据文案 -->
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据">
        <!-- 序号列：type="index" 自动生成当前页行号 -->
        <el-table-column type="index" label="序号" width="70" align="center" />
        <!-- 模板ID：关联 rp 模板表的记录主键，便于与技术侧核对 -->
        <el-table-column label="模板ID" prop="template_id" width="90" />
        <!-- 模板名称：冗余存储的模板名，模板改名后历史记录仍保留当时的名称 -->
        <el-table-column label="模板名称" prop="template_name" min-width="160" show-overflow-tooltip />
        <!-- 生成类型列：区分手动触发与定时任务触发 -->
        <el-table-column label="生成类型" prop="gen_type" width="100">
          <template #default="{ row }">
            <!-- manual：用户在模板列表点击“生成报表”触发，默认灰色标签 -->
            <el-tag v-if="row.gen_type==='manual'" size="small">手动</el-tag>
            <!-- schedule：后台定时任务触发，用 warning 色以示与手动生成的区别 -->
            <el-tag v-else-if="row.gen_type==='schedule'" size="small" type="warning">定时</el-tag>
            <!-- 兜底：未知类型直接显示原值，便于发现后端新枚举 -->
            <span v-else>{{ row.gen_type }}</span>
          </template>
        </el-table-column>
        <!-- 状态列：0 生成中（warning）/ 1 成功（success）/ 2 失败（danger） -->
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <!-- 生成中：任务尚未结束，可使用警告色提示用户等待或刷新 -->
            <el-tag v-if="row.gen_status===0" size="small" type="warning">生成中</el-tag>
            <!-- 成功：生成产物可用，对应 file_id 应有值 -->
            <el-tag v-else-if="row.gen_status===1" size="small" type="success">成功</el-tag>
            <!-- 失败：结合 error_msg 排查原因 -->
            <el-tag v-else-if="row.gen_status===2" size="small" type="danger">失败</el-tag>
            <!-- 兜底：未知状态直接显示原值 -->
            <span v-else>{{ row.gen_status }}</span>
          </template>
        </el-table-column>
        <!-- 文件ID：生成成功后产物文件的标识；为空时显示 '-' 保持表格整齐 -->
        <el-table-column label="文件ID" prop="file_id" min-width="140" show-overflow-tooltip>
          <template #default="{ row }">{{ row.file_id || '-' }}</template>
        </el-table-column>
        <!-- 错误信息：失败原因（如数据源连接失败、SQL 报错），为空时显示 '-' -->
        <el-table-column label="错误信息" prop="error_msg" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">{{ row.error_msg || '-' }}</template>
        </el-table-column>
        <!-- 耗时：生成任务耗时，单位毫秒，用于性能观察 -->
        <el-table-column label="耗时(ms)" prop="cost_time" width="100" />
        <!-- 生成用户ID：定时任务一般无用户，手动生成时为触发者 ID -->
        <el-table-column label="生成用户ID" prop="gen_user_id" width="110" />
        <!-- 生成时间：后端格式化的时间字符串，直接展示 -->
        <el-table-column label="生成时间" prop="gen_time" width="170" />
        <!-- 操作列：固定右侧，横向滚动时仍可见；op-col 复用全局操作列样式 -->
        <el-table-column label="操作" width="110" fixed="right" class-name="op-col">
          <template #default="{ row }">
            <!-- 查看报表：拉取该次生成结果并在弹窗中渲染；仅查看，不重新生成 -->
            <el-button link type="warning" @click="handlePreview(row)">查看报表</el-button>
          </template>
        </el-table-column>
      </el-table>
      <!-- 分页容器：统一右对齐版式 -->
      <div class="pagination-wrap">
        <!-- 分页器：current-page / page-size 双向绑定 query；@change 页码或条数变化后重新请求 -->
        <el-pagination background layout="total, sizes, prev, pager, next, jumper"
          :total="total" v-model:current-page="query.page" v-model:page-size="query.page_size"
          :page-sizes="[10, 20, 50, 100]" @change="fetchList" />
      </div>
    </el-card>

    <!-- 预览弹窗：标题动态带模板名；top=4vh 让弹窗靠上以留出更多纵向空间；
         destroy-on-close 关闭即销毁报表组件，避免上一次渲染残留 -->
    <el-dialog :title="previewTitle" v-model="previewVisible" width="980px" top="4vh" destroy-on-close>
      <!-- 预览容器：previewLoading 控制遮罩，接口未返回前保持占位高度 -->
      <div v-loading="previewLoading" class="preview-body">
        <!-- 报表渲染组件：previewData 为空时不渲染，避免传入空 payload 导致组件内部报错；
             数据由 /rp/gen/preview/{id} 返回的低代码报表结构驱动 -->
        <ReportPreview v-if="previewData" :payload="previewData" />
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
// 组合式 API：顶层声明的变量与函数自动暴露给模板，无需显式 return
import { ref, reactive, onMounted } from 'vue'
// 图标：查询、重置按钮
import { Search, Refresh } from '@element-plus/icons-vue'
// 统一请求实例：已封装 baseURL、Token 与错误提示
import request from '@/utils/request'
// 低代码报表渲染组件：接收后端返回的报表 payload，负责表格/图表等内容的展示
import ReportPreview from '@/components/report/ReportPreview.vue'

// 表格 loading：请求期间遮罩
const loading = ref(false)
// 当前页生成记录
const rows = ref([])
// 总条数，驱动分页器与页头统计
const total = ref(0)
// 预览弹窗显隐
const previewVisible = ref(false)
// 预览接口 loading：控制预览区域遮罩，与列表 loading 相互独立
const previewLoading = ref(false)
// 预览数据（后端返回的报表结构）；null 时模板中 v-if 不渲染报表组件
const previewData = ref(null)
// 预览弹窗标题，动态拼接当前记录的模板名
const previewTitle = ref('报表预览')

// 查询默认值：gen_status 为 null 表示不按状态筛选；分页默认第 1 页、每页 10 条
const query_orig = { page: 1, page_size: 10, template_name: '', gen_status: null }
// reactive 包裹以支持模板双向绑定，分页组件改动可直接同步回 query
const query = reactive({ ...query_orig })

// 拉取生成记录列表：只读查询，无增删改
async function fetchList() {
  loading.value = true
  try {
    // GET /rp/gen/list，params 携带分页与筛选条件
    const res = await request.get('/rp/gen/list', { params: query })
    // 兜底空数组，避免接口异常返回 null 时表格报错
    rows.value = res.data.list || []
    // 兜底 0，避免分页器出现 NaN
    total.value = res.data.total || 0
  } finally { loading.value = false }
}
// 查询：先重置页码为 1，避免停留在越界页
function handleSearch() { query.page = 1; fetchList() }
// 重置：还原默认查询条件后重新查询
function handleReset() { Object.assign(query, query_orig); handleSearch() }

// 查看报表：按生成记录 id 拉取该次生成的报表 payload，并交给预览组件渲染
async function handlePreview(row) {
  // 标题带上模板名，便于区分多条记录的预览
  previewTitle.value = `报表预览 · ${row.template_name || ''}`
  // 先清空旧数据，避免弹窗打开瞬间闪现上一次的报表内容
  previewData.value = null
  // 先打开弹窗并开启 loading，让用户立即看到反馈
  previewVisible.value = true
  previewLoading.value = true
  try {
    // GET /rp/gen/preview/{id}：返回该次生成结果的报表结构
    const res = await request.get(`/rp/gen/preview/${row.id}`)
    // 保存 payload 触发 v-if 渲染
    previewData.value = res.data
  } finally { previewLoading.value = false }
}

// 页面挂载后自动加载第一页
onMounted(fetchList)
</script>

<!-- 样式区块：仅约束预览容器高度，scoped 保证只作用于本页，不污染其他页面 -->
<style scoped>
/* .preview-body：报表渲染容器；给出最小高度是为了在数据未返回或 loading 时弹窗不塌陷，
   避免弹窗高度跳变；此处不涉及暗色主题变量，配色由 ReportPreview 组件内部决定 */
.preview-body { min-height: 320px; }
</style>
