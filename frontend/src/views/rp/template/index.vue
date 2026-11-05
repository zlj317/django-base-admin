<!--
  文件说明：报表模板（RP Template）管理页面，是报表模块的核心配置入口。
  职责：维护低代码报表模板，支持按名称/模板Key/状态查询、分页列表、新增/编辑、启停切换、
        单条与批量删除，以及“预览模板效果”和“立即生成报表”两个业务动作。
  关键字段：template_key 业务唯一标识，创建后不允许修改（防止历史生成记录/外部引用失效）；
            category_id 关联报表分类；ds_id 关联数据源（取数来源）；
            template_json 低代码报表结构（数据集、SQL、参数、表格/图表组件等）；
            permission_json 访问权限配置（可见角色/部门等）；version 模板版本号。
  依赖：Element Plus、@element-plus/icons-vue、@/utils/request 统一请求封装、
        @/components/report/ReportPreview.vue（按 payload 渲染报表）。
  被谁使用：rp 模块菜单路由加载本页；本页“生成报表”会产生 views/rp/gen 中的生成记录，
            其分类/数据源下拉数据来自 /rp/category/list 与 /rp/datasource/list。
-->
<template>
  <!-- 页面根容器：复用全局 app-container 样式，统一页面内边距与背景 -->
  <div class="app-container">
    <!-- 页头：标题与总数 -->
    <div class="page-header">
      <!-- 标题包裹层：约束标题与副标题的垂直排布 -->
      <div class="page-title-wrap">
        <!-- 页面主标题 -->
        <h2>报表模板</h2>
        <!-- 副标题：total 为模板列表接口返回的总条数，随筛选条件变化 -->
        <div class="sub">模板管理 · 共 {{ total }} 条</div>
      </div>
    </div>
    <!-- 查询卡片：shadow="never" 与表格卡片保持扁平统一的视觉 -->
    <el-card shadow="never" class="search-card">
      <!-- 查询表单：inline 行内布局；@submit.prevent 阻止原生提交，避免回车刷新页面 -->
      <el-form :model="query" inline @submit.prevent>
        <!-- 查询项：按模板名称模糊搜索 -->
        <el-form-item label="模板名称">
          <!-- 双向绑定 query.template_name；clearable 一键清空；回车即查询 -->
          <el-input v-model="query.template_name" placeholder="请输入模板名称" clearable style="width: 170px" @keyup.enter="handleSearch" />
        </el-form-item>
        <!-- 查询项：按模板 Key 精确匹配，便于定位具体模板 -->
        <el-form-item label="模板Key">
          <!-- 双向绑定 query.template_key；同为回车即查询，减少一次鼠标点击 -->
          <el-input v-model="query.template_key" placeholder="请输入模板Key" clearable style="width: 170px" @keyup.enter="handleSearch" />
        </el-form-item>
        <!-- 查询项：按启停状态筛选 -->
        <el-form-item label="状态">
          <!-- 1 启用 / 0 停用，与后端状态枚举一致；clearable 清空即查全部 -->
          <el-select v-model="query.status" placeholder="全部" clearable style="width: 110px">
            <el-option label="启用" :value="1" />
            <el-option label="停用" :value="0" />
          </el-select>
        </el-form-item>
        <!-- 无标签操作项：查询与重置 -->
        <el-form-item>
          <!-- 查询：handleSearch 会先重置页码再请求 -->
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <!-- 重置：恢复默认查询条件并加载第一页 -->
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 列表卡片：承载表格、操作列与分页 -->
    <el-card shadow="never" class="table-card">
      <!-- 卡片头部插槽：新增与批量删除入口 -->
      <template #header>
        <!-- 头部容器：flex 布局使按钮组靠右 -->
        <div class="card-header">
          <!-- 操作按钮组 -->
          <div class="card-actions">
            <!-- 新增：需 'rp:create' 权限；打开已重置的新增弹窗 -->
            <el-button v-perm="'rp:create'" type="primary" :icon="Plus" @click="openCreate">新增</el-button>
            <!-- 批量删除：未勾选时禁用；需 'rp:delete' 权限 -->
            <el-button v-perm="'rp:delete'" type="danger" plain :icon="Delete" :disabled="!selection.length" @click="handleBatchDelete">批量删除</el-button>
          </div>
        </div>
      </template>
      <!-- 数据表格：v-loading 请求遮罩；stripe 斑马纹；空数据文案；勾选变化同步 selection -->
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据" @selection-change="onSelectionChange">
        <!-- 序号列：type="index" 自动生成当前页行号 -->
        <el-table-column type="index" label="序号" width="70" align="center" />
        <!-- 多选列：勾选结果供批量删除使用 -->
        <el-table-column type="selection" width="50" />
        <!-- 模板名称：超长省略并悬浮显示全文 -->
        <el-table-column label="模板名称" prop="template_name" min-width="180" show-overflow-tooltip />
        <!-- 模板Key：业务唯一标识，调用方按 Key 引用模板；用省略样式防止过长撑破布局 -->
        <el-table-column label="模板Key" prop="template_key" min-width="140" show-overflow-tooltip />
        <!-- 分类列：优先展示后端联表返回的分类名，缺失时回退显示分类 ID，最后显示 '-' -->
        <el-table-column label="分类" min-width="120">
          <template #default="{ row }">{{ row.category_name || row.category_id || '-' }}</template>
        </el-table-column>
        <!-- 数据源列：优先展示联表返回的数据源名称，退化为 ID，再退化为 '-' -->
        <el-table-column label="数据源" min-width="120">
          <template #default="{ row }">{{ row.ds_name || row.ds_id || '-' }}</template>
        </el-table-column>
        <!-- 版本号：配置类字段，宽度固定 -->
        <el-table-column label="版本" prop="version" width="80" />
        <!-- 状态列：行内开关控制模板启用/停用 -->
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <!-- 开关值 1/0 与后端一致；需 'rp:update' 权限；change 后调用独立状态接口，
                 停用后模板不应再参与生成/预览 -->
            <el-switch v-model="row.status" :active-value="1" :inactive-value="0" v-perm="'rp:update'" @change="handleStatusChange(row)" />
          </template>
        </el-table-column>
        <!-- 创建时间：后端格式化后的字符串，直接展示 -->
        <el-table-column label="创建时间" prop="create_time" width="170" />
        <!-- 操作列：宽度 320 以容纳四个按钮；fixed="right" 横向滚动时固定可见；
             op-col 复用全局操作列样式 -->
        <el-table-column label="操作" width="320" fixed="right" class-name="op-col">
          <template #default="{ row }">
            <!-- 预览：按模板配置实时渲染一次效果（不落生成记录），无需额外权限，便于配置时自查 -->
            <el-button link type="warning" @click="handlePreview(row)">预览</el-button>
            <!-- 编辑：需 'rp:update' 权限，回填当前行到弹窗 -->
            <el-button v-perm="'rp:update'" link type="primary" @click="openEdit(row)">编辑</el-button>
            <!-- 生成报表：需 'rp:generate' 权限；二次确认后立即生成并展示结果，同时会产出生成记录 -->
            <el-button v-perm="'rp:generate'" link type="success" @click="handleGenerate(row)">生成报表</el-button>
            <!-- 删除：需 'rp:delete' 权限，二次确认后按 id 删除 -->
            <el-button v-perm="'rp:delete'" link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <!-- 分页容器：统一右对齐版式 -->
      <div class="pagination-wrap">
        <!-- 分页器：current-page / page-size 双向绑定 query；@change 页码或条数变化后重新请求 -->
        <el-pagination background layout="total, sizes, prev, pager, next, jumper"
          :total="total" v-model:current-page="query.page" v-model:page-size="query.page_size"
          :page-sizes="[10, 20, 50, 100]" @change="fetchList" />
      </div>
    </el-card>

    <!-- 新增/编辑弹窗：标题动态切换；点遮罩不关闭，防止误触丢失 JSON 配置；关闭即销毁表单 -->
    <el-dialog :title="dialogTitle" v-model="dialogVisible" width="720px" :close-on-click-modal="false" destroy-on-close>
      <!-- 弹窗表单：ref 供 submitForm 校验；rules 控制必填；label-width 统一标签宽度 -->
      <el-form ref="formRef" :model="form" :rules="rules" label-width="110px">
        <!-- 两列栅格：gutter=12 控制列间距，把较多字段压缩在两行内，减少弹窗纵向滚动 -->
        <el-row :gutter="12">
          <el-col :span="12">
            <!-- 模板名称：必填，长度 100 与后端字段约束一致 -->
            <el-form-item label="模板名称" prop="template_name">
              <el-input v-model="form.template_name" placeholder="请输入模板名称" maxlength="100" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <!-- 模板Key：必填且全局唯一；编辑态（form.id 存在）禁用，保证已有引用关系不失效 -->
            <el-form-item label="模板Key" prop="template_key">
              <el-input v-model="form.template_key" placeholder="唯一标识" maxlength="64" :disabled="!!form.id" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <!-- 分类：从 categoryOptions 下拉选择，关联报表分类，便于按业务归类检索 -->
            <el-form-item label="分类" prop="category_id">
              <!-- v-for 渲染分类选项，value 用分类 id；占满整行宽度避免截断 -->
              <el-select v-model="form.category_id" placeholder="请选择分类" style="width:100%">
                <el-option v-for="c in categoryOptions" :key="c.id" :label="c.category_name" :value="c.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <!-- 数据源：决定报表取数来源；选项来自 /rp/datasource/list -->
            <el-form-item label="数据源" prop="ds_id">
              <!-- value 传数据源 id，便于后端按 id 读取 ds_config 连接参数 -->
              <el-select v-model="form.ds_id" placeholder="请选择数据源" style="width:100%">
                <el-option v-for="d in dsOptions" :key="d.id" :label="d.ds_name" :value="d.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <!-- 版本号：字符串而非数字，允许 "1.0"、"v2" 这类写法 -->
            <el-form-item label="版本" prop="version">
              <el-input v-model="form.version" placeholder="如 1.0" maxlength="20" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <!-- 状态：1 启用 / 0 停用；停用模板不再参与生成，但已生成的历史记录仍保留 -->
            <el-form-item label="状态" prop="status">
              <el-radio-group v-model="form.status">
                <el-radio :value="1">启用</el-radio>
                <el-radio :value="0">停用</el-radio>
              </el-radio-group>
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <!-- 模板JSON：低代码报表的描述数据（数据集、SQL/占位符、查询参数、表格或图表组件），
                 必填；用 6 行文本域方便粘贴与校对 -->
            <el-form-item label="模板JSON" prop="template_json">
              <el-input v-model="form.template_json" type="textarea" :rows="6" placeholder="低代码报表模板JSON" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <!-- 权限JSON：控制哪些角色/部门可见该报表；3 行文本域，非必填 -->
            <el-form-item label="权限JSON" prop="permission_json">
              <el-input v-model="form.permission_json" type="textarea" :rows="3" placeholder="权限配置JSON" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <!-- 备注：自由文本说明，占满整行 -->
            <el-form-item label="备注" prop="remark">
              <el-input v-model="form.remark" type="textarea" :rows="2" placeholder="请输入备注" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <!-- 弹窗底部插槽：取消/确定 -->
      <template #footer>
        <!-- 取消：只关闭弹窗，不保存修改 -->
        <el-button @click="dialogVisible=false">取消</el-button>
        <!-- 确定：loading 防重复提交，点击后走校验与新增/更新 -->
        <el-button type="primary" :loading="saving" @click="submitForm">确定</el-button>
      </template>
    </el-dialog>

    <!-- 预览弹窗：标题动态带模板名/生成结果；top=4vh 靠上展示，留出更多内容高度；
         destroy-on-close 关闭即销毁报表组件，防止下次打开残留上一次内容 -->
    <el-dialog :title="previewTitle" v-model="previewVisible" width="980px" top="4vh" destroy-on-close>
      <!-- 预览容器：previewLoading 控制遮罩，接口未返回前保持占位高度 -->
      <div v-loading="previewLoading" class="preview-body">
        <!-- 报表渲染组件：previewData 为空时不渲染，避免空 payload 导致内部报错；
             数据由 /rp/template/preview/{id} 或 /rp/template/generate/{id} 返回 -->
        <ReportPreview v-if="previewData" :payload="previewData" />
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
// 组合式 API：顶层声明的变量与函数自动暴露给模板，无需显式 return
import { ref, reactive, onMounted } from 'vue'
// ElMessage 操作结果提示；ElMessageBox 生成/删除前的二次确认
import { ElMessage, ElMessageBox } from 'element-plus'
// 按钮图标：查询、重置、新增、批量删除
import { Search, Refresh, Plus, Delete } from '@element-plus/icons-vue'
// 统一请求实例：已封装 baseURL、Token 与错误提示
import request from '@/utils/request'
// 低代码报表渲染组件：接收报表 payload，负责表格/图表等内容展示
import ReportPreview from '@/components/report/ReportPreview.vue'

// 表格 loading：请求期间遮罩
const loading = ref(false)
// 当前页模板数据
const rows = ref([])
// 总条数，驱动分页器与页头统计
const total = ref(0)
// 勾选行，控制批量删除按钮并提供 ids
const selection = ref([])
// 提交按钮 loading，防重复提交
const saving = ref(false)
// 新增/编辑弹窗显隐
const dialogVisible = ref(false)
// 弹窗标题，区分新增模板与编辑模板
const dialogTitle = ref('新增')
// 表单实例引用，用于 validate
const formRef = ref()
// 分类下拉选项（来自 /rp/category/list），供表单分类选择
const categoryOptions = ref([])
// 数据源下拉选项（来自 /rp/datasource/list），供表单数据源选择
const dsOptions = ref([])
// 预览弹窗显隐
const previewVisible = ref(false)
// 预览 loading：与列表 loading 独立，避免互相影响
const previewLoading = ref(false)
// 预览 payload；null 时模板中 v-if 不渲染报表组件
const previewData = ref(null)
// 预览弹窗标题，按预览/生成场景动态拼接
const previewTitle = ref('报表预览')

// 查询默认值：状态默认 null 表示全部；分页默认第 1 页、每页 10 条
const query_orig = { page: 1, page_size: 10, template_name: '', template_key: '', status: null }
// reactive 包裹以支持模板双向绑定与分页组件同步
const query = reactive({ ...query_orig })

// 表单默认值：id=null 表示新增；分类/数据源默认未选；版本默认 1.0；状态默认启用
const form_orig = {
  id: null, template_name: '', template_key: '', category_id: null, ds_id: null,
  template_json: '', version: '1.0', status: 1, permission_json: '', remark: ''
}
// 弹窗表单对象，展开拷贝避免与 form_orig 共享引用
const form = reactive({ ...form_orig })

// 校验规则：名称/Key/模板JSON 必填；其余字段（分类、数据源、权限等）按业务允许留空
const rules = {
  template_name: [{ required: true, message: '请输入模板名称', trigger: 'blur' }],
  template_key: [{ required: true, message: '请输入模板Key', trigger: 'blur' }],
  template_json: [{ required: true, message: '请输入模板JSON', trigger: 'blur' }]
}

// 按动作名返回模板模块接口地址，避免路径硬编码散落各处
function apiUrl(action) {
  // 模板模块统一前缀，后端路由挂载点为 /rp/template
  const base = '/rp/template'
  // 对象查表：list/create/update/delete 四种动作
  return {
    list: base + '/list',
    create: base + '/create',
    update: base + '/update',
    delete: base + '/delete'
  }[action]
}

// 加载表单下拉选项：分类与数据源一次取 200 条，满足当前规模的下拉需求
async function loadOptions() {
  try {
    // 分类列表：下拉只需 id 与名称，取第一页最大数量即可
    const cRes = await request.get('/rp/category/list', { params: { page: 1, page_size: 200 } })
    // 兜底空数组，接口异常时下拉为空但不阻塞页面
    categoryOptions.value = cRes.data.list || []
    // 数据源列表：同样取 200 条，供数据源下拉选择
    const dRes = await request.get('/rp/datasource/list', { params: { page: 1, page_size: 200 } })
    // 兜底空数组
    dsOptions.value = dRes.data.list || []
  } catch (e) { /* ignore */ }
}

// 拉取模板列表：携带查询条件，回填 rows/total；finally 保证异常时关闭 loading
async function fetchList() {
  loading.value = true
  try {
    // GET 请求，params 自动拼接查询字符串
    const res = await request.get(apiUrl('list'), { params: query })
    // 兜底空数组，避免接口返回 null 时表格渲染异常
    rows.value = res.data.list || []
    // 兜底 0，避免分页器出现 NaN
    total.value = res.data.total || 0
  } finally { loading.value = false }
}
// 查询：先重置页码为 1，避免当前页超出新结果范围
function handleSearch() { query.page = 1; fetchList() }
// 重置：还原默认查询条件并重新查询
function handleReset() { Object.assign(query, query_orig); handleSearch() }
// 勾选变化：回调参数为选中行数组，同步给 selection 供批量删除使用
function onSelectionChange(r) { selection.value = r }

// 打开新增：先还原默认表单，避免上次编辑残留；标题改为“新增模板”
function openCreate() { Object.assign(form, form_orig); dialogTitle.value = '新增模板'; dialogVisible.value = true }
// 打开编辑：默认值打底、当前行覆盖；template_key 在弹窗中会被禁用，只读不改
function openEdit(row) { Object.assign(form, form_orig, row); dialogTitle.value = '编辑模板'; dialogVisible.value = true }

// 提交表单：先校验，再按 id 区分更新/新增
async function submitForm() {
  // 校验不通过会抛异常，中断后续提交
  await formRef.value.validate()
  saving.value = true
  try {
    // 有 id 表示编辑已有模板
    if (form.id) {
      // 剔除 id：更新接口把 id 放在路径上，body 不重复携带
      const { id, ...data } = form
      // PUT 更新模板（含 template_json / permission_json）
      await request.put(`${apiUrl('update')}/${id}`, data); ElMessage.success('更新成功')
    } else {
      // 无 id 走新增，提交整份表单
      await request.post(apiUrl('create'), form); ElMessage.success('新增成功')
    }
    // 成功后关闭弹窗并刷新列表
    dialogVisible.value = false; fetchList()
  } finally { saving.value = false }
}

// 预览模板：后端按模板配置实时执行一次（结合数据源与模板 JSON），返回报表 payload；
// 预览不会写入生成记录，适合配置时反复校验效果
async function handlePreview(row) {
  // 标题带模板名，便于区分不同模板的预览
  previewTitle.value = `报表预览 · ${row.template_name}`
  // 先清空旧数据，避免打开瞬间闪现上一次的报表
  previewData.value = null
  // 打开弹窗并开启遮罩，立即给用户反馈
  previewVisible.value = true
  previewLoading.value = true
  try {
    // GET /rp/template/preview/{id}
    const res = await request.get(`/rp/template/preview/${row.id}`)
    // 保存 payload 触发 v-if 渲染
    previewData.value = res.data
  } finally { previewLoading.value = false }
}

// 立即生成报表：确认后调用后端生成接口，成功会产出生成记录并返回本次报表 payload
async function handleGenerate(row) {
  // 生成可能耗时且会落库，先二次确认，文案带上模板名防止误点
  await ElMessageBox.confirm(`确定立即根据模板「${row.template_name}」生成报表？`, '提示', { type: 'warning' })
  // POST /rp/template/generate/{id}：同步返回本次生成结果
  const res = await request.post(`/rp/template/generate/${row.id}`)
  // 标题标明是“本次生成结果”，与普通预览区分
  previewTitle.value = `报表预览 · 本次生成结果`
  // 用生成结果直接打开预览弹窗
  previewData.value = res.data
  previewVisible.value = true
  // 提示生成成功，并刷新列表（模板的最近生成信息可能更新）
  ElMessage.success('报表生成成功')
  fetchList()
}

// 行内状态切换：调用独立状态接口，避免整条更新时覆盖模板 JSON 配置
async function handleStatusChange(row) {
  // PUT 只提交 status
  await request.put(`/rp/template/status/${row.id}`, { status: row.status })
  // 按新状态提示（1=已启用，0=已停用）
  ElMessage.success(row.status === 1 ? '已启用' : '已停用')
}

// 单条删除：先二次确认，取消会抛异常中断流程
async function handleDelete(row) {
  // warning 提示该操作不可恢复
  await ElMessageBox.confirm('确定删除该模板？', '提示', { type: 'warning' })
  // DELETE 请求体放 data；ids 数组便于复用批量接口
  await request.delete(apiUrl('delete'), { data: { ids: [row.id] } })
  // 提示并刷新列表
  ElMessage.success('删除成功'); fetchList()
}

// 批量删除：确认文案带选中数量
async function handleBatchDelete() {
  await ElMessageBox.confirm(`确定删除选中的 ${selection.value.length} 条模板？`, '提示', { type: 'warning' })
  // 收集勾选行 id 组成 ids 提交
  await request.delete(apiUrl('delete'), { data: { ids: selection.value.map(r => r.id) } })
  ElMessage.success('批量删除成功'); fetchList()
}

// 页面挂载后：加载第一页列表 + 预加载分类/数据源下拉选项（供新增/编辑弹窗使用）
onMounted(() => { fetchList(); loadOptions() })
</script>

<!-- 样式区块：仅约束预览容器高度，scoped 保证只作用于本页 -->
<style scoped>
/* .preview-body：报表渲染容器；最小高度用于数据未返回/loading 时保持弹窗体积，避免高度跳变；
   此处不涉及暗色主题变量，配色由 ReportPreview 组件内部自行适配 */
.preview-body { min-height: 320px; }
</style>
