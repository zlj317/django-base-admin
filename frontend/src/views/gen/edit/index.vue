<template>
  <div class="app-container">
    <!-- 生成信息 -->
    <el-card shadow="never" header="生成信息" class="mb14">
      <div v-loading="loading">
        <el-form ref="tableFormRef" :model="table" :rules="tableRules" label-width="110px">
          <el-row :gutter="16">
            <el-col :span="8">
              <el-form-item label="表名">
                <el-input :model-value="table.table_name" disabled />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="表注释">
                <el-input :model-value="table.table_comment" disabled />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="类名" prop="class_name">
                <el-input v-model.trim="table.class_name" placeholder="如 BizOrder" maxlength="50" />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="模块中文" prop="module_comment">
                <el-input v-model.trim="table.module_comment" placeholder="如 订单管理" maxlength="50" />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="模块标识" prop="module_name">
                <el-input v-model.trim="table.module_name" placeholder="如 biz_order" maxlength="50" />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="路由前缀" prop="url_prefix">
                <el-input v-model.trim="table.url_prefix" placeholder="如 /api/biz/order" maxlength="100" />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="前端页面路径" prop="gen_path">
                <el-input v-model.trim="table.gen_path" placeholder="如 views/biz/order" maxlength="100" />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="父级菜单" prop="parent_menu_id">
                <el-tree-select
                  v-model="table.parent_menu_id"
                  :data="menuTree"
                  :props="{ label: 'menu_name', children: 'children' }"
                  node-key="id"
                  check-strictly
                  clearable
                  filterable
                  default-expand-all
                  placeholder="生成菜单的上级位置"
                  style="width: 100%"
                />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="生成选项">
                <div class="switch-group">
                  <el-checkbox v-model="table.is_delete_logic" :true-value="1" :false-value="0">逻辑删除</el-checkbox>
                  <el-checkbox v-model="table.import_enable" :true-value="1" :false-value="0">导入</el-checkbox>
                  <el-checkbox v-model="table.export_enable" :true-value="1" :false-value="0">导出</el-checkbox>
                </div>
              </el-form-item>
            </el-col>
          </el-row>
        </el-form>
      </div>
    </el-card>

    <!-- 字段配置 -->
    <el-card shadow="never" header="字段配置">
      <el-table :data="columns" v-loading="loading" border row-key="id" max-height="520">
        <el-table-column label="序号" type="index" width="55" align="center" />
        <el-table-column label="字段名" prop="column_name" min-width="140" show-overflow-tooltip>
          <template #default="{ row }">
            <span>{{ row.column_name }}</span>
            <el-tag v-if="row.is_pk" type="danger" size="small" class="ml4">主键</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="字段注释" min-width="160">
          <template #default="{ row }">
            <el-input v-model="row.column_comment" placeholder="字段注释" maxlength="100" />
          </template>
        </el-table-column>
        <el-table-column label="字段类型" prop="column_type" min-width="130" show-overflow-tooltip />
        <el-table-column label="表单类型" min-width="130">
          <template #default="{ row }">
            <el-select v-model="row.form_type" placeholder="表单类型">
              <el-option v-for="t in formTypeOptions" :key="t.value" :label="t.label" :value="t.value" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="字典类型" min-width="150">
          <template #default="{ row }">
            <el-select v-model="row.dict_type" clearable filterable placeholder="关联字典">
              <el-option v-for="d in dictTypeOptions" :key="d" :label="d" :value="d" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="列表" width="65" align="center">
          <template #default="{ row }">
            <el-switch v-model="row.is_list" :active-value="1" :inactive-value="0" />
          </template>
        </el-table-column>
        <el-table-column label="查询" width="65" align="center">
          <template #default="{ row }">
            <el-switch v-model="row.is_query" :active-value="1" :inactive-value="0" />
          </template>
        </el-table-column>
        <el-table-column label="查询方式" min-width="110">
          <template #default="{ row }">
            <el-select v-model="row.query_type" :disabled="row.is_query !== 1" placeholder="查询方式">
              <el-option v-for="t in queryTypeOptions" :key="t.value" :label="t.label" :value="t.value" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="必填" width="65" align="center">
          <template #default="{ row }">
            <el-switch v-model="row.is_required" :active-value="1" :inactive-value="0" />
          </template>
        </el-table-column>
        <el-table-column label="导出" width="65" align="center">
          <template #default="{ row }">
            <el-switch v-model="row.is_export" :active-value="1" :inactive-value="0" />
          </template>
        </el-table-column>
        <el-table-column label="导入" width="65" align="center">
          <template #default="{ row }">
            <el-switch v-model="row.is_import" :active-value="1" :inactive-value="0" />
          </template>
        </el-table-column>
        <el-table-column label="排序" width="110" align="center">
          <template #default="{ row }">
            <el-input-number v-model="row.sort" :min="0" :max="999" controls-position="right" style="width: 90px" />
          </template>
        </el-table-column>
      </el-table>

      <div class="actions">
        <el-button v-perm="'gen:table:update'" type="primary" :icon="Check" :loading="saving" @click="handleSave">保存配置</el-button>
        <el-button v-perm="'gen:table:preview'" :icon="View" @click="previewRef.open(tableId)">预览代码</el-button>
        <el-button v-perm="'gen:table:preview'" :icon="Document" @click="showDdl">查看建表SQL</el-button>
        <el-button v-perm="'gen:table:download'" type="success" :icon="Download" @click="handleDownload">下载代码</el-button>
        <el-button :icon="Back" @click="router.back()">返 回</el-button>
      </div>
    </el-card>

    <!-- 代码预览弹窗 -->
    <CodePreviewDialog ref="previewRef" />

    <!-- 建表 SQL 弹窗 -->
    <el-dialog v-model="ddlVisible" title="建表 SQL" width="760px" top="8vh" destroy-on-close>
      <el-scrollbar max-height="60vh">
        <pre class="code-block">{{ ddlText }}</pre>
      </el-scrollbar>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Check, View, Document, Download, Back } from '@element-plus/icons-vue'
import request from '@/utils/request'
import { saveBlob } from '@/utils/download'
import CodePreviewDialog from '@/components/CodePreviewDialog.vue'

const route = useRoute()
const router = useRouter()
const tableId = route.params.id

const loading = ref(false)
const saving = ref(false)
const tableFormRef = ref()
const previewRef = ref()

const table = reactive({
  id: null,
  table_name: '',
  table_comment: '',
  class_name: '',
  module_name: '',
  module_comment: '',
  url_prefix: '',
  gen_path: '',
  parent_menu_id: null,
  is_delete_logic: 0,
  import_enable: 0,
  export_enable: 0
})

const columns = ref([])
const menuTree = ref([])
const dictTypeOptions = ref([])

const tableRules = {
  class_name: [{ required: true, message: '请输入类名', trigger: 'blur' }],
  module_name: [{ required: true, message: '请输入模块标识', trigger: 'blur' }],
  module_comment: [{ required: true, message: '请输入模块中文名', trigger: 'blur' }],
  url_prefix: [{ required: true, message: '请输入路由前缀', trigger: 'blur' }]
}

const formTypeOptions = [
  { value: 'input', label: '文本框' },
  { value: 'number', label: '数字' },
  { value: 'date', label: '日期' },
  { value: 'select', label: '下拉框' },
  { value: 'radio', label: '单选' },
  { value: 'textarea', label: '文本域' },
  { value: 'image', label: '图片上传' },
  { value: 'file', label: '文件上传' }
]

const queryTypeOptions = [
  { value: 'eq', label: '等于' },
  { value: 'like', label: '模糊' },
  { value: 'gt', label: '大于' },
  { value: 'lt', label: '小于' },
  { value: 'between', label: '范围' }
]

// 统一将后端返回的开关字段转为 0/1
function to01(v) {
  return Number(v) ? 1 : 0
}

// ---------- 数据加载 ----------
async function load() {
  loading.value = true
  try {
    const res = await request.get(`/gen/table/${tableId}`)
    const detail = res.data || {}
    const t = detail.table || {}
    Object.assign(table, {
      id: t.id,
      table_name: t.table_name,
      table_comment: t.table_comment,
      class_name: t.class_name,
      module_name: t.module_name,
      module_comment: t.module_comment,
      url_prefix: t.url_prefix,
      gen_path: t.gen_path,
      parent_menu_id: t.parent_menu_id ?? null,
      is_delete_logic: to01(t.is_delete_logic),
      import_enable: to01(t.import_enable),
      export_enable: to01(t.export_enable)
    })
    columns.value = (detail.columns || []).map(col => ({
      ...col,
      dict_type: col.dict_type || '',
      form_type: col.form_type || 'input',
      query_type: col.query_type || 'eq',
      is_pk: to01(col.is_pk),
      is_list: to01(col.is_list),
      is_query: to01(col.is_query),
      is_required: to01(col.is_required),
      is_export: to01(col.is_export),
      is_import: to01(col.is_import),
      sort: col.sort ?? 0
    }))
  } finally {
    loading.value = false
  }
}

async function loadMenuTree() {
  const res = await request.get('/system/menu/tree')
  menuTree.value = res.data || []
}

async function loadDictTypes() {
  const res = await request.get('/system/dict/data/all')
  dictTypeOptions.value = (res.data || []).map(d => d.dict_type)
}

// ---------- 操作 ----------
async function handleSave() {
  await tableFormRef.value.validate()
  saving.value = true
  try {
    const tablePayload = {
      table_comment: table.table_comment,
      class_name: table.class_name,
      module_name: table.module_name,
      module_comment: table.module_comment,
      url_prefix: table.url_prefix,
      gen_path: table.gen_path,
      parent_menu_id: table.parent_menu_id,
      is_delete_logic: table.is_delete_logic,
      import_enable: table.import_enable,
      export_enable: table.export_enable
    }
    const columnPayload = columns.value.map(col => ({
      ...col,
      dict_type: col.dict_type || '',
      is_pk: to01(col.is_pk),
      is_list: to01(col.is_list),
      is_query: to01(col.is_query),
      is_required: to01(col.is_required),
      is_export: to01(col.is_export),
      is_import: to01(col.is_import),
      sort: col.sort ?? 0
    }))
    await request.put(`/gen/table/${tableId}`, { table: tablePayload, columns: columnPayload })
    ElMessage.success('保存成功')
    load()
  } finally {
    saving.value = false
  }
}

const ddlVisible = ref(false)
const ddlText = ref('')

async function showDdl() {
  const res = await request.get(`/gen/table/${tableId}/ddl`)
  ddlText.value = (res.data && res.data.ddl) || ''
  ddlVisible.value = true
}

async function handleDownload() {
  const res = await request.get(`/gen/table/${tableId}/download`, { responseType: 'blob', timeout: 120000 })
  saveBlob(res.data, `${table.module_name || table.table_name}.zip`)
  ElMessage.success('下载成功')
}

onMounted(() => {
  load()
  loadMenuTree()
  loadDictTypes()
})
</script>

<style scoped>
.mb14 {
  margin-bottom: 14px;
}

.switch-group {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.ml4 {
  margin-left: 4px;
}

.actions {
  display: flex;
  justify-content: center;
  gap: 6px;
  margin-top: 18px;
}
</style>
