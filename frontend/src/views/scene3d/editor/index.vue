<!--
  文件级说明：
  职责：场景编辑器：加载场景对象，在 3D 画布中预览，左侧对象树增删，右侧属性表单调整位置/旋转/缩放/标签，保存与发布。
  数据来源：场景详情 /scene3d/:id/detail、模型资源 /scene3d/model/list；保存 /scene3d/:id/save、发布 /scene3d/:id/publish。
  实现说明：编辑只改前端对象数组，点击“保存”整体提交（object_code 为稳定键），后端按编码 upsert 并逻辑删除缺省项。
-->
<template>
  <div class="app-container scene3d-page editor-page">
    <!-- 页头：返回 + 场景信息 + 工具按钮 -->
    <div class="page-header">
      <div class="head-left">
        <el-button :icon="ArrowLeft" circle @click="goBack" />
        <div>
          <h2>{{ scene.scene_name || '场景编辑器' }}</h2>
          <div class="sub">
            编码 {{ scene.scene_code }} · {{ objects.length }} 个对象
            <el-tag size="small" :type="scene.scene_status === 1 ? 'success' : 'info'" effect="plain" style="margin-left: 8px">
              {{ ['草稿', '已发布', '已下线'][scene.scene_status] || '草稿' }}
            </el-tag>
            <el-tag v-if="dirty" size="small" type="warning" effect="plain" style="margin-left: 6px">未保存</el-tag>
          </div>
        </div>
      </div>
      <div class="head-actions">
        <el-button :icon="Download" :disabled="!objects.length" @click="exportConfig">导出配置</el-button>
        <el-button v-perm="'scene3d:scene:update'" type="primary" :icon="Check" :loading="saving" @click="saveScene">保存草稿</el-button>
        <el-button v-perm="'scene3d:scene:publish'" type="success" :icon="Promotion" :loading="publishing" @click="publishScene">发布</el-button>
      </div>
    </div>

    <!-- 三栏工作区：左对象树 / 中 3D / 右属性 -->
    <div class="editor-body">
      <!-- 左栏：对象列表 -->
      <aside class="pane left-pane">
        <div class="pane-head">
          <span>场景对象</span>
          <el-button v-perm="'scene3d:object:create'" size="small" type="primary" plain :icon="Plus" @click="openAdd">添加</el-button>
        </div>
        <el-scrollbar class="object-list">
          <div v-for="obj in objects" :key="obj.object_code" class="object-item" :class="{ active: currentCode === obj.object_code }" @click="selectObject(obj)">
            <el-icon class="obj-icon"><Box /></el-icon>
            <div class="obj-main">
              <span class="obj-name" :title="obj.object_name">{{ obj.object_name }}</span>
              <span class="obj-code">{{ obj.object_code }}</span>
            </div>
            <el-button v-perm="'scene3d:object:delete'" link type="danger" :icon="Delete" @click.stop="removeObject(obj)" />
          </div>
          <el-empty v-if="!objects.length" description="暂无对象，点击“添加”选择模型" :image-size="72" />
        </el-scrollbar>
      </aside>

      <!-- 中栏：3D 渲染 -->
      <section class="pane canvas-pane">
        <SceneViewer :objects="viewerObjects" :selected-id="selectedId" :config="scene.scene_config || {}" @select="handleSelect" />
        <!-- 画布上方信息条 -->
        <div class="canvas-bar">
          <span>点击对象可选中；右侧属性实时预览</span>
          <span class="count">{{ objects.length }} obj</span>
        </div>
      </section>

      <!-- 右栏：属性表单 -->
      <aside class="pane right-pane">
        <div class="pane-head"><span>对象属性</span></div>
        <el-scrollbar class="prop-scroll">
          <el-empty v-if="!current" description="请选择左侧对象" :image-size="64" />
          <el-form v-else :model="current" label-position="top" class="prop-form">
            <el-form-item label="对象名称">
              <el-input v-model="current.object_name" maxlength="100" @input="dirty = true" />
            </el-form-item>
            <el-form-item label="对象编码">
              <el-input v-model="current.object_code" maxlength="50" disabled />
            </el-form-item>
            <el-form-item label="模型资源">
              <el-select v-model="current.resource_id" style="width: 100%" @change="dirty = true">
                <el-option v-for="m in models" :key="m.id" :label="m.model_name" :value="m.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="位置 x / y / z">
              <div class="triple">
                <el-input-number v-model="current.position.x" :step="0.1" :precision="2" controls-position="right" @change="dirty = true" />
                <el-input-number v-model="current.position.y" :step="0.1" :precision="2" controls-position="right" @change="dirty = true" />
                <el-input-number v-model="current.position.z" :step="0.1" :precision="2" controls-position="right" @change="dirty = true" />
              </div>
            </el-form-item>
            <el-form-item label="旋转 x / y / z（弧度）">
              <div class="triple">
                <el-input-number v-model="current.rotation.x" :step="0.1" :precision="2" controls-position="right" @change="dirty = true" />
                <el-input-number v-model="current.rotation.y" :step="0.1" :precision="2" controls-position="right" @change="dirty = true" />
                <el-input-number v-model="current.rotation.z" :step="0.1" :precision="2" controls-position="right" @change="dirty = true" />
              </div>
            </el-form-item>
            <el-form-item label="缩放 x / y / z">
              <div class="triple">
                <el-input-number v-model="current.scale.x" :step="0.1" :min="0.1" :precision="2" controls-position="right" @change="dirty = true" />
                <el-input-number v-model="current.scale.y" :step="0.1" :min="0.1" :precision="2" controls-position="right" @change="dirty = true" />
                <el-input-number v-model="current.scale.z" :step="0.1" :min="0.1" :precision="2" controls-position="right" @change="dirty = true" />
              </div>
            </el-form-item>
            <el-form-item label="标签文字">
              <el-input v-model="current.label_text" maxlength="200" @input="dirty = true" />
            </el-form-item>
            <el-form-item label="显示标签">
              <el-switch v-model="current.is_show_label" :active-value="1" :inactive-value="0" @change="dirty = true" />
            </el-form-item>
            <el-form-item label="备注">
              <el-input v-model="current.remark" type="textarea" :rows="2" maxlength="500" @input="dirty = true" />
            </el-form-item>
          </el-form>
        </el-scrollbar>
      </aside>
    </div>

    <!-- 添加对象弹窗 -->
    <el-dialog v-model="addVisible" title="添加场景对象" width="520px" :close-on-click-modal="false" destroy-on-close>
      <el-form ref="addRef" :model="addForm" :rules="addRules" label-width="90px">
        <el-form-item label="模型资源" prop="resource_id">
          <el-select v-model="addForm.resource_id" placeholder="请选择模型" filterable style="width: 100%">
            <el-option v-for="m in models" :key="m.id" :label="`${m.model_name}（${m.model_code}）`" :value="m.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="对象名称" prop="object_name">
          <el-input v-model="addForm.object_name" placeholder="如：机柜A07" maxlength="100" />
        </el-form-item>
        <el-form-item label="对象编码" prop="object_code">
          <el-input v-model="addForm.object_code" placeholder="场景内唯一，如 cabinet_A07" maxlength="50" />
        </el-form-item>
        <el-form-item label="初始位置">
          <div class="triple">
            <el-input-number v-model="addForm.x" :step="0.5" :precision="2" controls-position="right" />
            <el-input-number v-model="addForm.y" :step="0.5" :precision="2" controls-position="right" />
            <el-input-number v-model="addForm.z" :step="0.5" :precision="2" controls-position="right" />
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addVisible = false">取消</el-button>
        <el-button type="primary" @click="addObject">添加</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
// Vue API
import { ref, reactive, computed, watch, onMounted } from 'vue'
// 路由：取场景 id、返回列表
import { useRoute, useRouter } from 'vue-router'
// 提示
import { ElMessage, ElMessageBox } from 'element-plus'
// 图标
import { ArrowLeft, Plus, Delete, Box, Check, Promotion, Download } from '@element-plus/icons-vue'
// 接口
import { sceneApi, modelApi } from '@/api/scene3d'
// 3D 渲染组件
import SceneViewer from '@/components/scene3d/SceneViewer.vue'

// 路由
const route = useRoute() // 当前路由
const router = useRouter() // 编程式跳转
const sceneId = route.params.id // 场景主键

// 场景与对象
const scene = ref({ scene_name: '', scene_code: '', scene_status: 0, scene_config: {} }) // 主表信息
const objects = ref([]) // 对象数组（编辑态）
const models = ref([]) // 模型资源下拉
const currentCode = ref('') // 当前选中对象编码
const dirty = ref(false) // 是否有未保存修改
const saving = ref(false) // 保存态
const publishing = ref(false) // 发布态

// 计算当前选中对象
const current = computed(() => objects.value.find(o => o.object_code === currentCode.value) || null) // 按编码查找
// 传给 3D 组件的选中主键：新对象还没有 id，用索引构造临时 id
const selectedId = computed(() => (current.value ? (current.value.id || `tmp_${current.value.object_code}`) : null))
// 3D 组件需要 id 作为拾取键：映射一份带稳定 id 的数组
const viewerObjects = computed(() => objects.value.map((o, i) => ({ ...o, id: o.id || `tmp_${o.object_code || i}` })))

// 添加弹窗
const addVisible = ref(false) // 显隐
const addRef = ref(null) // 表单引用
const addForm = reactive({ resource_id: '', object_name: '', object_code: '', x: 0, y: 0, z: 0 }) // 表单
const addRules = {
  resource_id: [{ required: true, message: '请选择模型资源', trigger: 'change' }],
  object_name: [{ required: true, message: '请输入对象名称', trigger: 'blur' }],
  object_code: [
    { required: true, message: '请输入对象编码', trigger: 'blur' },
    { pattern: /^[A-Za-z0-9_]+$/, message: '编码仅支持字母、数字与下划线', trigger: 'blur' }
  ]
}

// 数值归一化：保证对象上的向量字段完整
function normalize(obj) {
  const vec = (v, d = 0) => ({ x: Number(v && v.x) || d, y: Number(v && v.y) || d, z: Number(v && v.z) || d }) // 补齐 x/y/z
  return {
    id: obj.id || null, object_code: obj.object_code, object_name: obj.object_name,
    resource_id: obj.resource_id, parent_id: obj.parent_id || null,
    position: vec(obj.position), rotation: vec(obj.rotation), scale: vec(obj.scale, 1),
    label_text: obj.label_text || '', is_show_label: obj.is_show_label === 0 ? 0 : 1,
    sort: obj.sort || 0, remark: obj.remark || '', resource_name: obj.resource_name || ''
  } // 返回规范化对象
}

// 加载场景
async function loadScene() {
  const res = await sceneApi.detail(sceneId) // 详情
  const data = res.data || {} // 数据
  scene.value = data // 主表
  objects.value = (data.objects || []).map(normalize) // 对象
  currentCode.value = objects.value.length ? objects.value[0].object_code : '' // 默认选中第一个
  dirty.value = false // 刚加载无改动
}

// 加载模型下拉
async function loadModels() {
  const res = await modelApi.list({ page: 1, page_size: 200 }) // 最多 200 个
  models.value = res.data.list || [] // 缓存
}

// 3D 点击选中
function handleSelect(payload) {
  const target = objects.value.find(o => String(o.id) === String(payload.id) || `tmp_${o.object_code}` === String(payload.id)) // 兼容临时 id
  if (target) currentCode.value = target.object_code // 同步右侧表单
}

// 左键选中
function selectObject(obj) {
  currentCode.value = obj.object_code // 切换选中
}

// 选择模型后自动补充名称与编码
watch(() => addForm.resource_id, rid => {
  const model = models.value.find(m => m.id === rid) // 匹配模型
  if (model && !addForm.object_name) addForm.object_name = model.model_name // 默认名称
  if (!addForm.object_code) addForm.object_code = `obj_${Date.now().toString(36)}` // 默认唯一编码
})

// 打开添加
function openAdd() {
  Object.assign(addForm, { resource_id: models.value[0] ? models.value[0].id : '', object_name: '', object_code: '', x: 0, y: 0, z: 0 }) // 重置
  addVisible.value = true // 打开
}

// 添加对象到本地数组
function addObject() {
  addRef.value.validate().catch(() => false).then(valid => {
    if (!valid) return // 校验失败
    if (objects.value.some(o => o.object_code === addForm.object_code)) {
      ElMessage.warning('对象编码已存在') // 唯一性提示
      return
    }
    const model = models.value.find(m => m.id === addForm.resource_id) // 模型信息
    objects.value.push(normalize({
      object_code: addForm.object_code, object_name: addForm.object_name, resource_id: addForm.resource_id,
      position: { x: addForm.x, y: addForm.y, z: addForm.z }, rotation: { x: 0, y: 0, z: 0 }, scale: { x: 1, y: 1, z: 1 },
      label_text: addForm.object_name, is_show_label: 1, sort: objects.value.length + 1,
      resource_name: model ? model.model_name : ''
    })) // 入数组
    currentCode.value = addForm.object_code // 选中新对象
    addVisible.value = false // 关闭
    dirty.value = true // 标记未保存
  })
}

// 删除对象（本地移除，保存时后端逻辑删除缺省项）
async function removeObject(obj) {
  await ElMessageBox.confirm(`确认从场景移除「${obj.object_name}」？保存后生效。`, '提示', { type: 'warning' }) // 二次确认
  objects.value = objects.value.filter(o => o.object_code !== obj.object_code) // 过滤
  if (currentCode.value === obj.object_code) currentCode.value = objects.value.length ? objects.value[0].object_code : '' // 修正选中
  dirty.value = true // 标记
}

// 组装提交用的对象数组（不带临时 id）
function payloadObjects() {
  return objects.value.map((o, i) => ({
    object_code: o.object_code, object_name: o.object_name, resource_id: o.resource_id,
    parent_id: o.parent_id, position: o.position, rotation: o.rotation, scale: o.scale,
    label_text: o.label_text, is_show_label: o.is_show_label, sort: i + 1, remark: o.remark
  })) // 保持顺序即层级排序
}

// 保存草稿
async function saveScene() {
  if (!objects.value.length) {
    ElMessage.warning('场景至少需要一个对象才能保存') // 前置提示
    return
  }
  saving.value = true // 防重复
  try {
    await sceneApi.save(sceneId, {
      scene_config: scene.value.scene_config || {}, objects: payloadObjects(),
      version_desc: '编辑器手动保存' // 版本描述
    })
    ElMessage.success('保存成功') // 提示
    dirty.value = false // 清除标记
    await loadScene() // 重新拉取，拿到服务端主键
  } finally {
    saving.value = false // 释放
  }
}

// 发布：先保存再发布，保证发布的是当前编辑内容
async function publishScene() {
  if (!objects.value.length) {
    ElMessage.warning('场景至少需要一个对象才能发布') // 前置提示
    return
  }
  publishing.value = true // 防重复
  try {
    await sceneApi.save(sceneId, { scene_config: scene.value.scene_config || {}, objects: payloadObjects(), version_desc: '发布前保存' }) // 先保存
    await sceneApi.publish(sceneId) // 再发布
    ElMessage.success('发布成功') // 提示
    dirty.value = false // 清除标记
    await loadScene() // 刷新状态
  } finally {
    publishing.value = false // 释放
  }
}

// 导出配置：下载 JSON 文件
async function exportConfig() {
  const res = await sceneApi.exportConfig(sceneId) // 完整配置
  const blob = new Blob([JSON.stringify(res.data, null, 2)], { type: 'application/json' }) // JSON 文件
  const url = URL.createObjectURL(blob) // 临时地址
  const a = document.createElement('a') // 临时链接
  a.href = url
  a.download = `${scene.value.scene_code || 'scene3d'}.json`
  a.click() // 触发下载
  URL.revokeObjectURL(url) // 释放地址
}

// 返回列表
function goBack() {
  router.push('/scene3d/scene') // 菜单路径
}

// 首次加载
onMounted(async () => {
  await loadModels() // 模型
  await loadScene() // 场景
})
</script>

<style scoped>
/* 编辑器页：占满可视高度 */
.editor-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 120px);
  min-height: 520px;
}
/* 页头 */
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: var(--app-space-3);
  flex: 0 0 auto;
}
.head-left {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}
.page-header h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: var(--app-text-1);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.sub {
  margin-top: 2px;
  font-size: 12px;
  color: var(--app-text-3);
}
.head-actions {
  display: flex;
  gap: 8px;
  flex: 0 0 auto;
}
/* 三栏布局：中间自适应，左右固定宽度 */
.editor-body {
  display: grid;
  grid-template-columns: 240px minmax(0, 1fr) 300px;
  gap: var(--app-space-3);
  flex: 1;
  min-height: 0;
}
/* 面板：统一卡片外观，min-width:0 防止子项撑破 */
.pane {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  border: 1px solid var(--app-border-light);
  border-radius: var(--app-radius-lg);
  background: var(--app-surface);
}
/* 面板头 */
.pane-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-bottom: 1px solid var(--app-border-light);
  color: var(--app-text-2);
  font-size: 13px;
  font-weight: 600;
  flex: 0 0 auto;
}
/* 对象列表滚动区 */
.object-list {
  flex: 1;
  min-height: 0;
}
/* 单个对象行 */
.object-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-bottom: 1px solid var(--app-border-light);
  cursor: pointer;
  transition: background 0.15s;
}
.object-item:hover {
  background: var(--app-surface-2);
}
/* 选中态：品牌色左侧描边 + 浅底 */
.object-item.active {
  background: color-mix(in srgb, var(--brand-primary) 8%, transparent);
  box-shadow: inset 3px 0 0 var(--brand-primary);
}
.obj-icon {
  color: var(--app-text-3);
  flex: 0 0 auto;
}
.obj-main {
  display: flex;
  flex-direction: column;
  min-width: 0;
  flex: 1;
}
.obj-name {
  overflow: hidden;
  color: var(--app-text-1);
  font-size: 13px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.obj-code {
  overflow: hidden;
  color: var(--app-text-3);
  font-size: 11px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
/* 画布栏 */
.canvas-pane {
  position: relative;
}
.canvas-pane :deep(.scene-viewer) {
  flex: 1;
  height: 100%;
  border-radius: 0;
}
/* 画布信息条 */
.canvas-bar {
  position: absolute;
  top: 10px;
  left: 12px;
  right: 12px;
  display: flex;
  justify-content: space-between;
  color: var(--app-text-3);
  font-size: 12px;
  pointer-events: none;
}
/* 属性表单滚动区 */
.prop-scroll {
  flex: 1;
  min-height: 0;
  padding: 12px;
}
.prop-form :deep(.el-form-item) {
  margin-bottom: 12px;
}
/* 三分量输入：等宽排列 */
.triple {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 6px;
  width: 100%;
}
.triple :deep(.el-input-number) {
  width: 100%;
}
/* 窄屏：隐藏左右栏，保证画布可用 */
@media (max-width: 1280px) {
  .editor-body {
    grid-template-columns: 210px minmax(0, 1fr) 270px;
  }
}
@media (max-width: 1100px) {
  .editor-body {
    grid-template-columns: minmax(0, 1fr);
  }
  .left-pane,
  .right-pane {
    display: none;
  }
}
</style>
