<template>
  <!-- 文件说明：水印(imprint)模块「打印模板」维护页，维护可套打/打印的 HTML 模板及其纸张、默认标记与启停状态。
       依赖：@/utils/request 统一请求；后端接口 /imprint/print/*。
       被使用：由水印相关菜单路由加载，打印/导出业务按 template_key、biz_type 取用此处配置。 -->
  <div class="app-container">
    <!-- 页面头部：标题 + 记录总数 -->
    <div class="page-header">
      <!-- 标题区：主标题与当前查询结果条数 -->
      <div class="page-title-wrap">
        <h2>打印模板管理</h2>
        <!-- total 取自列表接口，用于让用户了解模板数量规模 -->
        <div class="sub">打印模板管理 · 共 {{ total }} 条</div>
      </div>
    </div>

    <!-- 查询区：shadow="never" 去掉阴影，与全站列表页保持一致 -->
    <el-card shadow="never" class="search-card">
      <!-- inline 行内排布筛选项；@submit.prevent 阻止原生提交，避免回车时刷新页面 -->
      <el-form :model="query" inline @submit.prevent>
        <!-- 模板名称：模糊匹配；@keyup.enter 回车即查询，符合用户搜索习惯 -->
        <el-form-item label="模板名称">
          <el-input v-model="query.template_name" placeholder="请输入模板名称" clearable style="width: 170px" @keyup.enter="handleSearch" />
        </el-form-item>
        <!-- 模板Key：业务侧引用模板的唯一标识，支持按 key 精确定位 -->
        <el-form-item label="模板Key">
          <el-input v-model="query.template_key" placeholder="请输入模板Key" clearable style="width: 170px" @keyup.enter="handleSearch" />
        </el-form-item>
        <!-- 业务类型：区分不同业务场景（如 order），用于筛选同一业务下的多套模板 -->
        <el-form-item label="业务类型">
          <el-input v-model="query.biz_type" placeholder="请输入业务类型" clearable style="width: 130px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item>
          <!-- 查询：回到第一页并按条件请求 -->
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <!-- 重置：恢复默认查询条件（含分页）后重新查询 -->
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 表格区：承载打印模板列表与分页 -->
    <el-card shadow="never" class="table-card">
      <!-- 卡片头部插槽：工具栏按钮独立于表格内容 -->
      <template #header>
        <div class="card-header">
          <div class="card-actions">
            <!-- 新增：重置表单后打开弹窗 -->
            <el-button type="primary" :icon="Plus" @click="openCreate">新增</el-button>
            <!-- 批量删除：未勾选时禁用，避免空请求；selection 由表格勾选事件维护 -->
            <el-button type="danger" plain :icon="Delete" :disabled="!selection.length" @click="handleBatchDelete">批量删除</el-button>
          </div>
        </div>
      </template>
      <!-- v-loading 请求期遮罩；stripe 斑马纹；empty-text 无数据占位 -->
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据" @selection-change="onSelectionChange">
        <!-- 自动序号列，仅用于阅读定位 -->
        <el-table-column type="index" label="序号" width="70" align="center" />
        <!-- 勾选列：支撑批量删除 -->
        <el-table-column type="selection" width="50" />
        <!-- 模板名称：用户可读的模板标题，过长时悬浮提示 -->
        <el-table-column label="模板名称" prop="template_name" min-width="180" show-overflow-tooltip />
        <!-- 模板Key：程序引用模板的唯一键，展示出来便于开发/业务核对 -->
        <el-table-column label="模板Key" prop="template_key" min-width="140" show-overflow-tooltip />
        <!-- 业务类型：标识该模板归属的业务场景 -->
        <el-table-column label="业务类型" prop="biz_type" width="120" />
        <!-- 纸张尺寸：A4/A5/B5/custom，影响打印排版 -->
        <el-table-column label="纸张尺寸" prop="paper_size" width="100" />
        <!-- 默认标记：is_default=1 表示该业务下的默认模板（橙色高亮），否则显示 - -->
        <el-table-column label="默认" width="70" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.is_default===1" size="small" type="warning">默认</el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <!-- 启用状态：1=启用（可被业务使用，绿色）；0=停用（灰色，不参与打印选择） -->
        <el-table-column label="状态" width="80" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.status===1" size="small" type="success">启用</el-tag>
            <el-tag v-else size="small" type="info">停用</el-tag>
          </template>
        </el-table-column>
        <!-- 创建时间由后端写入，前端只展示 -->
        <el-table-column label="创建时间" prop="create_time" width="170" />
        <!-- 操作列固定右侧，避免横向滚动后按钮不可见 -->
        <el-table-column label="操作" width="180" fixed="right" class-name="op-col">
          <template #default="{ row }">
            <!-- 编辑：整行回填表单 -->
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <!-- 删除：单条删除，带二次确认 -->
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <!-- 分页：@change 同时响应页码与每页条数变化 -->
      <div class="pagination-wrap">
        <el-pagination background layout="total, sizes, prev, pager, next, jumper"
          :total="total" v-model:current-page="query.page" v-model:page-size="query.page_size"
          :page-sizes="[10, 20, 50, 100]" @change="fetchList" />
      </div>
    </el-card>

    <!-- 新增/编辑弹窗：标题动态；禁止点遮罩关闭防止内容丢失；destroy-on-close 让每次打开都是干净表单 -->
    <el-dialog :title="dialogTitle" v-model="dialogVisible" width="760px" :close-on-click-modal="false" destroy-on-close>
      <!-- ref 供提交时校验；rules 控制必填项；label-width 统一标签宽度 -->
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <!-- 两列栅格，HTML 内容与备注占满整行便于编辑 -->
        <el-row :gutter="12">
          <el-col :span="12">
            <!-- 模板名称：展示用标题，必填 -->
            <el-form-item label="模板名称" prop="template_name">
              <el-input v-model="form.template_name" placeholder="请输入模板名称" maxlength="100" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <!-- 模板Key：业务唯一标识，编辑态禁用（!!form.id 为真即已存在），避免改 key 造成业务引用失效 -->
            <el-form-item label="模板Key" prop="template_key">
              <el-input v-model="form.template_key" placeholder="唯一标识" maxlength="64" :disabled="!!form.id" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <!-- 业务类型：标识模板服务于哪类业务，必填 -->
            <el-form-item label="业务类型" prop="biz_type">
              <el-input v-model="form.biz_type" placeholder="如 order" maxlength="64" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <!-- 纸张尺寸：A4/A5/B5 为常用规格，custom 表示自定义尺寸 -->
            <el-form-item label="纸张尺寸" prop="paper_size">
              <el-select v-model="form.paper_size" style="width:100%">
                <el-option label="A4" value="A4" />
                <el-option label="A5" value="A5" />
                <el-option label="B5" value="B5" />
                <el-option label="自定义" value="custom" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <!-- 是否默认：1/0 直接映射后端，同业务下建议只保留一个默认模板 -->
            <el-form-item label="是否默认" prop="is_default">
              <el-switch v-model="form.is_default" :active-value="1" :inactive-value="0" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <!-- 状态：启用后业务可选择该模板，停用则保留配置但不参与打印 -->
            <el-form-item label="状态" prop="status">
              <el-switch v-model="form.status" :active-value="1" :inactive-value="0" active-text="启用" inactive-text="停用" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <!-- HTML内容：即打印模板本体，支持占位符渲染；必填，10 行高度便于快速预览结构 -->
            <el-form-item label="HTML内容" prop="html_content">
              <el-input v-model="form.html_content" type="textarea" :rows="10" placeholder="请输入打印模板HTML内容" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <!-- 备注：内部说明用途，可为空 -->
            <el-form-item label="备注" prop="remark">
              <el-input v-model="form.remark" type="textarea" :rows="2" placeholder="请输入备注" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <!-- 底部按钮：取消只关闭弹窗；确定提交并由 saving 控制 loading -->
      <template #footer>
        <el-button @click="dialogVisible=false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitForm">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
// 响应式数据与挂载钩子
import { ref, reactive, onMounted } from 'vue'
// 消息提示与确认框：成功后提示、删除前二次确认
import { ElMessage, ElMessageBox } from 'element-plus'
// 按钮图标：查询/重置/新增/批量删除，按需引入减小体积
import { Search, Refresh, Plus, Delete } from '@element-plus/icons-vue'
// 统一请求封装（已处理 token、统一错误提示与 401 跳转）
import request from '@/utils/request'

// 列表请求加载状态，控制表格遮罩
const loading = ref(false)
// 当前页打印模板数据
const rows = ref([])
// 总记录数，供分页与页面统计
const total = ref(0)
// 表格勾选行，批量删除时取 id
const selection = ref([])
// 提交中状态，防止“确定”重复点击
const saving = ref(false)
// 弹窗显隐
const dialogVisible = ref(false)
// 弹窗标题：新增/编辑切换，提示当前模式
const dialogTitle = ref('新增打印模板')
// 表单实例，提交前调用 validate
const formRef = ref()

// 查询条件初始值，重置时整体还原；三个字符串条件默认为空表示不限
const query_orig = { page: 1, page_size: 10, template_name: '', template_key: '', biz_type: '' }
// 查询条件响应式副本，直接绑定到筛选控件与分页组件
const query = reactive({ ...query_orig })

// 表单初始值：id 为 null 表示新增；默认纸张 A4、启用状态、非默认，符合多数场景
const form_orig = {
  id: null, template_name: '', template_key: '', biz_type: '', paper_size: 'A4',
  is_default: 0, status: 1, html_content: '', remark: ''
}
// 弹窗表单响应式副本
const form = reactive({ ...form_orig })

// 校验规则：名称、Key、HTML 内容必填；blur 触发，避免输入过程中频繁报错
const rules = {
  template_name: [{ required: true, message: '请输入模板名称', trigger: 'blur' }],
  template_key: [{ required: true, message: '请输入模板Key', trigger: 'blur' }],
  html_content: [{ required: true, message: '请输入HTML内容', trigger: 'blur' }]
}

// 本模块接口前缀，统一维护
const apiBase = '/imprint/print'

// 查询列表：query 中同时包含分页与筛选条件，整体传给后端
async function fetchList() {
  loading.value = true
  try {
    const res = await request.get(apiBase + '/list', { params: query })
    // 空结果兜底为数组，保证表格正常渲染空状态
    rows.value = res.data.list || []
    // 总数兜底为 0，避免分页参数异常
    total.value = res.data.total || 0
  // 无论成功/失败都解除 loading，防止异常后遮罩卡住
  } finally { loading.value = false }
}

// 查询：回到第一页再请求，避免页码越界
function handleSearch() { query.page = 1; fetchList() }
// 重置：还原查询条件后查询
function handleReset() { Object.assign(query, query_orig); handleSearch() }
// 表格勾选变化：同步选中行给批量删除使用
function onSelectionChange(r) { selection.value = r }

// 新增：清空表单残留数据并切换标题后打开弹窗
function openCreate() { Object.assign(form, form_orig); dialogTitle.value = '新增打印模板'; dialogVisible.value = true }
// 编辑：先重置默认值再回填整行，避免行内缺失字段沿用上次编辑内容
function openEdit(row) { Object.assign(form, form_orig, row); dialogTitle.value = '编辑打印模板'; dialogVisible.value = true }

// 提交表单：按 id 判断新增还是更新，成功后关闭弹窗并刷新列表
async function submitForm() {
  // 校验不通过会抛出异常，后续代码不执行
  await formRef.value.validate()
  saving.value = true
  try {
    if (form.id) {
      // 编辑：剔除 id 后提交其余字段，id 作为路径参数
      const { id, ...data } = form
      await request.put(`${apiBase}/update/${id}`, data); ElMessage.success('更新成功')
    } else {
      // 新增：整份表单提交
      await request.post(apiBase + '/create', form); ElMessage.success('新增成功')
    }
    // 成功后关闭弹窗并刷新当前列表
    dialogVisible.value = false; fetchList()
  // 失败仅释放按钮，弹窗保留便于修正
  } finally { saving.value = false }
}

// 单条删除：确认后按 ids 数组提交（与批量删除共用接口）
async function handleDelete(row) {
  await ElMessageBox.confirm('确定删除该打印模板？', '提示', { type: 'warning' })
  await request.delete(apiBase + '/delete', { data: { ids: [row.id] } })
  ElMessage.success('删除成功'); fetchList()
}

// 批量删除：取所有勾选行 id 一次性提交
async function handleBatchDelete() {
  await ElMessageBox.confirm(`确定删除选中的 ${selection.value.length} 条？`, '提示', { type: 'warning' })
  await request.delete(apiBase + '/delete', { data: { ids: selection.value.map(r => r.id) } })
  ElMessage.success('批量删除成功'); fetchList()
}

// 挂载后立即拉取第一页数据
onMounted(fetchList)
</script>
