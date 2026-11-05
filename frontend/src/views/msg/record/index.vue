<!-- 站内消息记录页（消息中心 / 消息记录）
     职责：按接收人、消息类型、已读状态查询站内信记录，支持标记已读与单条/批量删除。
     接口：GET /msg/record/list（分页）、POST /msg/record/read/{id}（标记已读）、
           DELETE /msg/record/delete（单条/批量共用，ids 放请求体）。
     依赖：@/utils/request（统一 baseURL、token 与错误提示）、Element Plus 表格/标签/确认框、v-perm 权限指令。
     被谁使用：由后端菜单动态挂载进入；数据由消息发送流程写入，管理端在这里做查询与清理。 -->
<template>
  <!-- 页面根容器：复用全局 .app-container 的留白与进场动画 -->
  <div class="app-container">
    <!-- 页头：标题 + 记录总数 -->
    <div class="page-header">
      <!-- 标题组 -->
      <div class="page-title-wrap">
        <!-- 主标题：与菜单名一致 -->
        <h2>站内消息</h2>
        <!-- 副标题：total 为服务端返回的总记录数 -->
        <div class="sub">消息记录 · 共 {{ total }} 条</div>
      </div>
    </div>
    <!-- 查询卡片：shadow="never" 弱化辅助区域，突出下方表格 -->
    <el-card shadow="never" class="search-card">
      <!-- inline 单行排列筛选项；@submit.prevent 阻止回车触发表单原生提交刷新整页 -->
      <el-form :model="query" inline @submit.prevent>
        <!-- 接收人筛选：按用户 ID 查询其收到的消息 -->
        <el-form-item label="接收人ID">
          <!-- clearable 一键清空；160px 固定宽度；回车直接查询 -->
          <el-input v-model="query.receiver_id" placeholder="请输入接收人ID" clearable style="width: 160px" @keyup.enter="handleSearch" />
        </el-form-item>
        <!-- 消息类型筛选：下拉值即后端存储的类型编码 -->
        <el-form-item label="消息类型">
          <!-- 清空后 msg_type 回到 null，即不按类型过滤 -->
          <el-select v-model="query.msg_type" placeholder="全部" clearable style="width: 130px">
            <!-- todo = 待办：工作流中等待当前用户处理的任务提醒 -->
            <el-option label="待办" value="todo" />
            <!-- done = 已办：自己提交/处理的流程已完成的回执 -->
            <el-option label="已办" value="done" />
            <!-- cc = 抄送：流程抄送给当前用户的知会消息 -->
            <el-option label="抄送" value="cc" />
            <!-- system = 系统：系统公告、账号与权限变动等系统级消息 -->
            <el-option label="系统" value="system" />
            <!-- report = 报表：报表生成/导出完成通知 -->
            <el-option label="报表" value="report" />
            <!-- alarm = 告警：监控指标触发的告警通知 -->
            <el-option label="告警" value="alarm" />
            <!-- notice = 通知：通用业务通知 -->
            <el-option label="通知" value="notice" />
          </el-select>
        </el-form-item>
        <!-- 已读状态筛选：1/0 数字与后端 tinyint 保持一致 -->
        <el-form-item label="是否已读">
          <!-- 清空后 is_read 回到 null，即不按已读状态过滤 -->
          <el-select v-model="query.is_read" placeholder="全部" clearable style="width: 110px">
            <!-- 1 = 已读 -->
            <el-option label="已读" :value="1" />
            <!-- 0 = 未读 -->
            <el-option label="未读" :value="0" />
          </el-select>
        </el-form-item>
        <!-- 操作按钮组：查询 / 重置 -->
        <el-form-item>
          <!-- 查询：回到第一页并拉取 -->
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <!-- 重置：恢复默认条件后重新查询 -->
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 表格卡片：只提供删除类操作，没有新增/编辑入口 -->
    <el-card shadow="never" class="table-card">
      <!-- 工具栏插槽：批量删除；未勾选时禁用 -->
      <template #header>
        <div class="card-header">
          <div class="card-actions">
            <!-- 批量删除：需 msg:delete；plain 弱化危险色；selection 为空时禁用避免空提交 -->
            <el-button v-perm="'msg:delete'" type="danger" plain :icon="Delete" :disabled="!selection.length" @click="handleBatchDelete">批量删除</el-button>
          </div>
        </div>
      </template>
      <!-- 表格：v-loading 加载态；stripe 隔行变色；空态中文；selection-change 同步勾选行 -->
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据" @selection-change="onSelectionChange">
        <!-- 序号列：阅读定位 -->
        <el-table-column type="index" label="序号" width="70" align="center" />
        <!-- 多选列：为批量删除提供勾选能力 -->
        <el-table-column type="selection" width="50" />
        <!-- 消息类型：直接展示类型编码（todo/done/cc 等），与筛选下拉的取值对应 -->
        <el-table-column label="消息类型" prop="msg_type" width="100" />
        <!-- 标题：消息概要，超长省略并用 tooltip 展示全文 -->
        <el-table-column label="标题" prop="title" min-width="180" show-overflow-tooltip />
        <!-- 内容：消息正文，可能较长，min-width 给足空间 -->
        <el-table-column label="内容" prop="content" min-width="260" show-overflow-tooltip />
        <!-- 接收人ID：消息目标用户 -->
        <el-table-column label="接收人ID" prop="receiver_id" width="110" />
        <!-- 跳转链接：点击消息后要跳转的业务页面地址 -->
        <el-table-column label="跳转链接" prop="link_url" min-width="180" show-overflow-tooltip />
        <!-- 是否已读：根据 is_read 渲染标签，未读用 danger 色突出 -->
        <el-table-column label="是否已读" width="90" align="center">
          <template #default="{ row }">
            <!-- is_read 为真值展示"已读"，使用默认色 -->
            <el-tag v-if="row.is_read" size="small">已读</el-tag>
            <!-- 否则展示"未读"，红色提示需要处理 -->
            <el-tag v-else size="small" type="danger">未读</el-tag>
          </template>
        </el-table-column>
        <!-- 阅读时间：为空（未读）时用 '-' 占位 -->
        <el-table-column label="阅读时间" prop="read_time" width="170">
          <template #default="{ row }">{{ row.read_time || '-' }}</template>
        </el-table-column>
        <!-- 创建时间：消息写入时间 -->
        <el-table-column label="创建时间" prop="create_time" width="170" />
        <!-- 操作列：fixed="right" 横向滚动时仍可见 -->
        <el-table-column label="操作" width="200" fixed="right" class-name="op-col">
          <template #default="{ row }">
            <!-- 标记已读：仅未读行显示，避免对已读消息做无意义的重复操作；需 msg:update -->
            <el-button v-if="!row.is_read" v-perm="'msg:update'" link type="primary" @click="handleMarkRead(row)">标记已读</el-button>
            <!-- 删除：需 msg:delete，单条删除同样走 ids 数组接口 -->
            <el-button v-perm="'msg:delete'" link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
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
// ElMessage 成功提示；ElMessageBox 删除前二次确认
import { ElMessage, ElMessageBox } from 'element-plus'
// 图标组件以对象形式传给 :icon
import { Search, Refresh, Delete } from '@element-plus/icons-vue'
// 统一请求封装：内置 baseURL=/api、token 注入与统一错误提示
import request from '@/utils/request'

// 表格加载态
const loading = ref(false)
// 当前页的消息记录列表
const rows = ref([])
// 服务端返回的总记录数
const total = ref(0)
// 当前勾选的行，批量删除按钮的禁用与提交都依赖它
const selection = ref([])

// 查询条件默认值；文本为空、数字筛选为 null 均表示"全部"，页码从 1 开始
const query_orig = { page: 1, page_size: 10, receiver_id: '', msg_type: null, is_read: null }
// 实际查询条件：保留 reactive 引用，模板与请求参数共用
const query = reactive({ ...query_orig })

// 集中维护接口前缀，避免各处硬编码；按动作名返回对应 URL
function apiUrl(action) {
  const base = '/msg/record'
  // mark_read 为标记已读，调用时还会拼接记录 id
  return {
    list: base + '/list',
    delete: base + '/delete',
    mark_read: base + '/read'
  }[action]
}

// 拉取列表：loading 在 finally 中关闭，异常时不会卡在加载中
async function fetchList() {
  loading.value = true
  try {
    // 参数直接传 query；null 字段由后端忽略
    const res = await request.get(apiUrl('list'), { params: query })
    // 兜底空值，避免 list/total 缺省时渲染异常
    rows.value = res.data.list || []
    total.value = res.data.total || 0
  } finally { loading.value = false }
}
// 查询：条件变化后回到第 1 页再加载
function handleSearch() { query.page = 1; fetchList() }
// 重置：回填默认值并重新查询（不改变 reactive 引用）
function handleReset() { Object.assign(query, query_orig); handleSearch() }
// 表格勾选变化时同步选中行数组
function onSelectionChange(r) { selection.value = r }

// 标记已读：按记录 id 发送 POST，成功后刷新列表让"已读"状态立即生效
async function handleMarkRead(row) {
  await request.post(`${apiUrl('mark_read')}/${row.id}`)
  ElMessage.success('已标记为已读'); fetchList()
}

// 单条删除：先二次确认（用户取消会 reject，不会删除），再按 ids 数组提交
async function handleDelete(row) {
  await ElMessageBox.confirm('确定删除该消息？', '提示', { type: 'warning' })
  await request.delete(apiUrl('delete'), { data: { ids: [row.id] } })
  ElMessage.success('删除成功'); fetchList()
}

// 批量删除：用勾选行的 id 组成数组，与单条删除共用同一个 delete 接口
async function handleBatchDelete() {
  await ElMessageBox.confirm(`确定删除选中的 ${selection.value.length} 条消息？`, '提示', { type: 'warning' })
  await request.delete(apiUrl('delete'), { data: { ids: selection.value.map(r => r.id) } })
  ElMessage.success('批量删除成功'); fetchList()
}

// 页面挂载后加载第一页
onMounted(fetchList)
</script>
