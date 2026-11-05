<!-- 文件级说明：安全策略 - IP 访问控制（黑/白名单）列表页。
     职责：按 IP、名单类型、状态筛选名单，并支持新增、编辑、单条/批量删除。
     依赖：Vue 3 <script setup>、Element Plus（表格/弹窗/消息提示/图标）、@/utils/request（统一请求封装，baseURL=/api）。
     被谁使用：由 sec（安全）模块的路由挂载，作为 IP 黑名单/白名单的管理入口。
     注意：本文件不含 <style> 块，app-container / search-card / table-card 等样式均来自全局样式表。 -->
<template>
  <!-- 页面根容器：套用全局 app-container 布局（统一内边距与背景），向下承载页头与查询/表格两张卡片 -->
  <div class="app-container">
    <!-- 页头区域：左侧标题 + 副标题，副标题实时展示接口返回的总条数 -->
    <div class="page-header">
      <!-- 标题容器：横向排列主标题与统计信息 -->
      <div class="page-title-wrap">
        <!-- 页面主标题：固定文案，标明当前功能属于安全策略模块 -->
        <h2>安全策略</h2>
        <!-- 副标题：说明当前页面为 IP 访问控制，并回显 total（由列表接口返回，随查询条件变化） -->
        <div class="sub">IP访问控制 · 共 {{ total }} 条</div>
      </div>
    </div>

    <!-- 查询条件卡片：承载搜索表单；shadow="never" 去掉卡片阴影，与后台管理页的扁平视觉保持一致 -->
    <el-card shadow="never" class="search-card">
      <!-- 搜索表单：inline 让各表单项横向排列；@submit.prevent 阻止回车触发表单默认提交导致整页刷新 -->
      <el-form :model="query" inline @submit.prevent>
        <!-- IP 地址筛选项：绑定 query.ip，作为 list 接口的筛选参数 -->
        <el-form-item label="IP地址">
          <!-- 输入框：clearable 支持一键清空条件；@keyup.enter 回车即查询，减少鼠标操作；固定宽度让工具栏更整齐 -->
          <el-input v-model="query.ip" placeholder="请输入IP" clearable style="width: 170px" @keyup.enter="handleSearch" />
        </el-form-item>
        <!-- 名单类型筛选项：对应后端 control_type 字段 -->
        <el-form-item label="类型">
          <!-- 下拉框：placeholder="全部" 表示不限定类型；clearable 清空后回到"全部"语义 -->
          <el-select v-model="query.control_type" placeholder="全部" clearable style="width: 110px">
            <!-- 黑名单：命中的 IP 请求会被拒绝（后端取值 black） -->
            <el-option label="黑名单" value="black" />
            <!-- 白名单：命中的 IP 请求会被放行，通常优先于黑名单判断（后端取值 white） -->
            <el-option label="白名单" value="white" />
          </el-select>
        </el-form-item>
        <!-- 启用状态筛选项：对应后端 status 字段（1 启用 / 0 停用） -->
        <el-form-item label="状态">
          <!-- 下拉框：clearable 后可查询全部状态，便于排查历史规则 -->
          <el-select v-model="query.status" placeholder="全部" clearable style="width: 110px">
            <!-- 启用：规则正在生效，会参与访问控制判断 -->
            <el-option label="启用" :value="1" />
            <!-- 停用：规则保留在库中但不参与拦截，便于临时关闭后再恢复 -->
            <el-option label="停用" :value="0" />
          </el-select>
        </el-form-item>
        <!-- 操作按钮行：不写 label，借助 inline 布局与上方表单项对齐 -->
        <el-form-item>
          <!-- 查询按钮：点击后回到第 1 页并重新拉取列表，避免停留在已超出的页码 -->
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <!-- 重置按钮：恢复 query_orig 默认条件（含分页参数）后重新查询 -->
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 数据表格卡片：上方工具栏放新增/批量删除，下方放表格与分页 -->
    <el-card shadow="never" class="table-card">
      <!-- 卡片头部插槽：用自定义头部承载操作按钮，与查询卡片形成上下分区 -->
      <template #header>
        <!-- 头部容器：左右两端布局，按钮统一收在左侧 actions 中 -->
        <div class="card-header">
          <!-- 操作按钮组 -->
          <div class="card-actions">
            <!-- 新增按钮：打开新增弹窗，表单预填默认值（黑名单、启用） -->
            <el-button type="primary" :icon="Plus" @click="openCreate">新增</el-button>
            <!-- 批量删除：未勾选任何行时 disabled，避免发出空 ids 请求；plain 弱化危险按钮的视觉权重 -->
            <el-button type="danger" plain :icon="Delete" :disabled="!selection.length" @click="handleBatchDelete">批量删除</el-button>
          </div>
        </div>
      </template>
      <!-- 表格：v-loading 绑定请求态显示遮罩；stripe 斑马纹提升可读性；selection-change 把勾选行同步给批量删除 -->
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据" @selection-change="onSelectionChange">
        <!-- 序号列：type="index" 自动按当前页顺序编号，不做数据字段映射 -->
        <el-table-column type="index" label="序号" width="70" align="center" />
        <!-- 多选列：提供批量操作入口，宽度仅容纳复选框 -->
        <el-table-column type="selection" width="50" />
        <!-- IP 地址列：展示规则具体的 IP 或 CIDR 网段，min-width 保证长地址不被过度挤压 -->
        <el-table-column label="IP地址" prop="ip" min-width="140" />
        <!-- 名单类型列：把后端英文枚举翻译成中文标签，颜色区分风险等级 -->
        <el-table-column label="类型" width="100">
          <!-- 默认插槽：解构出当前行 row，按类型渲染不同标签 -->
          <template #default="{ row }">
            <!-- 黑名单：拦截型规则，用 danger 红色标签提示风险 -->
            <el-tag v-if="row.control_type==='black'" size="small" type="danger">黑名单</el-tag>
            <!-- 白名单：放行型规则，用 success 绿色标签表示安全 -->
            <el-tag v-else-if="row.control_type==='white'" size="small" type="success">白名单</el-tag>
            <!-- 兜底分支：后端出现未知枚举值时直接显示原值，便于排查数据问题 -->
            <span v-else>{{ row.control_type }}</span>
          </template>
        </el-table-column>
        <!-- 原因列：记录加入名单的业务原因；show-overflow-tooltip 让超长文案省略并可悬浮查看全文 -->
        <el-table-column label="原因" prop="reason" min-width="180" show-overflow-tooltip />
        <!-- 状态列：展示规则是否参与访问控制判断 -->
        <el-table-column label="状态" width="90" align="center">
          <!-- 默认插槽：按 status 数值渲染启停标签 -->
          <template #default="{ row }">
            <!-- 启用：status=1 表示规则生效 -->
            <el-tag v-if="row.status===1" size="small" type="success">启用</el-tag>
            <!-- 其余值统一按停用展示，避免脏数据导致空白单元格 -->
            <el-tag v-else size="small" type="info">停用</el-tag>
          </template>
        </el-table-column>
        <!-- 过期时间列：到期后规则自动失效 -->
        <el-table-column label="过期时间" prop="expire_time" width="170">
          <!-- 默认插槽：expire_time 为空表示永久有效，用"永久"文案替代空白 -->
          <template #default="{ row }">{{ row.expire_time || '永久' }}</template>
        </el-table-column>
        <!-- 创建时间列：规则录入时间，由后端返回，前端不做格式化 -->
        <el-table-column label="创建时间" prop="create_time" width="170" />
        <!-- 操作列：fixed="right" 横向滚动时固定在右侧；op-col 套用全局操作列样式 -->
        <el-table-column label="操作" width="180" fixed="right" class-name="op-col">
          <!-- 默认插槽：行级操作按钮 -->
          <template #default="{ row }">
            <!-- 编辑：把当前行数据带入弹窗，复用同一个表单组件 -->
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <!-- 删除：单条删除前会弹确认框，降低误操作概率 -->
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <!-- 分页容器：统一右对齐分页组件 -->
      <div class="pagination-wrap">
        <!-- 分页：background 使用背景块样式；layout 依次展示总数、每页条数、上一页、页码、下一页、跳页 -->
        <el-pagination background layout="total, sizes, prev, pager, next, jumper"
          :total="total" v-model:current-page="query.page" v-model:page-size="query.page_size"
          :page-sizes="[10, 20, 50, 100]" @change="fetchList" />
        <!-- 说明：current-page 与 page-size 双向绑定到 query，页码或每页条数变化都会触发 @change 重新查询 -->
      </div>
    </el-card>

    <!-- 新增/编辑弹窗：两种场景复用同一表单，title 由 dialogTitle 动态切换 -->
    <el-dialog :title="dialogTitle" v-model="dialogVisible" width="520px" :close-on-click-modal="false" destroy-on-close>
      <!-- 表单：formRef 供提交时调用 validate；rules 提供必填校验；label-width 统一标签宽度 -->
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <!-- 栅格布局：gutter=12 控制列间距，整行 24 栅格、半行 12 栅格排布表单项 -->
        <el-row :gutter="12">
          <!-- IP 地址：独占整行，便于完整输入网段 -->
          <el-col :span="24">
            <!-- 表单项：prop 与 rules 中的 ip 字段对应，校验结果会内联显示 -->
            <el-form-item label="IP地址" prop="ip">
              <!-- 输入框：支持单个 IP 或 CIDR 网段；maxlength 与后端字段长度保持一致，防止超长入库 -->
              <el-input v-model="form.ip" placeholder="如 192.168.1.1 或 192.168.1.0/24" maxlength="64" />
            </el-form-item>
          </el-col>
          <!-- 名单类型：单选，黑/白名单互斥 -->
          <el-col :span="24">
            <!-- 表单项：prop=control_type 触发必填校验 -->
            <el-form-item label="类型" prop="control_type">
              <!-- 单选组：绑定 form.control_type，取值与后端枚举一一对应 -->
              <el-radio-group v-model="form.control_type">
                <!-- 黑名单：选中后该 IP 请求被拒绝 -->
                <el-radio value="black">黑名单</el-radio>
                <!-- 白名单：选中后该 IP 请求被放行 -->
                <el-radio value="white">白名单</el-radio>
              </el-radio-group>
            </el-form-item>
          </el-col>
          <!-- 原因：多行文本，便于写清拉黑/放行的依据 -->
          <el-col :span="24">
            <!-- 表单项：原因非必填，仅作审计说明 -->
            <el-form-item label="原因" prop="reason">
              <!-- 文本域：2 行高度兼顾空间与可读性 -->
              <el-input v-model="form.reason" type="textarea" :rows="2" placeholder="请输入原因" />
            </el-form-item>
          </el-col>
          <!-- 过期时间：半行，与状态并排以节省弹窗高度 -->
          <el-col :span="12">
            <!-- 表单项：prop=expire_time，留空代表永久有效 -->
            <el-form-item label="过期时间" prop="expire_time">
              <!-- 日期时间选择器：clearable 清空即永久；宽度撑满所在栅格列，避免控件过窄 -->
              <el-date-picker v-model="form.expire_time" type="datetime" placeholder="不过期则留空" clearable style="width:100%" />
            </el-form-item>
          </el-col>
          <!-- 状态：半行，开关直接控制启用/停用 -->
          <el-col :span="12">
            <!-- 表单项：prop=status，取值 1/0 与后端字段类型保持一致 -->
            <el-form-item label="状态" prop="status">
              <!-- 开关：active-value=1、inactive-value=0，显式指定避免布尔值与后端整型不一致 -->
              <el-switch v-model="form.status" :active-value="1" :inactive-value="0" active-text="启用" inactive-text="停用" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <!-- 底部插槽：取消/确定按钮 -->
      <template #footer>
        <!-- 取消：直接关闭弹窗，不提交也不刷新列表 -->
        <el-button @click="dialogVisible=false">取消</el-button>
        <!-- 确定：loading 绑定 saving，请求期间禁用并转圈，防止重复提交产生重复数据 -->
        <el-button type="primary" :loading="saving" @click="submitForm">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
// 组合式 API：ref 管理基础响应式值，reactive 管理查询/表单对象，onMounted 用于页面挂载后首次拉取数据
import { ref, reactive, onMounted } from 'vue'
// Element Plus 的消息提示与确认框：用于操作结果反馈、删除前二次确认
import { ElMessage, ElMessageBox } from 'element-plus'
// 按钮图标：Search 查询、Refresh 重置、Plus 新增、Delete 删除，统一使用 Element Plus 图标库
import { Search, Refresh, Plus, Delete } from '@element-plus/icons-vue'
// 统一请求实例：已内置 baseURL=/api、token 注入与错误提示，业务代码只处理成功路径
import request from '@/utils/request'

// 表格加载态：请求期间为 true，交给 el-table 的 v-loading 显示遮罩，避免弱网下误判为无数据
const loading = ref(false)
// 当前页数据：由 list 接口的 data.list 填充，仅用于展示
const rows = ref([])
// 总条数：由 list 接口的 data.total 填充，同时供分页组件与页头统计使用
const total = ref(0)
// 已勾选行：表格 selection-change 回写，用于控制"批量删除"按钮的禁用态
const selection = ref([])
// 保存中标记：新增/更新期间置 true，绑定到确定按钮 loading，防止重复提交
const saving = ref(false)
// 弹窗显隐：新增与编辑共用一个弹窗，靠该开关统一切换
const dialogVisible = ref(false)
// 弹窗标题：新增与编辑仅文案不同，用 ref 动态切换
const dialogTitle = ref('新增IP名单')
// 表单实例：提交时调用 validate() 触发 el-form 校验规则
const formRef = ref()

// 查询条件默认值：抽成常量作为"重置"基准，避免重置时把分页大小等配置改乱
const query_orig = { page: 1, page_size: 10, ip: '', control_type: '', status: null }
// 响应式查询对象：用展开拷贝与基准解耦，修改当前条件不会污染 query_orig
const query = reactive({ ...query_orig })

// 表单默认值：默认新增黑名单且启用，打开弹窗即是可用的常见配置
const form_orig = {
  id: null, ip: '', control_type: 'black', reason: '', expire_time: null, status: 1
}
// 响应式表单对象：与默认值解耦，编辑时通过 Object.assign 覆盖字段
const form = reactive({ ...form_orig })

// 表单校验规则：IP 与类型必填；IP 在失焦时校验，类型在下拉变更时校验
const rules = {
  ip: [{ required: true, message: '请输入IP地址', trigger: 'blur' }],
  control_type: [{ required: true, message: '请选择类型', trigger: 'change' }]
}

// 接口前缀：本模块增删改查都挂在该前缀下，集中一处便于统一调整
const apiBase = '/sec/ip'

// 拉取列表：统一控制 loading，异常交给 request 拦截器提示，这里只保证 finally 复位加载态
async function fetchList() {
  loading.value = true
  try {
    // GET 分页查询：query 中的 page / page_size 与筛选条件直接序列化为 query string
    const res = await request.get(apiBase + '/list', { params: query })
    // data.list 为当前页记录；后端可能返回 null，用 [] 兜底避免表格渲染报错
    rows.value = res.data.list || []
    // data.total 为满足条件的总条数；缺失时按 0 处理，保证分页组件正常显示
    total.value = res.data.total || 0
  } finally { loading.value = false }
}

// 查询：条件变化后必须回到第 1 页，否则可能停留在超出总页数的空页
function handleSearch() { query.page = 1; fetchList() }
// 重置：先恢复默认条件（含分页参数），再走统一查询流程
function handleReset() { Object.assign(query, query_orig); handleSearch() }
// 勾选变化：直接接收 el-table 回传的选中行数组，供批量删除取 id
function onSelectionChange(r) { selection.value = r }

// 新增：先铺默认值（id=null），避免上一次编辑的 id 残留导致误走更新接口
function openCreate() { Object.assign(form, form_orig); dialogTitle.value = '新增IP名单'; dialogVisible.value = true }
// 编辑：默认值打底后再覆盖当前行，保证后端未返回的字段不会变成 undefined；标题同步切换
function openEdit(row) { Object.assign(form, form_orig, row); dialogTitle.value = '编辑IP名单'; dialogVisible.value = true }

// 提交表单：先整体校验，再按是否存在 id 分流到新增 / 更新
async function submitForm() {
  // validate 失败会 reject，后续保存逻辑不会执行（错误信息由 el-form 内联提示）
  await formRef.value.validate()
  saving.value = true
  try {
    // 有 id 视为编辑
    if (form.id) {
      // 解构剔除 id：id 已放进 URL，若留在请求体会被后端当作要修改的主键字段
      const { id, ...data } = form
      // 更新成功后提示，让用户确认操作已生效
      await request.put(`${apiBase}/update/${id}`, data); ElMessage.success('更新成功')
    } else {
      // 无 id 视为新增：整份表单 POST 到 /create
      await request.post(apiBase + '/create', form); ElMessage.success('新增成功')
    }
    // 成功后关闭弹窗并刷新列表，保证表格立即反映最新数据
    dialogVisible.value = false; fetchList()
  } finally { saving.value = false }
}

// 单条删除：先二次确认；用户点取消会 reject，后续删除请求不会发出
async function handleDelete(row) {
  await ElMessageBox.confirm('确定删除该记录？', '提示', { type: 'warning' })
  // DELETE 带请求体需用 data 字段传参；后端按 ids 数组处理，单条也统一传数组
  await request.delete(apiBase + '/delete', { data: { ids: [row.id] } })
  // 删除成功后提示并刷新，让被删记录立即从列表消失
  ElMessage.success('删除成功'); fetchList()
}

// 批量删除：确认文案带上选中数量，降低误删风险
async function handleBatchDelete() {
  await ElMessageBox.confirm(`确定删除选中的 ${selection.value.length} 条？`, '提示', { type: 'warning' })
  // 只提交 id 集合，避免把整行数据（含原因、时间等）传到后端
  await request.delete(apiBase + '/delete', { data: { ids: selection.value.map(r => r.id) } })
  // 成功后刷新列表；数据重载会同时清空表格的选中状态
  ElMessage.success('批量删除成功'); fetchList()
}

// 页面挂载后立即拉一次数据，避免用户首次进入看到空表格
onMounted(fetchList)
</script>
