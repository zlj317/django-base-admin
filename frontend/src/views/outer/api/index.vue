<!--
  文件级说明：外部接口管理页（第三方 API 配置）。
  职责：维护外部 HTTP 接口的地址、方法、请求头/参数模板与认证方式，支持筛选、分页、新增、编辑、启停、测试连通性、单条/批量删除。
  依赖：@/utils/request（统一 /api 前缀、Bearer token 与错误提示）；Element Plus（表格/表单/弹窗/消息）；
        @element-plus/icons-vue 的 Search、Refresh、Plus、Delete 图标；自定义指令 v-perm 控制按钮级权限。
  数据来源：GET /outer/api/list；POST /outer/api/create；PUT /outer/api/update/{id}；DELETE /outer/api/delete（body 传 ids）；
            PUT /outer/api/status/{id} 切换启停；POST /outer/api/test/{id} 触发后端真实调用做连通性测试。
  业务含义：认证方式 none=无鉴权、token=请求头带 Token、basic=HTTP Basic；auth_config 存对应凭据的 JSON。
  被谁使用：由路由挂载在“外部接口”菜单，是“数据同步”（outer/sync）选择目标接口的数据源。
-->
<template>
  <!-- 页面根容器：统一内边距与背景 -->
  <div class="app-container">
    <!-- 页头：标题 + 总条数副标题 -->
    <div class="page-header">
      <div class="page-title-wrap">
        <!-- 主标题：外部接口（配置的是被调用方接口，不是本系统对外提供的接口） -->
        <h2>外部接口</h2>
        <!-- 副标题：实时展示接口总数 -->
        <div class="sub">接口管理 · 共 {{ total }} 条</div>
      </div>
    </div>
    <!-- 查询条件卡片：扁平样式与表格卡片组成管理页布局 -->
    <el-card shadow="never" class="search-card">
      <!-- 行内查询表单；阻止原生提交，统一走查询按钮/回车 -->
      <el-form :model="query" inline @submit.prevent>
        <el-form-item label="接口名称">
          <!-- 名称模糊搜索：clearable 一键清空；回车即查询 -->
          <el-input v-model="query.api_name" placeholder="请输入名称" clearable style="width: 170px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="方法">
          <!-- HTTP 方法筛选：与后端枚举一致（大写），清空表示全部 -->
          <el-select v-model="query.method" placeholder="全部" clearable style="width: 110px">
            <!-- GET：查询类接口，参数通常放 URL -->
            <el-option label="GET" value="GET" />
            <!-- POST：提交类接口，参数放请求体 -->
            <el-option label="POST" value="POST" />
            <!-- PUT：更新类接口 -->
            <el-option label="PUT" value="PUT" />
            <!-- DELETE：删除类接口 -->
            <el-option label="DELETE" value="DELETE" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <!-- 1=启用（可被同步任务调用），0=停用（仅保留配置） -->
          <el-select v-model="query.status" placeholder="全部" clearable style="width: 110px">
            <!-- 启用：参与同步调用 -->
            <el-option label="启用" :value="1" />
            <!-- 停用：保留配置但不参与调用 -->
            <el-option label="停用" :value="0" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <!-- 查询：回到第 1 页按当前条件请求 -->
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <!-- 重置：恢复初始条件后重新查询 -->
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 表格卡片：头部为操作按钮，主体为接口列表，底部为分页 -->
    <el-card shadow="never" class="table-card">
      <!-- 卡片头部插槽：集中放置新增/批量删除 -->
      <template #header>
        <div class="card-header">
          <div class="card-actions">
            <!-- 新增：需要 outer:create 权限才渲染；点击重置表单并打开弹窗 -->
            <el-button v-perm="'outer:create'" type="primary" :icon="Plus" @click="openCreate">新增</el-button>
            <!-- 批量删除：需要 outer:delete 权限；未勾选时禁用，避免空提交 -->
            <el-button v-perm="'outer:delete'" type="danger" plain :icon="Delete" :disabled="!selection.length" @click="handleBatchDelete">批量删除</el-button>
          </div>
        </div>
      </template>
      <!-- 接口表格：selection-change 同步勾选行，供批量删除使用 -->
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据" @selection-change="onSelectionChange">
        <!-- 序号列：前端自动编号 -->
        <el-table-column type="index" label="序号" width="70" align="center" />
        <!-- 多选列：批量删除依赖它收集 ids -->
        <el-table-column type="selection" width="50" />
        <!-- 接口名称：超长省略 + 悬浮全文 -->
        <el-table-column label="接口名称" prop="api_name" min-width="160" show-overflow-tooltip />
        <!-- 请求 URL：完整第三方地址，超长省略便于保持列宽 -->
        <el-table-column label="请求URL" prop="api_url" min-width="220" show-overflow-tooltip />
        <el-table-column label="方法" width="90" align="center">
          <!-- 方法用不同颜色标签区分语义：GET 绿、POST 蓝、PUT 橙、DELETE 红 -->
          <template #default="{ row }">
            <el-tag :type="methodTagType(row.method)" size="small">{{ row.method }}</el-tag>
          </template>
        </el-table-column>
        <!-- 认证方式：展示 none/token/basic 原始枚举，具体凭据在编辑弹窗的 auth_config 中维护 -->
        <el-table-column label="认证方式" prop="auth_type" width="100" />
        <el-table-column label="状态" width="90" align="center">
          <!-- 行内开关直接改 row.status 并调用启停接口；v-perm 限定只有 outer:update 权限的用户可操作 -->
          <template #default="{ row }">
            <el-switch v-model="row.status" :active-value="1" :inactive-value="0" v-perm="'outer:update'" @change="handleStatusChange(row)" />
          </template>
        </el-table-column>
        <!-- 备注：说明接口用途，超长省略 -->
        <el-table-column label="备注" prop="remark" min-width="160" show-overflow-tooltip />
        <!-- 创建时间：后端已格式化，直接展示 -->
        <el-table-column label="创建时间" prop="create_time" width="170" />
        <!-- 操作列：固定右侧，含编辑/测试/删除三个按钮，宽度比规则页更宽以容纳三项 -->
        <el-table-column label="操作" width="260" fixed="right" class-name="op-col">
          <template #default="{ row }">
            <!-- 编辑：outer:update 权限；把当前行回填到表单 -->
            <el-button v-perm="'outer:update'" link type="primary" @click="openEdit(row)">编辑</el-button>
            <!-- 测试：outer:test 权限；后端按配置真实发起一次请求，验证地址与鉴权是否可用 -->
            <el-button v-perm="'outer:test'" link type="success" @click="handleTest(row)">测试</el-button>
            <!-- 删除：outer:delete 权限；二次确认后删除 -->
            <el-button v-perm="'outer:delete'" link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <!-- 分页容器：统一右对齐布局 -->
      <div class="pagination-wrap">
        <!-- 分页器：页码/每页条数双向绑定 query，变化即重新请求 -->
        <el-pagination background layout="total, sizes, prev, pager, next, jumper"
          :total="total" v-model:current-page="query.page" v-model:page-size="query.page_size"
          :page-sizes="[10, 20, 50, 100]" @change="fetchList" />
      </div>
    </el-card>

    <!-- 新增/编辑弹窗：720px 宽以容纳 JSON 文本域；禁点遮罩关闭防误触；destroy-on-close 保证表单实例干净 -->
    <el-dialog :title="dialogTitle" v-model="dialogVisible" width="720px" :close-on-click-modal="false" destroy-on-close>
      <!-- 接口配置表单：ref 用于校验，rules 约束名称/URL/方法/认证方式必填 -->
      <el-form ref="formRef" :model="form" :rules="rules" label-width="110px">
        <!-- 两列栅格：短字段占半行，JSON 文本域占满整行便于编辑 -->
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="接口名称" prop="api_name">
              <!-- 名称必填：用于列表展示，也是同步任务选择目标接口时的可读标识 -->
              <el-input v-model="form.api_name" placeholder="请输入接口名称" maxlength="100" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="请求方法" prop="method">
              <!-- 请求方法决定调用时的 HTTP 语义，也影响参数放在 URL 还是请求体 -->
              <el-select v-model="form.method" style="width:100%">
                <!-- GET：参数拼到 URL -->
                <el-option label="GET" value="GET" />
                <!-- POST：参数放请求体 -->
                <el-option label="POST" value="POST" />
                <!-- PUT：更新类接口 -->
                <el-option label="PUT" value="PUT" />
                <!-- DELETE：删除类接口 -->
                <el-option label="DELETE" value="DELETE" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="请求URL" prop="api_url">
              <!-- 完整第三方地址（含协议与域名），placeholder 给出格式示例，后端调用时原样使用 -->
              <el-input v-model="form.api_url" placeholder="https://api.example.com/v1/data" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="Headers JSON" prop="headers_json">
              <!-- 自定义请求头模板（JSON 字符串），例如 Content-Type，由后端在调用时注入 -->
              <el-input v-model="form.headers_json" type="textarea" :rows="3" placeholder='{"Content-Type":"application/json"}' />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="参数JSON" prop="params_json">
              <!-- 请求参数模板：GET 拼到 query，POST/PUT 作为请求体，具体处理在后端按 method 分流 -->
              <el-input v-model="form.params_json" type="textarea" :rows="3" placeholder='{"key":"val"}' />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="认证方式" prop="auth_type">
              <!-- 认证方式：none=无鉴权；token=请求头带 Token；basic=HTTP Basic 用户名密码 -->
              <el-select v-model="form.auth_type" style="width:100%">
                <!-- 无：公开接口或内网直连，不附加任何凭据 -->
                <el-option label="无" value="none" />
                <!-- Token：凭据存 auth_config，后端注入 Authorization 头 -->
                <el-option label="Token" value="token" />
                <!-- Basic：用户名/密码以 Base64 放入 Authorization 头 -->
                <el-option label="Basic" value="basic" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="状态" prop="status">
              <!-- 启停用：停用后同步任务不再调用该接口，配置仍然保留 -->
              <el-radio-group v-model="form.status">
                <el-radio :value="1">启用</el-radio>
                <el-radio :value="0">停用</el-radio>
              </el-radio-group>
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="认证配置" prop="auth_config">
              <!-- 认证凭据 JSON：token 方式如 {"token":"..."}，basic 方式存用户名/密码，与 auth_type 配套使用 -->
              <el-input v-model="form.auth_config" type="textarea" :rows="3" placeholder="Token/Basic 认证配置JSON" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="备注" prop="remark">
              <!-- 备注：记录接口用途/负责人等信息，方便后续维护 -->
              <el-input v-model="form.remark" type="textarea" :rows="2" placeholder="请输入备注" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <!-- 弹窗底部：取消不落库；确定走 submitForm（先校验，再按 id 分流新增/更新） -->
      <template #footer>
        <el-button @click="dialogVisible=false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitForm">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
// 组合式 API：ref 管标量/数组，reactive 管查询与表单，onMounted 做首屏加载
import { ref, reactive, onMounted } from 'vue'
// ElMessage 轻提示操作结果；ElMessageBox 用于删除确认与测试结果弹窗
import { ElMessage, ElMessageBox } from 'element-plus'
// 工具栏与操作列图标，保持全站按钮视觉一致
import { Search, Refresh, Plus, Delete } from '@element-plus/icons-vue'
// 统一请求实例：自动附带 token，失败由拦截器统一提示
import request from '@/utils/request'

// 表格加载态：请求期间显示遮罩
const loading = ref(false)
// 当前页接口列表，绑定 el-table 的 :data
const rows = ref([])
// 后端总条数：供分页与页头“共 N 条”使用
const total = ref(0)
// 表格勾选行：驱动批量删除按钮与 ids 收集
const selection = ref([])
// 保存中状态：控制“确定”按钮 loading，避免重复提交
const saving = ref(false)
// 弹窗显隐：新增/编辑共用
const dialogVisible = ref(false)
// 弹窗标题：新增与编辑复用弹窗时切换
const dialogTitle = ref('新增')
// 表单实例：提交前调用 validate()
const formRef = ref()

// 查询条件快照：重置时整体覆盖 query
// method/status 用 null 表示“全部”，api_name 用空串表示不按名称过滤
const query_orig = { page: 1, page_size: 10, api_name: '', method: null, status: null }
// 响应式查询对象：与查询表单和分页双向绑定，直接作为列表接口 params
const query = reactive({ ...query_orig })

// 表单初始值快照：新增时重置用，避免残留上一次编辑的数据
// 默认 GET + 无认证 + 启用，覆盖最常用的接口配置
const form_orig = {
  id: null, api_name: '', api_url: '', method: 'GET', headers_json: '', params_json: '',
  auth_type: 'none', auth_config: '', status: 1, remark: ''
}
// 响应式表单对象：弹窗内所有控件绑定到它
const form = reactive({ ...form_orig })

// 校验规则：名称、URL、方法、认证方式必填；headers/params/auth_config 允许为空
const rules = {
  api_name: [{ required: true, message: '请输入接口名称', trigger: 'blur' }],
  api_url: [{ required: true, message: '请输入请求URL', trigger: 'blur' }],
  method: [{ required: true, message: '请选择方法', trigger: 'change' }],
  auth_type: [{ required: true, message: '请选择认证方式', trigger: 'change' }]
}

// HTTP 方法 -> el-tag 颜色：让列表一眼区分为读/写/改/删，降低误操作概率
// 未知方法返回空串，使用标签默认色，避免报错
function methodTagType(m) {
  if (m === 'GET') return 'success'
  if (m === 'POST') return 'primary'
  if (m === 'PUT') return 'warning'
  if (m === 'DELETE') return 'danger'
  return ''
}

// 接口地址映射表：集中管理 /outer/api 下的四个基础端点，避免各处手写字符串不一致
// update 返回的是不带 id 的前缀，调用方自行拼接 /{id}
function apiUrl(action) {
  const base = '/outer/api'
  return {
    list: base + '/list',
    create: base + '/create',
    update: base + '/update',
    delete: base + '/delete'
  }[action]
}

// 列表查询：查询/重置/翻页/保存后刷新都复用
async function fetchList() {
  // 打开遮罩提示加载中
  loading.value = true
  try {
    // GET 分页查询，query 自动序列化为 URL 参数
    const res = await request.get(apiUrl('list'), { params: query })
    // list 兜底空数组、total 兜底 0，避免后端返回 null 时渲染异常
    rows.value = res.data.list || []
    total.value = res.data.total || 0
  // 成功失败都关闭遮罩
  } finally { loading.value = false }
}
// 查询：回到第 1 页再请求，避免旧页码越界
function handleSearch() { query.page = 1; fetchList() }
// 重置：用快照覆盖查询条件后重新查询
function handleReset() { Object.assign(query, query_orig); handleSearch() }
// 勾选变化：缓存选中行，供批量删除使用
function onSelectionChange(r) { selection.value = r }

// 新增：重置表单（id=null 保证走新增分支），切标题并打开弹窗
function openCreate() { Object.assign(form, form_orig); dialogTitle.value = '新增接口'; dialogVisible.value = true }
// 编辑：先铺默认值再覆盖行数据，保证缺失字段有兜底；id 决定后续走更新分支
function openEdit(row) { Object.assign(form, form_orig, row); dialogTitle.value = '编辑接口'; dialogVisible.value = true }

// 提交：先校验，再按 id 分流新增/更新，成功后关闭弹窗并刷新列表
async function submitForm() {
  // 校验失败会 reject 并中断，避免提交非法配置
  await formRef.value.validate()
  saving.value = true
  try {
    if (form.id) {
      // 更新：id 从路径传递，请求体只带业务字段
      const { id, ...data } = form
      await request.put(`${apiUrl('update')}/${id}`, data); ElMessage.success('更新成功')
    } else {
      // 新增：整表单提交，id 由后端生成
      await request.post(apiUrl('create'), form); ElMessage.success('新增成功')
    }
    // 成功后关闭弹窗并刷新当前页
    dialogVisible.value = false; fetchList()
  // 失败保留弹窗便于修改；无论如何解除 loading
  } finally { saving.value = false }
}

// 测试接口连通性：调用后端真实发起一次请求，把状态码、耗时与响应体回显给用户
async function handleTest(row) {
  // duration=0 表示不自动关闭，需手动 close：请求可能较久，常驻提示避免用户以为没反应
  const h = ElMessage({ message: `正在测试接口「${row.api_name}」...`, type: 'info', duration: 0 })
  try {
    // 由后端按已保存的配置发起调用（前端不直接请求第三方，避免跨域与凭据泄露）
    const res = await request.post(`/outer/api/test/${row.id}`)
    // 先关掉“正在测试”提示，再弹出结果
    h.close()
    // 结果弹窗：展示 HTTP 状态码、耗时、响应体；?? '-' 兼容后端未返回字段的情况
    ElMessageBox.alert(
      // dangerouslyUseHTMLString：需要富文本排版 pre 展示 JSON；注意响应体是外部数据，存在被注入 HTML 的风险
      `<p><b>HTTP状态码：</b> ${res.data?.http_code ?? '-'}</p>
       <p><b>耗时：</b> ${res.data?.cost_time ?? '-'} ms</p>
       <p><b>响应：</b></p>
       <pre style="max-height:300px;overflow:auto;white-space:pre-wrap;">${JSON.stringify(res.data?.response_body ?? res.data, null, 2)}</pre>`,
      '测试结果',
      { dangerouslyUseHTMLString: true }
    )
  } catch (e) {
    // 失败也必须关闭常驻提示，否则会一直挂在页面上
    h.close()
    // 额外提示失败原因；统一拦截器已提示过一次，这里补充“测试失败”上下文
    ElMessage.error('测试失败：' + (e.message || e))
  }
}

// 行内启停：开关已把新值写入 row.status，这里同步到后端
// 只提交 status 字段，避免用整行数据触发后端全量更新
async function handleStatusChange(row) {
  await request.put(`/outer/api/status/${row.id}`, { status: row.status })
  // 按最新状态给出反馈文案，让用户确认操作已生效
  ElMessage.success(row.status === 1 ? '已启用' : '已停用')
}

// 单条删除：二次确认后按 ids 数组提交（与批量删除共用接口）
async function handleDelete(row) {
  await ElMessageBox.confirm('确定删除该接口？', '提示', { type: 'warning' })
  await request.delete(apiUrl('delete'), { data: { ids: [row.id] } })
  ElMessage.success('删除成功'); fetchList()
}

// 批量删除：确认文案带数量，降低误删风险
async function handleBatchDelete() {
  await ElMessageBox.confirm(`确定删除选中的 ${selection.value.length} 条接口？`, '提示', { type: 'warning' })
  // 从选中行提取 id 组成数组提交
  await request.delete(apiUrl('delete'), { data: { ids: selection.value.map(r => r.id) } })
  ElMessage.success('批量删除成功'); fetchList()
}

// 首屏加载接口列表；本页没有下拉依赖，无需额外请求
onMounted(fetchList)
</script>
