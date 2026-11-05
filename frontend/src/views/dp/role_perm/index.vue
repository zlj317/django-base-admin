<!--
  角色数据权限页（/dp/role_perm）：
  职责：维护"角色 ↔ 数据权限"关联关系，只做新增与删除（关联本身无其他字段，故不提供编辑）。
  依赖：@/utils/request 统一请求、Element Plus 表格/表单/弹窗组件与图标；样式全部来自全局 styles/index.css（本文件无 style 块）。
  依赖接口：/system/role/list（角色下拉）、/dp/permission/list（权限下拉）、/dp/role_perm/*（关联增删查）。
  使用方：后台"数据权限"菜单；关联建立后，该角色的用户查询数据时按对应规则的 SQL 条件过滤。
-->
<template>
  <!-- 页面根容器：全局 .app-container 提供内边距与进场动画 -->
  <div class="app-container">
    <!-- 页面头部：标题 + 当前条件下关联总数 -->
    <div class="page-header">
      <!-- 标题容器：主副标题纵向排列 -->
      <div class="page-title-wrap">
        <!-- 主标题 -->
        <h2>角色数据权限</h2>
        <!-- 副标题：total 来自列表接口，随筛选变化 -->
        <div class="sub">角色与数据权限关联 · 共 {{ total }} 条</div>
      </div>
    </div>

    <!-- 搜索区卡片：扁平无阴影，复用全局搜索区版式 -->
    <el-card shadow="never" class="search-card">
      <!-- 查询表单：inline 横向排列；@submit.prevent 阻止原生提交刷新页面 -->
      <el-form :model="query" inline @submit.prevent>
        <!-- 角色筛选：下拉选项来自 roleOptions（挂载时远程加载）；clearable 后表示不限角色 -->
        <el-form-item label="角色">
          <el-select v-model="query.role_id" placeholder="全部" clearable style="width: 180px">
            <!-- 用 v-for 渲染角色选项：key 用 id 保证列表更新时不复用错误节点；label 用角色名提升可读性、value 用 id 便于后端过滤 -->
            <el-option v-for="r in roleOptions" :key="r.id" :label="r.role_name" :value="r.id" />
          </el-select>
        </el-form-item>
        <!-- 权限筛选：下拉选项来自 permOptions（数据权限规则列表）；clearable 后表示不限权限 -->
        <el-form-item label="权限">
          <el-select v-model="query.permission_id" placeholder="全部" clearable style="width: 180px">
            <!-- v-for 渲染数据权限选项：label 展示权限名称，value 传 id -->
            <el-option v-for="p in permOptions" :key="p.id" :label="p.permission_name" :value="p.id" />
          </el-select>
        </el-form-item>
        <!-- 操作按钮：查询回第一页，重置清空两个下拉并重新查询 -->
        <el-form-item>
          <!-- 按选择的角色/权限过滤关联记录 -->
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <!-- 还原查询初值并查询 -->
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 列表区卡片：表格 + 批量删除 + 分页 -->
    <el-card shadow="never" class="table-card">
      <!-- 卡片头部插槽：新增关联与批量删除入口 -->
      <template #header>
        <!-- 头部容器 -->
        <div class="card-header">
          <!-- 操作按钮组 -->
          <div class="card-actions">
            <!-- 新增关联：打开弹窗选择角色与数据权限 -->
            <el-button type="primary" :icon="Plus" @click="openCreate">新增</el-button>
            <!-- 批量删除：未勾选任何行时禁用，避免空 ids 请求 -->
            <el-button type="danger" plain :icon="Delete" :disabled="!selection.length" @click="handleBatchDelete">批量删除</el-button>
          </div>
        </div>
      </template>
      <!-- 关联表格：loading 遮罩 + 斑马纹，勾选行同步到 selection -->
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据" @selection-change="onSelectionChange">
        <!-- 序号列：前端行号 -->
        <el-table-column type="index" label="序号" width="70" align="center" />
        <!-- 多选列：批量删除的数据来源 -->
        <el-table-column type="selection" width="50" />
        <!-- 角色列：列表接口只返回 role_id，这里通过 getRoleName 映射成角色名，避免用户对着 id 猜 -->
        <el-table-column label="角色" min-width="160">
          <template #default="{ row }">{{ getRoleName(row.role_id) }}</template>
        </el-table-column>
        <!-- 权限列：同理把 permission_id 映射为权限名称，便于核对规则内容 -->
        <el-table-column label="权限" min-width="180">
          <template #default="{ row }">{{ getPermName(row.permission_id) }}</template>
        </el-table-column>
        <!-- 创建时间列：关联建立时间，由后端格式化后直接展示 -->
        <el-table-column label="创建时间" prop="create_time" width="170" />
        <!-- 操作列：仅删除（关联无其他可编辑字段），固定在右侧保证可见 -->
        <el-table-column label="操作" width="120" fixed="right" class-name="op-col">
          <template #default="{ row }">
            <!-- 删除关联：二次确认后解除该角色与权限的绑定 -->
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <!-- 分页容器：统一右对齐与留白 -->
      <div class="pagination-wrap">
        <!-- 分页器：@change 覆盖页码与每页条数变更，统一刷新 -->
        <el-pagination background layout="total, sizes, prev, pager, next, jumper"
          :total="total" v-model:current-page="query.page" v-model:page-size="query.page_size"
          :page-sizes="[10, 20, 50, 100]" @change="fetchList" />
      </div>
    </el-card>

    <!-- 新增关联弹窗：只有新增一种模式，标题固定；480px 宽度足够放两个下拉；禁止点遮罩关闭防误触；destroy-on-close 清除上次校验状态 -->
    <el-dialog :title="dialogTitle" v-model="dialogVisible" width="480px" :close-on-click-modal="false" destroy-on-close>
      <!-- 关联表单：ref 用于提交校验，rules 约束两个下拉必选 -->
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <!-- 角色选择：必选，决定把数据权限授予哪个角色 -->
        <el-form-item label="角色" prop="role_id">
          <!-- 宽度 100% 撑满行，选项来源与搜索区同一份 roleOptions，避免重复请求 -->
          <el-select v-model="form.role_id" placeholder="请选择角色" style="width:100%">
            <!-- v-for 渲染角色下拉项：label 角色名、value 角色 id -->
            <el-option v-for="r in roleOptions" :key="r.id" :label="r.role_name" :value="r.id" />
          </el-select>
        </el-form-item>
        <!-- 数据权限选择：必选，决定数据可见范围 -->
        <el-form-item label="数据权限" prop="permission_id">
          <!-- 宽度 100% 与上方保持一致的对齐效果 -->
          <el-select v-model="form.permission_id" placeholder="请选择权限" style="width:100%">
            <!-- v-for 渲染权限下拉项：label 权限名、value 权限 id -->
            <el-option v-for="p in permOptions" :key="p.id" :label="p.permission_name" :value="p.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <!-- 弹窗底部：取消不提交；确定走校验后调用新增接口 -->
      <template #footer>
        <!-- 取消：仅关闭弹窗 -->
        <el-button @click="dialogVisible=false">取消</el-button>
        <!-- 确定：saving 期间 loading，避免重复建立同一条关联 -->
        <el-button type="primary" :loading="saving" @click="submitForm">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
// 组合式 API：ref 管理状态，reactive 管理查询条件与表单，onMounted 首次加载下拉与列表
import { ref, reactive, onMounted } from 'vue'
// 统一提示与确认框：成功提示、删除确认
import { ElMessage, ElMessageBox } from 'element-plus'
// 图标：Search 查询、Refresh 重置、Plus 新增、Delete 批量删除
import { Search, Refresh, Plus, Delete } from '@element-plus/icons-vue'
// 统一 axios 实例：自动带 token、统一错误提示
import request from '@/utils/request'

// 列表加载态：控制表格遮罩
const loading = ref(false)
// 当前页关联数据（只含 role_id/permission_id 等 id 字段）
const rows = ref([])
// 关联总数：分页与副标题使用
const total = ref(0)
// 勾选行：批量删除时取 id
const selection = ref([])
// 提交中：驱动确定按钮 loading，防重复提交
const saving = ref(false)
// 弹窗显隐（本页只有新增场景）
const dialogVisible = ref(false)
// 弹窗标题：固定为新增文案，避免与其他页签混淆
const dialogTitle = ref('新增角色数据权限')
// 表单实例：提交前调用 validate()
const formRef = ref()
// 角色下拉数据：由 loadOptions 远程加载，同时用于表格里的 id→名称映射
const roleOptions = ref([])
// 数据权限下拉数据：同上，兼顾下拉选项与表格名称映射
const permOptions = ref([])

// 查询初值：role_id/permission_id 用 null 表示"全部"，重置时作为还原基准
const query_orig = { page: 1, page_size: 10, role_id: null, permission_id: null }
// 查询条件响应式副本：展开拷贝避免重置改写初值
const query = reactive({ ...query_orig })

// 表单初值：新增关联时两个字段都必须由用户选择，故默认 null
const form_orig = { id: null, role_id: null, permission_id: null }
// 表单响应式副本：新增时直接提交该对象
const form = reactive({ ...form_orig })

// 校验规则：两个下拉均必选；trigger=change 因为下拉选择后不会触发 blur
const rules = {
  role_id: [{ required: true, message: '请选择角色', trigger: 'change' }],
  permission_id: [{ required: true, message: '请选择数据权限', trigger: 'change' }]
}

// 接口基址：角色-权限关联统一前缀
const apiBase = '/dp/role_perm'

// id 转角色名：列表接口只给 id，若直接展示会让用户难以辨认
// 找不到时回退显示原始 id，保证数据不丢失（如选项未加载或被 200 条上限截断）
function getRoleName(id) {
  // 在下拉数据中线性查找，选项数量有限（最多 200），开销可忽略
  const r = roleOptions.value.find(x => x.id === id)
  return r ? r.role_name : id
}
// id 转权限名：与 getRoleName 同理，回退显示 id 便于排查脏数据
function getPermName(id) {
  // 按 id 精确匹配权限选项
  const p = permOptions.value.find(x => x.id === id)
  return p ? p.permission_name : id
}

// 并行加载角色与权限下拉：两个接口互不依赖，用 Promise.all 减少首屏等待
async function loadOptions() {
  try {
    // 各自 catch(() => null)：任一接口失败不阻断另一个，避免整个页面无选项可用
    const [rRes, pRes] = await Promise.all([
      // 角色列表：page_size=200 一次性取足够多的选项，规避分页下拉的复杂度
      request.get('/system/role/list', { params: { page: 1, page_size: 200 } }).catch(() => null),
      // 数据权限列表：同上，取前 200 条作为候选
      request.get('/dp/permission/list', { params: { page: 1, page_size: 200 } }).catch(() => null)
    ])
    // 仅在拿到响应时覆盖，失败则保留旧值/空数组，页面降级为展示原始 id
    if (rRes) roleOptions.value = rRes.data.list || []
    if (pRes) permOptions.value = pRes.data.list || []
  } catch (e) { /* ignore */ }
}

// 拉取关联列表：带查询条件（含分页）请求后端，返回 { list, total }
async function fetchList() {
  // 请求前打开 loading
  loading.value = true
  try {
    // GET /dp/role_perm/list：role_id/permission_id 为 null 时后端忽略
    const res = await request.get(apiBase + '/list', { params: query })
    // 兜底空数组，保证无数据时正常展示空表格
    rows.value = res.data.list || []
    // 兜底 0，保证分页器 total 为数字
    total.value = res.data.total || 0
  // 无论成败都关闭 loading，避免遮罩卡死
  } finally { loading.value = false }
}

// 查询：条件变化后回到第一页，避免页码超出新结果集
function handleSearch() { query.page = 1; fetchList() }
// 重置：还原查询初值（含分页）后重新查询
function handleReset() { Object.assign(query, query_orig); handleSearch() }
// 勾选变化：同步选中行，供批量删除禁用态与 id 收集
function onSelectionChange(r) { selection.value = r }

// 打开新增：先重置表单清空上次选择，再打开弹窗
function openCreate() { Object.assign(form, form_orig); dialogTitle.value = '新增角色数据权限'; dialogVisible.value = true }

// 提交新增：校验通过后调用 create，成功后关闭弹窗并刷新列表
async function submitForm() {
  // 校验两个下拉均已选择，未通过会抛异常中断提交
  await formRef.value.validate()
  // 进入提交态，禁用按钮避免重复建立关联
  saving.value = true
  try {
    // 新增关联：id 为 null，由后端生成主键；role_id+permission_id 组成关联关系
    await request.post(apiBase + '/create', form); ElMessage.success('新增成功')
    // 关闭弹窗并刷新列表，让新关联立即出现在表格中
    dialogVisible.value = false; fetchList()
  // 结束提交态
  } finally { saving.value = false }
}

// 删除单条关联：二次确认后提交 ids（仅一条）
async function handleDelete(row) {
  // 解除关联会改变该角色的数据可见范围，用警告型确认框拦截误操作
  await ElMessageBox.confirm('确定删除该关联？', '提示', { type: 'warning' })
  // DELETE 通过 data 传请求体，与后端统一 ids 约定一致
  await request.delete(apiBase + '/delete', { data: { ids: [row.id] } })
  // 成功后刷新列表，同步总数
  ElMessage.success('删除成功'); fetchList()
}

// 批量删除：确认文案带选中数量，让用户明确影响范围
async function handleBatchDelete() {
  // 取消会抛异常，后续请求不执行
  await ElMessageBox.confirm(`确定删除选中的 ${selection.value.length} 条？`, '提示', { type: 'warning' })
  // 汇总选中行 id 一次性提交，减少请求次数
  await request.delete(apiBase + '/delete', { data: { ids: selection.value.map(r => r.id) } })
  // 提示并刷新，勾选状态随数据刷新失效
  ElMessage.success('批量删除成功'); fetchList()
}

// 首次进入：先并行加载两个下拉，再拉列表；顺序上先 loadOptions 保证表格能映射出名称
onMounted(() => { loadOptions(); fetchList() })
</script>
