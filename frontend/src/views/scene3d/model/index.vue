<!--
  文件级说明：
  职责：模型资源管理页：查询、上传 glb/gltf/贴图、编辑元信息、预览与删除。
  数据来源：/api/scene3d/model/*（真实表 scene3d_model_resource + 附件表 wf_file）。
  说明：当前样例模型只有元信息（file_id=0），上传后才会生成可下载文件。
-->
<template>
  <div class="app-container scene3d-page">
    <!-- 页头 -->
    <div class="page-header">
      <div>
        <h2>模型资源</h2>
        <div class="sub">支持 .glb / .gltf / 贴图 · 单文件 ≤ 50MB · 共 {{ total }} 个</div>
      </div>
      <el-button v-perm="'scene3d:model:upload'" type="primary" :icon="Upload" @click="openUpload">上传模型</el-button>
    </div>

    <!-- 筛选 -->
    <el-card shadow="never" class="search-card">
      <el-form :model="query" inline @submit.prevent>
        <el-form-item label="模型名称">
          <el-input v-model="query.model_name" placeholder="请输入模型名称" clearable style="width: 180px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="模型类型">
          <el-select v-model="query.model_type" placeholder="全部" clearable style="width: 140px">
            <el-option label="3D 模型" value="model" />
            <el-option label="贴图" value="texture" />
            <el-option label="环境贴图" value="env" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 表格 -->
    <el-card shadow="never" class="table-card">
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无模型，请先上传">
        <el-table-column type="index" label="序号" width="70" align="center" />
        <el-table-column label="模型名称" prop="model_name" min-width="180" show-overflow-tooltip />
        <el-table-column label="模型编码" prop="model_code" min-width="140" />
        <el-table-column label="类型" width="100" align="center">
          <template #default="{ row }">
            <el-tag effect="plain" type="info">{{ typeText(row.model_type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="三角面" width="120" align="right">
          <template #default="{ row }">{{ Number(row.triangle_count || 0).toLocaleString() }}</template>
        </el-table-column>
        <el-table-column label="文件大小" width="120" align="right">
          <template #default="{ row }">{{ sizeText(row.file_size) }}</template>
        </el-table-column>
        <el-table-column label="文件" width="120" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.file_url" type="success">已上传</el-tag>
            <el-tag v-else type="warning">仅元信息</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'info'">{{ row.status === 1 ? '启用' : '停用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="创建时间" prop="create_time" width="170" />
        <el-table-column label="操作" width="190" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openPreview(row)">预览</el-button>
            <el-button v-perm="'scene3d:model:update'" link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button v-perm="'scene3d:model:delete'" link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination-wrap">
        <el-pagination background layout="total, sizes, prev, pager, next" :total="total"
          v-model:current-page="query.page" v-model:page-size="query.page_size" :page-sizes="[10, 20, 50, 100]" @change="fetchList" />
      </div>
    </el-card>

    <!-- 上传弹窗 -->
    <el-dialog v-model="uploadVisible" title="上传模型" width="560px" :close-on-click-modal="false" destroy-on-close>
      <el-form ref="uploadRef" :model="uploadForm" :rules="uploadRules" label-width="90px">
        <el-form-item label="模型文件" prop="file">
          <!-- 手动上传：选择文件后由提交按钮统一调用接口 -->
          <el-upload ref="fileRef" :auto-upload="false" :limit="1" :on-change="onFileChange" :on-remove="() => (uploadForm.file = null)" drag style="width: 100%">
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">拖拽文件到此处，或 <em>点击选择</em></div>
            <template #tip>
              <div class="el-upload__tip">支持 .glb/.gltf/.jpg/.png/.webp/.hdr，单文件不超过 50MB</div>
            </template>
          </el-upload>
        </el-form-item>
        <el-form-item label="模型名称" prop="model_name">
          <el-input v-model="uploadForm.model_name" placeholder="如：机柜_42U标准柜" maxlength="100" />
        </el-form-item>
        <el-form-item label="模型编码">
          <el-input v-model="uploadForm.model_code" placeholder="留空自动生成 MD-YYMMDDHHMMSS" maxlength="50" />
        </el-form-item>
        <el-form-item label="模型类型">
          <el-select v-model="uploadForm.model_type" style="width: 100%">
            <el-option label="3D 模型" value="model" />
            <el-option label="贴图" value="texture" />
            <el-option label="环境贴图" value="env" />
          </el-select>
        </el-form-item>
        <el-form-item label="三角面数">
          <el-input-number v-model="uploadForm.triangle_count" :min="0" :step="100" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="uploadForm.remark" type="textarea" :rows="2" maxlength="500" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="uploadVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitUpload">上传</el-button>
      </template>
    </el-dialog>

    <!-- 编辑弹窗 -->
    <el-dialog v-model="editVisible" title="编辑模型信息" width="520px" :close-on-click-modal="false" destroy-on-close>
      <el-form ref="editRef" :model="editForm" label-width="90px">
        <el-form-item label="模型名称" required>
          <el-input v-model="editForm.model_name" maxlength="100" />
        </el-form-item>
        <el-form-item label="模型类型">
          <el-select v-model="editForm.model_type" style="width: 100%">
            <el-option label="3D 模型" value="model" />
            <el-option label="贴图" value="texture" />
            <el-option label="环境贴图" value="env" />
          </el-select>
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="editForm.sort" :min="0" :max="999" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="editForm.remark" type="textarea" :rows="2" maxlength="500" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitEdit">保存</el-button>
      </template>
    </el-dialog>

    <!-- 预览弹窗 -->
    <el-dialog v-model="previewVisible" title="模型预览" width="560px">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="模型名称" :span="2">{{ preview.model_name }}</el-descriptions-item>
        <el-descriptions-item label="模型编码">{{ preview.model_code }}</el-descriptions-item>
        <el-descriptions-item label="类型">{{ typeText(preview.model_type) }}</el-descriptions-item>
        <el-descriptions-item label="三角面">{{ Number(preview.triangle_count || 0).toLocaleString() }}</el-descriptions-item>
        <el-descriptions-item label="文件大小">{{ sizeText(preview.file_size) }}</el-descriptions-item>
        <el-descriptions-item label="文件状态" :span="2">{{ preview.file_url ? '已上传，可下载' : '仅元信息（样例数据未附真实文件）' }}</el-descriptions-item>
      </el-descriptions>
      <!-- 预览占位：用令牌绘制的立方体示意图，无真实文件时不发请求 -->
      <div class="preview-box">
        <div class="cube"><span>CUBE</span></div>
        <div class="preview-meta">
          <p>当前项目以程序化几何体展示模型：机柜为长方体、传感器为球体。</p>
          <p>上传真实 glb 后，可在此基础上接入 GLTFLoader 做精确渲染。</p>
        </div>
      </div>
      <template #footer>
        <el-button @click="previewVisible = false">关闭</el-button>
        <el-button v-if="preview.file_url" type="primary" tag="a" :href="assetUrl(preview.file_url)" target="_blank">下载文件</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
// Vue API
import { ref, reactive, onMounted } from 'vue'
// 提示与确认
import { ElMessage, ElMessageBox } from 'element-plus'
// 图标
import { Upload, Search, Refresh, UploadFilled } from '@element-plus/icons-vue'
// 模型接口
import { modelApi } from '@/api/scene3d'

// 列表状态
const loading = ref(false) // 加载态
const saving = ref(false) // 提交态
const rows = ref([]) // 列表数据
const total = ref(0) // 总数
const query = reactive({ page: 1, page_size: 20, model_name: '', model_type: '' }) // 查询条件

// 上传状态
const uploadVisible = ref(false) // 上传弹窗
const uploadRef = ref(null) // 表单引用
const fileRef = ref(null) // 上传组件引用
const uploadForm = reactive({ file: null, model_name: '', model_code: '', model_type: 'model', triangle_count: 0, remark: '' }) // 上传字段

// 校验：文件与名称必填
const uploadRules = {
  file: [{ required: true, message: '请选择模型文件', trigger: 'change' }],
  model_name: [{ required: true, message: '请输入模型名称', trigger: 'blur' }]
}

// 编辑状态
const editVisible = ref(false) // 编辑弹窗
const editRef = ref(null) // 表单引用
const editForm = reactive({ id: null, model_name: '', model_type: 'model', sort: 0, remark: '' }) // 编辑字段

// 预览状态
const previewVisible = ref(false) // 预览弹窗
const preview = reactive({ model_name: '', model_code: '', model_type: '', triangle_count: 0, file_size: 0, file_url: null }) // 预览数据

// 类型文案映射
const typeText = type => ({ model: '3D 模型', texture: '贴图', env: '环境贴图' }[type] || type)

// 文件大小格式化
function sizeText(size) {
  const n = Number(size || 0) // 转数字
  if (n < 1024) return `${n} B` // 字节
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB` // KB
  return `${(n / 1024 / 1024).toFixed(1)} MB` // MB
}

// 资产地址：后端返回的是 /uploads 开头的相对路径
function assetUrl(url) {
  return url && url.startsWith('/') ? url : `/${url || ''}` // 统一补前导斜杠
}

// 拉列表
async function fetchList() {
  loading.value = true // 开启
  try {
    const res = await modelApi.list({ ...query }) // 请求
    rows.value = res.data.list || [] // 数据
    total.value = res.data.total || 0 // 总数
  } finally {
    loading.value = false // 关闭
  }
}

// 查询
function handleSearch() {
  query.page = 1 // 回第一页
  fetchList() // 请求
}

// 重置
function handleReset() {
  query.model_name = '' // 清空名称
  query.model_type = '' // 清空类型
  query.page = 1 // 回第一页
  fetchList() // 请求
}

// 打开上传
function openUpload() {
  Object.assign(uploadForm, { file: null, model_name: '', model_code: '', model_type: 'model', triangle_count: 0, remark: '' }) // 重置
  uploadVisible.value = true // 显示弹窗
}

// 文件选择：只保留一个文件
function onFileChange(file) {
  uploadForm.file = file.raw // 原生 File 对象
  if (!uploadForm.model_name) uploadForm.model_name = file.name.replace(/\.[^.]+$/, '') // 用文件名补默认名称
}

// 提交上传
async function submitUpload() {
  const valid = await uploadRef.value.validate().catch(() => false) // 校验
  if (!valid) return // 中断
  if (!uploadForm.file) {
    ElMessage.warning('请选择要上传的文件') // 兜底提示
    return
  }
  if (uploadForm.file.size > 50 * 1024 * 1024) {
    ElMessage.warning('文件超过 50MB 限制') // 前端预检
    return
  }
  saving.value = true // 防重复
  try {
    const fd = new FormData() // multipart 表单
    fd.append('file', uploadForm.file) // 文件
    fd.append('model_name', uploadForm.model_name) // 名称
    fd.append('model_code', uploadForm.model_code || '') // 编码可空
    fd.append('model_type', uploadForm.model_type) // 类型
    fd.append('triangle_count', uploadForm.triangle_count || 0) // 三角面
    fd.append('remark', uploadForm.remark || '') // 备注
    await modelApi.upload(fd) // 调用上传
    ElMessage.success('上传成功') // 提示
    uploadVisible.value = false // 关闭
    fetchList() // 刷新
  } finally {
    saving.value = false // 释放
  }
}

// 打开编辑
function openEdit(row) {
  Object.assign(editForm, { id: row.id, model_name: row.model_name, model_type: row.model_type, sort: row.sort || 0, remark: row.remark || '' }) // 回填
  editVisible.value = true // 打开
}

// 提交编辑
async function submitEdit() {
  if (!editForm.model_name) {
    ElMessage.warning('模型名称不能为空') // 简单校验
    return
  }
  saving.value = true // 防重复
  try {
    await modelApi.update(editForm.id, { model_name: editForm.model_name, model_type: editForm.model_type, sort: editForm.sort, remark: editForm.remark }) // 提交
    ElMessage.success('保存成功') // 提示
    editVisible.value = false // 关闭
    fetchList() // 刷新
  } finally {
    saving.value = false // 释放
  }
}

// 打开预览：补充 file_url 与访问地址
async function openPreview(row) {
  const res = await modelApi.preview(row.id) // 后端返回 file_url
  Object.assign(preview, { ...row, ...(res.data || {}) }) // 合并展示
  if (preview.file_url && !preview.file_url.startsWith('/uploads/')) {
    preview.file_url = `/uploads/${preview.file_url}` // 兼容相对路径
  }
  previewVisible.value = true // 显示
}

// 删除
async function handleDelete(row) {
  await ElMessageBox.confirm(`确认删除模型「${row.model_name}」？场景中引用该模型的对象将无法发布。`, '提示', { type: 'warning' }) // 二次确认
  await modelApi.remove([row.id]) // 逻辑删除
  ElMessage.success('删除成功') // 提示
  fetchList() // 刷新
}

// 首次加载
onMounted(fetchList)
</script>

<style scoped>
/* 页头 */
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: var(--app-space-4);
}
/* 标题 */
.page-header h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: var(--app-text-1);
}
/* 副标题 */
.sub {
  margin-top: 4px;
  font-size: 12px;
  color: var(--app-text-3);
}
/* 卡片圆角 */
.search-card {
  margin-bottom: var(--app-space-4);
  border-radius: var(--app-radius-lg);
}
.table-card {
  border-radius: var(--app-radius-lg);
}
/* 分页右对齐 */
.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: var(--app-space-4);
}
/* 预览占位区：立方体 + 说明 */
.preview-box {
  display: flex;
  gap: var(--app-space-4);
  margin-top: var(--app-space-4);
  padding: var(--app-space-4);
  border: 1px dashed var(--app-border);
  border-radius: var(--app-radius-md);
  background: var(--app-surface-2);
}
/* 立方体示意：纯 CSS 菱形，颜色走品牌令牌 */
.cube {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 96px;
  height: 96px;
  flex: 0 0 auto;
  border: 1px solid var(--app-border);
  border-radius: var(--app-radius-md);
  background: linear-gradient(135deg, color-mix(in srgb, var(--brand-primary) 22%, transparent), transparent);
  color: var(--app-text-2);
  font-size: 12px;
  font-weight: 600;
}
/* 预览说明文字 */
.preview-meta {
  font-size: 13px;
  line-height: 1.7;
  color: var(--app-text-2);
}
.preview-meta p {
  margin: 0 0 4px;
}
</style>
