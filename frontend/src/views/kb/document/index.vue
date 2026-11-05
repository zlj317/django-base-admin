<!--
  文件级说明：
  职责：知识库「文档列表」管理页——顶部统计卡与常用标签云、中部搜索条件、文档表格（分页），
        支持新建/编辑（弹窗）、阅读（抽屉）、删除与版本查看占位。
  依赖：@/utils/request（统一请求封装）、Element Plus 组件与图标、views/kb/category 的分类数据（通过列表接口读取）。
  被谁使用：知识库菜单下的文档管理路由；本页的分类下拉与统计接口均为独立请求，不依赖其他页面状态。
-->
<template>
  <!-- 页面根容器：app-container 提供统一内边距，kb-wrap 预留底部空白 -->
  <div class="app-container kb-wrap">
    <!-- 页头：标题 + 总数副标题；total 来自列表接口，随分页条件变化 -->
    <div class="page-header">
      <div class="page-title-wrap">
        <!-- 模块标题：本页管理的是知识库文档（正文/标签/权限），区别于分类页 -->
        <h2>文档列表</h2>
        <!-- 副标题：显示当前筛选条件下的总条数，让用户不必看分页器也能知道规模 -->
        <div class="sub">知识库文档 · 共 {{ total }} 篇</div>
      </div>
    </div>

    <!-- 顶部统计卡片 + 标签云 -->
    <!-- 统计卡行：gutter=16 与下方标签/搜索区保持一致的间距 -->
    <el-row :gutter="16" class="stat-row">
      <!-- 单张统计卡：:xs=12 超小屏一屏两卡，:sm=6 小屏以上一屏四卡；
           v-for 直接遍历 statCards 配置，新增指标只需改配置数组；:key 用索引保证渲染稳定 -->
      <el-col :xs="12" :sm="6" v-for="(s, i) in statCards" :key="i">
        <!-- 卡片主体：class 拼接 s.color，便于未来按指标类型定制配色（当前样式仅用 .mini-stat 通用样式） -->
        <div class="mini-stat" :class="'ms-' + s.color">
          <!-- 图标底座：背景取配置里的渐变色串 s.bg，让四张卡视觉上可区分 -->
          <div class="ms-icon" :style="{ background: s.bg }">
            <!-- 动态图标：component :is 渲染配置中的图标组件，避免在模板里写四段 v-if -->
            <el-icon :size="20"><component :is="s.icon" /></el-icon>
          </div>
          <div class="ms-info">
            <!-- 数值：统一走 getStat(key) 取值，配置与数据解耦，缺失时兜底为 0 -->
            <div class="ms-value">{{ getStat(s.key) }}</div>
            <!-- 指标名称：直接取配置 label -->
            <div class="ms-label">{{ s.label }}</div>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- 标签云行：占满整行，展示常用标签及出现次数 -->
    <el-row :gutter="16" class="tag-row">
      <el-col :span="24">
        <el-card shadow="never" class="tags-card">
          <!-- 标签云标题：紫色色标 + 文案，与页内其他面板保持统一装饰语言 -->
          <div class="tags-header">
            <span class="panel-dot dot-purple"></span>
            <span class="tags-title">🏷️ 热门标签</span>
          </div>
          <!-- 标签容器：flex-wrap 让标签随宽度自动换行 -->
          <div class="tags-cloud">
            <!-- 单个标签：key 用标签名（数据里名称唯一）；
                 :color 按索引循环取 tagColors，使相邻标签颜色区分；
                 effect=light 让自定义底色上的文字保持浅色模式；
                 文案展示“名称 × 出现次数” -->
            <el-tag
              v-for="(t, i) in hotTags"
              :key="t.name"
              :color="tagColors[i % tagColors.length]"
              effect="light"
              class="tag-cloud-item"
            >{{ t.name }} × {{ t.count }}</el-tag>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 搜索区：条件直接绑定 query 对象，点查询/回车才发请求，避免每次输入都请求 -->
    <el-card shadow="never" class="search-card">
      <!-- inline 让表单项横向排列；@submit.prevent 阻止表单默认提交（回车时不刷新页面） -->
      <el-form :model="query" inline @submit.prevent>
        <el-form-item label="标题">
          <!-- 标题模糊搜索：clearable 支持清空；@keyup.enter 让回车等价于点“查询”，符合后台列表习惯 -->
          <el-input v-model="query.doc_title" placeholder="请输入标题" clearable style="width: 180px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="分类">
          <!-- 分类筛选：绑定 category_id；filterable 便于分类较多时检索；clearable 表示不限制分类 -->
          <el-select v-model="query.category_id" placeholder="全部" clearable filterable style="width: 160px">
            <!-- 选项来自 /kb/category/list，只取 id 与名称，label 直接展示分类名（这里不体现层级缩进） -->
            <el-option v-for="c in categoryOptions" :key="c.id" :label="c.category_name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <!-- 状态筛选：1=发布、0=草稿，与表格状态标签的取值一致；clearable 表示全部 -->
          <el-select v-model="query.status" placeholder="全部" clearable style="width: 120px">
            <el-option label="发布" :value="1" />
            <el-option label="草稿" :value="0" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <!-- 查询：重置到第 1 页再请求，避免停留在旧页码导致空列表 -->
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <!-- 重置：把 query 恢复初值后同样重新查询 -->
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
          <!-- 新建：打开弹窗，此时 form 已由 openCreate 重置为初值 -->
          <el-button type="primary" :icon="Plus" @click="openCreate">新建文档</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 表格区：展示当前分页条件下的文档，空态用中文提示 -->
    <el-card shadow="never" class="table-card">
      <!-- v-loading 绑定 loading；rows 为当前页数据；stripe 斑马纹；empty-text 空数据文案 -->
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据">
        <!-- 序号列：仅按当前页顺序编号，不参与数据绑定 -->
        <el-table-column type="index" label="序号" width="70" align="center" />
        <!-- 标题列：min-width 保证可读宽度；超长时悬浮显示完整标题 -->
        <el-table-column label="标题" prop="doc_title" min-width="220" show-overflow-tooltip />
        <!-- 分类列：优先显示后端回传的 category_name，缺失时回退 category_id，最后显示“-” -->
        <el-table-column label="分类" min-width="120">
          <template #default="{ row }">{{ row.category_name || row.category_id || '-' }}</template>
        </el-table-column>
        <!-- 标签列：tags 可能是字符串或数组，交给 parseTags 统一成数组后逐个渲染小标签；
             :key 用索引，因为同一文档可能有重复标签 -->
        <el-table-column label="标签" min-width="160">
          <template #default="{ row }">
            <div class="tag-cell">
              <el-tag v-for="(t, i) in parseTags(row.tags)" :key="i" size="small" effect="plain" class="mini-tag">{{ t }}</el-tag>
            </div>
          </template>
        </el-table-column>
        <!-- 作者列：优先显示 author_name，回退 author_id，最后“-” -->
        <el-table-column label="作者" min-width="100">
          <template #default="{ row }">{{ row.author_name || row.author_id || '-' }}</template>
        </el-table-column>
        <!-- 权限列：标签颜色由 permission_type 决定（公开=success、私有=info、其余=warning）；
             文案通过映射表翻译成中文，未知类型直接显示原值。
             注意：这里的映射和颜色只影响展示，实际访问控制由后端按 role_json 校验 -->
        <el-table-column label="权限" width="110" align="center">
          <template #default="{ row }">
            <el-tag :type="row.permission_type === 'public' ? 'success' : (row.permission_type === 'private' ? 'info' : 'warning')" effect="light" size="small">
              {{ { public: '公开', internal: '内部', private: '私有' }[row.permission_type] || row.permission_type || '-' }}
            </el-tag>
          </template>
        </el-table-column>
        <!-- 阅读数：后端已累加好的计数，直接展示 -->
        <el-table-column label="阅读" prop="read_count" width="80" />
        <!-- 版本号：当前值，配合“版本”按钮查看（按钮目前只做提示） -->
        <el-table-column label="版本" prop="version" width="80" />
        <!-- 状态列：1=发布（绿色），其余按草稿（灰色）处理；与搜索区状态值对应 -->
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'info'" effect="light" size="small">
              {{ row.status === 1 ? '发布' : '草稿' }}
            </el-tag>
          </template>
        </el-table-column>
        <!-- 操作列：fixed=right 横向滚动时常驻；op-col 复用全局操作列样式 -->
        <el-table-column label="操作" width="220" fixed="right" class-name="op-col">
          <template #default="{ row }">
            <!-- 编辑：回填整行数据到弹窗 -->
            <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
            <!-- 阅读：打开右侧抽屉展示正文与元信息，不跳转新页面 -->
            <el-button link type="success" @click="handleRead(row)">阅读</el-button>
            <!-- 版本：目前仅提示版本号，版本历史接口尚未接入（占位入口） -->
            <el-button link type="warning" @click="handleVersion(row)">版本</el-button>
            <!-- 删除：二次确认后调用删除接口，并刷新列表与统计 -->
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <!-- 分页器：background 使用带底色样式；v-model 直接绑定 query.page / query.page_size；
           @change 同时覆盖页码与每页条数变化，统一触发 fetchList；
           page-sizes 提供常用档位，多选后仍由后端分页 -->
      <div class="pagination-wrap">
        <el-pagination background layout="total, sizes, prev, pager, next, jumper"
          :total="total" v-model:current-page="query.page" v-model:page-size="query.page_size"
          :page-sizes="[10, 20, 50, 100]" @change="fetchList" />
      </div>
    </el-card>

    <!-- 新建/编辑弹窗：两种模式共用；宽度 760px 是为了容纳双列表单与 12 行正文 -->
    <el-dialog :title="dialogTitle" v-model="dialogVisible" width="760px" top="5vh" :close-on-click-modal="false" destroy-on-close>
      <!-- 表单：formRef 用于提交前校验；rules 只约束标题；label-width=100 让“权限类型”等标签对齐 -->
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <!-- 用栅格把字段排成两列：整行字段（标题/正文/权限配置）占 24，其余占 12 -->
        <el-row :gutter="12">
          <el-col :span="24">
            <!-- 标题：必填；maxlength=200 与后端字段长度对齐 -->
            <el-form-item label="标题" prop="doc_title">
              <el-input v-model="form.doc_title" placeholder="请输入文档标题" maxlength="200" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <!-- 分类：可清空（表示未归类）；filterable 便于分类多时检索；选项复用搜索区同一份 categoryOptions -->
            <el-form-item label="分类" prop="category_id">
              <el-select v-model="form.category_id" placeholder="请选择分类" filterable clearable style="width:100%">
                <el-option v-for="c in categoryOptions" :key="c.id" :label="c.category_name" :value="c.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <!-- 状态：1=发布 0=草稿；新文档默认草稿，避免未写完的内容直接对外可见 -->
            <el-form-item label="状态" prop="status">
              <el-radio-group v-model="form.status">
                <el-radio :value="1">发布</el-radio>
                <el-radio :value="0">草稿</el-radio>
              </el-radio-group>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <!-- 权限类型：public/internal/private 三档，直接对应后端的可见范围判断 -->
            <el-form-item label="权限类型" prop="permission_type">
              <el-select v-model="form.permission_type" placeholder="请选择" style="width:100%">
                <el-option label="公开 public" value="public" />
                <el-option label="内部 internal" value="internal" />
                <el-option label="私有 private" value="private" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <!-- 标签：以逗号分隔的字符串提交，列表展示时由 parseTags 再拆开 -->
            <el-form-item label="标签">
              <el-input v-model="form.tags" placeholder="逗号分隔，如：教程,常见问题" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <!-- 附件ID：关联已上传文件表的主键，前端只传 id 不做上传 -->
            <el-form-item label="附件ID">
              <el-input v-model="form.file_id" placeholder="file_id" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <!-- 版本号：自由文本（如 1.0），便于人工维护文档版本 -->
            <el-form-item label="版本号">
              <el-input v-model="form.version" placeholder="如 1.0" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <!-- 文档内容：当前用纯文本域（占位提示未来升级富文本）；12 行高度保证长文可读；
                 doc-textarea 类把字体设为等宽，便于阅读代码/配置类文档 -->
            <el-form-item label="文档内容" prop="doc_content">
              <el-input v-model="form.doc_content" type="textarea" :rows="12" placeholder="请输入文档正文（后续可升级为富文本编辑器）" class="doc-textarea" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <!-- 权限配置：JSON 字符串原样提交，由后端解析成角色白名单；占位示例用 &quot; 转义双引号 -->
            <el-form-item label="权限配置">
              <el-input v-model="form.role_json" type="textarea" :rows="3" placeholder="角色权限 JSON，如 {&quot;roles&quot;: [&quot;admin&quot;]}" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <!-- 底部按钮：取消关闭弹窗；确定用 saving 控制 loading，提交期间禁止重复点击 -->
      <template #footer>
        <el-button @click="dialogVisible=false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitForm">确定</el-button>
      </template>
    </el-dialog>

    <!-- 阅读抽屉：从右侧滑出展示正文，不打断列表浏览；
         宽度 600px 兼顾长文可读性；destroy-on-close 关闭后销毁内容，避免残留上一篇的滚动位置 -->
    <el-drawer v-model="readVisible" :title="readData.doc_title || '文档阅读'" size="600px" destroy-on-close>
      <!-- 仅在有 id（即已回填数据）时渲染正文，避免打开动画期间出现空壳闪烁 -->
      <div v-if="readData.id" class="read-body">
        <!-- 元信息条：分类/作者/阅读数/创建时间，缺失值统一用“-”或 0 兜底 -->
        <div class="read-meta">
          <span class="rm-item">📁 {{ readData.category_name || readData.category_id || '-' }}</span>
          <span class="rm-item">👤 {{ readData.author_name || readData.author_id || '-' }}</span>
          <span class="rm-item">👁️ {{ readData.read_count || 0 }} 次</span>
          <span class="rm-item">📅 {{ readData.create_time }}</span>
        </div>
        <!-- 正文：纯文本渲染（非 v-html），换行由 .read-content 的 white-space: pre-wrap 保留 -->
        <div class="read-content">{{ readData.doc_content || '（暂无内容）' }}</div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
// 组合式 API：状态与方法均局部于本组件
// ref 用于基础响应式值与模板引用；reactive 用于表单/查询对象；onMounted 负责首屏加载
import { ref, reactive, onMounted } from 'vue'
// ElMessage 做结果提示；ElMessageBox 提供删除二次确认
import { ElMessage, ElMessageBox } from 'element-plus'
// 图标：Search/Refresh/Plus 用于按钮；Document/View/TrendCharts/Tickets 用于四张统计卡
import { Search, Refresh, Plus, Document, TrendCharts, View, Tickets } from '@element-plus/icons-vue'
// 统一请求实例：自动带 token、统一解析 { code, msg, data } 并统一报错
import request from '@/utils/request'

// 表格加载态：控制 el-table 的 v-loading
const loading = ref(false)
// 当前页文档数据（后端分页）
const rows = ref([])
// 总条数：供分页器与页头副标题使用
const total = ref(0)
// 提交中标记：防止弹窗“确定”被连点造成重复创建
const saving = ref(false)
// 弹窗显隐
const dialogVisible = ref(false)
// 弹窗标题：新建/编辑共用弹窗，用标题区分当前模式
const dialogTitle = ref('新建文档')
// el-form 实例：提交前调用 validate
const formRef = ref()
// 分类下拉选项：来自分类列表接口，搜索区与编辑弹窗共用同一份
const categoryOptions = ref([])

// 查询初值：重置时整体恢复，保证页码与所有筛选项回到初始状态
const query_orig = { page: 1, page_size: 10, doc_title: '', category_id: null, status: null }
// 查询对象：reactive 便于 Object.assign 一次性重置；分页器直接 v-model 到 page/page_size
const query = reactive({ ...query_orig })

// 表单初值：新建/重置都基于它；author_id 不在界面上编辑，由后端按当前登录人填充
const form_orig = {
  id: null, doc_title: '', category_id: null, tags: '', author_id: null,
  permission_type: 'public', version: '1.0', status: 0, doc_content: '', file_id: '', role_json: ''
}
// 弹窗表单：reactive 便于就地重置/回填，模板直接双向绑定
const form = reactive({ ...form_orig })

// 校验规则：标题必填，失焦触发；正文允许留空（用于先存草稿的场景）
const rules = { doc_title: [{ required: true, message: '请输入标题', trigger: 'blur' }] }

// 统计
// 统计值容器：key 与 statCards 一一对应；统计接口异常时保留上一次数值
const stats = reactive({ total_documents: 0, total_reads: 0, today_new: 0, published: 0 })
// 统计卡配置：key 取数值、label 显示名称、icon 为图标组件、bg 为图标底座渐变；
// 抽成数组后模板用 v-for 渲染，新增指标只需在此追加一项
const statCards = [
  // 总文档数：列表接口的 total 也会同步写入该字段，保证翻页后数字不消失
  { key: 'total_documents', label: '总文档数', icon: Document, color: 'blue', bg: 'linear-gradient(135deg, var(--chart-1), color-mix(in srgb, var(--chart-1) 72%, #ffffff))' },
  // 总阅读数：由统计接口下发，列表接口不返回
  { key: 'total_reads', label: '总阅读数', icon: View, color: 'purple', bg: 'linear-gradient(135deg, var(--chart-4), color-mix(in srgb, var(--chart-4) 72%, #ffffff))' },
  // 今日新增：按自然日统计，来自统计接口
  { key: 'today_new', label: '今日新增', icon: TrendCharts, color: 'green', bg: 'linear-gradient(135deg, var(--chart-5), color-mix(in srgb, var(--chart-5) 72%, #ffffff))' },
  // 已发布：status=1 的数量，来自统计接口
  { key: 'published', label: '已发布', icon: Tickets, color: 'orange', bg: 'linear-gradient(135deg, var(--chart-3), color-mix(in srgb, var(--chart-3) 72%, #ffffff))' }
]

// 标签云配色：按标签索引循环取色，全部引用主题图表变量，切换主题/暗色时自动跟随
const tagColors = ['var(--chart-1)', 'var(--chart-4)', 'var(--chart-5)', 'var(--chart-3)', 'var(--chart-6)', 'var(--chart-2)', 'var(--chart-6)', 'var(--app-text-3)']
// 热门标签：当前为前端静态示例数据（未接后端接口），仅用于展示标签云；name 同时作为 v-for 的 key
const hotTags = ref([
  { name: '教程', count: 24 },
  { name: 'API', count: 18 },
  { name: '配置', count: 16 },
  { name: '最佳实践', count: 12 },
  { name: 'FAQ', count: 10 },
  { name: '架构', count: 9 },
  { name: '部署', count: 8 },
  { name: '运维', count: 6 }
])

// 阅读抽屉显隐：点击表格“阅读”时打开
const readVisible = ref(false)
// 阅读数据：整行拷贝，抽屉里展示正文与元信息；初始为空对象，靠 v-if=readData.id 控制渲染
const readData = reactive({})

// 取统计值：key 为动态字符串，stats[key] 缺失时统一兜底为 0，避免模板出现 undefined
function getStat(key) { return stats[key] ?? 0 }

// 标签归一化：后端可能返回字符串（逗号分隔）或数组，统一转成字符串数组供 v-for 渲染；
// 中英文逗号都支持，并去掉首尾空白、过滤空项，避免渲染出空标签
function parseTags(tags) {
  if (!tags) return []
  if (Array.isArray(tags)) return tags
  return String(tags).split(/[,，]/).map(t => t.trim()).filter(Boolean)
}

// 拉取当前分页的文档列表：loading 只包住请求与赋值，finally 保证异常时也解除遮罩
async function fetchList() {
  loading.value = true
  try {
    // params 直接传 reactive 的 query，axios 会序列化为 page/page_size/筛选条件
    const res = await request.get('/kb/document/list', { params: query })
    // 兼容后端未返回 list/total 的情况
    rows.value = res.data.list || []
    total.value = res.data.total || 0
    // 更新统计
    // 列表接口的 total 同步给“总文档数”卡：即使统计接口失败，这个数字仍然准确
    stats.total_documents = res.data.total || stats.total_documents
  } finally { loading.value = false }
}

// 加载分类下拉：分类量级小，一次取 500 条；只保留 id 与名称，避免把整棵树的字段带进下拉
// 失败时静默（对应 catch 内的注释），不阻断文档列表主流程
async function loadCategoryOptions() {
  try {
    const res = await request.get('/kb/category/list', { params: { page: 1, page_size: 500 } })
    categoryOptions.value = (res.data.list || []).map(x => ({ id: x.id, category_name: x.category_name }))
  } catch { /* ignore */ }
}

// 加载统计卡数据：独立接口，与列表请求解耦；失败时保留已有数值，避免数字被清零
async function loadStats() {
  try {
    const res = await request.get('/kb/document/stats')
    if (res.data) Object.assign(stats, res.data)
  } catch { /* 统计接口异常时保留已有数值 */ }
}

// 查询：回到第 1 页再请求，避免当前页超出新条件的总页数导致空列表
function handleSearch() { query.page = 1; fetchList() }
// 重置：先整体恢复查询初值（含页码），再走统一的查询流程
function handleReset() { Object.assign(query, query_orig); handleSearch() }

// 新建：恢复表单初值并设置标题；不额外清空 categoryOptions，分类下拉沿用已加载数据
function openCreate() { Object.assign(form, form_orig); dialogTitle.value = '新建文档'; dialogVisible.value = true }
// 编辑：先恢复初值再用整行覆盖，避免上一次编辑的字段残留；行内多余字段一并带入，提交时剔除 id
function openEdit(row) { Object.assign(form, form_orig, row); dialogTitle.value = '编辑文档'; dialogVisible.value = true }

// 提交：先校验，再按有无 id 走更新/新增；成功后关闭弹窗，同时刷新列表与统计（总数/已发布可能变化）
async function submitForm() {
  await formRef.value.validate()
  saving.value = true
  try {
    if (form.id) {
      // 更新：剔除 id（主键已在 URL 中），其余字段整体提交
      const { id, ...data } = form
      await request.put(`/kb/document/update/${id}`, data); ElMessage.success('更新成功')
    } else {
      // 新增：直接提交表单；作者由后端按登录态补全
      await request.post('/kb/document/create', form); ElMessage.success('新建成功')
    }
    dialogVisible.value = false; fetchList(); loadStats()
  } finally { saving.value = false }
}

// 阅读：把整行数据拷贝到 readData（reactive 对象需逐字段覆盖），再打开抽屉
function handleRead(row) {
  Object.assign(readData, { ...row })
  readVisible.value = true
}

// 版本查看：版本历史接口尚未实现，这里只做信息提示，保留入口便于后续接入
function handleVersion(row) {
  ElMessage.info(`查看「${row.doc_title}」版本 v${row.version || '1.0'}（版本历史功能待实现）`)
}

// 删除：二次确认后按 ids 数组提交（axios delete 用 data 传请求体），成功后刷新列表与统计
async function handleDelete(row) {
  await ElMessageBox.confirm(`确定删除文档「${row.doc_title}」？`, '提示', { type: 'warning' })
  await request.delete('/kb/document/delete', { data: { ids: [row.id] } })
  ElMessage.success('删除成功'); fetchList(); loadStats()
}

// 首屏并行发起三个独立请求：列表、分类下拉、统计；任一失败不影响其余（各自内部已兜底）
onMounted(() => { fetchList(); loadCategoryOptions(); loadStats() })
</script>

<style scoped>
/* 页面底部留白：避免最后一排卡片贴住窗口底边 */
.kb-wrap { padding-bottom: 20px; }
/* 统计卡行下间距：与标签云行形成 14px 的呼吸感 */
.stat-row { margin-bottom: 14px; }
/* 标签云行下间距：与搜索卡片分隔 */
.tag-row { margin-bottom: 14px; }

/* 单张统计卡：横向排列图标与数值，背景/边框使用主题变量以适配浅色与暗色 */
.mini-stat {
  display: flex; align-items: center; gap: 12px;
  padding: 16px 18px; background: var(--app-surface); border-radius: 12px;
  border: 1px solid var(--app-border-light); box-shadow: 0 2px 8px rgba(30, 41, 59, 0.04);
  transition: transform 0.15s;
}
/* hover 时轻微上浮，提示卡片可交互（当前点击无行为，仅视觉反馈） */
.mini-stat:hover { transform: translateY(-2px); }
/* 图标底座：固定 44x44 圆角方块，颜色 #fff 保证叠在任意图表色渐变上都可读；flex-shrink=0 防止被文字挤压 */
.ms-icon {
  display: flex; align-items: center; justify-content: center;
  width: 44px; height: 44px; border-radius: 12px; color: #fff; flex-shrink: 0;
}
/* 数值区：flex:1 占据剩余宽度；min-width:0 允许内部超长数字正常收缩而不撑破卡片 */
.ms-info { flex: 1; min-width: 0; }
/* 统计数值：22px 加粗 + 主题一级文字色；tabular-nums 让数字等宽，翻页刷新时不产生横向抖动 */
.ms-value { font-size: 22px; font-weight: 700; color: var(--app-text-1); font-variant-numeric: tabular-nums; }
/* 指标名称：12px 主题二级文字色，弱化于数值 */
.ms-label { font-size: 12px; color: var(--app-text-2); margin-top: 2px; }

/* 标签云卡片：与页面其他卡片统一圆角与浅边框 */
.tags-card { border-radius: 14px; border: 1px solid var(--app-border-light); }
/* 标签云标题：色标+文字横排，加粗 14px；margin-bottom 与标签区拉开距离 */
.tags-header { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; font-weight: 600; font-size: 14px; color: var(--app-text-1); }
/* 紫色竖条色标：本页统一使用紫色渐变作为强调色 */
.panel-dot { width: 4px; height: 16px; border-radius: 3px; background: linear-gradient(180deg, #8b5cf6, #a78bfa); }
/* 标签容器：flex-wrap 让标签随容器宽度自动换行，gap 8px 保持均匀间距 */
.tags-cloud { display: flex; flex-wrap: wrap; gap: 8px; }
/* 单个标签：pointer 光标暗示可点击（当前无点击逻辑）；hover 放大 5% 做轻反馈；固定高度保证行高一致 */
.tag-cloud-item { cursor: pointer; transition: transform 0.15s; font-size: 13px; height: 28px; padding: 0 12px; line-height: 26px; }
/* hover 放大反馈 */
.tag-cloud-item:hover { transform: scale(1.05); }

/* 搜索卡与表格卡：统一 14px 圆角 + 主题浅边框 */
.search-card, .table-card { border-radius: 14px; border: 1px solid var(--app-border-light); }

/* 表格标签单元格：flex-wrap 让多标签自动换行，3px 间距保持紧凑 */
.tag-cell { display: flex; flex-wrap: wrap; gap: 3px; }
/* 单个标签限宽 120px，避免超长标签把表格列撑开 */
.mini-tag { max-width: 120px; }

/* 正文文本域：穿透 Element Plus 内部 textarea，改用等宽字体，便于阅读代码/配置类文档 */
.doc-textarea :deep(textarea) {
  font-family: Menlo, Monaco, Consolas, monospace; font-size: 13px; line-height: 1.8;
}

/* 抽屉内容左右留 6px，避免文字贴边 */
.read-body { padding: 0 6px; }
/* 元信息条：浅色主题面板底 + 圆角，放在正文上方做信息摘要 */
.read-meta { display: flex; flex-wrap: wrap; gap: 14px; margin-bottom: 20px; padding: 12px 14px; background: var(--app-surface-2); border-radius: 8px; }
/* 单条元信息：12px 主题二级文字色，弱化于正文 */
.rm-item { font-size: 12px; color: var(--app-text-2); }
/* 正文：14px 行高 1.9 提升长文可读性；pre-wrap 保留后端文本的换行与空格；
   word-break 防止超长英文/URL 撑破抽屉。
   注意：文字色写死 #374151，未走主题变量，暗色主题下与深色面板对比度偏低 */
.read-content { font-size: 14px; color: #374151; line-height: 1.9; white-space: pre-wrap; word-break: break-word; }
</style>
