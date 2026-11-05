<template>
<!-- ============================================================
     文件：学生信息表管理页（views/student/index.vue）
     职责：学生数据的查询、分页列表、新增/编辑、单条/批量删除、
           Excel 导入（含模板下载）与导出。
     依赖：@/api/student（后端 CRUD/导入导出接口）、@/utils/dict（性别字典缓存）、
           utils/request（由 api 层内部使用）、v-perm 权限指令。
     被谁使用：由后端菜单配置驱动，作为动态路由页面挂载在 layout 下。
     主题：颜色使用 app 系列主题变量，表格与弹窗由 Element Plus 主题联动。
     ============================================================ -->
  <div class="app-container">
    <!-- 页面头部：标题 + 右侧总数说明（total 来自列表接口返回值） -->
    <div class="page-header">
      <div class="page-title-wrap">
        <h2>学生信息表</h2>
        <div class="sub">数据维护 · 共 {{ total }} 条记录</div>
      </div>
    </div>
    <!-- 查询区域：所有条件都以 inline 形式排布，支持回车直接查询 -->
    <el-card shadow="never" class="search-card">
      <!-- :model 绑定 query；@submit.prevent 阻止表单默认提交行为（避免刷新页面） -->
      <el-form :model="query" inline @submit.prevent>
        <!-- 学生姓名：模糊查询条件，回车触发查询 -->
        <el-form-item label="学生姓名">
          <el-input v-model="query.name" placeholder="请输入学生姓名" clearable style="width: 180px" @keyup.enter="handleQuery" />
        </el-form-item>
        <!-- 年龄：此处用文本框而非数字框，便于后端按字符串模糊匹配 -->
        <el-form-item label="年龄">
          <el-input v-model="query.age" placeholder="请输入年龄" clearable style="width: 180px" @keyup.enter="handleQuery" />
        </el-form-item>
        <!-- 性别：下拉选项来自数据字典 sys_user_sex，
             dictList 返回 [{ dict_value, dict_label }]，value 存字典值 -->
        <el-form-item label="性别（字典sys_user_sex）">
          <el-select v-model="query.gender" placeholder="请选择" clearable style="width: 180px">
            <el-option v-for="d in dictList('sys_user_sex')" :key="d.dict_value" :label="d.dict_label" :value="d.dict_value" />
          </el-select>
        </el-form-item>
        <!-- 手机号：模糊查询 -->
        <el-form-item label="手机号">
          <el-input v-model="query.phone" placeholder="请输入手机号" clearable style="width: 180px" @keyup.enter="handleQuery" />
        </el-form-item>
        <!-- 邮箱：模糊查询 -->
        <el-form-item label="邮箱">
          <el-input v-model="query.email" placeholder="请输入邮箱" clearable style="width: 180px" @keyup.enter="handleQuery" />
        </el-form-item>
        <!-- 入学日期：当前仅支持文本框输入（后端按字符串匹配），未使用日期选择器 -->
        <el-form-item label="入学日期">
          <el-input v-model="query.enroll_date" placeholder="请输入入学日期" clearable style="width: 180px" @keyup.enter="handleQuery" />
        </el-form-item>
        <!-- 总分：文本框输入，便于支持区间/模糊等后端匹配方式 -->
        <el-form-item label="总分">
          <el-input v-model="query.score" placeholder="请输入总分" clearable style="width: 180px" @keyup.enter="handleQuery" />
        </el-form-item>
        <!-- 家庭住址：模糊查询 -->
        <el-form-item label="家庭住址">
          <el-input v-model="query.address" placeholder="请输入家庭住址" clearable style="width: 180px" @keyup.enter="handleQuery" />
        </el-form-item>
        <!-- 查询/重置按钮：查询会重置到第 1 页，重置会清空除分页外的所有条件 -->
        <el-form-item class="search-actions">
          <!-- 查询：图标 Search，点击调用 handleQuery -->
          <el-button type="primary" :icon="Search" @click="handleQuery">查询</el-button>
          <!-- 重置：图标 Refresh，点击调用 resetQuery -->
          <el-button :icon="Refresh" @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 数据表格卡片：工具条放在 header 插槽，表格与分页放在 body -->
    <el-card shadow="never" class="table-card">
      <!-- 卡片头部：左侧为操作按钮组 -->
      <template #header>
        <div class="card-header">
          <div class="card-actions">
            <!-- 新增：打开空白表单弹窗；v-perm 控制无权限用户不可见 -->
            <el-button v-perm="'student:create'" type="primary" :icon="Plus" @click="openCreate">新增</el-button>
            <!-- 导入：仅打开导入弹窗，真正的上传在弹窗内点击“开始导入”时发生 -->
            <el-button v-perm="'student:import'" type="success" plain :icon="Upload" @click="importVisible = true">导入</el-button>
            <!-- 导出：以当前查询条件导出 Excel（与左侧查询区共享 query） -->
            <el-button v-perm="'student:export'" type="warning" plain :icon="Download" @click="handleExport">导出</el-button>
            <!-- 批量删除：未勾选任何行时禁用，避免空提交 -->
            <el-button v-perm="'student:delete'" type="danger" plain :icon="Delete" :disabled="!selectedIds.length" @click="handleBatchDelete">批量删除</el-button>
          </div>
        </div>
      </template>
      <!-- 表格：加载态由 loading 控制；stripe 斑马纹；空数据文案自定义；
           selection-change 在勾选变化时同步 selectedIds -->
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据" @selection-change="onSelectionChange">
        <!-- 序号列：Type=index 由表格自动按当前页顺序生成（非后端字段） -->
        <el-table-column type="index" label="序号" width="70" align="center" />
        <!-- 复选框列：批量操作依赖它产出的选中行 -->
        <el-table-column type="selection" width="50" align="center" />
        <!-- 学生姓名：show-overflow-tooltip 内容过长时省略并悬浮显示全称 -->
        <el-table-column label="学生姓名" prop="name" align="center" show-overflow-tooltip />
        <!-- 年龄：直接展示后端字段 -->
        <el-table-column label="年龄" prop="age" align="center" show-overflow-tooltip />
        <!-- 性别：用自定义插槽，把字典值翻译成字典标签并渲染为彩色 Tag -->
        <el-table-column label="性别（字典sys_user_sex）" prop="gender" align="center">
          <template #default="scope">
            <!-- scope.row 为当前行数据；字典值 '0' 用 primary 样式，其余用 info，
                 dictLabel 负责把值转成中文标签 -->
            <el-tag :type="scope.row.gender === '0' ? 'primary' : 'info'">{{ dictLabel('sys_user_sex', scope.row.gender) }}</el-tag>
          </template>
        </el-table-column>
        <!-- 手机号 -->
        <el-table-column label="手机号" prop="phone" align="center" show-overflow-tooltip />
        <!-- 邮箱 -->
        <el-table-column label="邮箱" prop="email" align="center" show-overflow-tooltip />
        <!-- 入学日期（后端格式化后的字符串） -->
        <el-table-column label="入学日期" prop="enroll_date" align="center" show-overflow-tooltip />
        <!-- 总分 -->
        <el-table-column label="总分" prop="score" align="center" show-overflow-tooltip />
        <!-- 家庭住址：长文本同样省略显示 -->
        <el-table-column label="家庭住址" prop="address" align="center" show-overflow-tooltip />
        <!-- 操作列：fixed=right 固定在右侧，横向滚动时始终可见 -->
        <el-table-column label="操作" width="150" align="center" fixed="right">
          <template #default="scope">
            <!-- 编辑：把当前行合并进表单后打开弹窗（受 student:update 权限控制） -->
            <el-button v-perm="'student:update'" link type="primary" :icon="Edit" @click="handleEdit(scope.row)">编辑</el-button>
            <!-- 删除：单条删除，弹确认框后调用接口（受 student:delete 权限控制） -->
            <el-button v-perm="'student:delete'" link type="danger" :icon="Delete" @click="handleDelete(scope.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <!-- 分页区：双向绑定 query.page / query.page_size；
           @change 在页码或每页条数变化时重新拉取列表 -->
      <div class="pagination-wrap">
        <el-pagination background layout="total, sizes, prev, pager, next, jumper"
          :total="total" v-model:current-page="query.page" v-model:page-size="query.page_size"
          :page-sizes="[10, 20, 50, 100]" @change="getList" />
      </div>
    </el-card>
    <!-- 新增/编辑弹窗：标题按 form.id 判断是编辑还是新增；
         :close-on-click-modal=false 防止误点遮罩丢失填写内容；
         destroy-on-close 关闭后销毁表单，避免校验状态残留到下一次打开 -->
    <el-dialog :title="form.id ? '编辑学生信息表' : '新增学生信息表'" v-model="dialogVisible" width="640px" :close-on-click-modal="false" destroy-on-close>
      <!-- 弹窗表单：rules 目前只对 name 做必填校验；label-width 统一标签宽度 -->
      <el-form ref="formRef" :model="form" :rules="rules" label-width="110px" class="dialog-form">
        <!-- 学生姓名：唯一必填项，失焦时校验 -->
        <el-form-item label="学生姓名" prop="name">
          <el-input v-model="form.name" placeholder="请输入学生姓名" />
        </el-form-item>
        <!-- 年龄：数字输入框，min=0 禁止负数；提交时会把空串转成 null -->
        <el-form-item label="年龄" prop="age">
          <el-input-number v-model="form.age" :min="0" style="width: 100%" />
        </el-form-item>
        <!-- 性别：字典下拉，选项与查询区使用同一份缓存数据 -->
        <el-form-item label="性别（字典sys_user_sex）" prop="gender">
          <el-select v-model="form.gender" placeholder="请输入性别（字典sys_user_sex）" clearable style="width: 100%">
            <el-option v-for="d in dictList('sys_user_sex')" :key="d.dict_value" :label="d.dict_label" :value="d.dict_value" />
          </el-select>
        </el-form-item>
        <!-- 手机号：无额外格式校验，仅原样提交 -->
        <el-form-item label="手机号" prop="phone">
          <el-input v-model="form.phone" placeholder="请输入手机号" />
        </el-form-item>
        <!-- 邮箱：同样未做格式校验 -->
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" placeholder="请输入邮箱" />
        </el-form-item>
        <!-- 入学日期：日期时间选择器；value-format 保证绑定值为
             「YYYY-MM-DD HH:mm:ss」字符串，可直接提交给后端 -->
        <el-form-item label="入学日期" prop="enroll_date">
          <el-date-picker v-model="form.enroll_date" type="datetime" placeholder="请输入入学日期" value-format="YYYY-MM-DD HH:mm:ss" style="width: 100%" />
        </el-form-item>
        <!-- 总分：数字输入框，min=0 -->
        <el-form-item label="总分" prop="score">
          <el-input-number v-model="form.score" :min="0" style="width: 100%" />
        </el-form-item>
        <!-- 家庭住址：普通文本 -->
        <el-form-item label="家庭住址" prop="address">
          <el-input v-model="form.address" placeholder="请输入家庭住址" />
        </el-form-item>
      </el-form>
      <!-- 弹窗底部：取消仅关闭弹窗（不清空表单，下次打开会被覆盖）；
           确定按钮 loading 由 saving 控制，防止重复提交 -->
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitForm">确定</el-button>
      </template>
    </el-dialog>
    <!-- 导入弹窗：文件选择 + 模板下载 + 导入错误回显 -->
    <el-dialog title="导入学生信息表" v-model="importVisible" width="420px">
      <!-- 拖拽上传：auto-upload=false 表示只选文件不自动上传，
           由 submitImport 手动发请求；limit=1 一次只允许一个文件；
           file-list 绑定外部列表以便组件受控 -->
      <el-upload drag :auto-upload="false" :limit="1" accept=".xlsx,.xls" :on-change="onFileChange" :file-list="fileList">
        <el-icon size="40"><UploadFilled /></el-icon>
        <div>将 Excel 文件拖到此处，或点击选择</div>
      </el-upload>
      <!-- 模板下载入口：后端返回 xlsx 二进制，由 downloadTemplate 触发保存 -->
      <div class="mt12">
        <el-button link type="primary" @click="downloadTemplate">下载导入模板</el-button>
      </div>
      <!-- 错误提示：仅当后端返回逐行错误时显示；closable=false 避免用户误关后看不到原因 -->
      <el-alert v-if="importErrors.length" type="error" :closable="false" class="mt12">
        <div v-for="e in importErrors" :key="e"> {{ e }}</div>
      </el-alert>
      <!-- 导入弹窗底部：开始导入时按钮 loading，防止重复上传 -->
      <template #footer>
        <el-button @click="importVisible = false">取消</el-button>
        <el-button type="primary" :loading="importing" @click="submitImport">开始导入</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
// ============================================================
// 脚本说明：本页是标准 CRUD 列表页，数据流为
// query（查询条件+分页）→ getList() 拉取列表 → rows/total 渲染表格；
// 新增/编辑共用 form 与同一个弹窗，用 form.id 区分提交到哪个接口。
// 重置、删除、导入导出等操作均在此集中处理，接口调用统一走 @/api/student。
// ============================================================
// reactive 用于查询条件与表单对象（需要 v-model 双向绑定）；ref 用于标量/数组/组件实例
import { reactive, ref } from 'vue'
// ElMessage 做轻量结果提示；ElMessageBox 提供删除前的确认弹窗
import { ElMessage, ElMessageBox } from 'element-plus'
// 图标：上传占位、新增、编辑、删除、查询、重置、导入按钮、导出按钮
import { UploadFilled, Plus, Edit, Delete, Search, Refresh, Upload, Download } from '@element-plus/icons-vue'
// 学生模块的全部接口：增删改查、导出、导入、导入模板下载
import { createApi, deleteApi, exportApi, importApi, listApi, templateApi, updateApi } from '@/api/student'
// 字典工具：dictLabel 值转标签、dictList 取字典项、loadDicts 预热字典缓存
import { dictLabel, dictList, loadDicts } from '@/utils/dict'

// 组件初始化时即加载字典：页面渲染时 dictList('sys_user_sex') 需要已有缓存；
// 这里未 await，属于“先发请求、模板按空数组渲染”的现有做法
loadDicts()

// 表格加载态：控制 v-loading 遮罩
const loading = ref(false)
// 表单提交中标记：控制“确定”按钮 loading
const saving = ref(false)
// 表格数据源
const rows = ref([])
// 记录总数：既用于分页组件，也用于页面头部“共 N 条记录”
const total = ref(0)
// 当前勾选行 id 集合：批量删除的依据，也用于禁用按钮
const selectedIds = ref([])
// 新增/编辑弹窗显隐
const dialogVisible = ref(false)
// 弹窗表单实例：提交时调用 validate 触发校验
const formRef = ref()
// 导入弹窗显隐
const importVisible = ref(false)
// 导入请求中标记：控制导入按钮 loading
const importing = ref(false)
// 选中的原始 File 对象：提交导入时作为 FormData 的载荷
const importFile = ref(null)
// 后端返回的逐行错误信息列表，用于弹窗内回显
const importErrors = ref([])
// el-upload 的受控文件列表
const fileList = ref([])

// 查询条件与分页参数：page/page_size 会随分页组件双向绑定变化
const query = reactive({ page: 1, page_size: 10 })
// 以下逐项初始化为空串，保证后端收到的是“空条件”而不是 undefined
query.name = ''
query.age = ''
query.gender = ''
query.phone = ''
query.email = ''
query.enroll_date = ''
query.score = ''
query.address = ''

// 空白表单模板：id=null 表示新增；每次打开弹窗都先复制它，避免残留上次的数据
const emptyForm = { id: null }
emptyForm.name = ''
emptyForm.age = null
emptyForm.gender = ''
emptyForm.phone = ''
emptyForm.email = ''
emptyForm.enroll_date = ''
emptyForm.score = null
emptyForm.address = ''
// 实际参与编辑的表单对象：展开 emptyForm 得到独立副本，避免与模板共享引用
const form = reactive({ ...emptyForm })

// 校验规则：仅姓名必填；其余字段后端未要求，故不做前端校验
const rules = {
  name: [{ required: true, message: '请输入学生姓名', trigger: 'blur' }],
}

// 拉取列表：把 query 原样作为查询参数（含分页）提交，
// 接口返回 { list, total }，分别写入表格与总数
async function getList() {
  // 打开遮罩，防止用户看到旧数据产生误解
  loading.value = true
  try {
    const data = await listApi(query)
    // 列表数据直接替换（不做本地拼接，保证与后端分页一致）
    rows.value = data.list
    // 总数用于分页与头部统计
    total.value = data.total
  } finally {
    // 失败时也必须关闭遮罩（异常继续向上抛给拦截器处理）
    loading.value = false
  }
}

// 点击“查询”：条件变化后必须回到第 1 页，否则可能停留在超出范围的页码
function handleQuery() {
  query.page = 1
  getList()
}

// 点击“重置”：清空除分页外的全部查询条件，然后按空条件重新查询
function resetQuery() {
  // 遍历 query 的所有键，跳过 page/page_size 以保留每页条数设置
  Object.keys(query).forEach((key) => {
    if (!['page', 'page_size'].includes(key)) query[key] = ''
  })
  // 复用 handleQuery，同时重置页码为 1
  handleQuery()
}

// 表格勾选变化：把选中行的 id 收集成数组，
// 供批量删除使用，同时驱动按钮的 disabled 状态
function onSelectionChange(selection) {
  selectedIds.value = selection.map((item) => item.id)
}

// 新增：先用空白模板覆盖表单（含 id=null），再打开弹窗
function openCreate() {
  Object.assign(form, emptyForm)
  dialogVisible.value = true
}

// 编辑：先铺空白模板，再用当前行数据覆盖，
// 这样后端未返回的字段会保持默认值而不是残留上一次的内容
function handleEdit(row) {
  Object.assign(form, emptyForm, row)
  dialogVisible.value = true
}

// 提交表单：先校验，再按 form.id 判断新增或修改
function submitForm() {
  // 回调式 validate：valid=false 时直接返回，不发起请求
  formRef.value.validate(async (valid) => {
    if (!valid) return
    // 进入保存中状态，按钮显示 loading
    saving.value = true
    try {
      // 复制一份载荷，避免为了清洗数据而改动界面上的 form
      const payload = { ...form }
      // 数值/日期字段空串转 null，避免后端校验失败
      // 数字输入框清空后可能得到 ''，日期选择器同理，统一转 null
      if (payload.age === '') payload.age = null
      if (payload.enroll_date === '') payload.enroll_date = null
      if (payload.score === '') payload.score = null
      // 有 id 走更新，否则走新建
      if (form.id) {
        await updateApi(form.id, payload)
        ElMessage.success('修改成功')
      } else {
        await createApi(payload)
        ElMessage.success('新增成功')
      }
      // 成功后关闭弹窗并刷新列表（保持在当前页码）
      dialogVisible.value = false
      getList()
    } finally {
      // 无论成功失败都要解除 loading
      saving.value = false
    }
  })
}

// 单条删除：先弹确认框，确认后才调用删除接口；
// 接口约定接收 id 数组，因此这里包成 [row.id]
function handleDelete(row) {
  ElMessageBox.confirm('确认删除该条记录？', '提示', { type: 'warning' }).then(async () => {
    await deleteApi([row.id])
    ElMessage.success('删除成功')
    // 刷新列表；若删掉的是当前页最后一条，页码不会自动回退（现有行为）
    getList()
  })
}

// 批量删除：确认框文案里拼接当前选中数量；确认后一次性提交 id 数组
function handleBatchDelete() {
  ElMessageBox.confirm('确认删除选中的 %s 条记录？'.replace('%s', selectedIds.value.length), '提示', { type: 'warning' }).then(async () => {
    await deleteApi(selectedIds.value)
    ElMessage.success('删除成功')
    getList()
  })
}

// 导出：按当前查询条件请求 xlsx 二进制，
// 再用临时 <a> 触发浏览器下载（不新开窗口）
async function handleExport() {
  // api 层已设置 responseType=blob，返回的是 Blob 对象
  const blob = await exportApi(query)
  // 生成指向该 Blob 的临时 URL
  const url = URL.createObjectURL(blob)
  // 动态创建隐藏下载链接
  const link = document.createElement('a')
  link.href = url
  // 文件名固定为中文，便于用户识别
  link.download = '学生信息表.xlsx'
  // 模拟点击触发下载（无需插入 DOM 也能生效）
  link.click()
  // 释放临时 URL，避免内存泄漏
  URL.revokeObjectURL(url)
}

// 选择文件回调：el-upload 的 file 对象把原始 File 放在 raw 上，
// 这里只缓存 raw，真正的上传在 submitImport 中进行
function onFileChange(file) {
  importFile.value = file.raw
}

// 下载导入模板：与导出使用同一套 Blob + 临时链接方案
async function downloadTemplate() {
  const blob = await templateApi()
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  // 模板文件名与导入弹窗标题对应
  link.download = '学生信息表导入模板.xlsx'
  link.click()
  URL.revokeObjectURL(url)
}

// 执行导入：未选文件先给出警告；成功后提示条数，
// 若后端返回逐行错误则保留弹窗展示错误，否则关闭弹窗并刷新列表
async function submitImport() {
  // 前端兜底校验：避免空提交
  if (!importFile.value) {
    ElMessage.warning('请选择要导入的文件')
    return
  }
  importing.value = true
  // 每次导入前清空上一次的错误列表，避免旧信息干扰
  importErrors.value = []
  try {
    const result = await importApi(importFile.value)
    // 成功条数由后端返回
    ElMessage.success(`成功导入 ${result.success_count} 条`)
    // 有错误则留在弹窗中展示明细；无错误直接关闭弹窗
    if (result.errors && result.errors.length) importErrors.value = result.errors
    else importVisible.value = false
    // 无论是否有部分失败，都刷新列表以显示已入库的数据
    getList()
  } finally {
    importing.value = false
  }
}

// 组件 setup 阶段直接拉取一次列表：进入页面即有数据，
// 不依赖 onMounted，保证首屏渲染前请求已发出
getList()
</script>

<style scoped>
/* ============================================================
   样式区说明：本页只做少量局部样式覆盖，其余（查询卡片、表格、弹窗）
   由全局 Element Plus 主题与 layout 通用类提供，因此这里没有大面积换肤代码。
   ============================================================ */
/* 页面主标题：20px 加粗，使用主题主文字色，暗色下自动变亮 */
.page-title-wrap h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: var(--app-text-1);
  letter-spacing: 0.5px;
}
/* 标题下的副说明（共 N 条记录）：小号灰色；
   注意这里用的是固定色值 #8a94a6，未走主题变量，暗色模式下对比度偏低 */
.page-title-wrap .sub {
  margin-top: 6px;
  font-size: 12px;
  color: #8a94a6;
}
/* 表格卡片头部：左右两端对齐；当前只有左侧按钮组，
   预留 space-between 以便后续在右侧加入统计或搜索框 */
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
/* 操作按钮组：横向排列并留 10px 间距 */
.card-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}
/* 清除 Element Plus 默认的相邻按钮左外边距，
   避免与上面 gap 叠加导致间距翻倍 */
.card-actions .el-button + .el-button {
  margin-left: 0;
}
/* 弹窗表单：顶部留 4px，避免第一个输入框紧贴弹窗标题分隔线 */
.dialog-form {
  padding-top: 4px;
}
/* 通用下间距工具类：12px（当前模板未使用，保留供后续扩展） */
.mb12 { margin-bottom: 12px }
/* 通用上间距工具类：导入弹窗中模板下载与错误提示用它拉开距离 */
.mt12 { margin-top: 12px }
</style>