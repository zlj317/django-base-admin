<!--
  文件级说明：
  职责：3D 场景管理页：场景卡片列表、新建、发布/下线、复制、分享、版本回滚、访问授权、访问记录。
  数据来源：/api/scene3d/list 与 /scene3d/:id/*（真实表 scene3d_scene 及关联对象/版本/授权/日志）。
  交互约定：编辑入口跳转 /scene3d/editor/:id（隐藏菜单路由），预览入口打开只读全屏页。
-->
<template>
  <div class="app-container scene3d-page">
    <!-- 页头 -->
    <div class="page-header">
      <div>
        <h2>3D 场景管理</h2>
        <div class="sub">场景资产 · 发布状态 · 版本与访问控制 · 共 {{ total }} 个</div>
      </div>
      <div class="head-actions">
        <el-button :icon="Refresh" @click="fetchList">刷新</el-button>
        <el-button v-perm="'scene3d:scene:create'" type="primary" :icon="Plus" @click="openCreate">新建场景</el-button>
      </div>
    </div>

    <!-- 筛选 -->
    <el-card shadow="never" class="search-card">
      <el-form inline @submit.prevent>
        <el-form-item label="场景名称">
          <el-input v-model="query.scene_name" placeholder="名称关键词" clearable style="width: 180px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="场景编码">
          <el-input v-model="query.scene_code" placeholder="编码关键词" clearable style="width: 170px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="query.category_id" placeholder="全部分类" clearable style="width: 160px">
            <el-option v-for="c in categories" :key="c.id" :label="c.category_name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="query.scene_status" placeholder="全部" clearable style="width: 120px">
            <el-option label="草稿" :value="0" />
            <el-option label="已发布" :value="1" />
            <el-option label="已下线" :value="2" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 场景卡片：grid 铺满，避免 flex 子项收缩导致宽度塌陷 -->
    <div v-loading="loading" class="scene-grid">
      <!-- 空态引导卡片 -->
      <div v-if="!loading && !rows.length" class="empty-card">
        <el-icon :size="34"><Monitor /></el-icon>
        <p>暂无 3D 场景</p>
        <el-button v-perm="'scene3d:scene:create'" type="primary" plain @click="openCreate">创建第一个场景</el-button>
      </div>
      <!-- 场景卡片 -->
      <div v-for="item in rows" :key="item.id" class="scene-card" :class="{ published: item.scene_status === 1 }">
        <!-- 缩略图：用主题令牌绘制的等距线框，避免外链图片 -->
        <div class="thumb" @click="openView(item)">
          <div class="iso">
            <span class="face f1"></span><span class="face f2"></span><span class="face f3"></span>
          </div>
          <div class="thumb-badge">
            <el-tag :type="statusTag(item.scene_status)" effect="dark" size="small">{{ statusText(item.scene_status) }}</el-tag>
          </div>
        </div>
        <!-- 卡片主体 -->
        <div class="body">
          <div class="name-row">
            <span class="name" :title="item.scene_name">{{ item.scene_name }}</span>
            <el-tag size="small" effect="plain" type="info">{{ item.category_name || '未分类' }}</el-tag>
          </div>
          <div class="meta">
            <span>编码 {{ item.scene_code }}</span>
            <span>更新 {{ (item.update_time || '').slice(0, 16) }}</span>
          </div>
          <!-- 操作区：权限逐个控制 -->
          <div class="ops">
            <el-button v-perm="'scene3d:scene:update'" size="small" type="primary" @click="goEditor(item)">编辑</el-button>
            <el-button size="small" @click="openView(item)">查看</el-button>
            <el-dropdown trigger="click" @command="cmd => handleCommand(cmd, item)">
              <el-button size="small">更多<el-icon class="el-icon--right"><ArrowDown /></el-icon></el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item v-if="item.scene_status !== 1" command="publish" :disabled="!can('scene3d:scene:publish')">发布</el-dropdown-item>
                  <el-dropdown-item v-if="item.scene_status === 1" command="offline" :disabled="!can('scene3d:scene:publish')">下线</el-dropdown-item>
                  <el-dropdown-item command="copy" :disabled="!can('scene3d:scene:create')">复制场景</el-dropdown-item>
                  <el-dropdown-item command="share" :disabled="!can('scene3d:scene:share')">生成分享</el-dropdown-item>
                  <el-dropdown-item command="version" :disabled="!can('scene3d:scene:version')">版本记录</el-dropdown-item>
                  <el-dropdown-item command="permission" :disabled="!can('scene3d:permission:list')">访问授权</el-dropdown-item>
                  <el-dropdown-item command="visit" :disabled="!can('scene3d:scene:list')">访问记录</el-dropdown-item>
                  <el-dropdown-item command="remove" divided :disabled="!can('scene3d:scene:delete')">删除</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>
      </div>
    </div>

    <!-- 分页 -->
    <div class="pagination-wrap">
      <el-pagination background layout="total, sizes, prev, pager, next, jumper" :total="total"
        v-model:current-page="query.page" v-model:page-size="query.page_size" :page-sizes="[9, 12, 24, 48]" @change="fetchList" />
    </div>

    <!-- 新建场景弹窗 -->
    <el-dialog v-model="createVisible" title="新建 3D 场景" width="560px" :close-on-click-modal="false" destroy-on-close>
      <el-form ref="createRef" :model="createForm" :rules="createRules" label-width="90px">
        <el-form-item label="场景名称" prop="scene_name">
          <el-input v-model="createForm.scene_name" placeholder="如：数据中心机房 DC-ROOM-01" maxlength="100" />
        </el-form-item>
        <el-form-item label="场景编码">
          <el-input v-model="createForm.scene_code" placeholder="留空自动生成 SC-YYYYMMDD-XXXX" maxlength="50" />
        </el-form-item>
        <el-form-item label="场景分类" prop="category_id">
          <el-select v-model="createForm.category_id" placeholder="请选择分类" style="width: 100%">
            <el-option v-for="c in categories" :key="c.id" :label="c.category_name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="来源模板">
          <el-select v-model="createForm.template_id" placeholder="可不选" clearable style="width: 100%">
            <el-option v-for="t in templates" :key="t.id" :label="t.template_name" :value="t.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="场景描述">
          <el-input v-model="createForm.remark" type="textarea" :rows="3" maxlength="1000" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitCreate">创建并进入编辑器</el-button>
      </template>
    </el-dialog>

    <!-- 分享弹窗 -->
    <el-dialog v-model="shareVisible" title="生成分享链接" width="520px" :close-on-click-modal="false">
      <el-form label-width="90px">
        <el-form-item label="有效期">
          <el-select v-model="shareDays" style="width: 160px">
            <el-option v-for="d in [1, 3, 7, 15, 30]" :key="d" :label="`${d} 天`" :value="d" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="shareResult" label="分享地址">
          <el-input :model-value="shareUrl(shareResult.share_url)" readonly>
            <template #append><el-button @click="copyLink">复制</el-button></template>
          </el-input>
          <div class="hint">到期时间：{{ shareResult.expire }}（免登录只读访问）</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="shareVisible = false">关闭</el-button>
        <el-button type="primary" :loading="saving" @click="submitShare">生成链接</el-button>
      </template>
    </el-dialog>

    <!-- 版本抽屉 -->
    <el-drawer v-model="versionVisible" title="版本记录" size="440px">
      <el-timeline v-if="versions.length" class="version-line">
        <el-timeline-item v-for="v in versions" :key="v.id" :timestamp="v.create_time" placement="top">
          <div class="version-item">
            <div class="version-title">
              <strong>{{ v.version_no }}</strong>
              <el-tag v-if="v.is_publish === 1" size="small" type="success">发布版本</el-tag>
            </div>
            <p class="version-desc">{{ v.version_desc || '无描述' }}</p>
            <p class="version-by">操作人：{{ v.create_by || '—' }}</p>
            <el-button v-perm="'scene3d:scene:version'" size="small" type="primary" plain @click="rollback(v)">回滚到此版本</el-button>
          </div>
        </el-timeline-item>
      </el-timeline>
      <el-empty v-else description="暂无版本记录" />
    </el-drawer>

    <!-- 访问授权抽屉 -->
    <el-drawer v-model="permissionVisible" title="访问授权" size="520px">
      <div class="perm-add">
        <el-select v-model="permForm.target_id" placeholder="选择角色" filterable style="flex: 1">
          <el-option v-for="r in roles" :key="r.id" :label="r.role_name" :value="r.id" />
        </el-select>
        <el-select v-model="permForm.permission_type" style="width: 120px">
          <el-option label="只读" :value="1" />
          <el-option label="可交互" :value="2" />
          <el-option label="可编辑" :value="3" />
        </el-select>
        <el-button v-perm="'scene3d:permission:create'" type="primary" :disabled="!permForm.target_id" @click="addPermission">授权</el-button>
      </div>
      <el-table :data="permissions" size="small" empty-text="暂无授权，默认由菜单权限控制">
        <el-table-column label="授权对象" min-width="140">
          <template #default="{ row }">{{ row.target_name || row.target_id }}（{{ row.target_type === 'role' ? '角色' : row.target_type === 'user' ? '用户' : '部门' }}）</template>
        </el-table-column>
        <el-table-column label="权限" width="100">
          <template #default="{ row }">{{ ['只读', '可交互', '可编辑'][row.permission_type - 1] || '未知' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="80">
          <template #default="{ row }">
            <el-button v-perm="'scene3d:permission:delete'" link type="danger" @click="removePermission(row)">移除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-drawer>

    <!-- 访问记录抽屉 -->
    <el-drawer v-model="visitVisible" title="访问记录" size="620px">
      <el-table v-loading="visitLoading" :data="visits" size="small" empty-text="暂无访问记录">
        <el-table-column label="访问人" prop="username" width="110" />
        <el-table-column label="方式" prop="access_type" width="100" />
        <el-table-column label="IP" prop="access_ip" width="130" />
        <el-table-column label="停留" width="80">
          <template #default="{ row }">{{ row.stay_seconds }}s</template>
        </el-table-column>
        <el-table-column label="访问时间" prop="access_time" width="160" />
      </el-table>
    </el-drawer>
  </div>
</template>

<script setup>
// Vue API
import { ref, reactive, onMounted } from 'vue'
// 路由：跳转编辑器/预览
import { useRouter } from 'vue-router'
// 提示与确认
import { ElMessage, ElMessageBox } from 'element-plus'
// 图标
import { Plus, Search, Refresh, Monitor, ArrowDown } from '@element-plus/icons-vue'
// 统一请求（角色下拉复用系统接口）
import request from '@/utils/request'
// 场景/分类/模板/授权接口
import { sceneApi, categoryApi, templateApi, permissionApi } from '@/api/scene3d'
// 权限判断工具（与 v-perm 指令同源，用于下拉项禁用）
import { hasPerm } from '@/store/auth'

// 路由实例
const router = useRouter()

// 列表状态
const loading = ref(false) // 加载态
const saving = ref(false) // 提交态
const rows = ref([]) // 场景数据
const total = ref(0) // 总数
const query = reactive({ page: 1, page_size: 9, scene_name: '', scene_code: '', category_id: '', scene_status: '' }) // 查询条件
const categories = ref([]) // 分类下拉
const templates = ref([]) // 模板下拉
const roles = ref([]) // 角色下拉

// 新建弹窗
const createVisible = ref(false) // 显隐
const createRef = ref(null) // 表单引用
const createForm = reactive({ scene_name: '', scene_code: '', category_id: '', template_id: '', remark: '' }) // 表单
const createRules = {
  scene_name: [{ required: true, message: '请输入场景名称', trigger: 'blur' }],
  category_id: [{ required: true, message: '请选择场景分类', trigger: 'change' }]
}

// 分享
const shareVisible = ref(false) // 显隐
const shareDays = ref(7) // 有效天数
const shareResult = ref(null) // 生成结果
const shareSceneId = ref(null) // 当前场景

// 版本
const versionVisible = ref(false) // 显隐
const versions = ref([]) // 版本列表
const versionSceneId = ref(null) // 当前场景

// 授权
const permissionVisible = ref(false) // 显隐
const permissions = ref([]) // 授权列表
const permissionSceneId = ref(null) // 当前场景
const permForm = reactive({ target_id: '', permission_type: 1 }) // 授权表单

// 访问记录
const visitVisible = ref(false) // 显隐
const visitLoading = ref(false) // 加载态
const visits = ref([]) // 记录

// 状态文案与标签
const statusText = s => ({ 0: '草稿', 1: '已发布', 2: '已下线' }[s] || '未知') // 文案
const statusTag = s => ({ 0: 'info', 1: 'success', 2: 'warning' }[s] || 'info') // 标签色

// 权限判断：与 v-perm 指令一致
const can = perm => hasPerm(perm)

// 拉场景列表
async function fetchList() {
  loading.value = true // 开启
  try {
    const res = await sceneApi.list({ ...query }) // 请求
    rows.value = res.data.list || [] // 数据
    total.value = res.data.total || 0 // 总数
  } finally {
    loading.value = false // 关闭
  }
}

// 查询
function handleSearch() {
  query.page = 1 // 回第一页
  fetchList() // 请求
}

// 重置
function handleReset() {
  Object.assign(query, { page: 1, page_size: 9, scene_name: '', scene_code: '', category_id: '', scene_status: '' }) // 恢复
  fetchList() // 请求
}

// 拉下拉选项
async function fetchOptions() {
  const [c, t, r] = await Promise.all([
    categoryApi.list({ page: 1, page_size: 100 }), // 分类
    templateApi.list({ page: 1, page_size: 100 }), // 模板
    request.get('/system/role/list', { params: { page: 1, page_size: 100 } }) // 角色（复用系统接口）
  ])
  categories.value = c.data.list || [] // 分类
  templates.value = t.data.list || [] // 模板
  roles.value = r.data.list || [] // 角色
}

// 打开新建
function openCreate() {
  Object.assign(createForm, { scene_name: '', scene_code: '', category_id: categories.value[0] ? categories.value[0].id : '', template_id: '', remark: '' }) // 重置
  createVisible.value = true // 打开
}

// 提交新建：成功后直接进入编辑器
async function submitCreate() {
  const valid = await createRef.value.validate().catch(() => false) // 校验
  if (!valid) return // 中断
  saving.value = true // 防重复
  try {
    const res = await sceneApi.create({
      scene_name: createForm.scene_name, scene_code: createForm.scene_code || `SC-${Date.now()}`, // 编码留空时用时间戳兜底，后端仍会校验唯一
      category_id: createForm.category_id, template_id: createForm.template_id || null, // 模板可空
      scene_status: 0, scene_config: {}, remark: createForm.remark // 新场景为草稿
    })
    ElMessage.success('创建成功，正在进入编辑器') // 提示
    createVisible.value = false // 关闭
    router.push(`/scene3d/editor/${res.data.id}`) // 跳转编辑器
  } finally {
    saving.value = false // 释放
  }
}

// 进入编辑器
function goEditor(item) {
  router.push(`/scene3d/editor/${item.id}`) // 隐藏菜单路由
}

// 打开只读查看页
function openView(item) {
  window.open(`/scene3d/view/${item.id}`, '_blank') // 新窗口全屏查看，避免占后台布局
}

// 下拉命令分发
async function handleCommand(cmd, item) {
  if (cmd === 'publish') return publish(item) // 发布
  if (cmd === 'offline') return offline(item) // 下线
  if (cmd === 'copy') return copyScene(item) // 复制
  if (cmd === 'share') return openShare(item) // 分享
  if (cmd === 'version') return openVersions(item) // 版本
  if (cmd === 'permission') return openPermissions(item) // 授权
  if (cmd === 'visit') return openVisits(item) // 访问记录
  if (cmd === 'remove') return removeScene(item) // 删除
}

// 发布
async function publish(item) {
  await ElMessageBox.confirm(`确认发布场景「${item.scene_name}」？发布后分享页与只读页可访问。`, '发布确认', { type: 'warning' }) // 二次确认
  await sceneApi.publish(item.id) // 调用发布
  ElMessage.success('发布成功') // 提示
  fetchList() // 刷新
}

// 下线
async function offline(item) {
  await ElMessageBox.confirm(`确认下线场景「${item.scene_name}」？下线后分享链接失效。`, '下线确认', { type: 'warning' }) // 二次确认
  await sceneApi.offline(item.id) // 调用下线
  ElMessage.success('已下线') // 提示
  fetchList() // 刷新
}

// 复制
async function copyScene(item) {
  await sceneApi.copy(item.id) // 后端复制对象/绑定/规则
  ElMessage.success('复制成功，已生成草稿副本') // 提示
  fetchList() // 刷新
}

// 打开分享
function openShare(item) {
  shareSceneId.value = item.id // 记录场景
  shareDays.value = 7 // 默认有效期
  shareResult.value = null // 清空上一次
  shareVisible.value = true // 打开
}

// 生成分享链接
async function submitShare() {
  if (!shareSceneId.value) return // 防御
  saving.value = true // 防重复
  try {
    const res = await sceneApi.share(shareSceneId.value, shareDays.value) // 请求
    shareResult.value = res.data // 保存结果
    ElMessage.success('分享链接已生成') // 提示
  } finally {
    saving.value = false // 释放
  }
}

// 分享完整地址
function shareUrl(path) {
  return path && path.startsWith('http') ? path : `${window.location.origin}${path || ''}` // 拼当前域名
}

// 复制链接
async function copyLink() {
  const text = shareUrl(shareResult.value && shareResult.value.share_url) // 完整地址
  try {
    await navigator.clipboard.writeText(text) // 现代浏览器剪贴板
  } catch {
    const input = document.createElement('textarea') // 兜底方案：临时文本框
    input.value = text
    document.body.appendChild(input)
    input.select()
    document.execCommand('copy')
    input.remove()
  }
  ElMessage.success('已复制') // 提示
}

// 打开版本抽屉
async function openVersions(item) {
  versionSceneId.value = item.id // 记录场景
  const res = await sceneApi.versions(item.id) // 请求版本
  versions.value = (res.data && res.data.list) || [] // 列表
  versionVisible.value = true // 打开
}

// 回滚
async function rollback(v) {
  await ElMessageBox.confirm(`确认回滚到 ${v.version_no}？当前配置会先保存为新版本。`, '回滚确认', { type: 'warning' }) // 二次确认
  await sceneApi.rollback(versionSceneId.value, v.id) // 回滚
  ElMessage.success('回滚成功') // 提示
  const res = await sceneApi.versions(versionSceneId.value) // 刷新版本列表
  versions.value = (res.data && res.data.list) || [] // 更新
  fetchList() // 刷新场景
}

// 打开授权抽屉
async function openPermissions(item) {
  permissionSceneId.value = item.id // 记录场景
  permForm.target_id = '' // 清空表单
  permForm.permission_type = 1 // 默认只读
  const res = await permissionApi.list({ scene_id: item.id, page: 1, page_size: 100 }) // 请求授权
  permissions.value = res.data.list || [] // 列表
  permissionVisible.value = true // 打开
}

// 新增授权
async function addPermission() {
  if (!permForm.target_id) return // 防御
  await permissionApi.create({ scene_id: permissionSceneId.value, target_type: 'role', target_id: permForm.target_id, permission_type: permForm.permission_type }) // 授权
  ElMessage.success('授权成功') // 提示
  const res = await permissionApi.list({ scene_id: permissionSceneId.value, page: 1, page_size: 100 }) // 刷新
  permissions.value = res.data.list || [] // 更新
}

// 移除授权
async function removePermission(row) {
  await permissionApi.remove([row.id]) // 逻辑删除
  ElMessage.success('已移除') // 提示
  const res = await permissionApi.list({ scene_id: permissionSceneId.value, page: 1, page_size: 100 }) // 刷新
  permissions.value = res.data.list || [] // 更新
}

// 打开访问记录
async function openVisits(item) {
  visitVisible.value = true // 先打开抽屉
  visitLoading.value = true // 开启加载
  try {
    const res = await sceneApi.visitLogs(item.id, { page: 1, page_size: 100 }) // 请求
    visits.value = res.data.list || [] // 列表
  } finally {
    visitLoading.value = false // 关闭
  }
}

// 删除场景
async function removeScene(item) {
  await ElMessageBox.confirm(`确认删除场景「${item.scene_name}」？对象、绑定与规则将一并逻辑删除。`, '删除确认', { type: 'warning' }) // 二次确认
  await sceneApi.remove([item.id]) // 逻辑删除
  ElMessage.success('删除成功') // 提示
  fetchList() // 刷新
}

// 首次加载
onMounted(async () => {
  await fetchOptions() // 下拉选项
  fetchList() // 场景列表
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
.head-actions {
  display: flex;
  gap: 8px;
}
/* 搜索卡片 */
.search-card {
  margin-bottom: var(--app-space-4);
  border-radius: var(--app-radius-lg);
}
/* 卡片栅格：minmax(0,1fr) 防止内容撑破，卡片宽度自然铺满 */
.scene-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: var(--app-space-4);
  min-height: 160px;
}
/* 卡片：flex 纵向排列，宽度 100% 避免被父级收缩 */
.scene-card {
  display: flex;
  flex-direction: column;
  width: 100%;
  min-width: 0;
  overflow: hidden;
  border: 1px solid var(--app-border-light);
  border-radius: var(--app-radius-lg);
  background: var(--app-surface);
  transition: box-shadow 0.2s, transform 0.2s;
}
/* 悬浮反馈 */
.scene-card:hover {
  box-shadow: var(--app-shadow-md);
  transform: translateY(-2px);
}
/* 已发布场景：顶部品牌色描边 */
.scene-card.published {
  border-color: color-mix(in srgb, var(--brand-primary) 42%, var(--app-border-light));
}
/* 缩略图区域 */
.thumb {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  height: 150px;
  background: linear-gradient(135deg, color-mix(in srgb, var(--brand-primary) 14%, var(--app-surface-2)), var(--app-surface-2));
  cursor: pointer;
}
/* 等距线框：三个菱形组成立方体示意 */
.iso {
  position: relative;
  width: 74px;
  height: 74px;
}
.iso .face {
  position: absolute;
  width: 44px;
  height: 44px;
  background: color-mix(in srgb, var(--brand-primary) 26%, transparent);
  border: 1px solid color-mix(in srgb, var(--brand-primary) 52%, transparent);
  transform: rotate(45deg) skew(-8deg, -8deg);
}
.iso .f1 {
  top: 0;
  left: 15px;
}
.iso .f2 {
  top: 26px;
  left: 0;
  background: color-mix(in srgb, var(--brand-primary) 16%, transparent);
}
.iso .f3 {
  top: 26px;
  left: 30px;
  background: color-mix(in srgb, var(--brand-primary) 34%, transparent);
}
/* 状态角标 */
.thumb-badge {
  position: absolute;
  top: 10px;
  right: 10px;
}
/* 卡片主体 */
.body {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: var(--app-space-4);
  min-width: 0;
}
/* 名称行：超长省略 */
.name-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  min-width: 0;
}
.name {
  overflow: hidden;
  color: var(--app-text-1);
  font-size: 15px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}
/* 元信息 */
.meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 14px;
  color: var(--app-text-3);
  font-size: 12px;
}
/* 操作区 */
.ops {
  display: flex;
  gap: 6px;
  margin-top: 2px;
}
/* 空态卡片：跨满所有列 */
.empty-card {
  grid-column: 1 / -1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 280px;
  border: 1px dashed var(--app-border);
  border-radius: var(--app-radius-lg);
  color: var(--app-text-3);
  background: var(--app-surface-2);
}
.empty-card p {
  margin: 0;
  font-size: 13px;
}
/* 分页 */
.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: var(--app-space-4);
}
/* 分享提示 */
.hint {
  margin-top: 4px;
  color: var(--app-text-3);
  font-size: 12px;
}
/* 版本时间线 */
.version-line {
  padding-left: 6px;
}
.version-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.version-title {
  display: flex;
  align-items: center;
  gap: 8px;
}
.version-desc {
  margin: 0;
  color: var(--app-text-2);
  font-size: 13px;
}
.version-by {
  margin: 0;
  color: var(--app-text-3);
  font-size: 12px;
}
/* 授权新增行 */
.perm-add {
  display: flex;
  gap: 8px;
  margin-bottom: var(--app-space-4);
}
</style>
