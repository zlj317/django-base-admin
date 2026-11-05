<!--
  脱敏规则配置页（/dsm/rule）：
  职责：维护数据脱敏规则（适用字段类型、掩码样式、匹配正则、启停），供后端在数据输出环节按规则替换敏感内容。
  依赖：@/utils/request 统一请求、Element Plus 表格/表单/弹窗组件与图标；样式全部来自全局 styles/index.css（本文件无 style 块）。
  使用方：后台"数据脱敏"菜单；规则启用后由后端对手机号、身份证、邮箱等敏感字段做掩码处理，避免明文泄露。
  注意：掩码样式与正则配置错误会导致脱敏失效或过度掩码，属于安全相关配置。
-->
<template>
  <!-- 页面根容器：全局 .app-container 提供内边距与进场动画 -->
  <div class="app-container">
    <!-- 页面头部：标题 + 当前条件下规则总数 -->
    <div class="page-header">
      <!-- 标题容器：主副标题纵向排列 -->
      <div class="page-title-wrap">
        <!-- 主标题 -->
        <h2>脱敏规则配置</h2>
        <!-- 副标题：total 来自列表接口，随筛选变化 -->
        <div class="sub">数据脱敏规则管理 · 共 {{ total }} 条</div>
      </div>
    </div>

    <!-- 搜索区卡片：扁平无阴影，复用全局搜索区版式 -->
    <el-card shadow="never" class="search-card">
      <!-- 查询表单：inline 横向排列；@submit.prevent 阻止原生提交导致的页面刷新 -->
      <el-form :model="query" inline @submit.prevent>
        <!-- 规则名称筛选：模糊匹配，回车即查询 -->
        <el-form-item label="规则名称">
          <el-input v-model="query.rule_name" placeholder="请输入规则名称" clearable style="width: 170px" @keyup.enter="handleSearch" />
        </el-form-item>
        <!-- 规则类型筛选：即被脱敏字段的敏感类型，空值表示不过滤 -->
        <el-form-item label="规则类型">
          <el-select v-model="query.rule_type" placeholder="全部" clearable style="width: 130px">
            <!-- 类型枚举：phone=手机号（保留前 3 后 4）；id_card=身份证号（保留前后若干位）；email=邮箱（掩码用户名部分）；name=姓名（保留姓氏）；bank_card=银行卡号（保留后 4 位）；custom=自定义，按掩码样式+正则自由定义 -->
            <el-option label="手机号" value="phone" />
            <el-option label="身份证" value="id_card" />
            <el-option label="邮箱" value="email" />
            <el-option label="姓名" value="name" />
            <el-option label="银行卡" value="bank_card" />
            <el-option label="自定义" value="custom" />
          </el-select>
        </el-form-item>
        <!-- 启用状态筛选：1=启用（脱敏生效）；0=停用（保留配置但不替换数据） -->
        <el-form-item label="状态">
          <el-select v-model="query.status" placeholder="全部" clearable style="width: 110px">
            <!-- 状态枚举：1 启用、0 停用；数字值与后端 status 字段一致 -->
            <el-option label="启用" :value="1" />
            <el-option label="停用" :value="0" />
          </el-select>
        </el-form-item>
        <!-- 操作按钮：查询回第一页，重置还原全部条件 -->
        <el-form-item>
          <!-- 按当前条件查询 -->
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <!-- 清空筛选条件并重新查询 -->
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 列表区卡片：承载表格、批量操作与分页 -->
    <el-card shadow="never" class="table-card">
      <!-- 卡片头部插槽：新增与批量删除入口 -->
      <template #header>
        <!-- 头部容器 -->
        <div class="card-header">
          <!-- 操作按钮组 -->
          <div class="card-actions">
            <!-- 新增规则：打开空白弹窗，提交前由 rules 校验 -->
            <el-button type="primary" :icon="Plus" @click="openCreate">新增</el-button>
            <!-- 批量删除：未勾选时禁用，避免空 ids 请求 -->
            <el-button type="danger" plain :icon="Delete" :disabled="!selection.length" @click="handleBatchDelete">批量删除</el-button>
          </div>
        </div>
      </template>
      <!-- 数据表格：请求期遮罩 + 斑马纹，勾选行同步到 selection -->
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据" @selection-change="onSelectionChange">
        <!-- 序号列：前端行号 -->
        <el-table-column type="index" label="序号" width="70" align="center" />
        <!-- 多选列：批量删除的数据来源 -->
        <el-table-column type="selection" width="50" />
        <!-- 规则名称列：自适应宽度，超长用 tooltip 完整展示 -->
        <el-table-column label="规则名称" prop="rule_name" min-width="180" show-overflow-tooltip />
        <!-- 规则类型列：不同敏感类型用不同颜色标签区分，便于快速定位 -->
        <el-table-column label="规则类型" width="110">
          <template #default="{ row }">
            <!-- phone=手机号：默认色（最高频的敏感字段） -->
            <el-tag v-if="row.rule_type==='phone'" size="small">手机号</el-tag>
            <!-- id_card=身份证：绿色，属于强身份标识 -->
            <el-tag v-else-if="row.rule_type==='id_card'" size="small" type="success">身份证</el-tag>
            <!-- email=邮箱：橙色，掩码用户名部分 -->
            <el-tag v-else-if="row.rule_type==='email'" size="small" type="warning">邮箱</el-tag>
            <!-- name=姓名：灰色，通常只保留姓氏 -->
            <el-tag v-else-if="row.rule_type==='name'" size="small" type="info">姓名</el-tag>
            <!-- bank_card=银行卡：红色，涉及资金信息需重点关注 -->
            <el-tag v-else-if="row.rule_type==='bank_card'" size="small" type="danger">银行卡</el-tag>
            <!-- custom=自定义：默认色，掩码效果完全取决于下方样式与正则 -->
            <el-tag v-else-if="row.rule_type==='custom'" size="small">自定义</el-tag>
            <!-- 兜底：未识别类型原样展示，便于发现枚举未同步 -->
            <span v-else>{{ row.rule_type }}</span>
          </template>
        </el-table-column>
        <!-- 掩码样式列：替换后的展示形态，如 *** **** ****（用星号分段覆盖原值），是该规则的核心输出 -->
        <el-table-column label="掩码样式" prop="mask_style" min-width="140" show-overflow-tooltip />
        <!-- 正则列：用于匹配目标字段值，命中后才按掩码样式替换；写错会导致脱敏不生效 -->
        <el-table-column label="正则" prop="regular" min-width="180" show-overflow-tooltip />
        <!-- 状态列：只有启用规则才会实际执行脱敏 -->
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <!-- status=1 启用：绿色，脱敏生效 -->
            <el-tag v-if="row.status===1" size="small" type="success">启用</el-tag>
            <!-- 其余视为停用：灰色，规则保留但不下发 -->
            <el-tag v-else size="small" type="info">停用</el-tag>
          </template>
        </el-table-column>
        <!-- 创建时间列：后端格式化时间串 -->
        <el-table-column label="创建时间" prop="create_time" width="170" />
        <!-- 操作列：固定在右侧保证可见 -->
        <el-table-column label="操作" width="180" fixed="right" class-name="op-col">
          <template #default="{ row }">
            <!-- 编辑：当前行合并进表单后打开弹窗 -->
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <!-- 删除：二次确认后调用删除接口 -->
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <!-- 分页容器：统一右对齐与留白 -->
      <div class="pagination-wrap">
        <!-- 分页器：@change 覆盖页码与每页条数变更，统一重新拉取 -->
        <el-pagination background layout="total, sizes, prev, pager, next, jumper"
          :total="total" v-model:current-page="query.page" v-model:page-size="query.page_size"
          :page-sizes="[10, 20, 50, 100]" @change="fetchList" />
      </div>
    </el-card>

    <!-- 新增/编辑弹窗：宽度 560px 容纳正则文本域；禁止点遮罩关闭防误触丢失配置；destroy-on-close 清理上次校验状态 -->
    <el-dialog :title="dialogTitle" v-model="dialogVisible" width="560px" :close-on-click-modal="false" destroy-on-close>
      <!-- 规则表单：ref 用于提交校验，rules 约束必填项 -->
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <!-- 栅格布局：gutter=12 列间距，本页字段均为整行（span=24） -->
        <el-row :gutter="12">
          <!-- 规则名称占整行：名称较长需要完整输入宽度 -->
          <el-col :span="24">
            <el-form-item label="规则名称" prop="rule_name">
              <!-- maxlength=100 与后端字段长度一致 -->
              <el-input v-model="form.rule_name" placeholder="请输入规则名称" maxlength="100" />
            </el-form-item>
          </el-col>
          <!-- 规则类型占整行：决定默认脱敏语义 -->
          <el-col :span="24">
            <el-form-item label="规则类型" prop="rule_type">
              <!-- 宽度 100% 撑满整行 -->
              <el-select v-model="form.rule_type" style="width:100%">
                <!-- 类型枚举：phone=手机号；id_card=身份证；email=邮箱；name=姓名；bank_card=银行卡；custom=自定义（需自行填写掩码样式与正则） -->
                <el-option label="手机号" value="phone" />
                <el-option label="身份证" value="id_card" />
                <el-option label="邮箱" value="email" />
                <el-option label="姓名" value="name" />
                <el-option label="银行卡" value="bank_card" />
                <el-option label="自定义" value="custom" />
              </el-select>
            </el-form-item>
          </el-col>
          <!-- 掩码样式占整行：示例 *** **** **** 表示把原值按段替换为星号，配置错误会造成过度掩码 -->
          <el-col :span="24">
            <el-form-item label="掩码样式" prop="mask_style">
              <el-input v-model="form.mask_style" placeholder="如 *** **** ****" />
            </el-form-item>
          </el-col>
          <!-- 正则表达式占整行：2 行文本域便于阅读，正则决定哪些值会被掩码匹配 -->
          <el-col :span="24">
            <el-form-item label="正则表达式" prop="regular">
              <!-- 匹配失败则脱敏不生效，属于安全关键字段，提交前需人工核对 -->
              <el-input v-model="form.regular" type="textarea" :rows="2" placeholder="请输入匹配正则" />
            </el-form-item>
          </el-col>
          <!-- 状态占整行：1=启用、0=停用，带文字提示避免误触 -->
          <el-col :span="24">
            <el-form-item label="状态" prop="status">
              <!-- 显式绑定 0/1 数值，与后端字段类型一致 -->
              <el-switch v-model="form.status" :active-value="1" :inactive-value="0" active-text="启用" inactive-text="停用" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <!-- 弹窗底部：取消不保存；确定走校验与提交 -->
      <template #footer>
        <!-- 取消：直接关闭弹窗，丢弃本次修改 -->
        <el-button @click="dialogVisible=false">取消</el-button>
        <!-- 确定：提交期 loading，避免重复创建规则 -->
        <el-button type="primary" :loading="saving" @click="submitForm">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
// 组合式 API：ref 管理基本状态，reactive 管理查询条件与表单，onMounted 首次加载
import { ref, reactive, onMounted } from 'vue'
// 统一提示与确认框：保存成功提示、删除确认
import { ElMessage, ElMessageBox } from 'element-plus'
// 图标：Search 查询、Refresh 重置、Plus 新增、Delete 批量删除
import { Search, Refresh, Plus, Delete } from '@element-plus/icons-vue'
// 统一 axios 实例：自动带 token、统一错误提示
import request from '@/utils/request'

// 列表加载态：控制表格遮罩
const loading = ref(false)
// 当前页规则数据
const rows = ref([])
// 规则总数：分页与副标题使用
const total = ref(0)
// 勾选行：批量删除时取 id
const selection = ref([])
// 提交中：驱动确定按钮 loading，防重复提交
const saving = ref(false)
// 弹窗显隐：新增与编辑共用
const dialogVisible = ref(false)
// 弹窗标题：区分新增/编辑场景
const dialogTitle = ref('新增脱敏规则')
// 表单实例：提交前调用 validate()
const formRef = ref()

// 查询初值：作为重置基准；status 用 null 表示全部（0 是有效状态码，不能用 falsy 判断）
const query_orig = { page: 1, page_size: 10, rule_name: '', rule_type: '', status: null }
// 查询条件响应式副本：展开拷贝避免重置改写初值
const query = reactive({ ...query_orig })

// 表单初值：rule_type 默认 custom（最通用，避免新增时误用内置类型的固定脱敏语义）；status=1 默认启用
const form_orig = {
  id: null, rule_name: '', rule_type: 'custom', mask_style: '', regular: '', status: 1
}
// 表单响应式副本：新增/编辑复用同一对象
const form = reactive({ ...form_orig })

// 校验规则：名称必填（失焦校验）；类型必填（下拉用 change 触发）
// 掩码样式与正则未设为必填，但它们是脱敏生效的关键，留空会导致规则无效，需运维自行保证
const rules = {
  rule_name: [{ required: true, message: '请输入规则名称', trigger: 'blur' }],
  rule_type: [{ required: true, message: '请选择规则类型', trigger: 'change' }]
}

// 接口基址：脱敏规则统一前缀
const apiBase = '/dsm/rule'

// 拉取列表：带查询条件（含分页）请求后端，返回 { list, total }
async function fetchList() {
  // 请求前打开 loading
  loading.value = true
  try {
    // GET /dsm/rule/list：空串/null 条件由后端忽略
    const res = await request.get(apiBase + '/list', { params: query })
    // 兜底空数组，保证无数据时正常展示空表格
    rows.value = res.data.list || []
    // 兜底 0，保证分页器 total 为数字
    total.value = res.data.total || 0
  // 无论成败都关闭 loading，避免遮罩卡死
  } finally { loading.value = false }
}

// 查询：条件变化后回到第一页，避免页码超出新结果集
function handleSearch() { query.page = 1; fetchList() }
// 重置：还原查询初值（含分页）后重新查询
function handleReset() { Object.assign(query, query_orig); handleSearch() }
// 勾选变化：同步选中行，供批量删除禁用态与 id 收集
function onSelectionChange(r) { selection.value = r }

// 打开新增：先重置表单清除上次残留，再设置标题与显隐
function openCreate() { Object.assign(form, form_orig); dialogTitle.value = '新增脱敏规则'; dialogVisible.value = true }
// 打开编辑：先还原初值再合并当前行，避免上次编辑残留字段被带入
function openEdit(row) { Object.assign(form, form_orig, row); dialogTitle.value = '编辑脱敏规则'; dialogVisible.value = true }

// 提交：按 id 判断新增或更新，成功后关闭弹窗并刷新列表
async function submitForm() {
  // 先整体校验，未通过会抛异常中断提交
  await formRef.value.validate()
  // 进入提交态，禁用按钮防止重复提交
  saving.value = true
  try {
    // 有 id 走更新：剔除 id 避免同时出现在 URL 与请求体
    if (form.id) {
      const { id, ...data } = form
      await request.put(`${apiBase}/update/${id}`, data); ElMessage.success('更新成功')
    } else {
      // 无 id 走新增，主键由后端生成
      await request.post(apiBase + '/create', form); ElMessage.success('新增成功')
    }
    // 关闭弹窗并刷新，让表格与脱敏配置同步
    dialogVisible.value = false; fetchList()
  // 结束提交态，避免按钮一直 loading
  } finally { saving.value = false }
}

// 删除单条：二次确认后按 ids 提交（仅一条）
async function handleDelete(row) {
  // 删除后该字段可能恢复明文输出，属安全敏感操作，需二次确认
  await ElMessageBox.confirm('确定删除该脱敏规则？', '提示', { type: 'warning' })
  // DELETE 用 data 传请求体，与后端统一删除约定一致
  await request.delete(apiBase + '/delete', { data: { ids: [row.id] } })
  // 成功后刷新列表，同步总数
  ElMessage.success('删除成功'); fetchList()
}

// 批量删除：确认文案带选中数量，明确影响范围
async function handleBatchDelete() {
  // 取消会抛异常，后续请求不执行
  await ElMessageBox.confirm(`确定删除选中的 ${selection.value.length} 条？`, '提示', { type: 'warning' })
  // 汇总选中 id 一次性提交，减少请求次数
  await request.delete(apiBase + '/delete', { data: { ids: selection.value.map(r => r.id) } })
  // 提示并刷新，勾选随数据刷新失效
  ElMessage.success('批量删除成功'); fetchList()
}

// 首次进入加载第一页规则列表
onMounted(fetchList)
</script>
