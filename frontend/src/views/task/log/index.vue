<!-- 文件级说明：任务调度 - 任务执行日志（只读）列表页。
     职责：按任务名称、运行状态查询每次调度的执行结果、返回信息、错误信息与耗时。
     依赖：Vue 3 <script setup>、Element Plus（表格/分页/图标）、@/utils/request（统一请求封装，baseURL=/api）。
     被谁使用：由 task 模块的路由挂载，用于排查任务失败原因、确认“立即执行”是否成功。
     注意：本文件不含 <style> 块，页面样式来自全局样式表。 -->
<template>
  <!-- 页面根容器：套用全局 app-container 布局 -->
  <div class="app-container">
    <!-- 页头区域 -->
    <div class="page-header">
      <!-- 标题容器：主标题与统计信息横排 -->
      <div class="page-title-wrap">
        <!-- 页面主标题 -->
        <h2>任务日志</h2>
        <!-- 副标题：说明本页只读，并回显接口返回的总条数 -->
        <div class="sub">只读 · 共 {{ total }} 条</div>
      </div>
    </div>
    <!-- 查询条件卡片：shadow="never" 去掉阴影，保持后台列表页的扁平风格 -->
    <el-card shadow="never" class="search-card">
      <!-- 搜索表单：inline 横向排列；@submit.prevent 阻止回车触发默认提交刷新页面 -->
      <el-form :model="query" inline @submit.prevent>
        <!-- 任务名称筛选项：对应后端 task_name，用于排查某个具体任务的历史执行 -->
        <el-form-item label="任务名称">
          <!-- 输入框：clearable 一键清空；回车即查询；固定宽度保持工具栏整齐 -->
          <el-input v-model="query.task_name" placeholder="请输入任务名称" clearable style="width: 170px" @keyup.enter="handleSearch" />
        </el-form-item>
        <!-- 运行状态筛选项：对应后端 run_status（0 运行中 / 1 成功 / 2 失败） -->
        <el-form-item label="运行状态">
          <!-- 下拉框：clearable 后可查询全部状态 -->
          <el-select v-model="query.run_status" placeholder="全部" clearable style="width: 130px">
            <!-- 运行中：任务尚未结束，通常用于观察长任务是否卡住 -->
            <el-option label="运行中" :value="0" />
            <!-- 成功：任务正常执行完毕 -->
            <el-option label="成功" :value="1" />
            <!-- 失败：执行异常，需结合错误信息列定位原因 -->
            <el-option label="失败" :value="2" />
          </el-select>
        </el-form-item>
        <!-- 操作按钮行 -->
        <el-form-item>
          <!-- 查询按钮：回第 1 页并重新拉取 -->
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <!-- 重置按钮：恢复默认条件后重新查询 -->
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 数据日志卡片：只读展示，无工具栏按钮 -->
    <el-card shadow="never" class="table-card">
      <!-- 表格：v-loading 显示加载遮罩；stripe 斑马纹便于逐条核对；无多选列，因为本页不提供批量操作 -->
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据">
        <!-- 序号列：按当前页顺序自动编号 -->
        <el-table-column type="index" label="序号" width="70" align="center" />
        <!-- 任务 ID 列：关联任务信息表的主键，便于按 ID 反查任务配置 -->
        <el-table-column label="任务ID" prop="task_id" width="90" />
        <!-- 任务名称列：执行时冗余记录的名称，任务改名后仍能看到当时名称 -->
        <el-table-column label="任务名称" prop="task_name" min-width="160" show-overflow-tooltip />
        <!-- 运行状态列：把后端状态码翻译成中文标签，颜色区分结果 -->
        <el-table-column label="运行状态" width="100" align="center">
          <!-- 默认插槽：按 run_status 渲染标签 -->
          <template #default="{ row }">
            <!-- 运行中：0，用 warning 橙色提示尚未结束 -->
            <el-tag v-if="row.run_status===0" size="small" type="warning">运行中</el-tag>
            <!-- 成功：1，用 success 绿色 -->
            <el-tag v-else-if="row.run_status===1" size="small" type="success">成功</el-tag>
            <!-- 失败：2，用 danger 红色 -->
            <el-tag v-else-if="row.run_status===2" size="small" type="danger">失败</el-tag>
            <!-- 兜底：未知状态码直接展示原值，便于排查数据异常 -->
            <span v-else>{{ row.run_status }}</span>
          </template>
        </el-table-column>
        <!-- 返回信息列：任务函数的正常输出（如同步条数），空值显示 "-" -->
        <el-table-column label="返回信息" prop="return_info" min-width="200" show-overflow-tooltip>
          <!-- 默认插槽：空值统一用短横线占位，保持表格对齐 -->
          <template #default="{ row }">{{ row.return_info || '-' }}</template>
        </el-table-column>
        <!-- 错误信息列：失败时的异常堆栈/原因，是定位问题的核心字段 -->
        <el-table-column label="错误信息" prop="error_msg" min-width="220" show-overflow-tooltip>
          <!-- 默认插槽：成功任务通常无错误信息，用短横线占位 -->
          <template #default="{ row }">{{ row.error_msg || '-' }}</template>
        </el-table-column>
        <!-- 耗时列：本次执行耗时（毫秒），可用于发现性能退化 -->
        <el-table-column label="耗时(ms)" prop="cost_time" width="100" />
        <!-- 运行时间列：本次执行的开始时间 -->
        <el-table-column label="运行时间" prop="run_time" width="170" />
      </el-table>
      <!-- 分页容器 -->
      <div class="pagination-wrap">
        <!-- 分页：页码与每页条数双向绑定 query，变化触发 @change 重新查询 -->
        <el-pagination background layout="total, sizes, prev, pager, next, jumper"
          :total="total" v-model:current-page="query.page" v-model:page-size="query.page_size"
          :page-sizes="[10, 20, 50, 100]" @change="fetchList" />
        <!-- 说明：每页可选 10/20/50/100 条 -->
      </div>
    </el-card>
  </div>
</template>

<script setup>
// 组合式 API：ref 管理加载态/数据，reactive 管理查询条件，onMounted 挂载后首次拉取
import { ref, reactive, onMounted } from 'vue'
// 按钮图标：Search 查询、Refresh 重置
import { Search, Refresh } from '@element-plus/icons-vue'
// 统一请求实例：内置 baseURL=/api、token 注入与错误提示，本页只读取日志
import request from '@/utils/request'

// 表格加载态：请求期间置 true，交给 v-loading 显示遮罩
const loading = ref(false)
// 当前页日志数据：由 list 接口的 data.list 填充
const rows = ref([])
// 总条数：由 list 接口的 data.total 填充，供分页与页头统计使用
const total = ref(0)

// 查询条件默认值：作为"重置"的基准，避免重置时丢失分页大小
const query_orig = { page: 1, page_size: 10, task_name: '', run_status: null }
// 响应式查询对象：展开拷贝与基准解耦
const query = reactive({ ...query_orig })

// 拉取列表：try/finally 保证请求失败时加载态也能复位，错误提示由 request 拦截器统一处理
async function fetchList() {
  loading.value = true
  try {
    // GET 分页查询：query 直接作为分页与筛选参数
    const res = await request.get('/task/log/list', { params: query })
    // data.list 为当前页日志；null 时用 [] 兜底避免表格报错
    rows.value = res.data.list || []
    // data.total 为总条数；缺失时按 0 处理
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
