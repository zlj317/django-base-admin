<!-- 文件级说明：系统编号 - 编码规则管理页。
     职责：维护流水号生成规则，并支持单条/批量“生成编号”调用后端取号接口。
     编号构成：前缀 prefix + 日期段(date_format) + 分隔符 separator + 定长序号(seq_length 位)。
     序号行为：每次取号按 step 递增，并按 reset_type（按日/按月/按年/不重置）到期归零重新计数。
     依赖：Vue 3 <script setup>、Element Plus（表格/弹窗/消息提示/图标）、@/utils/request（统一请求封装，baseURL=/api）。
     被谁使用：由 sys_no 模块的路由挂载，供业务单据（订单、工单等）统一取号。
     注意：本文件不含 <style> 块，页面样式来自全局样式表。 -->
<template>
  <!-- 页面根容器：套用全局 app-container 布局 -->
  <div class="app-container">
    <!-- 页头区域 -->
    <div class="page-header">
      <!-- 标题容器：主标题与统计信息横排 -->
      <div class="page-title-wrap">
        <!-- 页面主标题 -->
        <h2>编码规则管理</h2>
        <!-- 副标题：说明页面用途，并回显接口返回的总条数 -->
        <div class="sub">编号规则管理 · 共 {{ total }} 条</div>
      </div>
    </div>

    <!-- 查询条件卡片：shadow="never" 去掉阴影，保持后台列表页的扁平风格 -->
    <el-card shadow="never" class="search-card">
      <!-- 搜索表单：inline 横向排列；@submit.prevent 阻止回车触发默认提交刷新页面 -->
      <el-form :model="query" inline @submit.prevent>
        <!-- 规则 Key 筛选项：rule_key 是规则的程序唯一标识，业务代码按它取号 -->
        <el-form-item label="规则Key">
          <!-- 输入框：clearable 一键清空；回车即查询；固定宽度保持工具栏整齐 -->
          <el-input v-model="query.rule_key" placeholder="请输入规则Key" clearable style="width: 170px" @keyup.enter="handleSearch" />
        </el-form-item>
        <!-- 规则名称筛选项：便于按业务名称（如“订单号”）检索 -->
        <el-form-item label="规则名称">
          <!-- 输入框：回车即查询 -->
          <el-input v-model="query.rule_name" placeholder="请输入规则名称" clearable style="width: 170px" @keyup.enter="handleSearch" />
        </el-form-item>
        <!-- 启用状态筛选项：对应后端 status（1 启用 / 0 停用） -->
        <el-form-item label="状态">
          <!-- 下拉框：clearable 后可查询全部状态 -->
          <el-select v-model="query.status" placeholder="全部" clearable style="width: 110px">
            <!-- 启用：规则可被业务取号 -->
            <el-option label="启用" :value="1" />
            <!-- 停用：规则保留但不允许取号，便于停用旧编号方案 -->
            <el-option label="停用" :value="0" />
          </el-select>
        </el-form-item>
        <!-- 操作按钮行 -->
        <el-form-item>
          <!-- 查询按钮：回第 1 页并重新拉取 -->
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <!-- 重置按钮：恢复默认条件后重新查询 -->
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 数据表格卡片：头部工具栏 + 规则表格 + 分页 -->
    <el-card shadow="never" class="table-card">
      <!-- 卡片头部插槽：承载新增、批量生成编号、批量删除 -->
      <template #header>
        <!-- 头部容器 -->
        <div class="card-header">
          <!-- 操作按钮组 -->
          <div class="card-actions">
            <!-- 新增按钮：打开弹窗，预填 YYYYMMDD、4 位序号、按日重置等常用默认值 -->
            <el-button type="primary" :icon="Plus" @click="openCreate">新增</el-button>
            <!-- 批量生成编号：warning 提示这是会产生真实流水号的操作；未勾选时禁用，避免无目标调用 -->
            <el-button type="warning" :icon="MagicStick" :disabled="!selection.length" @click="handleGenerateBatch">生成编号</el-button>
            <!-- 批量删除：无勾选时禁用；plain 弱化危险按钮视觉 -->
            <el-button type="danger" plain :icon="Delete" :disabled="!selection.length" @click="handleBatchDelete">批量删除</el-button>
          </div>
        </div>
      </template>
      <!-- 表格：v-loading 显示加载遮罩；stripe 斑马纹；selection-change 同步选中行 -->
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据" @selection-change="onSelectionChange">
        <!-- 序号列：按当前页顺序自动编号 -->
        <el-table-column type="index" label="序号" width="70" align="center" />
        <!-- 多选列：为批量生成与批量删除提供目标集合 -->
        <el-table-column type="selection" width="50" />
        <!-- 规则 Key 列：程序调用取号接口时使用的唯一标识 -->
        <el-table-column label="规则Key" prop="rule_key" min-width="140" show-overflow-tooltip />
        <!-- 规则名称列：业务可读名称，便于识别编号用途 -->
        <el-table-column label="规则名称" prop="rule_name" min-width="180" show-overflow-tooltip />
        <!-- 前缀列：编号的固定开头，如 NO、ORD -->
        <el-table-column label="前缀" prop="prefix" width="100" />
        <!-- 日期格式列：决定日期段样式，常见 YYYYMMDD（20261105）、YYYYMM、YYYY，空值表示不带日期 -->
        <el-table-column label="日期格式" prop="date_format" width="110" />
        <!-- 序列长度列：序号补零后的位数，如 4 表示 0001 -->
        <el-table-column label="序列长度" prop="seq_length" width="90" />
        <!-- 步长列：每次取号的递增幅度，1 为连续编号，大于 1 可预留号段 -->
        <el-table-column label="步长" prop="step" width="70" />
        <!-- 分隔符列：拼接各段用的字符，如 "-" 得到 NO-20261105-0001 -->
        <el-table-column label="分隔符" prop="separator" width="90" />
        <!-- 重置方式列：决定序号何时归零重新计数 -->
        <el-table-column label="重置方式" width="100">
          <!-- 默认插槽：按 reset_type 渲染中文标签 -->
          <template #default="{ row }">
            <!-- 按日：跨天后序号重新从起始值计数 -->
            <el-tag v-if="row.reset_type==='day'" size="small">按日</el-tag>
            <!-- 按月：跨月后序号归零 -->
            <el-tag v-else-if="row.reset_type==='month'" size="small" type="success">按月</el-tag>
            <!-- 按年：跨年后序号归零 -->
            <el-tag v-else-if="row.reset_type==='year'" size="small" type="warning">按年</el-tag>
            <!-- 不重置：全局持续递增，适合合同号等长期唯一编号 -->
            <el-tag v-else-if="row.reset_type==='none'" size="small" type="info">不重置</el-tag>
            <!-- 兜底：未知枚举直接展示原值，便于排查脏数据 -->
            <span v-else>{{ row.reset_type }}</span>
          </template>
        </el-table-column>
        <!-- 状态列：规则是否允许被取号 -->
        <el-table-column label="状态" width="80" align="center">
          <!-- 默认插槽：按 status 渲染启停标签 -->
          <template #default="{ row }">
            <!-- 启用：status=1 -->
            <el-tag v-if="row.status===1" size="small" type="success">启用</el-tag>
            <!-- 其余值按停用展示 -->
            <el-tag v-else size="small" type="info">停用</el-tag>
          </template>
        </el-table-column>
        <!-- 备注列：规则用途说明 -->
        <el-table-column label="备注" prop="remark" min-width="150" show-overflow-tooltip />
        <!-- 创建时间列 -->
        <el-table-column label="创建时间" prop="create_time" width="170" />
        <!-- 操作列：横向滚动时固定在右侧 -->
        <el-table-column label="操作" width="240" fixed="right" class-name="op-col">
          <!-- 默认插槽：行级操作 -->
          <template #default="{ row }">
            <!-- 生成编号：对该规则调用一次取号接口，后端会占用一个真实序号 -->
            <el-button link type="warning" :icon="MagicStick" @click="handleGenerate(row)">生成编号</el-button>
            <!-- 编辑：把当前行带入共用弹窗；规则 Key 在编辑态禁用，防止改标识影响业务调用 -->
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <!-- 删除：单条删除前二次确认 -->
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <!-- 分页容器 -->
      <div class="pagination-wrap">
        <!-- 分页：页码与每页条数双向绑定 query，变化触发 @change 重新查询 -->
        <el-pagination background layout="total, sizes, prev, pager, next, jumper"
          :total="total" v-model:current-page="query.page" v-model:page-size="query.page_size"
          :page-sizes="[10, 20, 50, 100]" @change="fetchList" />
        <!-- 说明：每页可选 10/20/50/100 条 -->
      </div>
    </el-card>

    <!-- 新增/编辑弹窗：共用一套表单；width 680px 以容纳 8/24 栅格的三列布局 -->
    <el-dialog :title="dialogTitle" v-model="dialogVisible" width="680px" :close-on-click-modal="false" destroy-on-close>
      <!-- 表单：formRef 用于提交校验；label-width 100px 统一标签宽度 -->
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <!-- 栅格布局：gutter=12；每行 24 栅格 -->
        <el-row :gutter="12">
          <!-- 规则 Key：半行 -->
          <el-col :span="12">
            <!-- 表单项：rule_key 必填，编辑态禁用 -->
            <el-form-item label="规则Key" prop="rule_key">
              <!-- 输入框：:disabled="!!form.id" 表示已有 id（编辑态）时不允许修改唯一标识 -->
              <el-input v-model="form.rule_key" placeholder="唯一标识" maxlength="64" :disabled="!!form.id" />
            </el-form-item>
          </el-col>
          <!-- 规则名称：半行 -->
          <el-col :span="12">
            <!-- 表单项：rule_name 必填 -->
            <el-form-item label="规则名称" prop="rule_name">
              <!-- 输入框：业务可读名称 -->
              <el-input v-model="form.rule_name" placeholder="请输入规则名称" maxlength="100" />
            </el-form-item>
          </el-col>
          <!-- 前缀：三分之一行 -->
          <el-col :span="8">
            <!-- 表单项：prefix 为编号固定开头 -->
            <el-form-item label="前缀" prop="prefix">
              <!-- 输入框：maxlength 20，避免编号过长 -->
              <el-input v-model="form.prefix" placeholder="如 NO" maxlength="20" />
            </el-form-item>
          </el-col>
          <!-- 日期格式：三分之一行 -->
          <el-col :span="8">
            <!-- 表单项：date_format 决定日期段样式 -->
            <el-form-item label="日期格式" prop="date_format">
              <!-- 下拉框：宽度撑满栅格；空字符串表示编号中不带日期段 -->
              <el-select v-model="form.date_format" style="width:100%">
                <!-- YYYYMMDD：日期精确到天，配合按日重置可得到每天独立的流水号 -->
                <el-option label="YYYYMMDD" value="YYYYMMDD" />
                <!-- YYYYMM：日期精确到月，适合月度报表编号 -->
                <el-option label="YYYYMM" value="YYYYMM" />
                <!-- YYYY：只带年份，编号更短 -->
                <el-option label="YYYY" value="YYYY" />
                <!-- 无日期：value 为空串，编号只由前缀与序号组成 -->
                <el-option label="无日期" value="" />
              </el-select>
            </el-form-item>
          </el-col>
          <!-- 序列长度：三分之一行 -->
          <el-col :span="8">
            <!-- 表单项：seq_length 为序号补零位数 -->
            <el-form-item label="序列长度" prop="seq_length">
              <!-- 数字输入：1~10 位，位数过多会让编号过长 -->
              <el-input-number v-model="form.seq_length" :min="1" :max="10" />
            </el-form-item>
          </el-col>
          <!-- 步长：三分之一行 -->
          <el-col :span="8">
            <!-- 表单项：step 为每次取号的递增幅度 -->
            <el-form-item label="步长" prop="step">
              <!-- 数字输入：1~100，大于 1 会跳号，可用于按业务线预留号段 -->
              <el-input-number v-model="form.step" :min="1" :max="100" />
            </el-form-item>
          </el-col>
          <!-- 分隔符：三分之一行 -->
          <el-col :span="8">
            <!-- 表单项：separator 拼接各段 -->
            <el-form-item label="分隔符" prop="separator">
              <!-- 输入框：最长 5 字符，如 "-"、"_"；留空则各段直接相连 -->
              <el-input v-model="form.separator" placeholder="如 -" maxlength="5" />
            </el-form-item>
          </el-col>
          <!-- 重置方式：三分之一行 -->
          <el-col :span="8">
            <!-- 表单项：reset_type 决定序号归零周期 -->
            <el-form-item label="重置方式" prop="reset_type">
              <!-- 下拉框：宽度撑满栅格 -->
              <el-select v-model="form.reset_type" style="width:100%">
                <!-- 按日：每天重新从起始序号计数 -->
                <el-option label="按日" value="day" />
                <!-- 按月：每月重新计数 -->
                <el-option label="按月" value="month" />
                <!-- 按年：每年重新计数 -->
                <el-option label="按年" value="year" />
                <!-- 不重置：序号持续递增，不因时间归零 -->
                <el-option label="不重置" value="none" />
              </el-select>
            </el-form-item>
          </el-col>
          <!-- 状态：整行 -->
          <el-col :span="24">
            <!-- 表单项：status 取 1/0 -->
            <el-form-item label="状态" prop="status">
              <!-- 开关：显式指定 active/inactive 值，与后端整型字段保持一致 -->
              <el-switch v-model="form.status" :active-value="1" :inactive-value="0" active-text="启用" inactive-text="停用" />
            </el-form-item>
          </el-col>
          <!-- 备注：整行 -->
          <el-col :span="24">
            <!-- 表单项：备注非必填，仅作规则用途说明 -->
            <el-form-item label="备注" prop="remark">
              <!-- 文本域：2 行高度兼顾空间与可读性 -->
              <el-input v-model="form.remark" type="textarea" :rows="2" placeholder="请输入备注" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <!-- 底部插槽 -->
      <template #footer>
        <!-- 取消：仅关闭弹窗 -->
        <el-button @click="dialogVisible=false">取消</el-button>
        <!-- 确定：saving 期间禁用并转圈，防止重复提交 -->
        <el-button type="primary" :loading="saving" @click="submitForm">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
// 组合式 API：ref 管理状态值，reactive 管理查询/表单对象，onMounted 挂载后首次拉取
import { ref, reactive, onMounted } from 'vue'
// Element Plus 消息提示与确认框：结果反馈、删除前二次确认
import { ElMessage, ElMessageBox } from 'element-plus'
// 按钮图标：Search 查询、Refresh 重置、Plus 新增、Delete 删除、MagicStick 生成编号
import { Search, Refresh, Plus, Delete, MagicStick } from '@element-plus/icons-vue'
// 统一请求实例：内置 baseURL=/api、token 注入与错误提示
import request from '@/utils/request'

// 表格加载态：请求期间显示遮罩
const loading = ref(false)
// 当前页规则数据
const rows = ref([])
// 总条数：供分页与页头统计
const total = ref(0)
// 已勾选行：供批量生成编号与批量删除使用
const selection = ref([])
// 保存中标记：防止弹窗内重复提交
const saving = ref(false)
// 弹窗显隐开关
const dialogVisible = ref(false)
// 弹窗标题：新增/编辑动态切换
const dialogTitle = ref('新增编码规则')
// 表单实例：提交时触发校验
const formRef = ref()

// 查询条件默认值：作为重置基准
const query_orig = { page: 1, page_size: 10, rule_key: '', rule_name: '', status: null }
// 响应式查询对象：与基准解耦
const query = reactive({ ...query_orig })

// 表单默认值：默认 YYYYMMDD 日期段、4 位序号、步长 1、"-" 分隔、按日重置
const form_orig = {
  id: null, rule_key: '', rule_name: '', prefix: '', date_format: 'YYYYMMDD',
  seq_length: 4, step: 1, separator: '-', reset_type: 'day', status: 1, remark: ''
}
// 响应式表单对象
const form = reactive({ ...form_orig })

// 校验规则：规则 Key 与名称必填，失焦时校验
const rules = {
  rule_key: [{ required: true, message: '请输入规则Key', trigger: 'blur' }],
  rule_name: [{ required: true, message: '请输入规则名称', trigger: 'blur' }]
}

// 接口前缀：本模块所有接口都基于它
const apiBase = '/sys_no/rule'

// 拉取列表：try/finally 保证失败时也能复位加载态，错误提示由 request 拦截器统一处理
async function fetchList() {
  loading.value = true
  try {
    // GET 分页查询：query 内含分页与筛选条件
    const res = await request.get(apiBase + '/list', { params: query })
    // data.list 为当前页规则；null 时用 [] 兜底
    rows.value = res.data.list || []
    // data.total 为总条数；缺失时按 0 处理
    total.value = res.data.total || 0
  } finally { loading.value = false }
}

// 查询：条件变化回到第 1 页，避免停在超出的页码
function handleSearch() { query.page = 1; fetchList() }
// 重置：恢复默认条件（含分页参数）后重新查询
function handleReset() { Object.assign(query, query_orig); handleSearch() }
// 勾选变化：接收 el-table 回传的选中行
function onSelectionChange(r) { selection.value = r }

// 新增：铺默认值（id=null），避免上次编辑的 id 残留误走更新接口
function openCreate() { Object.assign(form, form_orig); dialogTitle.value = '新增编码规则'; dialogVisible.value = true }
// 编辑：默认值打底再覆盖当前行，避免后端缺字段时出现 undefined；标题同步切换
function openEdit(row) { Object.assign(form, form_orig, row); dialogTitle.value = '编辑编码规则'; dialogVisible.value = true }

// 提交表单：先校验，再按是否有 id 分流新增/更新
async function submitForm() {
  // 校验失败会 reject，后续保存逻辑不会执行
  await formRef.value.validate()
  saving.value = true
  try {
    // 有 id 视为编辑
    if (form.id) {
      // 剔除 id：id 已放到 URL，留在请求体会被当作主键字段
      const { id, ...data } = form
      // PUT 更新并提示成功
      await request.put(`${apiBase}/update/${id}`, data); ElMessage.success('更新成功')
    } else {
      // 无 id 视为新增
      await request.post(apiBase + '/create', form); ElMessage.success('新增成功')
    }
    // 成功后关闭弹窗并刷新列表
    dialogVisible.value = false; fetchList()
  } finally { saving.value = false }
}

// 单条生成编号：副作用是真实消耗一个序号，因此结果仅提示、不自动刷新列表
async function handleGenerate(row) {
  try {
    // POST /generate/{id}：由后端原子自增并返回拼好的完整编号
    const res = await request.post(`${apiBase}/generate/${row.id}`)
    // 后端可能返回 { number } 或直接返回编号字符串，两种结构都兼容展示
    ElMessage.success(`生成编号：${res.data?.number || res.data}`)
  } catch (e) { /* handled by interceptor */ }
}

// 批量生成编号：对选中规则逐条串行取号，避免并发抢占序号导致顺序不可控
async function handleGenerateBatch() {
  for (const row of selection.value) {
    try {
      // 每次选中行单独调用一次取号接口
      const res = await request.post(`${apiBase}/generate/${row.id}`)
      // 提示中带上规则名，便于在批量结果里区分是哪条规则生成的编号
      ElMessage.success(`${row.rule_name} → ${res.data?.number || res.data}`)
    } catch (e) { /* skip */ }
  }
}

// 单条删除：确认框取消会 reject，后续删除不会执行
async function handleDelete(row) {
  await ElMessageBox.confirm('确定删除该编码规则？', '提示', { type: 'warning' })
  // DELETE 带请求体用 data 传参；后端按 ids 数组处理，单条也传数组
  await request.delete(apiBase + '/delete', { data: { ids: [row.id] } })
  // 删除成功后提示并刷新
  ElMessage.success('删除成功'); fetchList()
}

// 批量删除：确认文案带选中数量
async function handleBatchDelete() {
  await ElMessageBox.confirm(`确定删除选中的 ${selection.value.length} 条？`, '提示', { type: 'warning' })
  // 只提交 id 集合，避免传输整行数据
  await request.delete(apiBase + '/delete', { data: { ids: selection.value.map(r => r.id) } })
  // 刷新后表格重新加载，选中态随之清空
  ElMessage.success('批量删除成功'); fetchList()
}

// 页面挂载后立即加载一次数据
onMounted(fetchList)
</script>
