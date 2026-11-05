<!--
  文件级说明：
  职责：知识库「文档分类」维护页——左栏用分类树展示自关联层级并支持根级/子级增删改与关键词过滤，
        右栏用表格展示当前选中节点的子树（未选中时展示全量），新建/编辑共用同一个弹窗。
  依赖：@/utils/request（统一请求封装，响应体 res 的 data 为业务数据）、Element Plus 组件与图标、
        @/directive/perm（全局 v-perm，本页未使用按钮级权限指令）。
  被谁使用：知识库菜单下的分类管理路由；本页产出的分类数据同时供 views/kb/document 的分类下拉复用。
-->
<template>
  <!-- 页面根容器：app-container 提供统一页面内边距，kb-wrap 额外预留底部空白，避免内容贴底 -->
  <div class="app-container kb-wrap">
    <!-- 页头：只展示模块标题与一句话定位，本页的新增入口放在左右两张卡片的头部 -->
    <div class="page-header">
      <div class="page-title-wrap">
        <!-- 模块标题：区别于左栏卡片内的“分类目录”，这里表明管理对象是“文档分类” -->
        <h2>文档分类</h2>
        <!-- 副标题：说明本页空间结构（左树右表），降低新用户的理解成本 -->
        <div class="sub">树结构管理 · 左侧分类树 + 右侧文档</div>
      </div>
    </div>

    <!-- 主区域：24 栅格分左右两栏，gutter=16 保证两张卡片之间有留白 -->
    <el-row :gutter="16" class="main-row">
      <!-- 左栏：分类树。
           分类是 parent_id 自关联结构，用树比用表格更直观；节点内直接放操作按钮，
           避免为每个分类单独跳转编辑页。 -->
      <el-col :xs="24" :md="7">
        <!-- 左侧卡片：shadow=never 走扁平风格，与项目其他管理页保持一致 -->
        <el-card shadow="never" class="tree-card">
          <!-- 卡片头插槽：左侧标题，右侧“根级”新建入口 -->
          <template #header>
            <!-- 头布局：两端对齐，标题与按钮之间不会被长文案挤压 -->
            <div class="card-header">
              <!-- 标题区：色标 + 文案，色标用于与右侧蓝色面板区分主次 -->
              <div class="card-title">
                <!-- 4px 紫色竖条（样式见 .panel-dot/.dot-purple），纯视觉装饰 -->
                <span class="panel-dot dot-purple"></span>
                分类目录
              </div>
              <!-- 根级新建：openCreate(null) 传 null 表示没有父级，即创建顶层分类 -->
              <el-button type="primary" size="small" :icon="Plus" @click="openCreate(null)">根级</el-button>
            </div>
          </template>
          <!-- 树工具栏：左侧关键词过滤，右侧手动刷新 -->
          <div class="tree-toolbar">
            <!-- 关键词输入：v-model 同步 treeKeyword；clearable 支持一键清空；
                 @input 每次输入即调用 handleFilterNode → treeRef.filter，做本地即时过滤（不发请求）；
                 固定 180px 是为了给右侧“刷新”按钮留出同一行的空间 -->
            <el-input v-model="treeKeyword" placeholder="搜索分类" clearable style="width: 180px" @input="handleFilterNode" />
            <!-- 刷新：重新拉取全量分类并重建树，用于同步其他人的改动 -->
            <el-button link type="primary" @click="refreshTree">刷新</el-button>
          </div>
          <!-- 树容器：限高滚动（样式 .tree-wrap），分类较多时不会把整页撑高 -->
          <div class="tree-wrap">
            <!-- 分类树：
                 ref=treeRef 供 handleFilterNode 调用树实例的 filter 方法；
                 :data=treeData 由 buildTree 生成（同级已按 sort 升序）；
                 :props 把后端字段 category_name/children 映射成组件需要的 label/children；
                 :filter-node-method 自定义匹配规则（只按分类名称匹配）；
                 node-key=id 给节点稳定标识，用于高亮与定位；
                 default-expand-all 分类层级通常较浅，默认全展开减少点击成本；
                 highlight-current 高亮当前选中节点，与右侧表格形成联动；
                 :expand-on-click-node=false 让点击节点只做“选中”，展开/收起交给左侧箭头，
                 避免每次点选都造成树跳动；
                 @node-click 把选中节点同步到右侧表格 -->
            <el-tree
              ref="treeRef"
              :data="treeData"
              :props="{ label: 'category_name', children: 'children' }"
              :filter-node-method="filterNode"
              node-key="id"
              default-expand-all
              highlight-current
              :expand-on-click-node="false"
              @node-click="handleNodeClick"
            >
              <!-- 节点插槽：node 为树节点包装（含 label），data 为后端原始记录（含 id/children/hideOps） -->
              <template #default="{ node, data }">
                <!-- 单个节点：左侧图标+名称，右侧悬浮操作按钮 -->
                <div class="tree-node">
                  <!-- 左侧：有子节点显示文件夹图标，叶子显示文档图标，让层级一眼可辨 -->
                  <div class="tn-left">
                    <el-icon v-if="data.children && data.children.length"><FolderOpened /></el-icon>
                    <el-icon v-else><Document /></el-icon>
                    <span class="tn-label">{{ node.label }}</span>
                  </div>
                  <!-- 操作区：data.hideOps 为真时不渲染（后端可用它标记不允许维护的系统内置分类） -->
                  <div class="tn-actions" v-if="!data.hideOps">
                    <!-- 新增子分类：以当前节点 id 作父级；@click.stop 阻止冒泡到 node-click，避免顺带切换右侧表格 -->
                    <el-button link size="small" type="primary" @click.stop="openCreate(data.id)">子</el-button>
                    <!-- 编辑当前分类：同样阻止冒泡，保持右侧当前视图不被切换 -->
                    <el-button link size="small" type="primary" @click.stop="openEdit(data)">改</el-button>
                    <!-- 删除当前分类：后端为级联删除，确认文案已明确提示子分类会一起删除 -->
                    <el-button link size="small" type="danger" @click.stop="handleDelete(data)">删</el-button>
                  </div>
                </div>
              </template>
            </el-tree>
          </div>
        </el-card>
      </el-col>

      <!-- 右栏：分类列表表格。
           与左树共用同一份 allNodes 数据：点树节点后只做本地过滤，避免每次点击都请求接口。 -->
      <el-col :xs="24" :md="17">
        <!-- 右侧卡片：与左栏同款扁平卡片，17/24 宽度让表格列有足够展示空间 -->
        <el-card shadow="never" class="table-card">
          <!-- 卡片头：左侧标题+当前选中提示，右侧新增子分类 -->
          <template #header>
            <div class="card-header">
              <!-- 标题区：蓝色色标用于与左侧紫色面板区分主次 -->
              <div class="card-title">
                <span class="panel-dot dot-blue"></span>
                分类列表
                <!-- 当前选中节点提示：仅在点击过树节点后显示；名称为空（理论上的根）时显示“根级” -->
                <el-tag size="small" effect="light" type="info" v-if="selectedNode">
                  当前选中: {{ selectedNode.category_name || '根级' }}
                </el-tag>
              </div>
              <!-- 新增子分类：默认以当前选中节点为父级；未选中时 selectedNode 为 null，
                   ?. 可选链保证不报错，并由 || null 回退为根级新增 -->
              <el-button type="primary" :icon="Plus" @click="openCreate(selectedNode?.id || null)">新增子分类</el-button>
            </div>
          </template>
          <!-- 列表：v-loading 受 loading 控制；tableRows 为“当前子树或全量”，由 loadAll/handleNodeClick 切换；
               stripe 斑马纹便于横向读行；empty-text 用于无数据时的中文空态 -->
          <el-table v-loading="loading" :data="tableRows" stripe empty-text="暂无数据">
            <!-- 序号列：纯展示，不参与数据绑定 -->
            <el-table-column type="index" label="序号" width="70" align="center" />
            <!-- 分类名称：min-width 保证内容不足时也不至于过窄；内容超长时悬浮显示完整文本 -->
            <el-table-column label="分类名称" prop="category_name" min-width="200" show-overflow-tooltip />
            <!-- 父级：parent_name 由前端用 id→名称映射拼装；缺失时依次回退到 parent_id，最后显示“—” -->
            <el-table-column label="父级" min-width="140">
              <template #default="{ row }">{{ row.parent_name || row.parent_id || '—' }}</template>
            </el-table-column>
            <!-- 排序：直接透出后端 sort 值，便于管理员核对左树的先后顺序 -->
            <el-table-column label="排序" prop="sort" width="80" />
            <!-- 状态：开关直接绑定行数据，切换即调用 handleStatusChange 落库，无需再点“保存” -->
            <el-table-column label="状态" width="90" align="center">
              <template #default="{ row }">
                <el-switch v-model="row.status" :active-value="1" :inactive-value="0" @change="handleStatusChange(row)" />
              </template>
            </el-table-column>
            <!-- 创建时间：后端返回已格式化字符串，前端直接展示不再二次处理 -->
            <el-table-column label="创建时间" prop="create_time" width="170" />
            <!-- 操作列：fixed=right 让横向滚动时操作入口常驻右侧；op-col 复用全局操作列样式 -->
            <el-table-column label="操作" width="180" fixed="right" class-name="op-col">
              <template #default="{ row }">
                <!-- 新增子：以本行 id 为父级打开新建弹窗 -->
                <el-button link type="primary" @click="openCreate(row.id)">新增子</el-button>
                <!-- 编辑：把本行数据回填到弹窗表单 -->
                <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
                <!-- 删除：二次确认后调用级联删除接口 -->
                <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <!-- 新建/编辑弹窗：两种模式复用同一个表单，由 dialogTitle 区分；
         入口分别是左树的“根级/子/改”和右表的“新增子分类/新增子/编辑”。 -->
    <el-dialog :title="dialogTitle" v-model="dialogVisible" width="500px" :close-on-click-modal="false" destroy-on-close>
      <!-- 表单：formRef 供提交前 validate；rules 只约束分类名称；label-width=90 让“父级分类”等标签对齐 -->
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <!-- 父级分类：留空即根级（placeholder 已说明）；clearable 允许把子分类改成根级；
             filterable 便于层级较深/分类较多时快速定位；宽度铺满表单项 -->
        <el-form-item label="父级分类">
          <el-select v-model="form.parent_id" placeholder="根级（不选择）" clearable filterable style="width:100%">
            <!-- 选项来自 parentOptions：由树扁平化生成，label 前缀全角空格用于表现层级深度 -->
            <el-option v-for="o in parentOptions" :key="o.id" :label="o.category_name" :value="o.id" />
          </el-select>
        </el-form-item>
        <!-- 分类名称：必填；maxlength=100 与后端字段长度对齐，提前拦截超长输入 -->
        <el-form-item label="分类名称" prop="category_name">
          <el-input v-model="form.category_name" placeholder="请输入分类名称" maxlength="100" />
        </el-form-item>
        <!-- 排序：0~9999，数值越小越靠前（buildTree 对同级按 sort 升序） -->
        <el-form-item label="排序" prop="sort">
          <el-input-number v-model="form.sort" :min="0" :max="9999" />
        </el-form-item>
        <!-- 状态：1=启用 0=停用，取值与表格 el-switch 保持一致 -->
        <el-form-item label="状态" prop="status">
          <el-switch v-model="form.status" :active-value="1" :inactive-value="0" active-text="启用" inactive-text="停用" />
        </el-form-item>
        <!-- 备注：可选，记录分类用途，方便其他管理员理解 -->
        <el-form-item label="备注" prop="remark">
          <el-input v-model="form.remark" type="textarea" :rows="2" placeholder="请输入备注" />
        </el-form-item>
      </el-form>
      <!-- 底部按钮：取消直接关闭弹窗；确定按钮用 saving 控制 loading，提交期间不可重复点击 -->
      <template #footer>
        <el-button @click="dialogVisible=false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitForm">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
// 组合式 API：本页所有状态与方法都只属于该组件，不对外暴露
// ref 用于基础响应式值与模板引用；reactive 用于可整体重置的表单/对象；computed 让父级选项随树自动更新；
// onMounted 负责首屏数据加载
import { ref, reactive, computed, onMounted } from 'vue'
// ElMessage 做轻量结果提示；ElMessageBox 提供删除前的二次确认
import { ElMessage, ElMessageBox } from 'element-plus'
// Plus 用于新建按钮图标；FolderOpened/Document 用于在树节点上区分“有子级/叶子”
import { Plus, FolderOpened, Document } from '@element-plus/icons-vue'
// 统一请求实例：自动注入 token，并把 { code, msg, data } 收敛为 res（错误提示由拦截器统一处理）
import request from '@/utils/request'

// 表格加载态：控制右表的 v-loading 遮罩
const loading = ref(false)
// 提交中标记：避免弹窗“确定”被连点造成重复创建
const saving = ref(false)
// 树数据：由全量列表经 buildTree 生成，直接给 el-tree 使用
const treeData = ref([])
// 全量分类平铺数据：既用于建树，也作为右表默认数据源，避免重复请求
const allNodes = ref([])
// el-tree 实例引用：关键词过滤时调用其内置 filter
const treeRef = ref()
// 树搜索关键词：与输入框双向绑定，filterNode 按它匹配
const treeKeyword = ref('')

// 当前选中树节点：决定右表展示哪棵子树，并作为“新增子分类”的默认父级
const selectedNode = ref(null) // 当前选中的树节点
// 右表数据：默认全量，点击树节点后被替换为对应子树
const tableRows = ref([])

// 表单初值：新建与重置都基于它，保证不会残留上一次编辑的数据
const form_orig = { id: null, parent_id: null, category_name: '', sort: 0, status: 1, remark: '' }
// 弹窗表单：用 reactive 就地重置/回填，模板可直接双向绑定
const form = reactive({ ...form_orig })
// el-form 实例：提交前调用 validate 触发校验
const formRef = ref()
// 弹窗显隐：新建/编辑打开，提交或取消后关闭
const dialogVisible = ref(false)
// 弹窗标题：两种模式共用一个弹窗，靠标题让用户明确当前是新建还是编辑
const dialogTitle = ref('新建分类')

// 校验规则：分类名称必填，失焦触发（与后端非空约束对应）
const rules = { category_name: [{ required: true, message: '请输入分类名称', trigger: 'blur' }] }

// 父级下拉选项：树变化时自动重算，避免手动维护两份数据
const parentOptions = computed(() => flattenOptions(treeData.value))

// 把树按深度优先展开成下拉选项；depth 用全角空格前缀体现层级，避免只看到同名分类分不清父子
function flattenOptions(tree, depth = 0, out = []) {
  // 行首分号防止 ASI 误解析；(tree || []) 对空树做兜底
  ;(tree || []).forEach(n => {
    // 推入下拉项：名称前按 depth 叠加全角空格，形成视觉缩进
    out.push({ id: n.id, category_name: `${'　'.repeat(depth)}${n.category_name}` })
    // 有子级则递归，depth+1 加深一级缩进
    if (n.children?.length) flattenOptions(n.children, depth + 1, out)
  })
  // 返回同一个累积数组，供递归过程与 computed 共用
  return out
}

// 递归构建树：按 parent_id 归组（parent_id 可能为 null/0/undefined，统一收敛成 null），
// 同级按 sort 升序；返回结果直接作为 el-tree 的 data
function buildTree(list, parentId = null) {
  return list
    // 只取当前父级下的直接子节点；根级调用时 parentId=null
    .filter(x => (x.parent_id || null) === parentId)
    // 升序：sort 小的排前面；sort 缺失按 0 处理
    .sort((a, b) => (a.sort || 0) - (b.sort || 0))
    // 递归挂载 children；叶子节点得到空数组，模板据此切换文件夹/文档图标
    .map(x => ({ ...x, children: buildTree(list, x.id) }))
}

// 加载全量分类：分类量级小，一次取 1000 条在前端建树；
// 这样搜索、点树过滤都变成纯本地计算，不再产生额外请求
async function loadAll() {
  loading.value = true
  try {
    // page_size=1000 作为“全量”上限；若分类量未来超过该值，需要改为分页或按需加载
    const res = await request.get('/kb/category/list', { params: { page: 1, page_size: 1000 } })
    // 后端未返回 list 时兜底为空数组，保证后续 buildTree/filter 不报错
    allNodes.value = res.data.list || []
    // 生成树，供左侧 el-tree 使用（父级为 null 即从根开始）
    treeData.value = buildTree(allNodes.value, null)
    // 右表默认展示全量（用户尚未点击任何树节点时）
    tableRows.value = [...allNodes.value]
    // 补 parent_name：列表接口只给 parent_id，这里用 id→名称映射就地拼装，
    // 避免表格每行再单独请求父级；注意下一行会整体重新赋值覆盖此处的临时结果
    const idMap = new Map(allNodes.value.map(n => [n.id, n.category_name]))
    tableRows.value = allNodes.value.map(n => ({
      ...n,
      parent_name: n.parent_id ? idMap.get(n.parent_id) : null
    }))
  } finally { loading.value = false }
}

// 手动刷新：工具栏按钮触发，语义等同重新加载全量
function refreshTree() { loadAll() }

// 点击树节点：记录选中项，并把右表切换为该节点子树，实现“点谁看谁”
function handleNodeClick(data) {
  selectedNode.value = data
  // 筛选该节点及其子节点
  // 递归收集子树 id（含自身）；每次点击都重新遍历，数据量很大时可考虑缓存结果
  const descendants = collectIds(data)
  // 只保留该子树内的记录；n.parent_id === data.id 是兜底条件（collectIds 实际已覆盖全部后代）
  tableRows.value = allNodes.value
    .filter(n => descendants.has(n.id) || n.parent_id === data.id)
    .map(n => {
      // 与 loadAll 一样补父级名称；此处每行都新建 Map，数据量大时可提到 map 外层复用
      const idMap = new Map(allNodes.value.map(x => [x.id, x.category_name]))
      return { ...n, parent_name: n.parent_id ? idMap.get(n.parent_id) : null }
    })
}

// 深度优先收集节点自身与全部后代的 id，返回 Set 便于 O(1) 判定
function collectIds(node) {
  const ids = new Set([node.id])
  // 递归遍历 children；叶子节点 children 为空，walk 不做任何事
  const walk = (arr) => arr.forEach(n => { ids.add(n.id); walk(n.children || []) })
  walk(node.children || [])
  return ids
}

// el-tree 过滤规则：value=关键词，data=节点原始数据；关键词为空时全部保留
function filterNode(value, data) {
  if (!value) return true
  // 仅按分类名称做包含匹配，空名称做兜底避免报错
  return (data.category_name || '').includes(value)
}
// 输入变化即触发：调用树实例内置 filter；treeRef 尚未挂载时用可选链跳过
function handleFilterNode() { treeRef.value?.filter(treeKeyword.value) }

// 新建：parentId 为节点的 id，null 表示根级；先恢复初值再覆盖父级，避免带入上次编辑的内容
function openCreate(parentId) {
  // ?? null：调用方可能传 undefined，统一收敛为 null，后端按“根级”处理
  Object.assign(form, form_orig, { parent_id: parentId ?? null })
  dialogTitle.value = '新建分类'
  dialogVisible.value = true
}

// 编辑：把整行数据覆盖到表单；行里多出的字段（children/parent_name 等）也会被带上，
// 更新时已剔除 id，其余多余字段由后端忽略
function openEdit(row) {
  Object.assign(form, form_orig, row)
  dialogTitle.value = '编辑分类'
  dialogVisible.value = true
}

// 提交：先校验，再按有无 id 走更新/新增；成功后关闭弹窗并重新拉全量（层级可能变化，必须重建树）
async function submitForm() {
  await formRef.value.validate()
  saving.value = true
  try {
    if (form.id) {
      // 更新时剔除 id：主键已在 URL 路径中，避免请求体重复携带
      const { id, ...data } = form
      await request.put(`/kb/category/update/${id}`, data); ElMessage.success('更新成功')
    } else {
      // 新增：直接提交整个表单（id 为 null，后端按新增处理）
      await request.post('/kb/category/create', form); ElMessage.success('新建成功')
    }
    // 关闭弹窗并刷新：父子关系/排序可能变化，不能只改当前行
    dialogVisible.value = false; loadAll()
  } finally { saving.value = false }
}

// 表格状态开关：开关已先改 row.status（乐观更新），这里只负责提交；
// 失败时把 1/0 反转回去，保证界面与后端一致（错误提示由请求拦截器统一弹出）
async function handleStatusChange(row) {
  try {
    await request.put(`/kb/category/update/${row.id}`, { status: row.status })
    ElMessage.success(row.status === 1 ? '已启用' : '已停用')
  } catch { row.status = row.status === 1 ? 0 : 1 }
}

// 删除：先二次确认（后端级联删除，确认文案明确提示子分类会一并删除），再按 ids 数组提交
async function handleDelete(row) {
  await ElMessageBox.confirm(`确定删除分类「${row.category_name}」？子分类将一并删除。`, '提示', { type: 'warning' })
  // axios 的 delete 需要用 data 字段携带请求体
  await request.delete('/kb/category/delete', { data: { ids: [row.id] } })
  ElMessage.success('删除成功'); loadAll(); selectedNode.value = null
}

// 首次挂载加载全量：左树与右表同时就绪
onMounted(loadAll)
</script>

<style scoped>
/* 页面底部留白：避免最后一张卡片贴住窗口底边 */
.kb-wrap { padding-bottom: 20px; }
/* 主行下边距：与页面后续内容（若有）保持统一节奏 */
.main-row { margin-bottom: 16px; }

/* 左树/右表卡片：统一 14px 圆角 + 主题浅边框，弱化卡片存在感、突出内容 */
.tree-card, .table-card { border-radius: 14px; border: 1px solid var(--app-border-light); }
/* 卡片头：两端对齐，标题与操作按钮分别贴左/贴右，gap 防止长标题挤压按钮 */
.card-header { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
/* 卡片标题：加粗 14px + 主题一级文字色，保证浅色/暗色主题下都有足够对比度 */
.card-title { display: flex; align-items: center; gap: 8px; font-weight: 600; font-size: 14px; color: var(--app-text-1); }
/* 面板色标基础形状：4px 宽、16px 高的小竖条，作为标题前的强调装饰 */
.panel-dot { width: 4px; height: 16px; border-radius: 3px; }
/* 左侧分类树用紫色渐变，与右表蓝色形成主次区分 */
.dot-purple { background: linear-gradient(180deg, #8b5cf6, #a78bfa); }
/* 右侧表格用品牌主色到靛蓝的渐变，跟随主题变量 --brand-primary */
.dot-blue { background: linear-gradient(180deg, var(--brand-primary), #6366f1); }

/* 树工具栏：输入框与刷新按钮两端分布，底部留 12px 与树容器分隔 */
.tree-toolbar { display: flex; justify-content: space-between; margin-bottom: 12px; }
/* 树容器：最高 560px 并纵向滚动，分类很多时页面高度保持稳定 */
.tree-wrap { max-height: 560px; overflow-y: auto; }

/* 单个树节点：撑满整行宽度并左右两端对齐，字号 13px 适配紧凑的树列表 */
.tree-node {
  display: flex; align-items: center; justify-content: space-between;
  width: 100%; font-size: 13px;
}
/* 节点左侧：图标与名称水平排列，gap 6px 保持紧凑 */
.tn-left { display: flex; align-items: center; gap: 6px; }
/* 节点名称：主题一级文字色，保证在树的默认底色上可读 */
.tn-label { color: var(--app-text-1); }
/* 操作区默认透明：避免每个节点都常驻 3 个按钮造成视觉噪音；用 0.15s 过渡做淡入 */
.tn-actions { opacity: 0; transition: opacity 0.15s; }
/* 鼠标悬停当前节点时才显示操作按钮，兼顾可发现性与整洁 */
.tree-node:hover .tn-actions { opacity: 1; }

/* 树节点 hover 背景：使用品牌主色浅色变量，浅色/暗色主题自动适配；:deep 用于穿透组件作用域 */
:deep(.el-tree-node__content:hover) { background: var(--brand-primary-soft); }
/* 当前选中节点背景：与 hover 同色表示“已选中”，并覆盖组件默认高亮样式 */
:deep(.el-tree-node.is-current > .el-tree-node__content) { background: var(--brand-primary-soft); }
</style>
