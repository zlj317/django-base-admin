<!--
  数据权限配置页（/dp/permission）：
  职责：维护数据权限规则（数据范围类型、范围值、SQL 过滤条件、排序、启停），供角色通过 role_perm 关联后生效。
  依赖：@/utils/request 统一请求、Element Plus 表格/表单/弹窗组件与图标；样式来自全局 styles/index.css（本文件无 style 块）。
  使用方：后台"数据权限"菜单；角色绑定见 dp/role_perm，最终由后端按 SQL 条件过滤查询结果集。
  安全提示：数据范围类型与 SQL 条件直接决定用户能看到哪些数据，配置错误会造成越权或看不到数据。
-->
<template>
  <!-- 页面根容器：全局 .app-container 提供内边距与进场动画 -->
  <div class="app-container">
    <!-- 页面头部：标题 + 当前条件下规则总数 -->
    <div class="page-header">
      <!-- 标题容器：主副标题纵向排布 -->
      <div class="page-title-wrap">
        <!-- 主标题 -->
        <h2>数据权限配置</h2>
        <!-- 副标题：total 由列表接口返回，随筛选变化 -->
        <div class="sub">数据权限规则管理 · 共 {{ total }} 条</div>
      </div>
    </div>

    <!-- 搜索区卡片：扁平无阴影，复用全局搜索区留白 -->
    <el-card shadow="never" class="search-card">
      <!-- 查询表单：inline 横向排列；@submit.prevent 阻止原生提交导致的页面刷新 -->
      <el-form :model="query" inline @submit.prevent>
        <!-- 权限名称筛选：模糊匹配，回车即查询 -->
        <el-form-item label="权限名称">
          <el-input v-model="query.permission_name" placeholder="请输入权限名称" clearable style="width: 170px" @keyup.enter="handleSearch" />
        </el-form-item>
        <!-- 权限类型（数据范围）筛选：空值表示不过滤，展示全部规则 -->
        <el-form-item label="权限类型">
          <el-select v-model="query.permission_type" placeholder="全部" clearable style="width: 130px">
            <!-- 数据范围枚举：all=全部数据（不做过滤，通常仅超级管理员）；dept=仅本部门数据；dept_and_sub=本部门及全部下级部门；self=仅本人创建的数据；custom=自定义，靠范围值+SQL 条件表达 -->
            <el-option label="全部数据" value="all" />
            <el-option label="本部门" value="dept" />
            <el-option label="本部门及以下" value="dept_and_sub" />
            <el-option label="仅本人" value="self" />
            <el-option label="自定义" value="custom" />
          </el-select>
        </el-form-item>
        <!-- 启用状态筛选：1=启用（参与权限判定）；0=停用（规则保留但不生效） -->
        <el-form-item label="状态">
          <el-select v-model="query.status" placeholder="全部" clearable style="width: 110px">
            <!-- 状态枚举：1 启用、0 停用；用数字对齐后端 status 字段 -->
            <el-option label="启用" :value="1" />
            <el-option label="停用" :value="0" />
          </el-select>
        </el-form-item>
        <!-- 操作按钮：查询回第一页，重置还原全部条件 -->
        <el-form-item>
          <!-- 按当前条件查询 -->
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <!-- 清空筛选并重新查询 -->
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
      <!-- 数据表格：请求期遮罩 + 斑马纹，勾选行写入 selection 供批量删除使用 -->
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据" @selection-change="onSelectionChange">
        <!-- 序号列：前端行号 -->
        <el-table-column type="index" label="序号" width="70" align="center" />
        <!-- 多选列：批量删除的数据来源 -->
        <el-table-column type="selection" width="50" />
        <!-- 权限名称列：自适应宽度，超长文本用 tooltip 展示 -->
        <el-table-column label="权限名称" prop="permission_name" min-width="180" show-overflow-tooltip />
        <!-- 权限类型列：用不同颜色标签直观区分数据范围大小（范围越大越需谨慎） -->
        <el-table-column label="权限类型" width="120">
          <template #default="{ row }">
            <!-- all=全部数据：默认色标签，属于范围最大的规则，通常只给超管 -->
            <el-tag v-if="row.permission_type==='all'" size="small">全部数据</el-tag>
            <!-- dept=仅本部门：绿色表示受限的正常范围 -->
            <el-tag v-else-if="row.permission_type==='dept'" size="small" type="success">本部门</el-tag>
            <!-- dept_and_sub=本部门及以下：橙色提示范围已向下扩展 -->
            <el-tag v-else-if="row.permission_type==='dept_and_sub'" size="small" type="warning">部门及以下</el-tag>
            <!-- self=仅本人：灰色表示最小范围 -->
            <el-tag v-else-if="row.permission_type==='self'" size="small" type="info">仅本人</el-tag>
            <!-- custom=自定义：红色提示需人工核对范围值与 SQL 条件，避免越权 -->
            <el-tag v-else-if="row.permission_type==='custom'" size="small" type="danger">自定义</el-tag>
            <!-- 兜底：未识别的类型原样展示，便于发现后端新增类型未同步 -->
            <span v-else>{{ row.permission_type }}</span>
          </template>
        </el-table-column>
        <!-- 范围值列：custom 等类型下保存的部门/用户 id 列表等，与 SQL 条件配合限定数据范围 -->
        <el-table-column label="范围值" prop="scope_value" min-width="140" show-overflow-tooltip />
        <!-- SQL 条件列：最终拼接进查询语句的过滤表达式，是数据权限落地的核心字段 -->
        <el-table-column label="SQL条件" prop="sql_condition" min-width="180" show-overflow-tooltip />
        <!-- 排序列：规则排序值，多条规则命中时的先后次序由后端排序逻辑决定 -->
        <el-table-column label="排序" prop="sort" width="70" />
        <!-- 状态列：仅启用状态的规则才会参与数据过滤 -->
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <!-- status=1 启用：绿色 -->
            <el-tag v-if="row.status===1" size="small" type="success">启用</el-tag>
            <!-- 其余一律视为停用：灰色，规则保留但不下发 -->
            <el-tag v-else size="small" type="info">停用</el-tag>
          </template>
        </el-table-column>
        <!-- 创建时间列：后端格式化时间串 -->
        <el-table-column label="创建时间" prop="create_time" width="170" />
        <!-- 操作列：固定在右侧保证可见 -->
        <el-table-column label="操作" width="180" fixed="right" class-name="op-col">
          <template #default="{ row }">
            <!-- 编辑：当前行数据合并进表单后打开弹窗 -->
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <!-- 删除：二次确认后调用删除接口 -->
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <!-- 分页容器：统一右对齐与留白 -->
      <div class="pagination-wrap">
        <!-- 分页器：@change 同时覆盖页码与每页条数变更，统一重新拉取 -->
        <el-pagination background layout="total, sizes, prev, pager, next, jumper"
          :total="total" v-model:current-page="query.page" v-model:page-size="query.page_size"
          :page-sizes="[10, 20, 50, 100]" @change="fetchList" />
      </div>
    </el-card>

    <!-- 新增/编辑弹窗：宽度 640px 容纳 SQL 条件；禁止点遮罩关闭防止误触丢失内容；destroy-on-close 清空上次校验状态 -->
    <el-dialog :title="dialogTitle" v-model="dialogVisible" width="640px" :close-on-click-modal="false" destroy-on-close>
      <!-- 权限表单：ref 用于提交校验，rules 约束必填项 -->
      <el-form ref="formRef" :model="form" :rules="rules" label-width="110px">
        <!-- 栅格布局：gutter=12 列间距；半行字段 span=12，整行字段 span=24 -->
        <el-row :gutter="12">
          <!-- 权限名称占半行：名称不长，与类型并排更紧凑 -->
          <el-col :span="12">
            <el-form-item label="权限名称" prop="permission_name">
              <!-- maxlength=100 与后端字段长度一致，前端先限制非法长输入 -->
              <el-input v-model="form.permission_name" placeholder="请输入权限名称" maxlength="100" />
            </el-form-item>
          </el-col>
          <!-- 权限类型占半行：决定数据范围的语义 -->
          <el-col :span="12">
            <el-form-item label="权限类型" prop="permission_type">
              <!-- 宽度 100% 撑满栅格列，与相邻输入框视觉对齐 -->
              <el-select v-model="form.permission_type" style="width:100%">
                <!-- 数据范围枚举：all=全部数据；dept=本部门；dept_and_sub=本部门及下级；self=仅本人；custom=自定义（需配合范围值与 SQL 条件） -->
                <el-option label="全部数据" value="all" />
                <el-option label="本部门" value="dept" />
                <el-option label="本部门及以下" value="dept_and_sub" />
                <el-option label="仅本人" value="self" />
                <el-option label="自定义" value="custom" />
              </el-select>
            </el-form-item>
          </el-col>
          <!-- 范围值占整行：如自定义范围下的部门 id 列表，字符串较长需要整行宽度 -->
          <el-col :span="24">
            <el-form-item label="范围值" prop="scope_value">
              <!-- 提示格式便于运维填写：如 dept_id 列表（后端按范围值做数据过滤） -->
              <el-input v-model="form.scope_value" placeholder="如 dept_id 列表" />
            </el-form-item>
          </el-col>
          <!-- SQL 条件占整行：多行文本，便于阅读与核对过滤逻辑 -->
          <el-col :span="24">
            <el-form-item label="SQL条件" prop="sql_condition">
              <!-- 3 行文本域：示例 dept_id IN (...) AND create_by = #{userId}，其中 #{userId} 由后端替换为当前登录用户 -->
              <el-input v-model="form.sql_condition" type="textarea" :rows="3" placeholder="如 dept_id IN (...) AND create_by = #{userId}" />
            </el-form-item>
          </el-col>
          <!-- 排序占半行：数值型，最小值 0，避免负值导致排序语义异常 -->
          <el-col :span="12">
            <el-form-item label="排序" prop="sort">
              <!-- :min=0 仅做前端限制，最终以后端校验为准 -->
              <el-input-number v-model="form.sort" :min="0" />
            </el-form-item>
          </el-col>
          <!-- 状态占半行：1=启用、0=停用，带文字提示 -->
          <el-col :span="12">
            <el-form-item label="状态" prop="status">
              <!-- 显式绑定 0/1 数值，与后端字段类型保持一致 -->
              <el-switch v-model="form.status" :active-value="1" :inactive-value="0" active-text="启用" inactive-text="停用" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <!-- 弹窗底部：取消不保存；确定走校验与提交 -->
      <template #footer>
        <!-- 取消：直接关闭弹窗，本次修改不提交 -->
        <el-button @click="dialogVisible=false">取消</el-button>
        <!-- 确定：提交期间 loading，避免重复创建同名规则 -->
        <el-button type="primary" :loading="saving" @click="submitForm">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
// 组合式 API：ref 管理基本状态，reactive 管理查询条件与表单，onMounted 首次加载
import { ref, reactive, onMounted } from 'vue'
// 统一提示与确认框：成功提示、删除确认
import { ElMessage, ElMessageBox } from 'element-plus'
// 图标：Search 查询、Refresh 重置、Plus 新增、Delete 批量删除
import { Search, Refresh, Plus, Delete } from '@element-plus/icons-vue'
// 统一 axios 实例：自动带 token、统一错误提示（见 utils/request.js）
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
const dialogTitle = ref('新增数据权限')
// 表单实例：提交时调用 validate()
const formRef = ref()

// 查询初值：作为重置基准；status 用 null 表示全部（0 是有效状态码，不能用 falsy 判断）
const query_orig = { page: 1, page_size: 10, permission_name: '', permission_type: '', status: null }
// 查询条件响应式副本：展开拷贝防止重置改写初值
const query = reactive({ ...query_orig })

// 表单初值：permission_type 默认 all（新增时从最宽松类型开始，由管理员按需收紧）；sort=0；status=1 默认启用
const form_orig = {
  id: null, permission_name: '', permission_type: 'all', scope_value: '', sql_condition: '', sort: 0, status: 1
}
// 表单响应式副本：新增/编辑复用同一对象
const form = reactive({ ...form_orig })

// 校验规则：名称必填（失焦校验）；类型必填（选择即校验，因为下拉不会失焦触发）
const rules = {
  permission_name: [{ required: true, message: '请输入权限名称', trigger: 'blur' }],
  permission_type: [{ required: true, message: '请选择权限类型', trigger: 'change' }]
}

// 接口基址：数据权限规则统一前缀
const apiBase = '/dp/permission'

// 拉取列表：带查询条件（含分页）请求后端，返回 { list, total }
async function fetchList() {
  // 请求前打开 loading
  loading.value = true
  try {
    // GET /dp/permission/list：空串/null 条件由后端忽略
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
// 重置：还原查询初值（含分页）再查询
function handleReset() { Object.assign(query, query_orig); handleSearch() }
// 勾选变化：同步选中行，供批量删除禁用态与 id 收集
function onSelectionChange(r) { selection.value = r }

// 打开新增：先重置表单清除上次残留，再设置标题与显隐
function openCreate() { Object.assign(form, form_orig); dialogTitle.value = '新增数据权限'; dialogVisible.value = true }
// 打开编辑：先还原初值再合并当前行，防止上一次编辑残留字段被带入
function openEdit(row) { Object.assign(form, form_orig, row); dialogTitle.value = '编辑数据权限'; dialogVisible.value = true }

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
    // 关闭弹窗并刷新，让表格同步最新配置
    dialogVisible.value = false; fetchList()
  // 结束提交态，防止按钮一直 loading
  } finally { saving.value = false }
}

// 删除单条：二次确认后按 ids 提交（仅一条）
async function handleDelete(row) {
  // 删除会影响相关角色的数据可见范围，需二次确认
  await ElMessageBox.confirm('确定删除该数据权限？', '提示', { type: 'warning' })
  // DELETE 用 data 传请求体，与后端统一删除约定一致
  await request.delete(apiBase + '/delete', { data: { ids: [row.id] } })
  // 成功后刷新列表，同步总数
  ElMessage.success('删除成功'); fetchList()
}

// 批量删除：确认框带数量，明确影响范围
async function handleBatchDelete() {
  // 取消会抛异常，后续请求不执行
  await ElMessageBox.confirm(`确定删除选中的 ${selection.value.length} 条？`, '提示', { type: 'warning' })
  // 汇总选中 id 一次性提交
  await request.delete(apiBase + '/delete', { data: { ids: selection.value.map(r => r.id) } })
  // 提示并刷新，勾选随数据刷新失效
  ElMessage.success('批量删除成功'); fetchList()
}

// 首次进入加载第一页规则列表
onMounted(fetchList)
</script>
