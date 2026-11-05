<!--
  文件级说明：
  职责：BI「大屏管理」页——维护大屏基础配置（名称、JSON 布局、状态、自动刷新间隔、分享密码/链接），
        提供搜索、分页列表、预览、发布、分享、删除（含批量）。
  依赖：@/utils/request（统一请求封装）、Element Plus 组件与图标、vue-router（预览跳转）、
        全局 v-perm 指令（bi:create/bi:update/bi:publish/bi:delete）。
  被谁使用：BI 菜单下的大屏管理路由；预览/分享分别路由到 views/bi/screen/view.vue（BiScreenView / BiScreenShare）。
  说明：本文件没有 <style> 段，视觉样式全部复用全局样式。
-->
<template>
  <!-- 页面根容器：复用全局 app-container 内边距 -->
  <div class="app-container">
    <!-- 页头：标题 + 当前筛选条件下的总条数 -->
    <div class="page-header">
      <div class="page-title-wrap">
        <!-- 模块标题 -->
        <h2>大屏管理</h2>
        <!-- 副标题：total 来自列表接口 -->
        <div class="sub">大屏配置 · 共 {{ total }} 条</div>
      </div>
    </div>
    <!-- 搜索区：按名称与状态过滤 -->
    <el-card shadow="never" class="search-card">
      <!-- inline 横向排列；@submit.prevent 阻止表单默认提交刷新页面 -->
      <el-form :model="query" inline @submit.prevent>
        <el-form-item label="大屏名称">
          <!-- 名称模糊搜索：clearable 可清空；回车等价于点查询 -->
          <el-input v-model="query.screen_name" placeholder="请输入名称" clearable style="width: 170px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="状态">
          <!-- 状态筛选：0=草稿、1=已发布、2=停用，与表格标签/表单下拉的取值保持一致 -->
          <el-select v-model="query.status" placeholder="全部" clearable style="width: 130px">
            <el-option label="草稿" :value="0" />
            <el-option label="已发布" :value="1" />
            <el-option label="停用" :value="2" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <!-- 查询：重置到第 1 页再请求 -->
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <!-- 重置：恢复查询初值后再请求 -->
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 表格卡：头部为新增/批量删除，主体为分页列表 -->
    <el-card shadow="never" class="table-card">
      <template #header>
        <div class="card-header">
          <div class="card-actions">
            <!-- 新增：v-perm 控制 bi:create 权限，无权限时指令直接隐藏 -->
            <el-button v-perm="'bi:create'" type="primary" :icon="Plus" @click="openCreate">新增</el-button>
            <!-- 批量删除：未勾选时置灰；权限码 bi:delete；点击后二次确认 -->
            <el-button v-perm="'bi:delete'" type="danger" plain :icon="Delete" :disabled="!selection.length" @click="handleBatchDelete">批量删除</el-button>
          </div>
        </div>
      </template>
      <!-- 列表：@selection-change 同步勾选行，供批量删除 -->
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据" @selection-change="onSelectionChange">
        <!-- 序号列：当前页展示序号 -->
        <el-table-column type="index" label="序号" width="70" align="center" />
        <!-- 勾选列：开启多选 -->
        <el-table-column type="selection" width="50" />
        <!-- 大屏名称：超长时悬浮显示全文 -->
        <el-table-column label="大屏名称" prop="screen_name" min-width="180" show-overflow-tooltip />
        <!-- 刷新秒：大屏预览时的自动刷新间隔（0 表示不自动刷新），显示在预览页顶栏 -->
        <el-table-column label="刷新秒" prop="refresh_sec" width="90" />
        <!-- 分享链接：发布后由后端生成的分享地址（通常含 token）；未生成时显示“-” -->
        <el-table-column label="分享链接" prop="share_url" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">{{ row.share_url || '-' }}</template>
        </el-table-column>
        <!-- 状态列：0=草稿（灰）、1=已发布（绿）、2=停用（黄），未知值回退为原始文本 -->
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.status===0" size="small" type="info">草稿</el-tag>
            <el-tag v-else-if="row.status===1" size="small" type="success">已发布</el-tag>
            <el-tag v-else-if="row.status===2" size="small" type="warning">停用</el-tag>
            <span v-else>{{ row.status }}</span>
          </template>
        </el-table-column>
        <!-- 创建时间：后端格式化好的字符串 -->
        <el-table-column label="创建时间" prop="create_time" width="170" />
        <!-- 操作列：宽度 330 容纳最多 5 个按钮；fixed=right 横向滚动时固定 -->
        <el-table-column label="操作" width="330" fixed="right" class-name="op-col">
          <template #default="{ row }">
            <!-- 预览：跳转到 /bi/view/:id（路由 BiScreenView，不挂后台布局，铺满窗口） -->
            <el-button link type="warning" @click="handleView(row)">预览</el-button>
            <!-- 编辑：按 bi:update 权限显示，回填整行数据到弹窗 -->
            <el-button v-perm="'bi:update'" link type="primary" @click="openEdit(row)">编辑</el-button>
            <!-- 发布：仅草稿状态可见；再叠加 bi:publish 权限；发布后后端生成 share_url 并刷新列表 -->
            <el-button v-if="row.status===0" v-perm="'bi:publish'" link type="success" @click="handlePublish(row)">发布</el-button>
            <!-- 分享：仅已发布且已生成 share_url 时可见，直接用后端地址在新标签打开 -->
            <el-button v-if="row.status===1 && row.share_url" link type="success" @click="handleShare(row)">分享</el-button>
            <!-- 删除：按 bi:delete 权限显示 -->
            <el-button v-perm="'bi:delete'" link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <!-- 分页器：v-model 绑定 query.page/page_size，@change 覆盖页码与每页条数变化 -->
      <div class="pagination-wrap">
        <el-pagination background layout="total, sizes, prev, pager, next, jumper"
          :total="total" v-model:current-page="query.page" v-model:page-size="query.page_size"
          :page-sizes="[10, 20, 50, 100]" @change="fetchList" />
      </div>
    </el-card>

    <!-- 新增/编辑弹窗：共用表单，标题由 dialogTitle 区分；720px 宽度容纳 8 行 JSON 配置 -->
    <el-dialog :title="dialogTitle" v-model="dialogVisible" width="720px" :close-on-click-modal="false" destroy-on-close>
      <!-- 表单：formRef 提交前校验；label-width=110 让“分享密码/刷新秒”等标签对齐 -->
      <el-form ref="formRef" :model="form" :rules="rules" label-width="110px">
        <!-- 大屏名称：必填，显示在预览页顶栏与画布标题处 -->
        <el-form-item label="大屏名称" prop="screen_name">
          <el-input v-model="form.screen_name" placeholder="请输入大屏名称" maxlength="100" />
        </el-form-item>
        <!-- 大屏配置：JSON 字符串，view.vue 解析后决定画布尺寸与所有图表位置。
             主要字段含义：
               width/height：设计稿画布尺寸（默认 1920x1080），缩放按此比例计算；
               background：画布背景（可选，覆盖默认深色底）；
               widgets[]：每个图表一项，x/y/w/h 为画布内的绝对坐标与尺寸（px），
               type 决定渲染组件（kpi/table/text/line/bar/pie 等），
               title/unit/subtitle 为展示文案，data 为由数据集查询出的 columns/rows/categories/series/value 等。
             前端只做文本编辑，不解析/校验 JSON 合法性（由后端与预览页解析） -->
        <el-form-item label="大屏配置" prop="screen_config">
          <el-input v-model="form.screen_config" type="textarea" :rows="8" placeholder="大屏JSON配置" />
        </el-form-item>
        <!-- 状态：0=草稿、1=已发布、2=停用；发布按钮会把草稿改为已发布并生成分享链接 -->
        <el-form-item label="状态" prop="status">
          <el-select v-model="form.status" style="width:100%">
            <el-option label="草稿" :value="0" />
            <el-option label="已发布" :value="1" />
            <el-option label="停用" :value="2" />
          </el-select>
        </el-form-item>
        <!-- 刷新秒：预览页自动刷新数据的间隔，0~3600 秒；0 表示不自动刷新 -->
        <el-form-item label="刷新秒" prop="refresh_sec">
          <el-input-number v-model="form.refresh_sec" :min="0" :max="3600" />
        </el-form-item>
        <!-- 分享密码：可选，留空表示分享链接无密码；show-password 隐藏明文，maxlength=32 对齐后端字段 -->
        <el-form-item label="分享密码" prop="share_password">
          <el-input v-model="form.share_password" placeholder="可留空，留空则无密码" maxlength="32" show-password />
        </el-form-item>
        <!-- 备注：可选说明，仅后台可见 -->
        <el-form-item label="备注" prop="remark">
          <el-input v-model="form.remark" type="textarea" :rows="2" placeholder="请输入备注" />
        </el-form-item>
      </el-form>
      <!-- 底部按钮：取消关闭弹窗；确定用 saving 控制 loading，避免重复提交 -->
      <template #footer>
        <el-button @click="dialogVisible=false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitForm">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
// 组合式 API：状态与方法局部于本组件
// ref 基础响应式/模板引用；reactive 表单与查询对象；onMounted 首屏加载
import { ref, reactive, onMounted } from 'vue'
// useRouter 仅用于“预览”的编程式跳转，避免在表格里拼 router-link
import { useRouter } from 'vue-router'
// ElMessage 结果提示；ElMessageBox 删除二次确认
import { ElMessage, ElMessageBox } from 'element-plus'
// 图标：Search/Refresh 搜索按钮；Plus/Delete 新增与批量删除
import { Search, Refresh, Plus, Delete } from '@element-plus/icons-vue'
// 统一请求实例：自动带 token、统一解析 { code, msg, data }、统一错误提示
import request from '@/utils/request'

// 路由实例：handleView 用它跳到预览页
const router = useRouter()

// 列表加载态：控制 el-table 的 v-loading
const loading = ref(false)
// 当前页大屏数据
const rows = ref([])
// 总条数：分页器与页头副标题共用
const total = ref(0)
// 当前勾选行：用于批量删除按钮的可用状态与提交
const selection = ref([])
// 提交中标记：防止弹窗重复提交
const saving = ref(false)
// 弹窗显隐
const dialogVisible = ref(false)
// 弹窗标题：新增/编辑共用弹窗，用标题区分模式
const dialogTitle = ref('新增')
// el-form 实例：提交前 validate
const formRef = ref()

// 查询初值：重置时整体恢复，页码回到 1
const query_orig = { page: 1, page_size: 10, screen_name: '', status: null }
// 查询对象：reactive 便于 Object.assign 重置；分页器直接 v-model 到 page/page_size
const query = reactive({ ...query_orig })

// 表单初值：新建默认草稿（status=0）、60 秒刷新、无分享密码/链接；编辑时由整行数据覆盖
const form_orig = {
  id: null, screen_name: '', screen_config: '', status: 0,
  share_url: '', share_password: '', refresh_sec: 60, remark: ''
}
// 弹窗表单：就地重置/回填；share_url 用户不可编辑，仅随编辑回填、提交时一并带回后端
const form = reactive({ ...form_orig })

// 校验规则：名称与配置必填；配置的 JSON 合法性不在前端校验，交给后端/预览页解析
const rules = {
  screen_name: [{ required: true, message: '请输入大屏名称', trigger: 'blur' }],
  screen_config: [{ required: true, message: '请输入大屏配置', trigger: 'blur' }]
}

// 接口地址表：集中维护 /bi/screen 的四个动作路径；update 需在调用处再拼 /{id}
function apiUrl(action) {
  const base = '/bi/screen'
  return {
    list: base + '/list',
    create: base + '/create',
    update: base + '/update',
    delete: base + '/delete'
  }[action]
}

// 拉取大屏列表：params 为 reactive 的 query；finally 保证异常时解除 loading
async function fetchList() {
  loading.value = true
  try {
    const res = await request.get(apiUrl('list'), { params: query })
    // 兼容后端未返回 list/total
    rows.value = res.data.list || []
    total.value = res.data.total || 0
  } finally { loading.value = false }
}
// 查询：回到第 1 页，避免旧页码超出新条件的总页数
function handleSearch() { query.page = 1; fetchList() }
// 重置：整体恢复查询初值后再查询
function handleReset() { Object.assign(query, query_orig); handleSearch() }
// 勾选变化：直接使用 el-table 回调的最新选中行数组
function onSelectionChange(r) { selection.value = r }

// 新增：恢复表单初值并设置标题；share_url 也被清空，避免新建时误带上一条大屏的分享地址
function openCreate() { Object.assign(form, form_orig); dialogTitle.value = '新增大屏'; dialogVisible.value = true }
// 编辑：先恢复初值再用整行覆盖（含 share_url/share_password），提交时剔除 id；share_url 在界面上不可见但会原样回传
function openEdit(row) { Object.assign(form, form_orig, row); dialogTitle.value = '编辑大屏'; dialogVisible.value = true }

// 提交：校验后按有无 id 走更新/新增；成功后关闭弹窗并刷新列表（名称/状态/分享链接可能变化）
async function submitForm() {
  await formRef.value.validate()
  saving.value = true
  try {
    if (form.id) {
      // 更新：剔除 id（主键已在 URL 中），其余字段整体提交
      const { id, ...data } = form
      await request.put(`${apiUrl('update')}/${id}`, data); ElMessage.success('更新成功')
    } else {
      // 新增：直接提交表单（含默认 status=0 草稿）
      await request.post(apiUrl('create'), form); ElMessage.success('新增成功')
    }
    dialogVisible.value = false; fetchList()
  } finally { saving.value = false }
}

// 发布：二次确认后调用 publish 接口（无请求体）；发布成功后后端会生成 share_url，
// 因此必须刷新列表才能拿到最新状态与分享地址（本地不自行改 status，避免与后端不一致）
async function handlePublish(row) {
  await ElMessageBox.confirm(`确定发布大屏「${row.screen_name}」？`, '提示', { type: 'warning' })
  await request.post(`/bi/screen/publish/${row.id}`)
  ElMessage.success('发布成功'); fetchList()
}

// 预览：跳转 /bi/view/:id（路由 BiScreenView，不套后台布局、铺满窗口），只读展示不做权限拦截
function handleView(row) {
  router.push(`/bi/view/${row.id}`)
}

// 分享：优先使用后端生成的 share_url（通常带 token，可免登录访问）；
// 缺失时回退到本地预览路由（需登录）；用 window.open 新标签打开，不影响当前管理页
function handleShare(row) {
  const path = row.share_url || `/bi/view/${row.id}`
  window.open(path, '_blank')
}

// 单条删除：二次确认后按 ids 数组提交（axios delete 用 data 携带请求体），成功后刷新列表
async function handleDelete(row) {
  await ElMessageBox.confirm('确定删除该大屏？', '提示', { type: 'warning' })
  await request.delete(apiUrl('delete'), { data: { ids: [row.id] } })
  ElMessage.success('删除成功'); fetchList()
}

// 批量删除：确认文案带选中数量，把 selection 映射成 id 数组一次提交
async function handleBatchDelete() {
  await ElMessageBox.confirm(`确定删除选中的 ${selection.value.length} 条大屏？`, '提示', { type: 'warning' })
  await request.delete(apiUrl('delete'), { data: { ids: selection.value.map(r => r.id) } })
  ElMessage.success('批量删除成功'); fetchList()
}

// 首屏加载列表；大屏下拉在其他页面（数据集）才需要，这里不额外请求
onMounted(fetchList)
</script>
