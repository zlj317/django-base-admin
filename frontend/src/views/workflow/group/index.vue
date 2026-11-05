<!--
  文件级说明：用户分组管理页（workflow/group/index.vue）
  职责：维护「固定审批小组」及其成员；流程审批节点可直接选择分组作为审批人集合。
  依赖：@/utils/request 统一 HTTP 封装；Element Plus 表单/表格/弹窗/标签组件；v-perm 权限指令。
  使用方：由工作流管理菜单下的「用户分组」路由加载，属于后台管理页面。
-->
<template>
  <!-- 页面根容器：套用全局布局的内边距与背景 -->
  <div class="app-container">
    <!-- 页头：标题 + 分组总数，便于管理员了解数据规模 -->
    <div class="page-header">
      <div class="page-title-wrap">
        <h2>用户分组</h2>
        <!-- total 为后端返回的总条数，随查询实时刷新 -->
        <div class="sub">固定审批小组管理 · 共 {{ total }} 条记录</div>
      </div>
    </div>

    <!-- 搜索区：无阴影卡片承载筛选表单，保持与其它管理页一致 -->
    <el-card shadow="never" class="search-card">
      <!-- @submit.prevent 阻止表单默认提交，避免回车刷新页面 -->
      <el-form :model="query" inline @submit.prevent>
        <!-- 分组名称筛选：支持模糊查询，回车即搜索 -->
        <el-form-item label="分组名称">
          <el-input v-model="query.group_name" placeholder="请输入分组名称" clearable style="width: 180px" @keyup.enter="handleQuery" />
        </el-form-item>
        <!-- 分组编码筛选：编码是分组在流程配置中的稳定标识 -->
        <el-form-item label="分组编码">
          <el-input v-model="query.group_code" placeholder="请输入分组编码" clearable style="width: 180px" @keyup.enter="handleQuery" />
        </el-form-item>
        <el-form-item class="search-actions">
          <!-- 查询：回到第一页并按当前条件请求 -->
          <el-button type="primary" :icon="Search" @click="handleQuery">查询</el-button>
          <!-- 重置：清空筛选条件后重新请求 -->
          <el-button :icon="Refresh" @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 列表区卡片：头部放置新增/批量删除操作 -->
    <el-card shadow="never" class="table-card">
      <!-- 卡片头部插槽 -->
      <template #header>
        <div class="card-header">
          <div class="card-actions">
            <!-- 新增分组：受 wf:group:create 权限控制 -->
            <el-button v-perm="'wf:group:create'" type="primary" :icon="Plus" @click="openCreate">新增</el-button>
            <!-- 批量删除：未勾选时禁用，避免空提交 -->
            <el-button v-perm="'wf:group:delete'" type="danger" plain :icon="Delete" :disabled="!selectedIds.length" @click="handleBatchDelete">批量删除</el-button>
          </div>
        </div>
      </template>
      <!-- 表格：loading 遮罩 + 斑马纹；勾选变化时同步 selectedIds -->
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据" @selection-change="onSelectionChange">
        <!-- 自动序号列，便于定位行 -->
        <el-table-column type="index" label="序号" width="70" align="center" />
        <!-- 勾选列，供批量删除 -->
        <el-table-column type="selection" width="50" align="center" />
        <!-- 分组名称：主标识列 -->
        <el-table-column label="分组名称" prop="group_name" min-width="150" show-overflow-tooltip />
        <!-- 分组编码：唯一标识，供流程配置引用 -->
        <el-table-column label="分组编码" prop="group_code" min-width="140" show-overflow-tooltip />
        <!-- 成员数：后端已聚合统计，前端直接展示 -->
        <el-table-column label="成员数" prop="user_count" width="90" align="center" />
        <!-- 成员列：用标签逐个展示姓名，超出宽度自动换行 -->
        <el-table-column label="成员" min-width="200">
          <template #default="scope">
            <!-- v-for 遍历 user_names；key 用姓名（同一分组内姓名理论上不重复） -->
            <el-tag v-for="name in scope.row.user_names" :key="name" size="small" class="member-tag">{{ name }}</el-tag>
            <!-- 可选链判断为空时给出兜底文案；v-if 保证无成员时不渲染标签 -->
            <span v-if="!scope.row.user_names?.length" class="text-muted">暂无成员</span>
          </template>
        </el-table-column>
        <!-- 状态列：本页约定 status=0 为启用 -->
        <el-table-column label="状态" width="90" align="center">
          <template #default="scope">
            <!-- status=0 显示启用（绿色），否则显示停用（灰色） -->
            <el-tag :type="scope.row.status === 0 ? 'success' : 'info'">{{ scope.row.status === 0 ? '启用' : '停用' }}</el-tag>
          </template>
        </el-table-column>
        <!-- 创建时间：后端返回的格式化字符串 -->
        <el-table-column label="创建时间" prop="create_time" width="170" />
        <!-- 操作列：三个操作按钮，固定右侧保证可见 -->
        <el-table-column label="操作" width="230" align="center" fixed="right">
          <template #default="scope">
            <!-- 成员：打开成员配置弹窗，复用编辑权限（维护成员属于更新操作） -->
            <el-button v-perm="'wf:group:update'" link type="primary" :icon="UserFilled" @click="openMembers(scope.row)">成员</el-button>
            <!-- 编辑：修改分组基本信息 -->
            <el-button v-perm="'wf:group:update'" link type="primary" :icon="Edit" @click="openEdit(scope.row)">编辑</el-button>
            <!-- 删除：单条删除，前端二次确认 -->
            <el-button v-perm="'wf:group:delete'" link type="danger" :icon="Delete" @click="handleDelete(scope.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <!-- 分页：页码与每页条数双向绑定 query，变化后重新请求 -->
      <div class="pagination-wrap">
        <el-pagination background layout="total, sizes, prev, pager, next, jumper"
          :total="total" v-model:current-page="query.page" v-model:page-size="query.page_size"
          :page-sizes="[10, 20, 50, 100]" @change="getList" />
      </div>
    </el-card>

    <!-- 新增/编辑分组弹窗：标题随 form.id 切换，点遮罩不关闭以防误丢数据 -->
    <el-dialog :title="form.id ? '编辑用户分组' : '新增用户分组'" v-model="dialogVisible" width="520px" :close-on-click-modal="false" destroy-on-close>
      <!-- 表单：绑定 form 与校验规则 -->
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <!-- 分组名称：必填 -->
        <el-form-item label="分组名称" prop="group_name">
          <el-input v-model="form.group_name" placeholder="如：财务审批组" />
        </el-form-item>
        <!-- 分组编码：必填且编辑时禁用，避免破坏已有流程对该编码的引用 -->
        <el-form-item label="分组编码" prop="group_code">
          <el-input v-model="form.group_code" placeholder="唯一编码，如 finance_group" :disabled="!!form.id" />
        </el-form-item>
        <!-- 状态：本页约定 0 启用 / 1 停用，与列表着色逻辑对应 -->
        <el-form-item label="状态" prop="status">
          <el-radio-group v-model="form.status">
            <el-radio :label="0">启用</el-radio>
            <el-radio :label="1">停用</el-radio>
          </el-radio-group>
        </el-form-item>
        <!-- 备注：选填，用于说明分组职责 -->
        <el-form-item label="备注" prop="remark">
          <el-input v-model="form.remark" type="textarea" :rows="3" placeholder="请输入备注" />
        </el-form-item>
      </el-form>
      <!-- 底部按钮：取消关闭弹窗；确定提交并展示 loading -->
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitForm">确定</el-button>
      </template>
    </el-dialog>

    <!-- 成员配置弹窗：标题拼接当前分组名称，便于确认正在编辑哪个分组 -->
    <el-dialog v-model="memberVisible" :title="`分组成员 · ${memberGroup.group_name}`" width="560px" :close-on-click-modal="false">
      <!-- 多选用户下拉：filterable 支持按用户名搜索；选中结果写入 selectedUsers（存用户 id） -->
      <el-select v-model="selectedUsers" multiple filterable placeholder="请选择分组用户" style="width: 100%">
        <!-- 下拉项标签优先展示「昵称（用户名）」，昵称为空时退化为用户名 -->
        <el-option v-for="user in userOptions" :key="user.id" :label="user.nickname ? `${user.nickname}（${user.username}）` : user.username" :value="user.id" />
      </el-select>
      <!-- 底部按钮：保存成员走 saveMembers，并展示独立 loading 防止重复点击 -->
      <template #footer>
        <el-button @click="memberVisible = false">取消</el-button>
        <el-button type="primary" :loading="memberSaving" @click="saveMembers">保存成员</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
// 组合式 API：ref 管理基础状态，reactive 管理查询/表单对象，onMounted 首屏加载
import { ref, reactive, onMounted } from 'vue'
// ElMessage 操作结果提示；ElMessageBox 删除确认框
import { ElMessage, ElMessageBox } from 'element-plus'
// 搜索、刷新、新增、删除、编辑、成员图标
import { Search, Refresh, Plus, Delete, Edit, UserFilled } from '@element-plus/icons-vue'
// 统一请求实例：自动带 token 并统一处理响应与错误
import request from '@/utils/request'

// 列表加载中标记，控制表格遮罩
const loading = ref(false)
// 表单保存中标记，控制弹窗确定按钮 loading
const saving = ref(false)
// 当前页分组列表
const rows = ref([])
// 分组总数，供分页与页头统计
const total = ref(0)
// 表格勾选行 id，供批量删除
const selectedIds = ref([])
// 新增/编辑弹窗显隐
const dialogVisible = ref(false)
// 表单实例，提交前调用 validate()
const formRef = ref()
// 查询条件：page/page_size 绑定分页；group_name/group_code 为筛选关键字
const query = reactive({ page: 1, page_size: 10, group_name: '', group_code: '' })
// 表单数据：id=0 表示新增；status 默认 0（本页约定 0 为启用）
const form = reactive({ id: 0, group_name: '', group_code: '', status: 0, remark: '' })
// 表单校验规则：名称与编码必填
const rules = {
  group_name: [{ required: true, message: '请输入分组名称', trigger: 'blur' }],
  group_code: [{ required: true, message: '请输入分组编码', trigger: 'blur' }]
}

// 成员弹窗显隐
const memberVisible = ref(false)
// 成员保存中标记，独立于基础表单 saving
const memberSaving = ref(false)
// 当前正在配置成员的分组（只保存 id 与名称，用于标题与请求路径）
const memberGroup = reactive({ id: 0, group_name: '' })
// 已选用户 id 数组，多选下拉直接绑定
const selectedUsers = ref([])
// 用户下拉候选列表，首次打开成员弹窗时懒加载
const userOptions = ref([])

// 拉取分组列表：query 同时携带分页与筛选条件
async function getList() {
  // 打开加载遮罩，提示用户数据正在刷新
  loading.value = true
  try {
    // GET /api/wf/group/list，返回 { list, total }
    const res = await request.get('/wf/group/list', { params: query })
    rows.value = res.data.list
    total.value = res.data.total
  } finally {
    // 始终关闭遮罩，避免请求失败后界面卡在加载态
    loading.value = false
  }
}
// 查询：重置到第一页，防止筛选后当前页超出数据范围
function handleQuery() {
  query.page = 1
  getList()
}
// 重置：清空筛选条件并回到第一页
function resetQuery() {
  Object.assign(query, { page: 1, group_name: '', group_code: '' })
  getList()
}
// 勾选变化：把行对象映射为 id 数组
function onSelectionChange(rowsSelected) {
  selectedIds.value = rowsSelected.map(row => row.id)
}
// 新增：清空表单并置 id=0
function openCreate() {
  Object.assign(form, { id: 0, group_name: '', group_code: '', status: 0, remark: '' })
  dialogVisible.value = true
}
// 编辑：用当前行回填表单，remark 兜底为空串
function openEdit(row) {
  Object.assign(form, { id: row.id, group_name: row.group_name, group_code: row.group_code, status: row.status, remark: row.remark || '' })
  dialogVisible.value = true
}
// 保存分组：校验通过后按 id 判断新增或更新
async function submitForm() {
  // 校验失败会 reject，直接中断提交
  await formRef.value.validate()
  saving.value = true
  try {
    if (form.id) {
      // 编辑：PUT /wf/group/update/{id}
      await request.put(`/wf/group/update/${form.id}`, form)
      ElMessage.success('修改成功')
    } else {
      // 新增：POST /wf/group/create
      await request.post('/wf/group/create', form)
      ElMessage.success('新增成功')
    }
    // 成功后关闭弹窗并刷新列表
    dialogVisible.value = false
    getList()
  } finally {
    saving.value = false
  }
}
// 单条删除：先确认再请求，ids 以数组形式提交以复用批量接口
async function handleDelete(row) {
  // 取消确认会 reject，函数中断，不发出请求
  await ElMessageBox.confirm(`确认删除分组「${row.group_name}」吗？`, '提示', { type: 'warning' })
  await request.delete('/wf/group/delete', { data: { ids: [row.id] } })
  ElMessage.success('删除成功')
  getList()
}
// 批量删除：把勾选的 id 数组一次性提交
async function handleBatchDelete() {
  await ElMessageBox.confirm(`确认删除选中的 ${selectedIds.value.length} 个分组吗？`, '提示', { type: 'warning' })
  await request.delete('/wf/group/delete', { data: { ids: selectedIds.value } })
  ElMessage.success('删除成功')
  getList()
}

// 加载用户下拉候选：仅在首次打开成员弹窗时调用，避免首屏多余请求
async function loadUserOptions() {
  const res = await request.get('/wf/option/users')
  // 后端可能返回 null，这里兜底为空数组，防止 v-for 报错
  userOptions.value = res.data || []
}
// 打开成员弹窗：先确保用户选项已加载，再拉取该分组已选成员
async function openMembers(row) {
  // 候选用户未加载时才请求，后续打开直接复用缓存
  if (!userOptions.value.length) await loadUserOptions()
  // 记录当前分组，供标题展示与保存时拼接口路径
  memberGroup.id = row.id
  memberGroup.group_name = row.group_name
  // 查询该分组已有成员 id 列表
  const res = await request.get(`/wf/group/users/${row.id}`)
  // 后端返回 user_ids，缺失时兜底空数组
  selectedUsers.value = res.data.user_ids || []
  memberVisible.value = true
}
// 保存成员：把选中用户 id 数组写回分组
async function saveMembers() {
  memberSaving.value = true
  try {
    // PUT /wf/group/set_users/{id}，后端按该数组全量覆盖成员关系
    await request.put(`/wf/group/set_users/${memberGroup.id}`, { user_ids: selectedUsers.value })
    ElMessage.success('成员保存成功')
    memberVisible.value = false
    // 刷新列表以更新成员数与成员标签
    getList()
  } finally {
    memberSaving.value = false
  }
}

// 组件挂载后立即加载首屏分组数据
onMounted(getList)
</script>

<style scoped>
/* 成员标签：右侧与上下留白，多个标签排列时不粘连 */
.member-tag {
  margin: 2px 6px 2px 0;
}
/* 空成员提示：使用 Element Plus 次要文字色变量，自动适配亮/暗色主题；字号略小弱化存在感 */
.text-muted {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}
</style>
