<!-- 文件级说明：安全策略 - 登录尝试记录（只读）列表页。
     职责：按用户名、登录结果筛选历史登录日志，仅做查询展示，不提供新增/修改/删除。
     依赖：Vue 3 <script setup>、Element Plus（表格/分页/图标）、@/utils/request（统一请求封装，baseURL=/api）。
     被谁使用：由 sec（安全）模块的路由挂载，用于审计暴力破解、异常登录等安全事件。
     注意：本文件不含 <style> 块，页面结构样式来自全局样式表。 -->
<template>
  <!-- 页面根容器：套用全局 app-container 布局，向下承载页头与查询/表格卡片 -->
  <div class="app-container">
    <!-- 页头区域：标题 + 副标题 -->
    <div class="page-header">
      <!-- 标题容器：横向排列主标题与统计信息 -->
      <div class="page-title-wrap">
        <!-- 主标题：标明当前页面为登录尝试记录 -->
        <h2>登录尝试记录</h2>
        <!-- 副标题：说明这是只读的安全日志，并回显 total（接口返回的总条数） -->
        <div class="sub">登录安全日志 · 共 {{ total }} 条（只读）</div>
      </div>
    </div>

    <!-- 查询条件卡片：承载搜索表单；shadow="never" 保持与后台管理页一致的扁平风格 -->
    <el-card shadow="never" class="search-card">
      <!-- 搜索表单：inline 横向排列；@submit.prevent 阻止回车触发表单默认提交造成页面刷新 -->
      <el-form :model="query" inline @submit.prevent>
        <!-- 用户名筛选项：对应后端 username 字段 -->
        <el-form-item label="用户名">
          <!-- 输入框：clearable 一键清空；@keyup.enter 回车即查询；固定宽度保持工具栏整齐 -->
          <el-input v-model="query.username" placeholder="请输入用户名" clearable style="width: 170px" @keyup.enter="handleSearch" />
        </el-form-item>
        <!-- 登录结果筛选项：对应后端 success_flag（1 成功 / 0 失败） -->
        <el-form-item label="结果">
          <!-- 下拉框：placeholder="全部" 表示不按结果过滤；clearable 清空后回到全部 -->
          <el-select v-model="query.success_flag" placeholder="全部" clearable style="width: 110px">
            <!-- 成功：账号密码校验通过，可作为正常登录的对照记录 -->
            <el-option label="成功" :value="1" />
            <!-- 失败：校验未通过，是识别暴力破解的主要依据 -->
            <el-option label="失败" :value="0" />
          </el-select>
        </el-form-item>
        <!-- 操作按钮行 -->
        <el-form-item>
          <!-- 查询按钮：回到第 1 页并重新拉取日志 -->
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <!-- 重置按钮：恢复默认查询条件后重新查询 -->
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 数据表格卡片：只读展示，无工具栏按钮 -->
    <el-card shadow="never" class="table-card">
      <!-- 表格：v-loading 显示请求遮罩；stripe 斑马纹便于逐行核对；无多选列，因为本页不提供批量操作 -->
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据">
        <!-- 序号列：按当前页顺序自动编号 -->
        <el-table-column type="index" label="序号" width="70" align="center" />
        <!-- 用户名列：被尝试登录的账号；超长时省略并悬浮查看全文 -->
        <el-table-column label="用户名" prop="username" min-width="140" show-overflow-tooltip />
        <!-- IP 地址列：发起登录请求的来源 IP，是定位攻击来源的关键信息 -->
        <el-table-column label="IP地址" prop="ip" width="140" />
        <!-- 登录时间列：后端返回的时间字符串，前端直接展示不做格式化 -->
        <el-table-column label="登录时间" prop="attempt_time" width="170" />
        <!-- 结果列：把后端标记翻译成中文标签，颜色区分成功/失败 -->
        <el-table-column label="结果" width="90" align="center">
          <!-- 默认插槽：解构当前行 row -->
          <template #default="{ row }">
            <!-- 成功：兼容后端返回数字 1 或字符串 '1' 的两种序列化形式 -->
            <el-tag v-if="row.success_flag===1 || row.success_flag==='1'" size="small" type="success">成功</el-tag>
            <!-- 其余值统一按失败展示，避免脏数据造成空白 -->
            <el-tag v-else size="small" type="danger">失败</el-tag>
          </template>
        </el-table-column>
        <!-- User-Agent 列：记录客户端浏览器/工具标识，便于识别脚本化攻击 -->
        <el-table-column label="User-Agent" prop="user_agent" min-width="200" show-overflow-tooltip />
      </el-table>
      <!-- 分页容器 -->
      <div class="pagination-wrap">
        <!-- 分页：layout 展示总数、每页条数、上一页、页码、下一页、跳页 -->
        <el-pagination background layout="total, sizes, prev, pager, next, jumper"
          :total="total" v-model:current-page="query.page" v-model:page-size="query.page_size"
          :page-sizes="[10, 20, 50, 100]" @change="fetchList" />
        <!-- 说明：页码与每页条数双向绑定 query，变化即触发 @change 重新查询 -->
      </div>
    </el-card>
  </div>
</template>

<script setup>
// 组合式 API：ref 管理加载态/数据，reactive 管理查询条件，onMounted 在挂载后首次拉取数据
import { ref, reactive, onMounted } from 'vue'
// 按钮图标：Search 查询、Refresh 重置
import { Search, Refresh } from '@element-plus/icons-vue'
// 统一请求实例：内置 baseURL=/api、token 注入与错误提示，本页只读取列表
import request from '@/utils/request'

// 表格加载态：请求期间置 true，交给 v-loading 显示遮罩
const loading = ref(false)
// 当前页日志数据：由 list 接口的 data.list 填充
const rows = ref([])
// 总条数：由 list 接口的 data.total 填充，供分页与页头统计使用
const total = ref(0)

// 查询条件默认值：作为"重置"的基准，避免重置时丢失分页大小
const query_orig = { page: 1, page_size: 10, username: '', success_flag: null }
// 响应式查询对象：展开拷贝与基准解耦，修改条件不影响 query_orig
const query = reactive({ ...query_orig })

// 拉取列表：try/finally 保证请求失败时加载态也能复位，错误提示由 request 拦截器统一处理
async function fetchList() {
  loading.value = true
  try {
    // GET 分页查询：query 直接作为分页与筛选参数
    const res = await request.get('/sec/login_attempt/list', { params: query })
    // data.list 为当前页记录；null 时用 [] 兜底避免表格报错
    rows.value = res.data.list || []
    // data.total 为满足条件的总条数；缺失时按 0 处理
    total.value = res.data.total || 0
  } finally { loading.value = false }
}

// 查询：条件变化后回到第 1 页，避免停留在超出的页码
function handleSearch() { query.page = 1; fetchList() }
// 重置：恢复默认条件（含分页参数）后重新查询
function handleReset() { Object.assign(query, query_orig); handleSearch() }

// 页面挂载后立即拉取一次，避免首屏出现空表格
onMounted(fetchList)
</script>
