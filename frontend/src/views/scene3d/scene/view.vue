<!--
  文件级说明：
  职责：3D 场景只读查看页/分享页（全屏，不挂后台布局）。
  入口：/scene3d/view/:id（登录态，走 /scene3d/:id/detail）；/scene3d/share/:token（免登录，走 /scene3d/share/:token）。
  交互：点击对象查看属性、绑定与告警；顶部显示场景状态与对象统计；分享模式隐藏后台入口。
-->
<template>
  <div class="viewer-page">
    <!-- 顶部栏：场景信息 + 操作 -->
    <header class="viewer-head">
      <div class="brand">
        <div class="logo">3D</div>
        <div>
          <h1>{{ scene.scene_name || '场景加载中…' }}</h1>
          <div class="meta">
            <span>{{ scene.category_name || '未分类' }}</span>
            <span v-if="scene.scene_code">编码 {{ scene.scene_code }}</span>
            <span>{{ objects.length }} 对象</span>
            <el-tag size="small" :type="scene.scene_status === 1 ? 'success' : 'info'" effect="dark">
              {{ ['草稿', '已发布', '已下线'][scene.scene_status] || '草稿' }}
            </el-tag>
            <el-tag v-if="isShare" size="small" type="warning" effect="dark">分享只读</el-tag>
          </div>
        </div>
      </div>
      <div class="head-ops">
        <el-button :icon="Refresh" circle @click="loadData" />
        <el-button v-if="!isShare" @click="goBack">返回后台</el-button>
      </div>
    </header>

    <!-- 主体：画布 + 侧栏 -->
    <main class="viewer-body">
      <div class="canvas-wrap">
        <SceneViewer :objects="objects" :selected-id="selectedId" :config="scene.scene_config || {}" @select="handleSelect" />
        <!-- 左下角操作提示已由组件展示，这里补充空态引导 -->
        <div v-if="!loading && !objects.length" class="canvas-empty">
          <p>该场景尚未配置对象</p>
          <span>请在后台「场景编辑器」添加模型并保存发布后再查看。</span>
        </div>
      </div>

      <!-- 右侧信息栏 -->
      <aside class="side-pane">
        <div class="side-head">对象信息</div>
        <div v-if="current" class="obj-detail">
          <div class="obj-title">{{ current.object_name }}</div>
          <div class="obj-code">{{ current.object_code }}</div>
          <el-descriptions :column="1" size="small" border class="obj-desc">
            <el-descriptions-item label="模型">{{ current.resource_name || '—' }}</el-descriptions-item>
            <el-descriptions-item label="坐标">
              {{ vecText(current.position) }}
            </el-descriptions-item>
            <el-descriptions-item label="缩放">{{ vecText(current.scale) }}</el-descriptions-item>
          </el-descriptions>
          <!-- 绑定数据 -->
          <div class="section-title">数据绑定</div>
          <div v-if="currentBindings.length" class="bind-list">
            <div v-for="b in currentBindings" :key="b.id" class="bind-item">
              <span class="bind-name">{{ b.bind_name }}</span>
              <span class="bind-meta">{{ b.data_source_type === 'db' ? '数据库' : b.data_source_type === 'api' ? '接口' : '实时通道' }} · {{ b.refresh_interval }}s</span>
            </div>
          </div>
          <div v-else class="empty-tip">暂未绑定数据</div>
          <!-- 告警规则 -->
          <div class="section-title">告警规则</div>
          <div v-if="currentRules.length" class="rule-list">
            <div v-for="r in currentRules" :key="r.id" class="rule-item" :style="{ borderLeftColor: (r.alarm_effect && r.alarm_effect.color) || 'var(--chart-4)' }">
              <span>{{ r.rule_name }}</span>
              <span class="rule-cond">{{ r.compare_operator }} {{ r.threshold_value }}</span>
            </div>
          </div>
          <div v-else class="empty-tip">暂无告警规则</div>
        </div>
        <!-- 未选中时展示对象列表 -->
        <div v-else class="obj-list">
          <div v-for="o in objects" :key="o.id" class="obj-row" @click="selectObject(o)">
            <el-icon><Box /></el-icon>
            <span class="row-name">{{ o.object_name }}</span>
            <span class="row-code">{{ o.object_code }}</span>
          </div>
          <div v-if="!objects.length" class="empty-tip">暂无对象</div>
        </div>
      </aside>
    </main>

    <!-- 加载遮罩 -->
    <div v-if="loading" class="loading-mask">
      <el-icon class="is-loading" :size="22"><Loading /></el-icon>
      <span>正在加载场景…</span>
    </div>

    <!-- 错误提示 -->
    <div v-if="errorMessage" class="error-mask">
      <el-result icon="warning" title="场景无法打开" :sub-title="errorMessage">
        <template #extra>
          <el-button v-if="!isShare" type="primary" @click="goBack">返回后台</el-button>
        </template>
      </el-result>
    </div>
  </div>
</template>

<script setup>
// Vue API
import { ref, computed, onMounted } from 'vue'
// 路由：解析 id/token，返回入口
import { useRoute, useRouter } from 'vue-router'
// 接口
import { sceneApi, screenApi } from '@/api/scene3d'
// 3D 组件
import SceneViewer from '@/components/scene3d/SceneViewer.vue'
// 图标
import { Refresh, Box, Loading } from '@element-plus/icons-vue'

// 路由
const route = useRoute() // 当前路由
const router = useRouter() // 返回
const isShare = !!route.params.token // 带 token 即分享模式
const sceneId = route.params.id // 登录查看模式的场景主键

// 数据
const loading = ref(true) // 加载态
const errorMessage = ref('') // 错误文案
const scene = ref({ scene_name: '', scene_code: '', scene_status: 0, scene_config: {} }) // 场景主表
const objects = ref([]) // 对象
const bindings = ref([]) // 绑定
const rules = ref([]) // 规则
const selectedId = ref(null) // 选中对象主键

// 当前对象
const current = computed(() => objects.value.find(o => String(o.id) === String(selectedId.value)) || null) // 按主键匹配

// 当前对象的绑定
const currentBindings = computed(() => (current.value ? bindings.value.filter(b => String(b.object_id) === String(current.value.id)) : [])) // 过滤对象

// 当前对象的告警规则：通过绑定 ID 反查
const currentRules = computed(() => {
  const ids = currentBindings.value.map(b => String(b.id)) // 当前对象的绑定集合
  return rules.value.filter(r => ids.includes(String(r.bind_id))) // 只保留关联规则
})

// 向量格式化
function vecText(v) {
  const p = v || {} // 空对象兜底
  return `x ${Number(p.x || 0).toFixed(1)} / y ${Number(p.y || 0).toFixed(1)} / z ${Number(p.z || 0).toFixed(1)}` // 统一保留一位
}

// 加载数据：分享走 token，查看走 id
async function loadData() {
  loading.value = true // 开启
  errorMessage.value = '' // 清除错误
  try {
    const res = isShare ? await screenApi.share(route.params.token) : await sceneApi.detail(sceneId) // 按模式请求
    const data = (res && res.data) || {} // 数据体
    scene.value = data // 主表
    objects.value = (data.objects || []).map(o => ({ ...o, resource_name: o.resource_name })) // 对象
    bindings.value = data.bindings || [] // 绑定
    rules.value = data.rules || [] // 规则
    selectedId.value = objects.value.length ? objects.value[0].id : null // 默认选中第一个
  } catch (err) {
    const msg = (err && err.message) || '链接无效或场景未发布' // 兜底文案
    errorMessage.value = msg // 展示错误
  } finally {
    loading.value = false // 关闭
  }
}

// 3D 点击
function handleSelect(payload) {
  selectedId.value = payload.id // 同步侧栏
}

// 列表点击
function selectObject(obj) {
  selectedId.value = obj.id // 同步画布高亮
}

// 返回后台：查看页回场景列表，分享页关闭标签页
function goBack() {
  if (isShare) window.close() // 分享页尝试关闭窗口
  else router.push('/scene3d/screen') // 查看页回发布大屏
}

// 首次加载
onMounted(loadData)
</script>

<style scoped>
/* 页面：深色/浅色背景由主题令牌决定，铺满窗口 */
.viewer-page {
  position: relative;
  display: flex;
  flex-direction: column;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  background: var(--app-bg);
  color: var(--app-text-1);
}
/* 顶部栏 */
.viewer-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 12px 20px;
  border-bottom: 1px solid var(--app-border-light);
  background: var(--app-surface);
  flex: 0 0 auto;
}
/* 品牌区 */
.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}
/* Logo 方块：品牌色渐变 */
.logo {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  flex: 0 0 auto;
  border-radius: 10px;
  background: linear-gradient(135deg, var(--brand-primary), color-mix(in srgb, var(--brand-primary) 55%, #000));
  color: #fff;
  font-size: 15px;
  font-weight: 700;
  letter-spacing: 1px;
}
/* 标题 */
.brand h1 {
  margin: 0;
  font-size: 17px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
/* 元信息 */
.meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 3px;
  color: var(--app-text-3);
  font-size: 12px;
}
/* 顶部操作 */
.head-ops {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 0 0 auto;
}
/* 主体：画布 + 侧栏，min-width:0 防止画布撑破 */
.viewer-body {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  gap: 0;
  flex: 1;
  min-height: 0;
}
/* 画布容器 */
.canvas-wrap {
  position: relative;
  min-width: 0;
  min-height: 0;
  padding: 12px;
}
.canvas-wrap :deep(.scene-viewer) {
  height: 100%;
}
/* 画布空态引导 */
.canvas-empty {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
  color: var(--app-text-3);
  pointer-events: none;
}
.canvas-empty p {
  margin: 0 0 6px;
  color: var(--app-text-2);
  font-size: 14px;
  font-weight: 600;
}
.canvas-empty span {
  font-size: 12px;
}
/* 侧栏 */
.side-pane {
  display: flex;
  flex-direction: column;
  min-width: 0;
  border-left: 1px solid var(--app-border-light);
  background: var(--app-surface);
  overflow: hidden;
}
/* 侧栏头 */
.side-head {
  padding: 12px 14px;
  border-bottom: 1px solid var(--app-border-light);
  color: var(--app-text-2);
  font-size: 13px;
  font-weight: 600;
  flex: 0 0 auto;
}
/* 对象详情滚动区 */
.obj-detail,
.obj-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 12px 14px;
}
/* 对象标题 */
.obj-title {
  font-size: 15px;
  font-weight: 600;
}
/* 对象编码 */
.obj-code {
  margin-bottom: 8px;
  color: var(--app-text-3);
  font-size: 12px;
}
/* 描述表 */
.obj-desc {
  margin-bottom: 12px;
}
/* 分区标题 */
.section-title {
  margin: 14px 0 8px;
  color: var(--app-text-2);
  font-size: 12px;
  font-weight: 600;
}
/* 绑定列表 */
.bind-list,
.rule-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
/* 绑定项 */
.bind-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 8px;
  border: 1px solid var(--app-border-light);
  border-radius: var(--app-radius-md);
  background: var(--app-surface-2);
  font-size: 12px;
}
.bind-name {
  overflow: hidden;
  color: var(--app-text-1);
  text-overflow: ellipsis;
  white-space: nowrap;
}
.bind-meta {
  flex: 0 0 auto;
  color: var(--app-text-3);
}
/* 规则项：左侧色条表示告警颜色 */
.rule-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 7px 8px;
  border-left: 3px solid var(--chart-4);
  border-radius: var(--app-radius-sm);
  background: var(--app-surface-2);
  font-size: 12px;
}
.rule-cond {
  color: var(--app-text-3);
}
/* 对象列表行 */
.obj-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 6px;
  border-bottom: 1px solid var(--app-border-light);
  color: var(--app-text-3);
  font-size: 12px;
  cursor: pointer;
}
.obj-row:hover {
  background: var(--app-surface-2);
}
.row-name {
  flex: 1;
  overflow: hidden;
  color: var(--app-text-1);
  text-overflow: ellipsis;
  white-space: nowrap;
}
.row-code {
  flex: 0 0 auto;
  font-size: 11px;
}
/* 空提示 */
.empty-tip {
  padding: 10px 0;
  color: var(--app-text-3);
  font-size: 12px;
  text-align: center;
}
/* 加载遮罩 */
.loading-mask,
.error-mask {
  position: absolute;
  inset: 0;
  z-index: 10;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: var(--app-text-3);
  font-size: 13px;
  background: color-mix(in srgb, var(--app-bg) 88%, transparent);
}
/* 窄屏：隐藏侧栏 */
@media (max-width: 1100px) {
  .viewer-body {
    grid-template-columns: minmax(0, 1fr);
  }
  .side-pane {
    display: none;
  }
}
</style>
