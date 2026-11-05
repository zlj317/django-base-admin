<!-- 流程表单管理页（workflow/form/index.vue）
     职责：维护业务表单的元信息（名称/标识/状态），并内置字段设计器为表单增删字段、实时预览，
           最终把字段定义序列化为 form_json 保存。
     依赖：Element Plus、@/utils/request、@/components/workflow/FormRenderer.vue（表单预览渲染）。
     被谁使用：工作流管理菜单下的「流程表单」路由页面；流程模型可绑定这里维护的表单。 -->
<template>
  <!-- 页面根容器：沿用全局 app-container 内边距 -->
  <div class="app-container">
    <!-- 页面头部：标题与记录数 -->
    <div class="page-header">
      <div class="page-title-wrap">
        <h2>流程表单</h2>
        <!-- 副标题：说明表单用于业务填写并展示总记录数 -->
        <div class="sub">自定义业务表单设计与绑定 · 共 {{ total }} 条记录</div>
      </div>
    </div>

    <!-- 查询条件卡片 -->
    <el-card shadow="never" class="search-card">
      <!-- 内联查询表单；阻止原生提交，回车由输入框单独触发查询 -->
      <el-form :model="query" inline @submit.prevent>
        <el-form-item label="表单名称">
          <!-- 名称模糊查询 -->
          <el-input v-model="query.form_name" placeholder="请输入表单名称" clearable style="width: 180px" @keyup.enter="handleQuery" />
        </el-form-item>
        <el-form-item label="表单标识">
          <!-- 标识（form_key）查询，用于快速定位 -->
          <el-input v-model="query.form_key" placeholder="请输入表单标识" clearable style="width: 180px" @keyup.enter="handleQuery" />
        </el-form-item>
        <el-form-item class="search-actions">
          <el-button type="primary" :icon="Search" @click="handleQuery">查询</el-button>
          <el-button :icon="Refresh" @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 表单列表卡片 -->
    <el-card shadow="never" class="table-card">
      <template #header>
        <div class="card-header">
          <div class="card-actions">
            <!-- 新增表单：仅创建元信息，字段在设计器中维护 -->
            <el-button v-perm="'wf:form:create'" type="primary" :icon="Plus" @click="openCreate">新增</el-button>
            <!-- 批量删除：无勾选时禁用 -->
            <el-button v-perm="'wf:form:delete'" type="danger" plain :icon="Delete" :disabled="!selectedIds.length" @click="handleBatchDelete">批量删除</el-button>
          </div>
        </div>
      </template>
      <!-- 表格：勾选变化同步 selectedIds 供批量删除使用 -->
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据" @selection-change="onSelectionChange">
        <el-table-column type="index" label="序号" width="70" align="center" />
        <el-table-column type="selection" width="50" align="center" />
        <!-- 表单名称：展示用，发起流程时作为页面标题参考 -->
        <el-table-column label="表单名称" prop="form_name" min-width="160" show-overflow-tooltip />
        <!-- 表单标识：唯一 key，字段值按 key 存储 -->
        <el-table-column label="表单标识" prop="form_key" min-width="150" show-overflow-tooltip />
        <el-table-column label="字段数" width="90" align="center">
          <!-- 字段数不入库为独立列，由 form_json 解析后统计 -->
          <template #default="scope">{{ fieldCount(scope.row) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="90" align="center">
          <template #default="scope">
            <!-- 注意：表单状态 0=启用、其他=停用，与流程模型的 0=草稿语义不同 -->
            <el-tag :type="scope.row.status === 0 ? 'success' : 'info'">{{ scope.row.status === 0 ? '启用' : '停用' }}</el-tag>
          </template>
        </el-table-column>
        <!-- 备注：辅助说明表单用途 -->
        <el-table-column label="备注" prop="remark" min-width="150" show-overflow-tooltip />
        <!-- 创建时间：后端格式化的时间字符串 -->
        <el-table-column label="创建时间" prop="create_time" width="170" />
        <!-- 操作列固定右侧 -->
        <el-table-column label="操作" width="220" align="center" fixed="right">
          <template #default="scope">
            <!-- 设计表单：打开字段设计器弹窗 -->
            <el-button v-perm="'wf:form:update'" link type="primary" :icon="Grid" @click="openDesign(scope.row)">设计表单</el-button>
            <!-- 编辑：修改名称/状态/备注等元信息 -->
            <el-button v-perm="'wf:form:update'" link type="primary" :icon="Edit" @click="openEdit(scope.row)">编辑</el-button>
            <!-- 删除：删除该表单及其字段定义 -->
            <el-button v-perm="'wf:form:delete'" link type="danger" :icon="Delete" @click="handleDelete(scope.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <!-- 分页：页码/条数双向绑定到 query，变化即重新拉取 -->
      <div class="pagination-wrap">
        <el-pagination background layout="total, sizes, prev, pager, next, jumper"
          :total="total" v-model:current-page="query.page" v-model:page-size="query.page_size"
          :page-sizes="[10, 20, 50, 100]" @change="getList" />
      </div>
    </el-card>

    <!-- 新增/编辑表单元信息弹窗：关闭即销毁，避免校验状态残留 -->
    <el-dialog :title="form.id ? '编辑流程表单' : '新增流程表单'" v-model="dialogVisible" width="540px" :close-on-click-modal="false" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="表单名称" prop="form_name">
          <!-- 展示名称，如“请假申请单” -->
          <el-input v-model="form.form_name" placeholder="如：请假申请单" />
        </el-form-item>
        <el-form-item label="表单标识" prop="form_key">
          <!-- 唯一标识：编辑时禁用，因为它决定流程实例中表单数据的存储键 -->
          <el-input v-model="form.form_key" placeholder="唯一标识，如 leave_form" :disabled="!!form.id" />
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <!-- 0=启用、1=停用；停用后新流程不应再选择该表单 -->
          <el-radio-group v-model="form.status">
            <el-radio :label="0">启用</el-radio>
            <el-radio :label="1">停用</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="备注" prop="remark">
          <el-input v-model="form.remark" type="textarea" :rows="3" placeholder="请输入备注" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitForm">确定</el-button>
      </template>
    </el-dialog>

    <!-- 表单设计弹窗：左侧字段列表 + 右侧实时预览；1000px 宽保证两栏可读，top=5vh 给长列表留高度 -->
    <el-dialog v-model="designVisible" :title="`表单设计 · ${design.form_name}`" width="1000px" top="5vh" :close-on-click-modal="false" destroy-on-close>
      <div class="design-layout">
        <!-- 左侧：字段设计区 -->
        <div class="design-panel">
          <!-- 工具栏：添加字段 / 保存表单 -->
          <div class="design-toolbar">
            <!-- 不传 index 默认新增字段 -->
            <el-button type="primary" :icon="Plus" @click="openFieldDialog()">添加字段</el-button>
            <!-- 保存表单：把 design.fields 序列化为 form_json 提交 -->
            <el-button :icon="DocumentChecked" :loading="designSaving" @click="saveDesign">保存表单</el-button>
          </div>
          <!-- 字段列表：直接编辑 design.fields 数组，保存前只在浏览器端生效 -->
          <el-table :data="design.fields" size="small" border empty-text="暂无字段，请添加">
            <el-table-column label="字段名称" prop="label" min-width="110" />
            <el-table-column label="字段标识" prop="key" min-width="110" />
            <el-table-column label="类型" width="100" align="center">
              <!-- 类型值转中文名展示 -->
              <template #default="scope">{{ typeName(scope.row.type) }}</template>
            </el-table-column>
            <el-table-column label="必填" width="70" align="center">
              <!-- 布尔值转“是/否”，避免直接显示 true/false -->
              <template #default="scope">{{ scope.row.required ? '是' : '否' }}</template>
            </el-table-column>
            <el-table-column label="操作" width="140" align="center">
              <template #default="scope">
                <!-- 传当前行下标进入编辑态，confirmField 时按该位置替换 -->
                <el-button link type="primary" @click="openFieldDialog(scope.$index)">编辑</el-button>
                <!-- 删除字段：同步移除预览数据 -->
                <el-button link type="danger" @click="removeField(scope.$index)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
        <!-- 右侧：预览区，使用真实渲染组件保证所见即所得 -->
        <div class="design-preview">
          <div class="preview-title">表单预览</div>
          <!-- fields 为设计中的字段定义，data 为预览输入值双向绑定的对象 -->
          <FormRenderer :fields="design.fields" :data="previewData" />
        </div>
      </div>
      <template #footer>
        <el-button @click="designVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 字段编辑弹窗：append-to-body 避免被上层弹窗的层级/裁剪影响 -->
    <el-dialog v-model="fieldVisible" :title="fieldIndex >= 0 ? '编辑字段' : '添加字段'" width="520px" append-to-body :close-on-click-modal="false">
      <!-- 字段编辑表单（仅前端校验，必填与重复校验在 confirmField 中手写） -->
      <el-form :model="field" label-width="90px">
        <el-form-item label="字段名称">
          <!-- 字段标签：展示给填写人看的中文名 -->
          <el-input v-model="field.label" placeholder="如：请假天数" />
        </el-form-item>
        <el-form-item label="字段标识">
          <!-- 字段 key：编辑时禁用，因为已保存实例的数据以 key 为键 -->
          <el-input v-model="field.key" placeholder="英文标识，如 leaveDays" :disabled="fieldIndex >= 0" />
        </el-form-item>
        <el-form-item label="字段类型">
          <!-- 字段类型决定渲染控件与数据校验方式 -->
          <el-select v-model="field.type" style="width: 100%">
            <el-option v-for="item in fieldTypes" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="field.type === 'select'" label="选项">
          <!-- 仅下拉类型需要选项；用英文逗号分隔，confirmField 时拆分为数组 -->
          <el-input v-model="field.optionsText" placeholder="多个选项用英文逗号分隔，如：事假,病假,年假" />
        </el-form-item>
        <el-form-item label="必填">
          <!-- 必填开关，渲染组件据此加校验 -->
          <el-switch v-model="field.required" />
        </el-form-item>
        <el-form-item label="提示文字">
          <!-- 输入框占位/提示文案 -->
          <el-input v-model="field.placeholder" placeholder="输入框占位提示" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="fieldVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmField">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
// Vue 组合式 API：ref/reactive 管理列表、弹窗与设计器状态，onMounted 首次加载列表
import { ref, reactive, onMounted } from 'vue'
// Element Plus：成功提示与删除/警告确认
import { ElMessage, ElMessageBox } from 'element-plus'
// 按钮与操作列图标
import { Search, Refresh, Plus, Delete, Edit, Grid, DocumentChecked } from '@element-plus/icons-vue'
// 统一请求实例：携带 token、统一错误提示
import request from '@/utils/request'
// 表单渲染组件：设计器中用于实时预览字段效果
import FormRenderer from '@/components/workflow/FormRenderer.vue'

// 可选字段类型清单：同时作为 typeName 的中文名映射源，保持设计弹窗与列表展示一致
const fieldTypes = [
  // 单行文本，适合姓名、事由等短文本
  { label: '单行文本', value: 'text' },
  // 多行文本，适合说明、备注等长文本
  { label: '多行文本', value: 'textarea' },
  // 数字，适合天数、金额等数值
  { label: '数字', value: 'number' },
  // 日期，渲染为日期选择器
  { label: '日期', value: 'date' },
  // 下拉选择，需要额外配置选项
  { label: '下拉选择', value: 'select' },
  // 附件地址，保存上传后的文件 URL
  { label: '附件地址', value: 'file' }
]

// 列表加载状态
const loading = ref(false)
// 元信息弹窗提交状态
const saving = ref(false)
// 当前页表单数据
const rows = ref([])
// 记录总数
const total = ref(0)
// 已勾选表单 id，驱动批量删除
const selectedIds = ref([])
// 元信息弹窗可见性
const dialogVisible = ref(false)
// 元信息表单实例引用，用于 validate
const formRef = ref()
// 查询条件：分页 + 名称/标识筛选
const query = reactive({ page: 1, page_size: 10, form_name: '', form_key: '' })
// 元信息表单数据；status 默认 0=启用
const form = reactive({ id: 0, form_name: '', form_key: '', status: 0, remark: '' })
// 元信息校验规则：名称与标识必填
const rules = {
  form_name: [{ required: true, message: '请输入表单名称', trigger: 'blur' }],
  form_key: [{ required: true, message: '请输入表单标识', trigger: 'blur' }]
}

// 设计弹窗可见性
const designVisible = ref(false)
// 设计保存状态：驱动“保存表单”按钮 loading
const designSaving = ref(false)
// 设计中的表单：id/form_name 用于提交与标题，fields 为字段定义数组
const design = reactive({ id: 0, form_name: '', fields: [] })
// 预览数据：以字段 key 为键存放预览输入值，与 FormRenderer 的 data 双向绑定
const previewData = reactive({})

// 字段弹窗可见性
const fieldVisible = ref(false)
// 当前编辑字段的下标：-1 表示新增，>=0 表示编辑 design.fields 中对应项
const fieldIndex = ref(-1)
// 字段编辑临时对象；optionsText 保存逗号分隔的原始文本，确认时再拆分
const field = reactive({ label: '', key: '', type: 'text', required: false, placeholder: '', optionsText: '' })

// 解析后端 form_json 字段定义：非数组或 JSON 损坏时返回空数组，避免列表渲染崩溃
function parseFields(row) {
  try {
    const list = JSON.parse(row.form_json || '[]')
    return Array.isArray(list) ? list : []
  } catch (e) {
    return []
  }
}
// 列表“字段数”列：解析 form_json 后取长度（不依赖后端额外字段）
function fieldCount(row) {
  return parseFields(row).length
}
// 类型值 → 中文名：查 fieldTypes，找不到时回退原始值，保证异常数据也能展示
function typeName(type) {
  return fieldTypes.find(item => item.value === type)?.label || type
}

// 拉取表单列表：query 含分页与筛选，成功后回填 rows/total
async function getList() {
  loading.value = true
  try {
    const res = await request.get('/wf/form/list', { params: query })
    rows.value = res.data.list
    total.value = res.data.total
  } finally {
    // 成功失败都关闭 loading，避免表格一直转圈
    loading.value = false
  }
}
// 查询：回到第一页后请求，保证结果从首页展示
function handleQuery() {
  query.page = 1
  getList()
}
// 重置筛选条件（保留每页条数）
function resetQuery() {
  Object.assign(query, { page: 1, form_name: '', form_key: '' })
  getList()
}
// 勾选变化：仅保存 id 供批量删除
function onSelectionChange(rowsSelected) {
  selectedIds.value = rowsSelected.map(row => row.id)
}
// 打开新增弹窗：重置表单默认值（状态默认启用）
function openCreate() {
  Object.assign(form, { id: 0, form_name: '', form_key: '', status: 0, remark: '' })
  dialogVisible.value = true
}
// 打开编辑弹窗：回填当前行数据
function openEdit(row) {
  Object.assign(form, { id: row.id, form_name: row.form_name, form_key: row.form_key, status: row.status, remark: row.remark || '' })
  dialogVisible.value = true
}
// 提交元信息：新增时附带空字段定义 form_json='[]'，保证后续设计器可直接读取数组
async function submitForm() {
  await formRef.value.validate()
  saving.value = true
  try {
    if (form.id) {
      // 编辑：只更新元信息，字段定义由设计器单独保存
      await request.put(`/wf/form/update/${form.id}`, form)
      ElMessage.success('修改成功')
    } else {
      // 新增：初始化空字段数组，避免后端存储 null 导致解析失败
      await request.post('/wf/form/create', { ...form, form_json: '[]' })
      ElMessage.success('新增成功')
    }
    dialogVisible.value = false
    getList()
  } finally {
    saving.value = false
  }
}
// 删除单个表单：确认后按 id 删除并刷新
async function handleDelete(row) {
  await ElMessageBox.confirm(`确认删除表单「${row.form_name}」吗？`, '提示', { type: 'warning' })
  await request.delete('/wf/form/delete', { data: { ids: [row.id] } })
  ElMessage.success('删除成功')
  getList()
}
// 批量删除：删除所有勾选表单
async function handleBatchDelete() {
  await ElMessageBox.confirm(`确认删除选中的 ${selectedIds.value.length} 条表单吗？`, '提示', { type: 'warning' })
  await request.delete('/wf/form/delete', { data: { ids: selectedIds.value } })
  ElMessage.success('删除成功')
  getList()
}

// 打开表单设计器：拉取详情（含已解析的字段数组 form_json_obj），重置预览数据后初始化默认值
async function openDesign(row) {
  const res = await request.get(`/wf/form/detail/${row.id}`)
  design.id = res.data.id
  design.form_name = res.data.form_name
  // 后端直接返回解析后的数组，前端无需再 JSON.parse
  design.fields = res.data.form_json_obj || []
  // 清空上一张表单遗留的预览键，避免预览出现无关字段
  Object.keys(previewData).forEach(key => delete previewData[key])
  // 为每个字段建立预览默认值：数字用 null，其余用空串，避免类型不匹配告警
  design.fields.forEach(item => { previewData[item.key] = item.type === 'number' ? null : '' })
  designVisible.value = true
}
// 打开字段弹窗：index=-1 新增；否则回填 design.fields[index]，选项数组重新拼成逗号文本
function openFieldDialog(index = -1) {
  fieldIndex.value = index
  if (index >= 0) {
    const item = design.fields[index]
    Object.assign(field, {
      label: item.label,
      key: item.key,
      type: item.type,
      required: !!item.required,
      placeholder: item.placeholder || '',
      optionsText: (item.options || []).join(',')
    })
  } else {
    // 新增：重置为默认文本字段
    Object.assign(field, { label: '', key: '', type: 'text', required: false, placeholder: '', optionsText: '' })
  }
  fieldVisible.value = true
}
// 确认字段：校验必填、key 唯一（编辑时排除自身），构造字段对象并写回 design.fields
function confirmField() {
  if (!field.label || !field.key) {
    ElMessage.warning('请填写字段名称与字段标识')
    return
  }
  // key 是数据存储键，必须全局唯一；编辑时下标相同的旧值不算冲突
  if (design.fields.some((item, idx) => item.key === field.key && idx !== fieldIndex.value)) {
    ElMessage.warning('字段标识已存在')
    return
  }
  // 组装字段定义：仅下拉类型才写入 options 数组，其余类型不带该字段
  const item = {
    label: field.label,
    key: field.key,
    type: field.type,
    required: !!field.required,
    placeholder: field.placeholder,
    ...(field.type === 'select' ? { options: field.optionsText.split(',').map(s => s.trim()).filter(Boolean) } : {})
  }
  if (fieldIndex.value >= 0) {
    // 编辑：原位替换，保持字段顺序不变
    design.fields.splice(fieldIndex.value, 1, item)
  } else {
    // 新增：追加到末尾，同时补上预览默认值
    design.fields.push(item)
    previewData[item.key] = item.type === 'number' ? null : ''
  }
  fieldVisible.value = false
}
// 删除字段：从字段数组移除并同步清理预览数据
function removeField(index) {
  const key = design.fields[index].key
  design.fields.splice(index, 1)
  delete previewData[key]
}
// 保存表单设计：至少一个字段，序列化字段数组写入 form_json，成功后关闭弹窗并刷新列表
async function saveDesign() {
  if (!design.fields.length) {
    ElMessage.warning('请至少添加一个字段')
    return
  }
  designSaving.value = true
  try {
    // 只提交 form_json：字段定义是设计器唯一需要持久化的内容
    await request.put(`/wf/form/update/${design.id}`, { form_json: JSON.stringify(design.fields) })
    ElMessage.success('表单保存成功')
    designVisible.value = false
    getList()
  } finally {
    designSaving.value = false
  }
}

// 页面挂载后加载首屏列表
onMounted(getList)
</script>

<style scoped>
/* 样式仅作用于本页 */
.design-layout {
  /* 设计弹窗主体：左侧字段区 + 右侧预览区横向排列，顶部对齐 */
  display: flex;
  gap: 16px;
  align-items: flex-start;
}
.design-panel {
  /* 左侧字段设计区占满剩余宽度；min-width:0 防止表格横向撑破布局 */
  flex: 1;
  min-width: 0;
}
.design-toolbar {
  /* 设计器工具栏：按钮横向排列并留出下方间距 */
  display: flex;
  gap: 10px;
  margin-bottom: 12px;
}
.design-preview {
  /* 右侧预览区固定 380px 且不伸缩；浅灰底 + 边框区分编辑区，min-height 保证无字段时仍有可视化区域 */
  width: 380px;
  flex: none;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  padding: 12px;
  background: var(--el-fill-color-lighter);
  min-height: 300px;
}
.preview-title {
  /* 预览区标题：加粗并留出下方间距 */
  font-weight: 600;
  margin-bottom: 10px;
}
</style>
