<!--
  文件级说明：
  职责：附件回收站页。展示已（逻辑）删除的文件，支持按文件名查询、单条/批量恢复，以及单条/批量彻底删除。
  依赖：@/utils/request（/file/recycle/list、/file/recycle/restore/{id}、/file/recycle/hard_delete/{id}）、
        Element Plus 组件与图标、全局 v-perm 权限指令。
  被谁使用：由后端菜单配置 component='file/recycle/index' 生成动态路由后加载。
  说明：批量恢复/彻底删除目前是前端循环逐条调用接口；恢复是 POST，彻底删除是 DELETE。
-->
<template>
  <!-- 页面根容器：复用全局内边距与背景 -->
  <div class="app-container">
    <!-- 页头：标题与回收站当前总数 -->
    <div class="page-header">
      <div class="page-title-wrap">
        <!-- 页面标题 -->
        <h2>回收站</h2>
        <!-- 副标题：强调这里都是已删除文件，并展示总数 -->
        <div class="sub">已删除文件 · 共 {{ total }} 条</div>
      </div>
    </div>
    <!-- 查询卡片：shadow=never 保持扁平风格 -->
    <el-card shadow="never" class="search-card">
      <!-- 查询表单：inline 横向；@submit.prevent 阻止默认提交刷新页面 -->
      <el-form :model="query" inline @submit.prevent>
        <!-- 文件名：按原始文件名过滤回收站记录 -->
        <el-form-item label="文件名">
          <!-- 回车即查询；clearable 一键清空 -->
          <el-input v-model="query.original_name" placeholder="请输入文件名" clearable style="width: 180px" @keyup.enter="handleSearch" />
        </el-form-item>
        <!-- 查询/重置按钮 -->
        <el-form-item>
          <!-- 查询：回到第 1 页并按条件请求 -->
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <!-- 重置：清空条件后重新查询 -->
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 表格卡片：批量操作工具栏 + 回收站列表 + 分页 -->
    <el-card shadow="never" class="table-card">
      <!-- 卡片头部插槽：批量恢复与批量彻底删除 -->
      <template #header>
        <div class="card-header">
          <div class="card-actions">
            <!-- 批量恢复：success 色表示“可挽回”的善意操作；未勾选时禁用 -->
            <el-button v-perm="'file:restore'" type="success" plain :icon="RefreshRight" :disabled="!selection.length" @click="handleBatchRestore">批量恢复</el-button>
            <!-- 批量彻底删除：danger 色提示不可恢复；未勾选时禁用 -->
            <el-button v-perm="'file:hardDelete'" type="danger" plain :icon="Delete" :disabled="!selection.length" @click="handleBatchHardDelete">批量彻底删除</el-button>
          </div>
        </div>
      </template>
      <!-- 回收站表格：stripe 斑马纹；v-loading 遮罩；空态文案；勾选同步供批量操作 -->
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据" @selection-change="onSelectionChange">
        <!-- 序号列：当前页编号 -->
        <el-table-column type="index" label="序号" width="70" align="center" />
        <!-- 勾选列：批量恢复/彻底删除依赖它收集选中行 -->
        <el-table-column type="selection" width="50" />
        <!-- 原始文件名：原上传名，恢复后仍使用这个名字 -->
        <el-table-column label="原始文件名" prop="original_name" min-width="180" show-overflow-tooltip />
        <!-- 存储文件名：对象存储/磁盘中的实际文件名 -->
        <el-table-column label="存储文件名" prop="file_name" min-width="180" show-overflow-tooltip />
        <!-- 大小：由字节数格式化展示 -->
        <el-table-column label="大小" width="110">
          <template #default="{ row }">{{ formatSize(row.file_size) }}</template>
        </el-table-column>
        <!-- 存储类型：local/oss/cos/minio -->
        <el-table-column label="存储类型" prop="storage_type" width="100" />
        <!-- 业务类型：文件所属业务模块 -->
        <el-table-column label="业务类型" prop="biz_type" width="100" />
        <!-- 删除时间：进入回收站的时间；可据此判断清理时机 -->
        <el-table-column label="删除时间" prop="delete_time" width="170" />
        <!-- 操作列：固定在右侧 -->
        <el-table-column label="操作" width="200" fixed="right" class-name="op-col">
          <template #default="{ row }">
            <!-- 恢复：把该文件从回收站还原；受 file:restore 控制 -->
            <el-button v-perm="'file:restore'" link type="success" @click="handleRestore(row)">恢复</el-button>
            <!-- 彻底删除：删除记录与存储文件，不可恢复；受 file:hardDelete 控制 -->
            <el-button v-perm="'file:hardDelete'" link type="danger" @click="handleHardDelete(row)">彻底删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <!-- 分页容器：页码/页大小双向绑定 query，变化时重新请求 -->
      <div class="pagination-wrap">
        <el-pagination background layout="total, sizes, prev, pager, next, jumper"
          :total="total" v-model:current-page="query.page" v-model:page-size="query.page_size"
          :page-sizes="[10, 20, 50, 100]" @change="fetchList" />
      </div>
    </el-card>
  </div>
</template>

<script setup>
// Vue 基础能力：ref 维护加载/列表/总数/勾选；reactive 维护查询条件；onMounted 首次加载
import { ref, reactive, onMounted } from 'vue'
// Element Plus 消息提示与确认框：恢复/删除反馈与不可逆操作确认
import { ElMessage, ElMessageBox } from 'element-plus'
// 查询/重置/删除/恢复按钮图标
import { Search, Refresh, Delete, RefreshRight } from '@element-plus/icons-vue'
// 统一请求实例：自动鉴权、解包响应体并统一报错
import request from '@/utils/request'

// 列表加载态：控制表格遮罩
const loading = ref(false)
// 当前页回收站记录
const rows = ref([])
// 回收站总数，供分页器与页头统计
const total = ref(0)
// 当前勾选行，批量恢复/彻底删除依赖它
const selection = ref([])

// 查询条件初始值：仅文件名一个条件，page/page_size 与列表共用
const query_orig = { page: 1, page_size: 10, original_name: '' }
// 响应式查询对象：浅拷贝初始值，便于重置整体还原
const query = reactive({ ...query_orig })

// 按动作名映射接口路径，统一维护 /file/recycle 前缀
// 说明：restore 与 hard_delete 是单条操作，调用时需再拼 /{id}
function apiUrl(action) {
  const base = '/file/recycle'
  return {
    list: base + '/list',
    restore: base + '/restore',
    hard_delete: base + '/hard_delete'
  }[action]
}

// 把字节数格式化为易读大小：B/KB/MB/GB，保留两位小数
function formatSize(bytes) {
  // 空值兜底；0 字节是合法值，单独保留
  if (!bytes && bytes !== 0) return '-'
  // 小于 1KB 按字节显示
  if (bytes < 1024) return bytes + ' B'
  // 小于 1MB 按 KB 显示
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB'
  // 小于 1GB 按 MB 显示
  if (bytes < 1024 * 1024 * 1024) return (bytes / 1024 / 1024).toFixed(2) + ' MB'
  // 其余按 GB 显示
  return (bytes / 1024 / 1024 / 1024).toFixed(2) + ' GB'
}

// 拉取回收站列表：query 同时携带分页参数与文件名条件
async function fetchList() {
  loading.value = true
  try {
    const res = await request.get(apiUrl('list'), { params: query })
    // 兜底空数组/0，保证表格与分页稳定
    rows.value = res.data.list || []
    total.value = res.data.total || 0
  } finally {
    // 请求结束关闭遮罩
    loading.value = false
  }
}

// 查询：先回到第 1 页再请求
function handleSearch() { query.page = 1; fetchList() }
// 重置：还原查询条件后重新查询
function handleReset() { Object.assign(query, query_orig); handleSearch() }
// 勾选变化：同步选中行，批量按钮的禁用状态依赖它
function onSelectionChange(r) { selection.value = r }

// 单条恢复：确认后调用 POST /restore/{id}，成功后刷新列表
async function handleRestore(row) {
  await ElMessageBox.confirm('确定恢复该文件？', '提示', { type: 'warning' })
  // 恢复接口按 id 定位记录，无请求体
  await request.post(`${apiUrl('restore')}/${row.id}`)
  ElMessage.success('恢复成功')
  fetchList()
}

// 批量恢复：前端循环逐条调用恢复接口（后端未提供批量入参）
async function handleBatchRestore() {
  await ElMessageBox.confirm(`确定恢复选中的 ${selection.value.length} 个文件？`, '提示', { type: 'warning' })
  for (const r of selection.value) {
    // 串行 await，保证每条恢复请求依次完成；任一失败会中断循环并走统一错误提示
    await request.post(`${apiUrl('restore')}/${r.id}`)
  }
  ElMessage.success('批量恢复成功')
  fetchList()
}

// 单条彻底删除：不可恢复，因此确认框使用 error 类型强化警示
async function handleHardDelete(row) {
  await ElMessageBox.confirm('彻底删除不可恢复，确定执行？', '提示', { type: 'error' })
  // 彻底删除使用 DELETE /hard_delete/{id}，同时清理存储中的物理文件
  await request.delete(`${apiUrl('hard_delete')}/${row.id}`)
  ElMessage.success('已彻底删除')
  fetchList()
}

// 批量彻底删除：前端循环逐条调用彻底删除接口
async function handleBatchHardDelete() {
  await ElMessageBox.confirm(`彻底删除 ${selection.value.length} 个文件，不可恢复，确定执行？`, '提示', { type: 'error' })
  for (const r of selection.value) {
    // 串行删除，避免并发删除给后端存储造成压力
    await request.delete(`${apiUrl('hard_delete')}/${r.id}`)
  }
  ElMessage.success('已彻底删除')
  fetchList()
}

// 页面挂载后加载第一页回收站数据
onMounted(fetchList)
</script>
