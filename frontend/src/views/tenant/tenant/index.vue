<!-- 租户管理页（租户管理 / 租户管理）
     职责：维护多租户主体（名称、唯一编码、到期时间、启停状态与套餐额度：最大用户数、最大存储空间），
           是平台侧开通/停用客户租户的入口。
     接口：GET /tenant/tenant/list（分页）、POST /tenant/tenant/create、
           PUT /tenant/tenant/update/{id}、DELETE /tenant/tenant/delete（ids 放请求体）。
     依赖：@/utils/request（统一 baseURL、token 与错误提示）、Element Plus 表单/表格/弹窗、日期选择与数字输入组件。
     被谁使用：由后端菜单动态挂载进入；租户维度会在登录后约束可见数据范围与资源额度。 -->
<template>
  <!-- 页面根容器：复用全局 .app-container 的留白与进场动画 -->
  <div class="app-container">
    <!-- 页头：标题 + 租户总数 -->
    <div class="page-header">
      <!-- 标题组 -->
      <div class="page-title-wrap">
        <!-- 主标题：与菜单名一致 -->
        <h2>租户管理</h2>
        <!-- 副标题：total 为服务端返回的总记录数 -->
        <div class="sub">多租户管理 · 共 {{ total }} 条</div>
      </div>
    </div>
    <!-- 查询卡片：shadow="never" 弱化辅助区域 -->
    <el-card shadow="never" class="search-card">
      <!-- inline 单行排列；@submit.prevent 阻止回车触发表单原生提交刷新整页 -->
      <el-form :model="query" inline @submit.prevent>
        <!-- 租户名称筛选：按展示名称模糊查询 -->
        <el-form-item label="租户名称">
          <!-- clearable 一键清空；170px 与编码输入框等宽；回车直接查询 -->
          <el-input v-model="query.tenant_name" placeholder="请输入租户名称" clearable style="width: 170px" @keyup.enter="handleSearch" />
        </el-form-item>
        <!-- 租户编码筛选：编码是租户的唯一标识，常用于精确定位 -->
        <el-form-item label="租户编码">
          <!-- 宽度与名称输入框一致，保持查询栏栅格整齐 -->
          <el-input v-model="query.tenant_code" placeholder="请输入租户编码" clearable style="width: 170px" @keyup.enter="handleSearch" />
        </el-form-item>
        <!-- 状态筛选：1/0 数字与后端 tinyint 一致 -->
        <el-form-item label="状态">
          <!-- 清空后 status 回到 null，即不按状态过滤 -->
          <el-select v-model="query.status" placeholder="全部" clearable style="width: 110px">
            <!-- 1 = 启用：租户可正常登录使用 -->
            <el-option label="启用" :value="1" />
            <!-- 0 = 停用：租户被冻结，数据保留但不可用 -->
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

    <!-- 表格卡片：新建入口放在表格上方工具栏 -->
    <el-card shadow="never" class="table-card">
      <!-- 工具栏插槽：仅一个新建按钮（本页未接批量删除） -->
      <template #header>
        <div class="card-header">
          <div class="card-actions">
            <!-- 新建租户：该按钮未加 v-perm，前端不做权限隐藏，权限由后端接口校验 -->
            <el-button type="primary" :icon="Plus" @click="openCreate">新建租户</el-button>
          </div>
        </div>
      </template>
      <!-- 表格：v-loading 加载态；stripe 隔行变色；空态中文；本页无批量操作故无选择列 -->
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据">
        <!-- 序号列：阅读定位 -->
        <el-table-column type="index" label="序号" width="70" align="center" />
        <!-- 租户名称：展示名 -->
        <el-table-column label="租户名称" prop="tenant_name" min-width="160" show-overflow-tooltip />
        <!-- 租户编码：全局唯一标识，创建后不可修改（见弹窗 :disabled） -->
        <el-table-column label="租户编码" prop="tenant_code" min-width="140" show-overflow-tooltip />
        <!-- 状态列：启用用绿色标签、停用用灰色标签，只读展示（本页不提供行内开关） -->
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <!-- effect="light" 使用浅色底，与页面整体低饱和风格一致 -->
            <el-tag :type="row.status === 1 ? 'success' : 'info'" effect="light">
              {{ row.status === 1 ? '启用' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <!-- 到期时间：租户有效期截止时间，为空通常表示不限时（由后端解释） -->
        <el-table-column label="到期时间" prop="expire_time" width="170" />
        <!-- 最大用户数：套餐额度之一，限制该租户可创建/启用的用户数量 -->
        <el-table-column label="最大用户数" prop="max_user_count" width="110" />
        <!-- 最大存储(MB)：套餐额度之一，限制该租户的文件存储总量，单位 MB -->
        <el-table-column label="最大存储(MB)" prop="max_storage_mb" width="130" />
        <!-- 备注：开通信息等补充说明 -->
        <el-table-column label="备注" prop="remark" min-width="140" show-overflow-tooltip />
        <!-- 操作列：fixed="right" 横向滚动时保持可见 -->
        <el-table-column label="操作" width="180" fixed="right" class-name="op-col">
          <template #default="{ row }">
            <!-- 编辑：带整行数据进入表单；按钮未加 v-perm，权限由后端校验 -->
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <!-- 删除：二次确认后按 ids 数组提交；按钮未加 v-perm，权限由后端校验 -->
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
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

    <!-- 新建/编辑弹窗：标题随模式切换；禁止点遮罩关闭防误操作；destroy-on-close 每次打开重建表单 -->
    <el-dialog :title="dialogTitle" v-model="dialogVisible" width="680px" :close-on-click-modal="false" destroy-on-close>
      <!-- ref 供 validate 调用；:model/:rules 绑定数据与校验规则；label-width 统一标签宽度 -->
      <el-form ref="formRef" :model="form" :rules="rules" label-width="110px">
        <!-- 栅格布局：gutter=12 控制两列间距，小屏仍保持两列（字段不多，不额外做响应式断点） -->
        <el-row :gutter="12">
          <!-- 左列：租户名称 -->
          <el-col :span="12">
            <el-form-item label="租户名称" prop="tenant_name">
              <!-- maxlength 100 与后端字段长度对齐，避免提交超长导致后端校验失败 -->
              <el-input v-model="form.tenant_name" placeholder="请输入租户名称" maxlength="100" />
            </el-form-item>
          </el-col>
          <!-- 右列：租户编码 -->
          <el-col :span="12">
            <el-form-item label="租户编码" prop="tenant_code">
              <!-- :disabled="!!form.id" 编辑态禁止改编码：编码用于数据隔离/路由识别，需保持稳定 -->
              <el-input v-model="form.tenant_code" placeholder="唯一标识" maxlength="64" :disabled="!!form.id" />
            </el-form-item>
          </el-col>
          <!-- 左列：到期时间 -->
          <el-col :span="12">
            <el-form-item label="到期时间" prop="expire_time">
              <!-- value-format 固定输出 YYYY-MM-DD HH:mm:ss，保证与后端约定的时间字符串格式一致 -->
              <el-date-picker v-model="form.expire_time" type="datetime" placeholder="选择到期时间" value-format="YYYY-MM-DD HH:mm:ss" style="width:100%" />
            </el-form-item>
          </el-col>
          <!-- 右列：启停状态 -->
          <el-col :span="12">
            <el-form-item label="状态" prop="status">
              <!-- 1 启用 / 0 停用；active-text/inactive-text 把文字显示在开关两侧 -->
              <el-switch v-model="form.status" :active-value="1" :inactive-value="0" active-text="启用" inactive-text="停用" />
            </el-form-item>
          </el-col>
          <!-- 左列：套餐额度——最大用户数 -->
          <el-col :span="12">
            <el-form-item label="最大用户数" prop="max_user_count">
              <!-- 数字输入：最小 1，最大 99999，避免出现 0 或离谱上限 -->
              <el-input-number v-model="form.max_user_count" :min="1" :max="99999" style="width:100%" />
            </el-form-item>
          </el-col>
          <!-- 右列：套餐额度——最大存储空间 -->
          <el-col :span="12">
            <el-form-item label="最大存储(MB)" prop="max_storage_mb">
              <!-- 单位 MB；上限 1048576（1TB），与后端额度校验范围对应 -->
              <el-input-number v-model="form.max_storage_mb" :min="1" :max="1048576" style="width:100%" />
            </el-form-item>
          </el-col>
          <!-- 整行：备注 -->
          <el-col :span="24">
            <el-form-item label="备注" prop="remark">
              <!-- 2 行文本域，用于记录开通原因、联系人等 -->
              <el-input v-model="form.remark" type="textarea" :rows="2" placeholder="请输入备注" />
            </el-form-item>
          </el-col>
        </el-row>
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
import { Search, Refresh, Plus } from '@element-plus/icons-vue'
// 统一请求封装：内置 baseURL=/api、token 注入与统一错误提示
import request from '@/utils/request'

// 表格加载态
const loading = ref(false)
// 当前页的租户列表
const rows = ref([])
// 服务端返回的总记录数
const total = ref(0)
// 提交中标记，控制确定按钮 loading，防止重复提交
const saving = ref(false)
// 新建/编辑弹窗显隐
const dialogVisible = ref(false)
// 弹窗标题，打开时按"新建/编辑"改写
const dialogTitle = ref('新建租户')
// el-form 实例，提交前调用 validate 做必填校验
const formRef = ref()

// 查询条件默认值；空字符串/null 表示"全部"，页码从 1 开始
const query_orig = { page: 1, page_size: 10, tenant_name: '', tenant_code: '', status: null }
// 实际查询条件：保留 reactive 引用，模板与请求参数共用
const query = reactive({ ...query_orig })

// 表单默认值：新建租户默认给 100 用户 / 1024MB 的初始额度，status=1 启用；
// 编辑时先铺默认值再覆盖行数据，避免残留上一次编辑的内容
const form_orig = {
  id: null, tenant_name: '', tenant_code: '', expire_time: '',
  max_user_count: 100, max_storage_mb: 1024, status: 1, remark: ''
}
// 当前新建/编辑的表单数据，与弹窗表单双向绑定
const form = reactive({ ...form_orig })

// 必填校验规则：名称与编码不能为空，文本框失焦触发
const rules = {
  tenant_name: [{ required: true, message: '请输入租户名称', trigger: 'blur' }],
  tenant_code: [{ required: true, message: '请输入租户编码', trigger: 'blur' }]
}

// 集中维护接口前缀，避免各处硬编码；按动作名返回对应 URL
function apiUrl(action) {
  const base = '/tenant/tenant'
  return { list: base + '/list', create: base + '/create', update: base + '/update', delete: base + '/delete' }[action]
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

// 新建：恢复默认表单，设置标题并打开弹窗
function openCreate() { Object.assign(form, form_orig); dialogTitle.value = '新建租户'; dialogVisible.value = true }
// 编辑：先铺默认值再覆盖行数据，保证当前行没有的字段回到默认而不是沿用上一条记录的值
function openEdit(row) { Object.assign(form, form_orig, row); dialogTitle.value = '编辑租户'; dialogVisible.value = true }

// 提交表单：先校验，再按有无 id 区分新建/更新，成功后关闭弹窗并刷新列表
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
      // 新建：直接提交整份表单
      await request.post(apiUrl('create'), form); ElMessage.success('新建成功')
    }
    // 成功后关闭弹窗并刷新列表
    dialogVisible.value = false; fetchList()
  } finally { saving.value = false }
}

// 删除租户：二次确认文案带出名称，降低误删风险；用户取消会 reject，不会执行删除
async function handleDelete(row) {
  await ElMessageBox.confirm(`确定删除租户「${row.tenant_name}」？`, '提示', { type: 'warning' })
  await request.delete(apiUrl('delete'), { data: { ids: [row.id] } })
  ElMessage.success('删除成功'); fetchList()
}

// 页面挂载后加载第一页
onMounted(fetchList)
</script>
