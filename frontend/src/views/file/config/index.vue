<!--
  文件级说明：
  职责：附件模块的上传配置页。以键值对形式维护 upload（允许上传的类型/大小等）、preview（预览策略）、
        storage（存储介质）三类配置，支持查询、新增、编辑、单条与批量删除。
  依赖：@/utils/request（/file/config/list、/create、/update/{id}、/delete）、Element Plus 组件与图标、
        全局 v-perm 权限指令。
  被谁使用：由后端菜单配置 component='file/config/index' 生成动态路由后加载。
  说明：配置值以字符串存储，按配置键由后端在实际上传/预览/存储时解析，前端只负责录入。
-->
<template>
  <!-- 页面根容器：复用全局内边距与背景 -->
  <div class="app-container">
    <!-- 页头：标题与当前配置总数 -->
    <div class="page-header">
      <div class="page-title-wrap">
        <!-- 页面标题 -->
        <h2>上传配置</h2>
        <!-- 副标题：说明本页维护上传/预览/存储三类配置，并展示总条数 -->
        <div class="sub">上传/预览配置 · 共 {{ total }} 条</div>
      </div>
    </div>
    <!-- 查询卡片：shadow=never 保持扁平风格 -->
    <el-card shadow="never" class="search-card">
      <!-- 查询表单：inline 横向；@submit.prevent 阻止默认提交刷新页面 -->
      <el-form :model="query" inline @submit.prevent>
        <!-- 配置键：按 key 精确/模糊查询（如 max_size、allow_ext） -->
        <el-form-item label="配置键">
          <!-- 回车即查询；clearable 一键清空 -->
          <el-input v-model="query.config_key" placeholder="请输入配置键" clearable style="width: 160px" @keyup.enter="handleSearch" />
        </el-form-item>
        <!-- 配置类型：按配置用途分类筛选 -->
        <el-form-item label="配置类型">
          <!-- 下拉筛选，clearable 后为空表示全部类型 -->
          <el-select v-model="query.config_type" placeholder="全部" clearable style="width: 140px">
            <!-- 上传相关配置：限制大小、扩展名、保存目录等 -->
            <el-option label="上传" value="upload" />
            <!-- 预览相关配置：是否允许预览、预览地址有效期等 -->
            <el-option label="预览" value="preview" />
            <!-- 存储相关配置：默认存储介质、各云端存储参数等 -->
            <el-option label="存储" value="storage" />
          </el-select>
        </el-form-item>
        <!-- 查询/重置按钮 -->
        <el-form-item>
          <!-- 查询：回到第 1 页并按条件请求 -->
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <!-- 重置：恢复初始条件后重新查询 -->
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 表格卡片：工具栏 + 配置列表 + 分页 -->
    <el-card shadow="never" class="table-card">
      <!-- 卡片头部插槽：新增与批量删除 -->
      <template #header>
        <div class="card-header">
          <div class="card-actions">
            <!-- 新增配置：受 file:create 控制，打开空白表单弹窗 -->
            <el-button v-perm="'file:create'" type="primary" :icon="Plus" @click="openCreate">新增</el-button>
            <!-- 批量删除：未勾选时禁用；plain 弱化危险操作视觉 -->
            <el-button v-perm="'file:delete'" type="danger" plain :icon="Delete" :disabled="!selection.length" @click="handleBatchDelete">批量删除</el-button>
          </div>
        </div>
      </template>
      <!-- 配置表格：stripe 斑马纹；v-loading 遮罩；勾选变化同步到 selection -->
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据" @selection-change="onSelectionChange">
        <!-- 序号列：当前页编号 -->
        <el-table-column type="index" label="序号" width="70" align="center" />
        <!-- 勾选列：批量删除依赖它收集选中行 -->
        <el-table-column type="selection" width="50" />
        <!-- 配置键：程序读取配置时使用的唯一 key（如 max_size/allow_ext） -->
        <el-table-column label="配置键" prop="config_key" min-width="140" show-overflow-tooltip />
        <!-- 配置名称：给管理员看的中文说明，避免只看到英文键 -->
        <el-table-column label="配置名称" prop="config_name" min-width="160" show-overflow-tooltip />
        <!-- 配置值：具体取值，可能是数字、JSON、逗号分隔列表等，后端按 key 解析 -->
        <el-table-column label="配置值" prop="config_value" min-width="200" show-overflow-tooltip />
        <!-- 配置类型：用不同颜色的标签区分 upload/preview/storage；未知类型原样展示 -->
        <el-table-column label="配置类型" prop="config_type" width="100">
          <template #default="{ row }">
            <!-- 上传类配置：默认主色标签 -->
            <el-tag v-if="row.config_type==='upload'" size="small">上传</el-tag>
            <!-- 预览类配置：绿色 success 标签 -->
            <el-tag v-else-if="row.config_type==='preview'" size="small" type="success">预览</el-tag>
            <!-- 存储类配置：橙色 warning 标签 -->
            <el-tag v-else-if="row.config_type==='storage'" size="small" type="warning">存储</el-tag>
            <!-- 兜底：后端出现新类型时直接显示原值，避免空白 -->
            <span v-else>{{ row.config_type }}</span>
          </template>
        </el-table-column>
        <!-- 备注：说明该配置的作用与取值格式 -->
        <el-table-column label="备注" prop="remark" min-width="160" show-overflow-tooltip />
        <!-- 创建时间：配置录入时间 -->
        <el-table-column label="创建时间" prop="create_time" width="170" />
        <!-- 操作列：固定在右侧 -->
        <el-table-column label="操作" width="180" fixed="right" class-name="op-col">
          <template #default="{ row }">
            <!-- 编辑：把当前行数据填入表单后弹窗；受 file:update 控制 -->
            <el-button v-perm="'file:update'" link type="primary" @click="openEdit(row)">编辑</el-button>
            <!-- 删除：二次确认后删除该条配置；受 file:delete 控制 -->
            <el-button v-perm="'file:delete'" link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <!-- 分页容器：页码/页大小双向绑定 query，变化时统一重新请求 -->
      <div class="pagination-wrap">
        <el-pagination background layout="total, sizes, prev, pager, next, jumper"
          :total="total" v-model:current-page="query.page" v-model:page-size="query.page_size"
          :page-sizes="[10, 20, 50, 100]" @change="fetchList" />
      </div>
    </el-card>

    <!-- 新增/编辑弹窗：title 随操作变化；destroy-on-close 关闭销毁表单，避免下次打开残留；
         close-on-click-modal=false 防止误点空白关闭而丢失编辑内容 -->
    <el-dialog :title="dialogTitle" v-model="dialogVisible" width="640px" :close-on-click-modal="false" destroy-on-close>
      <!-- 配置表单：formRef 供提交前校验；rules 控制配置键/名称/类型的必填 -->
      <el-form ref="formRef" :model="form" :rules="rules" label-width="110px">
        <!-- 配置键：后端实际读取的 key，必须稳定且唯一，长度与后端字段一致 -->
        <el-form-item label="配置键" prop="config_key">
          <!-- 必填；maxlength=64 防止超出数据库字段长度 -->
          <el-input v-model="form.config_key" placeholder="请输入配置键" maxlength="64" />
        </el-form-item>
        <!-- 配置名称：面向管理员的中文描述 -->
        <el-form-item label="配置名称" prop="config_name">
          <!-- 必填；maxlength=100 -->
          <el-input v-model="form.config_name" placeholder="请输入配置名称" maxlength="100" />
        </el-form-item>
        <!-- 配置值：字符串形式存储，数字/布尔/JSON 都可直接粘贴，由后端按 key 解释 -->
        <el-form-item label="配置值" prop="config_value">
          <!-- 文本域 3 行，便于填写较长配置（如扩展名列表、云端参数） -->
          <el-input v-model="form.config_value" type="textarea" :rows="3" placeholder="请输入配置值" />
        </el-form-item>
        <!-- 配置类型：决定该配置参与哪个环节（上传校验/预览策略/存储介质） -->
        <el-form-item label="配置类型" prop="config_type">
          <!-- 下拉占满整行，保证与文本域视觉宽度一致 -->
          <el-select v-model="form.config_type" placeholder="请选择配置类型" style="width:100%">
            <!-- 上传类 -->
            <el-option label="上传" value="upload" />
            <!-- 预览类 -->
            <el-option label="预览" value="preview" />
            <!-- 存储类 -->
            <el-option label="存储" value="storage" />
          </el-select>
        </el-form-item>
        <!-- 备注：补充说明取值格式或生效范围，非必填 -->
        <el-form-item label="备注" prop="remark">
          <!-- 2 行文本域即可满足说明用途 -->
          <el-input v-model="form.remark" type="textarea" :rows="2" placeholder="请输入备注" />
        </el-form-item>
      </el-form>
      <!-- 底部操作：取消直接关闭；确定触发校验与提交，请求中显示 loading 防重复提交 -->
      <template #footer>
        <el-button @click="dialogVisible=false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitForm">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
// Vue 基础能力：ref 维护加载/列表/弹窗等状态；reactive 维护查询与表单；onMounted 首次加载
import { ref, reactive, onMounted } from 'vue'
// Element Plus 消息提示与确认框：新增/更新/删除反馈、删除前确认
import { ElMessage, ElMessageBox } from 'element-plus'
// 查询/重置/新增/删除按钮图标
import { Search, Refresh, Plus, Delete } from '@element-plus/icons-vue'
// 统一请求实例：自动鉴权、解包响应体并统一报错
import request from '@/utils/request'

// 列表加载态：控制表格遮罩
const loading = ref(false)
// 当前页配置数据
const rows = ref([])
// 配置总数，供分页器与页头统计
const total = ref(0)
// 当前勾选行，批量删除依赖它
const selection = ref([])
// 提交中状态：控制确定按钮 loading，防止重复提交
const saving = ref(false)
// 弹窗显隐
const dialogVisible = ref(false)
// 弹窗标题：新增与编辑复用同一个弹窗，通过标题区分当前模式
const dialogTitle = ref('新增')
// 表单实例：submitForm 中调用 validate() 做必填校验
const formRef = ref()

// 查询条件初始值：config_key 为空、config_type 为 null 表示不筛选
const query_orig = { page: 1, page_size: 10, config_key: '', config_type: null }
// 响应式查询对象：浅拷贝初始值，便于重置时整体还原
const query = reactive({ ...query_orig })

// 表单初始值：新增时清空；编辑时用行数据覆盖；id 为空代表新增
const form_orig = {
  id: null, config_key: '', config_name: '', config_value: '', config_type: '', remark: ''
}
// 响应式表单对象：与弹窗表单双向绑定
const form = reactive({ ...form_orig })

// 表单校验规则：配置键/名称/类型必填；下拉选择用 change 触发，输入框用 blur 触发
const rules = {
  config_key: [{ required: true, message: '请输入配置键', trigger: 'blur' }],
  config_name: [{ required: true, message: '请输入配置名称', trigger: 'blur' }],
  config_type: [{ required: true, message: '请选择配置类型', trigger: 'change' }]
}

// 按动作名映射接口路径，统一维护 /file/config 前缀
// 注意：更新接口是 /file/config/update/{id}，调用方需再拼 id
function apiUrl(action) {
  const base = '/file/config'
  return {
    list: base + '/list',
    create: base + '/create',
    update: base + '/update',
    delete: base + '/delete'
  }[action]
}

// 拉取配置列表：query 同时携带分页参数与筛选条件
async function fetchList() {
  loading.value = true
  try {
    const res = await request.get(apiUrl('list'), { params: query })
    // 兜底空数组/0，保证表格与分页组件拿到稳定数据
    rows.value = res.data.list || []
    total.value = res.data.total || 0
  } finally {
    // 请求结束关闭遮罩
    loading.value = false
  }
}

// 查询：先回到第 1 页再请求
function handleSearch() { query.page = 1; fetchList() }
// 重置：还原查询条件后重新查询
function handleReset() { Object.assign(query, query_orig); handleSearch() }
// 勾选变化：同步选中行，批量删除按钮的禁用状态依赖它
function onSelectionChange(r) { selection.value = r }

// 打开新增弹窗：先恢复表单初始值（id=null 表示新增），再设置标题并显示
function openCreate() {
  Object.assign(form, form_orig)
  dialogTitle.value = '新增配置'
  dialogVisible.value = true
}

// 打开编辑弹窗：先恢复初始值，再用当前行覆盖，避免上一次新增/编辑的残留字段
function openEdit(row) {
  Object.assign(form, form_orig, row)
  dialogTitle.value = '编辑配置'
  dialogVisible.value = true
}

// 提交表单：有 id 走更新，无 id 走新增；成功后关闭弹窗并刷新列表
async function submitForm() {
  // 校验不通过会 reject，函数在此中断
  await formRef.value.validate()
  saving.value = true
  try {
    if (form.id) {
      // 更新路径需要 id，提交体里去掉 id 避免重复传参
      const { id, ...data } = form
      await request.put(`${apiUrl('update')}/${id}`, data)
      ElMessage.success('更新成功')
    } else {
      // 新增直接把表单对象作为请求体
      await request.post(apiUrl('create'), form)
      ElMessage.success('新增成功')
    }
    dialogVisible.value = false
    // 新增/更新都会改变列表，刷新当前页
    fetchList()
  } finally {
    // 成功或失败都恢复按钮状态
    saving.value = false
  }
}

// 单条删除：二次确认后提交 id 数组
async function handleDelete(row) {
  await ElMessageBox.confirm('确定删除该配置？', '提示', { type: 'warning' })
  await request.delete(apiUrl('delete'), { data: { ids: [row.id] } })
  ElMessage.success('删除成功')
  fetchList()
}

// 批量删除：汇总勾选行 id 后一次提交
async function handleBatchDelete() {
  await ElMessageBox.confirm(`确定删除选中的 ${selection.value.length} 条配置？`, '提示', { type: 'warning' })
  await request.delete(apiUrl('delete'), { data: { ids: selection.value.map(r => r.id) } })
  ElMessage.success('批量删除成功')
  fetchList()
}

// 页面挂载后加载第一页配置
onMounted(fetchList)
</script>
