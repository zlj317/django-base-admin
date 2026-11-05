<!-- 消息推送日志页（消息中心 / 推送记录）
     职责：只读查询每条消息在各渠道的实际下发结果（待推送/成功/失败、错误信息、重试次数、推送时间），用于排障与审计。
     接口：GET /msg/push_log/list（分页，参数 receiver_id/push_status/channel）。
     依赖：@/utils/request（统一 baseURL、token 与错误提示）、Element Plus 表格/标签组件、Search/Refresh 图标。
     被谁使用：由后端菜单动态挂载进入；本页不做任何写操作，数据由后端推送任务写入。 -->
<template>
  <!-- 页面根容器：复用全局 .app-container 的留白与进场动画 -->
  <div class="app-container">
    <!-- 页头：标题 + 总数；"只读"提示用户本页没有编辑能力 -->
    <div class="page-header">
      <!-- 标题组 -->
      <div class="page-title-wrap">
        <!-- 主标题：与菜单名一致 -->
        <h2>推送记录</h2>
        <!-- 副标题：total 为服务端返回的总记录数 -->
        <div class="sub">只读 · 共 {{ total }} 条</div>
      </div>
    </div>
    <!-- 查询卡片：shadow="never" 弱化辅助区域 -->
    <el-card shadow="never" class="search-card">
      <!-- inline 单行排列；@submit.prevent 阻止回车触发表单原生提交导致页面刷新 -->
      <el-form :model="query" inline @submit.prevent>
        <!-- 接收人筛选：按用户 ID 精确查询，便于定位某个用户收到的推送 -->
        <el-form-item label="接收人ID">
          <!-- clearable 一键清空；160px 固定宽度；回车直接查询 -->
          <el-input v-model="query.receiver_id" placeholder="请输入接收人ID" clearable style="width: 160px" @keyup.enter="handleSearch" />
        </el-form-item>
        <!-- 推送状态筛选：0/1/2 为后端状态码，与表格标签一一对应 -->
        <el-form-item label="推送状态">
          <!-- 清空后 push_status 回到 null，即不按状态过滤 -->
          <el-select v-model="query.push_status" placeholder="全部" clearable style="width: 130px">
            <!-- 0 = 待推送：消息已入队但尚未下发 -->
            <el-option label="待推送" :value="0" />
            <!-- 1 = 成功：对应渠道已返回成功 -->
            <el-option label="成功" :value="1" />
            <!-- 2 = 失败：下发失败，错误信息见列表 -->
            <el-option label="失败" :value="2" />
          </el-select>
        </el-form-item>
        <!-- 渠道筛选：枚举值取自推送渠道配置的渠道编码 -->
        <el-form-item label="渠道">
          <!-- 清空后 channel 回到 null，即不按渠道过滤 -->
          <el-select v-model="query.channel" placeholder="全部" clearable style="width: 130px">
            <!-- site = 站内信（写入站内消息记录） -->
            <el-option label="站内信" value="site" />
            <!-- sms = 短信 -->
            <el-option label="短信" value="sms" />
            <!-- email = 邮件 -->
            <el-option label="邮件" value="email" />
          </el-select>
        </el-form-item>
        <!-- 操作按钮组 -->
        <el-form-item>
          <!-- 查询：回到第一页并拉取 -->
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <!-- 重置：恢复默认条件后重新查询 -->
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 表格卡片：只读列表，无选择列与操作列 -->
    <el-card shadow="never" class="table-card">
      <!-- 表格：v-loading 显示请求加载态；stripe 隔行变色；空态使用中文 -->
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据">
        <!-- 序号列：仅用于阅读定位 -->
        <el-table-column type="index" label="序号" width="70" align="center" />
        <!-- 记录ID：对应消息记录表的主键，可串联"站内消息"页排查 -->
        <el-table-column label="记录ID" prop="record_id" min-width="160" show-overflow-tooltip />
        <!-- 接收人ID：消息目标用户 -->
        <el-table-column label="接收人ID" prop="receiver_id" width="110" />
        <!-- 渠道：直接展示渠道编码（site/sms/email），与渠道配置页的编码保持一致 -->
        <el-table-column label="渠道" prop="channel" width="100" />
        <!-- 推送状态：按状态码渲染不同颜色的标签，便于快速扫视失败记录 -->
        <el-table-column label="推送状态" width="110" align="center">
          <template #default="{ row }">
            <!-- 0 待推送：灰色 info 标签 -->
            <el-tag v-if="row.push_status===0" size="small" type="info">待推送</el-tag>
            <!-- 1 成功：绿色 success 标签 -->
            <el-tag v-else-if="row.push_status===1" size="small" type="success">成功</el-tag>
            <!-- 2 失败：红色 danger 标签 -->
            <el-tag v-else-if="row.push_status===2" size="small" type="danger">失败</el-tag>
            <!-- 兜底：出现未约定状态码时原样展示，避免误标成成功/失败 -->
            <span v-else>{{ row.push_status }}</span>
          </template>
        </el-table-column>
        <!-- 错误信息：失败原因（接口返回、超时等）；为空时用 '-' 占位保持表格整洁 -->
        <el-table-column label="错误信息" prop="error_msg" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">{{ row.error_msg || '-' }}</template>
        </el-table-column>
        <!-- 重试次数：失败后累计重试次数，用于判断是否是持续失败 -->
        <el-table-column label="重试次数" prop="retry_count" width="90" />
        <!-- 推送时间：真正下发的时间点，空值代表尚未推送 -->
        <el-table-column label="推送时间" prop="push_time" width="170" />
      </el-table>
      <!-- 分页：总数/每页条数/翻页/跳页；页码与页大小双向写回 query，变化即刷新 -->
      <div class="pagination-wrap">
        <el-pagination background layout="total, sizes, prev, pager, next, jumper"
          :total="total" v-model:current-page="query.page" v-model:page-size="query.page_size"
          :page-sizes="[10, 20, 50, 100]" @change="fetchList" />
      </div>
    </el-card>
  </div>
</template>

<script setup>
// 组合式 API：ref 管状态、reactive 管查询条件、onMounted 做首屏加载
import { ref, reactive, onMounted } from 'vue'
// 图标组件以对象形式传入 :icon
import { Search, Refresh } from '@element-plus/icons-vue'
// 统一请求封装：内置 baseURL=/api、token 注入与统一错误提示
import request from '@/utils/request'

// 表格加载态
const loading = ref(false)
// 当前页的推送日志列表
const rows = ref([])
// 服务端返回的总记录数
const total = ref(0)

// 查询条件默认值；布尔类筛选统一用 null 表示"全部"，页码从 1 开始
const query_orig = { page: 1, page_size: 10, receiver_id: '', push_status: null, channel: null }
// 实际查询条件：保留 reactive 引用，模板与请求参数共用
const query = reactive({ ...query_orig })

// 拉取列表：loading 在 finally 中关闭，异常时不会卡在加载中
async function fetchList() {
  loading.value = true
  try {
    // 参数直接传 query；null 字段由后端忽略
    const res = await request.get('/msg/push_log/list', { params: query })
    // 兜底空值，避免 list/total 缺省时渲染异常
    rows.value = res.data.list || []
    total.value = res.data.total || 0
  } finally { loading.value = false }
}
// 查询：条件变化后回到第 1 页再加载
function handleSearch() { query.page = 1; fetchList() }
// 重置：回填默认值并重新查询（不改变 reactive 引用）
function handleReset() { Object.assign(query, query_orig); handleSearch() }

// 页面挂载后加载第一页
onMounted(fetchList)
</script>
