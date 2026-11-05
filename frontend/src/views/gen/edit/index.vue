<!--
  文件级说明：
  职责：代码生成配置页（隐藏路由 /gen/edit/:id）。读取某张已导入表的配置，允许编辑类名、模块中文/标识、
        路由前缀、前端页面输出路径、父级菜单与逻辑删除/导入/导出开关，并逐列配置表单控件、字典、查询方式等；
        保存后回到列表页或继续预览/下载。
  依赖：@/utils/request（GET/PUT /gen/table/{id}、/system/menu/tree、/system/dict/data/all、DDL 与下载接口）、
        @/utils/download 的 saveBlob、@/components/CodePreviewDialog.vue、Element Plus 组件与图标、v-perm 指令。
  被谁使用：代码生成列表页点击“配置”跳转进入；路由已在 router/index.js 中静态注册。
  说明：从详情接口读到的 0/1 开关统一用 to01 归一化，避免后端返回 true/'1' 时 el-switch 无法正确显示。
-->
<template>
  <!-- 页面根容器：复用全局内边距与背景 -->
  <div class="app-container">
    <!-- 生成信息：表级基础配置，决定生成代码的命名、路由与菜单归属 -->
    <el-card shadow="never" header="生成信息" class="mb14">
      <!-- 请求详情期间整块遮罩，防止用户在数据未就绪时误改字段 -->
      <div v-loading="loading">
        <!-- 表级表单：tableFormRef 用于保存前校验；model 绑定 table；rules 校验必填项；固定标签宽度保证栅格对齐 -->
        <el-form ref="tableFormRef" :model="table" :rules="tableRules" label-width="110px">
          <!-- 栅格布局：24 栅格三列（每列 8），gutter=16 控制列间距 -->
          <el-row :gutter="16">
            <!-- 表名：来自数据库的真实表名，只读展示，用户不能改写 -->
            <el-col :span="8">
              <el-form-item label="表名">
                <!-- :model-value 单向展示 + disabled，防止被表单双向绑定误改 -->
                <el-input :model-value="table.table_name" disabled />
              </el-form-item>
            </el-col>
            <!-- 表注释：数据库表注释，只读展示，作为命名参考 -->
            <el-col :span="8">
              <el-form-item label="表注释">
                <!-- 只读展示，不参与提交 -->
                <el-input :model-value="table.table_comment" disabled />
              </el-form-item>
            </el-col>
            <!-- 类名：生成的实体/控制器类名前缀（大驼峰），如 BizOrder；prop 使 tableRules 中的必填规则生效 -->
            <el-col :span="8">
              <el-form-item label="类名" prop="class_name">
                <!-- v-model.trim 自动去掉首尾空格，避免生成非法标识符；maxlength 与后端字段长度保持一致 -->
                <el-input v-model.trim="table.class_name" placeholder="如 BizOrder" maxlength="50" />
              </el-form-item>
            </el-col>
            <!-- 模块中文：用于生成菜单名称、页面标题与注释文案 -->
            <el-col :span="8">
              <el-form-item label="模块中文" prop="module_comment">
                <!-- 文本输入 + 必填校验 -->
                <el-input v-model.trim="table.module_comment" placeholder="如 订单管理" maxlength="50" />
              </el-form-item>
            </el-col>
            <!-- 模块标识：英文小写下划线风格（如 biz_order），决定生成目录、路由与权限码前缀 -->
            <el-col :span="8">
              <el-form-item label="模块标识" prop="module_name">
                <!-- 必填；trim 防止空格混入路由/文件名 -->
                <el-input v-model.trim="table.module_name" placeholder="如 biz_order" maxlength="50" />
              </el-form-item>
            </el-col>
            <!-- 路由前缀：后端接口统一挂载前缀，生成的前端请求与后端路由都会拼上它 -->
            <el-col :span="8">
              <el-form-item label="路由前缀" prop="url_prefix">
                <!-- 示例给出 /api/模块/资源 的约定形式 -->
                <el-input v-model.trim="table.url_prefix" placeholder="如 /api/biz/order" maxlength="100" />
              </el-form-item>
            </el-col>
            <!-- 前端页面路径：生成前端页面时写入的目标目录（相对于 views），也是菜单 component 的取值 -->
            <el-col :span="8">
              <el-form-item label="前端页面路径" prop="gen_path">
                <!-- 非必填，为空时由后端使用默认路径 -->
                <el-input v-model.trim="table.gen_path" placeholder="如 views/biz/order" maxlength="100" />
              </el-form-item>
            </el-col>
            <!-- 父级菜单：生成菜单时要挂载到哪个目录下，决定侧边栏位置与访问路径前缀 -->
            <el-col :span="8">
              <el-form-item label="父级菜单" prop="parent_menu_id">
                <!-- 树形下拉：直接展示后端菜单树，选择某一级作为上级 -->
                <el-tree-select
                  v-model="table.parent_menu_id"
                  :data="menuTree"
                  :props="{ label: 'menu_name', children: 'children' }"
                  node-key="id"
                  check-strictly
                  clearable
                  filterable
                  default-expand-all
                  placeholder="生成菜单的上级位置"
                  style="width: 100%"
                />
                <!-- 说明：props 把后端字段映射为树组件需要的 label/children；node-key=id 保证节点唯一；
                     check-strictly 允许选中任意层级而不强制只选叶子；clearable 支持生成顶级菜单；
                     filterable 便于菜单较多时按名称搜索；default-expand-all 打开即可看清层级 -->
              </el-form-item>
            </el-col>
            <!-- 生成选项：三个开关控制生成代码是否包含对应能力，值仍以 0/1 提交给后端 -->
            <el-col :span="8">
              <el-form-item label="生成选项">
                <!-- 横向排列并允许换行，避免窄屏时三个开关挤在一起 -->
                <div class="switch-group">
                  <!-- 逻辑删除：生成的列表查询/删除逻辑会带 deleted 标记，数据仅做软删除 -->
                  <el-checkbox v-model="table.is_delete_logic" :true-value="1" :false-value="0">逻辑删除</el-checkbox>
                  <!-- 导入：生成 Excel 导入接口与页面上传入口 -->
                  <el-checkbox v-model="table.import_enable" :true-value="1" :false-value="0">导入</el-checkbox>
                  <!-- 导出：生成 Excel 导出接口与页面下载按钮 -->
                  <el-checkbox v-model="table.export_enable" :true-value="1" :false-value="0">导出</el-checkbox>
                </div>
              </el-form-item>
            </el-col>
          </el-row>
        </el-form>
      </div>
    </el-card>

    <!-- 字段配置：逐列决定生成的表单控件、列表/查询/导入导出行为 -->
    <el-card shadow="never" header="字段配置">
      <!-- 字段表格：border 显示竖线便于逐列编辑；row-key=id 保证行身份稳定，输入时不串行；
           max-height 超长字段列表内部滚动，避免页面被撑得太长 -->
      <el-table :data="columns" v-loading="loading" border row-key="id" max-height="520">
        <!-- 序号列：按当前顺序编号，排序值变化后可直观核对 -->
        <el-table-column label="序号" type="index" width="55" align="center" />
        <!-- 字段名：数据库列名，只读；主键列额外用红色标签标记，提示不可编辑关键信息 -->
        <el-table-column label="字段名" prop="column_name" min-width="140" show-overflow-tooltip>
          <template #default="{ row }">
            <!-- 直接展示列名 -->
            <span>{{ row.column_name }}</span>
            <!-- 仅主键行显示标签；ml4 拉开与列名的间距 -->
            <el-tag v-if="row.is_pk" type="danger" size="small" class="ml4">主键</el-tag>
          </template>
        </el-table-column>
        <!-- 字段注释：可编辑，既作为生成代码的字段说明，也作为表单 label/表头文案 -->
        <el-table-column label="字段注释" min-width="160">
          <template #default="{ row }">
            <!-- 行内编辑：直接改 columns 中对应行的 column_comment，保存时随整体提交 -->
            <el-input v-model="row.column_comment" placeholder="字段注释" maxlength="100" />
          </template>
        </el-table-column>
        <!-- 字段类型：数据库原始类型（如 varchar/int/datetime），只读，作为选择表单控件的参考 -->
        <el-table-column label="字段类型" prop="column_type" min-width="130" show-overflow-tooltip />
        <!-- 表单类型：决定该字段在新增/编辑弹窗里渲染成什么控件（文本框、日期、下拉等） -->
        <el-table-column label="表单类型" min-width="130">
          <template #default="{ row }">
            <!-- 可选项来自 formTypeOptions，value 与后端约定的控件类型一一对应 -->
            <el-select v-model="row.form_type" placeholder="表单类型">
              <el-option v-for="t in formTypeOptions" :key="t.value" :label="t.label" :value="t.value" />
            </el-select>
          </template>
        </el-table-column>
        <!-- 字典类型：当表单类型为下拉/单选时，关联系统字典以渲染可选项；留空表示使用静态选项或无字典 -->
        <el-table-column label="字典类型" min-width="150">
          <template #default="{ row }">
            <!-- clearable 允许解除关联；filterable 便于字典较多时搜索 -->
            <el-select v-model="row.dict_type" clearable filterable placeholder="关联字典">
              <!-- dictTypeOptions 为所有字典类型 code 的字符串列表 -->
              <el-option v-for="d in dictTypeOptions" :key="d" :label="d" :value="d" />
            </el-select>
          </template>
        </el-table-column>
        <!-- 列表：控制该字段是否出现在生成的列表页表格中 -->
        <el-table-column label="列表" width="65" align="center">
          <template #default="{ row }">
            <!-- 开关值显式指定 1/0，保证与后端字段类型一致 -->
            <el-switch v-model="row.is_list" :active-value="1" :inactive-value="0" />
          </template>
        </el-table-column>
        <!-- 查询：控制该字段是否作为列表页的查询条件 -->
        <el-table-column label="查询" width="65" align="center">
          <template #default="{ row }">
            <!-- 打开后下方的“查询方式”才会启用 -->
            <el-switch v-model="row.is_query" :active-value="1" :inactive-value="0" />
          </template>
        </el-table-column>
        <!-- 查询方式：决定后端过滤条件（等于/模糊/大于/小于/范围） -->
        <el-table-column label="查询方式" min-width="110">
          <template #default="{ row }">
            <!-- 未开启“查询”时禁用，避免配置了不生效的查询条件 -->
            <el-select v-model="row.query_type" :disabled="row.is_query !== 1" placeholder="查询方式">
              <!-- 选项来自 queryTypeOptions，value 对应后端约定的操作符 -->
              <el-option v-for="t in queryTypeOptions" :key="t.value" :label="t.label" :value="t.value" />
            </el-select>
          </template>
        </el-table-column>
        <!-- 必填：开启后生成的表单校验要求该字段必填 -->
        <el-table-column label="必填" width="65" align="center">
          <template #default="{ row }">
            <!-- 0/1 开关，保存时统一转换 -->
            <el-switch v-model="row.is_required" :active-value="1" :inactive-value="0" />
          </template>
        </el-table-column>
        <!-- 导出：控制该字段是否进入 Excel 导出的列 -->
        <el-table-column label="导出" width="65" align="center">
          <template #default="{ row }">
            <!-- 仅在表级“导出”开启时才有实际意义 -->
            <el-switch v-model="row.is_export" :active-value="1" :inactive-value="0" />
          </template>
        </el-table-column>
        <!-- 导入：控制该字段是否参与 Excel 导入解析 -->
        <el-table-column label="导入" width="65" align="center">
          <template #default="{ row }">
            <!-- 仅在表级“导入”开启时才有实际意义 -->
            <el-switch v-model="row.is_import" :active-value="1" :inactive-value="0" />
          </template>
        </el-table-column>
        <!-- 排序：控制字段在列表、表单与导出中的显示先后；数字越小越靠前 -->
        <el-table-column label="排序" width="110" align="center">
          <template #default="{ row }">
            <!-- 限制 0~999，避免误输入超大值或负数；controls-position=right 让步进按钮靠右更紧凑 -->
            <el-input-number v-model="row.sort" :min="0" :max="999" controls-position="right" style="width: 90px" />
          </template>
        </el-table-column>
      </el-table>

      <!-- 底部操作区：保存/预览/建表 SQL/下载/返回，居中排列（见 .actions 样式） -->
      <div class="actions">
        <!-- 保存配置：先触发表单校验，成功后提交表级与字段级配置；请求中 loading 防止重复点击 -->
        <el-button v-perm="'gen:table:update'" type="primary" :icon="Check" :loading="saving" @click="handleSave">保存配置</el-button>
        <!-- 预览代码：打开预览弹窗，参数为当前表 id -->
        <el-button v-perm="'gen:table:preview'" :icon="View" @click="previewRef.open(tableId)">预览代码</el-button>
        <!-- 查看建表 SQL：按当前配置重新生成建表语句并弹窗展示 -->
        <el-button v-perm="'gen:table:preview'" :icon="Document" @click="showDdl">查看建表SQL</el-button>
        <!-- 下载代码：以 ZIP 形式下载整套生成代码；success 色强调产出物 -->
        <el-button v-perm="'gen:table:download'" type="success" :icon="Download" @click="handleDownload">下载代码</el-button>
        <!-- 返回：不做保存，直接回到上一页（通常是代码生成列表） -->
        <el-button :icon="Back" @click="router.back()">返 回</el-button>
      </div>
    </el-card>

    <!-- 代码预览弹窗：通过 ref 调用 open(表id) 打开，组件内部负责请求与分文件展示 -->
    <CodePreviewDialog ref="previewRef" />

    <!-- 建表 SQL 弹窗：仅展示，不提供编辑；top=8vh 让弹窗更靠上，给长 SQL 留出高度 -->
    <el-dialog v-model="ddlVisible" title="建表 SQL" width="760px" top="8vh" destroy-on-close>
      <!-- 滚动容器：限制最大高度 60vh，超长建表语句在弹窗内部滚动 -->
      <el-scrollbar max-height="60vh">
        <!-- pre 保留 SQL 的换行与缩进；插值渲染为纯文本，不会被解析成 HTML -->
        <pre class="code-block">{{ ddlText }}</pre>
      </el-scrollbar>
    </el-dialog>
  </div>
</template>

<script setup>
// Vue 基础能力：onMounted 初始化加载；reactive 维护表级表单与提交结构；ref 维护加载/保存/弹窗状态
// 说明：computed 当前未在本文件使用
import { computed, onMounted, reactive, ref } from 'vue'
// 路由：useRoute 读取路径参数 id；useRouter 实现“返回”与后续跳转
import { useRoute, useRouter } from 'vue-router'
// Element Plus 消息提示：保存/下载成功后的反馈
import { ElMessage } from 'element-plus'
// 操作按钮图标：保存、预览、SQL、下载、返回
import { Check, View, Document, Download, Back } from '@element-plus/icons-vue'
// 统一请求实例：自动鉴权、解包响应体、统一错误提示
import request from '@/utils/request'
// 下载工具：把后端返回的 blob 保存为本地文件（本页用于代码 ZIP）
import { saveBlob } from '@/utils/download'
// 代码预览弹窗组件：复用列表页同一套预览能力
import CodePreviewDialog from '@/components/CodePreviewDialog.vue'

// 当前路由信息：用于取出隐藏路由 /gen/edit/:id 中的表配置 id
const route = useRoute()
// 路由器实例：用于“返回”操作
const router = useRouter()
// 当前正在配置的记录 id（路由参数为字符串，请求时直接拼进 URL）
const tableId = route.params.id

// 详情加载中：控制表单与字段表格的遮罩
const loading = ref(false)
// 保存请求进行中：用于保存按钮的 loading 与防重复提交
const saving = ref(false)
// 表级表单实例：handleSave 中调用 validate() 做必填校验
const tableFormRef = ref()
// 代码预览弹窗实例：调用 open(表id) 打开预览
const previewRef = ref()

// 表级配置：与“生成信息”表单一一对应；id 仅用于标识记录，不参与表级提交
const table = reactive({
  id: null,
  table_name: '',
  table_comment: '',
  class_name: '',
  module_name: '',
  module_comment: '',
  url_prefix: '',
  gen_path: '',
  parent_menu_id: null,
  is_delete_logic: 0,
  import_enable: 0,
  export_enable: 0
})

// 字段配置列表：每项包含列名、类型、表单类型、查询方式等可编辑属性
const columns = ref([])
// 菜单树：供“父级菜单”树形下拉选择上级目录
const menuTree = ref([])
// 字典类型选项：从字典数据接口聚合出的 dict_type 类型 code 列表
const dictTypeOptions = ref([])

// 表级表单校验规则：命名类字段为空会直接影响生成结果，因此全部必填；blur 触发更符合输入习惯
const tableRules = {
  class_name: [{ required: true, message: '请输入类名', trigger: 'blur' }],
  module_name: [{ required: true, message: '请输入模块标识', trigger: 'blur' }],
  module_comment: [{ required: true, message: '请输入模块中文名', trigger: 'blur' }],
  url_prefix: [{ required: true, message: '请输入路由前缀', trigger: 'blur' }]
}

// 表单控件类型选项：value 为后端约定的类型编码，label 为配置页展示文案
const formTypeOptions = [
  // 普通单行文本
  { value: 'input', label: '文本框' },
  // 纯数字输入
  { value: 'number', label: '数字' },
  // 日期选择
  { value: 'date', label: '日期' },
  // 下拉选择（可配合字典类型渲染选项）
  { value: 'select', label: '下拉框' },
  // 单选按钮组
  { value: 'radio', label: '单选' },
  // 多行文本
  { value: 'textarea', label: '文本域' },
  // 图片上传（单个图片）
  { value: 'image', label: '图片上传' },
  // 文件上传（走附件模块）
  { value: 'file', label: '文件上传' }
]

// 查询操作符选项：决定列表查询时后端拼接的过滤方式
const queryTypeOptions = [
  // 精确匹配
  { value: 'eq', label: '等于' },
  // 包含匹配（SQL LIKE）
  { value: 'like', label: '模糊' },
  // 大于
  { value: 'gt', label: '大于' },
  // 小于
  { value: 'lt', label: '小于' },
  // 区间（通常对应开始/结束两个输入）
  { value: 'between', label: '范围' }
]

// 统一将后端返回的开关字段转为 0/1
// 后端可能返回 true/false、'1'/'0' 或 null，Element Plus 开关只认数字 1/0，这里做一次归一化
function to01(v) {
  return Number(v) ? 1 : 0
}

// ---------- 数据加载 ----------
// 拉取当前表的完整配置（表级信息 + 字段列表），并归一化成页面可直接编辑的结构
async function load() {
  loading.value = true
  try {
    // 详情接口按 id 返回 { table, columns }
    const res = await request.get(`/gen/table/${tableId}`)
    // data 与 table 逐层兜底，避免后端异常返回导致后续赋值报错
    const detail = res.data || {}
    const t = detail.table || {}
    // 逐字段赋值而不是整体替换，保持 reactive 引用不变，表单绑定不会失效
    Object.assign(table, {
      id: t.id,
      table_name: t.table_name,
      table_comment: t.table_comment,
      class_name: t.class_name,
      module_name: t.module_name,
      module_comment: t.module_comment,
      url_prefix: t.url_prefix,
      gen_path: t.gen_path,
      // 父级菜单允许为空：用 ?? 只在 null/undefined 时兜底，保留 0 等合法值
      parent_menu_id: t.parent_menu_id ?? null,
      // 开关统一归一化成 1/0，保证 el-checkbox 正确选中
      is_delete_logic: to01(t.is_delete_logic),
      import_enable: to01(t.import_enable),
      export_enable: to01(t.export_enable)
    })
    // 字段列表同样做默认值兜底：字符串字段给空串，表单类型默认 input，查询方式默认 eq，排序默认 0
    columns.value = (detail.columns || []).map(col => ({
      // 保留后端返回的全部字段（如 column_name/column_type/column_comment）
      ...col,
      dict_type: col.dict_type || '',
      form_type: col.form_type || 'input',
      query_type: col.query_type || 'eq',
      is_pk: to01(col.is_pk),
      is_list: to01(col.is_list),
      is_query: to01(col.is_query),
      is_required: to01(col.is_required),
      is_export: to01(col.is_export),
      is_import: to01(col.is_import),
      // 排序允许为 0，因此用 ?? 而不是 ||，避免把 0 误判为空
      sort: col.sort ?? 0
    }))
  } finally {
    // 请求结束关闭遮罩，失败提示由请求拦截器统一处理
    loading.value = false
  }
}

// 加载菜单树：供“父级菜单”树形下拉使用，决定生成菜单挂载位置
async function loadMenuTree() {
  const res = await request.get('/system/menu/tree')
  // 后端未返回时兜底空数组，树组件可正常渲染空态
  menuTree.value = res.data || []
}

// 加载字典类型：只取 dict_type 作为下拉选项，页面只需要类型 code，不需要字典明细
async function loadDictTypes() {
  const res = await request.get('/system/dict/data/all')
  // 同一类型可能出现多条字典项，此处未去重，下拉会按返回顺序展示
  dictTypeOptions.value = (res.data || []).map(d => d.dict_type)
}

// ---------- 操作 ----------
// 保存配置：先校验表级必填项，再把表级与字段级数据一次性 PUT 给后端
async function handleSave() {
  // validate() 失败会 reject，函数在此中断，不会提交半成品数据
  await tableFormRef.value.validate()
  saving.value = true
  try {
    // 表级提交体：只包含可编辑字段；id/table_name/table_comment 由后端根据 id 识别并保持不变
    const tablePayload = {
      table_comment: table.table_comment,
      class_name: table.class_name,
      module_name: table.module_name,
      module_comment: table.module_comment,
      url_prefix: table.url_prefix,
      gen_path: table.gen_path,
      parent_menu_id: table.parent_menu_id,
      is_delete_logic: table.is_delete_logic,
      import_enable: table.import_enable,
      export_enable: table.export_enable
    }
    // 字段级提交体：再次归一化开关与默认值，防止行内编辑过程中出现字符串/undefined
    const columnPayload = columns.value.map(col => ({
      // 保留列名、类型等只读属性及其 id
      ...col,
      dict_type: col.dict_type || '',
      is_pk: to01(col.is_pk),
      is_list: to01(col.is_list),
      is_query: to01(col.is_query),
      is_required: to01(col.is_required),
      is_export: to01(col.is_export),
      is_import: to01(col.is_import),
      sort: col.sort ?? 0
    }))
    // 表级与字段级一起提交，后端保证同一事务内更新，避免只存一半
    await request.put(`/gen/table/${tableId}`, { table: tablePayload, columns: columnPayload })
    ElMessage.success('保存成功')
    // 重新拉取详情，用后端归一化后的结果刷新页面（例如默认值、排序回填）
    load()
  } finally {
    saving.value = false
  }
}

// 建表 SQL 弹窗显隐
const ddlVisible = ref(false)
// 建表 SQL 文本内容
const ddlText = ref('')

// 查看建表 SQL：按当前表结构请求 DDL 文本后打开弹窗
async function showDdl() {
  const res = await request.get(`/gen/table/${tableId}/ddl`)
  // 兼容 data 缺失或 ddl 为空，弹窗展示空文本而不是报错
  ddlText.value = (res.data && res.data.ddl) || ''
  ddlVisible.value = true
}

// 下载代码：以 ZIP 流下载整套生成代码
async function handleDownload() {
  // responseType=blob 拿到二进制；生成耗时较长，超时放宽到 120 秒
  const res = await request.get(`/gen/table/${tableId}/download`, { responseType: 'blob', timeout: 120000 })
  // 文件名优先模块标识，其次表名，保证压缩包可识别
  saveBlob(res.data, `${table.module_name || table.table_name}.zip`)
  ElMessage.success('下载成功')
}

// 页面挂载后并行加载：表详情、菜单树、字典类型三个请求互不依赖
onMounted(() => {
  load()
  loadMenuTree()
  loadDictTypes()
})
</script>

<!-- scoped 限定样式只作用于本页面，避免影响其他页面的同名类 -->
<style scoped>
/* 生成信息卡片与下方字段配置卡片之间的间距；14px 与系统列表页卡片间距保持一致 */
.mb14 {
  margin-bottom: 14px;
}

/* 生成选项三个复选框的容器：横向排列，间距 8px；窄屏自动换行，避免文字被挤压 */
.switch-group {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

/* 主键标签与字段名之间的左间距，避免红色标签紧贴文字 */
.ml4 {
  margin-left: 4px;
}

/* 底部操作区：水平居中排列，按钮间距 6px，顶部留 18px 与字段表格分隔 */
.actions {
  display: flex;
  justify-content: center;
  gap: 6px;
  margin-top: 18px;
}
/* 说明：本页样式只涉及间距/布局，未使用颜色或主题变量，因此无需额外适配暗色主题 */
</style>
