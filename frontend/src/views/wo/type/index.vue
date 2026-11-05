<!-- 工单类型页（工单管理 / 工单类型）
     职责：维护工单分类字典（类型名称、排序、启用/停用、备注）。工单列表页与"我的工单"页的类型下拉，
           均通过 GET /wo/type/list 读取本页维护的数据，因此本页是工单模块的基础配置入口。
     接口：GET /wo/type/list（分页列表）、POST /wo/type/create、PUT /wo/type/update/{id}、
           DELETE /wo/type/delete（按 ids 批量删除）；列表内的启停用开关复用 update 接口（仅传 status）。
     依赖：utils/request（统一注入 token 与错误提示）、Element Plus 的表单/表格/弹窗/分页组件、
           @element-plus/icons-vue 图标。
     被谁使用：由后端菜单表配置的 path（如 /wo/type）动态挂载；页面按钮未接 v-perm 权限码，
               能否增删改由后端接口鉴权决定。 -->
<template>
  <!-- 页面根容器：复用全局 .app-container 的留白与进场动画，与其它配置类页面版式一致 -->
  <div class="app-container">
    <!-- 页头：只放标题与总数；新建入口放在下方表格卡片工具栏，保持配置页"先看数据再操作"的节奏 -->
    <div class="page-header">
      <!-- 标题组：全局样式统一控制标题/副标题的字号、间距与颜色 -->
      <div class="page-title-wrap">
        <!-- 主标题与菜单名称一致，便于用户确认当前所在模块 -->
        <h2>工单类型</h2>
        <!-- 副标题展示总数：total 来自列表接口，随筛选条件变化 -->
        <div class="sub">工单分类 · 共 {{ total }} 条</div>
      </div>
    </div>
    <!-- 查询区卡片：shadow="never" 弱化层级，让表格成为视觉主体 -->
    <el-card shadow="never" class="search-card">
      <!-- inline 横排筛选项；@submit.prevent 阻止表单默认提交，避免回车时刷新整页 -->
      <el-form :model="query" inline @submit.prevent>
        <!-- 筛选项：类型名称关键字，透传给后端匹配 -->
        <el-form-item label="类型名称">
          <!-- clearable 一键清空；回车直接查询；固定 170px 与工单页文本筛选框宽度保持一致 -->
          <el-input v-model="query.type_name" placeholder="请输入类型名称" clearable style="width: 170px" @keyup.enter="handleSearch" />
        </el-form-item>
        <!-- 筛选项：启用状态；本页只有启用/停用两态，因此直接写死两个 el-option，无需字典 -->
        <el-form-item label="状态">
          <!-- clearable 清空即"全部"（初始 null）；110px 足够容纳"全部/启用/停用" -->
          <el-select v-model="query.status" placeholder="全部" clearable style="width: 110px">
            <!-- 1=启用：可被工单表单选中；数值与表格开关的 active-value 保持一致 -->
            <el-option label="启用" :value="1" />
            <!-- 0=停用：字典项仍保留，只是不再出现在新建工单的类型下拉中 -->
            <el-option label="停用" :value="0" />
          </el-select>
        </el-form-item>
        <!-- 操作按钮组无 label，紧跟筛选项之后 -->
        <el-form-item>
          <!-- 查询：handleSearch 先把页码重置为 1，避免停留在越界页导致空列表 -->
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <!-- 重置：回填默认条件后重新查询，不做二次确认 -->
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 表格卡片：与查询区拆开，查询只刷新表体；.table-card 全局类负责圆角与内边距 -->
    <el-card shadow="never" class="table-card">
      <!-- 卡片头部插槽：放置工具栏，新建入口固定在表格正上方 -->
      <template #header>
        <div class="card-header">
          <!-- 操作区：本页只有"新建类型"一个页级操作 -->
          <div class="card-actions">
            <!-- 新建：openCreate 会先回填默认值再打开弹窗，避免残留上次编辑的内容 -->
            <el-button type="primary" :icon="Plus" @click="openCreate">新建类型</el-button>
          </div>
        </div>
      </template>
      <!-- 表格：v-loading 请求期间遮罩防重复操作；stripe 斑马纹辅助读行；empty-text 统一空态文案 -->
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据">
        <!-- 序号列：按当前页递增，仅用于阅读定位 -->
        <el-table-column type="index" label="序号" width="70" align="center" />
        <!-- 类型名称：配置项的主字段；min-width 保证窄屏可读，超长省略并悬浮显示全文 -->
        <el-table-column label="类型名称" prop="type_name" min-width="200" show-overflow-tooltip />
        <!-- 排序：数值越小越靠前（由后端按该字段排序），固定宽度足够展示三位数以内 -->
        <el-table-column label="排序" prop="sort" width="90" />
        <!-- 状态列：用开关做就地表更，免去"编辑弹窗改状态再保存"的多步操作 -->
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <!-- v-model 直接绑定行对象的 status，切换瞬间 UI 先变；active-value=1（启用）、inactive-value=0（停用） -->
            <!-- @change 立即调用 update 接口；失败时由 handleStatusChange 回滚开关，避免界面与后端不一致 -->
            <el-switch v-model="row.status" :active-value="1" :inactive-value="0" @change="handleStatusChange(row)" />
          </template>
        </el-table-column>
        <!-- 操作列：fixed="right" 固定右侧；160px 容纳"编辑/删除"两个 link 按钮 -->
        <el-table-column label="操作" width="160" fixed="right" class-name="op-col">
          <template #default="{ row }">
            <!-- 编辑：打开弹窗修改名称/排序/状态/备注，走 update 接口整体保存 -->
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <!-- 删除：不可逆，点击后二次确认；已关联工单的类型是否允许删除由后端判定 -->
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <!-- 分页条容器：与表体拉开间距 -->
      <div class="pagination-wrap">
        <!-- v-model 直接改写 query.page/page_size；@change 在页码或页大小变化时重新请求 -->
        <el-pagination background layout="total, sizes, prev, pager, next, jumper"
          :total="total" v-model:current-page="query.page" v-model:page-size="query.page_size"
          :page-sizes="[10, 20, 50, 100]" @change="fetchList" />
      </div>
    </el-card>

    <!-- 新建/编辑弹窗：两种模式共用一套表单，靠 dialogTitle 与 form.id 区分；520px 足够放下四个短字段 -->
    <!-- :close-on-click-modal="false" 防止误点遮罩丢失输入；destroy-on-close 保证下次打开不残留校验状态 -->
    <el-dialog :title="dialogTitle" v-model="dialogVisible" width="520px" :close-on-click-modal="false" destroy-on-close>
      <!-- formRef 供 submitForm 调用 validate()；rules 只约束类型名称必填 -->
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <!-- 类型名称：必填项；maxlength=100 与后端字段长度对齐，前端先拦截超长输入 -->
        <el-form-item label="类型名称" prop="type_name">
          <el-input v-model="form.type_name" placeholder="请输入类型名称" maxlength="100" />
        </el-form-item>
        <!-- 排序：数值越小越靠前；:min=0/:max=9999 限定合法范围，避免负数或超大值打乱列表顺序 -->
        <el-form-item label="排序" prop="sort">
          <el-input-number v-model="form.sort" :min="0" :max="9999" />
        </el-form-item>
        <!-- 状态：开关与列表内的开关取值保持一致（1 启用 / 0 停用），便于一眼对照 -->
        <el-form-item label="状态" prop="status">
          <el-switch v-model="form.status" :active-value="1" :inactive-value="0" active-text="启用" inactive-text="停用" />
        </el-form-item>
        <!-- 备注：可选说明字段，2 行文本域足够填写用途/适用范围等补充信息 -->
        <el-form-item label="备注" prop="remark">
          <el-input v-model="form.remark" type="textarea" :rows="2" placeholder="请输入备注" />
        </el-form-item>
      </el-form>
      <!-- 底部按钮：取消直接关闭；确定按钮 loading=saving，防止重复提交产生重复类型 -->
      <template #footer>
        <el-button @click="dialogVisible=false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitForm">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
// 组合式 API：ref 用于原始值/数组，reactive 用于对象（用 Object.assign 就地覆盖以保持响应式引用）
import { ref, reactive, onMounted } from 'vue'
// ElMessage 做成功提示；ElMessageBox 做删除前的二次确认（本页没有状态流转按钮，仅删除是不可逆操作）
import { ElMessage, ElMessageBox } from 'element-plus'
// 图标以组件对象传入 :icon
import { Search, Refresh, Plus } from '@element-plus/icons-vue'
// 统一请求实例：内置 baseURL=/api、token 注入、统一错误提示与 401 跳登录
import request from '@/utils/request'

// 列表加载态：绑定 el-table 的 v-loading，避免请求期间重复操作
const loading = ref(false)
// 当前页数据：请求成功后整体替换；行对象直接参与 el-switch 双向绑定，故不能冻结
const rows = ref([])
// 总条数：供分页器 total 与页头"共 N 条"使用
const total = ref(0)
// 表单提交中标记：控制确定按钮 loading，防止重复提交生成重复类型
const saving = ref(false)
// 新建/编辑弹窗显隐
const dialogVisible = ref(false)
// 弹窗标题：区分"新建类型"与"编辑类型"两种模式
const dialogTitle = ref('新建类型')
// 表单实例：submitForm 里调用 validate() 触发统一校验
const formRef = ref()

// 查询条件默认值：抽成常量便于重置时整体回填；status 为 null 表示"全部"
const query_orig = { page: 1, page_size: 10, type_name: '', status: null }
// 响应式查询对象：分页组件 v-model 直接改写 page/page_size，必须用 reactive
const query = reactive({ ...query_orig })

// 表单默认值：id=null 表示新建；sort=0 让它默认排在最前，status=1 默认启用（新建即可被工单选到）
const form_orig = { id: null, type_name: '', sort: 0, status: 1, remark: '' }
// 响应式表单对象：编辑时 Object.assign(form, form_orig, row)，避免替换对象导致绑定失效
const form = reactive({ ...form_orig })

// 校验规则：只有类型名称必填，blur 时校验；sort/status 有默认值，remark 本就是可选字段
const rules = { type_name: [{ required: true, message: '请输入类型名称', trigger: 'blur' }] }

// 接口路径集中映射：/wo/type 前缀只在这里出现一次，避免各函数散落硬编码
// 列表/新增/更新/删除四个动作共用同一份基址，便于后续统一调整
function apiUrl(action) {
  const base = '/wo/type'
  return { list: base + '/list', create: base + '/create', update: base + '/update', delete: base + '/delete' }[action]
}

// 拉取列表：query 为 reactive 对象，axios 会按当前值序列化，无需手动拆解
// 错误不在此 catch：request 拦截器统一提示并 reject，这里只负责 finally 复位 loading
async function fetchList() {
  loading.value = true
  try {
    const res = await request.get(apiUrl('list'), { params: query })
    rows.value = res.data.list || []
    total.value = res.data.total || 0
  } finally { loading.value = false }
}
// 查询：先回到第 1 页，避免新条件落在越界页导致空列表
function handleSearch() { query.page = 1; fetchList() }
// 重置：回填默认条件后复用查询逻辑
function handleReset() { Object.assign(query, query_orig); handleSearch() }

// 新建：回填默认值清空上次输入，再设置标题并打开弹窗（Object.assign 保持 form 的响应式引用）
function openCreate() { Object.assign(form, form_orig); dialogTitle.value = '新建类型'; dialogVisible.value = true }
// 编辑：先铺默认值再覆盖行数据，行里缺字段时仍有合法初值
function openEdit(row) { Object.assign(form, form_orig, row); dialogTitle.value = '编辑类型'; dialogVisible.value = true }

// 提交表单：validate() 失败会 reject 并中止，避免带非法数据请求
// 按 form.id 区分新建/编辑；编辑时剥离 id 走路径参数，请求体不重复携带主键
async function submitForm() {
  await formRef.value.validate()
  saving.value = true
  try {
    if (form.id) {
      const { id, ...data } = form
      await request.put(`${apiUrl('update')}/${id}`, data); ElMessage.success('更新成功')
    } else {
      await request.post(apiUrl('create'), form); ElMessage.success('新建成功')
    }
    dialogVisible.value = false; fetchList()
  } finally { saving.value = false }
}

// 列表内就地表更：el-switch 已先行改动 row.status，这里只提交 status 做局部更新
// 失败时把开关回滚到相反值，保证界面与后端状态一致（错误提示由 request 拦截器统一弹出）
async function handleStatusChange(row) {
  try {
    await request.put(`${apiUrl('update')}/${row.id}`, { status: row.status })
    ElMessage.success(row.status === 1 ? '已启用' : '已停用')
  } catch { row.status = row.status === 1 ? 0 : 1 }
}

// 删除类型：不可逆操作，必须先二次确认；后端按 ids 数组接收，这里只传当前行
// 若该类型已被工单引用，是否允许删除由后端返回错误，前端不做预判
async function handleDelete(row) {
  await ElMessageBox.confirm(`确定删除类型「${row.type_name}」？`, '提示', { type: 'warning' })
  await request.delete(apiUrl('delete'), { data: { ids: [row.id] } })
  ElMessage.success('删除成功'); fetchList()
}

// 首次挂载：加载类型列表；本页无其它字典依赖，单个请求即可
onMounted(fetchList)
</script>
