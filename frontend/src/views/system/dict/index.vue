<template>
  <div class="app-container">
    <div class="page-header">
      <div class="page-title-wrap">
        <h2>字典管理</h2>
        <div class="sub">字典类型与字典项维护</div>
      </div>
    </div>
    <el-row :gutter="14">
      <!-- 左侧：字典类型 -->
      <el-col :span="10">
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span>字典类型</span>
              <div>
                <el-button v-perm="'system:dict:create'" type="primary" size="small" :icon="Plus" @click="openTypeCreate">新增类型</el-button>
              </div>
            </div>
          </template>

          <el-form inline @submit.prevent>
            <el-form-item label="名称">
              <el-input v-model="typeQuery.dict_name" placeholder="字典名称" clearable style="width: 120px" @keyup.enter="searchTypes" />
            </el-form-item>
            <el-form-item label="类型">
              <el-input v-model="typeQuery.dict_type" placeholder="类型编码" clearable style="width: 120px" @keyup.enter="searchTypes" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :icon="Search" @click="searchTypes">查询</el-button>
            </el-form-item>
          </el-form>

          <el-table
            v-loading="typeLoading"
            :data="typeList"
            highlight-current-row
            :row-class-name="typeRowClass"
            @row-click="selectType"
          >
            <el-table-column label="字典名称" prop="dict_name" min-width="100" show-overflow-tooltip />
            <el-table-column label="类型编码" prop="dict_type" min-width="110" show-overflow-tooltip />
            <el-table-column label="状态" width="70" align="center">
              <template #default="{ row }">
                <el-tag :type="row.status === 0 ? 'success' : 'danger'" size="small">
                  {{ row.status === 0 ? '正常' : '停用' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="140" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" @click.stop="selectType(row)">字典项</el-button>
                <el-button v-perm="'system:dict:update'" link type="primary" @click.stop="openTypeEdit(row)">编辑</el-button>
                <el-button v-perm="'system:dict:delete'" link type="danger" @click.stop="handleTypeDelete(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>

          <div class="pagination-wrap">
            <el-pagination
              v-model:current-page="typePage"
              v-model:page-size="typePageSize"
              :total="typeTotal"
              :page-sizes="[10, 20, 50]"
              layout="total, prev, pager, next"
              @size-change="typePage = 1; fetchTypes()"
              @current-change="fetchTypes"
            />
          </div>
        </el-card>
      </el-col>

      <!-- 右侧：字典数据 -->
      <el-col :span="14">
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span>字典数据{{ currentType ? `（${currentType.dict_name} / ${currentType.dict_type}）` : '' }}</span>
              <div>
                <el-button
                  v-perm="'system:dict:create'"
                  type="primary"
                  size="small"
                  :icon="Plus"
                  :disabled="!currentType"
                  @click="openDataCreate"
                >新增字典项</el-button>
              </div>
            </div>
          </template>

          <el-empty v-if="!currentType" description="请先在左侧选择字典类型" :image-size="80" />
          <template v-else>
            <el-table stripe empty-text="暂无数据" v-loading="dataLoading" :data="dataList">
              <el-table-column label="标签" prop="dict_label" min-width="110" show-overflow-tooltip />
              <el-table-column label="键值" prop="dict_value" min-width="90" show-overflow-tooltip />
              <el-table-column label="排序" prop="dict_sort" width="70" align="center" />
              <el-table-column label="状态" width="80" align="center">
                <template #default="{ row }">
                  <el-tag :type="row.status === 0 ? 'success' : 'danger'" size="small">
                    {{ row.status === 0 ? '正常' : '停用' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="备注" prop="remark" min-width="110" show-overflow-tooltip>
                <template #default="{ row }">{{ row.remark || '-' }}</template>
              </el-table-column>
              <el-table-column label="操作" width="120" fixed="right">
                <template #default="{ row }">
                  <el-button v-perm="'system:dict:update'" link type="primary" @click="openDataEdit(row)">编辑</el-button>
                  <el-button v-perm="'system:dict:delete'" link type="danger" @click="handleDataDelete(row)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>

            <div class="pagination-wrap">
              <el-pagination
                v-model:current-page="dataPage"
                v-model:page-size="dataPageSize"
                :total="dataTotal"
                :page-sizes="[10, 20, 50]"
                layout="total, prev, pager, next"
                @size-change="dataPage = 1; fetchData()"
                @current-change="fetchData"
              />
            </div>
          </template>
        </el-card>
      </el-col>
    </el-row>

    <!-- 字典类型弹窗 -->
    <el-dialog v-model="typeVisible" :title="typeForm.id ? '编辑字典类型' : '新增字典类型'" width="480px" destroy-on-close>
      <el-form ref="typeFormRef" :model="typeForm" :rules="typeRules" label-width="90px">
        <el-form-item label="字典名称" prop="dict_name">
          <el-input v-model.trim="typeForm.dict_name" placeholder="如 用户性别" maxlength="50" />
        </el-form-item>
        <el-form-item label="类型编码" prop="dict_type">
          <el-input v-model.trim="typeForm.dict_type" placeholder="如 sys_user_sex" :disabled="!!typeForm.id" maxlength="50" />
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <el-radio-group v-model="typeForm.status">
            <el-radio :value="0">正常</el-radio>
            <el-radio :value="1">停用</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="备注" prop="remark">
          <el-input v-model="typeForm.remark" type="textarea" :rows="3" maxlength="200" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="typeVisible = false">取 消</el-button>
        <el-button type="primary" :loading="saving" @click="handleTypeSave">确 定</el-button>
      </template>
    </el-dialog>

    <!-- 字典数据弹窗 -->
    <el-dialog v-model="dataVisible" :title="dataForm.id ? '编辑字典项' : '新增字典项'" width="480px" destroy-on-close>
      <el-form ref="dataFormRef" :model="dataForm" :rules="dataRules" label-width="90px">
        <el-form-item label="字典类型">
          <el-input :model-value="currentType ? currentType.dict_type : ''" disabled />
        </el-form-item>
        <el-form-item label="数据标签" prop="dict_label">
          <el-input v-model.trim="dataForm.dict_label" placeholder="如 男" maxlength="50" />
        </el-form-item>
        <el-form-item label="数据键值" prop="dict_value">
          <el-input v-model.trim="dataForm.dict_value" placeholder="如 1" maxlength="50" />
        </el-form-item>
        <el-form-item label="显示排序" prop="dict_sort">
          <el-input-number v-model="dataForm.dict_sort" :min="0" :max="999" controls-position="right" />
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <el-radio-group v-model="dataForm.status">
            <el-radio :value="0">正常</el-radio>
            <el-radio :value="1">停用</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="备注" prop="remark">
          <el-input v-model="dataForm.remark" type="textarea" :rows="3" maxlength="200" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dataVisible = false">取 消</el-button>
        <el-button type="primary" :loading="saving" @click="handleDataSave">确 定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, Refresh } from '@element-plus/icons-vue'
import request from '@/utils/request'

const saving = ref(false)

// ---------- 字典类型 ----------
const typeLoading = ref(false)
const typeList = ref([])
const typeTotal = ref(0)
const typePage = ref(1)
const typePageSize = ref(10)
const typeQuery = reactive({ dict_name: '', dict_type: '' })
const currentType = ref(null)

async function fetchTypes() {
  typeLoading.value = true
  try {
    const res = await request.get('/system/dict/type/list', {
      params: { page: typePage.value, page_size: typePageSize.value, ...typeQuery }
    })
    typeList.value = res.data.list || []
    typeTotal.value = res.data.total || 0
    // 当前选中类型可能已被删除
    if (currentType.value && !typeList.value.some(t => t.id === currentType.value.id)) {
      clearCurrentType()
    }
  } finally {
    typeLoading.value = false
  }
}

function searchTypes() {
  typePage.value = 1
  fetchTypes()
}

function typeRowClass({ row }) {
  return currentType.value && currentType.value.id === row.id ? 'current-type-row' : ''
}

function selectType(row) {
  currentType.value = row
  dataPage.value = 1
  fetchData()
}

function clearCurrentType() {
  currentType.value = null
  dataList.value = []
  dataTotal.value = 0
}

// 类型新增/编辑
const typeVisible = ref(false)
const typeFormRef = ref()
const typeForm = reactive({ id: null, dict_name: '', dict_type: '', status: 0, remark: '' })
const typeRules = {
  dict_name: [{ required: true, message: '请输入字典名称', trigger: 'blur' }],
  dict_type: [{ required: true, message: '请输入类型编码', trigger: 'blur' }]
}

function openTypeCreate() {
  typeForm.id = null
  typeForm.dict_name = ''
  typeForm.dict_type = ''
  typeForm.status = 0
  typeForm.remark = ''
  typeVisible.value = true
}

function openTypeEdit(row) {
  typeForm.id = row.id
  typeForm.dict_name = row.dict_name
  typeForm.dict_type = row.dict_type
  typeForm.status = row.status
  typeForm.remark = row.remark || ''
  typeVisible.value = true
}

async function handleTypeSave() {
  await typeFormRef.value.validate()
  saving.value = true
  try {
    const payload = {
      dict_name: typeForm.dict_name,
      dict_type: typeForm.dict_type,
      status: typeForm.status,
      remark: typeForm.remark
    }
    if (typeForm.id) {
      await request.put(`/system/dict/type/update/${typeForm.id}`, payload)
      ElMessage.success('修改成功')
    } else {
      await request.post('/system/dict/type/create', payload)
      ElMessage.success('新增成功')
    }
    typeVisible.value = false
    fetchTypes()
  } finally {
    saving.value = false
  }
}

async function handleTypeDelete(row) {
  await ElMessageBox.confirm(`确定删除字典类型「${row.dict_name}」吗？其下字典项将不可用。`, '提示', { type: 'warning' })
  await request.delete('/system/dict/type/delete', { data: { ids: [row.id] } })
  ElMessage.success('删除成功')
  if (currentType.value && currentType.value.id === row.id) clearCurrentType()
  fetchTypes()
}

// ---------- 字典数据 ----------
const dataLoading = ref(false)
const dataList = ref([])
const dataTotal = ref(0)
const dataPage = ref(1)
const dataPageSize = ref(10)

async function fetchData() {
  if (!currentType.value) return
  dataLoading.value = true
  try {
    const res = await request.get('/system/dict/data/list', {
      params: { page: dataPage.value, page_size: dataPageSize.value, dict_type: currentType.value.dict_type }
    })
    dataList.value = res.data.list || []
    dataTotal.value = res.data.total || 0
  } finally {
    dataLoading.value = false
  }
}

const dataVisible = ref(false)
const dataFormRef = ref()
const dataForm = reactive({
  id: null,
  dict_type_id: null,
  dict_label: '',
  dict_value: '',
  dict_sort: 0,
  status: 0,
  remark: ''
})
const dataRules = {
  dict_label: [{ required: true, message: '请输入数据标签', trigger: 'blur' }],
  dict_value: [{ required: true, message: '请输入数据键值', trigger: 'blur' }]
}

function openDataCreate() {
  dataForm.id = null
  dataForm.dict_type_id = currentType.value.id
  dataForm.dict_label = ''
  dataForm.dict_value = ''
  dataForm.dict_sort = 0
  dataForm.status = 0
  dataForm.remark = ''
  dataVisible.value = true
}

function openDataEdit(row) {
  dataForm.id = row.id
  dataForm.dict_type_id = row.dict_type_id ?? currentType.value.id
  dataForm.dict_label = row.dict_label
  dataForm.dict_value = row.dict_value
  dataForm.dict_sort = row.dict_sort
  dataForm.status = row.status
  dataForm.remark = row.remark || ''
  dataVisible.value = true
}

async function handleDataSave() {
  await dataFormRef.value.validate()
  saving.value = true
  try {
    const payload = {
      dict_type_id: dataForm.dict_type_id,
      dict_label: dataForm.dict_label,
      dict_value: dataForm.dict_value,
      dict_sort: dataForm.dict_sort,
      status: dataForm.status,
      remark: dataForm.remark
    }
    if (dataForm.id) {
      await request.put(`/system/dict/data/update/${dataForm.id}`, payload)
      ElMessage.success('修改成功')
    } else {
      await request.post('/system/dict/data/create', payload)
      ElMessage.success('新增成功')
    }
    dataVisible.value = false
    fetchData()
  } finally {
    saving.value = false
  }
}

async function handleDataDelete(row) {
  await ElMessageBox.confirm(`确定删除字典项「${row.dict_label}」吗？`, '提示', { type: 'warning' })
  await request.delete('/system/dict/data/delete', { data: { ids: [row.id] } })
  ElMessage.success('删除成功')
  fetchData()
}

onMounted(fetchTypes)
</script>

<style scoped>
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

:deep(.current-type-row) {
  background-color: #ecf5ff;
}
</style>
