<!--
  文件级说明：监控告警规则管理页。
  职责：维护系统监控告警规则（CPU/内存/磁盘/网络/业务五类指标），支持筛选、分页、新增、编辑、单条/批量删除。
  依赖：@/utils/request（统一 /api 前缀、Bearer token 与错误提示）；Element Plus（表单/表格/弹窗/消息）；
        @element-plus/icons-vue 的 Search、Refresh、Plus、Delete 图标。
  数据来源：GET /mon/rule/list 列表；POST /mon/rule/create 新增；PUT /mon/rule/update/{id} 更新；
            DELETE /mon/rule/delete（请求体携带 ids 数组）删除（单条与批量共用）。
  业务含义：一条规则 = 某监控指标的取值与 threshold 做 compare_op 比较，成立即按 alarm_level 生成告警，
            并通过 channel 指定的渠道通知；status=0 的规则不参与巡检。
  被谁使用：由路由挂载在监控模块“监控告警”菜单，产生的告警记录在 mon/record 页只读展示。
-->
<template>
  <!-- 页面根容器：统一内边距与背景，保持与全站管理页一致 -->
  <div class="app-container">
    <!-- 页头区域：标题 + 当前总条数副标题 -->
    <div class="page-header">
      <div class="page-title-wrap">
        <!-- 主标题：监控告警（这里配置的是规则，不是告警记录） -->
        <h2>监控告警</h2>
        <!-- 副标题：实时展示规则总条数，便于快速判断规则规模 -->
        <div class="sub">系统监控告警规则 · 共 {{ total }} 条</div>
      </div>
    </div>

    <!-- 查询条件卡片：与表格卡片同为扁平样式，避免卡片阴影叠加导致视觉沉重 -->
    <el-card shadow="never" class="search-card">
      <!-- 行内查询表单；@submit.prevent 拦截原生提交，统一由查询按钮/回车触发 -->
      <el-form :model="query" inline @submit.prevent>
        <el-form-item label="规则名称">
          <!-- 名称关键字输入框：clearable 一键清空；回车直接查询，减少鼠标操作 -->
          <el-input v-model="query.rule_name" placeholder="请输入规则名称" clearable style="width: 170px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="监控类型">
          <!-- 监控类型下拉：值与后端枚举一致，用于只看某一类指标规则；清空表示全部 -->
          <el-select v-model="query.monitor_type" placeholder="全部" clearable style="width: 110px">
            <!-- cpu：CPU 使用率类指标 -->
            <el-option label="CPU" value="cpu" />
            <!-- memory：内存占用类指标 -->
            <el-option label="内存" value="memory" />
            <!-- disk：磁盘容量/使用率类指标 -->
            <el-option label="磁盘" value="disk" />
            <!-- network：网络流量/连通性类指标 -->
            <el-option label="网络" value="network" />
            <!-- business：业务指标（如订单失败率），与硬件指标区分 -->
            <el-option label="业务" value="business" />
          </el-select>
        </el-form-item>
        <el-form-item label="告警级别">
          <!-- 级别下拉：筛选规则触发后生成的告警级别 -->
          <el-select v-model="query.alarm_level" placeholder="全部" clearable style="width: 110px">
            <!-- info：提示级，仅告知 -->
            <el-option label="提示" value="info" />
            <!-- warning：警告级，需要关注但业务可继续 -->
            <el-option label="警告" value="warning" />
            <!-- critical：严重级，需要立即处置 -->
            <el-option label="严重" value="critical" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <!-- 状态筛选：1=启用（参与巡检），0=停用（仅保留配置） -->
          <el-select v-model="query.status" placeholder="全部" clearable style="width: 110px">
            <!-- 启用：规则会被监控任务执行 -->
            <el-option label="启用" :value="1" />
            <!-- 停用：规则保留但不产生新告警 -->
            <el-option label="停用" :value="0" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <!-- 查询按钮：回到第 1 页并按当前条件请求 -->
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <!-- 重置按钮：恢复初始条件（含分页）后重新查询 -->
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 表格卡片：头部放操作按钮，主体为规则列表，底部为分页 -->
    <el-card shadow="never" class="table-card">
      <!-- 卡片头部插槽：集中放置新增/批量删除，避免与查询区混在一起造成误解 -->
      <template #header>
        <div class="card-header">
          <div class="card-actions">
            <!-- 新增：重置表单后打开弹窗，标题切为“新增告警规则” -->
            <el-button type="primary" :icon="Plus" @click="openCreate">新增</el-button>
            <!-- 批量删除：未勾选任何行时禁用，防止空选提交；plain 表示次要危险按钮 -->
            <el-button type="danger" plain :icon="Delete" :disabled="!selection.length" @click="handleBatchDelete">批量删除</el-button>
          </div>
        </div>
      </template>
      <!-- 规则表格：selection-change 同步选中行到 selection，驱动批量删除按钮的可用状态 -->
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据" @selection-change="onSelectionChange">
        <!-- 序号列：前端自动编号，便于阅读定位，不参与业务 -->
        <el-table-column type="index" label="序号" width="70" align="center" />
        <!-- 多选列：批量删除依赖它收集 ids -->
        <el-table-column type="selection" width="50" />
        <!-- 规则名称：超长省略并悬浮显示全文，保持列宽稳定 -->
        <el-table-column label="规则名称" prop="rule_name" min-width="180" show-overflow-tooltip />
        <el-table-column label="监控类型" width="100">
          <!-- 类型用不同颜色标签区分：CPU 蓝、内存绿、磁盘橙、网络灰、业务红，便于快速扫读 -->
          <template #default="{ row }">
            <!-- cpu：CPU 指标规则，默认蓝色标签 -->
            <el-tag v-if="row.monitor_type==='cpu'" size="small">CPU</el-tag>
            <!-- memory：内存指标规则，绿色标签 -->
            <el-tag v-else-if="row.monitor_type==='memory'" size="small" type="success">内存</el-tag>
            <!-- disk：磁盘指标规则，橙色标签提示容量风险 -->
            <el-tag v-else-if="row.monitor_type==='disk'" size="small" type="warning">磁盘</el-tag>
            <!-- network：网络指标规则，灰色信息标签 -->
            <el-tag v-else-if="row.monitor_type==='network'" size="small" type="info">网络</el-tag>
            <!-- business：业务指标规则，红色标签与技术指标区分 -->
            <el-tag v-else-if="row.monitor_type==='business'" size="small" type="danger">业务</el-tag>
            <!-- 兜底：未知枚举直接显示原值，避免空白 -->
            <span v-else>{{ row.monitor_type }}</span>
          </template>
        </el-table-column>
        <!-- 比较符：规则执行时使用，如 > 表示“指标值大于阈值即告警” -->
        <el-table-column label="比较符" prop="compare_op" width="90" align="center" />
        <!-- 阈值：与比较符组成告警判定条件，CPU 场景通常为百分比 -->
        <el-table-column label="阈值" prop="threshold" width="100" />
        <el-table-column label="告警级别" width="100" align="center">
          <!-- 级别颜色与告警记录页保持一致，形成统一视觉语义 -->
          <template #default="{ row }">
            <!-- info：提示级 -->
            <el-tag v-if="row.alarm_level==='info'" size="small">提示</el-tag>
            <!-- warning：警告级 -->
            <el-tag v-else-if="row.alarm_level==='warning'" size="small" type="warning">警告</el-tag>
            <!-- critical：严重级 -->
            <el-tag v-else-if="row.alarm_level==='critical'" size="small" type="danger">严重</el-tag>
            <!-- 兜底：未知级别显示原值 -->
            <span v-else>{{ row.alarm_level }}</span>
          </template>
        </el-table-column>
        <!-- 通知渠道：逗号分隔的渠道标识（如 email,sms,dingtalk），超长省略 -->
        <el-table-column label="通知渠道" prop="channel" min-width="140" show-overflow-tooltip />
        <el-table-column label="状态" width="90" align="center">
          <!-- 1=启用（绿色）、其余=停用（灰色），颜色即巡检开关状态 -->
          <template #default="{ row }">
            <el-tag v-if="row.status===1" size="small" type="success">启用</el-tag>
            <el-tag v-else size="small" type="info">停用</el-tag>
          </template>
        </el-table-column>
        <!-- 创建时间：后端已格式化字符串，前端直接展示 -->
        <el-table-column label="创建时间" prop="create_time" width="170" />
        <!-- 操作列：固定在右侧，横向滚动时始终可见；op-col 为全局样式，统一操作按钮排布 -->
        <el-table-column label="操作" width="180" fixed="right" class-name="op-col">
          <template #default="{ row }">
            <!-- 编辑：把当前行数据回填到表单并打开弹窗 -->
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <!-- 删除：二次确认后按单条 id 删除并刷新列表 -->
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <!-- 分页容器：统一右对齐布局 -->
      <div class="pagination-wrap">
        <!-- 分页器：current-page / page-size 双向绑定 query，任一变化触发 @change 重新请求 -->
        <el-pagination background layout="total, sizes, prev, pager, next, jumper"
          :total="total" v-model:current-page="query.page" v-model:page-size="query.page_size"
          :page-sizes="[10, 20, 50, 100]" @change="fetchList" />
      </div>
    </el-card>

    <!-- 新增/编辑弹窗：标题由 dialogTitle 动态切换；close-on-click-modal=false 防误关；destroy-on-close 保证每次打开都是干净实例 -->
    <el-dialog :title="dialogTitle" v-model="dialogVisible" width="560px" :close-on-click-modal="false" destroy-on-close>
      <!-- 规则编辑表单：ref 供提交前校验；rules 只约束名称与监控类型两项必填 -->
      <el-form ref="formRef" :model="form" :rules="rules" label-width="110px">
        <!-- 栅格布局：gutter=12 控制两列间距，每行满 24 栏 -->
        <el-row :gutter="12">
          <el-col :span="24">
            <el-form-item label="规则名称" prop="rule_name">
              <!-- 规则名称必填，maxlength=100 与后端字段长度一致，避免提交超长被拒 -->
              <el-input v-model="form.rule_name" placeholder="请输入规则名称" maxlength="100" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="监控类型" prop="monitor_type">
              <!-- 监控类型决定后端采用哪个指标采集器取数，不同类型下阈值含义不同 -->
              <el-select v-model="form.monitor_type" style="width:100%">
                <!-- cpu：CPU 使用率 -->
                <el-option label="CPU" value="cpu" />
                <!-- memory：内存使用率 -->
                <el-option label="内存" value="memory" />
                <!-- disk：磁盘使用率 -->
                <el-option label="磁盘" value="disk" />
                <!-- network：网络指标 -->
                <el-option label="网络" value="network" />
                <!-- business：业务指标 -->
                <el-option label="业务" value="business" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="比较符" prop="compare_op">
              <!-- 比较符与阈值组成判定表达式，例如 “CPU 使用率 > 80” 即触发告警 -->
              <el-select v-model="form.compare_op" style="width:100%">
                <!-- 大于：指标高于阈值即告警 -->
                <el-option label="大于 >" value=">" />
                <!-- 大于等于：等于阈值也视为越界 -->
                <el-option label="大于等于 >=" value=">=" />
                <!-- 小于：用于低水位类告警（如可用空间不足） -->
                <el-option label="小于 <" value="<" />
                <!-- 小于等于：含边界的低水位判定 -->
                <el-option label="小于等于 <=" value="<=" />
                <!-- 等于：精确匹配类判定，保留与后端枚举一致 -->
                <el-option label="等于 =" value="=" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="阈值" prop="threshold">
              <!-- 阈值：precision=2 限定两位小数，与后端数值精度对齐；紧邻比较符便于阅读判定表达式 -->
              <el-input-number v-model="form.threshold" :precision="2" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="告警级别" prop="alarm_level">
              <!-- 告警级别决定生成记录的严重程度与通知优先级 -->
              <el-select v-model="form.alarm_level" style="width:100%">
                <!-- info：提示级 -->
                <el-option label="提示" value="info" />
                <!-- warning：警告级 -->
                <el-option label="警告" value="warning" />
                <!-- critical：严重级 -->
                <el-option label="严重" value="critical" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="通知渠道" prop="channel">
              <!-- 通知渠道：多值用英文逗号分隔（email,sms,dingtalk），后端据此分发告警消息 -->
              <el-input v-model="form.channel" placeholder="如 email,sms,dingtalk" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="状态" prop="status">
              <!-- 状态开关：1=启用参与巡检，0=停用仅保留配置；active/inactive-value 保证提交数值而非布尔 -->
              <el-switch v-model="form.status" :active-value="1" :inactive-value="0" active-text="启用" inactive-text="停用" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <!-- 弹窗底部：取消直接关闭不落库；确定走 submitForm（内含校验与 saving loading 防重复提交） -->
      <template #footer>
        <el-button @click="dialogVisible=false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitForm">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
// 组合式 API：ref 管标量/数组，reactive 管查询与表单对象，onMounted 做首屏加载
import { ref, reactive, onMounted } from 'vue'
// ElMessage 用于轻提示成功结果；ElMessageBox 用于删除前的二次确认
import { ElMessage, ElMessageBox } from 'element-plus'
// 工具栏与操作列图标，保持与其它管理页一致的按钮视觉
import { Search, Refresh, Plus, Delete } from '@element-plus/icons-vue'
// 统一请求实例：自动带 token、统一报错与 401 处理，业务代码只处理成功路径
import request from '@/utils/request'

// 表格加载态：请求期间显示遮罩，避免重复查询
const loading = ref(false)
// 当前页规则列表，绑定 el-table 的 :data
const rows = ref([])
// 后端总条数：供分页与页头“共 N 条”使用
const total = ref(0)
// 表格勾选行集合：驱动批量删除按钮禁用状态与批量 ids 收集
const selection = ref([])
// 保存中状态：控制弹窗“确定”按钮 loading，防止重复提交
const saving = ref(false)
// 弹窗显隐：新增/编辑共用同一个弹窗
const dialogVisible = ref(false)
// 弹窗标题：新增与编辑复用弹窗时切换文案
const dialogTitle = ref('新增告警规则')
// 表单组件实例：提交前调用 validate() 触发 rules 校验
const formRef = ref()

// 查询条件快照：重置时整体覆盖 query，保证清空筛选并回到第 1 页
// monitor_type/alarm_level 用空串、status 用 null，符合后端“空值不过滤”的约定
const query_orig = { page: 1, page_size: 10, rule_name: '', monitor_type: '', alarm_level: '', status: null }
// 响应式查询对象：与查询表单、分页双向绑定，直接作为列表接口的 params
const query = reactive({ ...query_orig })

// 表单初始值快照：新增时用它重置表单，避免残留上一次编辑的数据
// 默认值为一条“CPU > 80 警告、启用”的常用规则，减少新增时的输入成本
const form_orig = {
  id: null, rule_name: '', monitor_type: 'cpu', compare_op: '>', threshold: 80,
  alarm_level: 'warning', channel: '', status: 1
}
// 响应式表单对象：弹窗内所有控件都绑定到它
const form = reactive({ ...form_orig })

// 表单校验规则：名称与监控类型必填；其余字段有默认值，故不做必填约束
const rules = {
  rule_name: [{ required: true, message: '请输入规则名称', trigger: 'blur' }],
  monitor_type: [{ required: true, message: '请选择监控类型', trigger: 'change' }]
}

// 接口基础路径：列表/新增/更新/删除都以此为前缀，改版本号只需改这里
const apiBase = '/mon/rule'

// 列表查询：查询、重置、翻页、保存后刷新都复用，避免参数拼装分散
async function fetchList() {
  // 打开遮罩，提示用户正在加载
  loading.value = true
  try {
    // GET 分页查询：query 里的 page/page_size 及筛选字段自动序列化到 URL
    const res = await request.get(apiBase + '/list', { params: query })
    // list 兜底空数组，total 兜底 0，防止后端返回 null 时表格/分页异常
    rows.value = res.data.list || []
    total.value = res.data.total || 0
  // 无论成功失败都关闭遮罩
  } finally { loading.value = false }
}

// 查询：先回到第 1 页，避免旧页码越界导致空结果
function handleSearch() { query.page = 1; fetchList() }
// 重置：用快照覆盖查询条件后重新查询
function handleReset() { Object.assign(query, query_orig); handleSearch() }
// 勾选变化：把选中行缓存到 selection，供批量删除使用
function onSelectionChange(r) { selection.value = r }

// 新增：用快照重置表单（含 id=null，保证走新增分支），切换标题并打开弹窗
function openCreate() { Object.assign(form, form_orig); dialogTitle.value = '新增告警规则'; dialogVisible.value = true }
// 编辑：先铺默认值再覆盖当前行数据，保证后端未返回的字段有默认值；id 决定后续走更新分支
function openEdit(row) { Object.assign(form, form_orig, row); dialogTitle.value = '编辑告警规则'; dialogVisible.value = true }

// 提交表单：先校验，再按是否有 id 分流到更新或新增，成功后关闭弹窗并刷新列表
async function submitForm() {
  // validate 失败会 reject 并中断流程，避免提交非法数据
  await formRef.value.validate()
  saving.value = true
  try {
    if (form.id) {
      // 更新：把 id 从请求体中拆出（后端从路径取 id），其余字段作为 JSON 体提交
      const { id, ...data } = form
      await request.put(`${apiBase}/update/${id}`, data); ElMessage.success('更新成功')
    } else {
      // 新增：整表单作为 JSON 体提交，id=null 由后端生成
      await request.post(apiBase + '/create', form); ElMessage.success('新增成功')
    }
    // 成功后才关闭弹窗，并刷新当前页数据
    dialogVisible.value = false; fetchList()
  // 失败时保留弹窗方便用户修改；无论如何先解除 loading
  } finally { saving.value = false }
}

// 单条删除：先二次确认（取消会 reject 并中断），再以 DELETE 请求体提交 ids 数组
async function handleDelete(row) {
  await ElMessageBox.confirm('确定删除该告警规则？', '提示', { type: 'warning' })
  // 单条与批量共用删除接口，统一传 ids 数组便于后端复用校验逻辑
  await request.delete(apiBase + '/delete', { data: { ids: [row.id] } })
  ElMessage.success('删除成功'); fetchList()
}

// 批量删除：确认文案带选中数量，降低误删风险
async function handleBatchDelete() {
  await ElMessageBox.confirm(`确定删除选中的 ${selection.value.length} 条？`, '提示', { type: 'warning' })
  // 从选中行提取 id 组成 ids 数组提交
  await request.delete(apiBase + '/delete', { data: { ids: selection.value.map(r => r.id) } })
  ElMessage.success('批量删除成功'); fetchList()
}

// 首屏加载规则列表；下拉选项在本页不存在，无需额外请求
onMounted(fetchList)
</script>
