<!-- 消息推送渠道配置页（消息中心 / 推送渠道）
     职责：维护各推送渠道（site 站内信、sms 短信、email 邮件等）的启用开关与渠道参数 JSON。
     接口：GET /msg/push_config/list（分页）、POST /msg/push_config/create、
           PUT /msg/push_config/update/{id}、PUT /msg/push_config/status/{id}（仅改启用状态）、
           DELETE /msg/push_config/delete（单条与批量共用，ids 放在请求体）。
     依赖：@/utils/request（统一 baseURL、token 与错误提示）、Element Plus 表单/表格/弹窗、v-perm 按钮权限指令。
     被谁使用：由后端菜单动态挂载进入；这里的渠道配置决定消息最终通过哪种方式下发。 -->
<template>
  <!-- 页面根容器：复用全局 .app-container 的留白与进场动画，保持各业务页一致 -->
  <div class="app-container">
    <!-- 页头：展示模块名与渠道总数，本页没有页头级操作按钮 -->
    <div class="page-header">
      <!-- 标题组：主标题与菜单名一致，副标题补充说明本页能力 -->
      <div class="page-title-wrap">
        <!-- 主标题：推送渠道 -->
        <h2>推送渠道</h2>
        <!-- 副标题：total 为服务端返回的总记录数，展示当前已配置的渠道数量 -->
        <div class="sub">多渠道推送配置 · 共 {{ total }} 条</div>
      </div>
    </div>
    <!-- 查询卡片：shadow="never" 去掉阴影，弱化辅助区域、突出下方表格 -->
    <el-card shadow="never" class="search-card">
      <!-- inline 横向排列筛选项；@submit.prevent 阻止回车触发浏览器原生提交导致整页刷新 -->
      <el-form :model="query" inline @submit.prevent>
        <!-- 渠道筛选：按渠道编码（site/sms/email 等）检索 -->
        <el-form-item label="渠道">
          <!-- clearable 一键清空；固定 160px 让查询栏宽度稳定；@keyup.enter 支持键盘直接查询 -->
          <el-input v-model="query.channel" placeholder="请输入渠道编码" clearable style="width: 160px" @keyup.enter="handleSearch" />
        </el-form-item>
        <!-- 启用状态筛选：取值为 1/0 数字，与后端 tinyint 字段保持一致；null 表示"全部" -->
        <el-form-item label="启用状态">
          <!-- clearable 清空后 enabled 回到 null，即不再按启用状态过滤 -->
          <el-select v-model="query.enabled" placeholder="全部" clearable style="width: 120px">
            <!-- 1 = 启用：该渠道可被消息发送流程使用 -->
            <el-option label="启用" :value="1" />
            <!-- 0 = 停用：配置保留，但发送时跳过该渠道 -->
            <el-option label="停用" :value="0" />
          </el-select>
        </el-form-item>
        <!-- 操作按钮组：查询 / 重置，无 label 紧跟筛选项，符合从左到右的操作顺序 -->
        <el-form-item>
          <!-- 主按钮：触发查询并回到第一页；Search 为已导入的图标组件对象 -->
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <!-- 次按钮：恢复默认查询条件后重新加载，无需二次确认 -->
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 表格卡片：与查询区分离，刷新列表时只更新表体 -->
    <el-card shadow="never" class="table-card">
      <!-- 工具栏插槽：新增与批量删除；批量删除依赖表格勾选，放在表格正上方更顺手 -->
      <template #header>
        <div class="card-header">
          <div class="card-actions">
            <!-- 新增：需 msg:create 权限；openCreate 会先重置表单再打开弹窗 -->
            <el-button v-perm="'msg:create'" type="primary" :icon="Plus" @click="openCreate">新增</el-button>
            <!-- 批量删除：需 msg:delete；plain 弱化危险色；未勾选任何行时禁用，避免空提交 -->
            <el-button v-perm="'msg:delete'" type="danger" plain :icon="Delete" :disabled="!selection.length" @click="handleBatchDelete">批量删除</el-button>
          </div>
        </div>
      </template>
      <!-- 表格：v-loading 复用请求加载态；stripe 隔行变色便于长列表读数；空态使用中文；
           @selection-change 把勾选行同步给批量删除按钮 -->
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据" @selection-change="onSelectionChange">
        <!-- 序号列：仅用于阅读定位，宽度 70 足够容纳三位数 -->
        <el-table-column type="index" label="序号" width="70" align="center" />
        <!-- 多选列：为批量删除提供勾选能力，固定 50px 不参与剩余宽度分配 -->
        <el-table-column type="selection" width="50" />
        <!-- 渠道编码：后端唯一标识（如 site/sms/email）；创建后不可修改，见弹窗中的 :disabled 控制 -->
        <el-table-column label="渠道编码" prop="channel" min-width="120" show-overflow-tooltip />
        <!-- 渠道名称：给人看的展示名，与编码分离，换文案不影响程序按编码判断 -->
        <el-table-column label="渠道名称" prop="channel_name" min-width="150" show-overflow-tooltip />
        <!-- 启用列：开关直接改写行数据，change 时立即调用状态接口（不走整表单提交） -->
        <el-table-column label="启用" width="90" align="center">
          <template #default="{ row }">
            <!-- active-value/inactive-value 用 1/0 对齐后端；v-perm 无 msg:update 时隐藏该开关 -->
            <el-switch v-model="row.enabled" :active-value="1" :inactive-value="0" v-perm="'msg:update'" @change="handleStatusChange(row)" />
          </template>
        </el-table-column>
        <!-- 配置 JSON：渠道参数（如短信签名、SMTP 账号），后端按字符串原样存储，前端不做结构解析 -->
        <el-table-column label="配置JSON" prop="config_json" min-width="240" show-overflow-tooltip />
        <!-- 备注：运营侧的补充说明 -->
        <el-table-column label="备注" prop="remark" min-width="160" show-overflow-tooltip />
        <!-- 创建时间：后端格式化的时间字符串，直接展示 -->
        <el-table-column label="创建时间" prop="create_time" width="170" />
        <!-- 操作列：fixed="right" 固定在最右侧，横向滚动时操作按钮仍然可见 -->
        <el-table-column label="操作" width="180" fixed="right" class-name="op-col">
          <template #default="{ row }">
            <!-- 编辑：需 msg:update 权限，整行数据带入表单 -->
            <el-button v-perm="'msg:update'" link type="primary" @click="openEdit(row)">编辑</el-button>
            <!-- 删除：需 msg:delete 权限，单条删除同样走 ids 数组接口 -->
            <el-button v-perm="'msg:delete'" link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <!-- 分页：background 给页码加底色；layout 依次展示总数、每页条数、翻页、跳页；
           total 绑定服务端总数；current-page/page-size 双向绑定回 query，翻页即改查询参数；
           @change 在页码或每页条数变化时统一重新拉取列表 -->
      <div class="pagination-wrap">
        <el-pagination background layout="total, sizes, prev, pager, next, jumper"
          :total="total" v-model:current-page="query.page" v-model:page-size="query.page_size"
          :page-sizes="[10, 20, 50, 100]" @change="fetchList" />
      </div>
    </el-card>

    <!-- 新增/编辑弹窗：标题随模式切换；close-on-click-modal=false 防止误点遮罩丢失填写内容；
         destroy-on-close 关闭即销毁表单，下次打开重新挂载、不会残留校验状态 -->
    <el-dialog :title="dialogTitle" v-model="dialogVisible" width="640px" :close-on-click-modal="false" destroy-on-close>
      <!-- ref 用于调用 validate；:model 绑定表单数据；:rules 绑定校验规则；label-width 统一标签宽度 -->
      <el-form ref="formRef" :model="form" :rules="rules" label-width="110px">
        <!-- 渠道编码：编辑时 :disabled="!!form.id" 禁止修改——编码会被消息模板/日志引用，需保持稳定 -->
        <el-form-item label="渠道编码" prop="channel">
          <!-- maxlength 32 与后端字段长度对齐；placeholder 给出内置渠道的编码示例 -->
          <el-input v-model="form.channel" placeholder="如 site/sms/email" maxlength="32" :disabled="!!form.id" />
        </el-form-item>
        <!-- 渠道名称：展示名称，可随时调整，不影响发送逻辑 -->
        <el-form-item label="渠道名称" prop="channel_name">
          <!-- maxlength 100 与后端字段长度对齐 -->
          <el-input v-model="form.channel_name" placeholder="请输入渠道名称" maxlength="100" />
        </el-form-item>
        <!-- 是否启用：单选 1/0，语义与列表开关、查询下拉保持一致 -->
        <el-form-item label="是否启用" prop="enabled">
          <el-radio-group v-model="form.enabled">
            <!-- 1 = 启用 -->
            <el-radio :value="1">启用</el-radio>
            <!-- 0 = 停用 -->
            <el-radio :value="0">停用</el-radio>
          </el-radio-group>
        </el-form-item>
        <!-- 配置 JSON：以字符串保存渠道凭据/参数；前端只负责录入，不做 JSON.parse 校验 -->
        <el-form-item label="配置JSON" prop="config_json">
          <!-- 5 行文本域便于查看较大配置；placeholder 用示例提示键值对格式 -->
          <el-input v-model="form.config_json" type="textarea" :rows="5" placeholder='{"key":"value"}' />
        </el-form-item>
        <!-- 备注：可选说明，2 行足够 -->
        <el-form-item label="备注" prop="remark">
          <el-input v-model="form.remark" type="textarea" :rows="2" placeholder="请输入备注" />
        </el-form-item>
      </el-form>
      <!-- 弹窗底部按钮：取消直接关闭；确定带 loading 防止重复提交 -->
      <template #footer>
        <el-button @click="dialogVisible=false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitForm">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
// 组合式 API：ref 定义基本类型响应式、reactive 定义对象响应式、onMounted 做首屏加载
import { ref, reactive, onMounted } from 'vue'
// ElMessage 用于成功提示；ElMessageBox 用于删除前的二次确认
import { ElMessage, ElMessageBox } from 'element-plus'
// 图标组件需以组件对象形式传给 :icon，因此直接导入
import { Search, Refresh, Plus, Delete } from '@element-plus/icons-vue'
// 统一请求封装：已内置 baseURL=/api、token 注入与错误提示
import request from '@/utils/request'

// 表格加载态：请求期间给表格加遮罩，避免用户看到旧数据误以为已刷新
const loading = ref(false)
// 当前页的渠道配置列表
const rows = ref([])
// 服务端返回的总记录数，供分页组件计算页数
const total = ref(0)
// 当前勾选的行，批量删除按钮的禁用与提交都依赖它
const selection = ref([])
// 提交中标记，用于确定按钮 loading，防止重复提交
const saving = ref(false)
// 新增/编辑弹窗显隐
const dialogVisible = ref(false)
// 弹窗标题，打开时按"新增/编辑"改写
const dialogTitle = ref('新增')
// el-form 实例，提交前调用 validate 做必填校验
const formRef = ref()

// 查询条件默认值；channel 为空字符串、enabled 为 null 都表示"不过滤"，单独保存一份便于重置
const query_orig = { page: 1, page_size: 10, channel: '', enabled: null }
// 实际查询条件：用 reactive 拷贝默认值，模板与请求参数共用同一个对象
const query = reactive({ ...query_orig })

// 表单默认值：新增前用它清空；编辑时先铺默认值再覆盖行数据，避免残留上一次编辑的内容
const form_orig = {
  id: null, channel: '', channel_name: '', enabled: 1, config_json: '', remark: ''
}
// 当前新增/编辑的表单数据，与弹窗表单双向绑定
const form = reactive({ ...form_orig })

// 必填校验规则：渠道编码与名称都不能为空，文本框失焦时触发
const rules = {
  channel: [{ required: true, message: '请输入渠道编码', trigger: 'blur' }],
  channel_name: [{ required: true, message: '请输入渠道名称', trigger: 'blur' }]
}

// 集中维护接口前缀：避免各调用处硬编码相同的 base，改路径时只需改这一处
function apiUrl(action) {
  const base = '/msg/push_config'
  // 按动作名返回对应接口地址，action 由调用方保证合法
  return {
    list: base + '/list',
    create: base + '/create',
    update: base + '/update',
    delete: base + '/delete'
  }[action]
}

// 拉取列表：请求期间开启 loading，异常时也通过 finally 关闭，避免表格一直转圈
async function fetchList() {
  loading.value = true
  try {
    // 直接把响应式的 query 作为 params；空字符串/null 由后端忽略，不影响过滤结果
    const res = await request.get(apiUrl('list'), { params: query })
    // 兜底空值，避免后端未返回 list/total 时页面报错
    rows.value = res.data.list || []
    total.value = res.data.total || 0
  } finally { loading.value = false }
}
// 查询：筛选条件变化后回到第 1 页，防止停留在已越界的页码
function handleSearch() { query.page = 1; fetchList() }
// 重置：Object.assign 回填默认值（保留 reactive 引用，不破坏模板绑定），随后重新查询
function handleReset() { Object.assign(query, query_orig); handleSearch() }
// 表格勾选变化时同步选中行数组
function onSelectionChange(r) { selection.value = r }

// 新增：先把表单恢复为默认值，设置标题并打开弹窗
function openCreate() { Object.assign(form, form_orig); dialogTitle.value = '新增渠道'; dialogVisible.value = true }
// 编辑：先铺默认值再覆盖行数据，保证当前行没有的字段回到默认而不是残留上一条记录的值
function openEdit(row) { Object.assign(form, form_orig, row); dialogTitle.value = '编辑渠道'; dialogVisible.value = true }

// 提交表单：先校验，再按有无 id 区分新增/更新，成功后关闭弹窗并刷新列表
async function submitForm() {
  // validate 返回 Promise，校验失败会抛出异常并中断后续提交
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
    // 成功后关闭弹窗并刷新列表，让表格显示最新数据
    dialogVisible.value = false; fetchList()
  } finally { saving.value = false }
}

// 行内启用开关：change 后立即提交状态变更，只发 enabled 一个字段，不再走整表单校验
async function handleStatusChange(row) {
  await request.put(`/msg/push_config/status/${row.id}`, { enabled: row.enabled })
  // 按开关值给出不同提示文案，让用户确认操作已生效
  ElMessage.success(row.enabled === 1 ? '已启用' : '已停用')
}

// 单条删除：先二次确认（用户取消会 reject，后续删除不会执行），再按 ids 数组删除
async function handleDelete(row) {
  await ElMessageBox.confirm('确定删除该渠道配置？', '提示', { type: 'warning' })
  await request.delete(apiUrl('delete'), { data: { ids: [row.id] } })
  ElMessage.success('删除成功'); fetchList()
}

// 批量删除：用勾选行的 id 组成数组，与单条删除共用同一个 delete 接口
async function handleBatchDelete() {
  await ElMessageBox.confirm(`确定删除选中的 ${selection.value.length} 条配置？`, '提示', { type: 'warning' })
  await request.delete(apiUrl('delete'), { data: { ids: selection.value.map(r => r.id) } })
  ElMessage.success('批量删除成功'); fetchList()
}

// 页面挂载后立即加载第一页数据
onMounted(fetchList)
</script>
