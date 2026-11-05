<!--
  文件级说明：外部接口调用日志页（只读）。
  职责：按接口名称与 HTTP 状态码查询第三方接口的历史调用记录，展示请求 URL、参数、响应、耗时与错误信息。
  依赖：@/utils/request（统一 /api 前缀、Bearer token 与错误提示）；Element Plus 表格/表单/分页；
        @element-plus/icons-vue 的 Search、Refresh 图标。
  数据来源：GET /outer/log/list（分页 + 条件过滤）。
  被谁使用：由路由挂载在“外部接口 → 调用日志”菜单，用于排查 outer/api 与 outer/sync 的调用失败问题。
-->
<template>
  <!-- 页面根容器：统一内边距与背景 -->
  <div class="app-container">
    <!-- 页头：标题 + 总条数副标题 -->
    <div class="page-header">
      <div class="page-title-wrap">
        <!-- 主标题：请求日志 -->
        <h2>请求日志</h2>
        <!-- 副标题：强调只读属性，并实时展示总条数 -->
        <div class="sub">只读 · 共 {{ total }} 条</div>
      </div>
    </div>
    <!-- 查询条件卡片：扁平样式，与表格卡片形成管理页布局 -->
    <el-card shadow="never" class="search-card">
      <!-- 行内表单；阻止原生提交，统一走按钮/回车查询 -->
      <el-form :model="query" inline @submit.prevent>
        <el-form-item label="接口名称">
          <!-- 名称模糊搜索：clearable 一键清空，回车即查询 -->
          <el-input v-model="query.api_name" placeholder="请输入接口名称" clearable style="width: 180px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="HTTP状态">
          <!-- 状态码精确过滤：输入框保留字符串类型，与后端按字符串匹配的约定一致（如 200/404） -->
          <el-input v-model="query.http_code" placeholder="如 200" clearable style="width: 120px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item>
          <!-- 查询：回到第 1 页按当前条件请求 -->
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <!-- 重置：恢复初始条件后重新查询 -->
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 日志表格卡片：只读列表，无新增/编辑/删除操作 -->
    <el-card shadow="never" class="table-card">
      <!-- 表格：v-loading 遮罩、stripe 斑马纹、空态文案 -->
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据">
        <!-- 序号列：前端自动编号 -->
        <el-table-column type="index" label="序号" width="70" align="center" />
        <!-- 接口ID：对应 outer/api 里的接口主键，便于与接口配置页对照 -->
        <el-table-column label="接口ID" prop="api_id" width="90" />
        <el-table-column label="接口名称" min-width="150">
          <!-- 名称为空（接口已删除）时用 “-” 占位，避免出现空白单元格 -->
          <template #default="{ row }">{{ row.api_name || '-' }}</template>
        </el-table-column>
        <!-- 请求URL：记录调用当时的完整地址，便于排查参数/路径问题 -->
        <el-table-column label="请求URL" prop="request_url" min-width="220" show-overflow-tooltip />
        <!-- 请求参数：原始请求体/参数文本，超长省略并悬浮查看 -->
        <el-table-column label="请求参数" prop="request_param" min-width="200" show-overflow-tooltip />
        <!-- 响应：返回体原文，超长省略；失败时通常也能看到错误响应 -->
        <el-table-column label="响应" prop="response_body" min-width="200" show-overflow-tooltip />
        <el-table-column label="HTTP状态" width="100" align="center">
          <!-- 状态码按区间着色：2xx 绿色=成功；>=400 红色=失败；其余默认色 -->
          <template #default="{ row }">
            <!-- 2xx：调用成功 -->
            <el-tag v-if="row.http_code>=200 && row.http_code<300" size="small" type="success">{{ row.http_code }}</el-tag>
            <!-- >=400：客户端/服务端错误，重点排查对象 -->
            <el-tag v-else-if="row.http_code>=400" size="small" type="danger">{{ row.http_code }}</el-tag>
            <!-- 其余（3xx 或空值）：显示原值，空值降级为 “-” -->
            <el-tag v-else size="small">{{ row.http_code || '-' }}</el-tag>
          </template>
        </el-table-column>
        <!-- 耗时(ms)：接口响应时间，用于评估第三方性能 -->
        <el-table-column label="耗时(ms)" prop="cost_time" width="100" />
        <!-- 错误信息：调用异常时的简要原因，为空时显示 “-” -->
        <el-table-column label="错误信息" prop="error_msg" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">{{ row.error_msg || '-' }}</template>
        </el-table-column>
        <!-- 请求时间：后端已格式化字符串，直接展示 -->
        <el-table-column label="请求时间" prop="request_time" width="170" />
      </el-table>
      <!-- 分页容器：统一右对齐布局 -->
      <div class="pagination-wrap">
        <!-- 分页器：页码/每页条数双向绑定 query，变化即重新请求 -->
        <el-pagination background layout="total, sizes, prev, pager, next, jumper"
          :total="total" v-model:current-page="query.page" v-model:page-size="query.page_size"
          :page-sizes="[10, 20, 50, 100]" @change="fetchList" />
      </div>
    </el-card>
  </div>
</template>

<script setup>
// 组合式 API：ref 管标量/数组，reactive 管查询对象，onMounted 做首屏加载
import { ref, reactive, onMounted } from 'vue'
// 查询/重置按钮图标
import { Search, Refresh } from '@element-plus/icons-vue'
// 统一请求实例：自动带 token，失败统一提示
import request from '@/utils/request'

// 表格加载态：请求期间显示遮罩
const loading = ref(false)
// 当前页日志列表，绑定 el-table 的 :data
const rows = ref([])
// 后端总条数：供分页与页头“共 N 条”使用
const total = ref(0)

// 查询条件快照：重置时整体覆盖 query；两个字段都用空串表示不按该条件过滤
// http_code 用字符串而非数字，避免空串与 0 混淆，也便于按文本匹配
const query_orig = { page: 1, page_size: 10, api_name: '', http_code: '' }
// 响应式查询对象：与查询表单、分页双向绑定，直接作为列表接口 params
const query = reactive({ ...query_orig })

// 列表查询：查询/重置/翻页都复用（日志为后端写入，本页不会主动刷新）
async function fetchList() {
  // 打开遮罩提示加载中
  loading.value = true
  try {
    // GET 分页查询，条件由 query 序列化为 URL 参数
    const res = await request.get('/outer/log/list', { params: query })
    // list 兜底空数组、total 兜底 0，避免后端返回 null 时渲染异常
    rows.value = res.data.list || []
    total.value = res.data.total || 0
  // 成功失败都关闭遮罩
  } finally { loading.value = false }
}
// 查询：回到第 1 页再请求，避免旧页码越界
function handleSearch() { query.page = 1; fetchList() }
// 重置：用快照覆盖查询条件后重新查询
function handleReset() { Object.assign(query, query_orig); handleSearch() }

// 首屏加载日志列表
onMounted(fetchList)
</script>
