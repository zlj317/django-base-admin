<!--
  备份记录页（/backup/record）：
  职责：查询并展示数据库备份记录，支持手动触发备份、下载备份文件、删除记录；不负责策略配置（见 backup/strategy）。
  依赖：@/utils/request 统一请求（自动带 token、统一错误提示与登录态处理）、Element Plus 组件与图标。
  样式：文件内无 style 块，版式全部来自全局 styles/index.css 的 .app-container/.page-header/.search-card/.table-card/.pagination-wrap。
  使用方：由后台路由挂载，作为"数据备份管理"菜单下的记录列表页。
-->
<template>
  <!-- 页面根容器：套用全局 .app-container 的内边距与进场动画，保证与其他列表页版式一致 -->
  <div class="app-container">
    <!-- 页面头部：左侧标题加副标题；副标题动态显示当前筛选结果的总数，便于快速感知数据量 -->
    <div class="page-header">
      <!-- 标题容器：负责主标题与副标题的纵向排布 -->
      <div class="page-title-wrap">
        <!-- 主标题，表明当前所处模块 -->
        <h2>数据备份管理</h2>
        <!-- 副标题：total 来自列表接口返回值，随查询条件与分页联动 -->
        <div class="sub">数据库备份记录 · 共 {{ total }} 条</div>
      </div>
    </div>

    <!-- 搜索区卡片：shadow="never" 去掉阴影保持扁平风格；.search-card 提供专用留白与表单项间距 -->
    <el-card shadow="never" class="search-card">
      <!-- 查询表单：inline 让筛选条件横向排列；@submit.prevent 阻止回车触发浏览器原生提交、避免整页刷新 -->
      <el-form :model="query" inline @submit.prevent>
        <!-- 备份名称筛选：模糊匹配；clearable 允许一键清空；回车直接触发查询，符合表单操作习惯 -->
        <el-form-item label="备份名称">
          <el-input v-model="query.backup_name" placeholder="请输入备份名称" clearable style="width: 170px" @keyup.enter="handleSearch" />
        </el-form-item>
        <!-- 备份类型筛选：绑定后端约定的类型码；clearable 后可置空表示"全部类型"不过滤 -->
        <el-form-item label="备份类型">
          <el-select v-model="query.backup_type" placeholder="全部" clearable style="width: 110px">
            <!-- 类型枚举：full=全量备份（整库完整导出）；incremental=增量备份（仅导出上次备份后的变更）；manual=手动备份（用户点击"手动备份"产生的一次性任务） -->
            <el-option label="全量" value="full" />
            <el-option label="增量" value="incremental" />
            <el-option label="手动" value="manual" />
          </el-select>
        </el-form-item>
        <!-- 备份状态筛选：用数字码与后端一致；默认 null 表示全部，故与 clearable 配合使用 -->
        <el-form-item label="状态">
          <el-select v-model="query.backup_status" placeholder="全部" clearable style="width: 120px">
            <!-- 状态枚举：0=备份中（任务已提交尚未产出文件）；1=成功；2=失败（需查看后端日志排查） -->
            <el-option label="备份中" :value="0" />
            <el-option label="成功" :value="1" />
            <el-option label="失败" :value="2" />
          </el-select>
        </el-form-item>
        <!-- 操作按钮区：查询会重置到第一页，重置会还原全部筛选条件后重新查询 -->
        <el-form-item>
          <!-- 主按钮：立即按当前条件查询 -->
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <!-- 次按钮：清空筛选条件并重新查询，避免用户逐项手动删除 -->
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 列表区卡片：.table-card 统一表头背景与内边距，分页贴底展示 -->
    <el-card shadow="never" class="table-card">
      <!-- 卡片头部插槽：集中放置新增/批量类操作按钮，与列表内容分层 -->
      <template #header>
        <!-- 头部容器：左右布局，此处只有左侧操作区 -->
        <div class="card-header">
          <!-- 操作按钮组：手动备份会立即向后端提交一个一次性备份任务 -->
          <div class="card-actions">
            <!-- 手动备份按钮：确认后调用 /backup/record/manual，不依赖定时策略 -->
            <el-button type="primary" :icon="Plus" @click="handleManualBackup">手动备份</el-button>
          </div>
        </div>
      </template>
      <!-- 数据表格：v-loading 在请求期间显示遮罩；stripe 斑马纹；@selection-change 同步勾选行到 selection -->
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据" @selection-change="onSelectionChange">
        <!-- 序号列：仅前端渲染行号，避免后端额外返回 -->
        <el-table-column type="index" label="序号" width="70" align="center" />
        <!-- 多选列：当前页面未提供批量操作，但保留勾选能力（selection 已与表格联动） -->
        <el-table-column type="selection" width="50" />
        <!-- 备份名称列：min-width 自适应，超长文本用 tooltip 悬浮显示，避免撑破表格 -->
        <el-table-column label="备份名称" prop="backup_name" min-width="180" show-overflow-tooltip />
        <!-- 备份类型列：按类型码渲染不同颜色的标签，便于快速区分备份性质 -->
        <el-table-column label="备份类型" width="90">
          <template #default="{ row }">
            <!-- full=全量备份：默认蓝色标签（主类型） -->
            <el-tag v-if="row.backup_type==='full'" size="small">全量</el-tag>
            <!-- incremental=增量备份：绿色表示轻量、日常高频执行 -->
            <el-tag v-else-if="row.backup_type==='incremental'" size="small" type="success">增量</el-tag>
            <!-- manual=手动备份：橙色提示非计划内操作 -->
            <el-tag v-else-if="row.backup_type==='manual'" size="small" type="warning">手动</el-tag>
            <!-- 兜底：后端新增未识别的类型时原样显示，避免空白单元格 -->
            <span v-else>{{ row.backup_type }}</span>
          </template>
        </el-table-column>
        <!-- 数据库列：展示被备份的目标库名 -->
        <el-table-column label="数据库" prop="db_name" width="130" />
        <!-- 文件大小列：后端存字节数，这里格式化为带单位的可读值 -->
        <el-table-column label="文件大小" width="100">
          <template #default="{ row }">{{ formatSize(row.file_size) }}</template>
        </el-table-column>
        <!-- 加密列：备份文件是否加密存储，加密是敏感数据备份的常见合规要求 -->
        <el-table-column label="加密" width="70" align="center">
          <template #default="{ row }">
            <!-- encrypt_flag=1 表示已加密，用警示色提醒下载后需解密；其他值视为未加密 -->
            <el-tag v-if="row.encrypt_flag===1" size="small" type="warning">是</el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <!-- 状态列：用颜色区分任务生命周期，失败态用危险色便于发现 -->
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <!-- 0=备份中：任务进行中，此时下载可能不可用 -->
            <el-tag v-if="row.backup_status===0" size="small">备份中</el-tag>
            <!-- 1=成功：文件已生成，可下载 -->
            <el-tag v-else-if="row.backup_status===1" size="small" type="success">成功</el-tag>
            <!-- 2=失败：需要排查后端日志 -->
            <el-tag v-else-if="row.backup_status===2" size="small" type="danger">失败</el-tag>
            <!-- 兜底：未知状态不显示错误标签 -->
            <span v-else>-</span>
          </template>
        </el-table-column>
        <!-- 备份时间列：由后端返回的格式化时间串直接展示 -->
        <el-table-column label="备份时间" prop="backup_time" width="170" />
        <!-- 耗时列：任务执行秒数；?? 保证 0 也正常显示，仅空值显示短横线 -->
        <el-table-column label="耗时(秒)" prop="cost_time" width="90">
          <template #default="{ row }">{{ row.cost_time ?? '-' }}</template>
        </el-table-column>
        <!-- 操作列：fixed="right" 横向滚动时固定在右侧；.op-col 控制按钮间距 -->
        <el-table-column label="操作" width="180" fixed="right" class-name="op-col">
          <template #default="{ row }">
            <!-- 下载：以 blob 方式取回备份文件并触发浏览器保存 -->
            <el-button link type="primary" @click="handleDownload(row)">下载</el-button>
            <!-- 删除：二次确认后按 id 删除单条记录（通常同时删除磁盘文件） -->
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <!-- 分页容器：.pagination-wrap 负责右对齐与上下留白 -->
      <div class="pagination-wrap">
        <!-- 分页器：background 使用块状页码；layout 依次为总数、每页条数、上一页、页码、下一页、跳页器；@change 在页码或每页条数变化时统一刷新列表 -->
        <el-pagination background layout="total, sizes, prev, pager, next, jumper"
          :total="total" v-model:current-page="query.page" v-model:page-size="query.page_size"
          :page-sizes="[10, 20, 50, 100]" @change="fetchList" />
      </div>
    </el-card>
  </div>
</template>

<script setup>
// 组合式 API：ref 声明响应式基本值，reactive 声明响应式对象（查询条件/表单），onMounted 挂载后首次拉取数据
import { ref, reactive, onMounted } from 'vue'
// Element Plus 消息与确认框：统一成功提示、删除/备份前的二次确认
import { ElMessage, ElMessageBox } from 'element-plus'
// 图标：Search 查询、Refresh 重置、Plus 手动备份
import { Search, Refresh, Plus } from '@element-plus/icons-vue'
// 统一 axios 实例：baseURL=/api、自动带 token、统一错误提示（见 utils/request.js）
import request from '@/utils/request'

// 列表加载态：请求期间为 true，驱动表格遮罩，防止重复点击触发并发请求造成数据错乱
const loading = ref(false)
// 当前页数据：直接绑定到 el-table，仅保存接口返回的本页记录
const rows = ref([])
// 记录总数：供分页器计算页数，同时用于页面副标题展示
const total = ref(0)
// 已勾选行：由表格 selection-change 事件回写，便于将来扩展批量操作
const selection = ref([])

// 查询条件初值：单独抽出作为"重置"的还原基准；page/page_size 也纳入重置，保证回到第一页
// backup_name/backup_type 用空串表示不筛选；backup_status 用 null 表示全部状态（0 是有效状态值，不能用 falsy 判断）
const query_orig = { page: 1, page_size: 10, backup_name: '', backup_type: '', backup_status: null }
// 查询条件的响应式副本：用展开拷贝避免直接引用初值对象被改动
const query = reactive({ ...query_orig })

// 接口基址：备份记录相关接口统一前缀，便于集中修改路由
const apiBase = '/backup/record'

// 字节数转可读体积：后端 file_size 为字节，展示层按 1024 进制换算到 B/KB/MB/GB
function formatSize(bytes) {
  // 空值/0 直接显示短横线，避免出现 "0.0 B" 这类误导性信息
  if (!bytes) return '-'
  // 单位阶梯：最大到 GB，足够覆盖单库备份的常见量级
  const units = ['B', 'KB', 'MB', 'GB']
  let i = 0
  // 显式转数字，防止后端返回字符串导致除法结果异常
  let val = Number(bytes)
  // 循环降阶，直到小于 1024 或到达最大单位
  while (val >= 1024 && i < units.length - 1) { val /= 1024; i++ }
  // 保留一位小数并拼接单位，兼顾精度与可读性
  return val.toFixed(1) + ' ' + units[i]
}

// 拉取列表：携带当前查询条件（含分页）请求后端，返回 { list, total }
async function fetchList() {
  // 进入请求先开启 loading，避免用户看到旧数据误以为已更新
  loading.value = true
  try {
    // GET /backup/record/list：query 作为查询参数，空串/null 由后端忽略
    const res = await request.get(apiBase + '/list', { params: query })
    // 兜底空数组：后端无数据时表格正常显示 empty-text，不报错
    rows.value = res.data.list || []
    // 兜底 0：保证分页器总数始终是数字
    total.value = res.data.total || 0
  // 无论成功失败都关闭 loading，防止异常后遮罩一直不消失
  } finally { loading.value = false }
}

// 查询：条件变化必须回到第一页，否则可能停在超出新结果集的页码而显示空列表
function handleSearch() { query.page = 1; fetchList() }
// 重置：把查询条件还原为初值（含分页）后再查询，避免残留筛选条件影响结果
function handleReset() { Object.assign(query, query_orig); handleSearch() }
// 勾选变化：Element Plus 传入当前选中行数组，直接同步到 selection
function onSelectionChange(r) { selection.value = r }

// 手动备份：先二次确认（备份会占用数据库资源），确认后提交任务并刷新列表看到"备份中"状态
async function handleManualBackup() {
  // 警告型确认框：用户取消会抛异常，交由调用方（无 try）自然中断后续请求
  await ElMessageBox.confirm('确定立即执行手动备份？', '提示', { type: 'warning' })
  // POST 提交手动备份任务：后端异步执行，接口立即返回
  await request.post(apiBase + '/manual')
  // 提示已提交而非已完成，避免用户误以为备份文件已就绪
  ElMessage.success('备份任务已提交'); fetchList()
}

// 下载备份文件：后端返回二进制流，前端用临时 <a> 触发浏览器另存
async function handleDownload(row) {
  try {
    // responseType: 'blob' 让 axios 保留二进制；request 拦截器对 blob 会直接返回原始 response
    const res = await request.get(`${apiBase}/download/${row.id}`, { responseType: 'blob' })
    // 生成临时对象 URL，把 blob 包装成可点击的链接
    const url = URL.createObjectURL(res.data)
    // 动态创建并点击隐藏链接：无需在本页放常驻下载元素
    const a = document.createElement('a')
    // 指定下载地址与文件名（缺省回退为 backup，避免文件名异常）
    a.href = url; a.download = row.backup_name || 'backup'
    // 触发下载后立即释放对象 URL，防止内存泄漏
    a.click(); URL.revokeObjectURL(url)
  } catch (e) { /* handled */ }
}

// 删除单条记录：二次确认后按 ids 数组提交，后端统一走批量删除接口
async function handleDelete(row) {
  // 删除不可恢复，用警告型确认框拦截误操作
  await ElMessageBox.confirm('确定删除该备份记录？', '提示', { type: 'warning' })
  // DELETE 用 data 传体：与后端约定的 records 删除形式保持一致
  await request.delete(apiBase + '/delete', { data: { ids: [row.id] } })
  // 成功后提示并刷新列表，使总数与分页同步变化
  ElMessage.success('删除成功'); fetchList()
}

// 首次挂载即拉取第一页数据，用户进入页面即可看到记录
onMounted(fetchList)
</script>
