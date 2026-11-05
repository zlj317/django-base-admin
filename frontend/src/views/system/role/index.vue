<!-- 角色管理页（系统管理 / 角色管理）
     职责：维护角色档案（名称、权限字符、显示顺序、数据范围、状态、备注），并为角色分配菜单/按钮权限。
     接口：GET /system/role/list、POST /system/role/create、PUT /system/role/update/{id}、DELETE /system/role/delete、
           GET /system/menu/tree（分配权限时的菜单树）、GET /system/role/menu_ids/{id}（该角色已有权限）、
           PUT /system/role/assign_menus/{id}。
     依赖：utils/request（统一鉴权与错误提示）、v-perm 指令（按钮级权限）、Element Plus 的卡片/表格/表单/弹窗/树。
     使用方式：由后端菜单表配置的路由（如 /system/role）动态挂载，需 system:role:* 权限码。
     说明：本页没有 <style> 块，外观全部复用全局 .app-container/.search-card/.table-card 等样式与 Element Plus 默认表现。 -->
<template>
  <!-- 页面根容器：复用全局 .app-container 的内边距与进场动画，保证与用户/菜单管理页留白一致 -->
  <div class="app-container">
    <!-- 页头：左侧标题组，本页无页头级操作按钮 -->
    <div class="page-header">
      <!-- 标题组容器：全局样式统一控制主标题与副标题的字号、颜色与间距 -->
      <div class="page-title-wrap">
        <!-- 主标题：与菜单名称一致，帮助用户确认当前模块 -->
        <h2>角色管理</h2>
        <!-- 副标题：点明本页两大能力——分配菜单权限与设定数据范围 -->
        <div class="sub">角色权限与数据范围</div>
      </div>
    </div>
    <!-- 查询栏：角色列表通常不长，只保留"名称 + 状态"两个最常用条件，查询区保持一行不折行 -->
    <!-- shadow="never"：去掉卡片阴影，弱化辅助区域，让表格成为页面主体 -->
    <el-card shadow="never" class="search-card">
      <!-- inline 横向排列；@submit.prevent 阻止回车触发的浏览器默认表单提交 -->
      <el-form inline @submit.prevent>
        <!-- 筛选项：角色名称（如"管理员""运营"），后端按名称模糊匹配 -->
        <el-form-item label="角色名称">
          <!-- clearable 一键清空；@keyup.enter 回车即查询；180px 比状态下拉略宽，容纳较长的角色名输入 -->
          <el-input v-model="query.role_name" placeholder="请输入角色名称" clearable style="width: 180px" @keyup.enter="handleSearch" />
        </el-form-item>
        <!-- 筛选项：状态；用下拉而非输入，避免非法值，并提供"全部"语义 -->
        <el-form-item label="状态">
          <!-- status=null 表示全部；清空下拉即回到全部；120px 足够展示三种选项文案 -->
          <el-select v-model="query.status" placeholder="全部" clearable style="width: 120px">
            <!-- 0=正常：角色可被正常分配给用户 -->
            <el-option label="正常" :value="0" />
            <!-- 1=停用：角色保留但不再参与授权（具体行为由后端鉴权决定） -->
            <el-option label="停用" :value="1" />
          </el-select>
        </el-form-item>
        <!-- 操作按钮组：查询 / 重置，置于筛选项之后，符合先填条件再执行的顺序 -->
        <el-form-item>
          <!-- 查询：回到第一页并重新请求 -->
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <!-- 重置：清空名称与状态后重新查询 -->
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 表格卡片：查询条件与表格分卡；.table-card 全局类统一圆角、内边距与工具栏贴合度 -->
    <el-card shadow="never" class="table-card">
      <!-- 工具栏：新增与批量删除；批量删除依赖表格选中项，因此放在表格正上方 -->
      <div class="toolbar">
        <!-- 新增：需 system:role:create；openCreate 直接逐字段重置后开弹窗（角色页只有这一处需要初始化表单） -->
        <el-button v-perm="'system:role:create'" type="primary" :icon="Plus" @click="openCreate">新增</el-button>
        <!-- 批量删除：需 system:role:delete；plain 弱化红色块；未选中行时禁用，避免空提交 -->
        <el-button v-perm="'system:role:delete'" type="danger" plain :icon="Delete" :disabled="!selection.length" @click="handleBatchDelete">批量删除</el-button>
      </div>

      <!-- 表格：stripe 隔行变色；empty-text 中文空态；v-loading 复用请求状态；@selection-change 同步选中行给批量删除 -->
      <el-table stripe empty-text="暂无数据" v-loading="loading" :data="list" @selection-change="onSelectionChange">
        <!-- 序号列：定宽 70 + 居中，只承载当前页行号，用于快速定位到某一行 -->
        <el-table-column type="index" label="序号" width="70" align="center" />
        <!-- 多选列：固定 50px 只放复选框，不参与自适应，保证不同窗口宽度下列宽稳定 -->
        <el-table-column type="selection" width="50" />
        <!-- 角色名称列：min-width 保证窄屏可读；超长名称用 tooltip 展示完整值而不断行破坏行高 -->
        <el-table-column label="角色名称" prop="role_name" min-width="130" show-overflow-tooltip />
        <!-- 权限字符列：role_key 是后端鉴权用的角色标识（如 admin），与给人看的 role_name 不同，等宽相邻便于对照 -->
        <el-table-column label="权限字符" prop="role_key" min-width="130" show-overflow-tooltip />
        <!-- 显示顺序列：数字越小越靠前，定宽 90 + 居中便于纵向比较大小 -->
        <el-table-column label="显示顺序" prop="role_sort" width="90" align="center" />
        <!-- 数据范围列：后端存数字枚举，这里通过 dataScopeLabel 统一转成中文，避免用户记忆枚举含义 -->
        <el-table-column label="数据范围" width="150" align="center">
          <!-- 作用域插槽：把当前行的 data_scope 传给映射函数；命中不到时函数返回 '-' -->
          <template #default="{ row }">{{ dataScopeLabel(row.data_scope) }}</template>
        </el-table-column>
        <!-- 状态列：用标签而非开关，因为角色启停用影响所有关联用户，不适合在列表里一键切换；定宽 90 居中 -->
        <el-table-column label="状态" width="90" align="center">
          <!-- 作用域插槽：按当前行 status 计算标签类型与文案 -->
          <template #default="{ row }">
            <!-- 0 用 success（绿）、非 0 用 danger（红）：颜色先于文字传达状态；size=small 匹配表格行高 -->
            <el-tag :type="row.status === 0 ? 'success' : 'danger'" size="small">
              <!-- 文案与颜色同源判断，避免"绿色标签写停用"的自相矛盾 -->
              {{ row.status === 0 ? '正常' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <!-- 备注列：非关键字段，给自适应宽度；超长备注用 tooltip 展示，未填时用 '-' 占位 -->
        <el-table-column label="备注" prop="remark" min-width="130" show-overflow-tooltip>
          <!-- 备注可空，统一占位符避免空白单元格 -->
          <template #default="{ row }">{{ row.remark || '-' }}</template>
        </el-table-column>
        <!-- 创建时间列：定宽 170 容纳 'YYYY-MM-DD HH:mm:ss'，防止换行 -->
        <el-table-column label="创建时间" prop="create_time" width="170" />
        <!-- 操作列：fixed=right 横向滚动时始终可见；220px 容纳三个文字按钮 -->
        <el-table-column label="操作" width="220" fixed="right">
          <!-- 作用域插槽：每个操作都以当前行作为目标 -->
          <template #default="{ row }">
            <!-- 编辑：需 system:role:update；直接用行数据回填（列表接口已返回全部编辑字段） -->
            <el-button v-perm="'system:role:update'" link type="primary" @click="openEdit(row)">编辑</el-button>
            <!-- 分配权限：需 assignMenus；独立入口，打开菜单树勾选该角色可访问的菜单/按钮 -->
            <el-button v-perm="'system:role:assignMenus'" link type="primary" @click="openAssign(row)">分配权限</el-button>
            <!-- 删除：danger 色；需 system:role:delete，点击后仍有二次确认 -->
            <el-button v-perm="'system:role:delete'" link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页外层：全局类负责右对齐与和表格的间距 -->
      <div class="pagination-wrap">
        <!-- 分页器：页码与条数双向绑定到 ref；total 由接口返回；改条数回到第一页，翻页直接重新拉取 -->
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

    <!-- 新增/编辑弹窗：单列表单（560px 宽），字段少且都是短文本，无需栅格分栏 -->
    <!-- destroy-on-close：关闭即销毁内部表单，清空校验红字与残留输入，避免串到下一次打开 -->
    <el-dialog v-model="formVisible" :title="form.id ? '编辑角色' : '新增角色'" width="560px" destroy-on-close>
      <!-- 表单：ref 供 handleSave 调 validate；label-width=90 对齐"权限字符""显示顺序"等四字标签 -->
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <!-- 字段：角色名称，给人看的中文名（如"运营专员"），必填 -->
        <el-form-item label="角色名称" prop="role_name">
          <!-- trim + 30 字上限；名称重复性由后端校验（前端无法知道全量角色） -->
          <el-input v-model.trim="form.role_name" placeholder="请输入角色名称" maxlength="30" />
        </el-form-item>
        <!-- 字段：权限字符（role_key），后端鉴权时使用的稳定标识，新增后通常不建议修改 -->
        <el-form-item label="权限字符" prop="role_key">
          <!-- placeholder 给出 admin/common 这类示例，降低用户随意填写导致与后端约定不一致的概率 -->
          <el-input v-model.trim="form.role_key" placeholder="如 admin / common" maxlength="30" />
        </el-form-item>
        <!-- 字段：显示顺序，决定角色在下拉/列表中的先后；数字越小越靠前 -->
        <el-form-item label="显示顺序" prop="role_sort">
          <!-- 数字输入：min 0 / max 999 限制合法范围；controls-position=right 把加减按钮收在右侧，不挤占左侧标签 -->
          <el-input-number v-model="form.role_sort" :min="0" :max="999" controls-position="right" />
        </el-form-item>
        <!-- 字段：角色状态；用单选组明确"正常/停用"，避免开关取值与直觉相反 -->
        <el-form-item label="状态" prop="status">
          <!-- 单选组绑定 form.status -->
          <el-radio-group v-model="form.status">
            <!-- 0=正常 -->
            <el-radio :value="0">正常</el-radio>
            <!-- 1=停用 -->
            <el-radio :value="1">停用</el-radio>
          </el-radio-group>
        </el-form-item>
        <!-- 字段：数据范围，决定该角色能看到哪些部门的数据（后端按此做数据过滤） -->
        <el-form-item label="数据范围" prop="data_scope">
          <!-- 下拉：选项来自 dataScopeOptions 常量，value 与后端数字枚举一一对应；100% 宽度撑满表单 -->
          <el-select v-model="form.data_scope" style="width: 100%">
            <!-- v-for 渲染五档数据范围；label 为中文说明，value 为提交给后端的数字 -->
            <el-option v-for="d in dataScopeOptions" :key="d.value" :label="d.label" :value="d.value" />
          </el-select>
        </el-form-item>
        <!-- 字段：备注，用于记录该角色的用途/负责人等，非必填 -->
        <el-form-item label="备注" prop="remark">
          <!-- textarea：固定 3 行高度，输入较多说明时不会把弹窗越撑越高；maxlength 200 与后端字段长度一致 -->
          <el-input v-model="form.remark" type="textarea" :rows="3" placeholder="请输入备注" maxlength="200" />
        </el-form-item>
      </el-form>
      <!-- 弹窗底部：取消放弃，确定先校验再按 id 分流提交；saving 防止重复提交 -->
      <template #footer>
        <!-- 取消：直接关闭，角色页字段少、重填成本低，不做脏数据提示 -->
        <el-button @click="formVisible = false">取 消</el-button>
        <!-- 确定：handleSave 内部先 validate，校验失败不会发请求 -->
        <el-button type="primary" :loading="saving" @click="handleSave">确 定</el-button>
      </template>
    </el-dialog>

    <!-- 分配权限弹窗：以菜单树勾选的方式授予该角色可访问的菜单与按钮，数据源与菜单管理页同一份菜单树 -->
    <!-- 宽度 460：树层级较深但节点文字不长；标题拼接角色名，明确"正在给哪个角色授权"，空值兜底避免 undefined -->
    <el-dialog v-model="assignVisible" :title="`分配权限 - ${assignForm.role_name || ''}`" width="460px" destroy-on-close>
      <!-- 滚动容器：限制最大高度 420px，菜单层级多时改为内部滚动，保证底部"取消/保存"按钮始终可见 -->
      <el-scrollbar max-height="420px">
        <!-- 菜单树：ref 供提交时取勾选结果；:data 为 /system/menu/tree 结果；
             :props 把后端的 menu_name/children 映射成 label/children；node-key=id 让勾选集合以 id 表达；
             show-checkbox 开启勾选；default-expand-all 打开即全展开，避免用户逐层点开找按钮；
             :default-checked-keys 只回填叶子节点（原因见 collectLeafKeys 注释） -->
        <el-tree
          ref="menuTreeRef"
          :data="menuTree"
          :props="{ label: 'menu_name', children: 'children' }"
          node-key="id"
          show-checkbox
          default-expand-all
          :default-checked-keys="assignForm.checkedKeys"
        />
      </el-scrollbar>
      <!-- 底部按钮：取消放弃本次勾选；保存会把"全选 + 半选"的节点一起提交 -->
      <template #footer>
        <!-- 取消：关闭弹窗，已勾选内容不落库 -->
        <el-button @click="assignVisible = false">取 消</el-button>
        <!-- 保存：handleAssign 取 getCheckedKeys 与 getHalfCheckedKeys 合并去重后提交 -->
        <el-button type="primary" :loading="saving" @click="handleAssign">保 存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
// 逻辑区总述：<script setup> 顶层变量/函数自动暴露给模板；请求统一走 utils/request，错误提示与 401 跳转由拦截器处理
// Vue 组合式 API：onMounted 拉首屏列表；reactive 管理查询/表单等固定字段对象；ref 管理原始值与树/表单实例
import { onMounted, reactive, ref } from 'vue'
// Element Plus 命令式反馈：ElMessage 成功提示；ElMessageBox 删除前二次确认
import { ElMessage, ElMessageBox } from 'element-plus'
// 图标组件：模板 :icon 需要组件对象，从官方图标包按需导入
import { Search, Refresh, Plus, Delete } from '@element-plus/icons-vue'
// 统一请求实例：baseURL=/api、自动携带 token、响应解包与统一错误提示
import request from '@/utils/request'

// 表格加载态：请求期间遮罩表体，避免在旧数据上继续操作
const loading = ref(false)
// 提交态：新增/编辑弹窗与分配权限弹窗共用，控制按钮 loading 与防重复提交
const saving = ref(false)
// 当前页角色数据，作为 el-table 的 :data
const list = ref([])
// 总条数，供分页器计算页数
const total = ref(0)
// 当前页码，从 1 开始
const page = ref(1)
// 每页条数，默认 10
const pageSize = ref(10)
// 查询条件：字段名与后端入参一致，fetchList 时展开到 params；status=null 表示全部
const query = reactive({ role_name: '', status: null })
// 表格选中行：驱动批量删除按钮的禁用态，并提供待删除 id
const selection = ref([])

// 数据范围枚举：与后端约定 1~5 五档；集中成常量，表格展示与表单下拉共用，避免两处硬编码不一致
const dataScopeOptions = [
  // 1 全部数据权限：不受部门限制，能看到全库数据（范围最广，新增角色时需谨慎授予）
  { value: 1, label: '全部数据权限' },
  // 2 自定义数据权限：由后端另行配置具体部门集合，前端这里只负责展示名称
  { value: 2, label: '自定义数据权限' },
  // 3 本部门数据权限：只能看自己所属部门的数据
  { value: 3, label: '本部门数据权限' },
  // 4 本部门及以下数据权限：包含本部门与所有子部门，适合部门负责人
  { value: 4, label: '本部门及以下数据权限' },
  // 5 仅本人数据权限：范围最小，只能看自己创建的数据
  { value: 5, label: '仅本人数据权限' }
]

// 数字枚举 → 中文标签：表格的"数据范围"列使用；用 String 比较兼容后端返回字符串枚举的情况
function dataScopeLabel(v) {
  // find 命中第一条即返回；比较前统一转字符串，避免 1 与 '1' 不相等
  const hit = dataScopeOptions.find(d => String(d.value) === String(v))
  // 未命中（脏数据或后端新增枚举）返回 '-'，避免表格出现 undefined
  return hit ? hit.label : '-'
}

// ---------- 列表 ----------
// 列表区：查询、分页、重置与选中都围绕 fetchList；角色列表只走 /system/role/list
// 拉取角色列表：page/page_size 与查询条件一起提交，后端返回 { list, total }
async function fetchList() {
  // 请求前先开 loading，让遮罩在点击瞬间出现
  loading.value = true
  // try/finally：不写 catch，错误提示由 request 拦截器统一处理，这里只保证 loading 一定复位
  try {
    // GET /system/role/list：空字符串/null 参数会被 axios 忽略，等价于"不按该条件过滤"
    const res = await request.get('/system/role/list', {
      params: { page: page.value, page_size: pageSize.value, ...query }
    })
    // 列表兜底空数组，避免后端返回 null 时表格渲染报错
    list.value = res.data.list || []
    // 总数兜底 0，保证分页器始终拿到合法数字
    total.value = res.data.total || 0
  } finally {
    // 成功或失败都收起遮罩
    loading.value = false
  }
}

// 查询：回到第一页再请求，避免旧页码与新条件组合导致空结果
function handleSearch() {
  // 页码重置为 1
  page.value = 1
  // 发起请求
  fetchList()
}

// 重置：只清空两个条件，保持 query 的 reactive 引用不变
function handleReset() {
  // 清空角色名称关键字
  query.role_name = ''
  // 状态回到"全部"
  query.status = null
  // 复用查询逻辑，同时把页码拉回 1
  handleSearch()
}

// 切换每页条数：页码回到 1，避免请求到超出新总页数的页码
function handleSizeChange() {
  // 回到第一页
  page.value = 1
  // 按新条数查询
  fetchList()
}

// 表格选中回调：同步当前选中行，selection.length 驱动批量删除按钮的 disabled
function onSelectionChange(rows) {
  // 保存选中行
  selection.value = rows
}

// ---------- 新增/编辑 ----------
// 新增/编辑区：form 是单例对象，openCreate/openEdit 都会先逐字段覆盖，避免两次操作之间数据串场
// 弹窗显隐：模板 el-dialog 的 v-model
const formVisible = ref(false)
// 表单实例：handleSave 通过它调用 validate
const formRef = ref()
// 表单模型：字段与后端角色 DTO 一致；id=null 代表新增，有值代表编辑
const form = reactive({
  // 主键：编辑模式的标志，也是 update 接口路径参数
  id: null,
  // 角色名称：给人看的中文名，必填
  role_name: '',
  // 权限字符：后端鉴权用的角色标识，必填
  role_key: '',
  // 显示顺序：数字越小越靠前，新增默认 0
  role_sort: 0,
  // 状态：0 正常 / 1 停用，新增默认正常
  status: 0,
  // 数据范围：默认 1（全部数据权限）；新增后应由管理员按最小权限原则收紧，而不是长期保留该默认值
  data_scope: 1,
  // 备注：非必填的说明信息
  remark: ''
})

// 校验规则：三个必填项；显示顺序必填是因为它参与列表/下拉排序，缺失会导致顺序不可预期
const rules = {
  // 角色名称必填，失焦校验
  role_name: [{ required: true, message: '请输入角色名称', trigger: 'blur' }],
  // 权限字符必填：后端依赖它做角色判定，空值会让该角色无法被正确识别
  role_key: [{ required: true, message: '请输入权限字符', trigger: 'blur' }],
  // 显示顺序必填：避免出现 null 参与排序比较
  role_sort: [{ required: true, message: '请输入显示顺序', trigger: 'blur' }]
}

// 新增入口：逐字段恢复默认值后再开弹窗；角色页表单只在这一处需要初始化，因此没有单独抽出 resetForm
function openCreate() {
  // id 置空 → handleSave 走新增分支
  form.id = null
  // 清空名称与权限字符
  form.role_name = ''
  form.role_key = ''
  // 排序回到 0（最靠前）
  form.role_sort = 0
  // 状态默认正常
  form.status = 0
  // 数据范围默认"全部"；这是后端约定的默认档位，实际授权时管理员应按最小权限原则调整
  form.data_scope = 1
  // 备注清空
  form.remark = ''
  // 全部字段就绪后才打开弹窗，避免渲染出上一次的残留内容
  formVisible.value = true
}

// 编辑入口：直接用列表行数据回填，不再请求详情——角色列表接口已返回全部可编辑字段
function openEdit(row) {
  // 主键：进入编辑模式的标志
  form.id = row.id
  // 名称回填
  form.role_name = row.role_name
  // 权限字符回填
  form.role_key = row.role_key
  // 排序回填
  form.role_sort = row.role_sort
  // 状态回填（0/1）
  form.status = row.status
  // 数据范围回填（1~5）
  form.data_scope = row.data_scope
  // 备注回填；为空时 textarea 显示空，不影响编辑
  form.remark = row.remark
  // 回填完成后打开弹窗
  formVisible.value = true
}

// 保存：先校验，再用 id 分流新增/修改；两个分支共用同一份 payload
async function handleSave() {
  // 校验失败会 reject，后续提交不会执行
  await formRef.value.validate()
  // 校验通过后进入提交态
  saving.value = true
  // try/finally：失败由 request 统一提示，这里只复位 saving
  try {
    // 显式挑字段构造 payload：避免把 id 等非入参字段带给后端，也让提交内容一眼可读
    const payload = {
      // 角色名称
      role_name: form.role_name,
      // 权限字符
      role_key: form.role_key,
      // 显示顺序
      role_sort: form.role_sort,
      // 状态 0/1
      status: form.status,
      // 数据范围枚举 1~5
      data_scope: form.data_scope,
      // 备注
      remark: form.remark
    }
    // 有 id → 编辑
    if (form.id) {
      // PUT /system/role/update/{id}：id 走路径，payload 走 body
      await request.put(`/system/role/update/${form.id}`, payload)
      // 成功提示
      ElMessage.success('修改成功')
    } else {
      // 无 id → 新增
      await request.post('/system/role/create', payload)
      // 成功提示
      ElMessage.success('新增成功')
    }
    // 成功后关闭弹窗（失败保持打开，便于修正重试）
    formVisible.value = false
    // 重新拉取列表：新增会改变总数，必须以后端分页结果为准
    fetchList()
  } finally {
    // 复位提交态
    saving.value = false
  }
}

// ---------- 分配权限 ----------
// 分配权限区：菜单树懒加载 + 已授权叶子节点回填 + 提交时合并"全选/半选"节点
// 弹窗显隐：模板 el-dialog 的 v-model
const assignVisible = ref(false)
// 菜单树组件实例：提交时通过它读取 getCheckedKeys / getHalfCheckedKeys
const menuTreeRef = ref()
// 菜单树数据：首次打开分配弹窗时懒加载，之后在本页生命周期内复用，减少重复请求
const menuTree = ref([])
// 分配权限表单：id 定位角色、role_name 仅用于弹窗标题、checkedKeys 为回填给树的叶子节点 id 数组
const assignForm = reactive({ id: null, role_name: '', checkedKeys: [] })

// 收集叶子节点 id：把后端返回的 menu_ids 过滤成"叶子节点"再回填。
// 之所以不直接回填全部 id：el-tree 在父子联动模式下，给父节点设置 checked-key 会连带勾选其所有子节点；
// 后端返回的权限集合通常包含父目录 id，直接回填会把未授权的兄弟菜单也勾上，
// 因此只回填叶子节点，父级的全选/半选状态交给组件根据子节点自动计算。
function collectLeafKeys(nodes, ids, acc) {
  // 逐层遍历当前节点集合
  nodes.forEach(node => {
    // 有子节点 → 递归深入，只关心最末级节点
    if (node.children && node.children.length) {
      collectLeafKeys(node.children, ids, acc)
    } else if (ids.includes(node.id)) {
      // 叶子节点且确实在该角色的授权集合里 → 加入回填列表
      acc.push(node.id)
    }
  })
  // 返回累积结果（acc 由调用方传入空数组，递归过程中持续追加）
  return acc
}

// 打开分配权限弹窗：懒加载菜单树 + 拉取该角色已有权限 + 过滤为叶子后回填
async function openAssign(row) {
  // 目标角色 id
  assignForm.id = row.id
  // 角色名称用于弹窗标题
  assignForm.role_name = row.role_name
  // 先清空旧回填，避免上一次打开的角色勾选残留在树上
  assignForm.checkedKeys = []
  // 菜单树只加载一次：已存在则直接复用（菜单在本页操作期间变化概率低）
  if (!menuTree.value.length) {
    // GET /system/menu/tree：与菜单管理页使用同一份树数据
    const res = await request.get('/system/menu/tree')
    // 兜底空数组，树组件可正常渲染空态
    menuTree.value = res.data || []
  }
  // GET /system/role/menu_ids/{id}：返回该角色已授权的菜单/按钮 id 集合
  const res = await request.get(`/system/role/menu_ids/${row.id}`)
  // 兼容后端可能返回 null 的情况，兜底空数组
  const ids = (res.data && res.data.menu_ids) || []
  // 过滤为叶子节点后再交给 default-checked-keys，避免父节点级联勾选越权
  assignForm.checkedKeys = collectLeafKeys(menuTree.value, ids, [])
  // 数据就绪后才打开弹窗，避免树先空后变
  assignVisible.value = true
}

// 提交权限分配：全选节点 + 半选父节点一起提交，才能完整还原树形授权关系
async function handleAssign() {
  // getCheckedKeys 只返回完全勾选的节点（叶子）
  const checked = menuTreeRef.value.getCheckedKeys()
  // getHalfCheckedKeys 返回"部分子节点被授权"的父节点；不提交父节点后端无法还原层级
  const halfChecked = menuTreeRef.value.getHalfCheckedKeys()
  // Set 去重后再转数组：防止某些节点同时处于两种状态导致重复 id
  const menuIds = Array.from(new Set([...checked, ...halfChecked]))
  // 进入提交态
  saving.value = true
  // try/finally：失败由 request 提示，这里只复位 saving
  try {
    // PUT /system/role/assign_menus/{id}：body 为菜单 id 数组，后端按全量覆盖该角色权限
    await request.put(`/system/role/assign_menus/${assignForm.id}`, { menu_ids: menuIds })
    // 成功提示
    ElMessage.success('分配权限成功')
    // 关闭弹窗
    assignVisible.value = false
  } finally {
    // 复位提交态
    saving.value = false
  }
}

// ---------- 删除 ----------
// 删除区：单条与批量共用同一个删除接口，区别只在 ids 数组的来源
// 单条删除：确认后再提交，用户取消会 reject 并中断函数
async function handleDelete(row) {
  // 二次确认：文案带角色名，避免删错角色；type=warning 让确认框呈现警示色
  await ElMessageBox.confirm(`确定删除角色「${row.role_name}」吗？`, '提示', { type: 'warning' })
  // DELETE /system/role/delete：ids 通过 data 传请求体（axios delete 写法），单条也包装成数组
  await request.delete('/system/role/delete', { data: { ids: [row.id] } })
  // 成功提示
  ElMessage.success('删除成功')
  // 删除后刷新列表，让分页总数与当前页数据同步
  fetchList()
}

// 批量删除：选中数量由按钮 disabled 保证大于 0，这里直接提交
async function handleBatchDelete() {
  // 确认文案带数量，明确本次影响范围（删除不可撤销）
  await ElMessageBox.confirm(`确定删除选中的 ${selection.value.length} 个角色吗？`, '提示', { type: 'warning' })
  // 映射选中行 id 后一次性提交
  await request.delete('/system/role/delete', { data: { ids: selection.value.map(r => r.id) } })
  // 成功提示
  ElMessage.success('删除成功')
  // 刷新列表
  fetchList()
}

// 挂载后只拉角色列表；菜单树延迟到第一次"分配权限"时再请求，减少首屏请求数与无效流量
onMounted(fetchList)
</script>
