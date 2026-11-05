<!-- 消息模板管理页（消息中心 / 消息模板）
     职责：维护各类消息模板的编码、名称、内容（支持 ${变量} 占位）、发送渠道与启停状态，
           供消息发送流程按模板编码渲染并下发。
     接口：GET /msg/template/list（分页）、POST /msg/template/create、
           PUT /msg/template/update/{id}、PUT /msg/template/status/{id}（仅改启停）、
           DELETE /msg/template/delete（单条/批量共用，ids 放请求体）。
     依赖：@/utils/request（统一 baseURL、token 与错误提示）、Element Plus 表单/表格/弹窗、v-perm 权限指令。
     被谁使用：由后端菜单动态挂载进入；业务代码按模板编码取模板内容并替换占位变量。 -->
<template>
  <!-- 页面根容器：复用全局 .app-container 的留白与进场动画 -->
  <div class="app-container">
    <!-- 页头：标题 + 模板总数 -->
    <div class="page-header">
      <!-- 标题组 -->
      <div class="page-title-wrap">
        <!-- 主标题：与菜单名一致 -->
        <h2>消息模板</h2>
        <!-- 副标题：total 为服务端返回的总记录数 -->
        <div class="sub">模板管理 · 共 {{ total }} 条</div>
      </div>
    </div>
    <!-- 查询卡片：shadow="never" 弱化辅助区域 -->
    <el-card shadow="never" class="search-card">
      <!-- inline 单行排列；@submit.prevent 阻止回车触发表单原生提交刷新整页 -->
      <el-form :model="query" inline @submit.prevent>
        <!-- 模板编码筛选：编码是业务调用模板的唯一键，最常用于检索 -->
        <el-form-item label="模板编码">
          <!-- clearable 一键清空；160px 固定宽度；回车直接查询 -->
          <el-input v-model="query.template_code" placeholder="请输入编码" clearable style="width: 160px" @keyup.enter="handleSearch" />
        </el-form-item>
        <!-- 消息类型筛选：与模板所属的业务场景对应 -->
        <el-form-item label="消息类型">
          <!-- 清空后 msg_type 回到 null，即不按类型过滤 -->
          <el-select v-model="query.msg_type" placeholder="全部" clearable style="width: 130px">
            <!-- todo = 待办：流程待处理任务提醒 -->
            <el-option label="待办" value="todo" />
            <!-- done = 已办：流程处理完成回执 -->
            <el-option label="已办" value="done" />
            <!-- cc = 抄送：流程抄送知会 -->
            <el-option label="抄送" value="cc" />
            <!-- system = 系统：系统公告/账号类消息 -->
            <el-option label="系统" value="system" />
            <!-- report = 报表：报表生成完成通知 -->
            <el-option label="报表" value="report" />
            <!-- alarm = 告警：监控告警通知 -->
            <el-option label="告警" value="alarm" />
            <!-- notice = 通知：通用业务通知 -->
            <el-option label="通知" value="notice" />
          </el-select>
        </el-form-item>
        <!-- 状态筛选：1/0 与后端 tinyint 保持一致 -->
        <el-form-item label="状态">
          <!-- 清空后 status 回到 null，即不按启停状态过滤 -->
          <el-select v-model="query.status" placeholder="全部" clearable style="width: 110px">
            <!-- 1 = 启用：可被发送流程使用 -->
            <el-option label="启用" :value="1" />
            <!-- 0 = 停用：模板保留但不再参与发送 -->
            <el-option label="停用" :value="0" />
          </el-select>
        </el-form-item>
        <!-- 操作按钮组 -->
        <el-form-item>
          <!-- 查询：回到第一页并拉取 -->
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <!-- 重置：恢复默认条件后重新查询 -->
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 表格卡片：新增/批量删除放在表格上方工具栏 -->
    <el-card shadow="never" class="table-card">
      <!-- 工具栏插槽：新增与批量删除 -->
      <template #header>
        <div class="card-header">
          <div class="card-actions">
            <!-- 新增：需 msg:create；openCreate 先重置表单再开弹窗 -->
            <el-button v-perm="'msg:create'" type="primary" :icon="Plus" @click="openCreate">新增</el-button>
            <!-- 批量删除：需 msg:delete；未勾选时禁用，避免空提交 -->
            <el-button v-perm="'msg:delete'" type="danger" plain :icon="Delete" :disabled="!selection.length" @click="handleBatchDelete">批量删除</el-button>
          </div>
        </div>
      </template>
      <!-- 表格：v-loading 加载态；stripe 隔行变色；空态中文；selection-change 同步勾选行 -->
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据" @selection-change="onSelectionChange">
        <!-- 序号列：阅读定位 -->
        <el-table-column type="index" label="序号" width="70" align="center" />
        <!-- 多选列：为批量删除提供勾选能力 -->
        <el-table-column type="selection" width="50" />
        <!-- 模板编码：业务侧引用模板的唯一标识，创建后不可修改（见弹窗 :disabled） -->
        <el-table-column label="模板编码" prop="template_code" min-width="140" show-overflow-tooltip />
        <!-- 模板名称：展示名，便于运营识别 -->
        <el-table-column label="模板名称" prop="template_name" min-width="150" show-overflow-tooltip />
        <!-- 消息类型：业务场景编码 -->
        <el-table-column label="消息类型" prop="msg_type" width="90" />
        <!-- 模板内容：含 ${变量} 占位的正文，发送时由后端替换 -->
        <el-table-column label="模板内容" prop="template_content" min-width="220" show-overflow-tooltip />
        <!-- 渠道：模板默认使用的下发渠道编码（site/sms/email） -->
        <el-table-column label="渠道" prop="channel" width="100" />
        <!-- 状态列：开关直接改写行数据，change 时立即调用状态接口 -->
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <!-- active/inactive 用 1/0 对齐后端；无 msg:update 权限时隐藏开关 -->
            <el-switch v-model="row.status" :active-value="1" :inactive-value="0" v-perm="'msg:update'" @change="handleStatusChange(row)" />
          </template>
        </el-table-column>
        <!-- 创建时间：模板写入时间 -->
        <el-table-column label="创建时间" prop="create_time" width="170" />
        <!-- 操作列：fixed="right" 横向滚动时保持可见 -->
        <el-table-column label="操作" width="180" fixed="right" class-name="op-col">
          <template #default="{ row }">
            <!-- 编辑：需 msg:update，整行数据带入表单 -->
            <el-button v-perm="'msg:update'" link type="primary" @click="openEdit(row)">编辑</el-button>
            <!-- 删除：需 msg:delete，单条删除同样走 ids 数组接口 -->
            <el-button v-perm="'msg:delete'" link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <!-- 分页：总数/每页条数/翻页/跳页；页码与页大小双向写回 query，变化即刷新 -->
      <div class="pagination-wrap">
        <el-pagination background layout="total, sizes, prev, pager, next, jumper"
          :total="total" v-model:current-page="query.page" v-model:page-size="query.page_size"
          :page-sizes="[10, 20, 50, 100]" @change="fetchList" />
      </div>
    </el-card>

    <!-- 新增/编辑弹窗：标题随模式切换；禁止点遮罩关闭防误操作；destroy-on-close 每次打开重建表单 -->
    <el-dialog :title="dialogTitle" v-model="dialogVisible" width="680px" :close-on-click-modal="false" destroy-on-close>
      <!-- ref 供 validate 调用；:model/:rules 绑定数据与校验规则；label-width 统一标签宽度 -->
      <el-form ref="formRef" :model="form" :rules="rules" label-width="110px">
        <!-- 模板编码：编辑时禁止修改——业务代码按编码取模板，改编码会切断引用 -->
        <el-form-item label="模板编码" prop="template_code">
          <!-- maxlength 64 与后端字段长度对齐；:disabled="!!form.id" 表示编辑态只读 -->
          <el-input v-model="form.template_code" placeholder="请输入模板编码" maxlength="64" :disabled="!!form.id" />
        </el-form-item>
        <!-- 模板名称：展示名，可随时调整 -->
        <el-form-item label="模板名称" prop="template_name">
          <!-- maxlength 100 与后端字段长度对齐 -->
          <el-input v-model="form.template_name" placeholder="请输入模板名称" maxlength="100" />
        </el-form-item>
        <!-- 消息类型：决定模板归属的业务场景，必填 -->
        <el-form-item label="消息类型" prop="msg_type">
          <!-- style 100% 让下拉占满表单项宽度 -->
          <el-select v-model="form.msg_type" placeholder="请选择消息类型" style="width:100%">
            <!-- 各类型编码含义同查询栏 -->
            <el-option label="待办" value="todo" />
            <el-option label="已办" value="done" />
            <el-option label="抄送" value="cc" />
            <el-option label="系统" value="system" />
            <el-option label="报表" value="report" />
            <el-option label="告警" value="alarm" />
            <el-option label="通知" value="notice" />
          </el-select>
        </el-form-item>
        <!-- 模板内容：正文，支持 ${变量} 占位；发送时由后端按参数替换 -->
        <el-form-item label="模板内容" prop="template_content">
          <!-- 4 行文本域；placeholder 明确提示可使用 ${变量} 占位语法 -->
          <el-input v-model="form.template_content" type="textarea" :rows="4" placeholder="请输入模板内容，可用 ${变量} 占位" />
        </el-form-item>
        <!-- 发送渠道：决定该模板默认走站内信/短信/邮件 -->
        <el-form-item label="发送渠道" prop="channel">
          <!-- style 100% 让下拉占满表单项宽度 -->
          <el-select v-model="form.channel" placeholder="请选择渠道" style="width:100%">
            <!-- site = 站内信；sms = 短信；email = 邮件，取值与推送渠道配置一致 -->
            <el-option label="站内信" value="site" />
            <el-option label="短信" value="sms" />
            <el-option label="邮件" value="email" />
          </el-select>
        </el-form-item>
        <!-- 状态：1 启用 / 0 停用 -->
        <el-form-item label="状态" prop="status">
          <el-radio-group v-model="form.status">
            <!-- 1 = 启用 -->
            <el-radio :value="1">启用</el-radio>
            <!-- 0 = 停用 -->
            <el-radio :value="0">停用</el-radio>
          </el-radio-group>
        </el-form-item>
        <!-- 备注：可选说明 -->
        <el-form-item label="备注" prop="remark">
          <el-input v-model="form.remark" type="textarea" :rows="2" placeholder="请输入备注" />
        </el-form-item>
      </el-form>
      <!-- 弹窗底部：取消关闭；确定带 loading 防重复提交 -->
      <template #footer>
        <el-button @click="dialogVisible=false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitForm">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
// 组合式 API：ref 管状态、reactive 管查询/表单对象、onMounted 做首屏加载
import { ref, reactive, onMounted } from 'vue'
// ElMessage 成功提示；ElMessageBox 删除前二次确认
import { ElMessage, ElMessageBox } from 'element-plus'
// 图标组件以对象形式传给 :icon
import { Search, Refresh, Plus, Delete } from '@element-plus/icons-vue'
// 统一请求封装：内置 baseURL=/api、token 注入与统一错误提示
import request from '@/utils/request'

// 表格加载态
const loading = ref(false)
// 当前页的模板列表
const rows = ref([])
// 服务端返回的总记录数
const total = ref(0)
// 当前勾选的行，批量删除按钮的禁用与提交都依赖它
const selection = ref([])
// 提交中标记，控制确定按钮 loading，防止重复提交
const saving = ref(false)
// 新增/编辑弹窗显隐
const dialogVisible = ref(false)
// 弹窗标题，打开时按"新增/编辑"改写
const dialogTitle = ref('新增')
// el-form 实例，提交前调用 validate 做必填校验
const formRef = ref()

// 查询条件默认值；空字符串/null 表示"全部"，页码从 1 开始
const query_orig = { page: 1, page_size: 10, template_code: '', msg_type: null, status: null }
// 实际查询条件：保留 reactive 引用，模板与请求参数共用
const query = reactive({ ...query_orig })

// 表单默认值：新增前用它清空；编辑时先铺默认值再覆盖行数据，避免残留上一次编辑的内容
const form_orig = {
  id: null, template_code: '', template_name: '', msg_type: '', template_content: '',
  channel: '', status: 1, remark: ''
}
// 当前新增/编辑的表单数据，与弹窗表单双向绑定
const form = reactive({ ...form_orig })

// 必填校验规则：编码/名称/类型/内容/渠道均不能为空；文本框用 blur、下拉用 change 触发
const rules = {
  template_code: [{ required: true, message: '请输入模板编码', trigger: 'blur' }],
  template_name: [{ required: true, message: '请输入模板名称', trigger: 'blur' }],
  msg_type: [{ required: true, message: '请选择消息类型', trigger: 'change' }],
  template_content: [{ required: true, message: '请输入模板内容', trigger: 'blur' }],
  channel: [{ required: true, message: '请选择发送渠道', trigger: 'change' }]
}

// 集中维护接口前缀，避免各处硬编码；按动作名返回对应 URL
function apiUrl(action) {
  const base = '/msg/template'
  return {
    list: base + '/list',
    create: base + '/create',
    update: base + '/update',
    delete: base + '/delete'
  }[action]
}

// 拉取列表：loading 在 finally 中关闭，异常时不会卡在加载中
async function fetchList() {
  loading.value = true
  try {
    // 参数直接传 query；null 字段由后端忽略
    const res = await request.get(apiUrl('list'), { params: query })
    // 兜底空值，避免 list/total 缺省时渲染异常
    rows.value = res.data.list || []
    total.value = res.data.total || 0
  } finally { loading.value = false }
}
// 查询：条件变化后回到第 1 页再加载
function handleSearch() { query.page = 1; fetchList() }
// 重置：回填默认值并重新查询（不改变 reactive 引用）
function handleReset() { Object.assign(query, query_orig); handleSearch() }
// 表格勾选变化时同步选中行数组
function onSelectionChange(r) { selection.value = r }

// 新增：先恢复默认表单，再设置标题并打开弹窗
function openCreate() { Object.assign(form, form_orig); dialogTitle.value = '新增模板'; dialogVisible.value = true }
// 编辑：先铺默认值再覆盖行数据，保证当前行没有的字段不会沿用上一次的值
function openEdit(row) { Object.assign(form, form_orig, row); dialogTitle.value = '编辑模板'; dialogVisible.value = true }

// 提交表单：先校验，再按有无 id 区分新增/更新，成功后关闭弹窗并刷新列表
async function submitForm() {
  // 校验失败会抛出异常，后续提交不会执行
  await formRef.value.validate()
  saving.value = true
  try {
    if (form.id) {
      // 更新：解构剔除主键 id（已放进 URL），其余字段作为请求体
      const { id, ...data } = form
      await request.put(`${apiUrl('update')}/${id}`, data); ElMessage.success('更新成功')
    } else {
      // 新增：直接提交整份表单
      await request.post(apiUrl('create'), form); ElMessage.success('新增成功')
    }
    // 成功后关闭弹窗并刷新列表
    dialogVisible.value = false; fetchList()
  } finally { saving.value = false }
}

// 行内状态开关：change 后立即提交状态变更，只发 status 一个字段
async function handleStatusChange(row) {
  await request.put(`/msg/template/status/${row.id}`, { status: row.status })
  // 按开关值给出不同提示文案
  ElMessage.success(row.status === 1 ? '已启用' : '已停用')
}

// 单条删除：先二次确认（用户取消会 reject，不会删除），再按 ids 数组提交
async function handleDelete(row) {
  await ElMessageBox.confirm('确定删除该模板？', '提示', { type: 'warning' })
  await request.delete(apiUrl('delete'), { data: { ids: [row.id] } })
  ElMessage.success('删除成功'); fetchList()
}

// 批量删除：用勾选行的 id 组成数组，与单条删除共用同一个 delete 接口
async function handleBatchDelete() {
  await ElMessageBox.confirm(`确定删除选中的 ${selection.value.length} 条模板？`, '提示', { type: 'warning' })
  await request.delete(apiUrl('delete'), { data: { ids: selection.value.map(r => r.id) } })
  ElMessage.success('批量删除成功'); fetchList()
}

// 页面挂载后加载第一页
onMounted(fetchList)
</script>
