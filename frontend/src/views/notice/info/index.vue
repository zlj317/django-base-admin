<template>
  <!-- 文件说明：通知公告模块「公告管理（公告信息）」页面，维护公告标题/分类/内容/附件/置顶/有效期与发布状态。
       依赖：@/utils/request 统一请求；v-perm 权限指令（notice:create/update/delete）；后端接口 /notice/info/* 与 /notice/category/list。
       被使用：由公告相关菜单路由加载；门户/首页公告栏读取此处发布的公告数据。 -->
  <div class="app-container">
    <!-- 页面头部：标题与记录总数 -->
    <div class="page-header">
      <!-- 标题区：主标题 + 当前筛选结果条数 -->
      <div class="page-title-wrap">
        <h2>公告管理</h2>
        <!-- total 来自列表接口，查询/删除后随列表刷新 -->
        <div class="sub">公告列表 · 共 {{ total }} 条</div>
      </div>
    </div>
    <!-- 查询区：shadow="never" 去掉阴影，与全站列表页统一 -->
    <el-card shadow="never" class="search-card">
      <!-- inline 行内排布；@submit.prevent 阻止回车触发的原生表单提交 -->
      <el-form :model="query" inline @submit.prevent>
        <!-- 公告标题：模糊搜索，回车即查 -->
        <el-form-item label="公告标题">
          <el-input v-model="query.title" placeholder="请输入标题" clearable style="width: 180px" @keyup.enter="handleSearch" />
        </el-form-item>
        <!-- 分类筛选：选项由 loadCategories 预加载；clearable 清空后查全部分类 -->
        <el-form-item label="分类">
          <el-select v-model="query.category_id" placeholder="全部" clearable style="width: 150px">
            <el-option v-for="c in categoryOptions" :key="c.id" :label="c.category_name" :value="c.id" />
          </el-select>
        </el-form-item>
        <!-- 状态筛选：0=草稿（未发布，仅后台可见）、1=已发布（对外可见）、2=已下线（曾发布后撤下） -->
        <el-form-item label="状态">
          <el-select v-model="query.status" placeholder="全部" clearable style="width: 120px">
            <el-option label="草稿" :value="0" />
            <el-option label="已发布" :value="1" />
            <el-option label="已下线" :value="2" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <!-- 查询：回到第一页后按条件请求 -->
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <!-- 重置：恢复默认查询条件并重新查询 -->
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 表格区：公告列表 + 分页 -->
    <el-card shadow="never" class="table-card">
      <!-- 卡片头部插槽：工具栏按钮 -->
      <template #header>
        <div class="card-header">
          <div class="card-actions">
            <!-- 新增：需要 notice:create 权限，无权限时按钮被隐藏（v-perm 以 display:none 实现） -->
            <el-button v-perm="'notice:create'" type="primary" :icon="Plus" @click="openCreate">新增</el-button>
            <!-- 批量删除：需要 notice:delete 权限，未勾选时禁用避免空请求 -->
            <el-button v-perm="'notice:delete'" type="danger" plain :icon="Delete" :disabled="!selection.length" @click="handleBatchDelete">批量删除</el-button>
          </div>
        </div>
      </template>
      <!-- v-loading 请求遮罩；stripe 斑马纹；empty-text 空数据提示 -->
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据" @selection-change="onSelectionChange">
        <!-- 自动序号列 -->
        <el-table-column type="index" label="序号" width="70" align="center" />
        <!-- 勾选列：支撑批量删除 -->
        <el-table-column type="selection" width="50" />
        <!-- 公告标题：主要识别信息，过长时悬浮提示 -->
        <el-table-column label="标题" prop="title" min-width="220" show-overflow-tooltip />
        <!-- 分类：优先显示后端返回的 category_name，其次显示 id，最后占位符，避免空列 -->
        <el-table-column label="分类" min-width="120">
          <template #default="{ row }">{{ row.category_name || row.category_id || '-' }}</template>
        </el-table-column>
        <!-- 置顶：is_top 为真（后端可能返回 1/true）时显示橙色“置顶”，表示在门户列表优先展示 -->
        <el-table-column label="置顶" width="70" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.is_top" size="small" type="warning">置顶</el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <!-- 发布状态：0=草稿（灰色，仅后台可见）；1=已发布（绿色，对外可见）；2=已下线（橙色，撤下内容）；
             未知值原样显示，便于排查后端新增状态 -->
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.status===0" size="small" type="info">草稿</el-tag>
            <el-tag v-else-if="row.status===1" size="small" type="success">已发布</el-tag>
            <el-tag v-else-if="row.status===2" size="small" type="warning">已下线</el-tag>
            <span v-else>{{ row.status }}</span>
          </template>
        </el-table-column>
        <!-- 发布用户ID：记录发布操作人，便于追责/统计 -->
        <el-table-column label="发布用户ID" prop="publish_user_id" width="110" />
        <!-- 发布时间：草稿尚未发布时为空，空值统一显示 - -->
        <el-table-column label="发布时间" prop="publish_time" width="170">
          <template #default="{ row }">{{ row.publish_time || '-' }}</template>
        </el-table-column>
        <!-- 创建时间：无论是否发布都存在 -->
        <el-table-column label="创建时间" prop="create_time" width="170" />
        <!-- 操作列固定右侧；按钮随状态变化：草稿可发布、已发布可下线 -->
        <el-table-column label="操作" width="220" fixed="right" class-name="op-col">
          <template #default="{ row }">
            <!-- 编辑：任何状态都允许（含已发布），需要 notice:update 权限 -->
            <el-button v-perm="'notice:update'" link type="primary" @click="openEdit(row)">编辑</el-button>
            <!-- 发布：仅草稿（status===0）显示，发布后状态转为已发布 -->
            <el-button v-if="row.status===0" v-perm="'notice:update'" link type="success" @click="handlePublish(row)">发布</el-button>
            <!-- 下线：仅已发布（status===1）显示，下线后不再对外展示 -->
            <el-button v-if="row.status===1" v-perm="'notice:update'" link type="warning" @click="handleOffline(row)">下线</el-button>
            <!-- 删除：需要 notice:delete 权限，删除前二次确认 -->
            <el-button v-perm="'notice:delete'" link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <!-- 分页：当前页/每页条数双向绑定 query，变更后触发 fetchList -->
      <div class="pagination-wrap">
        <el-pagination background layout="total, sizes, prev, pager, next, jumper"
          :total="total" v-model:current-page="query.page" v-model:page-size="query.page_size"
          :page-sizes="[10, 20, 50, 100]" @change="fetchList" />
      </div>
    </el-card>

    <!-- 新增/编辑弹窗：标题动态切换；禁止点遮罩关闭避免录入丢失；destroy-on-close 保证重新打开表单干净 -->
    <el-dialog :title="dialogTitle" v-model="dialogVisible" width="720px" :close-on-click-modal="false" destroy-on-close>
      <!-- ref 用于提交校验；rules 控制标题/分类/内容必填；label-width=110 统一标签宽度 -->
      <el-form ref="formRef" :model="form" :rules="rules" label-width="110px">
        <!-- 两列栅格排布，标题与内容占整行 -->
        <el-row :gutter="12">
          <el-col :span="24">
            <!-- 标题：必填，最长 200 字符 -->
            <el-form-item label="标题" prop="title">
              <el-input v-model="form.title" placeholder="请输入公告标题" maxlength="200" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <!-- 分类：必填，选项来自分类接口，change 触发校验 -->
            <el-form-item label="分类" prop="category_id">
              <el-select v-model="form.category_id" placeholder="请选择分类" style="width:100%">
                <el-option v-for="c in categoryOptions" :key="c.id" :label="c.category_name" :value="c.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <!-- 状态：0 草稿 / 1 已发布 / 2 已下线；直接编辑状态用于修正数据 -->
            <el-form-item label="状态" prop="status">
              <el-select v-model="form.status" style="width:100%">
                <el-option label="草稿" :value="0" />
                <el-option label="已发布" :value="1" />
                <el-option label="已下线" :value="2" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <!-- 是否置顶：1=置顶（门户列表优先展示），0=普通 -->
            <el-form-item label="是否置顶" prop="is_top">
              <el-switch v-model="form.is_top" :active-value="1" :inactive-value="0" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <!-- 角色范围：逗号分隔的 role_id，用于限定公告可见的角色；具体为空时含义以后端约定为准 -->
            <el-form-item label="角色范围" prop="role_scope">
              <el-input v-model="form.role_scope" placeholder="role_id列表，逗号分隔" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <!-- 开始时间：公告生效起始时刻；value-format 保证提交给后端的是标准字符串而非 Date 对象 -->
            <el-form-item label="开始时间" prop="start_time">
              <el-date-picker v-model="form.start_time" type="datetime" placeholder="选择开始时间" style="width:100%" value-format="YYYY-MM-DD HH:mm:ss" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <!-- 结束时间：公告失效时刻，超过该时间门户不再展示 -->
            <el-form-item label="结束时间" prop="end_time">
              <el-date-picker v-model="form.end_time" type="datetime" placeholder="选择结束时间" style="width:100%" value-format="YYYY-MM-DD HH:mm:ss" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <!-- 附件ID列表：逗号分隔的附件 id，后端据此关联已上传文件 -->
            <el-form-item label="附件ID列表" prop="attachment_ids">
              <el-input v-model="form.attachment_ids" placeholder="附件ID逗号分隔" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <!-- 公告内容：必填正文，6 行高度便于编辑；当前为纯文本，不支持富文本 -->
            <el-form-item label="公告内容" prop="content">
              <el-input v-model="form.content" type="textarea" :rows="6" placeholder="请输入公告内容" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <!-- 底部：取消仅关闭；确定走 submitForm 并由 saving 防重复提交 -->
      <template #footer>
        <el-button @click="dialogVisible=false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitForm">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
// 响应式 API 与挂载钩子
import { ref, reactive, onMounted } from 'vue'
// 消息提示与二次确认框（发布/下线/删除均需确认）
import { ElMessage, ElMessageBox } from 'element-plus'
// 查询/重置/新增/删除按钮图标，按需引入
import { Search, Refresh, Plus, Delete } from '@element-plus/icons-vue'
// 统一请求实例：内置鉴权、统一错误提示与 401 跳转
import request from '@/utils/request'

// 列表加载状态，控制表格遮罩
const loading = ref(false)
// 当前页公告数据
const rows = ref([])
// 总记录数，供分页与页面统计
const total = ref(0)
// 勾选行，批量删除时取 id
const selection = ref([])
// 提交中状态，防止重复点击“确定”
const saving = ref(false)
// 弹窗显隐
const dialogVisible = ref(false)
// 弹窗标题，新增/编辑切换
const dialogTitle = ref('新增')
// 表单实例，提交前调用 validate
const formRef = ref()
// 公告分类下拉选项缓存，筛选与表单共用，避免重复请求
const categoryOptions = ref([])

// 查询条件初始值：status/category_id 为 null 表示不限制；重置时整体还原
const query_orig = { page: 1, page_size: 10, title: '', category_id: null, status: null }
// 查询条件响应式副本
const query = reactive({ ...query_orig })

// 表单初始值：新增默认状态 0（草稿）、不置顶；时间与附件为空字符串便于后端判空
const form_orig = {
  id: null, title: '', category_id: null, content: '', attachment_ids: '',
  is_top: 0, status: 0, role_scope: '', start_time: '', end_time: '',
  publish_user_id: null, publish_time: ''
}
// 弹窗表单响应式副本
const form = reactive({ ...form_orig })

// 校验规则：标题与内容 blur 校验、分类 change 校验（选择后立即消除报错）
// 注意：publish_user_id/publish_time 不在表单中，仅作数据字段保留
const rules = {
  title: [{ required: true, message: '请输入公告标题', trigger: 'blur' }],
  category_id: [{ required: true, message: '请选择分类', trigger: 'change' }],
  content: [{ required: true, message: '请输入公告内容', trigger: 'blur' }]
}

// 按动作名返回接口地址：base 集中定义，避免多处硬编码路径不一致
function apiUrl(action) {
  const base = '/notice/info'
  return {
    list: base + '/list',
    create: base + '/create',
    update: base + '/update',
    delete: base + '/delete'
  }[action]
}

// 预加载分类选项：一次取 200 条作为上限，供筛选与表单共用
async function loadCategories() {
  try {
    const res = await request.get('/notice/category/list', { params: { page: 1, page_size: 200 } })
    // 返回为空时降级空数组，保证下拉不报错
    categoryOptions.value = res.data.list || []
  // 分类加载失败不阻断公告列表展示，错误提示由 request 拦截器统一处理
  } catch (e) { /* ignore */ }
}

// 查询列表：query 同时携带分页与筛选条件
async function fetchList() {
  loading.value = true
  try {
    const res = await request.get(apiUrl('list'), { params: query })
    // 空数据兜底为数组，表格可正常展示空状态
    rows.value = res.data.list || []
    // 总数兜底 0，避免分页组件异常
    total.value = res.data.total || 0
  // 成功失败都解除 loading，防止遮罩残留
  } finally { loading.value = false }
}
// 查询：回到第一页再请求，避免页码越界
function handleSearch() { query.page = 1; fetchList() }
// 重置：整体还原查询条件（含分页）后重新查询
function handleReset() { Object.assign(query, query_orig); handleSearch() }
// 勾选变化：同步选中行供批量删除
function onSelectionChange(r) { selection.value = r }

// 新增：先把表单恢复默认值（清掉上次编辑残留），再打开弹窗
function openCreate() { Object.assign(form, form_orig); dialogTitle.value = '新增公告'; dialogVisible.value = true }
// 编辑：先重置默认值再覆盖整行，避免行内缺失字段沿用上次数据
function openEdit(row) { Object.assign(form, form_orig, row); dialogTitle.value = '编辑公告'; dialogVisible.value = true }

// 提交表单：有 id 走更新、无 id 走新增；成功后关闭弹窗并刷新列表
async function submitForm() {
  // 前端校验不通过会抛错并中止请求
  await formRef.value.validate()
  saving.value = true
  try {
    if (form.id) {
      // 编辑：剔除 id 后提交其余字段，id 通过路径参数传递
      const { id, ...data } = form
      await request.put(`${apiUrl('update')}/${id}`, data); ElMessage.success('更新成功')
    } else {
      // 新增：整份表单提交，状态默认草稿
      await request.post(apiUrl('create'), form); ElMessage.success('新增成功')
    }
    // 成功后收起弹窗并刷新当前页
    dialogVisible.value = false; fetchList()
  // 失败时仅释放按钮 loading，保留弹窗便于修改重试
  } finally { saving.value = false }
}

// 发布：仅草稿行可见；确认后调用发布接口，由后端把状态改为 1
async function handlePublish(row) {
  await ElMessageBox.confirm('确定发布该公告？', '提示', { type: 'warning' })
  await request.put(`/notice/info/publish/${row.id}`)
  ElMessage.success('发布成功'); fetchList()
}

// 下线：仅已发布行可见；确认后调用下线接口，由后端把状态改为 2
async function handleOffline(row) {
  await ElMessageBox.confirm('确定下线该公告？', '提示', { type: 'warning' })
  await request.put(`/notice/info/offline/${row.id}`)
  ElMessage.success('已下线'); fetchList()
}

// 单条删除：二次确认后按 ids 数组提交
async function handleDelete(row) {
  await ElMessageBox.confirm('确定删除该公告？', '提示', { type: 'warning' })
  await request.delete(apiUrl('delete'), { data: { ids: [row.id] } })
  ElMessage.success('删除成功'); fetchList()
}

// 批量删除：勾选行 id 一次性提交
async function handleBatchDelete() {
  await ElMessageBox.confirm(`确定删除选中的 ${selection.value.length} 条公告？`, '提示', { type: 'warning' })
  await request.delete(apiUrl('delete'), { data: { ids: selection.value.map(r => r.id) } })
  ElMessage.success('批量删除成功'); fetchList()
}

// 挂载后并行加载公告列表与分类选项：两者相互独立，先渲染列表可减少白屏
onMounted(() => { fetchList(); loadCategories() })
</script>
