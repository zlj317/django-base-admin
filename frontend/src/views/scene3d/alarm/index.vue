<!--
  文件级说明：
  职责：告警联动页：告警规则维护 + 告警记录确认 + 近 7 天统计。
  数据来源：/api/scene3d/alarm/*（规则 scene3d_alarm_rule、记录 scene3d_alarm_record、统计聚合）。
  交互：规则与记录用页签切换；未确认记录可直接确认，已确认记录只读。
-->
<template>
  <div class="app-container scene3d-page">
    <!-- 页头 -->
    <div class="page-header">
      <div>
        <h2>告警联动</h2>
        <div class="sub">阈值规则 · 三维闪烁/光晕表现 · 近 {{ stats.days || 7 }} 天统计</div>
      </div>
      <el-button v-perm="'scene3d:alarm:create'" type="primary" :icon="Plus" @click="openRuleCreate">新增规则</el-button>
    </div>

    <!-- 统计卡片：全部来自真实告警记录 -->
    <div class="stat-grid">
      <div class="stat-card">
        <span class="label">告警总数</span>
        <span class="num">{{ stats.total }}</span>
        <span class="foot">近 {{ stats.days || 7 }} 天</span>
      </div>
      <div class="stat-card warn">
        <span class="label">未确认</span>
        <span class="num">{{ stats.unconfirmed }}</span>
        <span class="foot">需及时处置</span>
      </div>
      <div class="stat-card ok">
        <span class="label">已确认</span>
        <span class="num">{{ stats.confirmed }}</span>
        <span class="foot">已处置完成</span>
      </div>
      <div class="stat-card level-3">
        <span class="label">严重告警</span>
        <span class="num">{{ levelValue(3) }}</span>
        <span class="foot">需要立即响应</span>
      </div>
    </div>

    <!-- 页签：规则 / 记录 -->
    <el-card shadow="never" class="table-card">
      <el-tabs v-model="tab">
        <!-- 规则页签 -->
        <el-tab-pane label="告警规则" name="rule">
          <el-table v-loading="ruleLoading" :data="rules" stripe empty-text="暂无告警规则">
            <el-table-column label="规则名称" prop="rule_name" min-width="180" show-overflow-tooltip />
            <el-table-column label="绑定对象" prop="object_name" min-width="150" />
            <el-table-column label="绑定名称" prop="bind_name" min-width="160" show-overflow-tooltip />
            <el-table-column label="条件" width="150" align="center">
              <template #default="{ row }">{{ row.compare_operator }} {{ row.threshold_value }}</template>
            </el-table-column>
            <el-table-column label="级别" width="100" align="center">
              <template #default="{ row }">
                <el-tag :type="levelTag(row.alarm_level)">{{ levelText(row.alarm_level) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="视觉表现" min-width="180">
              <template #default="{ row }">
                <span class="effect-dot" :style="{ background: effectColor(row) }"></span>
                {{ effectText(row) }}
              </template>
            </el-table-column>
            <el-table-column label="状态" width="90" align="center">
              <template #default="{ row }">
                <el-tag :type="row.status === 1 ? 'success' : 'info'">{{ row.status === 1 ? '启用' : '停用' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="150" fixed="right">
              <template #default="{ row }">
                <el-button v-perm="'scene3d:alarm:update'" link type="primary" @click="openRuleEdit(row)">编辑</el-button>
                <el-button v-perm="'scene3d:alarm:delete'" link type="danger" @click="removeRule(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <div class="pagination-wrap">
            <el-pagination background layout="total, prev, pager, next" :total="ruleTotal" v-model:current-page="ruleQuery.page" :page-size="20" @change="fetchRules" />
          </div>
        </el-tab-pane>

        <!-- 记录页签 -->
        <el-tab-pane label="告警记录" name="record">
          <el-form inline class="record-filter">
            <el-form-item label="状态">
              <el-select v-model="recordQuery.alarm_status" placeholder="全部" clearable style="width: 120px" @change="handleRecordSearch">
                <el-option label="未确认" :value="0" />
                <el-option label="已确认" :value="1" />
                <el-option label="已闭环" :value="2" />
              </el-select>
            </el-form-item>
            <el-form-item label="级别">
              <el-select v-model="recordQuery.alarm_level" placeholder="全部" clearable style="width: 120px" @change="handleRecordSearch">
                <el-option label="提示" :value="1" />
                <el-option label="警告" :value="2" />
                <el-option label="严重" :value="3" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button :icon="Refresh" @click="handleRecordReset">重置</el-button>
            </el-form-item>
          </el-form>
          <el-table v-loading="recordLoading" :data="records" stripe empty-text="暂无告警记录">
            <el-table-column label="场景" prop="scene_name" min-width="150" show-overflow-tooltip />
            <el-table-column label="对象" prop="object_name" min-width="130" />
            <el-table-column label="规则" prop="rule_name" min-width="150" show-overflow-tooltip />
            <el-table-column label="触发值" prop="alarm_value" width="100" align="center" />
            <el-table-column label="级别" width="90" align="center">
              <template #default="{ row }">
                <el-tag :type="levelTag(row.alarm_level)">{{ levelText(row.alarm_level) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="100" align="center">
              <template #default="{ row }">
                <el-tag :type="row.alarm_status === 0 ? 'warning' : row.alarm_status === 1 ? 'success' : 'info'">{{ statusText(row.alarm_status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="发生时间" prop="create_time" width="170" />
            <el-table-column label="确认时间" prop="confirm_time" width="170">
              <template #default="{ row }">{{ row.confirm_time || '—' }}</template>
            </el-table-column>
            <el-table-column label="操作" width="110" fixed="right">
              <template #default="{ row }">
                <el-button v-if="row.alarm_status === 0" v-perm="'scene3d:alarm:confirm'" link type="primary" @click="confirmRecord(row)">确认</el-button>
                <span v-else class="muted">已处理</span>
              </template>
            </el-table-column>
          </el-table>
          <div class="pagination-wrap">
            <el-pagination background layout="total, prev, pager, next" :total="recordTotal" v-model:current-page="recordQuery.page" :page-size="20" @change="fetchRecords" />
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- 规则弹窗 -->
    <el-dialog v-model="ruleDialog" :title="ruleForm.id ? '编辑告警规则' : '新增告警规则'" width="560px" :close-on-click-modal="false" destroy-on-close>
      <el-form ref="ruleRef" :model="ruleForm" :rules="ruleRules" label-width="100px">
        <el-form-item label="关联绑定" prop="bind_id">
          <el-select v-model="ruleForm.bind_id" placeholder="请选择数据绑定" filterable style="width: 100%">
            <el-option v-for="b in binds" :key="b.id" :label="`${b.bind_name}（${b.object_name || '-'}）`" :value="b.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="规则名称" prop="rule_name">
          <el-input v-model="ruleForm.rule_name" placeholder="如：机柜温度偏高" maxlength="100" />
        </el-form-item>
        <el-form-item label="比较条件" prop="threshold_value">
          <el-select v-model="ruleForm.compare_operator" style="width: 110px">
            <el-option label=">" value=">" />
            <el-option label=">=" value=">=" />
            <el-option label="<" value="<" />
            <el-option label="<=" value="<=" />
            <el-option label="=" value="=" />
          </el-select>
          <el-input v-model="ruleForm.threshold_value" placeholder="阈值，如 28" style="flex: 1; margin-left: 8px" />
        </el-form-item>
        <el-form-item label="告警级别">
          <el-radio-group v-model="ruleForm.alarm_level">
            <el-radio :value="1">提示</el-radio>
            <el-radio :value="2">警告</el-radio>
            <el-radio :value="3">严重</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="视觉表现">
          <el-checkbox v-model="ruleForm.blink">闪烁</el-checkbox>
          <el-checkbox v-model="ruleForm.glow">光晕</el-checkbox>
          <el-input v-model="ruleForm.effect_color" placeholder="颜色如 #ff7d00" style="width: 150px; margin-left: 8px" />
        </el-form-item>
        <el-form-item label="通知/流程">
          <el-switch v-model="ruleForm.is_auto_notice" :active-value="1" :inactive-value="0" active-text="自动推送消息" />
          <el-switch v-model="ruleForm.is_auto_workflow" :active-value="1" :inactive-value="0" active-text="自动发起审批" style="margin-left: 16px" />
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="ruleForm.status" :active-value="1" :inactive-value="0" active-text="启用" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="ruleForm.remark" type="textarea" :rows="2" maxlength="500" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="ruleDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitRule">保存</el-button>
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
import { Plus, Refresh } from '@element-plus/icons-vue'
// 接口
import { alarmApi, bindingApi } from '@/api/scene3d'

// 页签
const tab = ref('rule') // 默认展示规则

// 统计
const stats = reactive({ days: 7, total: 0, unconfirmed: 0, confirmed: 0, by_level: [] }) // 统计结果

// 规则列表
const ruleLoading = ref(false) // 加载态
const rules = ref([]) // 数据
const ruleTotal = ref(0) // 总数
const ruleQuery = reactive({ page: 1, page_size: 20 }) // 分页
const binds = ref([]) // 绑定下拉

// 规则弹窗
const ruleDialog = ref(false) // 显隐
const ruleRef = ref(null) // 表单引用
const saving = ref(false) // 提交态
const ruleForm = reactive({
  id: null, bind_id: '', rule_name: '', compare_operator: '>=', threshold_value: '28', alarm_level: 2,
  blink: true, glow: true, effect_color: '#ff7d00', is_auto_notice: 1, is_auto_workflow: 0, status: 1, remark: ''
}) // 规则表单

// 规则校验
const ruleRules = {
  bind_id: [{ required: true, message: '请选择数据绑定', trigger: 'change' }],
  rule_name: [{ required: true, message: '请输入规则名称', trigger: 'blur' }],
  threshold_value: [{ required: true, message: '请输入阈值', trigger: 'blur' }]
}

// 记录列表
const recordLoading = ref(false) // 加载态
const records = ref([]) // 数据
const recordTotal = ref(0) // 总数
const recordQuery = reactive({ page: 1, page_size: 20, alarm_status: '', alarm_level: '' }) // 查询

// 级别文案/标签
const levelText = level => ({ 1: '提示', 2: '警告', 3: '严重' }[level] || level) // 文案
const levelTag = level => ({ 1: 'info', 2: 'warning', 3: 'danger' }[level] || 'info') // 标签类型
const statusText = status => ({ 0: '未确认', 1: '已确认', 2: '已闭环', 3: '已忽略' }[status] || status) // 记录状态

// 从统计里取某级别数量
function levelValue(level) {
  const item = (stats.by_level || []).find(i => i.level === level) // 匹配级别
  return item ? item.value : 0 // 无匹配返回 0
}

// 规则视觉表现颜色
function effectColor(row) {
  return (row.alarm_effect && row.alarm_effect.color) || 'var(--chart-4)' // 取配置色，兜底图表色
}

// 规则视觉表现文字
function effectText(row) {
  const e = row.alarm_effect || {} // 配置
  const items = [] // 描述片段
  if (e.blink) items.push('闪烁') // 闪烁
  if (e.glow) items.push('光晕') // 光晕
  return items.length ? items.join(' + ') : '静态高亮' // 默认静态
}

// 拉规则
async function fetchRules() {
  ruleLoading.value = true // 开启
  try {
    const res = await alarmApi.rules({ ...ruleQuery }) // 请求
    rules.value = res.data.list || [] // 数据
    ruleTotal.value = res.data.total || 0 // 总数
  } finally {
    ruleLoading.value = false // 关闭
  }
}

// 拉记录
async function fetchRecords() {
  recordLoading.value = true // 开启
  try {
    const res = await alarmApi.records({ ...recordQuery }) // 请求
    records.value = res.data.list || [] // 数据
    recordTotal.value = res.data.total || 0 // 总数
  } finally {
    recordLoading.value = false // 关闭
  }
}

// 拉统计
async function fetchStats() {
  const res = await alarmApi.stats({ days: 7 }) // 近 7 天
  Object.assign(stats, res.data || {}) // 覆盖统计
}

// 拉绑定下拉
async function fetchBinds() {
  const res = await bindingApi.list({ page: 1, page_size: 200 }) // 最多 200 条
  binds.value = res.data.list || [] // 缓存
}

// 记录筛选
function handleRecordSearch() {
  recordQuery.page = 1 // 回第一页
  fetchRecords() // 请求
}

// 记录重置
function handleRecordReset() {
  Object.assign(recordQuery, { page: 1, page_size: 20, alarm_status: '', alarm_level: '' }) // 清空
  fetchRecords() // 请求
}

// 打开新增规则
function openRuleCreate() {
  Object.assign(ruleForm, {
    id: null, bind_id: '', rule_name: '', compare_operator: '>=', threshold_value: '28', alarm_level: 2,
    blink: true, glow: true, effect_color: '#ff7d00', is_auto_notice: 1, is_auto_workflow: 0, status: 1, remark: ''
  }) // 重置
  ruleDialog.value = true // 打开
}

// 打开编辑规则
function openRuleEdit(row) {
  const effect = row.alarm_effect || {} // 视觉表现
  Object.assign(ruleForm, {
    id: row.id, bind_id: row.bind_id, rule_name: row.rule_name, compare_operator: row.compare_operator,
    threshold_value: String(row.threshold_value), alarm_level: row.alarm_level,
    blink: !!effect.blink, glow: !!effect.glow, effect_color: effect.color || '#ff7d00',
    is_auto_notice: row.is_auto_notice, is_auto_workflow: row.is_auto_workflow, status: row.status, remark: row.remark || ''
  }) // 回填
  ruleDialog.value = true // 打开
}

// 提交规则
async function submitRule() {
  const valid = await ruleRef.value.validate().catch(() => false) // 校验
  if (!valid) return // 中断
  const payload = {
    bind_id: ruleForm.bind_id, rule_name: ruleForm.rule_name, compare_operator: ruleForm.compare_operator,
    threshold_value: String(ruleForm.threshold_value), alarm_level: ruleForm.alarm_level,
    alarm_effect: { blink: ruleForm.blink, glow: ruleForm.glow, color: ruleForm.effect_color },
    is_auto_notice: ruleForm.is_auto_notice, is_auto_workflow: ruleForm.is_auto_workflow,
    status: ruleForm.status, remark: ruleForm.remark
  } // 组装
  saving.value = true // 防重复
  try {
    if (ruleForm.id) await alarmApi.ruleUpdate(ruleForm.id, payload) // 编辑
    else await alarmApi.ruleCreate(payload) // 新增
    ElMessage.success('保存成功') // 提示
    ruleDialog.value = false // 关闭
    fetchRules() // 刷新
  } finally {
    saving.value = false // 释放
  }
}

// 删除规则
async function removeRule(row) {
  await ElMessageBox.confirm(`确认删除规则「${row.rule_name}」？`, '提示', { type: 'warning' }) // 二次确认
  await alarmApi.ruleRemove([row.id]) // 逻辑删除
  ElMessage.success('删除成功') // 提示
  fetchRules() // 刷新
}

// 确认告警
async function confirmRecord(row) {
  const { value } = await ElMessageBox.prompt('请输入处置备注（可留空直接确认）', `确认告警：${row.alarm_value}`, {
    inputPlaceholder: '如：已通知运维现场处理', inputValidator: () => true, confirmButtonText: '确认', cancelButtonText: '取消'
  }).catch(() => ({ value: null })) // 取消时返回 null
  if (value === null) return // 用户取消
  await alarmApi.confirm(row.id, value) // 提交确认
  ElMessage.success('已确认') // 提示
  fetchRecords() // 刷新记录
  fetchStats() // 刷新统计
}

// 首次加载
onMounted(async () => {
  await fetchBinds() // 先拉下拉，规则表单可用
  fetchRules() // 规则
  fetchRecords() // 记录
  fetchStats() // 统计
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
/* 统计四宫格：自适应列宽 */
.stat-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--app-space-4);
  margin-bottom: var(--app-space-4);
}
/* 统计卡片 */
.stat-card {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: var(--app-space-4);
  border: 1px solid var(--app-border-light);
  border-radius: var(--app-radius-lg);
  background: var(--app-surface);
}
/* 卡片标签 */
.stat-card .label {
  font-size: 12px;
  color: var(--app-text-3);
}
/* 数字 */
.stat-card .num {
  font-size: 28px;
  font-weight: 700;
  line-height: 1.2;
  color: var(--app-text-1);
  font-variant-numeric: tabular-nums;
}
/* 脚注 */
.stat-card .foot {
  font-size: 12px;
  color: var(--app-text-3);
}
/* 未确认：警示色 */
.stat-card.warn .num {
  color: var(--chart-4);
}
/* 已确认：成功色 */
.stat-card.ok .num {
  color: var(--chart-1);
}
/* 严重：危险色 */
.stat-card.level-3 .num {
  color: var(--chart-5);
}
/* 表格卡片 */
.table-card {
  border-radius: var(--app-radius-lg);
}
/* 分页 */
.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: var(--app-space-4);
}
/* 记录筛选 */
.record-filter {
  margin-bottom: var(--app-space-2);
}
/* 视觉表现色点 */
.effect-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  margin-right: 6px;
  border-radius: 50%;
  vertical-align: middle;
}
/* 已处理占位文字 */
.muted {
  color: var(--app-text-3);
  font-size: 12px;
}
/* 窄屏时统计改为两列 */
@media (max-width: 1100px) {
  .stat-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
