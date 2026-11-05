<!--
  文件级说明：
  职责：代码生成（数据表）列表页。展示已导入的数据表及其生成配置摘要，提供按表名查询、导入数据表、
        跳转生成配置、代码预览、ZIP 下载、单条/批量删除。
  依赖：@/utils/request（/gen/table/*、/gen/db/* 接口，已内置 token 与统一错误提示）、
        @/utils/download 的 saveBlob（把后端返回的二进制 ZIP 落成文件）、
        @/components/CodePreviewDialog.vue（代码预览弹窗，通过组件 ref 的 open(id) 打开）、
        Element Plus 组件与图标、全局 v-perm 权限指令。
  被谁使用：由后端菜单配置 component='gen/table/index' 生成动态路由后加载。
  说明：主列表与“导入数据表”弹窗各自维护分页/查询状态，互不影响；列表只保存导入结果，不展示表结构细节。
-->
<template>
  <!-- 页面根容器：复用全局 app-container 的页面内边距与背景 -->
  <div class="app-container">
    <!-- 页头：标题 + 副标题，点明本页面是数据表导入与代码生成入口 -->
    <div class="page-header">
      <div class="page-title-wrap">
        <!-- 页面标题 -->
        <h2>代码生成</h2>
        <!-- 副标题：说明列表数据的来源与用途 -->
        <div class="sub">数据表导入与代码生成配置</div>
      </div>
    </div>
    <!-- 查询栏：按表名筛选已导入的数据表；shadow=never 去掉投影，保持与系统内其他列表页一致的扁平风格 -->
    <el-card shadow="never" class="search-card">
      <!-- inline 让表单项横向排布；@submit.prevent 阻止浏览器默认表单提交造成页面刷新 -->
      <el-form inline @submit.prevent>
        <!-- 表名筛选条件：对应后端 table_name，做模糊匹配 -->
        <el-form-item label="表名称">
          <!-- clearable 提供一键清空；固定 200px 宽度保证查询栏排版稳定；回车等同点击“查询” -->
          <el-input v-model="query.table_name" placeholder="请输入表名称" clearable style="width: 200px" @keyup.enter="handleSearch" />
        </el-form-item>
        <!-- 操作按钮组：查询会重置到第一页；重置会清空条件后再查询 -->
        <el-form-item>
          <!-- 主按钮：以主题色强调最常用的查询动作 -->
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <!-- 次要按钮：清空表名条件并回到第一页 -->
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 表格卡片：承载工具栏、数据列表与分页 -->
    <el-card shadow="never" class="table-card">
      <!-- 工具栏：导入与批量删除两个全局操作 -->
      <div class="toolbar">
        <!-- 导入入口：v-perm 控制按钮显示，无 gen:table:import 权限的用户不可见；打开后会按需拉取可导入的数据表 -->
        <el-button v-perm="'gen:table:import'" type="primary" :icon="Upload" @click="openImport">导入数据表</el-button>
        <!-- 批量删除：plain 降低危险操作权重；未勾选任何行时禁用，避免空提交 -->
        <el-button v-perm="'gen:table:delete'" type="danger" plain :icon="Delete" :disabled="!selection.length" @click="handleBatchDelete">批量删除</el-button>
      </div>

      <!-- 数据表格：stripe 斑马纹提升可读性；empty-text 指定空态文案；v-loading 控制请求遮罩；
           selection-change 同步勾选行，供批量删除使用 -->
      <el-table stripe empty-text="暂无数据" v-loading="loading" :data="list" @selection-change="onSelectionChange">
        <!-- 序号列：按当前页自动编号，便于人工核对 -->
        <el-table-column type="index" label="序号" width="70" align="center" />
        <!-- 勾选列：批量删除依赖它收集选中行 -->
        <el-table-column type="selection" width="50" />
        <!-- 表名：数据表在数据库中的真实名称，生成代码与接口都以此为基础 -->
        <el-table-column label="表名" prop="table_name" min-width="160" show-overflow-tooltip />
        <!-- 表注释：取自数据库表注释；show-overflow-tooltip 用悬浮提示展示被截断的完整内容 -->
        <el-table-column label="表注释" prop="table_comment" min-width="130" show-overflow-tooltip>
          <!-- 作用域插槽：后端可能返回空注释，用 '-' 占位避免出现空白单元格 -->
          <template #default="{ row }">{{ row.table_comment || '-' }}</template>
        </el-table-column>
        <!-- 模块名：代码生成使用的英文模块标识（如 biz_order），决定目录与命名 -->
        <el-table-column label="模块名" prop="module_name" min-width="110" show-overflow-tooltip>
          <!-- 空值占位，保证表格视觉整齐 -->
          <template #default="{ row }">{{ row.module_name || '-' }}</template>
        </el-table-column>
        <!-- 模块中文：用于生成菜单名与页面标题 -->
        <el-table-column label="模块中文" prop="module_comment" min-width="110" show-overflow-tooltip>
          <!-- 空值占位 -->
          <template #default="{ row }">{{ row.module_comment || '-' }}</template>
        </el-table-column>
        <!-- 路由前缀：生成后端接口与前端请求时统一使用的前缀 -->
        <el-table-column label="路由前缀" prop="url_prefix" min-width="120" show-overflow-tooltip>
          <!-- 空值占位 -->
          <template #default="{ row }">{{ row.url_prefix || '-' }}</template>
        </el-table-column>
        <!-- 字段数：该表的列数量，作为配置是否完整的粗略参考 -->
        <el-table-column label="字段数" prop="column_count" width="80" align="center" />
        <!-- 创建时间：记录导入/配置生成的时间 -->
        <el-table-column label="创建时间" prop="create_time" width="170" />
        <!-- 操作列：fixed=right 固定在右侧，横向滚动时仍可操作 -->
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <!-- 配置：跳转生成配置页，可编辑类名、模块、字段表单项等；受 gen:table:update 控制 -->
            <el-button v-perm="'gen:table:update'" link type="primary" @click="goEdit(row)">配置</el-button>
            <!-- 预览：调用预览弹窗组件的 open(表id)，按需请求生成后的代码文本；受 gen:table:preview 控制 -->
            <el-button v-perm="'gen:table:preview'" link type="primary" @click="previewRef.open(row.id)">预览</el-button>
            <!-- 下载：以 success 色区分“产出物”类操作，下载生成代码 ZIP；受 gen:table:download 控制 -->
            <el-button v-perm="'gen:table:download'" link type="success" @click="handleDownload(row)">下载</el-button>
            <!-- 删除：删除该表的生成配置（不删数据库表），danger 色提示风险；受 gen:table:delete 控制 -->
            <el-button v-perm="'gen:table:delete'" link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页容器：右对齐或统一间距由全局 .pagination-wrap 控制 -->
      <div class="pagination-wrap">
        <!-- 分页器：双向绑定当前页与每页条数，二者变化都会触发对应回调重新请求 -->
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

    <!-- 导入数据表弹窗：从数据库中选择尚未导入的表，加入代码生成列表；destroy-on-close 关闭即销毁内容，避免残留上一次的勾选；
         宽度 760px 可容纳表名/表注释/创建时间/状态四列 -->
    <el-dialog v-model="importVisible" title="导入数据表" width="760px" destroy-on-close>
      <!-- 弹窗内独立查询表单：只影响弹窗里的“可导入表”列表，不影响主列表 -->
      <el-form inline @submit.prevent>
        <!-- 表名过滤：复用 importQuery.table_name，回车直接触发弹窗内查询 -->
        <el-form-item label="表名称">
          <!-- 宽度与主列表保持一致；clearable 便于快速清空条件 -->
          <el-input v-model="importQuery.table_name" placeholder="请输入表名称" clearable style="width: 200px" @keyup.enter="fetchImportTables" />
        </el-form-item>
        <el-form-item>
          <!-- 查询按钮：按当前条件重新拉取可导入数据表（第 1 页由用户手动切换或重新打开时重置） -->
          <el-button type="primary" :icon="Search" @click="fetchImportTables">查询</el-button>
        </el-form-item>
      </el-form>

      <!-- 可导入表列表：ref 用于回填跨页勾选状态；max-height 让弹窗高度可控，内部滚动 -->
      <el-table
        ref="importTableRef"
        v-loading="importLoading"
        :data="importList"
        max-height="380"
        @selection-change="onImportSelectionChange"
      >
        <!-- 勾选列：已导入的表置灰不可选（selectable 返回 false），防止重复导入 -->
        <el-table-column type="selection" width="50" :selectable="row => !row.imported" />
        <!-- 表名：数据库中的真实表名，提交导入时以此为准 -->
        <el-table-column label="表名" prop="table_name" min-width="170" show-overflow-tooltip />
        <!-- 表注释：帮助用户识别表用途，空值用 '-' 占位 -->
        <el-table-column label="表注释" prop="table_comment" min-width="150" show-overflow-tooltip>
          <template #default="{ row }">{{ row.table_comment || '-' }}</template>
        </el-table-column>
        <!-- 创建时间：表的创建时间，辅助判断新旧 -->
        <el-table-column label="创建时间" prop="create_time" width="170" />
        <!-- 状态列：直观区分该表是否已导入，颜色与文案双向对应 -->
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <!-- 已导入用灰色 info 标签，未导入用绿色 success 标签 -->
            <el-tag :type="row.imported ? 'info' : 'success'" size="small">
              {{ row.imported ? '已导入' : '未导入' }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>

      <!-- 弹窗分页：独立的状态，切换每页条数时先回到第 1 页再请求 -->
      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="importPage"
          v-model:page-size="importPageSize"
          :total="importTotal"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          @size-change="importPage = 1; fetchImportTables()"
          @current-change="fetchImportTables"
        />
      </div>

      <!-- 底部操作区：取消直接关闭弹窗；导入按钮显示已选数量，无选中时禁用且请求中显示 loading -->
      <template #footer>
        <el-button @click="importVisible = false">取 消</el-button>
        <el-button type="primary" :loading="importing" :disabled="!importSelection.length" @click="handleImport">
          导入（{{ importSelection.length }}）
        </el-button>
      </template>
    </el-dialog>

    <!-- 代码预览弹窗：组件内部自行请求代码内容，页面只通过 ref.open(表id) 触发；
         放在页面内而非表格行内，避免每行都创建一份弹窗实例 -->
    <CodePreviewDialog ref="previewRef" />
  </div>
</template>

<script setup>
// Vue 基础能力：onMounted 首次加载列表；reactive 维护查询条件；ref 维护加载态、分页与弹窗状态
import { onMounted, reactive, ref } from 'vue'
// 路由：用于“配置”按钮跳转到生成配置页
import { useRouter } from 'vue-router'
// Element Plus 消息提示与确认框：操作成功提示、删除前二次确认
import { ElMessage, ElMessageBox } from 'element-plus'
// 查询/重置/导入/删除按钮的图标
import { Search, Refresh, Upload, Delete } from '@element-plus/icons-vue'
// 统一请求实例：自动携带 token、统一解包响应体并处理错误提示
import request from '@/utils/request'
// 下载工具：把 blob 响应保存为本地文件（本页用于保存代码 ZIP）
import { saveBlob } from '@/utils/download'
// 代码预览弹窗组件：通过 ref 调用其 open(表id) 按需拉取并展示生成代码
import CodePreviewDialog from '@/components/CodePreviewDialog.vue'

// 路由器实例：goEdit 中用于编程式跳转
const router = useRouter()

// 列表请求加载态：控制表格 v-loading 遮罩，避免用户误以为无数据
const loading = ref(false)
// 当前页的表格数据（后端返回的 list 字段）
const list = ref([])
// 总记录数，供分页器计算总页数
const total = ref(0)
// 当前页码：查询/重置/切换每页条数时都会回到第 1 页
const page = ref(1)
// 每页条数，默认 10 条
const pageSize = ref(10)
// 查询条件：仅表名一个条件，用 reactive 便于表单双向绑定
const query = reactive({ table_name: '' })
// 当前勾选的行，批量删除按钮的可用状态与提交数据都依赖它
const selection = ref([])
// 代码预览弹窗组件实例：调用其 open(id) 打开预览
const previewRef = ref()

// ---------- 列表 ----------
// 拉取代码生成列表：分页参数与查询条件一并提交，响应拦截器已解包为 { code, msg, data }
async function fetchList() {
  // 发请求前先打开 loading，让用户立即得到反馈
  loading.value = true
  try {
    const res = await request.get('/gen/table/list', {
      // ...query 展开表名条件；为空时由后端忽略该条件
      params: { page: page.value, page_size: pageSize.value, ...query }
    })
    // 后端未返回 list 时兜底为空数组，避免表格渲染报错
    list.value = res.data.list || []
    // total 同样兜底为 0
    total.value = res.data.total || 0
  } finally {
    // 无论成功失败都关闭 loading（错误提示由请求拦截器统一处理）
    loading.value = false
  }
}

// 点击查询：回到第 1 页再请求，避免当前页码超出新结果的总页数
function handleSearch() {
  page.value = 1
  fetchList()
}

// 点击重置：清空表名条件并重新查询（复用 handleSearch 回到第 1 页）
function handleReset() {
  query.table_name = ''
  handleSearch()
}

// 切换每页条数：页大小变化后原页码可能越界，因此回到第 1 页重新请求
function handleSizeChange() {
  page.value = 1
  fetchList()
}

// 表格勾选变化：把选中行同步到 selection，供批量删除使用
function onSelectionChange(rows) {
  selection.value = rows
}

// 进入生成配置页：用记录 id 拼出隐藏路由 /gen/edit/:id
function goEdit(row) {
  router.push(`/gen/edit/${row.id}`)
}

// ---------- 导入数据表 ----------
// 导入弹窗显隐
const importVisible = ref(false)
// 弹窗内可导入表列表的加载态
const importLoading = ref(false)
// 导入请求进行中，用于禁用按钮并显示 loading，防止重复提交
const importing = ref(false)
// 弹窗内可导入的数据表列表
const importList = ref([])
// 弹窗内列表总记录数
const importTotal = ref(0)
// 弹窗内当前页码（与主列表独立）
const importPage = ref(1)
// 弹窗内每页条数（与主列表独立）
const importPageSize = ref(10)
// 弹窗内表名查询条件
const importQuery = reactive({ table_name: '' })
// 弹窗内已勾选的数据表，跨页保留
const importSelection = ref([])
// 弹窗内表格实例，用于程序化回填勾选状态
const importTableRef = ref()

// 打开导入弹窗：重置关键字/页码/勾选，再按默认条件拉取可导入表
function openImport() {
  importQuery.table_name = ''
  importPage.value = 1
  importSelection.value = []
  importVisible.value = true
  fetchImportTables()
}

// 拉取数据库中可导入的数据表（分页）；已导入的表会带 imported 标记，由表格决定是否可选
async function fetchImportTables() {
  importLoading.value = true
  try {
    const res = await request.get('/gen/db/tables', {
      params: { page: importPage.value, page_size: importPageSize.value, table_name: importQuery.table_name }
    })
    // 兜底空数组，保证表格可正常渲染
    importList.value = res.data.list || []
    importTotal.value = res.data.total || 0
    // 保留已勾选且仍在当前页的数据
    nextTickSelection()
  } finally {
    // 请求结束关闭遮罩，失败提示由拦截器统一处理
    importLoading.value = false
  }
}

// 回填勾选状态：翻页/查询后表格会重新渲染，需要把仍在当前页的已勾选表恢复为选中
// 用微任务延后执行，确保表格已经拿到新数据
function nextTickSelection() {
  Promise.resolve().then(() => {
    // 表格实例尚未挂载时不处理，避免空引用报错
    if (!importTableRef.value) return
    importList.value.forEach(row => {
      // 以 table_name 作为唯一键匹配跨页保留的勾选记录
      if (importSelection.value.some(item => item.table_name === row.table_name)) {
        importTableRef.value.toggleRowSelection(row, true)
      }
    })
  })
}

// 弹窗表格勾选变化：同步到 importSelection，提交导入与按钮计数都依赖它
function onImportSelectionChange(rows) {
  importSelection.value = rows
}

// 提交导入：把勾选表的表名提交给后端，成功后关闭弹窗并刷新主列表
async function handleImport() {
  // 只取表名，避免把整行展示字段（如 imported）传给后端
  const tables = importSelection.value.map(r => r.table_name)
  // 双重保险：按钮虽已禁用，但函数层仍要拦截空提交
  if (!tables.length) {
    ElMessage.warning('请选择要导入的数据表')
    return
  }
  importing.value = true
  try {
    await request.post('/gen/db/import', { tables })
    // 用实际提交数量提示，便于用户确认
    ElMessage.success(`成功导入 ${tables.length} 张表`)
    importVisible.value = false
    // 导入会新增记录，刷新主列表让用户看到最新数据
    fetchList()
  } finally {
    // 成功或失败都要恢复按钮状态
    importing.value = false
  }
}

// ---------- 下载 ----------
// 下载生成代码：后端以 ZIP 流返回，前端转存为文件
async function handleDownload(row) {
  // responseType=blob 让 axios 返回原始二进制响应（响应拦截器对 blob 直接透传）；
  // 代码生成可能较慢，单独放宽超时到 120 秒
  const res = await request.get(`/gen/table/${row.id}/download`, { responseType: 'blob', timeout: 120000 })
  // 文件名优先用模块名，其次类名/表名，保证解压前就能识别归属
  saveBlob(res.data, `${row.module_name || row.class_name || row.table_name}.zip`)
  ElMessage.success('下载成功')
}

// ---------- 删除 ----------
// 单条删除：先二次确认，再提交该记录 id
async function handleDelete(row) {
  // 确认框点取消会 reject，后续删除与提示都不会执行（由 Element Plus 控制流程）
  await ElMessageBox.confirm(`确定删除表「${row.table_name}」的生成配置吗？`, '提示', { type: 'warning' })
  // 删除接口用 DELETE 的 data 字段传 ids，符合后端批量删除的统一入参
  await request.delete('/gen/table/delete', { data: { ids: [row.id] } })
  ElMessage.success('删除成功')
  // 删除后刷新当前页；若当前页已空，后端会返回空列表
  fetchList()
}

// 批量删除：把勾选行的 id 汇总后一次性提交
async function handleBatchDelete() {
  await ElMessageBox.confirm(`确定删除选中的 ${selection.value.length} 张表的生成配置吗？`, '提示', { type: 'warning' })
  // map 只取 id，避免把表格中的展示字段提交给后端
  await request.delete('/gen/table/delete', { data: { ids: selection.value.map(r => r.id) } })
  ElMessage.success('删除成功')
  fetchList()
}

// 页面挂载后立即加载第一页列表
onMounted(fetchList)
</script>
