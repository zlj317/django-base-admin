<!-- 工单列表页（工单管理 / 工单列表）
     职责：工单的检索、新建、编辑、指派、解决、关闭、删除，以及只读查看工单详情与处理日志。
     接口：GET /wo/order/list（分页列表）、POST /wo/order/create、PUT /wo/order/update/{id}、
           DELETE /wo/order/delete（按 ids 批量删除）、PUT /wo/order/assign/{id}、
           PUT /wo/order/solve/{id}、PUT /wo/order/close/{id}、GET /wo/type/list（类型下拉）、
           GET /wo/log/list（处理日志）。
     依赖：utils/request（统一注入 token、统一错误提示、401 跳登录）、
           Element Plus 的表单/表格/分页/弹窗/抽屉组件、@element-plus/icons-vue 图标。
     被谁使用：本页由后端菜单表配置的 path（如 /wo/order）动态挂载，不在 router 中静态注册；
               页面内按钮未接 v-perm 前端权限码，能否操作最终由后端接口鉴权决定。 -->
<template>
  <!-- 页面根容器：复用全局 .app-container 的留白与进场动画，保证与其它业务页视觉一致 -->
  <div class="app-container">
    <!-- 页头：左侧只放标题与总数，新建等操作统一收在下方表格卡片的工具栏，避免两处入口分散注意力 -->
    <div class="page-header">
      <!-- 标题组：全局样式统一控制标题/副标题的字号、间距与颜色，页面内不再单独排版 -->
      <div class="page-title-wrap">
        <!-- 主标题与菜单名称保持一致，便于用户确认当前所在模块 -->
        <h2>工单列表</h2>
        <!-- 副标题展示总数：total 来自列表接口，抬头即可看到当前筛选下的数据规模 -->
        <div class="sub">工单管理 · 共 {{ total }} 条</div>
      </div>
    </div>
    <!-- 查询区卡片：shadow="never" 弱化阴影层级，让下方表格成为视觉主体 -->
    <el-card shadow="never" class="search-card">
      <!-- inline 让筛选项横向排布；@submit.prevent 阻止表单默认提交，避免输入框回车时刷新整页 -->
      <el-form :model="query" inline @submit.prevent>
        <!-- 筛选项：标题，按关键字检索工单主题，前端只透传值不做本地过滤 -->
        <el-form-item label="标题">
          <!-- clearable 支持一键清空；@keyup.enter 让键盘直接触发查询；固定 170px 使两个文本筛选项等宽对齐 -->
          <el-input v-model="query.title" placeholder="请输入工单标题" clearable style="width: 170px" @keyup.enter="handleSearch" />
        </el-form-item>
        <!-- 筛选项：工单号，供客服/运维按单号快速定位，避免只记得编号时翻页查找 -->
        <el-form-item label="工单号">
          <!-- 宽度与标题框一致，保持查询行的栅格节奏；回车即查询 -->
          <el-input v-model="query.order_no" placeholder="请输入工单号" clearable style="width: 170px" @keyup.enter="handleSearch" />
        </el-form-item>
        <!-- 筛选项：状态，用下拉限定合法取值，比输入框更不容易填错 -->
        <el-form-item label="状态">
          <!-- clearable 清空后回到"全部"；query.status 初始为 null，与后端"不筛选"语义一致 -->
          <el-select v-model="query.status" placeholder="全部" clearable style="width: 120px">
            <!-- 选项来源于 statusOptions 字典，保证筛选文案与表格状态标签完全一致 -->
            <el-option v-for="s in statusOptions" :key="s.value" :label="s.label" :value="s.value" />
          </el-select>
        </el-form-item>
        <!-- 筛选项：优先级，便于先把高优先级工单捞出来处理 -->
        <el-form-item label="优先级">
          <!-- 与状态框同宽，视觉上形成并列关系 -->
          <el-select v-model="query.priority" placeholder="全部" clearable style="width: 120px">
            <!-- 与表格标签、编辑弹窗共用 priorityOptions，避免多处维护字典导致文案/取值漂移 -->
            <el-option v-for="p in priorityOptions" :key="p.value" :label="p.label" :value="p.value" />
          </el-select>
        </el-form-item>
        <!-- 操作按钮组无 label：紧跟在筛选项之后，符合"填条件 → 执行"的从左到右阅读顺序 -->
        <el-form-item>
          <!-- 查询：handleSearch 会先把页码重置为 1，避免停留在越界页导致查询结果为空 -->
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <!-- 重置：回填默认条件并重新查询；条件可随时重填，故不做二次确认 -->
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 表格卡片：与查询区拆开，筛选变化只刷新表体；.table-card 全局类负责圆角与内边距 -->
    <el-card shadow="never" class="table-card">
      <!-- 卡片头部插槽：放置工具栏，固定在表格正上方，缩短"点击操作 → 看到结果"的视线距离 -->
      <template #header>
        <!-- 卡片头容器：本页页级操作只有"新建"，后续如需批量操作也放这里 -->
        <div class="card-header">
          <!-- 操作区 -->
          <div class="card-actions">
            <!-- 新建工单：openCreate 会先重置表单再开弹窗，保证不残留上一次编辑的数据 -->
            <el-button type="primary" :icon="Plus" @click="openCreate">新建工单</el-button>
          </div>
        </div>
      </template>
      <!-- 表格：v-loading 在请求期间覆盖遮罩，防重复点击；stripe 斑马纹便于横向读行；empty-text 统一空态文案 -->
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据">
        <!-- 序号列：按当前页自动递增，仅用于阅读定位，不承载业务含义 -->
        <el-table-column type="index" label="序号" width="70" align="center" />
        <!-- 工单号：业务唯一标识；min-width 保证窄屏不被压缩，show-overflow-tooltip 让超长值悬浮显示全文 -->
        <el-table-column label="工单号" prop="order_no" min-width="160" show-overflow-tooltip />
        <!-- 标题：工单核心信息，因此给了更宽的最小宽度，避免过早省略 -->
        <el-table-column label="标题" prop="title" min-width="200" show-overflow-tooltip />
        <!-- 类型列：优先展示后端回传的 type_name；缺失时退化为 order_type_id，再退化为 "-"，避免出现空白单元格 -->
        <el-table-column label="类型" min-width="100">
          <template #default="{ row }">{{ row.type_name || row.order_type_id || '-' }}</template>
        </el-table-column>
        <!-- 优先级列：居中展示彩色标签，让高优先级工单在长列表中一眼可辨 -->
        <el-table-column label="优先级" width="100" align="center">
          <template #default="{ row }">
            <!-- effect="light" 用浅色底，避免整表出现高饱和色块；size="small" 压缩行高，提升单屏信息量 -->
            <el-tag :type="priorityTag(row.priority)" effect="light" size="small">
              <!-- 文案由 priorityLabel 映射为 低/中/高，未知值统一兜底为"未知" -->
              {{ priorityLabel(row.priority) }}
            </el-tag>
          </template>
        </el-table-column>
        <!-- 状态列：反映工单流转阶段（待处理→处理中→已解决/已关闭），标签颜色由 statusTag 统一映射 -->
        <el-table-column label="状态" width="110" align="center">
          <template #default="{ row }">
            <!-- 处理中使用 primary 突出"进行中"，已解决用 success，待处理/已关闭用 info 弱化 -->
            <el-tag :type="statusTag(row.status)" effect="light" size="small">
              <!-- 文案由 statusLabel 映射，未知状态不显示空标签 -->
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <!-- 创建人列：优先显示名称；后端未联表时只回 creator_id，此时直接展示 ID 便于排障 -->
        <el-table-column label="创建人" min-width="100">
          <template #default="{ row }">{{ row.creator_name || row.creator_id || '-' }}</template>
        </el-table-column>
        <!-- 处理人列：未指派时 assignee_id 为空，统一显示 "-"，与"待处理"状态语义呼应 -->
        <el-table-column label="处理人" min-width="100">
          <template #default="{ row }">{{ row.assignee_name || row.assignee_id || '-' }}</template>
        </el-table-column>
        <!-- 期望时间：为处理人提供时限参考；固定 170px 以完整容纳 "YYYY-MM-DD HH:mm:ss" -->
        <el-table-column label="期望时间" prop="expect_time" width="170" />
        <!-- 关闭时间：仅在工单关闭后由后端写入，未关闭时为空显示，用于统计处理时效 -->
        <el-table-column label="关闭时间" prop="close_time" width="170" />
        <!-- 操作列：fixed="right" 固定在右侧，横向滚动时仍可操作；宽度 300 以容纳最多 6 个 link 按钮 -->
        <!-- 说明：这些按钮未加 v-perm，前端不做权限裁剪，后端接口才是最终权限边界 -->
        <el-table-column label="操作" width="300" fixed="right" class-name="op-col">
          <template #default="{ row }">
            <!-- 按钮容器：nowrap 防止窄屏下按钮换行，导致行高抖动 -->
            <div class="op-btns">
              <!-- 详情：任意状态均可查看（只读抽屉），不改变工单状态，也不触发后端写操作 -->
              <el-button link type="primary" @click="openDetail(row)">详情</el-button>
              <!-- 指派：仅"待处理(0)"与"处理中(1)"可（重新）分配处理人；已解决/已关闭再改派会破坏流程闭环 -->
              <el-button link type="warning" v-if="row.status === 0 || row.status === 1" @click="openAssign(row)">指派</el-button>
              <!-- 解决：仅"处理中(1)"可标记已解决，符合"先接单处理 → 再解决"的流转顺序，未指派不可直接解决 -->
              <el-button link type="success" v-if="row.status === 1" @click="handleSolve(row)">解决</el-button>
              <!-- 关闭：除"已关闭(3)"外均可见，用于取消无效工单或终止不再处理的工单 -->
              <el-button link type="info" v-if="row.status !== 3" @click="handleClose(row)">关闭</el-button>
              <!-- 编辑：不按状态限制，保留对历史工单信息（期望时间、附件等）的修正能力 -->
              <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
              <!-- 删除：不可逆的危险操作，点击后先弹二次确认，确认才调用删除接口 -->
              <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
      <!-- 分页条容器：单独留出上边距，与表体拉开层次 -->
      <div class="pagination-wrap">
        <!-- 分页：background 给页码加底色块便于点击；layout 依次为总数/页大小/上页/页码/下页/跳页 -->
        <!-- v-model 直接改写 query.page 与 query.page_size；@change 在两者任一变化时重新拉取列表 -->
        <el-pagination background layout="total, sizes, prev, pager, next, jumper"
          :total="total" v-model:current-page="query.page" v-model:page-size="query.page_size"
          :page-sizes="[10, 20, 50, 100]" @change="fetchList" />
      </div>
    </el-card>

    <!-- 新建/编辑弹窗：两种模式共用同一套表单，靠 dialogTitle 与 form.id 区分；id 为空走新建，有值走更新 -->
    <!-- :close-on-click-modal="false" 防止误点遮罩丢失已填内容；destroy-on-close 关闭即销毁，避免下次打开残留校验红框 -->
    <el-dialog :title="dialogTitle" v-model="dialogVisible" width="720px" :close-on-click-modal="false" destroy-on-close>
      <!-- formRef 供 submitForm 调用 validate()；rules 只约束标题与优先级，其余字段由后端兜底校验 -->
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <!-- 栅格布局：gutter=12 控制列间距；24 栅格让长文本占满一行，短字段两列一排以减少弹窗高度 -->
        <el-row :gutter="12">
          <!-- 标题：占满整行；maxlength=200 与后端字段长度对齐，前端先挡住超长输入 -->
          <el-col :span="24">
            <el-form-item label="标题" prop="title">
              <el-input v-model="form.title" placeholder="请输入工单标题" maxlength="200" />
            </el-form-item>
          </el-col>
          <!-- 工单类型：两列布局节省高度；选项来自 typeOptions，未加载时为空列表，不影响其它字段填写 -->
          <el-col :span="12">
            <el-form-item label="工单类型" prop="order_type_id">
              <!-- 宽度 100% 以撑满所在栅格；v-model 直接绑定类型 ID，提交给后端的是 id 而非名称 -->
              <el-select v-model="form.order_type_id" placeholder="请选择类型" style="width:100%">
                <!-- key 用 t.id 保证唯一；label 展示 type_name，value 传 id -->
                <el-option v-for="t in typeOptions" :key="t.id" :label="t.type_name" :value="t.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <!-- 优先级：与类型同排第二列；表单默认值为 2(中)，新建时不必强制用户改动 -->
          <el-col :span="12">
            <el-form-item label="优先级" prop="priority">
              <el-select v-model="form.priority" placeholder="请选择" style="width:100%">
                <!-- 复用列表页的优先级字典，保证前端各处的取值与文案一致 -->
                <el-option v-for="p in priorityOptions" :key="p.value" :label="p.label" :value="p.value" />
              </el-select>
            </el-form-item>
          </el-col>
          <!-- 创建人：直接填用户 ID（未接人员选择器）；:min=1 防止 0/负值这类非法用户 ID 被提交 -->
          <el-col :span="12">
            <el-form-item label="创建人" prop="creator_id">
              <el-input-number v-model="form.creator_id" :min="1" style="width:100%" />
            </el-form-item>
          </el-col>
          <!-- 处理人：:min=0 允许留空（0 表示暂不指派），与列表"待处理"状态、指派弹窗的 min=1 区分开 -->
          <el-col :span="12">
            <el-form-item label="处理人" prop="assignee_id">
              <el-input-number v-model="form.assignee_id" :min="0" style="width:100%" />
            </el-form-item>
          </el-col>
          <!-- 期望时间：datetime 精确到秒；value-format 统一为后端可直接入库的字符串格式，避免时区/格式转换 -->
          <el-col :span="12">
            <el-form-item label="期望时间" prop="expect_time">
              <el-date-picker v-model="form.expect_time" type="datetime" placeholder="选择期望时间" value-format="YYYY-MM-DD HH:mm:ss" style="width:100%" />
            </el-form-item>
          </el-col>
          <!-- 附件 ID：后端以逗号分隔字符串存储，因此这里用普通输入框而非上传组件 -->
          <el-col :span="12">
            <el-form-item label="附件ID" prop="attachment_ids">
              <el-input v-model="form.attachment_ids" placeholder="逗号分隔" />
            </el-form-item>
          </el-col>
          <!-- 工单内容：占满整行，5 行文本域兼顾描述空间与弹窗高度 -->
          <el-col :span="24">
            <el-form-item label="工单内容" prop="content">
              <el-input v-model="form.content" type="textarea" :rows="5" placeholder="请详细描述工单内容" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <!-- 弹窗底部：取消直接关闭且不重置（下次打开会由 openCreate/openEdit 重置）；确定按钮 loading 由 saving 控制防重复提交 -->
      <template #footer>
        <el-button @click="dialogVisible=false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitForm">确定</el-button>
      </template>
    </el-dialog>

    <!-- 详情抽屉：只读展示工单基本信息、内容、附件与处理日志；destroy-on-close 保证每次打开都重新初始化时间线 -->
    <el-drawer v-model="detailVisible" :title="detailData.title || '工单详情'" size="540px" destroy-on-close>
      <!-- v-if="detailData.id"：数据未就绪时不渲染空壳，避免抽屉里出现一整屏 "-" -->
      <div v-if="detailData.id" class="detail-body">
        <!-- 描述列表：单列 + border，字段名与值左右对齐；抽屉仅 540px，纵向排布比两列更易读 -->
        <el-descriptions :column="1" border>
          <!-- 工单号：业务唯一标识，放最前便于复制给他人沟通定位 -->
          <el-descriptions-item label="工单号">{{ detailData.order_no }}</el-descriptions-item>
          <!-- 状态：复用列表页的 statusTag/statusLabel，保证同一状态在不同位置颜色与文案一致 -->
          <el-descriptions-item label="状态">
            <el-tag :type="statusTag(detailData.status)" effect="light">{{ statusLabel(detailData.status) }}</el-tag>
          </el-descriptions-item>
          <!-- 优先级：同上复用优先级映射，形成统一的红黄绿语义 -->
          <el-descriptions-item label="优先级">
            <el-tag :type="priorityTag(detailData.priority)" effect="light">{{ priorityLabel(detailData.priority) }}</el-tag>
          </el-descriptions-item>
          <!-- 工单类型：名称缺失时退化为 ID；详情数据直接来自列表行，可能不含联表字段 -->
          <el-descriptions-item label="工单类型">{{ detailData.type_name || detailData.order_type_id || '-' }}</el-descriptions-item>
          <!-- 创建人：名称/ID 逐级回退，空值统一 "-" -->
          <el-descriptions-item label="创建人">{{ detailData.creator_name || detailData.creator_id || '-' }}</el-descriptions-item>
          <!-- 处理人：未指派时显示 "-"，提示当前工单尚未被接单 -->
          <el-descriptions-item label="处理人">{{ detailData.assignee_name || detailData.assignee_id || '-' }}</el-descriptions-item>
          <!-- 期望时间：无值时显示 "-"，不展示空字符串 -->
          <el-descriptions-item label="期望时间">{{ detailData.expect_time || '-' }}</el-descriptions-item>
          <!-- 关闭时间：仅已关闭工单有值，其余显示 "-" -->
          <el-descriptions-item label="关闭时间">{{ detailData.close_time || '-' }}</el-descriptions-item>
          <!-- 创建时间：用于判断工单存续时长 -->
          <el-descriptions-item label="创建时间">{{ detailData.create_time || '-' }}</el-descriptions-item>
        </el-descriptions>
        <!-- 工单内容区：单独成块，与上方字段表格拉开层次 -->
        <div class="detail-section">
          <div class="detail-section-title">📝 工单内容</div>
          <!-- 内容：保留换行的 pre-wrap 展示，空内容用"（无内容）"占位，避免出现空白区域 -->
          <div class="detail-content">{{ detailData.content || '（无内容）' }}</div>
        </div>
        <!-- 附件区：仅当 attachment_ids 有值才出现，避免"有标题无内容"的空块干扰阅读 -->
        <div class="detail-section" v-if="detailData.attachment_ids">
          <div class="detail-section-title">📎 附件</div>
          <!-- 附件 ID 串：等宽字体展示，便于人工核对逗号分隔的 ID 是否完整 -->
          <div class="detail-content mono">{{ detailData.attachment_ids }}</div>
        </div>
        <!-- 处理日志区：只读时间线，按后端返回顺序（通常按时间倒序）展示操作人、动作与备注 -->
        <div class="detail-section">
          <div class="detail-section-title">🕒 处理日志</div>
          <!-- v-if 有日志才渲染时间线，无日志时走下方空态分支 -->
          <el-timeline v-if="workLogs.length">
            <!-- :key 用索引：日志项没有稳定唯一 ID，索引在当前列表内唯一即可；timestamp 兼容 create_time/time 两种字段 -->
            <el-timeline-item v-for="(log, i) in workLogs" :key="i" :timestamp="log.create_time || log.time || ''">
              <div>
                <!-- 操作人：优先名称，缺失退化为 ID，再兜底"系统"（自动流转产生的日志） -->
                <strong>{{ log.operator_name || log.operator_id || '系统' }}</strong>
                <span class="muted"> 执行了 </span>
                <!-- 动作标签：优先展示原始动作码 action 的兜底文案，缺失时统一显示"处理" -->
                <el-tag effect="light" size="small">{{ log.action || log.action_label || '处理' }}</el-tag>
              </div>
              <!-- 备注：兼容 remark/content 两种后端字段命名；空值渲染为空串，避免出现 undefined -->
              <div class="log-remark">{{ log.remark || log.content || '' }}</div>
            </el-timeline-item>
          </el-timeline>
          <!-- 空态提示：与表格空态语气一致，避免用户误以为日志加载失败 -->
          <div v-else class="empty-tip">暂无处理日志</div>
        </div>
      </div>
    </el-drawer>

    <!-- 指派弹窗：功能单一（只填处理人），因此用 420px 轻量弹窗而不是抽屉，减少信息干扰 -->
    <el-dialog title="指派工单" v-model="assignVisible" width="420px" destroy-on-close>
      <!-- 表单不挂 rules：处理人必填在 submitAssign 里手动校验（该表单项没有 prop，走不了统一校验） -->
      <el-form label-width="90px">
        <!-- 工单标题：只读展示，帮助用户确认正在给哪条工单改派，避免开错弹窗后误操作 -->
        <el-form-item label="工单标题">
          <span>{{ assignData.title }}</span>
        </el-form-item>
        <!-- 处理人 ID：required 仅作视觉必填星标；:min=1 防止 0 被当作合法用户；placeholder 说明填用户主键 -->
        <el-form-item label="处理人ID" required>
          <el-input-number v-model="assignAssignee" :min="1" style="width:100%" placeholder="请输入处理人用户ID" />
        </el-form-item>
      </el-form>
      <!-- 底部：取消不提交；确定按钮 loading 绑定 assigning，防止连续点击对同一工单重复指派 -->
      <template #footer>
        <el-button @click="assignVisible=false">取消</el-button>
        <el-button type="primary" :loading="assigning" @click="submitAssign">确定指派</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
// 组合式 API：ref 承载原始值与数组，reactive 承载对象（用 Object.assign 就地修改以保持响应式引用不变）
import { ref, reactive, onMounted } from 'vue'
// ElMessage 做成功/警告轻提示；ElMessageBox 做不可逆或影响他人操作的二次确认
import { ElMessage, ElMessageBox } from 'element-plus'
// 图标以组件对象形式传给 :icon，避免在模板里内联 SVG
import { Search, Refresh, Plus } from '@element-plus/icons-vue'
// 统一请求实例：已内置 baseURL=/api、自动带 token、统一错误提示与 401 跳转登录
import request from '@/utils/request'

// 列表加载态：绑定 el-table 的 v-loading，防止加载中重复点击导致并发请求
const loading = ref(false)
// 当前页数据：请求成功后整体替换，保证表格内容与后端分页结果一致
const rows = ref([])
// 总条数：同时供分页器 total 与页头"共 N 条"使用
const total = ref(0)
// 表单提交中标记：控制确定按钮 loading，避免重复提交生成重复工单
const saving = ref(false)
// 新建/编辑弹窗显隐
const dialogVisible = ref(false)
// 弹窗标题：用于区分"新建工单"与"编辑工单"两种模式
const dialogTitle = ref('新建工单')
// 表单实例：submitForm 里调用 validate() 触发统一校验
const formRef = ref()
// 工单类型选项：来自 /wo/type/list，页面挂载时并行加载，供筛选与表单下拉使用
const typeOptions = ref([])

// 查询条件默认值：抽成常量，重置时回填，避免在多处重复写同样的字面量
// status/priority 用 null 表示"全部"，与 clearable 清空后的取值保持一致
const query_orig = { page: 1, page_size: 10, title: '', order_no: '', status: null, priority: null }
// 响应式查询对象：分页组件通过 v-model 直接改写 page/page_size，因此必须是 reactive 而非普通对象
const query = reactive({ ...query_orig })

// 状态字典：0 待处理 → 1 处理中 → 2 已解决 → 3 已关闭；顺序即业务流转顺序，label 同时用于筛选、表格与详情
const statusOptions = [
  { value: 0, label: '待处理' },
  { value: 1, label: '处理中' },
  { value: 2, label: '已解决' },
  { value: 3, label: '已关闭' }
]
// 优先级字典：数值越大越紧急，1/2/3 与后端 tinyint 取值一一对应，避免前后端枚举漂移
const priorityOptions = [
  { value: 1, label: '低' },
  { value: 2, label: '中' },
  { value: 3, label: '高' }
]

// 状态值 → 文案：找不到时兜底"未知"，防止脏数据渲染出空白标签
function statusLabel(v) { return statusOptions.find(x => x.value === v)?.label || '未知' }
// 状态值 → el-tag 类型：处理中用 primary 强调"进行中"，已解决用 success，待处理/已关闭用 info 弱化
function statusTag(v) { return ({ 0: 'info', 1: 'primary', 2: 'success', 3: 'info' })[v] || 'info' }
// 优先级值 → 文案：同样兜底"未知"
function priorityLabel(v) { return priorityOptions.find(x => x.value === v)?.label || '未知' }
// 优先级值 → 标签色：低=success(绿)、中=warning(黄)、高=danger(红)，形成"绿黄红"的直觉梯度
function priorityTag(v) { return ({ 1: 'success', 2: 'warning', 3: 'danger' })[v] || 'info' }

// 表单默认值：id=null 表示新建；priority 默认 2(中) 平衡紧急度与填写成本；status 默认 0(待处理) 符合新建即待处理的语义
// creator_id/assignee_id 为 null 表示未填，避免误传 0 这种非法用户 ID
const form_orig = {
  id: null, title: '', content: '', order_type_id: null, priority: 2,
  creator_id: null, assignee_id: null, attachment_ids: '', expect_time: '', status: 0
}
// 响应式表单对象：编辑时用 Object.assign(form, form_orig, row) 就地覆盖，保持模板绑定不失效
const form = reactive({ ...form_orig })

// 校验规则：标题必填（失焦触发，避免边输入边报错）；优先级必填（change 触发，下拉选择后立即反馈）
// 未给 order_type_id/content 加规则，是否必须由后端业务决定，前端不越权拦截
const rules = {
  title: [{ required: true, message: '请输入工单标题', trigger: 'blur' }],
  priority: [{ required: true, message: '请选择优先级', trigger: 'change' }]
}

// 详情抽屉
// 抽屉显隐：详情是纯只读视图，只读取数据，不会触发任何状态变更
const detailVisible = ref(false)
// 详情数据：用列表行直接摊平后填充，缺少的联表字段展示时再做逐级回退
const detailData = reactive({})
// 处理日志：打开详情时异步拉取，失败静默（详情主体不依赖日志也能看）
const workLogs = ref([])

// 指派
// 指派弹窗显隐
const assignVisible = ref(false)
// 指派上下文：只保留工单 id 与标题，提交时仅需 id，标题用于弹窗内回显确认
const assignData = reactive({ id: null, title: '' })
// 指派目标处理人：回填当前处理人，允许改派；为 null 时表示尚未选择
const assignAssignee = ref(null)
// 指派提交中标记：控制"确定指派"按钮 loading，避免重复提交
const assigning = ref(false)

// 接口路径集中映射：把 /wo/order 前缀收敛到一处，避免各函数里散落硬编码字符串
// 返回值按 action 取用，action 拼错时会得到 undefined，便于开发阶段快速发现
function apiUrl(action) {
  const base = '/wo/order'
  return { list: base + '/list', create: base + '/create', update: base + '/update', delete: base + '/delete' }[action]
}

// 拉取列表：params 直接传 query（reactive 对象会被 axios 序列化）
// 错误不在此 catch：request 拦截器已统一提示并 reject，这里只需 finally 复位 loading
async function fetchList() {
  loading.value = true
  try {
    const res = await request.get(apiUrl('list'), { params: query })
    rows.value = res.data.list || []
    total.value = res.data.total || 0
  } finally { loading.value = false }
}

// 加载工单类型下拉：一次取 200 条覆盖常用类型，避免额外分页
// 失败静默：类型只是辅助信息，加载失败不应阻断工单列表主流程
async function loadTypeOptions() {
  try {
    const res = await request.get('/wo/type/list', { params: { page: 1, page_size: 200 } })
    typeOptions.value = res.data.list || []
  } catch { /* ignore */ }
}

// 查询：先把页码重置为 1，否则新条件可能落在越界页导致"查不到数据"的假象
function handleSearch() { query.page = 1; fetchList() }
// 重置：把默认条件整体回填到 query（保留响应式引用），再复用查询逻辑
function handleReset() { Object.assign(query, query_orig); handleSearch() }

// 新建：先回填默认值清空上次输入，再设置标题并打开弹窗
// 这里用 Object.assign 而不是替换对象，避免 form 的响应式引用失效
function openCreate() {
  Object.assign(form, form_orig)
  dialogTitle.value = '新建工单'
  dialogVisible.value = true
}
// 编辑：先铺默认值再覆盖行数据，保证行里缺字段时仍有合法初值（如 undefined 不会写进输入框）
// 行数据可能带额外字段，但提交时会整体透传，后端按白名单处理，前端不做裁剪
function openEdit(row) {
  Object.assign(form, form_orig, row)
  dialogTitle.value = '编辑工单'
  dialogVisible.value = true
}

// 提交表单：validate() 校验通过后才发请求；校验失败会 reject，函数中止，不会误提交
// 按 form.id 区分新建/编辑：编辑时从 form 里剥离 id 走路径参数，避免请求体与路径重复携带主键
async function submitForm() {
  await formRef.value.validate()
  saving.value = true
  try {
    if (form.id) {
      const { id, ...data } = form
      await request.put(`${apiUrl('update')}/${id}`, data); ElMessage.success('更新成功')
    } else {
      await request.post(apiUrl('create'), form); ElMessage.success('新建成功')
    }
    // 成功后关闭弹窗并刷新列表，让用户立刻看到最新数据（含服务端生成的时间/编号字段）
    dialogVisible.value = false; fetchList()
  } finally { saving.value = false }
}

// 查看详情：先把列表行摊平进 detailData，让抽屉立即有内容，避免等待接口时出现空白
// 再异步补拉处理日志；日志接口失败不影响详情主体展示（catch 后仅时间线为空）
async function openDetail(row) {
  Object.assign(detailData, { ...row })
  workLogs.value = []
  try {
    const res = await request.get('/wo/log/list', { params: { order_id: row.id, page: 1, page_size: 50 } })
    workLogs.value = res.data?.list || []
  } catch { /* ignore */ }
  detailVisible.value = true
}

// 打开指派弹窗：回填当前处理人，便于"改派"场景下看出原来是谁
// assignee_id 为 0/空时统一置 null，避免输入框显示 0
function openAssign(row) {
  assignData.id = row.id
  assignData.title = row.title
  assignAssignee.value = row.assignee_id || null
  assignVisible.value = true
}

// 提交指派：表单项没有 prop，走不了统一校验，因此这里手动判断必填并提前 return
// 成功提示后关闭弹窗并刷新列表；finally 保证异常时按钮也能恢复可点击
async function submitAssign() {
  if (!assignAssignee.value) {
    ElMessage.warning('请输入处理人ID'); return
  }
  assigning.value = true
  try {
    await request.put(`/wo/order/assign/${assignData.id}`, { assignee_id: assignAssignee.value })
    ElMessage.success('指派成功')
    assignVisible.value = false; fetchList()
  } finally { assigning.value = false }
}

// 解决工单：先二次确认，confirm 被取消时会 reject，后续接口调用自然不执行
// 成功后刷新列表，让状态列从"处理中"变为"已解决"
async function handleSolve(row) {
  await ElMessageBox.confirm(`确定将工单「${row.title}」标记为已解决？`, '提示', { type: 'warning' })
  await request.put(`/wo/order/solve/${row.id}`)
  ElMessage.success('工单已解决'); fetchList()
}

// 关闭工单：同理先确认再调接口；关闭是不可逆流转，因此不做"点一下直接关闭"的快捷操作
async function handleClose(row) {
  await ElMessageBox.confirm(`确定关闭工单「${row.title}」？`, '提示', { type: 'warning' })
  await request.put(`/wo/order/close/${row.id}`)
  ElMessage.success('工单已关闭'); fetchList()
}

// 删除工单：不可逆操作，必须二次确认
// 后端删除接口按 ids 数组批量处理，这里只传单条，保持与其他模块的调用方式一致
async function handleDelete(row) {
  await ElMessageBox.confirm(`确定删除工单「${row.title}」？`, '提示', { type: 'warning' })
  await request.delete(apiUrl('delete'), { data: { ids: [row.id] } })
  ElMessage.success('删除成功'); fetchList()
}

// 首次挂载：并行发起列表与类型字典请求，缩短首屏等待；两者互不依赖，无需串行 await
onMounted(() => { fetchList(); loadTypeOptions() })
</script>

<style scoped>
/* scoped：样式只作用于本页元素，避免 .op-btns 这类通用命名污染其它页面；颜色统一用 --app-* 主题变量，暗色主题自动适配 */
/* 详情抽屉主体：左右微调 6px 内边距，让内容与抽屉边线留出呼吸感又不显窄 */
.detail-body { padding: 0 6px; }
/* 详情分区：与上一块拉开 20px，形成"基本信息 / 内容 / 附件 / 日志"的纵向层次 */
.detail-section { margin-top: 20px; }
/* 分区标题：14px 加粗 + 底部细分割线；文字色用 --app-text-1（主文本），暗色下自动转为浅色 */
.detail-section-title {
  font-size: 14px; font-weight: 600; color: var(--app-text-1); margin-bottom: 10px;
  padding-bottom: 6px; border-bottom: 1px solid var(--app-border-light);
}
/* 内容块：浅底容器 + pre-wrap 保留原始换行；word-break: break-all 防止长 URL/长工单号撑破 540px 抽屉 */
.detail-content { font-size: 13px; color: var(--app-text-2); line-height: 1.8; padding: 12px 14px; background: var(--app-surface-2); border-radius: 8px; white-space: pre-wrap; word-break: break-all; }
/* 等宽字体：附件 ID 这类逗号分隔的编号串用等宽更易逐段核对，字号略小以放下更多字符 */
.mono { font-family: Menlo, Monaco, Consolas, monospace; font-size: 12px; }
/* 次要文字：用 --app-text-3 做三级弱化，用于"执行了"等连接语，不抢日志主体信息 */
.muted { color: var(--app-text-3); }
/* 日志备注：与操作人行换行区分，12px 正文字色，保持时间线紧凑 */
.log-remark { margin-top: 6px; font-size: 12px; color: var(--app-text-2); }
/* 空态提示：与表格空态同色系弱化处理，提示存在但不喧宾夺主 */
.empty-tip { color: var(--app-text-3); font-size: 12px; padding: 10px 0; }
/* 操作按钮容器：nowrap + flex 让多个 link 按钮单行排列，避免固定在右侧的列内换行导致行高抖动 */
.op-btns { display: flex; flex-wrap: nowrap; align-items: center; white-space: nowrap; }
/* 压缩按钮左右内边距并清零默认 margin：一列要塞下最多 6 个按钮，避免撑破 300px 操作列 */
.op-btns .el-button { margin-left: 0; padding: 0 4px; }
</style>
