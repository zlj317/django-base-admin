<!-- 用户管理页（系统管理 / 用户管理）
     职责：维护后台账号资料、启停用、角色分配与密码重置，是"人 → 角色 → 权限"链路里人员一侧的入口。
     接口：GET /system/user/list（分页列表）、GET /system/user/{id}（编辑详情）、POST /system/user/create、
           PUT /system/user/update/{id}、PUT /system/user/status/{id}、PUT /system/user/reset_pwd/{id}、
           PUT /system/user/assign_roles/{id}、DELETE /system/user/delete（单条与批量共用）、
           GET /system/dept/tree（部门树）、GET /system/role/list（角色选项）。
     依赖：utils/request（统一注入 token、统一错误提示）、store/auth（读取当前登录用户，用于禁止修改自己的状态）、
           v-perm 指令（按钮级权限）、Element Plus 的卡片/表单/表格/弹窗/分页组件。
     使用方式：本页不在 router 中静态注册，由后端菜单表配置的 path（如 /system/user）动态挂载；
               访问者需具备 system:user:* 权限码，页面内的按钮再按细分权限码二次控制。 -->
<template>
  <!-- 页面根容器：复用全局 .app-container 的内边距与进场动画，保证各业务页留白一致 -->
  <div class="app-container">
    <!-- 页头：左侧标题组；本页没有页头级操作按钮，新增/批量删除统一放在表格工具栏 -->
    <div class="page-header">
      <!-- 标题组容器：全局样式统一控制标题与副标题的间距、字号与颜色，页面内不再单独写排版 -->
      <div class="page-title-wrap">
        <!-- 主标题：与菜单名称保持一致，便于用户确认当前所在模块 -->
        <h2>用户管理</h2>
        <!-- 副标题：一句话交代本页能力边界，说明这里既管账号也管角色 -->
        <div class="sub">账号维护与角色分配</div>
      </div>
    </div>
    <!-- 查询栏：把最常用的四个筛选条件集中在一行，回车即可查询，减少"输入→移鼠标→点按钮"的操作成本 -->
    <!-- shadow="never"：查询区属于辅助区域，去掉阴影以弱化层级，让下方表格成为视觉主体 -->
    <el-card shadow="never" class="search-card">
      <!-- inline 让表单项横向排列；@submit.prevent 阻止浏览器默认提交（表单内没有提交按钮，避免回车刷新整页） -->
      <el-form inline @submit.prevent>
        <!-- 筛选项：用户名（登录账号），由后端做匹配查询，前端只负责透传关键字 -->
        <el-form-item label="用户名">
          <!-- clearable 支持一键清空；@keyup.enter 让键盘操作直接触发查询；固定 170px 使三个文本筛选项等宽对齐 -->
          <el-input v-model="query.username" placeholder="请输入用户名" clearable style="width: 170px" @keyup.enter="handleSearch" />
        </el-form-item>
        <!-- 筛选项：昵称（展示名），与登录用户名分开检索，便于按人名查找而不必知道账号 -->
        <el-form-item label="昵称">
          <!-- 宽度与用户名输入框保持一致，保证查询栏形成规整的栅格节奏 -->
          <el-input v-model="query.nickname" placeholder="请输入昵称" clearable style="width: 170px" @keyup.enter="handleSearch" />
        </el-form-item>
        <!-- 筛选项：手机号，供客服/审计用手机号反查账号（手机号在后端通常建索引） -->
        <el-form-item label="手机号">
          <!-- 输入框不限制字符类型，格式校验只在新增/编辑表单里做，避免查询时被规则挡住 -->
          <el-input v-model="query.phone" placeholder="请输入手机号" clearable style="width: 170px" @keyup.enter="handleSearch" />
        </el-form-item>
        <!-- 筛选项：状态；用下拉而非输入框，避免用户手填非法值，也让"全部"这一语义显式可选 -->
        <el-form-item label="状态">
          <!-- status 初始为 null 表示"全部"，清空下拉即回到全部；120px 足够容纳"全部/正常/停用"三种文案 -->
          <el-select v-model="query.status" placeholder="全部" clearable style="width: 120px">
            <!-- 0 对应后端"正常"，用数字而非布尔/字符串，与数据库 tinyint 及列表开关的取值保持一致 -->
            <el-option label="正常" :value="0" />
            <!-- 1 对应"停用"；停用账号仍保留数据，仅禁止登录，便于离职人员审计 -->
            <el-option label="停用" :value="1" />
          </el-select>
        </el-form-item>
        <!-- 操作按钮组：无 label，紧跟在筛选项之后，符合"填条件 → 执行"的从左到右阅读顺序 -->
        <el-form-item>
          <!-- 主按钮：触发查询并回到第一页；:icon 需要组件对象，Search 已在 script 中导入 -->
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <!-- 次按钮：清空所有筛选条件后重新查询，不做二次确认（条件可随时重填，成本低） -->
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 表格卡片：与查询区分离，筛选条件变化时只刷新表体，不会连带查询区的布局；.table-card 全局类统一圆角与内边距 -->
    <el-card shadow="never" class="table-card">
      <!-- 工具栏：左侧新增与批量删除；批量操作依赖表格选中项，因此固定在表格正上方，缩短视线移动距离 -->
      <div class="toolbar">
        <!-- 新增：需 system:user:create；无权限时 v-perm 指令直接隐藏元素；openCreate 会先重置表单再开弹窗 -->
        <el-button v-perm="'system:user:create'" type="primary" :icon="Plus" @click="openCreate">新增</el-button>
        <!-- 批量删除：需 system:user:delete；plain 弱化危险色块；未选中任何行时禁用，避免空提交与误触 -->
        <el-button v-perm="'system:user:delete'" type="danger" plain :icon="Delete" :disabled="!selection.length" @click="handleBatchDelete">批量删除</el-button>
      </div>

      <!-- 表格：stripe 隔行变色便于长列表横向读数；empty-text 用中文空态替代默认英文；
           v-loading 复用请求 loading，加载时遮罩表体；@selection-change 把选中行同步给批量删除按钮 -->
      <el-table stripe empty-text="暂无数据" v-loading="loading" :data="list" @selection-change="onSelectionChange">
        <!-- 序号列：定宽 70 只容纳两三位数字；align=center 让数字在列内视觉居中，避免左对齐产生的锯齿感 -->
        <el-table-column type="index" label="序号" width="70" align="center" />
        <!-- 多选列：固定 50px 只为复选框预留宽度，不参与剩余空间分配，保证各屏下列宽稳定 -->
        <el-table-column type="selection" width="50" />
        <!-- 用户名列：min-width 保证窄屏不被挤压到不可读；show-overflow-tooltip 超长时悬浮展示完整值而非截断丢失信息 -->
        <el-table-column label="用户名" prop="username" min-width="110" show-overflow-tooltip />
        <!-- 昵称列：与用户名列等宽，两列常被并排阅读，等宽可减少视觉跳动 -->
        <el-table-column label="昵称" prop="nickname" min-width="110" show-overflow-tooltip />
        <!-- 部门列：dept_name 由后端列表接口冗余返回（用户表只存 dept_id），前端无需再查部门表，减少 N+1 请求 -->
        <el-table-column label="部门" prop="dept_name" min-width="120" show-overflow-tooltip>
          <!-- 作用域插槽：拿到当前行 row；部门可能为空（用户可不分配部门），用 '-' 占位避免空白单元格被误读为加载失败 -->
          <template #default="{ row }">{{ row.dept_name || '-' }}</template>
        </el-table-column>
        <!-- 手机号列：定宽 130px，11 位号码加内边距刚好放下；不随窗口缩放，避免数字被折行 -->
        <el-table-column label="手机号" prop="phone" width="130">
          <!-- 手机号非必填，统一用 '-' 占位；模板里不做格式化（中间四位打码属于脱敏需求，应在后端处理） -->
          <template #default="{ row }">{{ row.phone || '-' }}</template>
        </el-table-column>
        <!-- 角色列：一个用户可有多个角色，后端以 roles 数组返回；宽度自适应但设下限，保证多个标签有展示空间 -->
        <el-table-column label="角色" min-width="150">
          <!-- 作用域插槽：同一行内根据 roles 数量渲染标签组或占位符 -->
          <template #default="{ row }">
            <!-- 先判断数组存在且有长度：无角色时直接走下方 '-' 分支，避免渲染空标签容器 -->
            <template v-if="row.roles && row.roles.length">
              <!-- 角色标签：key 用角色 id（同一用户不会重复同一角色）；size=small 匹配表格行高；mr4 为全局工具类提供的 4px 右间距 -->
              <el-tag v-for="r in row.roles" :key="r.id" size="small" class="mr4">{{ r.role_name }}</el-tag>
            </template>
            <!-- 无角色兜底：账号尚未分配角色时明确展示 '-'，提示管理员需要补授权 -->
            <span v-else>-</span>
          </template>
        </el-table-column>
        <!-- 状态列：用开关直接切换启停用，省去"打开编辑弹窗再保存"的两步操作；定宽 90 足够容纳开关 -->
        <el-table-column label="状态" width="90" align="center">
          <!-- 作用域插槽：当前行数据既是展示源，也是开关 v-model 的直接写入目标 -->
          <template #default="{ row }">
            <!-- 提示层：:disabled 绑定"不是当前登录用户"——只有自己这一行才弹出提示，避免每行悬浮都打扰；
                 placement=top 让提示不遮挡下一行 -->
            <el-tooltip :disabled="row.id !== auth.user.id" content="不能修改自己的状态" placement="top">
              <!-- 状态开关：active-value=0 / inactive-value=1 与后端数字状态严格对齐（注意 0 是"正常"，与直觉相反）；
                   v-model 直接修改 row.status，切换即时反映在界面上；disabled 禁止改动自己，防止把自己锁在系统外；
                   v-perm 让无更新权限的用户看不到开关；@change 只负责提交，失败时由 handleStatusChange 回滚 -->
              <el-switch
                v-model="row.status"
                :active-value="0"
                :inactive-value="1"
                :disabled="row.id === auth.user.id"
                v-perm="'system:user:update'"
                @change="handleStatusChange(row)"
              />
            </el-tooltip>
          </template>
        </el-table-column>
        <!-- 创建时间列：定宽 170px，正好容纳 'YYYY-MM-DD HH:mm:ss'，避免时间被折成两行 -->
        <el-table-column label="创建时间" prop="create_time" width="170" />
        <!-- 操作列：fixed=right 在横向滚动时始终可见，避免用户滚动后还要找操作入口；
             width=310 按四个文字按钮的实际宽度预留；class-name="op-col" 触发本文件与全局样式里的不换行规则 -->
        <el-table-column label="操作" width="310" fixed="right" class-name="op-col">
          <!-- 作用域插槽：每个按钮都需要当前行 row 才能定位用户 -->
          <template #default="{ row }">
            <!-- 编辑：需 system:user:update；link 样式让操作区保持轻量，不与主按钮争夺视觉焦点 -->
            <el-button v-perm="'system:user:update'" link type="primary" @click="openEdit(row)">编辑</el-button>
            <!-- 重置密码：warning 色提示这是影响账号登录的敏感操作；需独立的 resetPwd 权限，便于把改密权收窄 -->
            <el-button v-perm="'system:user:resetPwd'" link type="warning" @click="openResetPwd(row)">重置密码</el-button>
            <!-- 分配角色：单独入口，允许只调整授权而不改动用户资料；需 assignRoles 权限 -->
            <el-button v-perm="'system:user:assignRoles'" link type="primary" @click="openAssign(row)">分配角色</el-button>
            <!-- 删除：danger 色 + 单条删除；需 system:user:delete，点击后仍有二次确认 -->
            <el-button v-perm="'system:user:delete'" link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页外层：全局 .pagination-wrap 负责右对齐，并与表格底部留出 6px 间距 -->
      <div class="pagination-wrap">
        <!-- 分页器：current-page/page-size 双向绑定，翻页与改条数会直接改这两个 ref；
             :total 来自接口，组件据此计算总页数；layout 同时展示总数、条数选择、翻页与跳页；
             改条数时 handleSizeChange 会把页码拉回 1；翻页则直接 fetchList 拉取对应页 -->
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

    <!-- 新增/编辑弹窗：复用同一套表单与校验规则，靠 form.id 区分模式，避免维护两份几乎相同的字段 -->
    <!-- destroy-on-close：关闭即销毁弹窗内部结构，清掉输入框焦点与上一次的校验红字，防止脏状态带到下次打开 -->
    <el-dialog v-model="formVisible" :title="form.id ? '编辑用户' : '新增用户'" width="640px" destroy-on-close>
      <!-- 表单：ref 供 handleSave 调 validate；:model 与 :rules 让表单项能按 prop 自动校验；
           label-width=90px 对齐"初始密码""所属部门"这类四字标签，避免冒号错位 -->
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <!-- 栅格布局：每行两列（span=12），把短字段并排，弹窗在 640px 宽度下即可容纳全部字段且不过长 -->
        <el-row :gutter="12">
          <!-- 左列：用户名 -->
          <el-col :span="12">
            <!-- 字段：用户名是登录唯一标识，因此单独成项并设为必填 -->
            <el-form-item label="用户名" prop="username">
              <!-- 编辑时禁用：用户名通常被后端当作唯一键，改动会影响登录、审计日志与已分配数据的归属；
                   v-model.trim 去掉首尾空格，避免"看不见的空格"造成登录失败；maxlength=30 与后端字段长度一致 -->
              <el-input v-model.trim="form.username" placeholder="请输入用户名" :disabled="!!form.id" maxlength="30" />
            </el-form-item>
          </el-col>
          <!-- 右列：昵称 -->
          <el-col :span="12">
            <!-- 字段：昵称是展示名，允许与用户名不同、也允许重复 -->
            <el-form-item label="昵称" prop="nickname">
              <!-- trim + 30 字上限，与校验规则保持一致，前端先挡住明显不合法的输入 -->
              <el-input v-model.trim="form.nickname" placeholder="请输入昵称" maxlength="30" />
            </el-form-item>
          </el-col>
          <!-- 左列：所属部门 -->
          <el-col :span="12">
            <!-- 字段：dept_id 决定该用户的数据权限范围（本部门/本部门及以下），必须与后端部门树中的节点 id 对应 -->
            <el-form-item label="所属部门" prop="dept_id">
              <!-- 部门树选择：:data 用 loadDeptTree 拉取的树；:props 把后端的 dept_name/children 映射为组件需要的 label/children；
                   node-key=id 保证 v-model 存的是部门 id 而非节点对象；check-strictly 允许选择任意层级（部门可以是父级）；
                   clearable 支持"不设部门"；filterable 让部门多时可按名称搜索；100% 宽度撑满栅格列 -->
              <el-tree-select
                v-model="form.dept_id"
                :data="deptTree"
                :props="{ label: 'dept_name', children: 'children' }"
                node-key="id"
                check-strictly
                clearable
                filterable
                placeholder="请选择部门"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <!-- 右列：手机号 -->
          <el-col :span="12">
            <!-- 字段：手机号非必填，但填了会走 validatePhone 格式校验；11 位上限对应大陆手机号 -->
            <el-form-item label="手机号" prop="phone">
              <!-- trim 防止复制粘贴带入空格；不限制只能输数字，以便兼容带区号的旧数据 -->
              <el-input v-model.trim="form.phone" placeholder="请输入手机号" maxlength="11" />
            </el-form-item>
          </el-col>
          <!-- 左列：邮箱 -->
          <el-col :span="12">
            <!-- 字段：邮箱非必填，用于通知或找回；长度上限 50 与后端字段保持一致 -->
            <el-form-item label="邮箱" prop="email">
              <!-- trim + 50 字上限；格式合法性由 validateEmail 负责 -->
              <el-input v-model.trim="form.email" placeholder="请输入邮箱" maxlength="50" />
            </el-form-item>
          </el-col>
          <!-- 右列：状态 -->
          <el-col :span="12">
            <!-- 字段：账号状态；新增默认 0（正常），由 resetForm 保证 -->
            <el-form-item label="状态" prop="status">
              <!-- 单选组而非开关：弹窗里需要明确展示"正常/停用"两种取值，避免开关含义（0=开启）与直觉冲突 -->
              <el-radio-group v-model="form.status">
                <!-- 0=正常，允许登录 -->
                <el-radio :value="0">正常</el-radio>
                <!-- 1=停用，账号保留但禁止登录 -->
                <el-radio :value="1">停用</el-radio>
              </el-radio-group>
            </el-form-item>
          </el-col>
          <!-- 初始密码只在"新增"时出现：编辑改密走独立的"重置密码"入口，避免管理员误改正在使用的密码；
               v-if 同时保证编辑模式下 password 字段不参与渲染与校验 -->
          <el-col v-if="!form.id" :span="12">
            <!-- 字段：初始密码，仅创建时提交给后端；编辑分支的 payload 已刻意排除它 -->
            <el-form-item label="初始密码" prop="password">
              <!-- type=password 默认掩码；show-password 提供明文切换，方便管理员核对；
                   trim 防止首尾空格成为密码的一部分（否则用户按输入内容登录会失败） -->
              <el-input v-model.trim="form.password" type="password" show-password placeholder="请输入初始密码" />
            </el-form-item>
          </el-col>
          <!-- 整行：角色多选需要横向空间展示已选角色标签，span=24 独占一行 -->
          <el-col :span="24">
            <!-- 字段：role_ids 数组决定用户的菜单与按钮权限，是授权的核心字段 -->
            <el-form-item label="所属角色" prop="role_ids">
              <!-- 多选下拉：multiple 支持一人多角色；filterable 在角色较多时可按名称过滤；
                   placeholder 提示需要主动选择；100% 宽度让已选标签有足够展示空间 -->
              <el-select v-model="form.role_ids" multiple filterable placeholder="请选择角色" style="width: 100%">
                <!-- 选项来自 loadRoleOptions（一次取前 100 条）；label 取 role_name，value 用 id，保证提交的是 id 数组 -->
                <el-option v-for="r in roleOptions" :key="r.id" :label="r.role_name" :value="r.id" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <!-- 弹窗底部：取消直接关闭不落库；确定先校验再按 id 分流提交；saving 期间按钮 loading，防止重复点击产生重复创建 -->
      <template #footer>
        <!-- 取消：不提示脏数据（本页字段少、重填成本低），直接关闭 -->
        <el-button @click="formVisible = false">取 消</el-button>
        <!-- 确定：handleSave 内部先 await validate，校验不过直接中断，不会发出请求 -->
        <el-button type="primary" :loading="saving" @click="handleSave">确 定</el-button>
      </template>
    </el-dialog>

    <!-- 重置密码弹窗：与用户资料表单完全独立（自己的 ref、rules、显隐状态），避免两套校验互相干扰 -->
    <!-- destroy-on-close：每次打开都重建，密码不会被上一次的输入残留 -->
    <el-dialog v-model="pwdVisible" title="重置密码" width="440px" destroy-on-close>
      <!-- 表单：label-width=80px 适配"新密码"三字；rules 只有 password 一条，聚焦改密这一个动作 -->
      <el-form ref="pwdFormRef" :model="pwdForm" :rules="pwdRules" label-width="80px">
        <!-- 只读展示目标用户名：让管理员在提交前再次确认操作对象，避免点错行改错人的密码 -->
        <el-form-item label="用户名">
          <!-- :model-value + disabled：只单向展示，不写回 pwdForm；若用 v-model，用户无法在禁用框里改值但仍会多一处绑定 -->
          <el-input :model-value="pwdForm.username" disabled />
        </el-form-item>
        <!-- 字段：新密码，必填且 6-32 位，规则与新增用户的初始密码保持一致 -->
        <el-form-item label="新密码" prop="password">
          <!-- placeholder 提前说明长度要求，减少提交后才看到校验错误的挫败感；show-password 便于核对输入 -->
          <el-input v-model.trim="pwdForm.password" type="password" show-password placeholder="请输入新密码（不少于6位）" />
        </el-form-item>
      </el-form>
      <!-- 底部按钮：与新增/编辑弹窗同构，取消放弃、确定提交；saving 防止重复点击 -->
      <template #footer>
        <!-- 取消：直接关闭，已输入的密码不保留（destroy-on-close 会清空表单项） -->
        <el-button @click="pwdVisible = false">取 消</el-button>
        <!-- 确定：handleResetPwd 先校验再调接口 -->
        <el-button type="primary" :loading="saving" @click="handleResetPwd">确 定</el-button>
      </template>
    </el-dialog>

    <!-- 分配角色弹窗：用复选框平铺展示全部角色，适合角色数量不多的场景；比多选下拉更直观、少一次展开操作 -->
    <!-- 标题拼接用户名，明确当前正在给谁授权；空值兜底避免出现 undefined -->
    <el-dialog v-model="assignVisible" :title="`分配角色 - ${assignForm.username || ''}`" width="440px" destroy-on-close>
      <!-- 复选框组：role_ids 与 assignForm 双向绑定；class="role-checks" 让它纵向排列成一列清单 -->
      <el-checkbox-group v-model="assignForm.role_ids" class="role-checks">
        <!-- 遍历角色选项：value=角色 id（提交内容），展示文案为 role_name；key 用 id 保证增删角色时复用正确 -->
        <el-checkbox v-for="r in roleOptions" :key="r.id" :value="r.id">{{ r.role_name }}</el-checkbox>
      </el-checkbox-group>
      <!-- 底部按钮：取消关闭、确定提交覆盖式角色数组 -->
      <template #footer>
        <!-- 取消：关闭弹窗，不修改任何角色关系 -->
        <el-button @click="assignVisible = false">取 消</el-button>
        <!-- 确定：handleAssign 提交 role_ids 后刷新列表，让表格中的角色标签立即更新 -->
        <el-button type="primary" :loading="saving" @click="handleAssign">确 定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
// 逻辑区总述：<script setup> 顶层声明的变量与函数会自动暴露给模板，无需 return；
// 所有请求统一走 utils/request，错误提示、token 续签与 401 跳转已由拦截器处理，这里只写成功路径。
// Vue 组合式 API：onMounted 在挂载后拉取首屏数据；reactive 管理"字段固定"的查询/表单对象；ref 管理原始值与组件实例
import { onMounted, reactive, ref } from 'vue'
// Element Plus 命令式反馈：ElMessage 做成功/失败提示，ElMessageBox 做删除前的二次确认（不经过模板中的弹窗组件）
import { ElMessage, ElMessageBox } from 'element-plus'
// 图标组件：模板里的 :icon 需要组件对象而非字符串，因此从官方图标包具名导入，按需打包
import { Search, Refresh, Plus, Delete } from '@element-plus/icons-vue'
// 全局登录态：只读取当前用户 id，用于"禁止修改自己的状态"这一防自锁保护
import { auth } from '@/store/auth'
// 统一请求实例：已配置 baseURL=/api、自动携带 Bearer token、统一响应解包与错误提示
import request from '@/utils/request'

// 表格加载态：请求期间遮罩表体，避免用户在旧数据上继续操作
const loading = ref(false)
// 提交态：新增/编辑、重置密码、分配角色三个弹窗共用，统一控制按钮 loading 与防重复提交
const saving = ref(false)
// 当前页用户数据，直接作为 el-table 的 :data
const list = ref([])
// 总条数，供分页器计算页数；与 list 分离是因为后端分页只返回当前页
const total = ref(0)
// 当前页码，从 1 开始；与 el-pagination 的 current-page 双向绑定
const page = ref(1)
// 每页条数，默认 10；与 el-pagination 的 page-size 双向绑定
const pageSize = ref(10)
// 查询条件：字段名与后端入参一致，fetchList 时整体展开到 params；status=null 表示"全部"（axios 会忽略 null 参数）
const query = reactive({ username: '', nickname: '', phone: '', status: null })
// 表格选中行数组：既用于批量删除按钮的禁用判断，也用于提交 ids
const selection = ref([])

// 部门树：页面初始化时拉取一次，新增/编辑弹窗的树选择器复用，避免每次开弹窗都请求
const deptTree = ref([])
// 角色选项：同时服务"新增/编辑"的多选下拉与"分配角色"的复选框组，因此只加载一次
const roleOptions = ref([])

// ---------- 列表 ----------
// 列表区：查询、分页、重置、选中都围绕 fetchList 组织；所有列表查询只走 /system/user/list 一个接口
// 拉取用户列表：把页码、每页条数与查询条件一起提交，后端返回 { list, total } 结构
async function fetchList() {
  // 先置 loading，让遮罩在请求发出前就出现，避免"点了没反应"的空档
  loading.value = true
  // try/finally 而不写 catch：request 拦截器已统一弹错误提示并 reject，这里只保证 loading 一定复位
  try {
    // GET /system/user/list：只读接口，params 中的空字符串/null 由 axios 序列化时忽略，前端无需逐项剔除
    const res = await request.get('/system/user/list', {
      params: { page: page.value, page_size: pageSize.value, ...query }
    })
    // 列表兜底空数组：后端异常返回 null 时，模板 v-for/表格渲染仍能正常工作
    list.value = res.data.list || []
    // 总数兜底 0：保证分页器的 total 始终是合法数字，不会出现 NaN 页码
    total.value = res.data.total || 0
  } finally {
    // 无论成功或失败都收起遮罩，否则一次失败会让表格永久 loading
    loading.value = false
  }
}

// 查询：必须回到第一页再查，否则带着旧页码 + 新条件可能直接查到空结果
function handleSearch() {
  // 页码重置为 1，与查询条件一起生效
  page.value = 1
  // 发起查询
  fetchList()
}

// 重置：逐字段清空而非整体替换 query 对象，保持 reactive 引用不变（替换会导致模板绑定失效）
function handleReset() {
  // 清空用户名关键字
  query.username = ''
  // 清空昵称关键字
  query.nickname = ''
  // 清空手机号关键字
  query.phone = ''
  // 状态回到"全部"（null 会被 axios 忽略，等价于不传该参数）
  query.status = null
  // 复用查询逻辑：同时把页码拉回 1 并重新请求
  handleSearch()
}

// 切换每页条数：页码必须回到 1，否则可能请求到超出新总页数的页码而显示空表
function handleSizeChange() {
  // 回到第一页
  page.value = 1
  // 按新条数重新查询
  fetchList()
}

// 表格选中回调：Element Plus 在选中项变化时传入当前所有选中行，直接同步给 selection 供批量删除使用
function onSelectionChange(rows) {
  // 保存选中行；selection.length 同时驱动批量删除按钮的 disabled
  selection.value = rows
}

// ---------- 基础数据 ----------
// 基础数据区：部门树与角色列表在页面初始化时一次性加载，供所有弹窗复用，减少重复请求
// 加载部门树：仅用于新增/编辑弹窗的"所属部门"树选择
async function loadDeptTree() {
  // GET /system/dept/tree：后端已按层级组装好 children，前端直接作为树数据使用，不再本地拼装
  const res = await request.get('/system/dept/tree')
  // 兜底空数组：部门为空时树选择器可正常渲染空态，不会报错
  deptTree.value = res.data || []
}

// 加载角色选项：一次取 100 条，角色总量通常远小于该值，因此不做分页或远程搜索
async function loadRoleOptions() {
  // 复用角色列表接口，只取第一页 100 条；参数固定，保证每次打开页面拿到的候选范围一致
  const res = await request.get('/system/role/list', { params: { page: 1, page_size: 100 } })
  // 取 list 字段并兜底空数组，避免模板 v-for 遍历 null
  roleOptions.value = res.data.list || []
}

// ---------- 新增/编辑 ----------
// 新增/编辑区：form 是单例 reactive 对象，打开弹窗前必须先 resetForm，否则上一次编辑的数据会串到新增
// 弹窗显隐：由模板 el-dialog 的 v-model 双向绑定
const formVisible = ref(false)
// 表单实例：handleSave 通过它调用 validate；不保存实例就无法在提交前统一校验
const formRef = ref()
// 表单模型：字段与后端用户 DTO 一一对应；id=null 代表新增，有值代表编辑（页面上多处用 form.id 做模式判断）
const form = reactive({
  // 用户 id：既是编辑模式的标志，也是 update 接口的路径参数
  id: null,
  // 登录用户名：编辑时禁改，新增时必填
  username: '',
  // 展示昵称：必填，用于列表与页面展示
  nickname: '',
  // 手机号：可空，填写后走格式校验
  phone: '',
  // 邮箱：可空，填写后走格式校验
  email: '',
  // 所属部门 id：可空，决定数据权限范围
  dept_id: null,
  // 状态：0 正常 / 1 停用，新增默认正常
  status: 0,
  // 初始密码：仅新增时提交，编辑时该字段不渲染也不参与 payload
  password: '',
  // 角色 id 数组：与多选下拉双向绑定，提交给后端用于建立用户-角色关系
  role_ids: []
})

// 手机号自定义校验器：Element Plus 的 validator 采用回调式，必须调用 callback 才会结束校验
// 设计成"非必填"：value 为空直接通过，只有填了值才校验格式，符合后端"手机号可空"的约束
const validatePhone = (rule, value, callback) => {
  // 仅当有值时校验：1 开头、第二位 3-9、共 11 位，覆盖当前大陆运营商号段
  if (value && !/^1[3-9]\d{9}$/.test(value)) {
    // 格式不符：把错误对象交给 callback，表单项下方会展示提示文案
    return callback(new Error('手机号格式不正确'))
  }
  // 校验通过：回调不带参数，表示该字段合法
  callback()
}

// 邮箱自定义校验器：同样允许为空，非空才校验，避免"非必填字段却被必填式格式拦住"
const validateEmail = (rule, value, callback) => {
  // 简化正则：本地部分 + @ + 域名 + 至少一段 .后缀；不追求 RFC 全量，避免误伤合法但少见的邮箱
  if (value && !/^[\w.-]+@[\w-]+(\.[\w-]+)+$/.test(value)) {
    // 返回错误：表单项展示"邮箱格式不正确"
    return callback(new Error('邮箱格式不正确'))
  }
  // 通过校验
  callback()
}

// 表单校验规则：与后端字段约束保持一致，前端先挡一遍无效请求，减少用户"提交后才报错"的往返
const rules = {
  // 用户名：必填 + 长度 2-30，长度与输入框 maxlength、数据库字段三者对齐
  username: [
    // 必填校验：失焦即校验，提示不依赖提交动作
    { required: true, message: '请输入用户名', trigger: 'blur' },
    // 长度校验：下限 2 位避免单字符账号，上限 30 与后端字段一致
    { min: 2, max: 30, message: '长度 2 到 30 个字符', trigger: 'blur' }
  ],
  // 昵称：必填；长度由输入框 maxlength 兜底，这里不再重复一条规则
  nickname: [{ required: true, message: '请输入昵称', trigger: 'blur' }],
  // 初始密码：必填 + 6-32 位；编辑模式下该字段不渲染，因此不会阻断编辑提交
  password: [
    // 必填：新增用户必须有初始密码，否则账号无法登录
    { required: true, message: '请输入初始密码', trigger: 'blur' },
    // 长度 6-32：与后端密码策略保持一致
    { min: 6, max: 32, message: '密码长度 6 到 32 位', trigger: 'blur' }
  ],
  // 手机号：走自定义校验器，非必填
  phone: [{ validator: validatePhone, trigger: 'blur' }],
  // 邮箱：走自定义校验器，非必填
  email: [{ validator: validateEmail, trigger: 'blur' }]
}

// 重置表单：逐字段赋默认值而非替换 form 对象，保持 reactive 引用，模板与 rules 不受影响
function resetForm() {
  // id 置空 → handleSave 会走新增分支，同时"初始密码"字段重新显示
  form.id = null
  // 清空文本字段（用户名/昵称）
  form.username = ''
  form.nickname = ''
  // 清空联系方式（手机号/邮箱）
  form.phone = ''
  form.email = ''
  // 部门不预选：留空由管理员显式选择
  form.dept_id = null
  // 状态回到 0（正常）：新增账号默认可登录
  form.status = 0
  // 密码清空：新增时必须重新填写，避免复用上一次输入
  form.password = ''
  // 角色清空：避免把上一次编辑的角色关系带到新增用户
  form.role_ids = []
}

// 新增入口：先重置再打开弹窗；顺序不能反，否则弹窗会先渲染出上一次的残留数据
function openCreate() {
  // 必须在 visible 之前重置，保证弹窗渲染时拿到干净的表单
  resetForm()
  // 打开弹窗
  formVisible.value = true
}

// 编辑入口：按行 id 拉取最新详情，而不是直接复制列表行，避免列表缓存的是旧数据（如角色/部门已被改动）
async function openEdit(row) {
  // 先重置，清掉上一次新增/编辑残留（尤其是 password）
  resetForm()
  // GET /system/user/{id}：详情接口会返回列表页可能精简掉的 dept_id、role_ids 等字段
  const res = await request.get(`/system/user/${row.id}`)
  // 兜底空对象，避免 detail 为 null 时后面读属性直接报错
  const detail = res.data || {}
  // 用 Object.assign 写入 reactive 对象：保持 form 引用不变，模板绑定无需重建
  Object.assign(form, {
    // 主键：有值即进入编辑模式
    id: detail.id,
    // 用户名：编辑时输入框禁用，但仍需回填展示
    username: detail.username,
    // 昵称回填
    nickname: detail.nickname,
    // 手机号回填（可能为 null，输入框会显示空）
    phone: detail.phone,
    // 邮箱回填
    email: detail.email,
    // 部门：?? 只在 null/undefined 时兜底为 null，不会把合法的 0 误判为空（不能用 ||）
    dept_id: detail.dept_id ?? null,
    // 状态回填：0 正常 / 1 停用
    status: detail.status,
    // 密码不回填：编辑模式不需要也不应该展示密码
    password: '',
    // 角色数组：后端可能返回 null，兜底空数组以适配多选组件
    role_ids: detail.role_ids || []
  })
  // 回填完成后才打开弹窗，避免用户看到空表单再"跳变"成有值
  formVisible.value = true
}

// 保存：先整表校验，再按 form.id 分流新增/修改；两个分支提交的字段不同（编辑刻意不提交 password）
async function handleSave() {
  // validate 返回 Promise：校验失败会 reject，后续提交语句不会执行（拦截器之外的第一道闸）
  await formRef.value.validate()
  // 校验通过后才进入提交态，避免校验失败时按钮短暂 loading 造成闪烁
  saving.value = true
  // try/finally：失败由 request 统一提示，这里只负责把 saving 复位
  try {
    // 有 id → 编辑
    if (form.id) {
      // 解构只取编辑允许的字段：刻意排除 password（改密走独立接口）与表单之外的字段
      const { id, username, nickname, phone, email, dept_id, status, role_ids } = form
      // PUT /system/user/update/{id}：id 走路径，body 只包含可编辑字段
      await request.put(`/system/user/update/${id}`, {
        // 字段名与后端入参一一对应，不做重命名，减少对接歧义
        username, nickname, phone, email, dept_id, status, role_ids
      })
      // 成功提示：文案用"修改"而非"保存"，让用户区分当前是编辑模式
      ElMessage.success('修改成功')
    } else {
      // 无 id → 新增；新增比编辑多一个 password
      const { username, nickname, phone, email, dept_id, status, password, role_ids } = form
      // POST /system/user/create：创建接口由后端生成真正的用户 id
      await request.post('/system/user/create', {
        // 初始密码随创建一起提交，后端可能在此处做加密存储
        username, nickname, phone, email, dept_id, status, password, role_ids
      })
      // 成功提示
      ElMessage.success('新增成功')
    }
    // 成功后关闭弹窗（失败时保持弹窗打开，用户可修正后重试）
    formVisible.value = false
    // 重新拉取列表：新增会改变总数，必须请求后端而不是本地插入，保证分页一致
    fetchList()
  } finally {
    // 无论成功失败都复位提交态，解锁按钮
    saving.value = false
  }
}

// ---------- 重置密码 ----------
// 重置密码区：独立表单/校验/显隐，与用户资料表单解耦，避免两套规则共用同一个 ref 导致校验错位
// 弹窗显隐：模板 el-dialog 的 v-model
const pwdVisible = ref(false)
// 重置密码表单实例：只用于该弹窗的 validate
const pwdFormRef = ref()
// 改密表单：id 用于拼接口路径，username 仅只读展示，password 为待提交的新密码
const pwdForm = reactive({ id: null, username: '', password: '' })
// 改密校验：与新增用户的密码规则保持一致（必填 + 6-32 位），避免两处策略漂移
const pwdRules = {
  password: [
    // 必填：不允许提交空密码
    { required: true, message: '请输入新密码', trigger: 'blur' },
    // 长度 6-32：与后端密码策略对齐
    { min: 6, max: 32, message: '密码长度 6 到 32 位', trigger: 'blur' }
  ]
}

// 打开重置密码弹窗：从当前行带入 id 与用户名，密码每次清空，防止复用上次输入
function openResetPwd(row) {
  // 目标用户 id：决定改谁的密码
  pwdForm.id = row.id
  // 用户名只读展示，帮助管理员确认操作对象
  pwdForm.username = row.username
  // 密码清空：强制重新输入
  pwdForm.password = ''
  // 打开弹窗
  pwdVisible.value = true
}

// 提交重置密码：先校验再请求；失败时保持弹窗打开，便于重试
async function handleResetPwd() {
  // 校验不通过会 reject，不会发请求
  await pwdFormRef.value.validate()
  // 进入提交态，防止重复点击
  saving.value = true
  try {
    // PUT /system/user/reset_pwd/{id}：密码放在 body 而非 URL，避免密码出现在访问日志/浏览器历史
    await request.put(`/system/user/reset_pwd/${pwdForm.id}`, { password: pwdForm.password })
    // 成功提示
    ElMessage.success('密码重置成功')
    // 关闭弹窗
    pwdVisible.value = false
  } finally {
    // 复位提交态
    saving.value = false
  }
}

// ---------- 分配角色 ----------
// 分配角色区：只改"用户-角色"关系，不动用户资料；提交采用覆盖式，后端按传入数组全量替换
// 弹窗显隐
const assignVisible = ref(false)
// 分配角色表单：id 定位用户、username 仅用于标题展示、role_ids 为提交内容（与复选框组双向绑定）
const assignForm = reactive({ id: null, username: '', role_ids: [] })

// 打开分配角色弹窗：从当前行的 roles 反推已选角色 id，让弹窗打开时就呈现当前授权状态
function openAssign(row) {
  // 目标用户 id
  assignForm.id = row.id
  // 用户名用于弹窗标题，明确"正在给谁授权"
  assignForm.username = row.username
  // roles 可能为 null，先兜底空数组；再只取 id，因为复选框的 value 是角色 id
  assignForm.role_ids = (row.roles || []).map(r => r.id)
  // 打开弹窗
  assignVisible.value = true
}

// 提交角色分配：不需要校验（可以清空所有角色，表示取消全部授权）
async function handleAssign() {
  // 进入提交态，防止重复点击
  saving.value = true
  try {
    // PUT /system/user/assign_roles/{id}：body 为角色 id 数组，后端按全量覆盖处理
    await request.put(`/system/user/assign_roles/${assignForm.id}`, { role_ids: assignForm.role_ids })
    // 成功提示
    ElMessage.success('分配角色成功')
    // 关闭弹窗
    assignVisible.value = false
    // 刷新列表，让表格里的角色标签同步更新
    fetchList()
  } finally {
    // 复位提交态
    saving.value = false
  }
}

// ---------- 状态/删除 ----------
// 状态与删除区：两者都会改变列表数据，操作成功后统一重新拉取

// 状态切换：el-switch 已先把 row.status 改成新值，这里负责提交；失败时必须把 UI 拨回旧值
async function handleStatusChange(row) {
  // 由新值反推旧值：状态只有 0/1 两种，因此用三元取反即可
  const oldVal = row.status === 0 ? 1 : 0
  // 只有请求成功才保留新状态，失败走 catch 回滚
  try {
    // PUT /system/user/status/{id}：按行提交最新状态值
    await request.put(`/system/user/status/${row.id}`, { status: row.status })
    // 按新值给出不同文案，让用户确认自己刚才是启用还是停用
    ElMessage.success(row.status === 0 ? '已启用' : '已停用')
  } catch (e) {
    // 请求失败时把开关拨回旧值：request 已弹错误提示，这里只负责让 UI 与实际状态一致
    row.status = oldVal
  }
}

// 单条删除：先二次确认，再把单个 id 包成数组，复用批量删除接口
async function handleDelete(row) {
  // confirm 返回 Promise；用户点"取消"会 reject，函数中断，不会误删
  await ElMessageBox.confirm(`确定删除用户「${row.username}」吗？`, '提示', { type: 'warning' })
  // DELETE /system/user/delete：ids 通过 data 传递（axios 的 delete 请求体写法），与批量删除共用同一接口
  await request.delete('/system/user/delete', { data: { ids: [row.id] } })
  // 成功提示
  ElMessage.success('删除成功')
  // 删除后重新拉取列表：当前页可能因此变空，需要后端返回最新的分页数据
  fetchList()
}

// 批量删除：选中行可能为 0，但按钮已用 :disabled 拦住，这里不再重复判空
async function handleBatchDelete() {
  // 确认文案带上数量，让用户明确本次影响范围（批量删除不可撤销）
  await ElMessageBox.confirm(`确定删除选中的 ${selection.value.length} 个用户吗？`, '提示', { type: 'warning' })
  // 从选中行映射出 id 数组，一次性提交，减少请求次数
  await request.delete('/system/user/delete', { data: { ids: selection.value.map(r => r.id) } })
  // 成功提示
  ElMessage.success('删除成功')
  // 刷新列表，同时清空已删除行带来的选中态（表格数据更新后 Element Plus 会重置选中）
  fetchList()
}

// 挂载后初始化：列表、部门树、角色选项三个请求互不依赖，因此并行发起（不 await，避免串行拖慢首屏）
onMounted(() => {
  // 首屏列表：进入页面立即展示第 1 页数据
  fetchList()
  // 部门树：供后续打开新增/编辑弹窗时直接使用
  loadDeptTree()
  // 角色选项：供新增/编辑的多选与分配角色弹窗使用
  loadRoleOptions()
})
</script>

<style scoped>
/* 本页样式只处理两处 Element Plus 默认表现，其余外观全部复用全局 .app-container/.table-card 等类，避免页面级样式重复 */
/* 分配角色弹窗的复选框组容器：把默认的行内排列改成一列，角色多时形成清单，点选目标更明确 */
.role-checks {
  /* flex 布局作为纵向排列的前提 */
  display: flex;
  /* 纵向排列：每个角色独占一行，避免横向换行后参差不齐、难以对齐勾选框 */
  flex-direction: column;
}

/* 操作列单元格：.op-col 是传给 el-table-column 的 class-name，最终落在表格单元格上；
   scoped 默认无法穿透到子组件内部，因此用 :deep 让选择器作用到 el-table 生成的 DOM */
:deep(.op-col .cell) {
  /* 禁止换行：四个文字按钮必须保持单行，换行会撑高行高、破坏表格密度，也与 fixed 列宽不匹配 */
  white-space: nowrap;
}
</style>
