<!--
  文件级说明：
  职责：BI「访问记录」只读列表——按大屏名称、访客用户 ID 筛选，分页展示大屏的访问日志（大屏 ID/名称/访客/IP/时间）。
  依赖：@/utils/request（统一请求封装）、Element Plus 图标（Search/Refresh）。
  被谁使用：BI 菜单下的访问统计路由；本页没有新增/编辑/删除入口，仅用于查询追溯。
  说明：本文件没有 <style> 段，样式复用全局 app-container/search-card/table-card/pagination-wrap。
-->
<template>
  <!-- 页面根容器：复用全局 app-container 内边距 -->
  <div class="app-container">
    <!-- 页头：标题 + 只读标识与总条数，明确本页不提供写操作 -->
    <div class="page-header">
      <div class="page-title-wrap">
        <!-- 模块标题 -->
        <h2>访问记录</h2>
        <!-- 副标题：“只读”提示避免用户寻找新增入口；total 随筛选条件变化 -->
        <div class="sub">只读 · 共 {{ total }} 条</div>
      </div>
    </div>
    <!-- 搜索区：两个条件均为输入框，回车即可查询 -->
    <el-card shadow="never" class="search-card">
      <!-- inline 横向排列；@submit.prevent 阻止表单默认提交刷新页面 -->
      <el-form :model="query" inline @submit.prevent>
        <el-form-item label="大屏名称">
          <!-- 名称模糊搜索：clearable 支持一键清空；回车等价于点“查询” -->
          <el-input v-model="query.screen_name" placeholder="请输入大屏名称" clearable style="width: 180px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="访客ID">
          <!-- 访客用户 ID：用于按具体用户追溯访问记录；clearable 可清空；回车同样触发查询 -->
          <el-input v-model="query.visitor_user_id" placeholder="请输入访客ID" clearable style="width: 160px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item>
          <!-- 查询：回到第 1 页再请求，避免旧页码超出新条件的总页数 -->
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <!-- 重置：恢复查询初值后再查询 -->
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 列表卡片：只读展示访问日志 -->
    <el-card shadow="never" class="table-card">
      <!-- v-loading 控制加载遮罩；rows 为当前页数据；stripe 斑马纹；empty-text 中文空态 -->
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据">
        <!-- 序号列：当前页内顺序编号 -->
        <el-table-column type="index" label="序号" width="70" align="center" />
        <!-- 大屏ID：固定宽度，数字较短，便于与名称对照排查 -->
        <el-table-column label="大屏ID" prop="screen_id" width="90" />
        <!-- 大屏名称：后端可能未关联到名称（大屏已删除），回退显示“-” -->
        <el-table-column label="大屏名称" min-width="180">
          <template #default="{ row }">{{ row.screen_name || '-' }}</template>
        </el-table-column>
        <!-- 访客用户ID：匿名访问时后端可能为空，直接显示原始值 -->
        <el-table-column label="访客用户ID" prop="visitor_user_id" width="120" />
        <!-- 访客IP：IPv6 较长，超长时悬浮查看全文 -->
        <el-table-column label="访客IP" prop="visit_ip" min-width="160" show-overflow-tooltip />
        <!-- 访问时间：后端格式化好的字符串，直接展示 -->
        <el-table-column label="访问时间" prop="visit_time" width="170" />
      </el-table>
      <!-- 分页器：v-model 绑定 query.page/page_size，@change 覆盖页码与每页条数变化 -->
      <div class="pagination-wrap">
        <el-pagination background layout="total, sizes, prev, pager, next, jumper"
          :total="total" v-model:current-page="query.page" v-model:page-size="query.page_size"
          :page-sizes="[10, 20, 50, 100]" @change="fetchList" />
      </div>
    </el-card>
  </div>
</template>

<script setup>
// 组合式 API：本页只有查询相关的最小状态
// ref 基础响应式；reactive 查询对象便于整体重置；onMounted 首屏加载
import { ref, reactive, onMounted } from 'vue'
// 仅需搜索/重置两个按钮图标
import { Search, Refresh } from '@element-plus/icons-vue'
// 统一请求实例：自动带 token、统一解析 { code, msg, data }、统一错误提示
import request from '@/utils/request'

// 列表加载态：控制 el-table 的 v-loading
const loading = ref(false)
// 当前页访问记录
const rows = ref([])
// 总条数：分页器与页头副标题共用
const total = ref(0)

// 查询初值：重置时整体恢复（页码回到 1，两个条件清空）
const query_orig = { page: 1, page_size: 10, screen_name: '', visitor_user_id: '' }
// 查询对象：reactive 便于 Object.assign 重置；分页器直接 v-model 到 page/page_size
const query = reactive({ ...query_orig })

// 拉取访问记录：params 为 reactive 的 query；finally 保证异常时也解除加载遮罩
async function fetchList() {
  loading.value = true
  try {
    const res = await request.get('/bi/visit/list', { params: query })
    // 兼容后端未返回 list/total 的情况
    rows.value = res.data.list || []
    total.value = res.data.total || 0
  } finally { loading.value = false }
}
// 查询：回到第 1 页，避免旧页码超出新条件的总页数
function handleSearch() { query.page = 1; fetchList() }
// 重置：整体恢复查询初值后再查询
function handleReset() { Object.assign(query, query_orig); handleSearch() }

// 首屏加载第一页数据
onMounted(fetchList)
</script>
