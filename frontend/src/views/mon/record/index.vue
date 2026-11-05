<!--
  文件级说明：监控告警记录页（只读视图）。
  职责：按规则名称、告警级别、处理状态筛选历史告警，并分页展示；本页只查询，不提供新增/编辑/删除入口。
  依赖：@/utils/request（统一 baseURL=/api、Bearer token 注入、统一错误提示与 401 跳转）；
        Element Plus 的卡片/表单/表格/分页组件；@element-plus/icons-vue 提供的 Search、Refresh 图标。
  数据来源：GET /mon/record/list 分页查询告警记录；GET /mon/rule/list 取前 200 条规则用于下拉与名称翻译。
  被谁使用：由路由挂载在监控模块“告警记录”菜单，是“监控告警规则”页（mon/rule）产生数据的只读落点。
-->
<template>
  <!-- 页面根容器：沿用全局 app-container 的页面内边距与背景，保证与其它管理页视觉一致 -->
  <div class="app-container">
    <!-- 页头区域：左侧标题 + 副标题，全站统一的两段式标题结构 -->
    <div class="page-header">
      <div class="page-title-wrap">
        <!-- 页面主标题：告警记录（历史数据），与告警规则配置页区分开 -->
        <h2>告警记录</h2>
        <!-- 副标题：实时展示当前筛选下的总条数；“只读”提示用户此处不能修改告警 -->
        <div class="sub">告警历史 · 共 {{ total }} 条（只读）</div>
      </div>
    </div>

    <!-- 查询条件卡片：shadow="never" 去掉阴影，与下方表格卡片形成扁平化管理页布局 -->
    <el-card shadow="never" class="search-card">
      <!-- 行内表单；@submit.prevent 阻止浏览器默认回车提交（避免整页刷新），查询统一走按钮或回车事件 -->
      <el-form :model="query" inline @submit.prevent>
        <el-form-item label="规则名称">
          <!-- 规则下拉：双向绑定 query.rule_id，clearable 允许清空为“全部”，宽度固定保持表单对齐 -->
          <el-select v-model="query.rule_id" placeholder="全部" clearable style="width: 200px">
            <!-- 选项来自页面挂载时拉取的 ruleOptions；key 用规则 id，value 提交给后端做 rule_id 精确过滤 -->
            <el-option v-for="r in ruleOptions" :key="r.id" :label="r.rule_name" :value="r.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="告警级别">
          <!-- 告警级别下拉：与后端枚举 info/warning/critical 一一对应，清空即不过滤 -->
          <el-select v-model="query.alarm_level" placeholder="全部" clearable style="width: 110px">
            <!-- info=提示（蓝色标签），属于知会类告警，不阻断业务 -->
            <el-option label="提示" value="info" />
            <!-- warning=警告（橙色标签），指标已越界但业务尚可运行，需关注 -->
            <el-option label="警告" value="warning" />
            <!-- critical=严重（红色标签），指标严重越界，需要立即处理 -->
            <el-option label="严重" value="critical" />
          </el-select>
        </el-form-item>
        <el-form-item label="处理状态">
          <!-- 处理状态下拉：0=待处理，1=已处理，用于只看未闭环的告警 -->
          <el-select v-model="query.handle_status" placeholder="全部" clearable style="width: 110px">
            <!-- 待处理（0）：尚未有人确认或处理，是运维最需要关注的集合 -->
            <el-option label="待处理" :value="0" />
            <!-- 已处理（1）：已被处理人闭环，便于复盘与审计 -->
            <el-option label="已处理" :value="1" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <!-- 查询按钮：触发 handleSearch（先回到第 1 页再请求），图标来自 Search 变量 -->
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <!-- 重置按钮：恢复初始查询条件并重新查询，不影响表格之外的状态 -->
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 数据表格卡片：承载告警列表与分页，与查询卡片区分层次 -->
    <el-card shadow="never" class="table-card">
      <!-- v-loading 与 loading 联动显示遮罩；stripe 斑马纹提升可读性；empty-text 指定空态文案 -->
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据">
        <!-- 序号列：由表格自动生成行号，不依赖后端额外字段 -->
        <el-table-column type="index" label="序号" width="70" align="center" />
        <el-table-column label="规则名称" min-width="160">
          <!-- 记录中只有 rule_id，这里用 getRuleName 翻译成可读名称；找不到时降级显示 id -->
          <template #default="{ row }">{{ getRuleName(row.rule_id) }}</template>
        </el-table-column>
        <el-table-column label="告警级别" width="100" align="center">
          <!-- 级别按后端枚举渲染不同颜色标签，颜色本身就是告警紧急程度的视觉编码 -->
          <template #default="{ row }">
            <!-- info：提示级，默认蓝色标签 -->
            <el-tag v-if="row.alarm_level==='info'" size="small">提示</el-tag>
            <!-- warning：警告级，橙色标签提醒关注 -->
            <el-tag v-else-if="row.alarm_level==='warning'" size="small" type="warning">警告</el-tag>
            <!-- critical：严重级，红色标签提示需立即处置 -->
            <el-tag v-else-if="row.alarm_level==='critical'" size="small" type="danger">严重</el-tag>
            <!-- 兜底：后端出现未知枚举时直接显示原值，避免数据丢失 -->
            <span v-else>{{ row.alarm_level }}</span>
          </template>
        </el-table-column>
        <!-- 告警内容：由规则触发时生成的描述文本；超长时显示省略号并悬浮提示完整内容 -->
        <el-table-column label="告警内容" prop="alarm_content" min-width="220" show-overflow-tooltip />
        <!-- 告警时间：后端已格式化的时间字符串，前端不再做时区/格式化处理 -->
        <el-table-column label="告警时间" prop="alarm_time" width="170" />
        <el-table-column label="处理状态" width="100" align="center">
          <!-- 1=已处理显示绿色；其余（含 0 与空值）统一按待处理显示橙色，避免表格出现空白 -->
          <template #default="{ row }">
            <el-tag v-if="row.handle_status===1" size="small" type="success">已处理</el-tag>
            <el-tag v-else size="small" type="warning">待处理</el-tag>
          </template>
        </el-table-column>
        <!-- 处理人：目前后端返回的是用户 id；为空时显示 “-”，避免待处理记录出现空白 -->
        <el-table-column label="处理人" prop="handler_id" width="100">
          <template #default="{ row }">{{ row.handler_id || '-' }}</template>
        </el-table-column>
        <!-- 处理时间：与处理人一致，未处理时为空串/空值，用 “-” 占位 -->
        <el-table-column label="处理时间" prop="handle_time" width="170">
          <template #default="{ row }">{{ row.handle_time || '-' }}</template>
        </el-table-column>
      </el-table>
      <!-- 分页容器：统一右对齐的内边距样式（样式定义在全局布局样式中） -->
      <div class="pagination-wrap">
        <!-- 分页器：background 为页码加底色；layout 依次显示总数、每页条数、上一页/页码/下一页、跳页输入 -->
        <!-- :total 用后端总条数；current-page / page-size 与 query 双向绑定，翻页即改请求参数 -->
        <el-pagination background layout="total, sizes, prev, pager, next, jumper"
          :total="total" v-model:current-page="query.page" v-model:page-size="query.page_size"
          :page-sizes="[10, 20, 50, 100]" @change="fetchList" />
      </div>
    </el-card>
  </div>
</template>

<script setup>
// 组合式 API 能力：ref 管理标量与数组，reactive 管理可整体重置的查询对象，onMounted 做首屏加载
import { ref, reactive, onMounted } from 'vue'
// 查询/重置按钮图标，保证工具栏按钮与全站风格一致
import { Search, Refresh } from '@element-plus/icons-vue'
// 统一请求实例：已内置 /api 前缀与 Bearer token，业务侧只需处理成功分支（失败由拦截器统一提示）
import request from '@/utils/request'

// 表格加载态：请求期间显示遮罩，防止用户在加载中重复点击查询或翻页
const loading = ref(false)
// 当前页告警记录数组，直接绑定 el-table 的 :data
const rows = ref([])
// 后端返回的总条数：同时供分页组件和页头“共 N 条”使用
const total = ref(0)
// 规则下拉缓存：一次拉取后，筛选下拉与“规则名称”列共用，避免逐行/逐次请求
const ruleOptions = ref([])

// 查询条件初始快照：重置时用它整体覆盖 query，保证清空所有筛选并回到第 1 页
// rule_id / handle_status 用 null 表示“全部”（后端约定 null 不过滤），alarm_level 用空串与后端空值筛选约定一致
const query_orig = { page: 1, page_size: 10, rule_id: null, alarm_level: '', handle_status: null }
// 响应式查询对象：与表单双向绑定，翻页、筛选、重置都直接修改它，请求时整对象作为 params
const query = reactive({ ...query_orig })

// 规则 id -> 规则名称：告警记录只存 rule_id，列表需要展示可读名称
// 找不到（规则已删除或下拉尚未加载）时返回原始 id，避免单元格变成空白
function getRuleName(id) {
  if (!id) return '-'
  const r = ruleOptions.value.find(x => x.id === id)
  return r ? r.rule_name : id
}

// 拉取规则下拉数据：规则数量有限，一次性取 200 条足够，无需分页交互
async function loadRules() {
  try {
    // 走与规则页相同的列表接口，这里只借用其名称字段做展示
    const res = await request.get('/mon/rule/list', { params: { page: 1, page_size: 200 } })
    // 兼容后端返回 null 的情况，兜底空数组
    ruleOptions.value = res.data.list || []
  // 下拉数据失败不阻塞告警列表展示，静默忽略；错误提示由 request 拦截器统一弹出
  // 此处不重新抛错，避免影响首屏其它加载逻辑
  } catch (e) { /* ignore */ }
}

// 列表查询：页面唯一的数据获取入口，查询/重置/翻页均复用，避免多处重复拼装参数
async function fetchList() {
  // 先开 loading，el-table 的 v-loading 随即显示遮罩
  loading.value = true
  try {
    // GET 查询：query 是响应式对象，axios 自动序列化 page/page_size/筛选字段到 URL
    const res = await request.get('/mon/record/list', { params: query })
    // list 兜底空数组，防止后端返回 null 时表格渲染异常
    rows.value = res.data.list || []
    // total 兜底 0，避免分页组件出现 NaN 或页码错乱
    total.value = res.data.total || 0
  // 成功或失败都关闭遮罩，避免异常时页面一直处于加载中
  } finally { loading.value = false }
}

// 点击“查询”：先回到第 1 页，防止沿用旧页码导致新筛选结果为空
function handleSearch() { query.page = 1; fetchList() }
// 点击“重置”：用快照覆盖当前条件（含分页），再复用查询逻辑刷新列表
function handleReset() { Object.assign(query, query_orig); handleSearch() }

// 首屏加载：并行拉取规则下拉与告警列表，二者无依赖；这样首屏即可筛选与展示
onMounted(() => { loadRules(); fetchList() })
</script>
