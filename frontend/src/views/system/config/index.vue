<template>
  <!-- 参数配置页：维护系统运行参数（键值对），供后端读取站点标题等运行时配置。
       职责：参数的分页查询、按名称/键名过滤、单条新增/编辑/删除与批量删除。
       依赖：utils/request 统一请求、store/auth 的权限指令、Element Plus 表格与弹窗。 -->
  <div class="app-container">
    <!-- 页面头部：标题 + 副标题，保持系统页统一的头部结构 -->
    <div class="page-header">
      <div class="page-title-wrap">
        <h2>参数配置</h2>
        <div class="sub">系统运行参数维护</div>
      </div>
    </div>
    <!-- 查询栏：按参数名称（可读名）与参数键名（程序取值用的 key）过滤 -->
    <el-card shadow="never" class="search-card">
      <!-- inline 横向排列；@submit.prevent 阻止回车触发原生表单提交 -->
      <el-form inline @submit.prevent>
        <!-- 参数名称：模糊查询条件，回车即查询 -->
        <el-form-item label="参数名称">
          <el-input v-model="query.config_name" placeholder="请输入参数名称" clearable style="width: 180px" @keyup.enter="handleSearch" />
        </el-form-item>
        <!-- 参数键名：精确/模糊查询条件，键名是后端读取配置的标识 -->
        <el-form-item label="参数键名">
          <el-input v-model="query.config_key" placeholder="请输入参数键名" clearable style="width: 180px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item>
          <!-- 查询：handleSearch 会先把页码归 1 再请求，避免停留在越界页 -->
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <!-- 重置：清空两个条件后重新查询 -->
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 参数列表卡片：工具栏 + 表格 + 分页 -->
    <el-card shadow="never" class="table-card">
      <!-- 工具栏：新增、批量删除；批量删除在未勾选时禁用，避免无效点击 -->
      <div class="toolbar">
        <el-button v-perm="'system:config:create'" type="primary" :icon="Plus" @click="openCreate">新增</el-button>
        <el-button v-perm="'system:config:delete'" type="danger" plain :icon="Delete" :disabled="!selection.length" @click="handleBatchDelete">批量删除</el-button>
      </div>

      <!-- 参数表格：selection-change 回写已勾选行，为批量删除提供数据；stripe 斑马纹提升可读性 -->
      <el-table stripe empty-text="暂无数据" v-loading="loading" :data="list" @selection-change="onSelectionChange">
        <!-- 序号列：按当前页渲染顺序递增 -->
        <el-table-column type="index" label="序号" width="70" align="center" />
        <!-- 多选列：仅用于批量删除，不参与其他业务 -->
        <el-table-column type="selection" width="50" />
        <!-- 参数名称：展示用名称，最小宽度由内容自适应 -->
        <el-table-column label="参数名称" prop="config_name" min-width="150" show-overflow-tooltip />
        <!-- 参数键名：后端读取配置的 key，通常为 sys.xxx 形式 -->
        <el-table-column label="参数键名" prop="config_key" min-width="160" show-overflow-tooltip />
        <!-- 参数键值：实际配置内容，可能较长，超长时 tooltip 展示 -->
        <el-table-column label="参数键值" prop="config_value" min-width="140" show-overflow-tooltip />
        <!-- 备注：选填说明，空值用 '-' 占位 -->
        <el-table-column label="备注" prop="remark" min-width="140" show-overflow-tooltip>
          <template #default="{ row }">{{ row.remark || '-' }}</template>
        </el-table-column>
        <!-- 创建时间：后端已格式化，前端直接展示 -->
        <el-table-column label="创建时间" prop="create_time" width="170" />
        <!-- 操作列：固定在右侧，编辑/删除均受权限指令控制 -->
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <!-- 编辑：回填表单后打开弹窗 -->
            <el-button v-perm="'system:config:update'" link type="primary" @click="openEdit(row)">编辑</el-button>
            <!-- 删除：二次确认后删除单条 -->
            <el-button v-perm="'system:config:delete'" link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页条：页大小变化时重置到第一页；翻页时保持当前页大小 -->
      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="fetchList"
        />
      </div>
    </el-card>

    <!-- 新增/编辑弹窗：共用同一表单，标题与提交方式由 form.id 决定；destroy-on-close 清除旧校验状态 -->
    <el-dialog v-model="formVisible" :title="form.id ? '编辑参数' : '新增参数'" width="520px" destroy-on-close>
      <!-- 参数表单：三个业务字段均必填（键名/键值是后端实际使用的配置项），备注选填 -->
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <!-- 参数名称：可读名称，必填 -->
        <el-form-item label="参数名称" prop="config_name">
          <el-input v-model.trim="form.config_name" placeholder="如 系统标题" maxlength="50" />
        </el-form-item>
        <!-- 参数键名：后端读取配置用的 key，必填；代码里通常以 sys.xxx 形式引用，改名需谨慎 -->
        <el-form-item label="参数键名" prop="config_key">
          <el-input v-model.trim="form.config_key" placeholder="如 sys.site.title" maxlength="50" />
        </el-form-item>
        <!-- 参数键值：实际内容，用多行文本支持较长的配置（如 JSON 串），限制 500 字 -->
        <el-form-item label="参数键值" prop="config_value">
          <el-input v-model="form.config_value" type="textarea" :rows="3" placeholder="请输入参数键值" maxlength="500" />
        </el-form-item>
        <!-- 备注：选填说明，限制 200 字 -->
        <el-form-item label="备注" prop="remark">
          <el-input v-model="form.remark" type="textarea" :rows="3" maxlength="200" />
        </el-form-item>
      </el-form>
      <!-- 底部按钮：取消仅关闭弹窗，确定走保存并带 loading -->
      <template #footer>
        <el-button @click="formVisible = false">取 消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">确 定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
// 组合式 API：ref 管理列表/分页/加载态，reactive 管理查询条件与表单模型
import { onMounted, reactive, ref } from 'vue'
// 消息提示与确认框：保存/删除结果反馈与二次确认
import { ElMessage, ElMessageBox } from 'element-plus'
// 图标按需引入：查询、重置、新增、批量删除
import { Search, Refresh, Plus, Delete } from '@element-plus/icons-vue'
// 统一请求实例：封装 baseURL、token、错误提示与 401 跳转
import request from '@/utils/request'

// 列表加载态：驱动表格 v-loading
const loading = ref(false)
// 保存中状态：驱动弹窗确定按钮 loading，防止重复提交
const saving = ref(false)
// 参数列表数据：当前页记录
const list = ref([])
// 参数总数：分页组件据此计算页数
const total = ref(0)
// 当前页码：与 v-model:current-page 双向绑定
const page = ref(1)
// 每页条数：与 page-sizes 选项对应
const pageSize = ref(10)
// 查询条件：键名与后端接口参数一致，请求时整体展开
const query = reactive({ config_name: '', config_key: '' })
// 已勾选行：批量删除的数据来源，空数组时按钮禁用
const selection = ref([])

// ---------- 列表 ----------
// 拉取参数列表：分页参数 + 查询条件；loading 在 finally 中收起，失败也能解除遮罩
async function fetchList() {
  loading.value = true
  try {
    const res = await request.get('/system/config/list', {
      params: { page: page.value, page_size: pageSize.value, ...query }
    })
    // 后端约定 data = { list, total }
    list.value = res.data.list || []
    total.value = res.data.total || 0
  } finally {
    loading.value = false
  }
}

// 条件查询：先重置到第一页，避免新条件下页码越界
function handleSearch() {
  page.value = 1
  fetchList()
}

// 重置查询：清空名称与键名后复用查询逻辑
function handleReset() {
  query.config_name = ''
  query.config_key = ''
  handleSearch()
}

// 每页条数变化：页码回到第一页再请求，保证展示的是新分页下的首屏
function handleSizeChange() {
  page.value = 1
  fetchList()
}

// 表格勾选变化：把当前选中行写回 selection，供批量删除使用
function onSelectionChange(rows) {
  selection.value = rows
}

// ---------- 新增/编辑 ----------
// 弹窗显隐：新增与编辑共用
const formVisible = ref(false)
// 表单实例：保存前调用 validate()
const formRef = ref()
// 表单模型：id 为 null 表示新增；其余字段与后端参数接口一一对应
const form = reactive({
  id: null,
  config_name: '',
  config_key: '',
  config_value: '',
  remark: ''
})

// 校验规则：名称、键名、键值均必填，备注选填
const rules = {
  config_name: [{ required: true, message: '请输入参数名称', trigger: 'blur' }],
  config_key: [{ required: true, message: '请输入参数键名', trigger: 'blur' }],
  config_value: [{ required: true, message: '请输入参数键值', trigger: 'blur' }]
}

// 打开新增弹窗：逐字段重置，避免上一次编辑值残留
function openCreate() {
  form.id = null
  form.config_name = ''
  form.config_key = ''
  form.config_value = ''
  form.remark = ''
  formVisible.value = true
}

// 打开编辑弹窗：把当前行回填到表单；备注空值转空串以适配 textarea
function openEdit(row) {
  form.id = row.id
  form.config_name = row.config_name
  form.config_key = row.config_key
  form.config_value = row.config_value
  form.remark = row.remark || ''
  formVisible.value = true
}

// 保存参数：校验通过后按 form.id 判断新增/修改；payload 显式挑选业务字段，id 走路径参数
async function handleSave() {
  await formRef.value.validate()
  saving.value = true
  try {
    const payload = {
      config_key: form.config_key,
      config_value: form.config_value,
      config_name: form.config_name,
      remark: form.remark
    }
    if (form.id) {
      // 编辑：PUT /system/config/update/{id}
      await request.put(`/system/config/update/${form.id}`, payload)
      ElMessage.success('修改成功')
    } else {
      // 新增：POST /system/config/create
      await request.post('/system/config/create', payload)
      ElMessage.success('新增成功')
    }
    formVisible.value = false
    // 保存后刷新列表，保持当前分页条件
    fetchList()
  } finally {
    // 无论成功失败都解除确定按钮 loading
    saving.value = false
  }
}

// ---------- 删除 ----------
// 单条删除：先二次确认（用户取消时 confirm 会 reject 并中断后续请求），再按 ids 数组提交删除
async function handleDelete(row) {
  await ElMessageBox.confirm(`确定删除参数「${row.config_name}」吗？`, '提示', { type: 'warning' })
  await request.delete('/system/config/delete', { data: { ids: [row.id] } })
  ElMessage.success('删除成功')
  fetchList()
}

// 批量删除：确认文案带上选中数量；把 selection 映射成 id 数组提交，删除后刷新列表
async function handleBatchDelete() {
  await ElMessageBox.confirm(`确定删除选中的 ${selection.value.length} 个参数吗？`, '提示', { type: 'warning' })
  await request.delete('/system/config/delete', { data: { ids: selection.value.map(r => r.id) } })
  ElMessage.success('删除成功')
  fetchList()
}

// 页面挂载后加载第一页参数数据
onMounted(fetchList)
</script>
