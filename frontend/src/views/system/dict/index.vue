<template>
  <!-- 字典管理页：上方维护“字典类型”，通过操作列的“字典数据”进入抽屉维护该类型下的字典项。
       职责：字典类型分页查询/新增/编辑/删除；字典项抽屉内分页查询/新增/编辑/删除。
       关联：两侧通过 currentType（当前选中的类型）建立左右联动，字典项请求按 dict_type 过滤。
       依赖：utils/request 统一请求、store/auth 的权限指令、Element Plus 表格/抽屉/弹窗。 -->
  <div class="app-container">
    <!-- 页面头部：标题 + 副标题，副标题说明字典项入口位置，降低使用者的寻找成本 -->
    <div class="page-header">
      <div class="page-title-wrap">
        <h2>字典管理</h2>
        <div class="sub">字典类型维护，字典项通过操作列进入维护</div>
      </div>
    </div>

    <!-- 查询栏：按字典名称、类型编码过滤字典类型列表 -->
    <el-card shadow="never" class="search-card">
      <!-- inline 让表单项横向排列；@submit.prevent 阻止原生提交，避免回车触发表单刷新页面 -->
      <el-form inline @submit.prevent>
        <!-- 字典名称：模糊查询条件，回车等同点击查询 -->
        <el-form-item label="字典名称">
          <el-input v-model="typeQuery.dict_name" placeholder="请输入字典名称" clearable style="width: 170px" @keyup.enter="searchTypes" />
        </el-form-item>
        <!-- 类型编码：后端唯一标识（dict_type），回车同理触发查询 -->
        <el-form-item label="类型编码">
          <el-input v-model="typeQuery.dict_type" placeholder="请输入类型编码" clearable style="width: 170px" @keyup.enter="searchTypes" />
        </el-form-item>
        <el-form-item>
          <!-- 查询：searchTypes 会先把页码重置为 1，再按当前条件请求 -->
          <el-button type="primary" :icon="Search" @click="searchTypes">查询</el-button>
          <!-- 重置：清空两个查询条件后重新查询 -->
          <el-button :icon="Refresh" @click="resetTypes">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 字典类型列表卡片：工具栏 + 表格 + 分页；stripe 斑马纹提升长列表可读性 -->
    <el-card shadow="never" class="table-card">
      <!-- 工具栏：仅一个新增入口，权限由 v-perm 指令控制 -->
      <div class="toolbar">
        <el-button v-perm="'system:dict:create'" type="primary" :icon="Plus" @click="openTypeCreate">新增类型</el-button>
      </div>

      <!-- 字典类型表格：loading 由 typeLoading 驱动，empty-text 自定义空态文案 -->
      <el-table v-loading="typeLoading" stripe empty-text="暂无数据" :data="typeList">
        <!-- 序号列：按当前页的渲染顺序递增，不表示真实主键 -->
        <el-table-column type="index" label="序号" width="70" align="center" />
        <!-- 字典名称：业务上的可读名称，过宽时省略并悬浮展示完整内容 -->
        <el-table-column label="字典名称" prop="dict_name" min-width="140" show-overflow-tooltip />
        <!-- 类型编码：全局唯一标识，字典项查询和代码取字典时都依赖它，因此单独一列方便核对 -->
        <el-table-column label="类型编码" prop="dict_type" min-width="160" show-overflow-tooltip />
        <!-- 状态：0 正常（success）/ 非 0 停用（danger），仅展示，修改需进入编辑弹窗 -->
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 0 ? 'success' : 'danger'" size="small">
              {{ row.status === 0 ? '正常' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <!-- 备注：选填说明，空值用 '-' 占位，超长内容由 tooltip 承载 -->
        <el-table-column label="备注" prop="remark" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">{{ row.remark || '-' }}</template>
        </el-table-column>
        <!-- 创建时间：后端已格式化，前端直接展示 -->
        <el-table-column label="创建时间" prop="create_time" width="170" />
        <!-- 操作列：固定在右侧；三个按钮分别是进入字典项维护、编辑类型、删除类型 -->
        <el-table-column label="操作" width="230" fixed="right">
          <template #default="{ row }">
            <!-- 字典数据：把当前行记为 currentType 并打开抽屉，左侧列表与右侧抽屉由此联动；
                 该入口不设权限，能进入本页即可查看字典项 -->
            <el-button link type="primary" @click="openDataDrawer(row)">字典数据</el-button>
            <!-- 编辑类型：回填表单；权限由 v-perm 控制 -->
            <el-button v-perm="'system:dict:update'" link type="primary" @click="openTypeEdit(row)">编辑</el-button>
            <!-- 删除类型：二次确认后连带影响字典项；权限由 v-perm 控制 -->
            <el-button v-perm="'system:dict:delete'" link type="danger" @click="handleTypeDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页条：current-page/page-size 双向绑定，变化后由事件回调重新请求 -->
      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="typePage"
          v-model:page-size="typePageSize"
          :total="typeTotal"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="typePage = 1; fetchTypes()"
          @current-change="fetchTypes"
        />
      </div>
    </el-card>

    <!-- 字典类型弹窗：新增/编辑复用，标题与提交方式由 typeForm.id 决定；destroy-on-close 避免残留校验状态 -->
    <el-dialog v-model="typeVisible" :title="typeForm.id ? '编辑字典类型' : '新增字典类型'" width="480px" destroy-on-close>
      <!-- 类型表单：字段与后端字典类型接口对应，label-width 统一标签宽度 -->
      <el-form ref="typeFormRef" :model="typeForm" :rules="typeRules" label-width="90px">
        <!-- 字典名称：展示用名称，必填；placeholder 给出命名示例 -->
        <el-form-item label="字典名称" prop="dict_name">
          <el-input v-model.trim="typeForm.dict_name" placeholder="如 用户性别" maxlength="50" />
        </el-form-item>
        <!-- 类型编码：程序读取字典的唯一 key，必填；编辑时禁用（已存在则不可改，避免已有字典项与代码引用失联） -->
        <el-form-item label="类型编码" prop="dict_type">
          <el-input v-model.trim="typeForm.dict_type" placeholder="如 sys_user_sex" :disabled="!!typeForm.id" maxlength="50" />
        </el-form-item>
        <!-- 状态：0 正常 / 1 停用，停用后前端一般不再取该字典 -->
        <el-form-item label="状态" prop="status">
          <el-radio-group v-model="typeForm.status">
            <el-radio :value="0">正常</el-radio>
            <el-radio :value="1">停用</el-radio>
          </el-radio-group>
        </el-form-item>
        <!-- 备注：选填说明，限制 200 字，与后端字段长度一致 -->
        <el-form-item label="备注" prop="remark">
          <el-input v-model="typeForm.remark" type="textarea" :rows="3" maxlength="200" />
        </el-form-item>
      </el-form>
      <!-- 底部按钮：取消关闭弹窗，确定走保存并带 loading -->
      <template #footer>
        <el-button @click="typeVisible = false">取 消</el-button>
        <el-button type="primary" :loading="saving" @click="handleTypeSave">确 定</el-button>
      </template>
    </el-dialog>

    <!-- 字典数据抽屉：右侧滑出，宽度 640px 以容纳更多列；destroy-on-close 保证切换类型时不残留旧数据组件状态 -->
    <el-drawer v-model="dataDrawerVisible" size="640px" destroy-on-close>
      <!-- 抽屉头部：主标题“字典数据”+ 当前类型信息（名称 / 编码），让用户明确正在维护哪一类 -->
      <template #header>
        <div class="drawer-title">
          <span>字典数据</span>
          <span v-if="currentType" class="drawer-sub">{{ currentType.dict_name }} / {{ currentType.dict_type }}</span>
        </div>
      </template>

      <!-- 抽屉工具栏：新增字典项，权限与类型新增共用 system:dict:create -->
      <div class="toolbar">
        <el-button v-perm="'system:dict:create'" type="primary" :icon="Plus" @click="openDataCreate">新增字典项</el-button>
      </div>

      <!-- 字典项表格：loading 由 dataLoading 驱动，数据只包含当前类型的字典项 -->
      <el-table v-loading="dataLoading" stripe empty-text="暂无数据" :data="dataList">
        <!-- 标签：展示给用户看的文案（如“男”） -->
        <el-table-column label="标签" prop="dict_label" min-width="100" show-overflow-tooltip />
        <!-- 键值：程序存储/传参用的值（如“1”），与标签成对出现 -->
        <el-table-column label="键值" prop="dict_value" min-width="90" show-overflow-tooltip />
        <!-- 排序：dict_sort 数值越小越靠前，决定下拉框中的展示顺序 -->
        <el-table-column label="排序" prop="dict_sort" width="70" align="center" />
        <!-- 状态：0 正常 / 非 0 停用，仅展示 -->
        <el-table-column label="状态" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 0 ? 'success' : 'danger'" size="small">
              {{ row.status === 0 ? '正常' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <!-- 备注：空值占位，超长时 tooltip 展示 -->
        <el-table-column label="备注" prop="remark" min-width="100" show-overflow-tooltip>
          <template #default="{ row }">{{ row.remark || '-' }}</template>
        </el-table-column>
        <!-- 操作列：编辑/删除当前字典项，均受权限指令控制 -->
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <!-- 编辑字典项：回填弹窗表单 -->
            <el-button v-perm="'system:dict:update'" link type="primary" @click="openDataEdit(row)">编辑</el-button>
            <!-- 删除字典项：二次确认后删除并刷新当前抽屉列表 -->
            <el-button v-perm="'system:dict:delete'" link type="danger" @click="handleDataDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 抽屉分页条：与类型列表分页相互独立，查询条件固定为当前字典类型 -->
      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="dataPage"
          v-model:page-size="dataPageSize"
          :total="dataTotal"
          :page-sizes="[10, 20, 50]"
          layout="total, prev, pager, next"
          @size-change="dataPage = 1; fetchData()"
          @current-change="fetchData"
        />
      </div>
    </el-drawer>

    <!-- 字典项弹窗：新增/编辑复用；所属类型由只读字段展示，用户无需也无法在此切换 -->
    <el-dialog v-model="dataVisible" :title="dataForm.id ? '编辑字典项' : '新增字典项'" width="480px" destroy-on-close>
      <!-- 字典项表单：校验标签与键值必填，其余选填 -->
      <el-form ref="dataFormRef" :model="dataForm" :rules="dataRules" label-width="90px">
        <!-- 字典类型：只读展示当前类型的编码，提醒用户该字典项归属哪个类型；
             使用 :model-value 单向传值而非 v-model，避免用户误改当前类型 -->
        <el-form-item label="字典类型">
          <el-input :model-value="currentType ? currentType.dict_type : ''" disabled />
        </el-form-item>
        <!-- 数据标签：给用户展示的文案，必填 -->
        <el-form-item label="数据标签" prop="dict_label">
          <el-input v-model.trim="dataForm.dict_label" placeholder="如 男" maxlength="50" />
        </el-form-item>
        <!-- 数据键值：实际存储值，必填；与标签成对，后端不强制唯一，由业务自行约定 -->
        <el-form-item label="数据键值" prop="dict_value">
          <el-input v-model.trim="dataForm.dict_value" placeholder="如 1" maxlength="50" />
        </el-form-item>
        <!-- 显示排序：0~999，控制同一类型下字典项的展示顺序 -->
        <el-form-item label="显示排序" prop="dict_sort">
          <el-input-number v-model="dataForm.dict_sort" :min="0" :max="999" controls-position="right" />
        </el-form-item>
        <!-- 状态：0 正常 / 1 停用 -->
        <el-form-item label="状态" prop="status">
          <el-radio-group v-model="dataForm.status">
            <el-radio :value="0">正常</el-radio>
            <el-radio :value="1">停用</el-radio>
          </el-radio-group>
        </el-form-item>
        <!-- 备注：选填说明，限制 200 字 -->
        <el-form-item label="备注" prop="remark">
          <el-input v-model="dataForm.remark" type="textarea" :rows="3" maxlength="200" />
        </el-form-item>
      </el-form>
      <!-- 底部按钮：取消关闭弹窗，确定保存字典项 -->
      <template #footer>
        <el-button @click="dataVisible = false">取 消</el-button>
        <el-button type="primary" :loading="saving" @click="handleDataSave">确 定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
// 组合式 API：ref 管理分页/加载态/表单显隐，reactive 管理查询条件与表单模型，onMounted 做首次加载
import { onMounted, reactive, ref } from 'vue'
// 统一消息提示与二次确认框，用于增删改结果反馈
import { ElMessage, ElMessageBox } from 'element-plus'
// 图标按需引入：Plus 新增、Search 查询、Refresh 重置
import { Plus, Search, Refresh } from '@element-plus/icons-vue'
// 统一请求实例：已封装 baseURL、token 注入、错误提示与 401 跳转
import request from '@/utils/request'

// 保存中状态：字典类型的保存与字典项的保存共用该标记，避免同时出现两个提交中的弹窗
const saving = ref(false)

// ---------- 字典类型 ----------
// 类型表格加载态：驱动 el-table 的 v-loading
const typeLoading = ref(false)
// 类型列表数据：当前页的类型记录
const typeList = ref([])
// 类型总条数：分页组件据此计算页数
const typeTotal = ref(0)
// 类型当前页码：v-model:current-page 双向绑定
const typePage = ref(1)
// 类型每页条数：与 page-sizes 选项对应
const typePageSize = ref(10)
// 类型查询条件：作为请求参数整体展开，键名与后端接口一致
const typeQuery = reactive({ dict_name: '', dict_type: '' })
// 当前正在查看字典项的类型行：打开抽屉时赋值，关闭时清空，是左右两栏联动的唯一纽带
const currentType = ref(null)

// 拉取字典类型列表：分页参数与查询条件一起提交；失败时由请求拦截器统一提示
async function fetchTypes() {
  typeLoading.value = true
  try {
    const res = await request.get('/system/dict/type/list', {
      params: { page: typePage.value, page_size: typePageSize.value, ...typeQuery }
    })
    // 后端约定 data = { list, total }，分别回填表格与分页总数
    typeList.value = res.data.list || []
    typeTotal.value = res.data.total || 0
    // 当前打开的字典类型可能已被删除
    if (currentType.value && !typeList.value.some(t => t.id === currentType.value.id)) {
      closeDataDrawer()
    }
  } finally {
    typeLoading.value = false
  }
}

// 条件查询：先把页码回到第一页再请求，避免停留在超出新结果范围的页码上
function searchTypes() {
  typePage.value = 1
  fetchTypes()
}

// 重置查询：清空名称与编码条件后复用查询逻辑，保证页码也归位
function resetTypes() {
  typeQuery.dict_name = ''
  typeQuery.dict_type = ''
  searchTypes()
}

// 类型新增/编辑
// 类型弹窗显隐：新增与编辑共用
const typeVisible = ref(false)
// 类型表单实例：保存前执行 validate()
const typeFormRef = ref()
// 类型表单模型：id 为 null 表示新增；status 默认 0 正常
const typeForm = reactive({ id: null, dict_name: '', dict_type: '', status: 0, remark: '' })
// 类型校验规则：名称与编码必填，编码是业务唯一键，不允许为空
const typeRules = {
  dict_name: [{ required: true, message: '请输入字典名称', trigger: 'blur' }],
  dict_type: [{ required: true, message: '请输入类型编码', trigger: 'blur' }]
}

// 打开新增类型弹窗：逐字段重置，避免上一次编辑的内容残留
function openTypeCreate() {
  typeForm.id = null
  typeForm.dict_name = ''
  typeForm.dict_type = ''
  typeForm.status = 0
  typeForm.remark = ''
  typeVisible.value = true
}

// 打开编辑类型弹窗：把行数据回填到表单；备注空值转空串以适配 textarea
function openTypeEdit(row) {
  typeForm.id = row.id
  typeForm.dict_name = row.dict_name
  typeForm.dict_type = row.dict_type
  typeForm.status = row.status
  typeForm.remark = row.remark || ''
  typeVisible.value = true
}

// 保存类型：校验通过后按 id 判断新增/修改；payload 只提交业务字段（id 走路径参数）
async function handleTypeSave() {
  await typeFormRef.value.validate()
  saving.value = true
  try {
    const payload = {
      dict_name: typeForm.dict_name,
      dict_type: typeForm.dict_type,
      status: typeForm.status,
      remark: typeForm.remark
    }
    if (typeForm.id) {
      // 编辑：PUT /system/dict/type/update/{id}
      await request.put(`/system/dict/type/update/${typeForm.id}`, payload)
      ElMessage.success('修改成功')
    } else {
      // 新增：POST /system/dict/type/create
      await request.post('/system/dict/type/create', payload)
      ElMessage.success('新增成功')
    }
    typeVisible.value = false
    // 保存后刷新列表，新类型立即可见
    fetchTypes()
  } finally {
    // 成功或失败都解除确定按钮 loading
    saving.value = false
  }
}

// 删除类型：确认文案提示“其下字典项将不可用”，删除接口以 ids 数组批量提交（此处只传一条）
async function handleTypeDelete(row) {
  await ElMessageBox.confirm(`确定删除字典类型「${row.dict_name}」吗？其下字典项将不可用。`, '提示', { type: 'warning' })
  await request.delete('/system/dict/type/delete', { data: { ids: [row.id] } })
  ElMessage.success('删除成功')
  // 若删除的正是抽屉里正在查看的类型，先关闭抽屉，避免右侧继续展示失效数据
  if (currentType.value && currentType.value.id === row.id) closeDataDrawer()
  fetchTypes()
}

// ---------- 字典数据（抽屉） ----------
// 抽屉显隐：打开时由 openDataDrawer 赋值 currentType
const dataDrawerVisible = ref(false)
// 抽屉内表格加载态：驱动抽屉里表格的 v-loading
const dataLoading = ref(false)
// 字典项列表：只包含当前类型的记录
const dataList = ref([])
// 字典项总数：抽屉内分页使用，与类型分页互不影响
const dataTotal = ref(0)
// 字典项当前页码
const dataPage = ref(1)
// 字典项每页条数：默认 10，可在 page-sizes 中调整
const dataPageSize = ref(10)

// 打开字典项抽屉：先记录当前类型，再把分页与缓存数据归零，确保抽屉不会闪现上一个类型的数据，最后拉取列表
function openDataDrawer(row) {
  currentType.value = row
  dataPage.value = 1
  dataList.value = []
  dataTotal.value = 0
  dataDrawerVisible.value = true
  fetchData()
}

// 关闭抽屉并彻底清理：清空 currentType 与列表，避免遗留引用导致后续请求误用旧类型
function closeDataDrawer() {
  dataDrawerVisible.value = false
  currentType.value = null
  dataList.value = []
  dataTotal.value = 0
}

// 拉取当前类型的字典项：按 dict_type（类型编码）而非类型 id 过滤，与后端接口参数保持一致；
// 无 currentType 时直接返回，防止分页组件在抽屉关闭后误触发请求
async function fetchData() {
  if (!currentType.value) return
  dataLoading.value = true
  try {
    const res = await request.get('/system/dict/data/list', {
      params: { page: dataPage.value, page_size: dataPageSize.value, dict_type: currentType.value.dict_type }
    })
    dataList.value = res.data.list || []
    dataTotal.value = res.data.total || 0
  } finally {
    dataLoading.value = false
  }
}

// 字典项弹窗显隐：新增/编辑共用
const dataVisible = ref(false)
// 字典项表单实例：保存前校验
const dataFormRef = ref()
// 字典项表单模型：dict_type_id 记录归属类型，新增时由 currentType.id 赋值
const dataForm = reactive({
  id: null,
  dict_type_id: null,
  dict_label: '',
  dict_value: '',
  dict_sort: 0,
  status: 0,
  remark: ''
})
// 字典项校验规则：标签与键值必填，其余可选
const dataRules = {
  dict_label: [{ required: true, message: '请输入数据标签', trigger: 'blur' }],
  dict_value: [{ required: true, message: '请输入数据键值', trigger: 'blur' }]
}

// 打开新增字典项弹窗：dict_type_id 取当前抽屉的类型 id，保证新记录归属正确；其余字段重置
function openDataCreate() {
  dataForm.id = null
  dataForm.dict_type_id = currentType.value.id
  dataForm.dict_label = ''
  dataForm.dict_value = ''
  dataForm.dict_sort = 0
  dataForm.status = 0
  dataForm.remark = ''
  dataVisible.value = true
}

// 打开编辑字典项弹窗：回填行数据；dict_type_id 兜底为当前类型 id，兼容后端未返回该字段的情况
function openDataEdit(row) {
  dataForm.id = row.id
  dataForm.dict_type_id = row.dict_type_id ?? currentType.value.id
  dataForm.dict_label = row.dict_label
  dataForm.dict_value = row.dict_value
  dataForm.dict_sort = row.dict_sort
  dataForm.status = row.status
  dataForm.remark = row.remark || ''
  dataVisible.value = true
}

// 保存字典项：按 id 判断新增/修改，payload 只包含业务字段；
// 保存成功后刷新抽屉列表（而不是类型列表，因为类型数据没有变化）
async function handleDataSave() {
  await dataFormRef.value.validate()
  saving.value = true
  try {
    const payload = {
      dict_type_id: dataForm.dict_type_id,
      dict_label: dataForm.dict_label,
      dict_value: dataForm.dict_value,
      dict_sort: dataForm.dict_sort,
      status: dataForm.status,
      remark: dataForm.remark
    }
    if (dataForm.id) {
      // 编辑：PUT /system/dict/data/update/{id}
      await request.put(`/system/dict/data/update/${dataForm.id}`, payload)
      ElMessage.success('修改成功')
    } else {
      // 新增：POST /system/dict/data/create，dict_type_id 决定挂到哪个字典类型下
      await request.post('/system/dict/data/create', payload)
      ElMessage.success('新增成功')
    }
    dataVisible.value = false
    // 刷新抽屉内列表，保持当前页码；若删除/新增导致页数变化由分页组件自行收敛
    fetchData()
  } finally {
    saving.value = false
  }
}

// 删除字典项：二次确认后按 ids 数组删除（后端批量接口），随后刷新抽屉列表
async function handleDataDelete(row) {
  await ElMessageBox.confirm(`确定删除字典项「${row.dict_label}」吗？`, '提示', { type: 'warning' })
  await request.delete('/system/dict/data/delete', { data: { ids: [row.id] } })
  ElMessage.success('删除成功')
  fetchData()
}

// 页面挂载后先加载字典类型列表；字典项只在打开抽屉时才请求，避免无谓请求
onMounted(fetchTypes)
</script>

<style scoped>
/* 抽屉标题容器：主标题与“名称/编码”信息排在同一行，baseline 对齐让不同字号也有统一基线 */
.drawer-title {
  display: flex;
  align-items: baseline;
  gap: 10px;
}

/* 抽屉副标题：展示当前字典类型的名称与编码，用更小字号与灰色弱化，避免与主标题争夺视觉焦点 */
.drawer-sub {
  font-size: 12px;
  color: #909399;
  font-weight: normal;
}
</style>
