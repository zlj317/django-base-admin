<!--
  文件说明：报表分类（RP Category）管理页面。
  职责：维护报表模板可选的分类字典，提供按名称查询、分页列表、新增/编辑、启用停用切换、
        单条删除与批量删除。
  依赖：Element Plus（表单/表格/弹窗/分页）与 @element-plus/icons-vue 图标、
        @/utils/request 统一请求封装（负责 baseURL/Token/错误提示）、v-perm 按钮级权限指令。
  被谁使用：rp 模块菜单路由加载本页；报表模板页（views/rp/template）通过
            /rp/category/list 拉取分类下拉数据，因此这里的启停状态会影响模板可选分类范围。
-->
<template>
  <!-- 页面根容器：复用全局 app-container 样式，统一页面内边距与背景 -->
  <div class="app-container">
    <!-- 页头：左侧标题区，右侧预留给后续扩展的操作按钮 -->
    <div class="page-header">
      <!-- 标题包裹层：约束主标题与副标题的垂直排布 -->
      <div class="page-title-wrap">
        <!-- 页面主标题 -->
        <h2>报表分类</h2>
        <!-- 副标题：total 取自列表接口返回的总条数，随查询条件实时变化 -->
        <div class="sub">分类维护 · 共 {{ total }} 条</div>
      </div>
    </div>
    <!-- 查询卡片：shadow="never" 去掉阴影，与下方表格卡片保持扁平的统一视觉 -->
    <el-card shadow="never" class="search-card">
      <!-- 查询表单：inline 行内布局节省纵向空间；@submit.prevent 阻止原生表单提交，
           避免输入框回车时触发页面刷新而丢失查询状态 -->
      <el-form :model="query" inline @submit.prevent>
        <!-- 查询项：按分类名称模糊检索 -->
        <el-form-item label="分类名称">
          <!-- 两向绑定 query.category_name；clearable 支持一键清空；
               固定宽度避免不同分辨率下布局抖动；@keyup.enter 回车即查询，符合列表页操作习惯 -->
          <el-input v-model="query.category_name" placeholder="请输入分类名称" clearable style="width: 170px" @keyup.enter="handleSearch" />
        </el-form-item>
        <!-- 无标签的操作项：仅承载查询与重置按钮 -->
        <el-form-item>
          <!-- 查询：交给 handleSearch，内部会先把页码重置为 1 再请求 -->
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <!-- 重置：还原默认查询条件并重新加载第一页 -->
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 列表卡片：承载表格与分页 -->
    <el-card shadow="never" class="table-card">
      <!-- 卡片头部插槽：集中放置表格上方的批量操作入口 -->
      <template #header>
        <!-- 头部容器：flex 布局，使操作按钮组靠右对齐 -->
        <div class="card-header">
          <!-- 操作按钮组 -->
          <div class="card-actions">
            <!-- 新增：v-perm 校验 'rp:create' 权限，无权限时该按钮不渲染；点击打开已重置的新增弹窗 -->
            <el-button v-perm="'rp:create'" type="primary" :icon="Plus" @click="openCreate">新增</el-button>
            <!-- 批量删除：未勾选任何行时 disabled，避免空 ids 请求；权限为 'rp:delete' -->
            <el-button v-perm="'rp:delete'" type="danger" plain :icon="Delete" :disabled="!selection.length" @click="handleBatchDelete">批量删除</el-button>
          </div>
        </div>
      </template>
      <!-- 数据表格：v-loading 在请求期间显示遮罩；stripe 斑马纹提升可读性；
           empty-text 空数据文案；selection-change 同步勾选行供批量删除使用 -->
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据" @selection-change="onSelectionChange">
        <!-- 序号列：type="index" 由表格自动按当前页生成行号，无需后端返回 -->
        <el-table-column type="index" label="序号" width="70" align="center" />
        <!-- 多选列：勾选结果写入 selection，是批量删除按钮启用与入参的来源 -->
        <el-table-column type="selection" width="50" />
        <!-- 分类名称：min-width 保证窄屏不挤压；show-overflow-tooltip 在内容超长时悬浮显示全文 -->
        <el-table-column label="分类名称" prop="category_name" min-width="160" show-overflow-tooltip />
        <!-- 分类编码：业务唯一标识，模板通过编码引用分类，编辑时应保持稳定 -->
        <el-table-column label="分类编码" prop="category_code" min-width="140" show-overflow-tooltip />
        <!-- 父级ID：树形层级字段，0 表示顶级分类 -->
        <el-table-column label="父级ID" prop="parent_id" width="90" />
        <!-- 排序：数值越小越靠前，列表顺序由后端按该字段升序返回 -->
        <el-table-column label="排序" prop="sort" width="90" />
        <!-- 状态列：仅展示开关，居中显示 -->
        <el-table-column label="状态" width="90" align="center">
          <!-- 作用域插槽：解构当前行 row，直接读写该行字段 -->
          <template #default="{ row }">
            <!-- 状态开关：active-value=1 / inactive-value=0 与后端枚举一致；
                 v-perm 无 'rp:update' 权限时不可操作；change 后立即调用状态接口（乐观更新，失败由请求拦截器提示） -->
            <el-switch v-model="row.status" :active-value="1" :inactive-value="0" v-perm="'rp:update'" @change="handleStatusChange(row)" />
          </template>
        </el-table-column>
        <!-- 备注：自由文本说明，超长省略 -->
        <el-table-column label="备注" prop="remark" min-width="180" show-overflow-tooltip />
        <!-- 创建时间：后端已格式化为字符串，前端直接展示不做二次处理 -->
        <el-table-column label="创建时间" prop="create_time" width="170" />
        <!-- 操作列：fixed="right" 固定在表格右侧，横向滚动时仍可见；
             class-name="op-col" 复用全局操作列样式（按钮间距与对齐） -->
        <el-table-column label="操作" width="180" fixed="right" class-name="op-col">
          <template #default="{ row }">
            <!-- 编辑：将当前行回填到表单，openEdit 内部先用默认值兜底防止残留 -->
            <el-button v-perm="'rp:update'" link type="primary" @click="openEdit(row)">编辑</el-button>
            <!-- 删除：二次确认后按 id 删除单条分类 -->
            <el-button v-perm="'rp:delete'" link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <!-- 分页容器：统一右对齐，与其他列表页保持一致的版式 -->
      <div class="pagination-wrap">
        <!-- 分页器：background 背景块样式；layout 控制展示总数/每页条数/翻页/跳页；
             v-model:current-page 与 v-model:page-size 双向绑定 query，翻页即改查询参数；
             @change 在页码或每页条数变化时重新请求列表 -->
        <el-pagination background layout="total, sizes, prev, pager, next, jumper"
          :total="total" v-model:current-page="query.page" v-model:page-size="query.page_size"
          :page-sizes="[10, 20, 50, 100]" @change="fetchList" />
      </div>
    </el-card>

    <!-- 新增/编辑弹窗：title 随操作动态变化；close-on-click-modal=false 防止误点遮罩丢失录入内容；
         destroy-on-close 关闭即销毁表单，避免下次打开残留上一次的数据 -->
    <el-dialog :title="dialogTitle" v-model="dialogVisible" width="560px" :close-on-click-modal="false" destroy-on-close>
      <!-- 弹窗表单：ref 暴露实例供 submitForm 调用 validate；rules 负责必填校验；label-width 统一标签宽度 -->
      <el-form ref="formRef" :model="form" :rules="rules" label-width="110px">
        <!-- 分类名称：必填；maxlength=64 与后端字段长度约束一致 -->
        <el-form-item label="分类名称" prop="category_name">
          <el-input v-model="form.category_name" placeholder="请输入分类名称" maxlength="64" />
        </el-form-item>
        <!-- 分类编码：必填且业务唯一，建议使用英文/数字短码，供模板侧引用 -->
        <el-form-item label="分类编码" prop="category_code">
          <el-input v-model="form.category_code" placeholder="请输入分类编码" maxlength="32" />
        </el-form-item>
        <!-- 父级ID：v-model.number 把输入转为数字，避免提交字符串；填 0 表示顶级分类 -->
        <el-form-item label="父级ID" prop="parent_id">
          <el-input v-model.number="form.parent_id" placeholder="0为顶级" />
        </el-form-item>
        <!-- 排序：限制 0~9999，防止误填超大值打乱列表顺序 -->
        <el-form-item label="排序" prop="sort">
          <el-input-number v-model="form.sort" :min="0" :max="9999" />
        </el-form-item>
        <!-- 状态：1 启用 / 0 停用；停用后模板的分类下拉通常不再提供该分类 -->
        <el-form-item label="状态" prop="status">
          <el-radio-group v-model="form.status">
            <el-radio :value="1">启用</el-radio>
            <el-radio :value="0">停用</el-radio>
          </el-radio-group>
        </el-form-item>
        <!-- 备注：两行文本域，存放补充说明 -->
        <el-form-item label="备注" prop="remark">
          <el-input v-model="form.remark" type="textarea" :rows="2" placeholder="请输入备注" />
        </el-form-item>
      </el-form>
      <!-- 弹窗底部插槽：取消/确定按钮 -->
      <template #footer>
        <!-- 取消：直接置为不可见，不触发校验与保存 -->
        <el-button @click="dialogVisible=false">取消</el-button>
        <!-- 确定：saving 期间按钮 loading 防重复提交；点击后走表单校验与新增/更新分支 -->
        <el-button type="primary" :loading="saving" @click="submitForm">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
// 组合式 API：script setup 内的顶层变量与函数会自动暴露给模板，无需 return
import { ref, reactive, onMounted } from 'vue'
// ElMessage 轻量提示（成功/失败）；ElMessageBox 用于删除前的二次确认弹窗
import { ElMessage, ElMessageBox } from 'element-plus'
// 图标：查询、重置、新增、批量删除按钮的视觉标识
import { Search, Refresh, Plus, Delete } from '@element-plus/icons-vue'
// 统一请求实例：已封装 baseURL、Token 注入与异常提示，业务代码只需关心接口路径
import request from '@/utils/request'

// 表格 loading：请求期间显示遮罩，防止用户重复操作
const loading = ref(false)
// 当前页数据集合，由 fetchList 回填
const rows = ref([])
// 总条数，同时驱动分页器与页头副标题
const total = ref(0)
// 表格勾选行；为空时批量删除按钮禁用
const selection = ref([])
// 提交按钮 loading，防止表单重复提交
const saving = ref(false)
// 新增/编辑弹窗显隐
const dialogVisible = ref(false)
// 弹窗标题，区分“新增分类”与“编辑分类”
const dialogTitle = ref('新增')
// 表单组件实例引用，submitForm 中调用 validate 校验
const formRef = ref()

// 查询条件默认值：既是初始值，也是重置时的还原模板
const query_orig = { page: 1, page_size: 10, category_name: '' }
// 用 reactive 包裹，模板中 query.xxx 变化可被追踪，分页组件也可直接双向绑定
const query = reactive({ ...query_orig })

// 表单默认值：id=null 代表新增；parent_id=0 表示顶级；sort=0；status=1 启用
const form_orig = {
  id: null, category_name: '', category_code: '', parent_id: 0, sort: 0, status: 1, remark: ''
}
// 弹窗表单对象，用展开拷贝避免与 form_orig 共享引用
const form = reactive({ ...form_orig })

// 校验规则：名称、编码必填，失焦即校验，与后端非空约束保持一致
const rules = {
  category_name: [{ required: true, message: '请输入分类名称', trigger: 'blur' }],
  category_code: [{ required: true, message: '请输入分类编码', trigger: 'blur' }]
}

// 按动作名返回分类模块接口地址，集中管理路径避免散落硬编码
function apiUrl(action) {
  // 分类模块统一前缀，后端路由挂载点为 /rp/category
  const base = '/rp/category'
  // 对象查表：list=分页列表、create=新增、update=更新、delete=删除
  return {
    list: base + '/list',
    create: base + '/create',
    update: base + '/update',
    delete: base + '/delete'
  }[action]
}

// 拉取分类列表：携带当前查询条件，回填数据与总数；finally 保证异常时也关闭 loading
async function fetchList() {
  loading.value = true
  try {
    // GET 请求，params 由 axios 自动拼接到查询字符串
    const res = await request.get(apiUrl('list'), { params: query })
    // 接口返回 null 时兜底为空数组，避免表格渲染异常
    rows.value = res.data.list || []
    // 总数兜底 0，避免分页器出现 NaN
    total.value = res.data.total || 0
  } finally { loading.value = false }
}
// 查询：先把页码重置为 1，防止停留在越界页导致查询结果为空
function handleSearch() { query.page = 1; fetchList() }
// 重置：用默认值覆盖查询对象（Object.assign 保留响应式引用），再按第一页查询
function handleReset() { Object.assign(query, query_orig); handleSearch() }
// 勾选变化：Element Plus 回调参数为选中行数组，直接同步给 selection
function onSelectionChange(r) { selection.value = r }

// 打开新增弹窗：先还原默认表单，避免上一次编辑的数据残留；同时切换标题
function openCreate() { Object.assign(form, form_orig); dialogTitle.value = '新增分类'; dialogVisible.value = true }
// 打开编辑弹窗：默认值打底、当前行覆盖（行对象只读取不修改），保证字段缺失时也有合理默认
function openEdit(row) { Object.assign(form, form_orig, row); dialogTitle.value = '编辑分类'; dialogVisible.value = true }

// 提交表单：先校验，再根据 id 有无区分新增与更新
async function submitForm() {
  // validate 校验失败会抛出异常并中断后续请求
  await formRef.value.validate()
  saving.value = true
  try {
    // 有 id 说明是编辑已有分类
    if (form.id) {
      // 解构剔除 id：更新接口把 id 放在路径上，请求体不再重复携带
      const { id, ...data } = form
      // PUT 更新指定 id 的分类，成功提示
      await request.put(`${apiUrl('update')}/${id}`, data); ElMessage.success('更新成功')
    } else {
      // 无 id 走新增，直接提交整个表单对象
      await request.post(apiUrl('create'), form); ElMessage.success('新增成功')
    }
    // 关闭弹窗并刷新列表，保证表格与页头总数同步
    dialogVisible.value = false; fetchList()
  } finally { saving.value = false }
}

// 行内状态切换：单独调用状态接口，避免整条记录更新时覆盖其他字段
async function handleStatusChange(row) {
  // PUT 提交最新 status；失败由请求拦截器统一提示，但此时开关已乐观改变
  await request.put(`/rp/category/status/${row.id}`, { status: row.status })
  // 按新状态给出对应提示（1=已启用，0=已停用）
  ElMessage.success(row.status === 1 ? '已启用' : '已停用')
}

// 单条删除：先二次确认，用户取消会抛异常从而中断后续删除
async function handleDelete(row) {
  // type=warning 以警示色提醒该操作不可恢复
  await ElMessageBox.confirm('确定删除该分类？', '提示', { type: 'warning' })
  // DELETE 请求体需放在 data 字段（axios 约定）；ids 传数组以兼容批量接口
  await request.delete(apiUrl('delete'), { data: { ids: [row.id] } })
  // 删除成功后提示并刷新列表
  ElMessage.success('删除成功'); fetchList()
}

// 批量删除：确认文案带选中数量，避免误删
async function handleBatchDelete() {
  await ElMessageBox.confirm(`确定删除选中的 ${selection.value.length} 条分类？`, '提示', { type: 'warning' })
  // 收集勾选行的 id 组成 ids 数组提交
  await request.delete(apiUrl('delete'), { data: { ids: selection.value.map(r => r.id) } })
  ElMessage.success('批量删除成功'); fetchList()
}

// 页面挂载后自动加载第一页数据
onMounted(fetchList)
</script>
