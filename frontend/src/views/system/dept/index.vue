<template>
  <!-- 部门管理页：用树形表格维护组织架构层级。
       职责：展示 /system/dept/tree 返回的部门树，提供新增（含新增下级）、编辑、删除、全部展开/折叠与刷新。
       依赖：utils/request 统一请求、store/auth 的权限判断、Element Plus 的表格与弹窗组件。 -->
  <div class="app-container">
    <!-- 页面头部：标题 + 副标题，与其他系统页保持统一的头部结构 -->
    <div class="page-header">
      <div class="page-title-wrap">
        <h2>部门管理</h2>
        <div class="sub">组织架构层级维护</div>
      </div>
    </div>
    <!-- 主体卡片：承载工具栏与树形表格；shadow=never 让卡片与页面背景保持扁平风格 -->
    <el-card shadow="never" class="table-card">
      <!-- 顶部工具栏：新增、展开/折叠、刷新，三个按钮按使用频率从左到右排列 -->
      <div class="toolbar">
        <!-- 新增顶级部门：不带参数调用 openCreate，parent_id 默认 0；
             用 v-perm 指令控制权限，无权限时按钮整体不渲染 -->
        <el-button v-perm="'system:dept:create'" type="primary" :icon="Plus" @click="openCreate()">新增</el-button>
        <!-- 全部展开/折叠：图标与文案随 expanded 取反切换，点击后由 toggleExpand 重建表格 -->
        <el-button plain :icon="expanded ? Minus : Expand" @click="toggleExpand">{{ expanded ? '全部折叠' : '全部展开' }}</el-button>
        <!-- 刷新：重新请求树数据，用于同步他人修改后的最新结构 -->
        <el-button :icon="Refresh" @click="fetchList">刷新</el-button>
      </div>

      <!-- 树形表格：row-key 指定唯一字段 id，tree-props 告诉表格用 children 字段渲染子层级。
           额外绑定 :key=tableKey：Element Plus 的 default-expand-all 只在初始化时读取，
           因此通过换 key 重建组件，才能让“全部展开/折叠”立即生效。 -->
      <el-table
        :key="tableKey"
        v-loading="loading"
        :data="list"
        row-key="id"
        :tree-props="{ children: 'children' }"
        :default-expand-all="expanded"
      >
        <!-- 序号列：按渲染行号递增（含子级行），仅作视觉参考 -->
        <el-table-column type="index" label="序号" width="70" align="center" />
        <!-- 部门名称：树形缩进由表格根据层级自动绘制，min-width 保证长名称可读 -->
        <el-table-column label="部门名称" prop="dept_name" min-width="200" />
        <!-- 显示排序：后端 order_num，数值越小越靠前，同级内生效 -->
        <el-table-column label="排序" prop="order_num" width="80" align="center" />
        <!-- 负责人：可能为空，用 '-' 占位避免出现空白单元格 -->
        <el-table-column label="负责人" prop="leader" width="120">
          <template #default="{ row }">{{ row.leader || '-' }}</template>
        </el-table-column>
        <!-- 联系电话：同上，空值占位，此列不做格式化 -->
        <el-table-column label="联系电话" prop="phone" width="140">
          <template #default="{ row }">{{ row.phone || '-' }}</template>
        </el-table-column>
        <!-- 状态：0 表示正常（绿色 success），非 0 统一按停用（红色 danger）展示；
             此处只做展示，修改需要进入编辑弹窗 -->
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 0 ? 'success' : 'danger'" size="small">
              {{ row.status === 0 ? '正常' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <!-- 创建时间：后端已格式化为字符串，前端直接显示不做转换 -->
        <el-table-column label="创建时间" prop="create_time" width="170" />
        <!-- 操作列：固定在右侧，水平滚动时始终可见；宽度容纳“新增/编辑/删除”三个文字按钮 -->
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <!-- 新增下级：把当前行作为父部门传入 openCreate（内部读取 parent.id）；
                 这里用 hasPerm 显式判断而非 v-perm 指令，效果一致：无 system:dept:create 权限就不渲染 -->
            <el-button
              v-if="hasPerm('system:dept:create')"
              link
              type="primary"
              @click="openCreate(row)"
            >新增</el-button>
            <!-- 编辑：按当前行数据回填表单；权限由 v-perm 指令控制 -->
            <el-button v-perm="'system:dept:update'" link type="primary" @click="openEdit(row)">编辑</el-button>
            <!-- 删除：点击后先二次确认，确认通过才发请求；权限由 v-perm 指令控制 -->
            <el-button v-perm="'system:dept:delete'" link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新增/编辑弹窗：新增与编辑复用同一表单，标题与提交方式由 form.id 决定；
         destroy-on-close 在关闭后销毁内部组件，避免旧校验状态影响下次打开 -->
    <el-dialog v-model="formVisible" :title="form.id ? '编辑部门' : '新增部门'" width="560px" destroy-on-close>
      <!-- 表单：:model 绑定响应式 form，:rules 绑定校验规则，label-width 固定标签宽度保证纵向对齐 -->
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <!-- 上级部门：树形选择器，数据来自 parentTree（含虚拟顶级节点）；
             check-strictly 允许任选层级而不强制级联；:props 指定后端字段名；filterable 便于名称搜索 -->
        <el-form-item label="上级部门" prop="parent_id">
          <el-tree-select
            v-model="form.parent_id"
            :data="parentTree"
            :props="{ label: 'dept_name', children: 'children' }"
            node-key="id"
            check-strictly
            filterable
            default-expand-all
            style="width: 100%"
          />
        </el-form-item>
        <!-- 部门名称：必填，v-model.trim 自动去除首尾空格，maxlength 与后端字段长度对齐 -->
        <el-form-item label="部门名称" prop="dept_name">
          <el-input v-model.trim="form.dept_name" placeholder="请输入部门名称" maxlength="30" />
        </el-form-item>
        <!-- 显示排序：0~999 的整数，决定同级部门的展示顺序，步进按钮放右侧符合数字输入习惯 -->
        <el-form-item label="显示排序" prop="order_num">
          <el-input-number v-model="form.order_num" :min="0" :max="999" controls-position="right" />
        </el-form-item>
        <!-- 负责人：选填，仅作为部门联系人信息 -->
        <el-form-item label="负责人" prop="leader">
          <el-input v-model.trim="form.leader" placeholder="请输入负责人" maxlength="20" />
        </el-form-item>
        <!-- 联系电话：选填，不做格式校验，保持与后端宽松校验一致 -->
        <el-form-item label="联系电话" prop="phone">
          <el-input v-model.trim="form.phone" placeholder="请输入联系电话" maxlength="20" />
        </el-form-item>
        <!-- 状态：0 正常 / 1 停用，单选框二选一；默认值来自 form.status -->
        <el-form-item label="状态" prop="status">
          <el-radio-group v-model="form.status">
            <el-radio :value="0">正常</el-radio>
            <el-radio :value="1">停用</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <!-- 弹窗底部：取消仅关闭弹窗，确定触发保存并带 loading 防重复提交 -->
      <template #footer>
        <el-button @click="formVisible = false">取 消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">确 定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
// 组合式 API：ref 存放基础状态，reactive 存放表单对象，computed 派生选择器数据，onMounted 做首次加载
import { computed, onMounted, reactive, ref } from 'vue'
// 消息提示与确认弹窗：保存/删除结果反馈，删除前做二次确认
import { ElMessage, ElMessageBox } from 'element-plus'
// 工具栏与按钮图标：按需引入，避免注册全量图标
import { Plus, Expand, Minus, Refresh } from '@element-plus/icons-vue'
// 统一请求实例：已封装 baseURL=/api、token 注入、错误提示与 401 跳转
import request from '@/utils/request'
// 权限判断工具：用于对作用域插槽内的按钮做条件渲染
import { hasPerm } from '@/store/auth'

// 列表加载态：驱动表格 v-loading 遮罩，请求开始/结束成对切换
const loading = ref(false)
// 保存中状态：驱动弹窗确定按钮的 loading，防止重复提交
const saving = ref(false)
// 部门树数据：后端返回的嵌套数组，children 字段即下级部门
const list = ref([])
// 全局展开状态：既作为表格 default-expand-all 的入参，也决定按钮显示“全部折叠”还是“全部展开”
const expanded = ref(true)
// 表格实例标识：每次切换展开状态自增，借助 :key 重建表格使 default-expand-all 重新生效
const tableKey = ref(0)

// 切换全部展开/折叠：先翻转状态，再递增 key 重建表格；Element Plus 没有命令式的“全部展开”API
function toggleExpand() {
  expanded.value = !expanded.value
  tableKey.value++
}

// ---------- 列表 ----------
// 拉取部门树：GET /system/dept/tree；loading 放在 finally 中收起，保证请求失败也能解除遮罩
async function fetchList() {
  loading.value = true
  try {
    const res = await request.get('/system/dept/tree')
    // data 为部门树数组，兜底空数组防止表格收到 null
    list.value = res.data || []
  } finally {
    loading.value = false
  }
}

// ---------- 新增/编辑 ----------
// 弹窗显隐：新增与编辑共用，靠 form.id 区分模式与标题
const formVisible = ref(false)
// el-form 实例：提交前调用 validate() 做整体校验
const formRef = ref()
// 表单模型：字段与后端部门接口一一对应；parent_id 默认 0 表示顶级部门，其余给安全的空值
const form = reactive({
  id: null,
  parent_id: 0,
  dept_name: '',
  order_num: 0,
  leader: '',
  phone: '',
  status: 0
})

// 校验规则：只强制上级部门与名称，负责人/电话选填，避免过度约束录入
const rules = {
  parent_id: [{ required: true, message: '请选择上级部门', trigger: 'change' }],
  dept_name: [{ required: true, message: '请输入部门名称', trigger: 'blur' }]
}

// 上级部门候选树：在真实部门树外层包一个虚拟“顶级部门”(id=0)，
// 这样新建顶级部门时仍能选中父节点；直接引用 list，不复制数据，保证编辑弹窗总能看到最新层级
const parentTree = computed(() => [
  { id: 0, dept_name: '顶级部门', children: list.value }
])

// 重置表单为新增默认值：每次打开弹窗前先执行，防止上一次编辑的值残留
function resetForm() {
  form.id = null
  form.parent_id = 0
  form.dept_name = ''
  form.order_num = 0
  form.leader = ''
  form.phone = ''
  form.status = 0
}

// 打开新增弹窗：parent 存在表示“新增下级”，把当前行 id 预填为上级部门；无参则由工具栏调用，即新增顶级
function openCreate(parent) {
  resetForm()
  if (parent) {
    form.parent_id = parent.id
  }
  formVisible.value = true
}

// 打开编辑弹窗：先重置再整体覆盖；parent_id 用 ?? 兜底 0，leader/phone 空值转空串以适配输入框
function openEdit(row) {
  resetForm()
  Object.assign(form, {
    id: row.id,
    parent_id: row.parent_id ?? 0,
    dept_name: row.dept_name,
    order_num: row.order_num,
    leader: row.leader || '',
    phone: row.phone || '',
    status: row.status
  })
  formVisible.value = true
}

// 保存部门：先跑表单校验（不通过会 reject 并中断），再按 form.id 判断新增还是修改；
// payload 显式挑选字段，避免把 id、children 等表格附加字段提交给后端
async function handleSave() {
  await formRef.value.validate()
  saving.value = true
  try {
    const payload = {
      parent_id: form.parent_id,
      dept_name: form.dept_name,
      order_num: form.order_num,
      leader: form.leader,
      phone: form.phone,
      status: form.status
    }
    if (form.id) {
      // 编辑：PUT /system/dept/update/{id}，带上完整字段做覆盖式更新
      await request.put(`/system/dept/update/${form.id}`, payload)
      ElMessage.success('修改成功')
    } else {
      // 新增：POST /system/dept/create，parent_id 决定挂在哪个层级下
      await request.post('/system/dept/create', payload)
      ElMessage.success('新增成功')
    }
    formVisible.value = false
    // 保存后刷新树，让新增/修改的层级与排序立即反映到列表
    fetchList()
  } finally {
    // 无论成功失败都解除确定按钮的 loading
    saving.value = false
  }
}

// ---------- 删除 ----------
// 删除部门：先弹确认框（用户取消时 confirm 会 reject，从当前函数向上抛出），确认后再调用删除接口并刷新
async function handleDelete(row) {
  await ElMessageBox.confirm(`确定删除部门「${row.dept_name}」吗？`, '提示', { type: 'warning' })
  await request.delete(`/system/dept/delete/${row.id}`)
  ElMessage.success('删除成功')
  fetchList()
}

// 页面挂载后立即加载部门树，保证进入页面即有数据
onMounted(fetchList)
</script>
