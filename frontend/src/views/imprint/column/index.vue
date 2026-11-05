<template>
  <!-- 文件说明：水印(imprint)模块「模板字段」维护页，管理导入模板 Excel 的列定义（字段名/表头/必填/类型/长度/排序）。
       依赖：@/utils/request 统一请求封装；后端接口 /imprint/column/* 与 /imprint/template/list。
       被使用：由水印相关菜单路由加载，此处维护的字段定义被导入解析时用于校验与表头映射。 -->
  <div class="app-container">
    <!-- 页面头部：标题 + 记录总数概览 -->
    <div class="page-header">
      <!-- 标题区：h2 主标题，sub 显示当前筛选条件下的总条数 -->
      <div class="page-title-wrap">
        <h2>模板字段</h2>
        <!-- total 来自列表接口的 total 字段，随查询/删除后刷新，帮助用户知道数据规模 -->
        <div class="sub">导入模板字段管理 · 共 {{ total }} 条</div>
      </div>
    </div>

    <!-- 查询区：shadow="never" 去掉卡片阴影，保持与全站列表页一致的扁平风格 -->
    <el-card shadow="never" class="search-card">
      <!-- inline 行内排布各筛选项；@submit.prevent 拦截原生表单提交，避免回车触发表单刷新页面 -->
      <el-form :model="query" inline @submit.prevent>
        <!-- 按所属模板筛选字段：clearable 允许清空，清空后查全部字段 -->
        <el-form-item label="所属模板">
          <!-- v-model 绑定 query.template_id；选项由 loadTemplates 预加载，避免每个字段行再请求模板名 -->
          <el-select v-model="query.template_id" placeholder="全部" clearable style="width: 200px">
            <!-- 以模板 id 作为提交值、名称作为显示文本；:key 保证虚拟滚动/重渲染时列表稳定 -->
            <el-option v-for="t in templateOptions" :key="t.id" :label="t.template_name" :value="t.id" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <!-- 查询：重置到第 1 页后按当前条件请求（handleSearch 内部处理翻页重置） -->
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <!-- 重置：把 query 恢复为初始值并重新查询，避免残留筛选条件 -->
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 表格区：承载字段列表与分页 -->
    <el-card shadow="never" class="table-card">
      <!-- 卡片头部插槽：只放操作按钮，保持表格上方工具栏独立 -->
      <template #header>
        <div class="card-header">
          <div class="card-actions">
            <!-- 新增：打开弹窗并重置表单为初始值 -->
            <el-button type="primary" :icon="Plus" @click="openCreate">新增</el-button>
            <!-- 批量删除：无勾选时禁用，避免空数组请求；selection 由表格勾选事件同步 -->
            <el-button type="danger" plain :icon="Delete" :disabled="!selection.length" @click="handleBatchDelete">批量删除</el-button>
          </div>
        </div>
      </template>
      <!-- v-loading 在请求期间显示遮罩；stripe 斑马纹便于横向阅读；empty-text 无数据时的占位文案 -->
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据" @selection-change="onSelectionChange">
        <!-- 序号列由表格自动生成，仅用于展示行号，不参与数据 -->
        <el-table-column type="index" label="序号" width="70" align="center" />
        <!-- 勾选列：配合 selection 实现批量删除 -->
        <el-table-column type="selection" width="50" />
        <!-- 所属模板：接口只返回 template_id，这里用本地模板缓存翻译成名称，缺失时回退显示 id -->
        <el-table-column label="所属模板" min-width="140">
          <template #default="{ row }">{{ getTemplateName(row.template_id) }}</template>
        </el-table-column>
        <!-- 字段名是导入时匹配 Excel 列的内部标识（如 user_name），show-overflow-tooltip 过长时悬浮看全 -->
        <el-table-column label="字段名" prop="column_name" min-width="140" show-overflow-tooltip />
        <!-- 表头是导出/导入模板里展示给用户的中文名（如 用户名） -->
        <el-table-column label="表头" prop="column_header" min-width="140" show-overflow-tooltip />
        <!-- 必填标识：1=必填（红色高亮，提示导入校验会拦截空值），0=可选（灰色弱化） -->
        <el-table-column label="必填" width="80" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.is_required===1" size="small" type="danger">必填</el-tag>
            <el-tag v-else size="small" type="info">可选</el-tag>
          </template>
        </el-table-column>
        <!-- 数据类型决定单元格解析方式（字符串/整数/小数/日期/布尔），直接展示后端存储值 -->
        <el-table-column label="数据类型" prop="data_type" width="110" />
        <!-- 最大长度用于后端/导入时的长度校验 -->
        <el-table-column label="最大长度" prop="max_length" width="90" />
        <!-- sort 控制字段在模板中的展示顺序，数值越小越靠前 -->
        <el-table-column label="排序" prop="sort" width="70" />
        <!-- 创建时间由后端生成，仅展示不做编辑 -->
        <el-table-column label="创建时间" prop="create_time" width="170" />
        <!-- 操作列固定在右侧，横向滚动时始终可见；op-col 为全局样式类 -->
        <el-table-column label="操作" width="180" fixed="right" class-name="op-col">
          <template #default="{ row }">
            <!-- 编辑：把整行回填进表单，避免缺失隐藏字段导致更新覆盖为空 -->
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <!-- 删除：单条删除，内部先二次确认再请求 -->
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <!-- 分页容器：统一样式间距 -->
      <div class="pagination-wrap">
        <!-- background 带底色按钮；layout 依次为总数/每页条数/上一页/页码/下一页/跳转 -->
        <el-pagination background layout="total, sizes, prev, pager, next, jumper"
          :total="total" v-model:current-page="query.page" v-model:page-size="query.page_size"
          :page-sizes="[10, 20, 50, 100]" @change="fetchList" />
      </div>
    </el-card>

    <!-- 新增/编辑弹窗：标题随模式切换；close-on-click-modal=false 防止误点遮罩丢失填写内容；
         destroy-on-close 关闭后销毁内部组件，下次打开时表单与校验状态都是全新的 -->
    <el-dialog :title="dialogTitle" v-model="dialogVisible" width="560px" :close-on-click-modal="false" destroy-on-close>
      <!-- ref 用于提交时调用 validate；:rules 绑定校验规则；label-width 统一标签宽度保持对齐 -->
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <!-- gutter=12 控制栅格间距，两列排布让字段较少的表单更紧凑 -->
        <el-row :gutter="12">
          <el-col :span="24">
            <!-- 所属模板必填：字段必须挂到某个导入模板下才有意义，rules 中触发方式为 change -->
            <el-form-item label="所属模板" prop="template_id">
              <el-select v-model="form.template_id" placeholder="请选择模板" style="width:100%">
                <!-- 复用列表页加载的模板选项，避免重复请求 -->
                <el-option v-for="t in templateOptions" :key="t.id" :label="t.template_name" :value="t.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <!-- 字段名：数据库/程序使用的英文标识，必填，最长 100 字符 -->
            <el-form-item label="字段名" prop="column_name">
              <el-input v-model="form.column_name" placeholder="如 user_name" maxlength="100" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <!-- 表头名称：模板中展示的中文列名，建议与字段语义一致便于用户填写 -->
            <el-form-item label="表头名称" prop="column_header">
              <el-input v-model="form.column_header" placeholder="如 用户名" maxlength="100" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <!-- 数据类型：决定导入时对该列值的解析与校验方式，选项值与后端枚举一致 -->
            <el-form-item label="数据类型" prop="data_type">
              <el-select v-model="form.data_type" style="width:100%">
                <el-option label="字符串" value="string" />
                <el-option label="整数" value="integer" />
                <el-option label="小数" value="decimal" />
                <el-option label="日期" value="date" />
                <el-option label="布尔" value="boolean" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <!-- 最大长度：限制 1~2000，避免录入过小值导致正常数据被截断或过大值失去校验意义 -->
            <el-form-item label="最大长度" prop="max_length">
              <el-input-number v-model="form.max_length" :min="1" :max="2000" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <!-- 排序：从 0 开始，数值越小越靠前，用于控制生成模板中的列顺序 -->
            <el-form-item label="排序" prop="sort">
              <el-input-number v-model="form.sort" :min="0" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <!-- 是否必填：开关直接映射后端 1/0，文字提示让含义更直观 -->
            <el-form-item label="是否必填" prop="is_required">
              <el-switch v-model="form.is_required" :active-value="1" :inactive-value="0" active-text="必填" inactive-text="可选" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <!-- 弹窗底部：取消仅关闭不保存，确定走 submitForm（内部先校验再提交并控制 loading） -->
      <template #footer>
        <el-button @click="dialogVisible=false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitForm">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
// ref/reactive 声明响应式数据，onMounted 在页面挂载后首次加载数据
import { ref, reactive, onMounted } from 'vue'
// ElMessage 用于轻量提示（成功/失败），ElMessageBox 用于删除等危险操作的二次确认框
import { ElMessage, ElMessageBox } from 'element-plus'
// 从图标库按需引入四个操作图标，分别用于查询/重置/新增/删除按钮，避免全量引入增大包体积
import { Search, Refresh, Plus, Delete } from '@element-plus/icons-vue'
// 统一请求实例：已内置 baseURL、token 注入与错误提示，业务层只关心业务数据
import request from '@/utils/request'

// 列表请求中显示 loading 遮罩，防止重复点击与误操作
const loading = ref(false)
// 当前页字段列表数据，来自接口 res.data.list
const rows = ref([])
// 记录总数，供分页组件与页面头部统计使用
const total = ref(0)
// 表格当前勾选的行，批量删除时取其 id 集合
const selection = ref([])
// 表单提交中状态，用于锁定“确定”按钮避免重复提交
const saving = ref(false)
// 新增/编辑弹窗显隐开关
const dialogVisible = ref(false)
// 弹窗标题，按新增/编辑动态切换，让用户明确当前操作
const dialogTitle = ref('新增模板字段')
// 表单组件实例引用，提交前通过它触发 validate 校验
const formRef = ref()
// 所属模板下拉选项缓存，列表翻译模板名称与表单选择共用，避免重复请求
const templateOptions = ref([])

// 查询条件初始值：单独保存一份，重置时用它整体还原，避免逐字段手写遗漏
const query_orig = { page: 1, page_size: 10, template_id: null }
// 查询条件响应式副本：分页组件与筛选控件直接修改此对象
const query = reactive({ ...query_orig })

// 表单初始值：id 为 null 表示新增；字符串字段给空、数值给 0，保证 v-model 类型稳定
const form_orig = {
  id: null, template_id: null, column_name: '', column_header: '',
  is_required: 0, data_type: 'string', max_length: 100, sort: 0
}
// 弹窗表单响应式副本，新增时重置、编辑时用 Object.assign 回填
const form = reactive({ ...form_orig })

// 校验规则：模板必选（change 触发，选择后立即消除报错）；字段名必填（blur 触发，输入框失焦时校验）
const rules = {
  template_id: [{ required: true, message: '请选择所属模板', trigger: 'change' }],
  column_name: [{ required: true, message: '请输入字段名', trigger: 'blur' }]
}

// 本模块接口前缀，集中一处便于后续统一调整路由
const apiBase = '/imprint/column'

// 把 template_id 翻译成模板名称：列表接口只返回 id，展示名称更可读
function getTemplateName(id) {
  // 空值（字段未关联模板）直接显示占位符，避免调用 find 出错
  if (!id) return '-'
  // 在已缓存的模板选项中查找匹配项
  const t = templateOptions.value.find(x => x.id === id)
  // 找不到（模板已删除/超出缓存范围）时退化为显示原始 id，保证信息不丢
  return t ? t.template_name : id
}

// 预加载模板下拉选项：一次取 200 条作为上限，供筛选与表单共用
async function loadTemplates() {
  try {
    const res = await request.get('/imprint/template/list', { params: { page: 1, page_size: 200 } })
    // 接口异常或返回空时降级为空数组，避免下拉渲染报错
    templateOptions.value = res.data.list || []
  // 模板加载失败不阻断主表格展示，这里静默忽略（错误提示已由 request 拦截器统一处理）
  } catch (e) { /* ignore */ }
}

// 查询列表：把当前 query（含分页、筛选）整体作为参数发给后端
async function fetchList() {
  loading.value = true
  try {
    const res = await request.get(apiBase + '/list', { params: query })
    // 后端无数据时 list 可能为 null，统一兜底成数组
    rows.value = res.data.list || []
    // total 兜底为 0，防止分页组件收到 undefined
    total.value = res.data.total || 0
  // 无论成功失败都关闭 loading，避免请求异常后遮罩一直停留
  } finally { loading.value = false }
}

// 查询：重置到第一页再请求，避免停留在越界页码导致空列表
function handleSearch() { query.page = 1; fetchList() }
// 重置：先整体还原查询条件（含分页），再按默认条件查询
function handleReset() { Object.assign(query, query_orig); handleSearch() }
// 表格勾选变化时同步选中行，供批量删除使用
function onSelectionChange(r) { selection.value = r }

// 新增：先把表单恢复初始值（清掉上次编辑残留），再打开弹窗
function openCreate() { Object.assign(form, form_orig); dialogTitle.value = '新增模板字段'; dialogVisible.value = true }
// 编辑：先重置为初始值再覆盖整行数据，保证行里缺失的字段使用默认值而非上次残留
function openEdit(row) { Object.assign(form, form_orig, row); dialogTitle.value = '编辑模板字段'; dialogVisible.value = true }

// 表单提交：新增走 create，编辑走 update/{id}，成功后关闭弹窗并刷新列表
async function submitForm() {
  // 先做前端校验；校验不通过会抛错并中断后续提交
  await formRef.value.validate()
  saving.value = true
  try {
    // id 存在说明是编辑态
    if (form.id) {
      // 解构剔除 id，避免把路径参数 id 又放进请求体造成后端校验冲突
      const { id, ...data } = form
      await request.put(`${apiBase}/update/${id}`, data); ElMessage.success('更新成功')
    } else {
      // 新增：直接把表单提交给创建接口
      await request.post(apiBase + '/create', form); ElMessage.success('新增成功')
    }
    // 成功后关闭弹窗并刷新当前页数据，让用户立即看到结果
    dialogVisible.value = false; fetchList()
  // 失败时只解除按钮 loading，弹窗保持打开以便用户修改后重试
  } finally { saving.value = false }
}

// 单条删除：先二次确认（防误删），确认框取消会抛错从而中断删除
async function handleDelete(row) {
  await ElMessageBox.confirm('确定删除该字段？', '提示', { type: 'warning' })
  // DELETE 带 body 时需用 data 字段传参；ids 统一用数组，与批量删除接口保持一致
  await request.delete(apiBase + '/delete', { data: { ids: [row.id] } })
  ElMessage.success('删除成功'); fetchList()
}

// 批量删除：把勾选行映射成 id 数组一次性提交
async function handleBatchDelete() {
  await ElMessageBox.confirm(`确定删除选中的 ${selection.value.length} 条？`, '提示', { type: 'warning' })
  await request.delete(apiBase + '/delete', { data: { ids: selection.value.map(r => r.id) } })
  ElMessage.success('批量删除成功'); fetchList()
}

// 页面挂载后并行发起两个请求：模板选项用于翻译/下拉，字段列表用于首屏表格
onMounted(() => { loadTemplates(); fetchList() })
</script>
