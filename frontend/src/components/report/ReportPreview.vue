<template>
  <div class="report-preview">
    <div class="rp-head">
      <div>
        <div class="rp-title">{{ payload.name }}</div>
        <div class="rp-meta">
          <el-tag size="small" effect="light">{{ payload.chart_label || typeLabel }}</el-tag>
          <span v-if="payload.category_name">分类：{{ payload.category_name }}</span>
          <span v-if="payload.ds_name">数据源：{{ payload.ds_name }}</span>
          <span v-if="payload.version">版本：v{{ payload.version }}</span>
          <span>更新时间：{{ payload.updated_at }}</span>
          <el-tag size="small" :type="payload.source === 'demo' ? 'warning' : 'success'" effect="light">
            {{ payload.source === 'demo' ? '演示数据' : '实时数据' }}
          </el-tag>
        </div>
      </div>
    </div>

    <div v-if="payload.record" class="rp-record">
      <span>生成记录 #{{ payload.record.id }}</span>
      <span>耗时 {{ payload.record.cost_time || 0 }} ms</span>
      <span>生成时间 {{ payload.record.gen_time || '-' }}</span>
      <span v-if="payload.record.param">参数：{{ payload.record.param }}</span>
      <el-tag v-if="payload.record.gen_status === 2" size="small" type="danger">生成失败：{{ payload.record.error_msg }}</el-tag>
    </div>

    <div v-if="summary.length" class="rp-kpis">
      <div v-for="item in summary" :key="item.label" class="rp-kpi">
        <div class="rp-kpi-value">{{ item.value }}<em v-if="item.unit">{{ item.unit }}</em></div>
        <div class="rp-kpi-label">{{ item.label }}</div>
      </div>
    </div>

    <div v-if="payload.chart === 'table'" class="rp-block">
      <div class="rp-block-title">报表数据</div>
      <el-table :data="payload.rows" size="small" stripe border max-height="360" empty-text="暂无数据">
        <el-table-column v-for="col in payload.columns" :key="col.prop" :prop="col.prop" :label="col.label"
          min-width="120" show-overflow-tooltip />
      </el-table>
    </div>
    <template v-else>
      <div class="rp-block rp-chart-block">
        <SimpleChart :type="payload.chart" :categories="payload.categories" :series="payload.series"
          :unit="payload.unit" :height="360" />
      </div>
      <div class="rp-block">
        <div class="rp-block-title">数据明细</div>
        <el-table :data="payload.rows" size="small" stripe border max-height="240" empty-text="暂无数据">
          <el-table-column v-for="col in payload.columns" :key="col.prop" :prop="col.prop" :label="col.label"
            min-width="110" show-overflow-tooltip />
        </el-table>
      </div>
    </template>
    <div v-if="payload.sql" class="rp-sql">查询语句：{{ payload.sql }}</div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import SimpleChart from '@/components/chart/SimpleChart.vue'

const props = defineProps({
  payload: { type: Object, default: () => ({}) }
})

const TYPE_LABELS = { bar: '柱状图', line: '折线图', pie: '饼图', table: '数据表格' }
const typeLabel = computed(() => TYPE_LABELS[props.payload.chart] || '')
const summary = computed(() => props.payload.summary || [])
</script>

<style scoped>
.report-preview { font-size: 13px; }
.rp-head { display: flex; justify-content: space-between; padding-bottom: 12px; border-bottom: 1px solid #eef1f6; }
.rp-title { font-size: 18px; font-weight: 600; color: #1f2937; }
.rp-meta { display: flex; flex-wrap: wrap; align-items: center; gap: 12px; margin-top: 8px; color: #8a94a6; font-size: 12px; }
.rp-record { display: flex; flex-wrap: wrap; gap: 14px; margin-top: 12px; padding: 10px 14px; font-size: 12px; color: #667085; background: #f7f9fc; border-radius: 8px; }
.rp-kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin: 14px 0; }
.rp-kpi { padding: 14px 16px; background: linear-gradient(160deg, #f4f7ff, #f8fafc); border: 1px solid #eef1f6; border-radius: 10px; }
.rp-kpi-value { font-size: 22px; font-weight: 700; color: #1f2937; }
.rp-kpi-value em { margin-left: 3px; font-style: normal; font-size: 12px; font-weight: 500; color: #8a94a6; }
.rp-kpi-label { margin-top: 6px; font-size: 12px; color: #8a94a6; }
.rp-block { margin-top: 14px; }
.rp-block-title { margin-bottom: 8px; font-size: 13px; font-weight: 600; color: #475467; }
.rp-chart-block { height: 360px; padding: 4px; border: 1px solid #eef1f6; border-radius: 10px; }
.rp-sql { margin-top: 12px; padding: 8px 12px; font-family: Consolas, monospace; font-size: 12px; color: #667085; background: #f7f9fc; border-radius: 8px; word-break: break-all; }
</style>
