<template>
  <!-- 登录日志页：审计账号登录记录（成功/失败），用于排查异常登录与账号安全问题。
       职责：按用户名与登录状态过滤、分页查询、批量删除、清空全部日志、查看单条详情。
       依赖：utils/request 统一请求、store/auth 的权限指令、Element Plus 表格/弹窗/描述列表。 -->
  <div class="app-container">
    <!-- 页面头部：标题 + 副标题，说明本页的审计用途 -->
    <div class="page-header">
      <div class="page-title-wrap">
        <h2>登录日志</h2>
        <div class="sub">账号登录记录审计</div>
      </div>
    </div>
    <!-- 查询栏：用户名 + 登录状态下拉过滤 -->
    <el-card shadow="never" class="search-card">
      <!-- inline 横向排列；@submit.prevent 阻止原生表单提交导致页面刷新 -->
      <el-form inline @submit.prevent>
        <!-- 用户名：登录账号，回车触发查询 -->
        <el-form-item label="用户名">
          <el-input v-model="query.username" placeholder="请输入用户名" clearable style="width: 180px" @keyup.enter="handleSearch" />
        </el-form-item>
        <!-- 登录状态：0 成功 / 1 失败；clearable 清空后为 null，接口不传该条件即表示全部 -->
        <el-form-item label="登录状态">
          <el-select v-model="query.status" placeholder="全部" clearable style="width: 140px">
            <el-option label="成功" :value="0" />
            <el-option label="失败" :value="1" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <!-- 查询：handleSearch 先把页码归 1，再按当前条件请求 -->
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <!-- 重置：清空用户名与状态后重新查询 -->
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 日志列表卡片：工具栏 + 表格 + 分页 -->
    <el-card shadow="never" class="table-card">
      <!-- 工具栏：批量删除（未勾选时禁用）与清空日志（不可恢复，单独确认） -->
      <div class="toolbar">
        <el-button v-perm="'system:loginlog:delete'" type="danger" plain :icon="Delete" :disabled="!selection.length" @click="handleBatchDelete">批量删除</el-button>
        <el-button v-perm="'system:loginlog:delete'" type="warning" plain :icon="Brush" @click="handleClear">清空日志</el-button>
      </div>

      <!-- 登录日志表格：selection-change 回写勾选行；stripe 斑马纹提升可读性 -->
      <el-table stripe empty-text="暂无数据" v-loading="loading" :data="list" @selection-change="onSelectionChange">
        <!-- 序号列：按当前页渲染顺序递增 -->
        <el-table-column type="index" label="序号" width="70" align="center" />
        <!-- 多选列：服务于批量删除 -->
        <el-table-column type="selection" width="50" />
        <!-- 用户名：登录账号，min-width 保证常见账号名不被截断 -->
        <el-table-column label="用户名" prop="username" min-width="110" show-overflow-tooltip />
        <!-- 登录 IP：空值用 '-' 占位，超长时 tooltip 展示 -->
        <el-table-column label="登录IP" prop="ip" min-width="130" show-overflow-tooltip>
          <template #default="{ row }">{{ row.ip || '-' }}</template>
        </el-table-column>
        <!-- 浏览器：后端解析的 UA 摘要，空值占位 -->
        <el-table-column label="浏览器" prop="browser" min-width="130" show-overflow-tooltip>
          <template #default="{ row }">{{ row.browser || '-' }}</template>
        </el-table-column>
        <!-- 登录状态：0 成功（success 绿）/ 非 0 失败（danger 红），仅展示 -->
        <el-table-column label="登录状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 0 ? 'success' : 'danger'" size="small">
              {{ row.status === 0 ? '成功' : '失败' }}
            </el-tag>
          </template>
        </el-table-column>
        <!-- 提示消息：失败原因等后端文案，超长时 tooltip 展示 -->
        <el-table-column label="提示消息" prop="msg" min-width="160" show-overflow-tooltip />
        <!-- 登录时间：后端已格式化，前端直接展示 -->
        <el-table-column label="登录时间" prop="login_time" width="170" />
        <!-- 操作列：固定在右侧，仅提供详情查看 -->
        <el-table-column label="操作" width="80" fixed="right">
          <template #default="{ row }">
            <!-- 详情：直接复用当前行数据，打开弹窗展示完整字段 -->
            <el-button link type="primary" @click="openDetail(row)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页条：页大小变化回归第一页；翻页按当前条件请求 -->
      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="fetchList"
        />
      </div>
    </el-card>

    <!-- 详情弹窗：单列描述列表展示登录记录全部字段，宽度 520px 足够容纳短文本 -->
    <el-dialog v-model="detailVisible" title="登录日志详情" width="520px" destroy-on-close>
      <!-- 单列布局便于竖向阅读；每项都做空值兜底 -->
      <el-descriptions :column="1" border size="small">
        <el-descriptions-item label="用户名">{{ detail.username || '-' }}</el-descriptions-item>
        <el-descriptions-item label="登录IP">{{ detail.ip || '-' }}</el-descriptions-item>
        <el-descriptions-item label="浏览器">{{ detail.browser || '-' }}</el-descriptions-item>
        <!-- 登录状态：与列表保持同一判定口径（0 成功，其余失败） -->
        <el-descriptions-item label="登录状态">{{ detail.status === 0 ? '成功' : '失败' }}</el-descriptions-item>
        <el-descriptions-item label="提示消息">{{ detail.msg || '-' }}</el-descriptions-item>
        <el-descriptions-item label="登录时间">{{ detail.login_time || '-' }}</el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup>
// 组合式 API：ref 管理列表/分页/弹窗状态，reactive 管理查询条件
import { onMounted, reactive, ref } from 'vue'
// 消息提示与确认框：删除/清空反馈与不可恢复操作确认
import { ElMessage, ElMessageBox } from 'element-plus'
// 图标按需引入：查询、重置、删除、清空
import { Search, Refresh, Delete, Brush } from '@element-plus/icons-vue'
// 统一请求实例：封装 baseURL、token、错误提示与 401 跳转
import request from '@/utils/request'

// 列表加载态：驱动表格 v-loading
const loading = ref(false)
// 登录日志列表：当前页记录，详情弹窗直接复用行数据
const list = ref([])
// 日志总数：分页组件据此计算页数
const total = ref(0)
// 当前页码
const page = ref(1)
// 每页条数
const pageSize = ref(10)
// 查询条件：status 为 null 表示不按状态过滤（下拉清空后的默认值）
const query = reactive({ username: '', status: null })
// 已勾选行：批量删除的数据来源，空数组时按钮禁用
const selection = ref([])

// ---------- 列表 ----------
// 拉取登录日志：分页 + 查询条件；loading 在 finally 收起，保证请求失败也能解除遮罩
async function fetchList() {
  loading.value = true
  try {
    const res = await request.get('/system/loginlog/list', {
      params: { page: page.value, page_size: pageSize.value, ...query }
    })
    // 后端约定 data = { list, total }
    list.value = res.data.list || []
    total.value = res.data.total || 0
  } finally {
    loading.value = false
  }
}

// 条件查询：先回到第一页再请求，避免新条件下页码越界
function handleSearch() {
  page.value = 1
  fetchList()
}

// 重置查询：清空用户名并把状态恢复为 null（即“全部”），再复用查询逻辑
function handleReset() {
  query.username = ''
  query.status = null
  handleSearch()
}

// 每页条数变化：页码归 1 后重新请求
function handleSizeChange() {
  page.value = 1
  fetchList()
}

// 表格勾选变化：写回 selection，供批量删除取 id
function onSelectionChange(rows) {
  selection.value = rows
}

// ---------- 详情 ----------
// 详情弹窗显隐：只读展示，不涉及编辑
const detailVisible = ref(false)
// 当前查看的登录日志行：复用列表行数据，避免额外详情请求
const detail = ref({})

// 打开详情：保存行数据并显示弹窗
function openDetail(row) {
  detail.value = row
  detailVisible.value = true
}

// ---------- 删除/清空 ----------
// 批量删除：确认文案带选中数量，按 selection 映射出的 id 数组提交，删除后刷新列表
async function handleBatchDelete() {
  await ElMessageBox.confirm(`确定删除选中的 ${selection.value.length} 条登录日志吗？`, '提示', { type: 'warning' })
  await request.delete('/system/loginlog/delete', { data: { ids: selection.value.map(r => r.id) } })
  ElMessage.success('删除成功')
  fetchList()
}

// 清空全部登录日志：不可恢复的高风险操作，确认框用“警告”标题强调后果，确认后 POST 清空接口并刷新
async function handleClear() {
  await ElMessageBox.confirm('确定清空全部登录日志吗？此操作不可恢复！', '警告', { type: 'warning' })
  await request.post('/system/loginlog/clear')
  ElMessage.success('清空成功')
  fetchList()
}

// 页面挂载后加载第一页登录日志
onMounted(fetchList)
</script>
