<!--
  文件级说明：
  职责：附件列表页。按文件名/业务类型/存储类型筛选附件，支持上传（可多选）、预览（跳转后端返回的临时地址）、
        下载、单条与批量删除。
  依赖：@/utils/request（/file/list、/file/upload、/file/preview_url/{id}、/file/download/{id}、/file/delete）、
        Element Plus 组件与图标、全局 v-perm 权限指令。
  被谁使用：由后端菜单配置 component='file/index' 生成动态路由后加载。
  说明：上传使用原生 input[type=file] 而不是 el-upload，逐个文件串行提交，便于逐个反馈成功/失败。
-->
<template>
  <!-- 页面根容器：复用全局内边距与背景 -->
  <div class="app-container">
    <!-- 页头：标题与统计信息；total 随列表查询实时更新 -->
    <div class="page-header">
      <div class="page-title-wrap">
        <!-- 页面标题 -->
        <h2>附件列表</h2>
        <!-- 副标题：展示当前筛选条件下的附件总数 -->
        <div class="sub">全部附件 · 共 {{ total }} 条</div>
      </div>
    </div>
    <!-- 查询卡片：shadow=never 保持系统列表页的扁平风格 -->
    <el-card shadow="never" class="search-card">
      <!-- 查询表单：model 绑定 query；inline 横向排列；@submit.prevent 阻止默认提交刷新页面 -->
      <el-form :model="query" inline @submit.prevent>
        <!-- 文件名：按上传时的原始文件名做模糊查询 -->
        <el-form-item label="文件名">
          <!-- 回车即查询；clearable 一键清空；固定宽度保证查询栏对齐 -->
          <el-input v-model="query.original_name" placeholder="请输入文件名" clearable style="width: 180px" @keyup.enter="handleSearch" />
        </el-form-item>
        <!-- 业务类型：附件归属的业务模块标识，用于按业务归档查询 -->
        <el-form-item label="业务类型">
          <!-- 同样是模糊查询，回车即可触发 -->
          <el-input v-model="query.biz_type" placeholder="请输入业务类型" clearable style="width: 150px" @keyup.enter="handleSearch" />
        </el-form-item>
        <!-- 存储类型：按附件实际落盘的存储介质筛选 -->
        <el-form-item label="存储类型">
          <!-- 下拉选择；clearable 后为空表示不限制存储类型 -->
          <el-select v-model="query.storage_type" placeholder="全部" clearable style="width: 130px">
            <!-- 本地磁盘 -->
            <el-option label="本地" value="local" />
            <!-- 阿里云 OSS -->
            <el-option label="OSS" value="oss" />
            <!-- 腾讯云 COS -->
            <el-option label="COS" value="cos" />
            <!-- 自建 MinIO -->
            <el-option label="MinIO" value="minio" />
          </el-select>
        </el-form-item>
        <!-- 操作按钮：查询、重置 -->
        <el-form-item>
          <!-- 查询：回到第 1 页并按当前条件请求 -->
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <!-- 重置：清空全部条件后重新查询 -->
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 表格卡片：工具栏 + 列表 + 分页 -->
    <el-card shadow="never" class="table-card">
      <!-- 卡片头部插槽：放置上传与批量删除按钮 -->
      <template #header>
        <div class="card-header">
          <div class="card-actions">
            <!-- 上传按钮：v-perm 控制权限；点击不直接提交，而是转发点击隐藏的 file input -->
            <el-button v-perm="'file:upload'" type="primary" :icon="Upload" @click="triggerUpload">上传</el-button>
            <!-- 原生文件输入：display:none 隐藏；multiple 允许一次选多个文件；change 后逐个上传 -->
            <input ref="fileInputRef" type="file" style="display:none" @change="handleFileChange" multiple />
            <!-- 批量删除：危险操作使用 plain；未勾选时禁用，避免无意义请求 -->
            <el-button v-perm="'file:delete'" type="danger" plain :icon="Delete" :disabled="!selection.length" @click="handleBatchDelete">批量删除</el-button>
          </div>
        </div>
      </template>
      <!-- 附件表格：stripe 斑马纹；v-loading 遮罩；无数据时显示 empty-text；勾选变化同步到 selection -->
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据" @selection-change="onSelectionChange">
        <!-- 序号列：当前页内编号 -->
        <el-table-column type="index" label="序号" width="70" align="center" />
        <!-- 勾选列：批量删除依赖它收集选中行 -->
        <el-table-column type="selection" width="50" />
        <!-- 原始文件名：用户上传时的文件名，下载时也优先用它作为保存名 -->
        <el-table-column label="原始文件名" prop="original_name" min-width="180" show-overflow-tooltip />
        <!-- 存储文件名：落盘后的实际文件名（通常带时间戳/随机串，防止重名覆盖） -->
        <el-table-column label="存储文件名" prop="file_name" min-width="180" show-overflow-tooltip />
        <!-- 文件大小：后端返回字节数，用 formatSize 转成 B/KB/MB/GB 便于阅读 -->
        <el-table-column label="文件大小" width="110">
          <template #default="{ row }">{{ formatSize(row.file_size) }}</template>
        </el-table-column>
        <!-- 存储类型：local/oss/cos/minio，标识文件实际存放位置 -->
        <el-table-column label="存储类型" prop="storage_type" width="100" />
        <!-- 业务类型：附件归属的业务模块，便于按业务检索 -->
        <el-table-column label="业务类型" prop="biz_type" width="100" />
        <!-- 业务ID：关联的业务数据主键，用于反查某条业务记录挂载的附件 -->
        <el-table-column label="业务ID" prop="biz_id" width="90" />
        <!-- 上传用户ID：记录上传人，便于审计 -->
        <el-table-column label="上传用户ID" prop="upload_user_id" width="110" />
        <!-- 创建时间：附件入库时间 -->
        <el-table-column label="创建时间" prop="create_time" width="170" />
        <!-- 操作列：固定在右侧；class-name=op-col 供全局样式统一操作列排版 -->
        <el-table-column label="操作" width="240" fixed="right" class-name="op-col">
          <template #default="{ row }">
            <!-- 预览：请求后端临时预览地址后新窗口打开；图片/PDF 等可直接在浏览器查看 -->
            <el-button link type="primary" @click="handlePreview(row)">预览</el-button>
            <!-- 下载：以 blob 方式请求文件流并触发浏览器保存，避免直接暴露存储地址 -->
            <el-button link type="primary" @click="handleDownload(row)">下载</el-button>
            <!-- 删除：受 file:delete 控制；通常为逻辑删除，文件会进入回收站 -->
            <el-button v-perm="'file:delete'" link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <!-- 分页容器：统一由全局 .pagination-wrap 控制位置与间距 -->
      <div class="pagination-wrap">
        <!-- 分页器：background 带背景块；支持总数/页大小/上一页/页码/下一页/跳页；
             页码与页大小直接双向绑定到 query，变化时统一触发 fetchList -->
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
// Element Plus 消息提示与确认框：上传/删除反馈、删除前确认
import { ElMessage, ElMessageBox } from 'element-plus'
// 查询/重置/删除/上传按钮图标
import { Search, Refresh, Delete, Upload } from '@element-plus/icons-vue'
// 统一请求实例：自动鉴权、解包响应体并统一报错
import request from '@/utils/request'

// 列表加载态：控制表格遮罩
const loading = ref(false)
// 当前页附件数据
const rows = ref([])
// 附件总数，供分页器与页头统计使用
const total = ref(0)
// 当前勾选行，批量删除依赖它
const selection = ref([])
// 隐藏的文件输入框引用：上传按钮通过它唤起系统文件选择框
const fileInputRef = ref(null)

// 查询条件初始值：page/page_size 与列表共用；storage_type 默认 null 表示不限
// 单独抽成常量，便于“重置”时整体还原
const query_orig = { page: 1, page_size: 10, original_name: '', biz_type: '', storage_type: null }
// 响应式查询对象：直接从初始值浅拷贝，避免改动常量
const query = reactive({ ...query_orig })

// 按动作名映射接口路径，避免在多个函数里重复拼写 '/file' 前缀
function apiUrl(action) {
  const base = '/file'
  return {
    list: base + '/list',
    delete: base + '/delete',
    upload: base + '/upload'
  }[action]
}

// 把字节数格式化为易读大小：B/KB/MB/GB，保留两位小数
function formatSize(bytes) {
  // 空值兜底（注意 0 字节是合法值，需单独保留），展示 '-' 而不是 '0 B'
  if (!bytes && bytes !== 0) return '-'
  // 小于 1KB 直接按字节显示
  if (bytes < 1024) return bytes + ' B'
  // 小于 1MB 按 KB 显示
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB'
  // 小于 1GB 按 MB 显示
  if (bytes < 1024 * 1024 * 1024) return (bytes / 1024 / 1024).toFixed(2) + ' MB'
  // 其余按 GB 显示
  return (bytes / 1024 / 1024 / 1024).toFixed(2) + ' GB'
}

// 拉取附件列表：query 同时包含分页参数与筛选条件，直接作为 URL 查询串提交
async function fetchList() {
  loading.value = true
  try {
    const res = await request.get(apiUrl('list'), { params: query })
    // 后端异常返回时兜底，保证表格与分页组件拿到稳定结构
    rows.value = res.data.list || []
    total.value = res.data.total || 0
  } finally {
    // 请求结束关闭遮罩
    loading.value = false
  }
}

// 查询：先回到第 1 页，避免旧页码超出新结果范围
function handleSearch() { query.page = 1; fetchList() }
// 重置：把查询对象还原为初始值，再按默认条件查询
function handleReset() { Object.assign(query, query_orig); handleSearch() }

// 触发文件选择：点击隐藏的 input，浏览器会弹出系统文件选择框
function triggerUpload() { fileInputRef.value.click() }

// 文件选择后逐个上传：串行提交便于逐个给出成功/失败提示，也避免并发占用带宽
async function handleFileChange(e) {
  // FileList 转数组；取消选择时 files 为空
  const files = Array.from(e.target.files || [])
  if (!files.length) return
  for (const f of files) {
    // 每个文件单独一个 FormData，字段名 file 与后端接收参数对应
    const fd = new FormData()
    fd.append('file', f)
    try {
      // multipart/form-data 由浏览器自动补 boundary，这里显式声明便于后端识别
      await request.post(apiUrl('upload'), fd, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      ElMessage.success(`上传成功: ${f.name}`)
    } catch (err) {
      // 单个文件失败不影响后续文件继续上传；具体错误已由拦截器提示
      ElMessage.error(`上传失败: ${f.name}`)
    }
  }
  // 清空 input 的值，保证再次选择同一文件也能触发 change
  e.target.value = ''
  // 上传完成后刷新列表，展示新增附件
  fetchList()
}

// 预览：后端返回临时访问地址（如预签名 URL），前端只负责新窗口打开
async function handlePreview(row) {
  try {
    const res = await request.get(`/file/preview_url/${row.id}`)
    if (res.data && res.data.url) {
      // _blank 新标签页打开，避免离开列表页
      window.open(res.data.url, '_blank')
    } else {
      // 后端未生成地址（如文件缺失/存储不支持预览）时给出明确提示
      ElMessage.warning('暂无预览地址')
    }
  } catch (e) { /* 错误提示由请求拦截器统一处理 */ }
}

// 下载：以 blob 形式取回文件流，再用临时 a 标签触发浏览器保存
async function handleDownload(row) {
  // responseType=blob 让 axios 保留二进制（拦截器对 blob 直接透传原始响应）
  const resp = await request.get(`/file/download/${row.id}`, { responseType: 'blob' })
  // 生成临时对象 URL 指向内存中的 blob
  const url = window.URL.createObjectURL(new Blob([resp.data]))
  // 动态创建 a 标签模拟点击下载
  const a = document.createElement('a')
  a.href = url
  // 保存名优先原始文件名，其次存储名，最后使用通用名
  a.download = row.original_name || row.file_name || 'download'
  document.body.appendChild(a)
  a.click()
  // 下载触发后立即移除节点，避免污染 DOM
  a.remove()
  // 释放对象 URL，防止内存泄漏
  window.URL.revokeObjectURL(url)
}

// 表格勾选变化：同步到 selection，驱动批量删除按钮状态
function onSelectionChange(r) { selection.value = r }

// 单条删除：二次确认后提交 id 数组（后端统一按批量接口处理）
async function handleDelete(row) {
  await ElMessageBox.confirm('确定删除该文件？', '提示', { type: 'warning' })
  // 删除接口用 DELETE 的 data 传 ids，与批量删除保持同一入参格式
  await request.delete(apiUrl('delete'), { data: { ids: [row.id] } })
  ElMessage.success('删除成功')
  fetchList()
}

// 批量删除：汇总勾选行 id 后一次提交
async function handleBatchDelete() {
  await ElMessageBox.confirm(`确定删除选中的 ${selection.value.length} 个文件？`, '提示', { type: 'warning' })
  await request.delete(apiUrl('delete'), { data: { ids: selection.value.map(r => r.id) } })
  ElMessage.success('批量删除成功')
  fetchList()
}

// 页面挂载后加载第一页附件列表
onMounted(fetchList)
</script>
