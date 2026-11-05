<!--
  文件级说明：
  职责：数据绑定管理：把场景对象绑定到数据库/接口/实时通道的数据源，并配置数值区间颜色映射。
  数据来源：/api/scene3d/binding/*，场景与对象下拉来自 /api/scene3d/list 与 /scene3d/object/list。
  安全：表名后端有白名单校验，前端也给出可选表清单，避免用户误填。
-->
<template>
  <div class="app-container scene3d-page">
    <!-- 页头 -->
    <div class="page-header">
      <div>
        <h2>数据绑定</h2>
        <div class="sub">对象 ↔ 数据源 · 支持区间配色 · 共 {{ total }} 条</div>
      </div>
      <el-button v-perm="'scene3d:binding:create'" type="primary" :icon="Plus" @click="openCreate">新增绑定</el-button>
    </div>

    <!-- 筛选：场景 + 类型 + 状态 -->
    <el-card shadow="never" class="search-card">
      <el-form inline @submit.prevent>
        <el-form-item label="场景">
          <el-select v-model="query.scene_id" placeholder="全部场景" clearable filterable style="width: 220px" @change="handleSearch">
            <el-option v-for="s in scenes" :key="s.id" :label="s.scene_name" :value="s.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="数据源">
          <el-select v-model="query.data_source_type" placeholder="全部" clearable style="width: 130px">
            <el-option label="数据库" value="db" />
            <el-option label="接口" value="api" />
            <el-option label="实时通道" value="ws" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 列表 -->
    <el-card shadow="never" class="table-card">
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据绑定">
        <el-table-column label="绑定名称" prop="bind_name" min-width="170" show-overflow-tooltip />
        <el-table-column label="场景对象" prop="object_name" min-width="150" show-overflow-tooltip />
        <el-table-column label="数据源" width="110" align="center">
          <template #default="{ row }">
            <el-tag effect="plain">{{ sourceText(row.data_source_type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="来源配置" min-width="220" show-overflow-tooltip>
          <template #default="{ row }">{{ sourceSummary(row) }}</template>
        </el-table-column>
        <el-table-column label="刷新间隔" width="110" align="right">
          <template #default="{ row }">{{ row.data_source_type === 'ws' ? '实时' : `${row.refresh_interval}s` }}</template>
        </el-table-column>
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'info'">{{ row.status === 1 ? '启用' : '停用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="230" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openPreview(row)">预览读数</el-button>
            <el-button v-perm="'scene3d:binding:update'" link type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button v-perm="'scene3d:binding:delete'" link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination-wrap">
        <el-pagination background layout="total, sizes, prev, pager, next" :total="total"
          v-model:current-page="query.page" v-model:page-size="query.page_size" :page-sizes="[10, 20, 50]" @change="fetchList" />
      </div>
    </el-card>

    <!-- 新增/编辑弹窗 -->
    <el-dialog v-model="dialogVisible" :title="form.id ? '编辑数据绑定' : '新增数据绑定'" width="620px" :close-on-click-modal="false" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="所属场景" prop="scene_id">
          <el-select v-model="form.scene_id" placeholder="请选择场景" filterable style="width: 100%" @change="loadObjects">
            <el-option v-for="s in scenes" :key="s.id" :label="s.scene_name" :value="s.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="场景对象" prop="object_id">
          <el-select v-model="form.object_id" placeholder="请选择对象" filterable style="width: 100%">
            <el-option v-for="o in objectOptions" :key="o.id" :label="`${o.object_name}（${o.object_code}）`" :value="o.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="绑定名称" prop="bind_name">
          <el-input v-model="form.bind_name" placeholder="如：机柜A01进风温度" maxlength="100" />
        </el-form-item>
        <el-form-item label="数据源类型">
          <el-radio-group v-model="form.data_source_type">
            <el-radio value="db">数据库</el-radio>
            <el-radio value="api">接口</el-radio>
            <el-radio value="ws">实时通道</el-radio>
          </el-radio-group>
        </el-form-item>
        <!-- 数据库来源：仅允许白名单表 -->
        <el-form-item v-if="form.data_source_type === 'db'" label="数据表">
          <el-select v-model="form.source_table" placeholder="请选择数据表" style="width: 100%">
            <el-option v-for="t in allowedTables" :key="t" :label="t" :value="t" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="form.data_source_type === 'db'" label="字段名">
          <el-input v-model="form.source_field" placeholder="如：temperature / load" />
        </el-form-item>
        <!-- 接口来源：填写 URL -->
        <el-form-item v-if="form.data_source_type === 'api'" label="接口地址">
          <el-input v-model="form.source_url" placeholder="如 /api/device/read?code=ac_01" />
        </el-form-item>
        <el-form-item v-if="form.data_source_type === 'ws'" label="通道标识">
          <el-input v-model="form.source_url" placeholder="如 ws://host/ws/device" />
        </el-form-item>
        <el-form-item label="刷新间隔">
          <el-input-number v-model="form.refresh_interval" :min="0" :max="3600" :disabled="form.data_source_type === 'ws'" /> <span class="unit">秒（ws 为实时）</span>
        </el-form-item>
        <el-form-item label="映射规则">
          <el-input v-model="form.mapping_text" type="textarea" :rows="4" placeholder='[{"max":28,"color":"#00b42a"},{"max":32,"color":"#ff7d00"},{"color":"#f53f3f"}]' />
          <div class="hint">JSON 数组：按 max 升序匹配区间，最后一项可省略 max 表示兜底。</div>
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

    <!-- 预览读数 -->
    <el-dialog v-model="previewVisible" title="绑定读数预览" width="440px">
      <div class="preview-value" :style="{ borderColor: previewColor }">
        <span class="value">{{ preview.value ?? '-' }}</span>
        <span class="unit">{{ preview.unit }}</span>
      </div>
      <el-descriptions :column="1" border size="small" style="margin-top: 16px">
        <el-descriptions-item label="绑定名称">{{ preview.bind_name }}</el-descriptions-item>
        <el-descriptions-item label="对象ID">{{ preview.object_id }}</el-descriptions-item>
        <el-descriptions-item label="数据来源">{{ sourceText(preview.source) }}</el-descriptions-item>
        <el-descriptions-item label="采集时间">{{ preview.time }}</el-descriptions-item>
      </el-descriptions>
      <div class="hint" style="margin-top: 10px">{{ preview.note }}</div>
    </el-dialog>
  </div>
</template>

<script setup>
// Vue API
import { ref, reactive, onMounted } from 'vue'
// 提示与确认
import { ElMessage, ElMessageBox } from 'element-plus'
// 图标
import { Plus, Search, Refresh } from '@element-plus/icons-vue'
// 接口
import { bindingApi, sceneApi, objectApi } from '@/api/scene3d'

// 白名单与后端保持一致
const allowedTables = ['wf_file', 'sys_user', 'scene3d_scene', 'scene3d_scene_object', 'scene3d_alarm_record']

// 列表状态
const loading = ref(false) // 加载态
const saving = ref(false) // 提交态
const rows = ref([]) // 数据
const total = ref(0) // 总数
const query = reactive({ page: 1, page_size: 20, scene_id: '', data_source_type: '' }) // 查询条件
const scenes = ref([]) // 场景下拉
const objectOptions = ref([]) // 对象下拉

// 弹窗状态
const dialogVisible = ref(false) // 弹窗显隐
const formRef = ref(null) // 表单引用
const form = reactive({
  id: null, scene_id: '', object_id: '', bind_name: '', data_source_type: 'db',
  source_table: 'scene3d_scene_object', source_field: 'temperature', source_url: '',
  refresh_interval: 30, mapping_text: '[]', status: 1, remark: ''
}) // 表单字段

// 校验
const rules = {
  scene_id: [{ required: true, message: '请选择场景', trigger: 'change' }],
  object_id: [{ required: true, message: '请选择对象', trigger: 'change' }],
  bind_name: [{ required: true, message: '请输入绑定名称', trigger: 'blur' }]
}

// 预览状态
const previewVisible = ref(false) // 预览弹窗
const preview = reactive({ bind_name: '', object_id: '', source: '', value: null, unit: '', time: '', note: '' }) // 预览数据
const previewColor = ref('var(--app-border)') // 预览边框色（按映射规则区间）

// 数据源文案
const sourceText = type => ({ db: '数据库', api: '接口', ws: '实时通道' }[type] || type)

// 来源配置摘要
function sourceSummary(row) {
  const cfg = row.source_config || {} // 配置对象
  if (row.data_source_type === 'db') return `${cfg.table || '-'} · ${cfg.field || '-'}` // 表 + 字段
  return cfg.url || '-' // 接口/通道地址
}

// 拉列表
async function fetchList() {
  loading.value = true // 开启
  try {
    const res = await bindingApi.list({ ...query }) // 请求
    rows.value = res.data.list || [] // 数据
    total.value = res.data.total || 0 // 总数
  } finally {
    loading.value = false // 关闭
  }
}

// 拉场景下拉
async function fetchScenes() {
  const res = await sceneApi.list({ page: 1, page_size: 100 }) // 最多 100 个场景
  scenes.value = res.data.list || [] // 缓存
}

// 按场景拉对象
async function loadObjects(sceneId) {
  objectOptions.value = [] // 先清空
  if (!sceneId) return // 未选场景
  const res = await objectApi.list({ page: 1, page_size: 200, scene_id: sceneId }) // 场景对象
  objectOptions.value = res.data.list || [] // 缓存
}

// 查询
function handleSearch() {
  query.page = 1 // 回第一页
  fetchList() // 请求
}

// 重置
function handleReset() {
  Object.assign(query, { page: 1, page_size: 20, scene_id: '', data_source_type: '' }) // 恢复默认
  fetchList() // 请求
}

// 打开新增
async function openCreate() {
  Object.assign(form, {
    id: null, scene_id: query.scene_id || (scenes.value[0] && scenes.value[0].id) || '', object_id: '',
    bind_name: '', data_source_type: 'db', source_table: 'scene3d_scene_object', source_field: 'temperature',
    source_url: '', refresh_interval: 30, mapping_text: '[]', status: 1, remark: ''
  }) // 重置表单
  await loadObjects(form.scene_id) // 加载对象
  dialogVisible.value = true // 打开弹窗
}

// 打开编辑
async function openEdit(row) {
  const cfg = row.source_config || {} // 来源配置
  Object.assign(form, {
    id: row.id, scene_id: row.scene_id, object_id: row.object_id, bind_name: row.bind_name,
    data_source_type: row.data_source_type, source_table: cfg.table || 'scene3d_scene_object',
    source_field: cfg.field || '', source_url: cfg.url || '', refresh_interval: row.refresh_interval || 0,
    mapping_text: JSON.stringify(row.mapping_rule || [], null, 2), status: row.status, remark: row.remark || ''
  }) // 回填
  await loadObjects(row.scene_id) // 加载对象
  dialogVisible.value = true // 打开
}

// 提交
async function submitForm() {
  const valid = await formRef.value.validate().catch(() => false) // 校验
  if (!valid) return // 中断
  let mapping = [] // 映射规则
  try {
    mapping = JSON.parse(form.mapping_text || '[]') // 解析 JSON
    if (!Array.isArray(mapping)) throw new Error('not array') // 必须是数组
  } catch {
    ElMessage.warning('映射规则必须是合法的 JSON 数组') // 格式提示
    return
  }
  const source_config = form.data_source_type === 'db'
    ? { table: form.source_table, field: form.source_field } // 数据库配置
    : { url: form.source_url } // 接口/实时通道配置
  const payload = {
    scene_id: form.scene_id, object_id: form.object_id, bind_name: form.bind_name,
    data_source_type: form.data_source_type, source_config, refresh_interval: form.refresh_interval,
    mapping_rule: mapping, status: form.status, remark: form.remark
  } // 组装入参
  saving.value = true // 防重复
  try {
    if (form.id) await bindingApi.update(form.id, payload) // 编辑
    else await bindingApi.create(payload) // 新增
    ElMessage.success('保存成功') // 提示
    dialogVisible.value = false // 关闭
    fetchList() // 刷新
  } finally {
    saving.value = false // 释放
  }
}

// 预览读数：按映射规则给边框着色，直观看到区间效果
async function openPreview(row) {
  const res = await bindingApi.preview(row.id) // 请求模拟读数
  Object.assign(preview, res.data || {}) // 填充
  previewColor.value = colorByValue(preview.value, row.mapping_rule) // 计算颜色
  previewVisible.value = true // 显示
}

// 区间配色：按 max 升序取第一个命中的颜色
function colorByValue(value, rule) {
  if (!Array.isArray(rule)) return 'var(--chart-1)' // 无规则兜底
  const num = Number(value) // 数值化
  const hit = rule.filter(item => item && (item.max === undefined || item.max === null || num <= Number(item.max))) // 命中区间
  return hit.length ? hit[0].color || 'var(--chart-1)' : 'var(--chart-1)' // 返回颜色
}

// 删除
async function handleDelete(row) {
  await ElMessageBox.confirm(`确认删除绑定「${row.bind_name}」？`, '提示', { type: 'warning' }) // 二次确认
  await bindingApi.remove([row.id]) // 逻辑删除
  ElMessage.success('删除成功') // 提示
  fetchList() // 刷新
}

// 首次加载
onMounted(async () => {
  await fetchScenes() // 先拉场景
  fetchList() // 再拉列表
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
.search-card {
  margin-bottom: var(--app-space-4);
  border-radius: var(--app-radius-lg);
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
/* 表单提示 */
.hint {
  margin-top: 4px;
  color: var(--app-text-3);
  font-size: 12px;
  line-height: 1.6;
}
/* 预览读数：大号数字与单位 */
.preview-value {
  display: flex;
  align-items: baseline;
  justify-content: center;
  gap: 6px;
  padding: var(--app-space-5);
  border: 2px solid var(--app-border);
  border-radius: var(--app-radius-lg);
  background: var(--app-surface-2);
  transition: border-color 0.2s;
}
.preview-value .value {
  font-size: 34px;
  font-weight: 700;
  color: var(--app-text-1);
  font-variant-numeric: tabular-nums;
}
.preview-value .unit {
  margin: 0;
  font-size: 14px;
  color: var(--app-text-3);
}
</style>
