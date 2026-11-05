<!--
  文件级说明：
  职责：BI「数据集」管理页——维护大屏图表的数据来源（MySQL 查询或 API 接口），
        提供按名称/类型/状态筛选、分页表格、行内启停、单条与批量删除、新增/编辑弹窗。
  依赖：@/utils/request（统一请求封装）、Element Plus 组件与图标、全局 v-perm 指令（bi:create/bi:update/bi:delete 按钮级权限）、
        /bi/screen/list 接口提供“所属大屏”下拉。
  被谁使用：BI 菜单下的数据集管理路由；数据集记录会被大屏配置中的图表按 screen_id 关联引用。
  说明：本文件没有 <style> 段，样式全部复用全局样式（app-container/search-card/table-card/pagination-wrap/op-col 等）。
-->
<template>
  <!-- 页面根容器：复用全局 app-container 内边距 -->
  <div class="app-container">
    <!-- 页头：标题 + 当前筛选条件下的总条数 -->
    <div class="page-header">
      <div class="page-title-wrap">
        <!-- 模块标题：数据集的类型与配置直接决定大屏图表能否取到数据 -->
        <h2>数据集管理</h2>
        <!-- 副标题：total 来自列表接口，随筛选条件变化 -->
        <div class="sub">大屏数据集 · 共 {{ total }} 条</div>
      </div>
    </div>
    <!-- 搜索区：条件绑定 query，点查询或回车才请求 -->
    <el-card shadow="never" class="search-card">
      <!-- inline 横向排列；@submit.prevent 阻止表单默认提交导致页面刷新 -->
      <el-form :model="query" inline @submit.prevent>
        <el-form-item label="数据集名称">
          <!-- 名称模糊搜索：clearable 可清空；回车等价于点“查询” -->
          <el-input v-model="query.dataset_name" placeholder="请输入名称" clearable style="width: 170px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="类型">
          <!-- 类型筛选：mysql/api 与表格行内标签、表单下拉的取值保持一致；clearable 表示全部 -->
          <el-select v-model="query.ds_type" placeholder="全部" clearable style="width: 120px">
            <el-option label="MySQL" value="mysql" />
            <el-option label="API" value="api" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <!-- 状态筛选：1=启用 0=停用，与行内 el-switch 的 active/inactive 值一致 -->
          <el-select v-model="query.status" placeholder="全部" clearable style="width: 110px">
            <el-option label="启用" :value="1" />
            <el-option label="停用" :value="0" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <!-- 查询：重置到第 1 页，避免旧页码超出新条件的总页数 -->
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <!-- 重置：恢复 query 初值后再查询 -->
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 表格卡：头部放新增/批量删除，主体为分页列表 -->
    <el-card shadow="never" class="table-card">
      <template #header>
        <div class="card-header">
          <div class="card-actions">
            <!-- 新增：v-perm 控制按钮级权限（无 bi:create 时指令直接隐藏元素） -->
            <el-button v-perm="'bi:create'" type="primary" :icon="Plus" @click="openCreate">新增</el-button>
            <!-- 批量删除：未勾选任何行时置灰；权限码为 bi:delete；点击后由 handleBatchDelete 二次确认 -->
            <el-button v-perm="'bi:delete'" type="danger" plain :icon="Delete" :disabled="!selection.length" @click="handleBatchDelete">批量删除</el-button>
          </div>
        </div>
      </template>
      <!-- 列表：@selection-change 同步选中行到 selection，供批量删除使用 -->
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据" @selection-change="onSelectionChange">
        <!-- 序号列：当前页内的展示序号 -->
        <el-table-column type="index" label="序号" width="70" align="center" />
        <!-- 勾选列：开启多选，宽度固定 50px -->
        <el-table-column type="selection" width="50" />
        <!-- 数据集名称：min-width 保证可读；超长时悬浮显示全文 -->
        <el-table-column label="数据集名称" prop="dataset_name" min-width="180" show-overflow-tooltip />
        <!-- 类型列：mysql/api 用不同颜色的标签区分，未知类型回退为原始文本，避免数据异常时显示空白 -->
        <el-table-column label="类型" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.ds_type==='mysql'" size="small">MySQL</el-tag>
            <el-tag v-else-if="row.ds_type==='api'" size="small" type="success">API</el-tag>
            <span v-else>{{ row.ds_type }}</span>
          </template>
        </el-table-column>
        <!-- 所属大屏：优先显示大屏名称，缺失时回退 screen_id，最后显示“-”（表示尚未绑定大屏） -->
        <el-table-column label="大屏" min-width="140">
          <template #default="{ row }">{{ row.screen_name || row.screen_id || '-' }}</template>
        </el-table-column>
        <!-- 配置：数据集 JSON 原文，便于快速确认 SQL/接口地址；超长时悬浮查看 -->
        <el-table-column label="配置" prop="ds_config" min-width="220" show-overflow-tooltip />
        <!-- 状态列：开关直接改 row.status 并调用 handleStatusChange 落库；
             v-perm 控制修改权限（无 bi:update 时隐藏开关，行内看不到启停入口） -->
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-switch v-model="row.status" :active-value="1" :inactive-value="0" v-perm="'bi:update'" @change="handleStatusChange(row)" />
          </template>
        </el-table-column>
        <!-- 备注：可选说明，超长悬浮查看 -->
        <el-table-column label="备注" prop="remark" min-width="160" show-overflow-tooltip />
        <!-- 创建时间：后端格式化好的字符串，直接展示 -->
        <el-table-column label="创建时间" prop="create_time" width="170" />
        <!-- 操作列：fixed=right 横向滚动时常驻；op-col 复用全局操作列样式 -->
        <el-table-column label="操作" width="180" fixed="right" class-name="op-col">
          <template #default="{ row }">
            <!-- 编辑：按 bi:update 权限控制显示 -->
            <el-button v-perm="'bi:update'" link type="primary" @click="openEdit(row)">编辑</el-button>
            <!-- 删除：按 bi:delete 权限控制显示 -->
            <el-button v-perm="'bi:delete'" link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <!-- 分页器：v-model 直接绑定 query.page/page_size，@change 覆盖页码与每页条数两种变化 -->
      <div class="pagination-wrap">
        <el-pagination background layout="total, sizes, prev, pager, next, jumper"
          :total="total" v-model:current-page="query.page" v-model:page-size="query.page_size"
          :page-sizes="[10, 20, 50, 100]" @change="fetchList" />
      </div>
    </el-card>

    <!-- 新增/编辑弹窗：共用一套表单，标题由 dialogTitle 区分；640px 宽度适配长 JSON 文本域 -->
    <el-dialog :title="dialogTitle" v-model="dialogVisible" width="640px" :close-on-click-modal="false" destroy-on-close>
      <!-- 表单：formRef 提交前校验；label-width=110 让“数据集名称/配置JSON”等标签对齐 -->
      <el-form ref="formRef" :model="form" :rules="rules" label-width="110px">
        <!-- 数据集名称：必填；maxlength=100 与后端字段长度一致 -->
        <el-form-item label="数据集名称" prop="dataset_name">
          <el-input v-model="form.dataset_name" placeholder="请输入数据集名称" maxlength="100" />
        </el-form-item>
        <!-- 类型：决定后端如何解释 ds_config（MySQL 视为查询语句，API 视为请求配置） -->
        <el-form-item label="类型" prop="ds_type">
          <el-select v-model="form.ds_type" style="width:100%">
            <el-option label="MySQL" value="mysql" />
            <el-option label="API" value="api" />
          </el-select>
        </el-form-item>
        <!-- 所属大屏：clearable 允许暂不绑定；选项来自 /bi/screen/list（最多 200 条） -->
        <el-form-item label="所属大屏" prop="screen_id">
          <el-select v-model="form.screen_id" placeholder="请选择大屏" style="width:100%" clearable>
            <el-option v-for="s in screenOptions" :key="s.id" :label="s.screen_name" :value="s.id" />
          </el-select>
        </el-form-item>
        <!-- 配置JSON：以纯文本提交，前端不做 JSON 解析/校验（格式是否合法由后端判断）；
             5 行高度便于查看多行 SQL/URL 配置 -->
        <el-form-item label="配置JSON" prop="ds_config">
          <el-input v-model="form.ds_config" type="textarea" :rows="5" placeholder="请输入数据源配置JSON" />
        </el-form-item>
        <!-- 状态：1=启用 0=停用；停用后大屏取数应跳过该数据集（由后端执行） -->
        <el-form-item label="状态" prop="status">
          <el-radio-group v-model="form.status">
            <el-radio :value="1">启用</el-radio>
            <el-radio :value="0">停用</el-radio>
          </el-radio-group>
        </el-form-item>
        <!-- 备注：可选，用于说明数据集用途/来源 -->
        <el-form-item label="备注" prop="remark">
          <el-input v-model="form.remark" type="textarea" :rows="2" placeholder="请输入备注" />
        </el-form-item>
      </el-form>
      <!-- 底部按钮：取消关闭弹窗；确定用 saving 控制 loading，避免重复提交 -->
      <template #footer>
        <el-button @click="dialogVisible=false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitForm">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
// 组合式 API：状态与方法局部于本组件
// ref 基础响应式/模板引用；reactive 表单与查询对象；onMounted 首屏并行加载列表与大屏下拉
import { ref, reactive, onMounted } from 'vue'
// ElMessage 结果提示；ElMessageBox 删除二次确认
import { ElMessage, ElMessageBox } from 'element-plus'
// 图标：Search/Refresh 搜索按钮；Plus/Delete 新增与批量删除
import { Search, Refresh, Plus, Delete } from '@element-plus/icons-vue'
// 统一请求实例：自动带 token、统一解析 { code, msg, data }、统一错误提示
import request from '@/utils/request'

// 列表加载态：控制 el-table 的 v-loading
const loading = ref(false)
// 当前页数据集数据
const rows = ref([])
// 总条数：分页器与页头副标题共用
const total = ref(0)
// 当前勾选的行：仅用于批量删除（长度决定按钮是否可用）
const selection = ref([])
// 提交中标记：防止弹窗重复提交
const saving = ref(false)
// 弹窗显隐
const dialogVisible = ref(false)
// 弹窗标题：新增/编辑共用弹窗，用标题区分模式
const dialogTitle = ref('新增')
// el-form 实例：提交前 validate
const formRef = ref()
// 所属大屏下拉：来自 /bi/screen/list，供表单选择关联大屏
const screenOptions = ref([])

// 查询初值：重置时整体恢复，页码也回到 1
const query_orig = { page: 1, page_size: 10, dataset_name: '', ds_type: null, status: null }
// 查询对象：reactive 便于 Object.assign 重置；分页器直接 v-model 到 page/page_size
const query = reactive({ ...query_orig })

// 表单初值：新增/重置都基于它；默认类型 mysql、默认启用
const form_orig = {
  id: null, dataset_name: '', ds_type: 'mysql', ds_config: '', screen_id: null, status: 1, remark: ''
}
// 弹窗表单：就地重置/回填
const form = reactive({ ...form_orig })

// 校验规则：名称/类型/配置必填；类型用 change 触发（下拉选择后立即校验），其余用 blur
const rules = {
  dataset_name: [{ required: true, message: '请输入数据集名称', trigger: 'blur' }],
  ds_type: [{ required: true, message: '请选择类型', trigger: 'change' }],
  ds_config: [{ required: true, message: '请输入配置JSON', trigger: 'blur' }]
}

// 接口地址表：集中维护 /bi/dataset 的四个动作路径，避免各处硬编码；
// 注意 update 还需在调用处拼接 /{id}，这里只返回基础路径
function apiUrl(action) {
  const base = '/bi/dataset'
  return {
    list: base + '/list',
    create: base + '/create',
    update: base + '/update',
    delete: base + '/delete'
  }[action]
}

// 加载大屏下拉：一次取 200 条足够覆盖当前规模；失败静默（catch 内注释），不影响数据集列表主流程
async function loadScreens() {
  try {
    const res = await request.get('/bi/screen/list', { params: { page: 1, page_size: 200 } })
    screenOptions.value = res.data.list || []
  } catch (e) { /* ignore */ }
}

// 拉取数据集列表：params 为 reactive 的 query，axios 负责序列化；finally 保证解除 loading
async function fetchList() {
  loading.value = true
  try {
    const res = await request.get(apiUrl('list'), { params: query })
    // 兼容后端未返回 list/total
    rows.value = res.data.list || []
    total.value = res.data.total || 0
  } finally { loading.value = false }
}
// 查询：回到第 1 页，避免旧页码超出新条件的总页数
function handleSearch() { query.page = 1; fetchList() }
// 重置：整体恢复查询初值后再查询
function handleReset() { Object.assign(query, query_orig); handleSearch() }
// 勾选变化：el-table 每次选择都会回调最新选中行数组，直接替换 selection
function onSelectionChange(r) { selection.value = r }

// 新增：恢复表单初值并设置标题；screenOptions 已提前加载，弹窗打开即可选择大屏
function openCreate() { Object.assign(form, form_orig); dialogTitle.value = '新增数据集'; dialogVisible.value = true }
// 编辑：先恢复初值再用整行覆盖，避免上次编辑残留；行内多余字段（screen_name 等）一并带入，提交时剔除 id
function openEdit(row) { Object.assign(form, form_orig, row); dialogTitle.value = '编辑数据集'; dialogVisible.value = true }

// 提交：校验通过后按有无 id 走更新/新增；成功后关闭弹窗并刷新列表
async function submitForm() {
  await formRef.value.validate()
  saving.value = true
  try {
    if (form.id) {
      // 更新：剔除 id（主键已在 URL 中），其余字段整体提交
      const { id, ...data } = form
      await request.put(`${apiUrl('update')}/${id}`, data); ElMessage.success('更新成功')
    } else {
      // 新增：直接提交表单（id 为 null）
      await request.post(apiUrl('create'), form); ElMessage.success('新增成功')
    }
    dialogVisible.value = false; fetchList()
  } finally { saving.value = false }
}

// 行内启停：走独立的 status 接口（只提交 status 字段），避免覆盖其他可能被他人修改的字段。
// 注意：开关已通过 v-model 改动 row.status，若请求失败这里没有回滚逻辑，
// 界面会短暂与后端不一致（错误提示由请求拦截器统一弹出）
async function handleStatusChange(row) {
  await request.put(`/bi/dataset/status/${row.id}`, { status: row.status })
  ElMessage.success(row.status === 1 ? '已启用' : '已停用')
}

// 单条删除：二次确认后按 ids 数组提交（axios delete 用 data 携带请求体），成功后刷新列表
async function handleDelete(row) {
  await ElMessageBox.confirm('确定删除该数据集？', '提示', { type: 'warning' })
  await request.delete(apiUrl('delete'), { data: { ids: [row.id] } })
  ElMessage.success('删除成功'); fetchList()
}

// 批量删除：确认文案带上选中数量；把 selection 映射成 id 数组后一次提交，减少请求次数
async function handleBatchDelete() {
  await ElMessageBox.confirm(`确定删除选中的 ${selection.value.length} 条数据集？`, '提示', { type: 'warning' })
  await request.delete(apiUrl('delete'), { data: { ids: selection.value.map(r => r.id) } })
  ElMessage.success('批量删除成功'); fetchList()
}

// 首屏加载：列表与大屏下拉并行请求，下拉失败不影响列表展示
onMounted(() => { fetchList(); loadScreens() })
</script>
