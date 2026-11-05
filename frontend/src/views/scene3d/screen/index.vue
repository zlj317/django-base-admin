<!--
  文件级说明：
  职责：场景发布页（3D 大屏）：展示已发布场景、资产指标、告警分布与最新告警，并提供预览/分享入口。
  数据来源：/api/scene3d/screen/data 聚合接口（场景/对象/模型/告警全部为真实表统计）。
  展示约定：纯 CSS + 令牌配色，明暗与 5 套配色自动跟随；无数据模块显示引导卡片。
-->
<template>
  <div class="app-container scene3d-page">
    <!-- 页头 -->
    <div class="page-header">
      <div>
        <h2>场景发布</h2>
        <div class="sub">已发布场景对外可见 · 分享页免登录只读 · 数据实时统计</div>
      </div>
      <el-button :icon="Refresh" :loading="loading" @click="loadData">刷新数据</el-button>
    </div>

    <!-- 指标区：4 个真实统计 -->
    <div class="metric-grid">
      <div class="metric-card">
        <span class="label">场景总数</span>
        <span class="value">{{ metrics.scene_total }}</span>
        <span class="foot">其中已发布 {{ metrics.published }} 个</span>
      </div>
      <div class="metric-card">
        <span class="label">场景对象</span>
        <span class="value">{{ metrics.object_total }}</span>
        <span class="foot">机柜 / 设备 / 传感器实例</span>
      </div>
      <div class="metric-card">
        <span class="label">模型资源</span>
        <span class="value">{{ metrics.model_total }}</span>
        <span class="foot">glb / 贴图 / 环境</span>
      </div>
      <div class="metric-card danger">
        <span class="label">未确认告警</span>
        <span class="value">{{ metrics.alarm_unconfirmed }}</span>
        <span class="foot">近 7 天共 {{ alarmTotal }} 条</span>
      </div>
    </div>

    <!-- 两列内容：左侧场景卡片，右侧告警分布 -->
    <div class="content-grid">
      <!-- 已发布场景 -->
      <section class="panel">
        <div class="panel-head">
          <span>已发布场景</span>
          <span class="panel-extra">{{ scenes.length }} 个</span>
        </div>
        <div v-if="scenes.length" class="pub-list">
          <div v-for="item in scenes" :key="item.id" class="pub-item">
            <!-- 场景预览图：主题令牌绘制的线框 -->
            <div class="pub-thumb">
              <div class="iso">
                <span class="f1"></span><span class="f2"></span><span class="f3"></span>
              </div>
            </div>
            <div class="pub-main">
              <div class="pub-name" :title="item.scene_name">{{ item.scene_name }}</div>
              <div class="pub-meta">
                <span>{{ item.category_name || '未分类' }}</span>
                <span>{{ item.object_count }} 对象</span>
                <span>更新 {{ (item.update_time || '').slice(0, 16) }}</span>
              </div>
            </div>
            <div class="pub-ops">
              <el-button size="small" type="primary" plain @click="openView(item)">预览</el-button>
              <el-button size="small" :icon="Link" @click="openShare(item)">分享</el-button>
            </div>
          </div>
        </div>
        <!-- 空态引导：无已发布场景 -->
        <div v-else class="guide-card">
          <el-icon :size="28"><Monitor /></el-icon>
          <p>暂无已发布场景</p>
          <span>请到「3D场景管理」完成对象配置后点击发布，发布后即可在此预览与分享。</span>
          <el-button type="primary" plain @click="goScenePage">去发布场景</el-button>
        </div>
      </section>

      <!-- 告警分布 -->
      <section class="panel">
        <div class="panel-head">
          <span>近 7 天告警分布</span>
          <span class="panel-extra">按级别</span>
        </div>
        <!-- 分布条：纯 CSS，颜色走图表令牌 -->
        <div class="bars">
          <div v-for="(item, idx) in alarmTrend" :key="item.name" class="bar-row">
            <span class="bar-label">{{ item.name }}</span>
            <div class="bar-track">
              <div class="bar-fill" :style="{ width: barWidth(item.value), background: `var(--chart-${idx === 0 ? 2 : idx === 1 ? 4 : 5})` }"></div>
            </div>
            <span class="bar-value">{{ item.value }}</span>
          </div>
        </div>
        <!-- 最新告警 -->
        <div class="panel-head sub-head">
          <span>最新告警</span>
          <span class="panel-extra">最近 5 条</span>
        </div>
        <el-table v-if="recent.length" :data="recent" size="small" class="alarm-table">
          <el-table-column label="场景" prop="scene_name" min-width="130" show-overflow-tooltip />
          <el-table-column label="对象" prop="object_name" min-width="110" show-overflow-tooltip />
          <el-table-column label="级别" width="80" align="center">
            <template #default="{ row }">
              <el-tag size="small" :type="row.alarm_level === 3 ? 'danger' : row.alarm_level === 2 ? 'warning' : 'info'">
                {{ ['提示', '警告', '严重'][row.alarm_level - 1] || '未知' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="时间" prop="create_time" width="160" />
        </el-table>
        <el-empty v-else description="近 7 天没有告警" :image-size="70" />
      </section>
    </div>

    <!-- 分享弹窗 -->
    <el-dialog v-model="shareVisible" title="场景分享" width="500px" :close-on-click-modal="false">
      <el-form label-width="90px">
        <el-form-item label="有效期">
          <el-select v-model="shareDays" style="width: 140px">
            <el-option v-for="d in [1, 3, 7, 15, 30]" :key="d" :label="`${d} 天`" :value="d" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="shareResult" label="分享地址">
          <el-input :model-value="shareUrl(shareResult.share_url)" readonly>
            <template #append><el-button @click="copyLink">复制</el-button></template>
          </el-input>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="shareVisible = false">关闭</el-button>
        <el-button type="primary" :loading="sharing" @click="submitShare">生成链接</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
// Vue API
import { ref, reactive, computed, onMounted } from 'vue'
// 路由：跳转场景管理与分享页
import { useRouter } from 'vue-router'
// 提示
import { ElMessage } from 'element-plus'
// 图标
import { Refresh, Link, Monitor } from '@element-plus/icons-vue'
// 接口
import { screenApi, sceneApi } from '@/api/scene3d'

// 路由
const router = useRouter()

// 页面数据
const loading = ref(false) // 加载态
const metrics = reactive({ scene_total: 0, published: 0, object_total: 0, model_total: 0, alarm_unconfirmed: 0 }) // 指标
const scenes = ref([]) // 已发布场景
const alarmTrend = ref([]) // 告警级别分布
const recent = ref([]) // 最新告警

// 告警总数：分布求和
const alarmTotal = computed(() => (alarmTrend.value || []).reduce((sum, i) => sum + Number(i.value || 0), 0))

// 分享状态
const shareVisible = ref(false) // 显隐
const shareDays = ref(7) // 有效期
const shareResult = ref(null) // 生成结果
const shareSceneId = ref(null) // 当前场景
const sharing = ref(false) // 提交态

// 加载聚合数据
async function loadData() {
  loading.value = true // 开启
  try {
    const res = await screenApi.data() // 聚合接口
    const data = res.data || {} // 数据
    Object.assign(metrics, data.metrics || {}) // 指标
    scenes.value = data.scenes || [] // 场景
    alarmTrend.value = data.alarm_trend || [] // 分布
    recent.value = data.recent_alarms || [] // 最新告警
  } finally {
    loading.value = false // 关闭
  }
}

// 分布条宽度：按最大值归一化，空数据时 0
function barWidth(value) {
  const max = Math.max(...(alarmTrend.value || []).map(i => Number(i.value || 0)), 1) // 最大值兜底 1
  return `${Math.round((Number(value || 0) / max) * 100)}%` // 百分比宽度
}

// 打开预览
function openView(item) {
  window.open(`/scene3d/view/${item.id}`, '_blank') // 新窗口只读
}

// 打开分享
function openShare(item) {
  shareSceneId.value = item.id // 记录场景
  shareDays.value = 7 // 默认 7 天
  shareResult.value = null // 清空
  shareVisible.value = true // 打开
}

// 生成分享
async function submitShare() {
  sharing.value = true // 防重复
  try {
    const res = await sceneApi.share(shareSceneId.value, shareDays.value) // 请求
    shareResult.value = res.data // 结果
    ElMessage.success('分享链接已生成') // 提示
  } finally {
    sharing.value = false // 释放
  }
}

// 完整地址
function shareUrl(path) {
  return path && path.startsWith('http') ? path : `${window.location.origin}${path || ''}` // 拼域名
}

// 复制
async function copyLink() {
  const text = shareUrl(shareResult.value && shareResult.value.share_url) // 地址
  try {
    await navigator.clipboard.writeText(text) // 剪贴板
  } catch {
    const input = document.createElement('textarea') // 兜底
    input.value = text
    document.body.appendChild(input)
    input.select()
    document.execCommand('copy')
    input.remove()
  }
  ElMessage.success('已复制') // 提示
}

// 去场景管理页
function goScenePage() {
  router.push('/scene3d/scene') // 菜单路径
}

// 首次加载
onMounted(loadData)
</script>

<style scoped>
/* 页头 */
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: var(--app-space-4);
}
.page-header h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: var(--app-text-1);
}
.sub {
  margin-top: 4px;
  font-size: 12px;
  color: var(--app-text-3);
}
/* 指标栅格：四列自适应 */
.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--app-space-4);
  margin-bottom: var(--app-space-4);
}
/* 指标卡片 */
.metric-card {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: var(--app-space-4);
  border: 1px solid var(--app-border-light);
  border-radius: var(--app-radius-lg);
  background: linear-gradient(160deg, var(--app-surface), var(--app-surface-2));
}
.metric-card .label {
  font-size: 12px;
  color: var(--app-text-3);
}
.metric-card .value {
  font-size: 30px;
  font-weight: 700;
  line-height: 1.15;
  color: var(--app-text-1);
  font-variant-numeric: tabular-nums;
}
.metric-card .foot {
  font-size: 12px;
  color: var(--app-text-3);
}
/* 告警指标：危险色 */
.metric-card.danger .value {
  color: var(--chart-5);
}
/* 内容两列：minmax(0,1fr) 防止子项撑破 */
.content-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(0, 0.85fr);
  gap: var(--app-space-4);
}
/* 面板：宽度 100%，min-width:0 修复 flex/grid 子项收缩 */
.panel {
  display: flex;
  flex-direction: column;
  width: 100%;
  min-width: 0;
  padding: var(--app-space-4);
  border: 1px solid var(--app-border-light);
  border-radius: var(--app-radius-lg);
  background: var(--app-surface);
}
/* 面板头 */
.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--app-space-3);
  color: var(--app-text-1);
  font-size: 14px;
  font-weight: 600;
}
.panel-extra {
  color: var(--app-text-3);
  font-size: 12px;
  font-weight: 400;
}
/* 子标题：与上方留出间隔 */
.sub-head {
  margin-top: var(--app-space-4);
  padding-top: var(--app-space-3);
  border-top: 1px solid var(--app-border-light);
}
/* 已发布场景列表 */
.pub-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
/* 单个场景行 */
.pub-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px;
  border: 1px solid var(--app-border-light);
  border-radius: var(--app-radius-md);
  background: var(--app-surface-2);
}
/* 缩略图 */
.pub-thumb {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 64px;
  height: 64px;
  flex: 0 0 auto;
  border-radius: var(--app-radius-md);
  background: color-mix(in srgb, var(--brand-primary) 12%, transparent);
}
/* 立方体线框：三个旋转菱形 */
.iso {
  position: relative;
  width: 40px;
  height: 40px;
}
.iso span {
  position: absolute;
  width: 24px;
  height: 24px;
  border: 1px solid color-mix(in srgb, var(--brand-primary) 55%, transparent);
  background: color-mix(in srgb, var(--brand-primary) 22%, transparent);
  transform: rotate(45deg) skew(-8deg, -8deg);
}
.iso .f1 {
  top: 0;
  left: 8px;
}
.iso .f2 {
  top: 14px;
  left: 0;
  opacity: 0.7;
}
.iso .f3 {
  top: 14px;
  left: 16px;
}
/* 场景主信息 */
.pub-main {
  flex: 1;
  min-width: 0;
}
.pub-name {
  overflow: hidden;
  color: var(--app-text-1);
  font-size: 13px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.pub-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 12px;
  margin-top: 3px;
  color: var(--app-text-3);
  font-size: 11px;
}
/* 场景操作 */
.pub-ops {
  display: flex;
  gap: 6px;
  flex: 0 0 auto;
}
/* 空态引导卡片 */
.guide-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 260px;
  padding: var(--app-space-6);
  border: 1px dashed var(--app-border);
  border-radius: var(--app-radius-md);
  color: var(--app-text-3);
  text-align: center;
}
.guide-card p {
  margin: 0;
  color: var(--app-text-2);
  font-size: 14px;
  font-weight: 600;
}
.guide-card span {
  max-width: 380px;
  font-size: 12px;
  line-height: 1.7;
}
/* 分布条 */
.bars {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.bar-row {
  display: grid;
  grid-template-columns: 50px minmax(0, 1fr) 40px;
  align-items: center;
  gap: 10px;
}
.bar-label {
  color: var(--app-text-2);
  font-size: 12px;
}
.bar-track {
  height: 10px;
  overflow: hidden;
  border-radius: 999px;
  background: var(--app-surface-2);
}
.bar-fill {
  height: 100%;
  border-radius: 999px;
  transition: width 0.4s ease;
}
.bar-value {
  color: var(--app-text-1);
  font-size: 12px;
  text-align: right;
  font-variant-numeric: tabular-nums;
}
/* 最新告警表格 */
.alarm-table {
  width: 100%;
}
/* 窄屏：指标两列、内容单列 */
@media (max-width: 1280px) {
  .metric-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
  .content-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
@media (max-width: 900px) {
  .metric-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
