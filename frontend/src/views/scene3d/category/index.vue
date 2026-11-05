<!--
  文件级说明：
  职责：3D 可视化「场景分类」管理页，提供分类的查询、新增、编辑、启停与删除。
  依赖：@/api/scene3d（统一接口）、Element Plus 表单/表格、v-perm 按钮权限指令。
  数据来源：/api/scene3d/category/list（真实表 scene3d_category）。
-->
<template>
  <!-- 页面容器：统一内边距 -->
  <div class="app-container scene3d-page">
    <!-- 页头：标题与统计 -->
    <div class="page-header">
      <div class="page-title-wrap">
        <h2>场景分类</h2>
        <div class="sub">3D 场景分类 · 共 {{ total }} 个</div>
      </div>
      <!-- 新增按钮：按按钮权限控制 -->
      <el-button v-perm="'scene3d:category:create'" type="primary" :icon="Plus" @click="openCreate">新增分类</el-button>
    </div>

    <!-- 搜索区：名称模糊 + 状态筛选 -->
    <el-card shadow="never" class="search-card">
      <el-form :model="query" inline @submit.prevent>
        <el-form-item label="分类名称">
          <el-input v-model="query.category_name" placeholder="请输入名称" clearable style="width: 180px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="query.status" placeholder="全部" clearable style="width: 120px">
            <el-option label="启用" :value="1" />
            <el-option label="停用" :value="0" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 数据表 -->
    <el-card shadow="never" class="table-card">
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无分类，请先新增">
        <el-table-column type="index" label="序号" width="70" align="center" />
        <el-table-column label="分类名称" prop="category_name" min-width="160" show-overflow-tooltip />
        <el-table-column label="分类编码" prop="category_code" min-width="140" show-overflow-tooltip />
        <el-table-column label="排序" prop="sort" width="80" align="center" />
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <!-- 状态标签：颜色取语义令牌 -->
            <el-tag :type="row.status === 1 ? 'success' : 'info'" effect="light">{{ row.status === 1 ? '启用' : '停用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="备注" prop="remark" min-width="180" show-overflow-tooltip />
        <el-table-column label="创建时间" prop="create_time" width="170" />
        <el-table-column label="操作" width="220" fixed="right" class-name="op-col">
          <template #default="{ row }">
            <el-button v-perm="'scene3d:category:update'" link type="primary" @click="openEdit(row)">编辑</el-button>
            <!-- 启停：直接切换状态，避免进入编辑弹窗 -->
            <el-button v-perm="'scene3d:category:update'" link :type="row.status === 1 ? 'warning' : 'success'" @click="toggleStatus(row)">{{ row.status === 1 ? '停用' : '启用' }}</el-button>
            <el-button v-perm="'scene3d:category:delete'" link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <!-- 分页 -->
      <div class="pagination-wrap">
        <el-pagination background layout="total, sizes, prev, pager, next, jumper" :total="total"
          v-model:current-page="query.page" v-model:page-size="query.page_size"
          :page-sizes="[10, 20, 50, 100]" @change="fetchList" />
      </div>
    </el-card>

    <!-- 新增/编辑弹窗 -->
    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑分类' : '新增分类'" width="520px" :close-on-click-modal="false" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="分类名称" prop="category_name">
          <el-input v-model="form.category_name" placeholder="如：机房 / 档案库房" maxlength="100" />
        </el-form-item>
        <el-form-item label="分类编码" prop="category_code">
          <el-input v-model="form.category_code" placeholder="如：ROOM_SERVER，保存后不建议修改" maxlength="50" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="form.sort" :min="0" :max="999" controls-position="right" />
        </el-form-item>
        <el-form-item label="状态">
          <el-radio-group v-model="form.status">
            <el-radio :value="1">启用</el-radio>
            <el-radio :value="0">停用</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" :rows="3" maxlength="500" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitForm">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
// Vue API：响应式状态与生命周期
import { ref, reactive, onMounted } from 'vue'
// 提示与二次确认
import { ElMessage, ElMessageBox } from 'element-plus'
// 按钮图标
import { Plus, Search, Refresh } from '@element-plus/icons-vue'
// 分类接口
import { categoryApi } from '@/api/scene3d'

// 列表状态
const loading = ref(false) // 表格加载态
const saving = ref(false) // 提交加载态
const rows = ref([]) // 当前页数据
const total = ref(0) // 总条数
const query = reactive({ page: 1, page_size: 20, category_name: '', status: '' }) // 查询条件

// 弹窗状态
const dialogVisible = ref(false) // 弹窗显隐
const formRef = ref(null) // 表单引用
const form = reactive({ id: null, category_name: '', category_code: '', sort: 0, status: 1, remark: '' }) // 表单数据

// 表单校验：名称与编码必填，编码建议大写字母/下划线
const rules = {
  category_name: [{ required: true, message: '请输入分类名称', trigger: 'blur' }],
  category_code: [
    { required: true, message: '请输入分类编码', trigger: 'blur' },
    { pattern: /^[A-Za-z0-9_]+$/, message: '编码仅支持字母、数字与下划线', trigger: 'blur' }
  ]
}

// 拉取列表
async function fetchList() {
  loading.value = true // 开启加载
  try {
    const res = await categoryApi.list({ ...query }) // 携带分页与筛选
    rows.value = res.data.list || [] // 当前页
    total.value = res.data.total || 0 // 总数
  } finally {
    loading.value = false // 关闭加载
  }
}

// 查询：回到第一页
function handleSearch() {
  query.page = 1 // 重置页码
  fetchList() // 请求
}

// 重置筛选
function handleReset() {
  query.category_name = '' // 清空名称
  query.status = '' // 清空状态
  query.page = 1 // 回第一页
  fetchList() // 重新加载
}

// 重置表单为初值
function resetForm() {
  Object.assign(form, { id: null, category_name: '', category_code: '', sort: 0, status: 1, remark: '' }) // 统一清空
}

// 打开新增
function openCreate() {
  resetForm() // 先清空
  dialogVisible.value = true // 打开弹窗
}

// 打开编辑
function openEdit(row) {
  resetForm() // 以防上一篇残留
  Object.assign(form, { ...row }) // 回填整行
  dialogVisible.value = true // 打开
}

// 提交表单
async function submitForm() {
  const valid = await formRef.value.validate().catch(() => false) // 校验失败直接返回
  if (!valid) return // 中断
  saving.value = true // 防重复提交
  try {
    const payload = { ...form } // 复制表单
    delete payload.id // 主键不作为入参
    if (form.id) await categoryApi.update(form.id, payload) // 编辑
    else await categoryApi.create(payload) // 新增
    ElMessage.success(form.id ? '编辑成功' : '新增成功') // 提示
    dialogVisible.value = false // 关闭弹窗
    fetchList() // 刷新列表
  } finally {
    saving.value = false // 释放按钮
  }
}

// 启停切换
async function toggleStatus(row) {
  await categoryApi.update(row.id, { status: row.status === 1 ? 0 : 1 }) // 只提交状态字段
  ElMessage.success('状态已更新') // 提示
  fetchList() // 刷新
}

// 删除（逻辑删除）
async function handleDelete(row) {
  await ElMessageBox.confirm(`确认删除分类「${row.category_name}」？`, '提示', { type: 'warning' }) // 二次确认
  await categoryApi.remove([row.id]) // 批量接口传数组
  ElMessage.success('删除成功') // 提示
  fetchList() // 刷新
}

// 首次进入加载
onMounted(fetchList)
</script>

<style scoped>
/* 页头：标题与操作按钮两端对齐 */
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: var(--app-space-4);
}
/* 标题：与全站页头字号一致 */
.page-header h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: var(--app-text-1);
}
/* 副标题 */
.page-title-wrap .sub {
  margin-top: 4px;
  font-size: 12px;
  color: var(--app-text-3);
}
/* 搜索卡片 */
.search-card {
  margin-bottom: var(--app-space-4);
  border-radius: var(--app-radius-lg);
}
/* 表格卡片 */
.table-card {
  border-radius: var(--app-radius-lg);
}
/* 分页容器：右对齐 */
.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: var(--app-space-4);
}
</style>
