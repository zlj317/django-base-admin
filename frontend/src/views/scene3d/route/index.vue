<!--
  文件级说明：
  职责：巡检路线页：路线维护（路径点位 JSON）、开始巡检漫游、巡检记录查看。
  数据来源：/api/scene3d/route/*（route、route/record）；漫游对象来自 /scene3d/:id/detail。
  交互：点击“开始巡检”生成记录并弹出 3D 漫游弹窗，相机按点位循环飞行。
-->
<template>
  <div class="app-container scene3d-page">
    <!-- 页头 -->
    <div class="page-header">
      <div>
        <h2>巡检路线</h2>
        <div class="sub">3D 漫游路径 · 点位与视角 · 共 {{ total }} 条</div>
      </div>
      <el-button v-perm="'scene3d:route:create'" type="primary" :icon="Plus" @click="openCreate">新增路线</el-button>
    </div>

    <!-- 页签 -->
    <el-card shadow="never" class="table-card">
      <el-tabs v-model="tab">
        <!-- 路线列表 -->
        <el-tab-pane label="路线配置" name="route">
          <el-table v-loading="loading" :data="rows" stripe empty-text="暂无巡检路线">
            <el-table-column label="路线名称" prop="route_name" min-width="180" show-overflow-tooltip />
            <el-table-column label="路线编码" prop="route_code" min-width="140" />
            <el-table-column label="所属场景" prop="scene_name" min-width="180" show-overflow-tooltip />
            <el-table-column label="点位数" prop="point_count" width="90" align="center" />
            <el-table-column label="速度" width="100" align="right">
              <template #default="{ row }">{{ Number(row.speed).toFixed(2) }}</template>
            </el-table-column>
            <el-table-column label="循环" width="90" align="center">
              <template #default="{ row }">{{ row.cycle_flag === 1 ? '是' : '否' }}</template>
            </el-table-column>
            <el-table-column label="状态" width="90" align="center">
              <template #default="{ row }">
                <el-tag :type="row.status === 1 ? 'success' : 'info'">{{ row.status === 1 ? '启用' : '停用' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="250" fixed="right">
              <template #default="{ row }">
                <el-button v-perm="'scene3d:route:play'" link type="primary" @click="startPatrol(row)">开始巡检</el-button>
                <el-button v-perm="'scene3d:route:update'" link type="primary" @click="openEdit(row)">编辑</el-button>
                <el-button v-perm="'scene3d:route:delete'" link type="danger" @click="removeRoute(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <div class="pagination-wrap">
            <el-pagination background layout="total, prev, pager, next" :total="total" v-model:current-page="query.page" :page-size="20" @change="fetchList" />
          </div>
        </el-tab-pane>

        <!-- 巡检记录 -->
        <el-tab-pane label="巡检记录" name="record">
          <el-table v-loading="recordLoading" :data="recordRows" stripe empty-text="暂无巡检记录">
            <el-table-column label="巡检单号" prop="patrol_code" min-width="180" />
            <el-table-column label="场景" prop="scene_name" min-width="160" show-overflow-tooltip />
            <el-table-column label="路线" prop="route_name" min-width="160" show-overflow-tooltip />
            <el-table-column label="状态" width="110" align="center">
              <template #default="{ row }">
                <el-tag :type="row.patrol_status === 0 ? 'warning' : row.patrol_status === 1 ? 'success' : 'danger'">
                  {{ ['进行中', '正常完成', '异常终止'][row.patrol_status] || '未知' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="异常数" prop="abnormal_count" width="90" align="center" />
            <el-table-column label="开始时间" prop="start_time" width="170" />
            <el-table-column label="结束时间" prop="end_time" width="170">
              <template #default="{ row }">{{ row.end_time || '—' }}</template>
            </el-table-column>
            <el-table-column label="备注" prop="remark" min-width="180" show-overflow-tooltip />
          </el-table>
          <div class="pagination-wrap">
            <el-pagination background layout="total, prev, pager, next" :total="recordTotal" v-model:current-page="recordQuery.page" :page-size="20" @change="fetchRecords" />
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- 新增/编辑弹窗 -->
    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑巡检路线' : '新增巡检路线'" width="640px" :close-on-click-modal="false" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="所属场景" prop="scene_id">
          <el-select v-model="form.scene_id" placeholder="请选择场景" filterable style="width: 100%">
            <el-option v-for="s in scenes" :key="s.id" :label="s.scene_name" :value="s.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="路线名称" prop="route_name">
          <el-input v-model="form.route_name" placeholder="如：机房日常巡检路线" maxlength="100" />
        </el-form-item>
        <el-form-item label="路线编码">
          <el-input v-model="form.route_code" placeholder="如：XJ-ROUTE-001" maxlength="50" />
        </el-form-item>
        <el-form-item label="漫游速度">
          <el-input-number v-model="form.speed" :min="0.1" :max="10" :step="0.1" :precision="2" />
          <span class="unit">点位/秒</span>
        </el-form-item>
        <el-form-item label="循环播放">
          <el-switch v-model="form.cycle_flag" :active-value="1" :inactive-value="0" />
        </el-form-item>
        <el-form-item label="路径点位" prop="way_text">
          <el-input v-model="form.way_text" type="textarea" :rows="8" placeholder='[{"x":0,"y":5,"z":9,"lookAt":{"x":0,"y":1,"z":0}}]' />
          <div class="way-actions">
            <el-button size="small" :disabled="!form.scene_id" @click="generateWayPoints">按场景对象生成点位</el-button>
            <span class="hint">每个点位包含相机坐标 x/y/z 与观察点 lookAt；至少 2 个点。</span>
          </div>
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="form.status" :active-value="1" :inactive-value="0" active-text="启用" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" :rows="2" maxlength="500" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitForm">保存</el-button>
      </template>
    </el-dialog>

    <!-- 巡检漫游弹窗 -->
    <el-dialog v-model="playVisible" title="巡检漫游" width="900px" top="5vh" :close-on-click-modal="false" destroy-on-close @closed="playing = false">
      <div class="play-head">
        <span class="play-title">{{ playInfo.route_name }}</span>
        <span class="play-meta">巡检单号 {{ playInfo.patrol_code }} · {{ viewObjects.length }} 个对象</span>
      </div>
      <div class="play-viewer">
        <!-- 3D 漫游：关闭鼠标交互，避免与动画冲突 -->
        <SceneViewer :objects="viewObjects" :way-points="playInfo.way_points" :playing="playing" :speed="playInfo.speed" :interactive="false" />
      </div>
      <template #footer>
        <el-button @click="playing = !playing">{{ playing ? '暂停' : '继续' }}</el-button>
        <el-button type="primary" @click="playVisible = false">结束巡检</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
// Vue API
import { ref, reactive, onMounted } from 'vue'
// 提示与确认
import { ElMessage, ElMessageBox } from 'element-plus'
// 图标
import { Plus } from '@element-plus/icons-vue'
// 接口
import { patrolApi, sceneApi } from '@/api/scene3d'
// 3D 渲染组件
import SceneViewer from '@/components/scene3d/SceneViewer.vue'

// 页签
const tab = ref('route') // 默认路线配置

// 路线列表
const loading = ref(false) // 加载态
const rows = ref([]) // 数据
const total = ref(0) // 总数
const query = reactive({ page: 1, page_size: 20 }) // 分页
const scenes = ref([]) // 场景下拉

// 巡检记录
const recordLoading = ref(false) // 加载态
const recordRows = ref([]) // 数据
const recordTotal = ref(0) // 总数
const recordQuery = reactive({ page: 1, page_size: 20 }) // 分页

// 弹窗
const dialogVisible = ref(false) // 新增/编辑
const formRef = ref(null) // 表单引用
const saving = ref(false) // 提交态
const form = reactive({
  id: null, scene_id: '', route_name: '', route_code: '', speed: 1.2, cycle_flag: 0, way_text: '[]', status: 1, remark: ''
}) // 路线表单

// 校验
const rules = {
  scene_id: [{ required: true, message: '请选择场景', trigger: 'change' }],
  route_name: [{ required: true, message: '请输入路线名称', trigger: 'blur' }],
  way_text: [{ required: true, message: '请填写路径点位', trigger: 'blur' }]
}

// 漫游弹窗
const playVisible = ref(false) // 显隐
const playing = ref(false) // 是否播放
const viewObjects = ref([]) // 场景对象
const playInfo = reactive({ route_name: '', patrol_code: '', way_points: [], speed: 1.2 }) // 当前漫游数据

// 流列表
async function fetchList() {
  loading.value = true // 开启
  try {
    const res = await patrolApi.list({ ...query }) // 请求
    rows.value = res.data.list || [] // 数据
    total.value = res.data.total || 0 // 总数
  } finally {
    loading.value = false // 关闭
  }
}

// 拉记录
async function fetchRecords() {
  recordLoading.value = true // 开启
  try {
    const res = await patrolApi.records({ ...recordQuery }) // 请求
    recordRows.value = res.data.list || [] // 数据
    recordTotal.value = res.data.total || 0 // 总数
  } finally {
    recordLoading.value = false // 关闭
  }
}

// 拉场景
async function fetchScenes() {
  const res = await sceneApi.list({ page: 1, page_size: 100 }) // 最多 100
  scenes.value = res.data.list || [] // 缓存
}

// 打开新增
function openCreate() {
  Object.assign(form, { id: null, scene_id: scenes.value[0] ? scenes.value[0].id : '', route_name: '', route_code: '', speed: 1.2, cycle_flag: 0, way_text: '[]', status: 1, remark: '' }) // 重置
  dialogVisible.value = true // 打开
}

// 打开编辑
function openEdit(row) {
  Object.assign(form, {
    id: row.id, scene_id: row.scene_id, route_name: row.route_name, route_code: row.route_code,
    speed: Number(row.speed), cycle_flag: row.cycle_flag, way_text: JSON.stringify(row.way_points || [], null, 2),
    status: row.status, remark: row.remark || ''
  }) // 回填
  dialogVisible.value = true // 打开
}

// 按场景对象生成点位：对象上方 1.5m、观察点为对象中心
async function generateWayPoints() {
  if (!form.scene_id) return // 未选场景
  const res = await sceneApi.detail(form.scene_id) // 取场景详情
  const objs = (res.data && res.data.objects) || [] // 对象数组
  if (!objs.length) {
    ElMessage.warning('该场景暂无对象，无法生成点位') // 提示
    return
  }
  const points = objs.slice(0, 8).map(obj => {
    const p = obj.position || {} // 对象坐标
    return {
      x: (Number(p.x) || 0) + 0,
      y: (Number(p.y) || 0) + 4.5,
      z: (Number(p.z) || 0) + 3.5,
      lookAt: { x: Number(p.x) || 0, y: Number(p.y) || 1.2, z: Number(p.z) || 0 }
    } // 相机高处俯视对象
  })
  form.way_text = JSON.stringify(points, null, 2) // 回填文本
  ElMessage.success(`已生成 ${points.length} 个点位，可手工微调`) // 提示
}

// 提交
async function submitForm() {
  const valid = await formRef.value.validate().catch(() => false) // 校验
  if (!valid) return // 中断
  let way = [] // 点位
  try {
    way = JSON.parse(form.way_text || '[]') // 解析
    if (!Array.isArray(way) || way.length < 2) throw new Error('too few') // 至少两个点
  } catch {
    ElMessage.warning('路径点位必须是至少 2 个点的 JSON 数组') // 提示
    return
  }
  const payload = {
    scene_id: form.scene_id, route_name: form.route_name, route_code: form.route_code || '',
    way_points: way, speed: form.speed, cycle_flag: form.cycle_flag, status: form.status, remark: form.remark
  } // 组装
  saving.value = true // 防重复
  try {
    if (form.id) await patrolApi.update(form.id, payload) // 编辑
    else await patrolApi.create(payload) // 新增
    ElMessage.success('保存成功') // 提示
    dialogVisible.value = false // 关闭
    fetchList() // 刷新
  } finally {
    saving.value = false // 释放
  }
}

// 删除
async function removeRoute(row) {
  await ElMessageBox.confirm(`确认删除路线「${row.route_name}」？`, '提示', { type: 'warning' }) // 二次确认
  await patrolApi.remove([row.id]) // 逻辑删除
  ElMessage.success('删除成功') // 提示
  fetchList() // 刷新
}

// 开始巡检：生成记录 + 加载场景对象 + 播放漫游
async function startPatrol(row) {
  const res = await patrolApi.play(row.id) // 生成记录并返回点位
  const data = res.data || {} // 返回体
  playInfo.route_name = row.route_name // 路线名
  playInfo.patrol_code = data.record ? data.record.patrol_code : '' // 巡检单号
  playInfo.way_points = data.way_points || [] // 点位
  playInfo.speed = data.speed || 1.2 // 速度
  const detail = await sceneApi.detail(row.scene_id) // 场景对象
  viewObjects.value = (detail.data && detail.data.objects) || [] // 对象
  playing.value = true // 自动播放
  playVisible.value = true // 打开弹窗
  ElMessage.success('巡检已开始，相机将按路线漫游') // 提示
  fetchRecords() // 刷新记录页签数据
}

// 首次加载
onMounted(async () => {
  await fetchScenes() // 场景下拉
  fetchList() // 路线
  fetchRecords() // 记录
})
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
.table-card {
  border-radius: var(--app-radius-lg);
}
.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: var(--app-space-4);
}
/* 单位说明 */
.unit {
  margin-left: 8px;
  color: var(--app-text-3);
  font-size: 12px;
}
/* 点位操作区 */
.way-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 6px;
}
/* 提示文字 */
.hint {
  color: var(--app-text-3);
  font-size: 12px;
}
/* 漫游弹窗头部 */
.play-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--app-space-3);
}
.play-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--app-text-1);
}
.play-meta {
  font-size: 12px;
  color: var(--app-text-3);
}
/* 3D 容器：固定高度保证 WebGL 有尺寸 */
.play-viewer {
  height: 62vh;
  min-height: 360px;
  border: 1px solid var(--app-border-light);
  border-radius: var(--app-radius-md);
  overflow: hidden;
  background: var(--app-bg);
}
</style>
