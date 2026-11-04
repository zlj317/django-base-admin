<template>
  <div class="app-container">
    <div class="page-header">
      <div class="page-title-wrap">
        <h2>生成记录</h2>
        <div class="sub">只读 · 共 {{ total }} 条</div>
      </div>
    </div>
    <el-card shadow="never" class="search-card">
      <el-form :model="query" inline @submit.prevent>
        <el-form-item label="模板名称">
          <el-input v-model="query.template_name" placeholder="请输入模板名称" clearable style="width: 180px" @keyup.enter="handleSearch" />
        </el-form-item>
        <el-form-item label="生成状态">
          <el-select v-model="query.gen_status" placeholder="全部" clearable style="width: 130px">
            <el-option label="生成中" :value="0" />
            <el-option label="成功" :value="1" />
            <el-option label="失败" :value="2" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="handleSearch">查询</el-button>
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="never" class="table-card">
      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据">
        <el-table-column label="记录ID" prop="id" width="80" />
        <el-table-column label="模板ID" prop="template_id" width="90" />
        <el-table-column label="模板名称" prop="template_name" min-width="160" show-overflow-tooltip />
        <el-table-column label="生成类型" prop="gen_type" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.gen_type==='manual'" size="small">手动</el-tag>
            <el-tag v-else-if="row.gen_type==='schedule'" size="small" type="warning">定时</el-tag>
            <span v-else>{{ row.gen_type }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.gen_status===0" size="small" type="warning">生成中</el-tag>
            <el-tag v-else-if="row.gen_status===1" size="small" type="success">成功</el-tag>
            <el-tag v-else-if="row.gen_status===2" size="small" type="danger">失败</el-tag>
            <span v-else>{{ row.gen_status }}</span>
          </template>
        </el-table-column>
        <el-table-column label="文件ID" prop="file_id" min-width="140" show-overflow-tooltip>
          <template #default="{ row }">{{ row.file_id || '-' }}</template>
        </el-table-column>
        <el-table-column label="错误信息" prop="error_msg" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">{{ row.error_msg || '-' }}</template>
        </el-table-column>
        <el-table-column label="耗时(ms)" prop="cost_time" width="100" />
        <el-table-column label="生成用户ID" prop="gen_user_id" width="110" />
        <el-table-column label="生成时间" prop="gen_time" width="170" />
        <el-table-column label="操作" width="110" fixed="right" class-name="op-col">
          <template #default="{ row }">
            <el-button link type="warning" @click="handlePreview(row)">查看报表</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination-wrap">
        <el-pagination background layout="total, sizes, prev, pager, next, jumper"
          :total="total" v-model:current-page="query.page" v-model:page-size="query.page_size"
          :page-sizes="[10, 20, 50, 100]" @change="fetchList" />
      </div>
    </el-card>

    <el-dialog :title="previewTitle" v-model="previewVisible" width="980px" top="4vh" destroy-on-close>
      <div v-loading="previewLoading" class="preview-body">
        <ReportPreview v-if="previewData" :payload="previewData" />
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { Search, Refresh } from '@element-plus/icons-vue'
import request from '@/utils/request'
import ReportPreview from '@/components/report/ReportPreview.vue'

const loading = ref(false)
const rows = ref([])
const total = ref(0)
const previewVisible = ref(false)
const previewLoading = ref(false)
const previewData = ref(null)
const previewTitle = ref('报表预览')

const query_orig = { page: 1, page_size: 10, template_name: '', gen_status: null }
const query = reactive({ ...query_orig })

async function fetchList() {
  loading.value = true
  try {
    const res = await request.get('/rp/gen/list', { params: query })
    rows.value = res.data.list || []
    total.value = res.data.total || 0
  } finally { loading.value = false }
}
function handleSearch() { query.page = 1; fetchList() }
function handleReset() { Object.assign(query, query_orig); handleSearch() }

async function handlePreview(row) {
  previewTitle.value = `报表预览 · ${row.template_name || ''}`
  previewData.value = null
  previewVisible.value = true
  previewLoading.value = true
  try {
    const res = await request.get(`/rp/gen/preview/${row.id}`)
    previewData.value = res.data
  } finally { previewLoading.value = false }
}

onMounted(fetchList)
</script>

<style scoped>
.preview-body { min-height: 320px; }
</style>
