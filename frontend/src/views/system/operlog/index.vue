<template>
  <!-- 操作日志页：审计系统内的写操作记录，便于追溯谁在何时调用了哪个接口、耗时多久、参数与返回是什么。
       职责：按操作人/模块/类型过滤、分页查询、批量删除、清空全部日志，以及单条详情查看。
       依赖：utils/request 统一请求、store/auth 的权限指令、Element Plus 表格/弹窗/描述列表。 -->
  <div class="app-container">
    <!-- 页面头部：标题 + 副标题，说明本页是审计用途 -->
    <div class="page-header">
      <div class="page-title-wrap">
        <h2>操作日志</h2>
        <div class="sub">系统操作行为审计</div>
      </div>
    </div>
    <!-- 查询栏：按操作人员、模块名称、操作类型三个维度过滤 -->
    <el-card shadow="never" class="search-card">
      <!-- inline 横向排列；@submit.prevent 阻止原生表单提交导致页面刷新 -->
      <el-form inline @submit.prevent>
        <!-- 操作人员：登录用户名，回车触发查询 -->
        <el-form-item label="操作人员">
          <el-input v-model="query.oper_user" placeholder="请输入操作人员" clearable style="width: 170px" @keyup.enter="handleSearch" />
        </el-form-item>
        <!-- 模块名称：业务模块标识（如“部门管理”），回车触发查询 -->
        <el-form-item label="模块名称">
          <el-input v-model="query.module_name" placeholder="请输入模块名称" clearable style="width: 170px" @keyup.enter="handleSearch" />
        </el-form-item>
        <!-- 操作类型：如新增/修改/删除等文本，后端按模糊匹配处理，回车触发查询 -->
        <el-form-item label="操作类型">
          <el-input v-model="query.oper_type" placeholder="请输入操作类型" clearable style="width: 170px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item>
          <!-- 查询：handleSearch 先把页码归 1，再按当前条件请求 -->
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <!-- 重置：清空三个条件后重新查询 -->
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 日志列表卡片：工具栏 + 表格 + 分页 -->
    <el-card shadow="never" class="table-card">
      <!-- 工具栏：批量删除（未勾选时禁用）与清空日志（高风险操作，单独确认） -->
      <div class="toolbar">
        <el-button v-perm="'system:operlog:delete'" type="danger" plain :icon="Delete" :disabled="!selection.length" @click="handleBatchDelete">批量删除</el-button>
        <el-button v-perm="'system:operlog:delete'" type="warning" plain :icon="Brush" @click="handleClear">清空日志</el-button>
      </div>

      <!-- 日志表格：selection-change 回写勾选行；stripe 斑马纹便于横向阅读长行 -->
      <el-table stripe empty-text="暂无数据" v-loading="loading" :data="list" @selection-change="onSelectionChange">
        <!-- 序号列：按当前页渲染顺序递增 -->
        <el-table-column type="index" label="序号" width="70" align="center" />
        <!-- 多选列：服务于批量删除 -->
        <el-table-column type="selection" width="50" />
        <!-- 操作人员：触发该操作的登录用户 -->
        <el-table-column label="操作人员" prop="oper_user" min-width="110" show-overflow-tooltip />
        <!-- 模块名称：操作所属的业务模块，便于按业务维度筛选 -->
        <el-table-column label="模块名称" prop="module_name" min-width="120" show-overflow-tooltip />
        <!-- 操作类型：后端记录的文本，空值用 '-' 占位 -->
        <el-table-column label="操作类型" prop="oper_type" min-width="100">
          <template #default="{ row }">{{ row.oper_type || '-' }}</template>
        </el-table-column>
        <!-- 请求地址：实际调用的后端接口路径，排查问题时的主要线索 -->
        <el-table-column label="请求地址" prop="request_url" min-width="200" show-overflow-tooltip />
        <!-- 耗时：接口响应毫秒数，用于定位慢接口 -->
        <el-table-column label="耗时(ms)" prop="cost_time" width="90" align="center" />
        <!-- 操作时间：后端已格式化，前端直接展示 -->
        <el-table-column label="操作时间" prop="oper_time" width="170" />
        <!-- 操作列：固定在右侧，只提供详情查看，不在此处做删除，避免误操作 -->
        <el-table-column label="操作" width="80" fixed="right">
          <template #default="{ row }">
            <!-- 详情：把当前行赋给 detail 并打开弹窗（列表接口通常已返回全部字段，无需再请求详情接口） -->
            <el-button link type="primary" @click="openDetail(row)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页条：页大小变化时回到第一页；翻页直接按当前条件请求 -->
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

    <!-- 详情弹窗：展示单条日志的概要信息与请求参数、返回结果（宽 700px 以便完整展示较长的请求体） -->
    <el-dialog v-model="detailVisible" title="操作日志详情" width="700px" destroy-on-close>
      <!-- 概要信息：两列布局 + 边框；接口地址与操作时间内容较长，各占整行(span=2) -->
      <el-descriptions :column="2" border size="small">
        <el-descriptions-item label="操作人员">{{ detail.oper_user || '-' }}</el-descriptions-item>
        <el-descriptions-item label="模块名称">{{ detail.module_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="操作类型">{{ detail.oper_type || '-' }}</el-descriptions-item>
        <el-descriptions-item label="耗时">{{ detail.cost_time }} ms</el-descriptions-item>
        <el-descriptions-item label="请求地址" :span="2">{{ detail.request_url || '-' }}</el-descriptions-item>
        <el-descriptions-item label="操作时间" :span="2">{{ detail.oper_time || '-' }}</el-descriptions-item>
      </el-descriptions>
      <!-- 请求参数块：调用 pretty 格式化后放入 pre，保留原始缩进，便于阅读 JSON -->
      <div class="detail-block">
        <div class="detail-label">请求参数</div>
        <pre class="plain-pre">{{ pretty(detail.request_param) }}</pre>
      </div>
      <!-- 返回结果块：同上；非 JSON 内容会原样输出 -->
      <div class="detail-block">
        <div class="detail-label">返回结果</div>
        <pre class="plain-pre">{{ pretty(detail.response_result) }}</pre>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
// 组合式 API：ref 管理列表/分页/弹窗状态，reactive 管理查询条件
import { onMounted, reactive, ref } from 'vue'
// 消息提示与确认框：删除/清空反馈与高风险操作确认
import { ElMessage, ElMessageBox } from 'element-plus'
// 图标按需引入：查询、重置、删除、清空
import { Search, Refresh, Delete, Brush } from '@element-plus/icons-vue'
// 统一请求实例：封装 baseURL、token、错误提示与 401 跳转
import request from '@/utils/request'

// 列表加载态：驱动表格 v-loading
const loading = ref(false)
// 日志列表数据：当前页记录（详情弹窗直接复用行数据）
const list = ref([])
// 日志总数：分页组件据此计算页数
const total = ref(0)
// 当前页码
const page = ref(1)
// 每页条数
const pageSize = ref(10)
// 查询条件：三个字段与后端接口参数同名，请求时整体展开
const query = reactive({ oper_user: '', module_name: '', oper_type: '' })
// 已勾选行：批量删除的数据来源，空数组时按钮禁用
const selection = ref([])

// ---------- 列表 ----------
// 拉取操作日志：分页 + 查询条件；loading 统一在 finally 收起
async function fetchList() {
  loading.value = true
  try {
    const res = await request.get('/system/operlog/list', {
      params: { page: page.value, page_size: pageSize.value, ...query }
    })
    // 后端约定 data = { list, total }
    list.value = res.data.list || []
    total.value = res.data.total || 0
  } finally {
    loading.value = false
  }
}

// 条件查询：先回到第一页再请求，避免新条件下列表页码越界
function handleSearch() {
  page.value = 1
  fetchList()
}

// 重置查询：清空三个条件后复用查询逻辑
function handleReset() {
  query.oper_user = ''
  query.module_name = ''
  query.oper_type = ''
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
// 详情弹窗显隐：只负责展示，不涉及编辑
const detailVisible = ref(false)
// 当前查看的日志行：直接复用列表行数据，避免额外详情请求
const detail = ref({})

// 打开详情：保存行数据并显示弹窗
function openDetail(row) {
  detail.value = row
  detailVisible.value = true
}

// 格式化请求参数/返回结果：空值返回 '-' 占位；能解析成 JSON 就按 2 空格缩进美化，
// 解析失败（如普通字符串、表单串）则原样转字符串展示，保证任何内容都有可读输出
function pretty(text) {
  if (text === null || text === undefined || text === '') return '-'
  try {
    return JSON.stringify(JSON.parse(text), null, 2)
  } catch (e) {
    return String(text)
  }
}

// ---------- 删除/清空 ----------
// 批量删除：确认文案带选中数量，按 selection 映射出的 id 数组提交，删除后刷新列表
async function handleBatchDelete() {
  await ElMessageBox.confirm(`确定删除选中的 ${selection.value.length} 条操作日志吗？`, '提示', { type: 'warning' })
  await request.delete('/system/operlog/delete', { data: { ids: selection.value.map(r => r.id) } })
  ElMessage.success('删除成功')
  fetchList()
}

// 清空全部日志：不可恢复的高风险操作，确认框用“警告”标题强调后果，确认后 POST 清空接口并刷新
async function handleClear() {
  await ElMessageBox.confirm('确定清空全部操作日志吗？此操作不可恢复！', '警告', { type: 'warning' })
  await request.post('/system/operlog/clear')
  ElMessage.success('清空成功')
  fetchList()
}

// 页面挂载后加载第一页操作日志
onMounted(fetchList)
</script>

<style scoped>
/* 详情信息块：与上方描述列表之间留出间距，分隔“概要信息”和“请求/返回内容”两个区域 */
.detail-block {
  margin-top: 14px;
}

/* 详情小标题：用灰色小号字标注“请求参数/返回结果”，弱化层级但保留可读性 */
.detail-label {
  margin-bottom: 6px;
  color: #909399;
  font-size: 13px;
}
</style>
