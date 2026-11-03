<template>
  <!-- 动态表单渲染：按字段配置输出输入组件，支持只读模式 -->
  <el-form :model="data" label-width="110px" :disabled="readonly" class="wf-form-render">
    <el-row :gutter="16">
      <el-col v-for="field in fields" :key="field.key" :span="field.type === 'textarea' || field.type === 'file' ? 24 : 12">
        <el-form-item :label="field.label">
          <el-input
            v-if="field.type === 'textarea'"
            v-model="data[field.key]"
            type="textarea"
            :rows="3"
            :placeholder="field.placeholder || '请输入' + field.label"
          />
          <el-input-number
            v-else-if="field.type === 'number'"
            v-model="data[field.key]"
            :controls-position="'right'"
            style="width: 100%"
          />
          <el-date-picker
            v-else-if="field.type === 'date'"
            v-model="data[field.key]"
            type="date"
            value-format="YYYY-MM-DD"
            :placeholder="field.placeholder || '请选择' + field.label"
            style="width: 100%"
          />
          <el-select
            v-else-if="field.type === 'select' || field.type === 'dict'"
            v-model="data[field.key]"
            clearable
            :placeholder="field.placeholder || '请选择' + field.label"
            style="width: 100%"
          >
            <el-option v-for="opt in field.options || []" :key="opt" :label="opt" :value="opt" />
          </el-select>
          <el-input
            v-else
            v-model="data[field.key]"
            :placeholder="field.placeholder || '请输入' + field.label"
          />
        </el-form-item>
      </el-col>
    </el-row>
    <div v-if="!fields.length" class="wf-empty">该表单暂未配置字段</div>
  </el-form>
</template>

<script setup>
defineProps({
  fields: { type: Array, default: () => [] },
  data: { type: Object, required: true },
  readonly: { type: Boolean, default: false }
})
</script>

<style scoped>
.wf-form-render :deep(.el-form-item) {
  margin-bottom: 16px;
}
.wf-empty {
  padding: 30px 0;
  text-align: center;
  color: var(--el-text-color-secondary);
}
</style>
