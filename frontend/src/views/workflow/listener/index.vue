<!--
  文件级说明：流程监听器管理页（workflow/listener/index.vue）
  职责：配置流程/节点事件触发后的动作（回调接口、消息通知、修改数据、写日志），实现流程与外部系统的联动。
  依赖：@/utils/request 统一 HTTP 封装；Element Plus 表单/表格/弹窗组件；v-perm 权限指令。
  使用方：由工作流管理菜单下的「监听器」路由加载，属于后台管理页面。
-->
<template>
  <!-- 页面根容器：套用全局布局样式 -->
  <div class="app-container">
    <!-- 页头：标题 + 监听器总数 -->
    <div class="page-header">
      <div class="page-title-wrap">
        <h2>流程监听器</h2>
        <!-- total 来自后端分页结果，查询后同步刷新 -->
        <div class="sub">节点事件回调与通知配置 · 共 {{ total }} 条记录</div>
      </div>
    </div>

    <!-- 搜索区：按流程模型和事件类型过滤监听规则 -->
    <el-card shadow="never" class="search-card">
      <!-- @submit.prevent 阻止默认提交行为 -->
      <el-form :model="query" inline @submit.prevent>
        <!-- 流程模型筛选：选项来自 modelOptions（首屏一次性加载） -->
        <el-form-item label="流程模型">
          <el-select v-model="query.model_id" placeholder="请选择" clearable style="width: 200px">
            <!-- 遍历模型选项；key 用 id，值为模型 id -->
            <el-option v-for="m in modelOptions" :key="m.id" :label="m.model_name" :value="m.id" />
          </el-select>
        </el-form-item>
        <!-- 事件类型筛选：选项与表单中的 eventTypes 共用同一份常量 -->
        <el-form-item label="事件类型">
          <el-select v-model="query.event_type" placeholder="请选择" clearable style="width: 160px">
            <el-option v-for="item in eventTypes" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item class="search-actions">
          <!-- 查询：回到第一页并请求 -->
          <el-button type="primary" :icon="Search" @click="handleQuery">查询</el-button>
          <!-- 重置：清空条件后重新请求 -->
          <el-button :icon="Refresh" @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 列表区卡片：头部操作按钮 + 表格 + 分页 -->
    <el-card shadow="never" class="table-card">
      <!-- 卡片头部插槽 -->
      <template #header>
        <div class="card-header">
          <div class="card-actions">
            <!-- 新增监听器：v-perm 控制创建权限 -->
            <el-button v-perm="'wf:listener:create'" type="primary" :icon="Plus" @click="openCreate">新增</el-button>
            <!-- 批量删除：无勾选时禁用 -->
            <el-button v-perm="'wf:listener:delete'" type="danger" plain :icon="Delete" :disabled="!selectedIds.length" @click="handleBatchDelete">批量删除</el-button>
          </div>
        </div>
      </template>
      <!-- 数据表格：勾选变化回传行对象，由 onSelectionChange 提取 id -->
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据" @selection-change="onSelectionChange">
        <!-- 自动序号列 -->
        <el-table-column type="index" label="序号" width="70" align="center" />
        <!-- 勾选列，供批量删除 -->
        <el-table-column type="selection" width="50" align="center" />
        <!-- 流程模型名称：由后端联表返回，前端直接展示 -->
        <el-table-column label="流程模型" prop="model_name" min-width="140" show-overflow-tooltip />
        <!-- 事件类型：存的是英文枚举值，需经 typeName 映射为中文标签 -->
        <el-table-column label="事件类型" width="110" align="center">
          <!-- typeName(eventTypes, value) 找不到时回退显示原始值，防止空白 -->
          <template #default="scope">{{ typeName(eventTypes, scope.row.event_type) }}</template>
        </el-table-column>
        <!-- 动作类型：同样通过 typeName 映射为中文 -->
        <el-table-column label="动作" width="110" align="center">
          <template #default="scope">{{ typeName(actionTypes, scope.row.action_type) }}</template>
        </el-table-column>
        <!-- 回调地址：仅动作类型为回调接口时有实际意义，长文本省略显示 -->
        <el-table-column label="回调地址" prop="callback_url" min-width="200" show-overflow-tooltip />
        <!-- 状态列：本页约定 status=0 为启用 -->
        <el-table-column label="状态" width="90" align="center">
          <template #default="scope">
            <!-- status=0 显示启用（绿色），其余显示停用（灰色） -->
            <el-tag :type="scope.row.status === 0 ? 'success' : 'info'">{{ scope.row.status === 0 ? '启用' : '停用' }}</el-tag>
          </template>
        </el-table-column>
        <!-- 创建时间：后端格式化好的字符串 -->
        <el-table-column label="创建时间" prop="create_time" width="170" />
        <!-- 操作列：固定右侧，保证横向滚动时可见 -->
        <el-table-column label="操作" width="150" align="center" fixed="right">
          <template #default="scope">
            <!-- 编辑：打开弹窗回填当前监听规则 -->
            <el-button v-perm="'wf:listener:update'" link type="primary" :icon="Edit" @click="openEdit(scope.row)">编辑</el-button>
            <!-- 删除：单条删除，前端二次确认 -->
            <el-button v-perm="'wf:listener:delete'" link type="danger" :icon="Delete" @click="handleDelete(scope.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <!-- 分页：页码/每页条数绑定 query，变化后重新请求 -->
      <div class="pagination-wrap">
        <el-pagination background layout="total, sizes, prev, pager, next, jumper"
          :total="total" v-model:current-page="query.page" v-model:page-size="query.page_size"
          :page-sizes="[10, 20, 50, 100]" @change="getList" />
      </div>
    </el-card>

    <!-- 新增/编辑监听器弹窗：标题随 form.id 切换；点遮罩不关闭防止配置丢失 -->
    <el-dialog :title="form.id ? '编辑监听器' : '新增监听器'" v-model="dialogVisible" width="560px" :close-on-click-modal="false" destroy-on-close>
      <!-- 表单：绑定 form 与校验规则；label-width 加宽以容纳四字标签 -->
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <!-- 流程模型：必填，决定监听器作用于哪个流程 -->
        <el-form-item label="流程模型" prop="model_id">
          <el-select v-model="form.model_id" placeholder="请选择流程模型" style="width: 100%">
            <el-option v-for="m in modelOptions" :key="m.id" :label="m.model_name" :value="m.id" />
          </el-select>
        </el-form-item>
        <!-- 事件类型：必填，决定在流程的哪个阶段触发 -->
        <el-form-item label="事件类型" prop="event_type">
          <el-select v-model="form.event_type" style="width: 100%">
            <el-option v-for="item in eventTypes" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <!-- 动作类型：必填，决定触发后执行什么动作 -->
        <el-form-item label="动作类型" prop="action_type">
          <el-select v-model="form.action_type" style="width: 100%">
            <el-option v-for="item in actionTypes" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <!-- 回调地址：仅动作类型为 callback 时可编辑，其它动作无需外部地址，禁用避免误填 -->
        <el-form-item label="回调地址" prop="callback_url">
          <el-input v-model="form.callback_url" placeholder="http://host/api/callback" :disabled="form.action_type !== 'callback'" />
        </el-form-item>
        <!-- 回调参数：以 JSON 字符串形式传入外部接口，模板示例帮助用户理解格式 -->
        <el-form-item label="回调参数" prop="callback_param">
          <el-input v-model="form.callback_param" type="textarea" :rows="3" placeholder='JSON 字符串，如 {"msg":"流程启动"}' />
        </el-form-item>
        <!-- 状态：本页约定 0 启用 / 1 停用 -->
        <el-form-item label="状态" prop="status">
          <el-radio-group v-model="form.status">
            <el-radio :label="0">启用</el-radio>
            <el-radio :label="1">停用</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <!-- 底部按钮：取消关闭；确定提交并展示 loading -->
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitForm">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
// 组合式 API：ref 定义响应式状态，reactive 定义查询/表单对象，onMounted 首屏加载
import { ref, reactive, onMounted } from 'vue'
// ElMessage 操作反馈；ElMessageBox 删除确认
import { ElMessage, ElMessageBox } from 'element-plus'
// 搜索、刷新、新增、删除、编辑图标
import { Search, Refresh, Plus, Delete, Edit } from '@element-plus/icons-vue'
// 统一请求实例：自动注入 token，统一处理响应与错误提示
import request from '@/utils/request'

// 事件类型枚举：与后端 event_type 字段取值一一对应，同时驱动筛选与表单下拉
const eventTypes = [
  // 流程实例创建/提交时触发
  { label: '流程启动', value: 'start' },
  // 审批人进入某个节点时触发
  { label: '节点进入', value: 'enter' },
  // 节点审批完成时触发
  { label: '节点完成', value: 'complete' },
  // 整个流程结束时触发
  { label: '流程结束', value: 'end' },
  // 审批被驳回时触发
  { label: '流程驳回', value: 'reject' }
]
// 动作类型枚举：决定监听器命中后执行的具体行为，取值与后端 action_type 一致
const actionTypes = [
  // 调用外部 HTTP 接口，需要填写 callback_url
  { label: '回调接口', value: 'callback' },
  // 发送站内/消息通知
  { label: '消息通知', value: 'notify' },
  // 回写业务数据
  { label: '修改数据', value: 'update_data' },
  // 仅记录日志用于审计
  { label: '写入日志', value: 'log' }
]

// 列表加载中标记
const loading = ref(false)
// 表单提交中标记
const saving = ref(false)
// 当前页监听器列表
const rows = ref([])
// 记录总数
const total = ref(0)
// 勾选行 id，供批量删除
const selectedIds = ref([])
// 新增/编辑弹窗显隐
const dialogVisible = ref(false)
// 表单实例引用
const formRef = ref()
// 查询条件：model_id/event_type 为空串表示不筛选
const query = reactive({ page: 1, page_size: 10, model_id: '', event_type: '' })
// 表单数据：默认创建一个「流程启动 + 消息通知」的启用规则，降低配置成本
const form = reactive({ id: 0, model_id: '', event_type: 'start', action_type: 'notify', callback_url: '', callback_param: '', status: 0 })
// 流程模型下拉选项，首屏一次性加载（最多 1000 条）
const modelOptions = ref([])
// 校验规则：三个选择项均必填，change 时即时校验
const rules = {
  model_id: [{ required: true, message: '请选择流程模型', trigger: 'change' }],
  event_type: [{ required: true, message: '请选择事件类型', trigger: 'change' }],
  action_type: [{ required: true, message: '请选择动作类型', trigger: 'change' }]
}

// 枚举值转中文标签：用于表格展示；未匹配到则回退原值，避免出现空白单元格
function typeName(options, value) {
  return options.find(item => item.value === value)?.label || value
}
// 拉取监听器列表
async function getList() {
  loading.value = true
  try {
    // GET /api/wf/listener/list，返回 { list, total }
    const res = await request.get('/wf/listener/list', { params: query })
    rows.value = res.data.list
    total.value = res.data.total
  } finally {
    // 无论成败都关闭遮罩
    loading.value = false
  }
}
// 加载流程模型选项：一次取 1000 条，视为全量下拉数据
async function loadModels() {
  const res = await request.get('/wf/model/list', { params: { page: 1, page_size: 1000 } })
  // 兜底空数组，防止后端返回 null 时 v-for 报错
  modelOptions.value = res.data.list || []
}
// 查询：回到第一页
function handleQuery() {
  query.page = 1
  getList()
}
// 重置筛选条件并重新查询
function resetQuery() {
  Object.assign(query, { page: 1, model_id: '', event_type: '' })
  getList()
}
// 勾选变化：收集行 id
function onSelectionChange(rowsSelected) {
  selectedIds.value = rowsSelected.map(row => row.id)
}
// 新增：重置表单，模型默认选中第一个选项，减少手动选择
function openCreate() {
  Object.assign(form, { id: 0, model_id: modelOptions.value[0]?.id || '', event_type: 'start', action_type: 'notify', callback_url: '', callback_param: '', status: 0 })
  dialogVisible.value = true
}
// 编辑：回填当前行；可空字段用 || '' 兜底，避免文本框显示 null
function openEdit(row) {
  Object.assign(form, {
    id: row.id, model_id: row.model_id, event_type: row.event_type, action_type: row.action_type,
    callback_url: row.callback_url || '', callback_param: row.callback_param || '', status: row.status
  })
  dialogVisible.value = true
}
// 保存：校验通过后按 id 判断新增或更新
async function submitForm() {
  // 校验失败会 reject，中断后续请求
  await formRef.value.validate()
  saving.value = true
  try {
    if (form.id) {
      // 编辑：PUT /wf/listener/update/{id}
      await request.put(`/wf/listener/update/${form.id}`, form)
      ElMessage.success('修改成功')
    } else {
      // 新增：POST /wf/listener/create
      await request.post('/wf/listener/create', form)
      ElMessage.success('新增成功')
    }
    dialogVisible.value = false
    getList()
  } finally {
    saving.value = false
  }
}
// 单条删除：先确认再请求
async function handleDelete(row) {
  // 取消确认会 reject，不会执行删除请求
  await ElMessageBox.confirm('确认删除该监听器吗？', '提示', { type: 'warning' })
  await request.delete('/wf/listener/delete', { data: { ids: [row.id] } })
  ElMessage.success('删除成功')
  getList()
}
// 批量删除：一次提交全部勾选 id
async function handleBatchDelete() {
  await ElMessageBox.confirm(`确认删除选中的 ${selectedIds.value.length} 条监听器吗？`, '提示', { type: 'warning' })
  await request.delete('/wf/listener/delete', { data: { ids: selectedIds.value } })
  ElMessage.success('删除成功')
  getList()
}

// 挂载后先加载模型下拉，再拉列表：保证表格展示与筛选下拉都有数据
onMounted(async () => {
  await loadModels()
  getList()
})
</script>
