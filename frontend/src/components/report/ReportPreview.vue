<!--
  文件级说明：
  职责：报表预览视图——展示报表基本信息、生成记录、KPI 指标、图表（或纯表格）以及数据明细。
  依赖：SimpleChart（自带 SVG 图表渲染）、payload 数据结构由后端报表接口返回。
  被谁使用：BI 报表预览/详情类页面，以 props.payload 传入完整数据后直接渲染。
  说明：本组件是纯展示组件，不发起任何请求，也不修改 payload。
-->
<template>
  <!-- 预览根节点：整体字号 13px，形成比普通页面更紧凑的报表阅读密度 -->
  <div class="report-preview">
    <!-- 报表头部：标题 + 元信息 -->
    <div class="rp-head">
      <div>
        <!-- 报表名称：主标题 -->
        <div class="rp-title">{{ payload.name }}</div>
        <!-- 元信息行：图表类型、分类、数据源、版本、更新时间与数据来源标识 -->
        <div class="rp-meta">
          <!-- 图表类型标签：优先使用后端给出的 chart_label，缺失时用本地映射 typeLabel 兜底 -->
          <el-tag size="small" effect="light">{{ payload.chart_label || typeLabel }}</el-tag>
          <!-- 分类名称：仅在报表配置了分类时显示，避免出现“分类：”后为空 -->
          <span v-if="payload.category_name">分类：{{ payload.category_name }}</span>
          <!-- 数据源名称：仅在有数据源配置时显示 -->
          <span v-if="payload.ds_name">数据源：{{ payload.ds_name }}</span>
          <!-- 版本号：有版本时前缀 v，便于用户核对报表迭代版本 -->
          <span v-if="payload.version">版本：v{{ payload.version }}</span>
          <!-- 更新时间：报表定义的最近修改时间 -->
          <span>更新时间：{{ payload.updated_at }}</span>
          <!-- 数据来源标签：demo 用 warning 色提示为演示数据，其余用 success 色表示实时数据；
               effect=light 使用浅色底，避免在元信息行里过于抢眼 -->
          <el-tag size="small" :type="payload.source === 'demo' ? 'warning' : 'success'" effect="light">
            {{ payload.source === 'demo' ? '演示数据' : '实时数据' }}
          </el-tag>
        </div>
      </div>
    </div>

    <!-- 生成记录条：仅在带 record 时展示，说明本次预览由哪次生成任务产出、耗时与参数 -->
    <div v-if="payload.record" class="rp-record">
      <!-- 生成记录 id：便于排查后台任务 -->
      <span>生成记录 #{{ payload.record.id }}</span>
      <!-- 生成耗时：缺失时兜底为 0ms -->
      <span>耗时 {{ payload.record.cost_time || 0 }} ms</span>
      <!-- 生成时间：缺失时显示短横线 -->
      <span>生成时间 {{ payload.record.gen_time || '-' }}</span>
      <!-- 生成参数：仅当后端记录了查询参数时展示 -->
      <span v-if="payload.record.param">参数：{{ payload.record.param }}</span>
      <!-- 生成失败提示：gen_status=2 表示失败，展示后端错误信息便于用户反馈 -->
      <el-tag v-if="payload.record.gen_status === 2" size="small" type="danger">生成失败：{{ payload.record.error_msg }}</el-tag>
    </div>

    <!-- KPI 卡片区：summary 非空时才渲染，用于展示指标汇总（如总量、均值等） -->
    <div v-if="summary.length" class="rp-kpis">
      <!-- 单个 KPI 卡片：label 作为 key，正常情况下同一报表内指标名唯一 -->
      <div v-for="item in summary" :key="item.label" class="rp-kpi">
        <!-- 指标值 + 可选单位（em 使用普通字重，避免单位看起来和数值一样重） -->
        <div class="rp-kpi-value">{{ item.value }}<em v-if="item.unit">{{ item.unit }}</em></div>
        <!-- 指标名称 -->
        <div class="rp-kpi-label">{{ item.label }}</div>
      </div>
    </div>

    <!-- 纯表格模式：chart='table' 时只渲染数据表格，不再画图表 -->
    <div v-if="payload.chart === 'table'" class="rp-block">
      <!-- 区块标题 -->
      <div class="rp-block-title">报表数据</div>
      <!-- 表格：stripe 斑马纹、border 边框；max-height 限制高度并内部滚动，避免超长表格撑破页面 -->
      <el-table :data="payload.rows" size="small" stripe border max-height="360" empty-text="暂无数据">
        <!-- 列配置完全由 payload.columns 驱动：[{ prop, label }]；min-width + tooltip 保证长文本可读 -->
        <el-table-column v-for="col in payload.columns" :key="col.prop" :prop="col.prop" :label="col.label"
          min-width="120" show-overflow-tooltip />
      </el-table>
    </div>
    <!-- 图表模式：除 table 外的 bar/line/pie 等，统一渲染图表 + 下方数据明细 -->
    <template v-else>
      <!-- 图表区块：固定高度容器，SimpleChart 内部按百分比铺满 -->
      <div class="rp-block rp-chart-block">
        <!-- 简易图表：type 为后端返回的图表类型，categories/series 为数据，unit 与图表纵轴/图例单位对应 -->
        <SimpleChart :type="payload.chart" :categories="payload.categories" :series="payload.series"
          :unit="payload.unit" :height="360" />
      </div>
      <!-- 数据明细区块：图表下方的原始数据表，方便用户核对图表数值 -->
      <div class="rp-block">
        <!-- 区块标题 -->
        <div class="rp-block-title">数据明细</div>
        <!-- 明细表格：高度限制 240px，与上方图表共同构成一屏可读的报表 -->
        <el-table :data="payload.rows" size="small" stripe border max-height="240" empty-text="暂无数据">
          <!-- 列同样由 payload.columns 驱动；明细表列宽略小，以容纳更多列 -->
          <el-table-column v-for="col in payload.columns" :key="col.prop" :prop="col.prop" :label="col.label"
            min-width="110" show-overflow-tooltip />
        </el-table>
      </div>
    </template>
    <!-- SQL 展示：仅当后端返回查询语句时显示，用于核对报表取数逻辑；word-break 处理长语句换行 -->
    <div v-if="payload.sql" class="rp-sql">查询语句：{{ payload.sql }}</div>
  </div>
</template>

<script setup>
// computed 用于派生图表类型中文名与 KPI 列表
import { computed } from 'vue'
// 简易 SVG 图表组件：bar/line/pie/gauge/rank 统一由它渲染
import SimpleChart from '@/components/chart/SimpleChart.vue'

// 唯一 props：payload 为后端报表预览接口返回的完整数据对象（含定义信息、图表数据、明细行、生成记录等）
const props = defineProps({
  payload: { type: Object, default: () => ({}) }
})

// 图表类型 -> 中文名映射：后端未提供 chart_label 时作为兜底展示
const TYPE_LABELS = { bar: '柱状图', line: '折线图', pie: '饼图', table: '数据表格' }
// 当前报表类型的展示文案：未知类型返回空串，模板中 tag 会显示为空标签但不会报错
const typeLabel = computed(() => TYPE_LABELS[props.payload.chart] || '')
// KPI 汇总列表：payload.summary 缺失时返回空数组，模板用 length 判断是否渲染整个 KPI 区块
const summary = computed(() => props.payload.summary || [])
</script>

<style scoped>
/* 预览根节点：整体 13px 基准字号，比后台常规页面更紧凑，适合报表信息密集阅读 */
.report-preview { font-size: 13px; }
/* 头部：两端对齐 + 底部细分割线，把标题信息与下方内容区分开 */
.rp-head { display: flex; justify-content: space-between; padding-bottom: 12px; border-bottom: 1px solid #eef1f6; }
/* 报表标题：18px 加粗深色，作为页面内最突出的文字层级 */
.rp-title { font-size: 18px; font-weight: 600; color: #1f2937; }
/* 元信息行：可换行排列（窄屏自动折行），12px 次级灰色，不抢标题注意力 */
.rp-meta { display: flex; flex-wrap: wrap; align-items: center; gap: 12px; margin-top: 8px; color: #8a94a6; font-size: 12px; }
/* 生成记录条：浅灰蓝底 + 圆角，形成一条独立的信息带；同样允许换行 */
.rp-record { display: flex; flex-wrap: wrap; gap: 14px; margin-top: 12px; padding: 10px 14px; font-size: 12px; color: #667085; background: #f7f9fc; border-radius: 8px; }
/* KPI 网格：auto-fit + minmax(150px,1fr) 让卡片自动换行并等分宽度，适配不同屏宽 */
.rp-kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin: 14px 0; }
/* KPI 卡片：淡蓝渐变底 + 细边框，弱化卡片之间的边界感 */
.rp-kpi { padding: 14px 16px; background: linear-gradient(160deg, #f4f7ff, #f8fafc); border: 1px solid #eef1f6; border-radius: 10px; }
/* KPI 数值：22px 加粗深色，卡片内最高视觉优先级 */
.rp-kpi-value { font-size: 22px; font-weight: 700; color: #1f2937; }
/* KPI 单位：普通字重、12px 灰色，与数值拉开层级（font-style:normal 去掉 em 默认斜体） */
.rp-kpi-value em { margin-left: 3px; font-style: normal; font-size: 12px; font-weight: 500; color: #8a94a6; }
/* KPI 名称：数值下方的小号灰色说明文字 */
.rp-kpi-label { margin-top: 6px; font-size: 12px; color: #8a94a6; }
/* 内容区块：统一上外边距，保证各区块之间节奏一致 */
.rp-block { margin-top: 14px; }
/* 区块标题：13px 加粗深灰，作为表格/图表前的小标题 */
.rp-block-title { margin-bottom: 8px; font-size: 13px; font-weight: 600; color: #475467; }
/* 图表区块：固定 360px 高度（与 SimpleChart 的 height 入参一致），细边框包裹形成卡片感 */
.rp-chart-block { height: 360px; padding: 4px; border: 1px solid #eef1f6; border-radius: 10px; }
/* SQL 区域：等宽字体 + 浅底 + 圆角；word-break:break-all 防止长 SQL 横向撑破容器 */
.rp-sql { margin-top: 12px; padding: 8px 12px; font-family: Consolas, monospace; font-size: 12px; color: #667085; background: #f7f9fc; border-radius: 8px; word-break: break-all; }
</style>
