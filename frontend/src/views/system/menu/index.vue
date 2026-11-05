<!-- 菜单管理页（系统管理 / 菜单管理）
     职责：维护后台菜单树——目录(M)、菜单(C)、按钮(F) 三类节点；记录路由地址、组件路径、图标、权限标识、
           显隐与排序。这份数据既驱动侧边栏/动态路由，也是 v-perm 按钮级权限码的来源，是权限模型的源头。
     接口：GET /system/menu/tree（列表与上级菜单树共用）、POST /system/menu/create、
           PUT /system/menu/update/{id}、DELETE /system/menu/delete/{id}。
     依赖：utils/request（统一鉴权与错误提示）、utils/icon（图标名 → Element Plus 组件）、
           store/auth 的 hasPerm（行内"新增"需与节点类型组合判断）、v-perm 指令（按钮级权限）。
     使用方式：由后端菜单表配置的路由（如 /system/menu）动态挂载，需 system:menu:* 权限码。
     说明：本页无 <style> 块，外观全部复用全局 .app-container 等类与 Element Plus 默认表现。 -->
<template>
  <!-- 页面根容器：复用全局 .app-container 的内边距与进场动画 -->
  <div class="app-container">
    <!-- 页头：左侧标题组；本页操作集中在表格工具栏，页头不放置按钮 -->
    <div class="page-header">
      <!-- 标题组容器：统一主标题/副标题排版 -->
      <div class="page-title-wrap">
        <!-- 主标题：与菜单名称一致，帮助用户确认当前模块 -->
        <h2>菜单管理</h2>
        <!-- 副标题：点明本页维护的是目录、菜单、按钮三层结构 -->
        <div class="sub">目录、菜单与按钮权限</div>
      </div>
    </div>
    <!-- 查询栏：菜单树本身是层级结构，筛选条件越少越利于保持树的完整展示，因此只保留名称与状态 -->
    <!-- shadow="never"：弱化查询区，将视觉主体留给菜单树表格 -->
    <el-card shadow="never" class="search-card">
      <!-- inline 横向排列；@submit.prevent 阻止回车触发浏览器默认表单提交 -->
      <el-form inline @submit.prevent>
        <!-- 筛选项：菜单名称，后端按名称过滤（可能导致父节点被过滤掉，具体行为由后端实现） -->
        <el-form-item label="菜单名称">
          <!-- 本页没有 handleSearch（无分页概念），回车直接调用 fetchList；clearable 支持一键清空 -->
          <el-input v-model="query.menu_name" placeholder="请输入菜单名称" clearable style="width: 180px" @keyup.enter="fetchList" />
        </el-form-item>
        <!-- 筛选项：状态；下拉选择，避免手填非法值 -->
        <el-form-item label="状态">
          <!-- status=null 表示全部；清空下拉即回到全部；120px 足够展示选项 -->
          <el-select v-model="query.status" placeholder="全部" clearable style="width: 120px">
            <!-- 0=正常：菜单/按钮参与路由与鉴权 -->
            <el-option label="正常" :value="0" />
            <!-- 1=停用：菜单保留但不再生效（是否隐藏由后端下发菜单时过滤） -->
            <el-option label="停用" :value="1" />
          </el-select>
        </el-form-item>
        <!-- 操作按钮组：查询直接 fetchList（树数据不分页，无需重置页码）；重置清空条件后重新请求 -->
        <el-form-item>
          <!-- 查询：按当前 menu_name/status 重新拉取整棵树 -->
          <el-button type="primary" :icon="Search" @click="fetchList">查询</el-button>
          <!-- 重置：handleReset 清空两个条件后再 fetchList -->
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 表格卡片：菜单树较深，卡片需要给表格留足纵向空间；.table-card 全局类统一内边距与圆角 -->
    <el-card shadow="never" class="table-card">
      <!-- 工具栏：新增顶层节点 + 展开/折叠全部；展开控制针对整棵树，因此放在表格正上方 -->
      <div class="toolbar">
        <!-- 新增（不传父级）：默认创建"目录"（openCreate 内 menu_type 初始为 M）；需 system:menu:create -->
        <el-button v-perm="'system:menu:create'" type="primary" :icon="Plus" @click="openCreate()">新增</el-button>
        <!-- 展开/折叠全部：图标与文案随 expanded 切换；点击后通过重建表格让 default-expand-all 生效 -->
        <el-button plain :icon="expanded ? Minus : Expand" @click="toggleExpand">{{ expanded ? '全部折叠' : '全部展开' }}</el-button>
      </div>

      <!-- 树形表格：:key=tableKey 用于强制重建——Element Plus 的 default-expand-all 只在首次渲染生效，
           展开/折叠切换必须换 key 重新挂载，否则不会重新展开；row-key=id + tree-props 告诉表格用 children 建树；
           v-loading 复用请求状态，避免空树时用户误以为"没有菜单" -->
      <el-table
        :key="tableKey"
        v-loading="loading"
        :data="list"
        row-key="id"
        :tree-props="{ children: 'children' }"
        :default-expand-all="expanded"
      >
        <!-- 序号列：定宽 70 + 居中；树形表格的序号按当前展开后的行顺序计算，仅作视觉参考 -->
        <el-table-column type="index" label="序号" width="70" align="center" />
        <!-- 菜单名称列：树形结构需要展示层级缩进，min-width 180 给缩进和长名称留空间 -->
        <el-table-column label="菜单名称" prop="menu_name" min-width="180" />
        <!-- 图标列：菜单在侧边栏展示的图标，定宽 70 居中，保证多行图标纵向对齐 -->
        <el-table-column label="图标" width="70" align="center">
          <!-- 作用域插槽：把当前行的 icon 名称交给 resolveIcon 解析 -->
          <template #default="{ row }">
            <!-- resolveIcon 返回组件或 null：v-if 先挡掉 null，避免渲染空 <component>；
                 解析逻辑兼容 'User'/'user'/'el-icon-user' 等历史命名，失败则退化为"无图标" -->
            <el-icon v-if="resolveIcon(row.icon)" :size="16"><component :is="resolveIcon(row.icon)" /></el-icon>
          </template>
        </el-table-column>
        <!-- 类型列：M=目录 / C=菜单 / F=按钮，用标签颜色区分层级（warning/success/info），定宽 80 居中 -->
        <el-table-column label="类型" width="80" align="center">
          <!-- 作用域插槽：把当前行的 menu_type 交给两个映射函数 -->
          <template #default="{ row }">
            <!-- typeTag 决定颜色、typeLabel 决定文案；size=small 与表格密度匹配 -->
            <el-tag :type="typeTag(row.menu_type)" size="small">{{ typeLabel(row.menu_type) }}</el-tag>
          </template>
        </el-table-column>
        <!-- 路由地址列：菜单在浏览器中的 path 片段（如 system/user）；min-width 保证长路径可读，超长用 tooltip -->
        <el-table-column label="路由地址" prop="path" min-width="120" show-overflow-tooltip />
        <!-- 组件路径列：相对 src/views 的组件位置，只有 C（菜单）类型才有值；给更宽下限以容纳完整路径 -->
        <el-table-column label="组件路径" prop="component" min-width="160" show-overflow-tooltip />
        <!-- 权限标识列：perms 形如 system:user:list，与 v-perm / 后端注解里的权限码一一对应 -->
        <el-table-column label="权限标识" prop="perms" min-width="160" show-overflow-tooltip />
        <!-- 排序列：数字越小越靠前，定宽 70 + 居中便于纵向比较 -->
        <el-table-column label="排序" prop="order_num" width="70" align="center" />
        <!-- 可见列：控制菜单是否出现在侧边栏；隐藏的菜单仍可通过路由访问（与"停用"语义不同） -->
        <el-table-column label="可见" width="80" align="center">
          <!-- 作用域插槽：后端 visible 可能是数字 1 或字符串 '1'，统一转字符串后再比较 -->
          <template #default="{ row }">
            <!-- visible='1' 用 info（灰）标签，降低存在感；显示状态用 success（绿），快速区分 -->
            <el-tag :type="String(row.visible) === '1' ? 'info' : 'success'" size="small">
              <!-- 文案与颜色同源判断，避免标签颜色与文字含义不一致 -->
              {{ String(row.visible) === '1' ? '隐藏' : '显示' }}
            </el-tag>
          </template>
        </el-table-column>
        <!-- 状态列：0 正常 / 1 停用；停用会参与后端菜单下发过滤，影响路由与权限 -->
        <el-table-column label="状态" width="80" align="center">
          <!-- 作用域插槽：按当前行 status 决定标签颜色与文案 -->
          <template #default="{ row }">
            <!-- 0 绿色"正常"，非 0 红色"停用"；size=small 与表格密度匹配 -->
            <el-tag :type="row.status === 0 ? 'success' : 'danger'" size="small">
              {{ row.status === 0 ? '正常' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <!-- 操作列：fixed=right 横向滚动时始终可见；200px 容纳行内"新增/编辑/删除"三个文字按钮 -->
        <el-table-column label="操作" width="200" fixed="right">
          <!-- 作用域插槽：行内新增需要父级节点信息，编辑/删除需要当前节点 -->
          <template #default="{ row }">
            <!-- 行内新增：F（按钮）节点不能再挂子项，因此类型条件先挡住；
                 这里用 v-if + hasPerm 而不用 v-perm，是因为需要与"非按钮"条件组合判断，指令无法表达与逻辑 -->
            <el-button
              v-if="row.menu_type !== 'F' && hasPerm('system:menu:create')"
              link
              type="primary"
              @click="openCreate(row)"
            >新增</el-button>
            <!-- 编辑：需 system:menu:update；openEdit 回填当前行全部字段 -->
            <el-button v-perm="'system:menu:update'" link type="primary" @click="openEdit(row)">编辑</el-button>
            <!-- 删除：danger 色；需 system:menu:delete；子节点是否允许级联删除由后端决定 -->
            <el-button v-perm="'system:menu:delete'" link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新增/编辑弹窗：菜单字段按类型动态显隐，同一表单承载三种节点，避免维护三套弹窗 -->
    <!-- destroy-on-close：关闭即销毁，清空校验状态与残留输入（尤其是类型切换后的隐藏字段） -->
    <el-dialog v-model="formVisible" :title="form.id ? '编辑菜单' : '新增菜单'" width="600px" destroy-on-close>
      <!-- 表单：ref 供 handleSave 调 validate；label-width=90 对齐"菜单类型""组件路径"等四字标签 -->
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <!-- 字段：菜单类型，决定后续显示哪些字段（M 目录 / C 菜单 / F 按钮） -->
        <el-form-item label="菜单类型" prop="menu_type">
          <!-- 单选按钮组：用分段按钮而非下拉，让三种类型一眼可见，也便于理解层级关系 -->
          <el-radio-group v-model="form.menu_type">
            <!-- M=目录：只做分组容器，不渲染页面、通常不配置权限标识 -->
            <el-radio-button value="M">目录</el-radio-button>
            <!-- C=菜单：对应一个前端页面，需要组件路径，可配置权限标识 -->
            <el-radio-button value="C">菜单</el-radio-button>
            <!-- F=按钮：页面内的操作权限点，只配置权限标识，不出现在侧边栏、不能再挂子项 -->
            <el-radio-button value="F">按钮</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <!-- 字段：上级菜单；parent_id=0 表示根目录，由 parentTree 中的虚拟根节点承载 -->
        <el-form-item label="上级菜单" prop="parent_id">
          <!-- 树选择：:data=parentTree（完整菜单树 + 虚拟根节点）；
               :props 把 menu_name/children 映射为 label/children；node-key=id 让 v-model 存 id；
               check-strictly 允许选择任意层级（目录、菜单都能作为父级）；
               filterable 支持按名称搜索；default-expand-all 展开即全展开，方便定位父级；
               100% 宽度撑满表单 -->
          <el-tree-select
            v-model="form.parent_id"
            :data="parentTree"
            :props="{ label: 'menu_name', children: 'children' }"
            node-key="id"
            check-strictly
            filterable
            default-expand-all
            style="width: 100%"
          />
        </el-form-item>
        <!-- 字段：菜单名称，侧边栏与权限树中展示的文字，必填 -->
        <el-form-item label="菜单名称" prop="menu_name">
          <!-- trim 去首尾空格；maxlength 30 与后端字段长度一致 -->
          <el-input v-model.trim="form.menu_name" placeholder="请输入菜单名称" maxlength="30" />
        </el-form-item>
        <!-- 字段：图标；按钮不出现在侧边栏，因此 F 类型隐藏该字段，减少无效录入 -->
        <el-form-item v-if="form.menu_type !== 'F'" label="图标" prop="icon">
          <!-- 输入 Element Plus 图标组件名（如 User / Setting）；clearable 支持移除图标 -->
          <el-input v-model.trim="form.icon" placeholder="Element Plus 图标名，如 User / Setting" clearable>
            <!-- 后缀插槽做实时预览：输入图标名后立刻看到效果，避免保存后才发现名字拼错；
                 iconComp 由 computed 解析，解析失败为 null，v-if 挡住空图标 -->
            <template #append>
              <el-icon v-if="iconComp"><component :is="iconComp" /></el-icon>
            </template>
          </el-input>
        </el-form-item>
        <!-- 字段：路由地址；按钮没有页面路由，因此 F 类型隐藏；目录与菜单需要 path 片段 -->
        <el-form-item v-if="form.menu_type !== 'F'" label="路由地址" prop="path">
          <!-- placeholder 演示 "system / user" 的拼接方式；具体是相对路径还是完整路径由后端路由生成逻辑决定 -->
          <el-input v-model.trim="form.path" placeholder="如 system / user" />
        </el-form-item>
        <!-- 字段：组件路径；只有 C（菜单）需要真正渲染页面组件，目录仅是分组，按钮无页面 -->
        <el-form-item v-if="form.menu_type === 'C'" label="组件路径" prop="component">
          <!-- 相对 src/views 的路径，如 system/user/index；后端据此交给前端动态 import -->
          <el-input v-model.trim="form.component" placeholder="相对 src/views，如 system/user/index" />
        </el-form-item>
        <!-- 字段：权限标识；目录不参与按钮级鉴权，因此只在 C/F 类型展示 -->
        <el-form-item v-if="form.menu_type !== 'M'" label="权限标识" prop="perms">
          <!-- 形如 system:user:list，需与后端鉴权注解、v-perm 指令使用的权限码完全一致 -->
          <el-input v-model.trim="form.perms" placeholder="如 system:user:list" />
        </el-form-item>
        <!-- 字段：显示排序，同层级内按此升序排列；所有类型都需要，因此不按类型显隐 -->
        <el-form-item label="显示排序" prop="order_num">
          <!-- 数字输入：min 0 / max 999；controls-position=right 把加减按钮收到右侧，不挤占标签区域 -->
          <el-input-number v-model="form.order_num" :min="0" :max="999" controls-position="right" />
        </el-form-item>
        <!-- 字段：是否显示；按钮不出现在侧边栏，因此 F 类型隐藏该字段（visible 对其无意义） -->
        <el-form-item v-if="form.menu_type !== 'F'" label="是否显示" prop="visible">
          <!-- 单选组明确"显示/隐藏"；注意与"菜单状态"不同：隐藏只是不在侧边栏出现，停用则整体不生效 -->
          <el-radio-group v-model="form.visible">
            <!-- 0=显示：出现在侧边栏 -->
            <el-radio :value="0">显示</el-radio>
            <!-- 1=隐藏：不显示在侧边栏，但仍可按路由访问（如详情页） -->
            <el-radio :value="1">隐藏</el-radio>
          </el-radio-group>
        </el-form-item>
        <!-- 字段：菜单状态；当前实现对 F（按钮）类型隐藏该字段，按钮节点的状态由后端默认逻辑处理 -->
        <el-form-item v-if="form.menu_type !== 'F'" label="菜单状态" prop="status">
          <!-- 单选组：0 正常 / 1 停用，与列表标签的取值保持一致 -->
          <el-radio-group v-model="form.status">
            <!-- 0=正常 -->
            <el-radio :value="0">正常</el-radio>
            <!-- 1=停用：后端下发菜单时会过滤，按钮权限也随之失效 -->
            <el-radio :value="1">停用</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <!-- 弹窗底部：取消放弃，确定先校验再按 id 分流提交；saving 防止重复点击 -->
      <template #footer>
        <!-- 取消：直接关闭，不做脏数据提示 -->
        <el-button @click="formVisible = false">取 消</el-button>
        <!-- 确定：handleSave 内部先 validate，校验失败不发请求 -->
        <el-button type="primary" :loading="saving" @click="handleSave">确 定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
// 逻辑区总述：<script setup> 顶层变量/函数自动暴露给模板；请求统一走 utils/request（token 注入与错误提示在拦截器完成）
// Vue 组合式 API：computed 让上级菜单树与图标预览随表单自动更新；onMounted 拉首屏树；reactive/ref 管理状态与实例
import { computed, onMounted, reactive, ref } from 'vue'
// Element Plus 命令式反馈：ElMessage 成功提示、ElMessageBox 删除二次确认
import { ElMessage, ElMessageBox } from 'element-plus'
// 图标组件：工具栏的 +/展开/折叠图标；:icon 需要组件对象而非字符串
import { Search, Refresh, Plus, Expand, Minus } from '@element-plus/icons-vue'
// 统一请求实例：baseURL=/api，自动携带 token，响应解包与统一错误提示
import request from '@/utils/request'
// 图标名解析工具：把后端存的图标字符串解析成 Element Plus 组件，解析失败返回 null（静默降级为无图标）
import { resolveIcon } from '@/utils/icon'
// 按钮级权限判断：用于行内"新增"按钮（需与"非按钮节点"条件组合，v-perm 指令无法表达与逻辑）
import { hasPerm } from '@/store/auth'

// 表格加载态：整棵菜单树一次拉取，请求期间遮罩，避免用户对旧树做增删改
const loading = ref(false)
// 提交态：新增/编辑弹窗使用，控制按钮 loading 与防重复提交
const saving = ref(false)
// 菜单树数据：接口直接返回树形数组（含 children），表格靠 row-key + tree-props 渲染
const list = ref([])
// 查询条件：name 与 status；树数据不分页，因此没有 page/pageSize
const query = reactive({ menu_name: '', status: null })
// 展开状态：驱动"全部展开/全部折叠"按钮文案与表格 default-expand-all
const expanded = ref(false)
// 表格 key：default-expand-all 只在首次渲染生效，切换展开状态时必须换 key 让表格重建
const tableKey = ref(0)

// 类型 → 中文：M 目录 / C 菜单 / F 按钮；未识别的类型统一兜底为"按钮"，避免表格出现空白标签
function typeLabel(t) {
  // 三元嵌套按 M→C→其余(F) 的顺序判断
  return t === 'M' ? '目录' : t === 'C' ? '菜单' : '按钮'
}
// 类型 → 标签颜色：目录用 warning（橙，层级较粗） / 菜单用 success（绿，可落地页面） / 按钮用 info（灰，权限点）
function typeTag(t) {
  // 颜色与 typeLabel 的判断顺序保持一致，避免同一类型两处判断口径不同
  return t === 'M' ? 'warning' : t === 'C' ? 'success' : 'info'
}

// 切换展开/折叠：先翻转状态，再自增 tableKey 触发 el-table 重新挂载
function toggleExpand() {
  // 翻转布尔值，模板据此切换图标与文案
  expanded.value = !expanded.value
  // 换 key 强制重建表格，让新的 default-expand-all 生效（Element Plus 不会响应式地重算展开态）
  tableKey.value++
}

// ---------- 列表 ----------
// 列表区：整棵菜单树一次性返回，没有分页；查询条件变化只影响后端过滤结果
async function fetchList() {
  // 请求前置 loading，遮罩整个树表格
  loading.value = true
  // try/finally：错误提示由 request 拦截器负责，这里只保证 loading 复位
  try {
    // GET /system/menu/tree：返回带 children 的树形数组；params 直接展开查询条件
    const res = await request.get('/system/menu/tree', { params: { ...query } })
    // 兜底空数组，保证 el-table 收到合法数据（空树时显示"暂无数据"）
    list.value = res.data || []
  } finally {
    // 成功或失败都收起遮罩
    loading.value = false
  }
}

// 重置：清空名称与状态后重新拉取；不做脏数据确认，因为查询条件改动无副作用
function handleReset() {
  // 清空名称关键字
  query.menu_name = ''
  // 状态回到"全部"（null 会被 axios 忽略）
  query.status = null
  // 按空条件重新请求整棵树
  fetchList()
}

// ---------- 新增/编辑 ----------
// 新增/编辑区：三种节点共用一份表单，按 menu_type 动态显隐字段；打开前必须 resetForm 防止残留
// 弹窗显隐：模板 el-dialog 的 v-model
const formVisible = ref(false)
// 表单实例：handleSave 通过它调用 validate
const formRef = ref()
// 表单模型：字段与后端菜单 DTO 一致；id=null 代表新增，有值代表编辑
const form = reactive({
  // 主键：编辑标志与 update 路径参数
  id: null,
  // 上级菜单 id：0 表示根目录（与 parentTree 的虚拟根节点对应）
  parent_id: 0,
  // 菜单类型：新增默认 M（目录），openCreate 会按父级类型推断更合适的默认值
  menu_type: 'M',
  // 菜单名称：侧边栏/权限树展示文字，必填
  menu_name: '',
  // 图标名：仅非按钮类型使用
  icon: '',
  // 路由地址：按钮无路由，故 F 类型不展示
  path: '',
  // 组件路径：仅 C（菜单）使用
  component: '',
  // 权限标识：仅 C/F 使用，与后端鉴权码对齐
  perms: '',
  // 显示顺序：同层排序，数字越小越靠前
  order_num: 0,
  // 是否显示：0 显示 / 1 隐藏（隐藏仍可按路由访问）
  visible: 0,
  // 状态：0 正常 / 1 停用
  status: 0
})

// 路由地址自定义校验：闭包读取 form.menu_type，因为 rules 是静态对象，需要随类型变化的规则
const validatePath = (rule, value, callback) => {
  // 非按钮类型必须有路由地址；按钮（F）不需要 path，直接放行
  if (form.menu_type !== 'F' && !value) {
    // 返回错误：表单项展示"请输入路由地址"
    return callback(new Error('请输入路由地址'))
  }
  // 通过校验
  callback()
}

// 校验规则：类型/上级菜单/名称必填；路由地址走自定义校验（按类型动态判断）
const rules = {
  // 类型必填：change 触发（单选按钮组没有 blur 语义）
  menu_type: [{ required: true, message: '请选择菜单类型', trigger: 'change' }],
  // 上级菜单必填：change 触发；新增时 parent_id 预填 0（根目录），因此不会拦住正常新增
  parent_id: [{ required: true, message: '请选择上级菜单', trigger: 'change' }],
  // 名称必填：失焦校验
  menu_name: [{ required: true, message: '请输入菜单名称', trigger: 'blur' }],
  // 路由地址：自定义校验，失焦触发
  path: [{ validator: validatePath, trigger: 'blur' }]
}

// 上级菜单树：在真实菜单树顶部虚拟出一个 id=0 的"根目录"节点。
// 原因：后端用 parent_id=0 表示顶层，但 el-tree-select 需要一个可勾选的节点才能表达"放到根目录"；
// 直接复用 list 会让用户无法把已有节点改回顶层。注意：这里引用的是完整 list，编辑时也包含当前节点自身。
const parentTree = computed(() => [
  // 虚拟根节点：id=0 与后端"顶层"约定一致；children 指向当前菜单树
  { id: 0, menu_name: '根目录', children: list.value }
])

// 图标实时预览：form.icon 变化时重新解析为组件；解析失败返回 null，模板用 v-if 兜底
const iconComp = computed(() => resolveIcon(form.icon))

// 重置表单：逐字段恢复默认值，保持 reactive 引用；被 openCreate 与 openEdit 复用
function resetForm() {
  // id 置空 → 提交时走新增分支
  form.id = null
  // 上级默认根目录（0），与虚拟根节点对应
  form.parent_id = 0
  // 默认建目录：对应工具栏"新增"按钮的语义
  form.menu_type = 'M'
  // 名称清空
  form.menu_name = ''
  // 图标清空，避免复用上一次的图标名
  form.icon = ''
  // 路由地址清空
  form.path = ''
  // 组件路径清空
  form.component = ''
  // 权限标识清空
  form.perms = ''
  // 排序回到 0
  form.order_num = 0
  // 默认显示（0）
  form.visible = 0
  // 默认正常（0）
  form.status = 0
}

// 新增入口：工具栏调用时不传 parent（建目录）；行内"新增"会传入父节点，并按父级类型推断子级类型
function openCreate(parent) {
  // 先重置，保证弹窗渲染的是干净数据
  resetForm()
  // 有父级 → 记录上级并推荐类型
  if (parent) {
    // 上级菜单设为当前行 id
    form.parent_id = parent.id
    // 目录下默认建菜单(C)，菜单下默认建按钮(F)；用户仍可在弹窗里手动切换
    form.menu_type = parent.menu_type === 'M' ? 'C' : 'F'
  }
  // 数据就绪后打开弹窗
  formVisible.value = true
}

// 编辑入口：直接用行数据回填，不再请求详情（树接口已返回全部编辑字段）
function openEdit(row) {
  // 先重置，清掉上一次切换类型后残留在隐藏字段里的值
  resetForm()
  // Object.assign 保持 form 引用不变
  Object.assign(form, {
    // 主键：进入编辑模式
    id: row.id,
    // 上级菜单：?? 只对 null/undefined 兜底为 0，不会把合法的 id 误判
    parent_id: row.parent_id ?? 0,
    // 类型：M/C/F
    menu_type: row.menu_type,
    // 名称
    menu_name: row.menu_name,
    // 图标：后端可能返回 null，用 || '' 适配输入框
    icon: row.icon || '',
    // 路由地址：同上兜底空串
    path: row.path || '',
    // 组件路径：目录/按钮通常为空
    component: row.component || '',
    // 权限标识：目录通常为空
    perms: row.perms || '',
    // 排序
    order_num: row.order_num,
    // 是否显示：0 显示 / 1 隐藏
    visible: row.visible,
    // 状态：0 正常 / 1 停用
    status: row.status
  })
  // 回填完成后打开弹窗
  formVisible.value = true
}

// 保存：三种节点共用一份 payload；注意类型切换后已隐藏的字段仍会携带表单里的当前值
async function handleSave() {
  // 校验失败会 reject，后续提交不会执行
  await formRef.value.validate()
  // 进入提交态，防止重复点击
  saving.value = true
  // try/finally：失败由 request 统一提示，这里只复位 saving
  try {
    // payload：字段名与后端入参一一对应；隐藏字段（如 F 的 path）仍会提交其当前值
    const payload = {
      // 上级菜单 id（0=根目录）
      parent_id: form.parent_id,
      // 节点类型 M/C/F
      menu_type: form.menu_type,
      // 菜单名称
      menu_name: form.menu_name,
      // 图标名（F 类型通常为空）
      icon: form.icon,
      // 路由地址（F 类型通常为空）
      path: form.path,
      // 组件路径（仅 C 有值）
      component: form.component,
      // 权限标识（仅 C/F 有值）
      perms: form.perms,
      // 显示顺序
      order_num: form.order_num,
      // 是否显示
      visible: form.visible,
      // 状态
      status: form.status
    }
    // 有 id → 编辑
    if (form.id) {
      // PUT /system/menu/update/{id}：id 走路径，payload 走 body
      await request.put(`/system/menu/update/${form.id}`, payload)
      // 成功提示
      ElMessage.success('修改成功')
    } else {
      // 无 id → 新增
      await request.post('/system/menu/create', payload)
      // 成功提示
      ElMessage.success('新增成功')
    }
    // 成功后关闭弹窗（失败保持打开便于修正）
    formVisible.value = false
    // 重新拉取整棵树：增改会改变层级与排序，本地插入难以保证顺序一致
    fetchList()
  } finally {
    // 复位提交态
    saving.value = false
  }
}

// ---------- 删除 ----------
// 删除：本页采用"id 走路径"的接口风格，与其他模块 delete + ids body 的写法不同，改动时需与后端保持一致
async function handleDelete(row) {
  // 二次确认：带菜单名，避免删错节点；type=warning 呈现警示色
  await ElMessageBox.confirm(`确定删除菜单「${row.menu_name}」吗？`, '提示', { type: 'warning' })
  // DELETE /system/menu/delete/{id}：无需请求体；子节点是否级联删除由后端决定
  await request.delete(`/system/menu/delete/${row.id}`)
  // 成功提示
  ElMessage.success('删除成功')
  // 刷新整棵树，移除被删节点及其可能被级联删除的子节点
  fetchList()
}

// 挂载后拉取整棵菜单树；本页无分页，首屏只需这一个请求
onMounted(fetchList)
</script>
