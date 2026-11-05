<!--
  文件级说明：
  职责：工作流动态表单渲染器——根据后端流程定义中的字段配置动态生成录入控件，并兼容只读查看。
  依赖：Element Plus 表单组件；字段配置结构为 { key, label, type, placeholder, options }。
  被谁使用：workflow/WorkflowDetail.vue（只读展示）以及流程发起/审批页面（可编辑录入）。
  说明：表单值不做本地副本，直接读写父组件传入的 data 对象（v-model 双向绑定）。
-->
<template>
  <!-- 动态表单渲染：按字段配置输出输入组件，支持只读模式 -->
  <!-- :disabled 统一控制整表单只读，避免给每个控件单独传 disabled；label-width 固定 110px 保证标签对齐 -->
  <el-form :model="data" label-width="110px" :disabled="readonly" class="wf-form-render">
    <!-- 栅格行：16px 列间距，让同一行的两个字段之间有呼吸感 -->
    <el-row :gutter="16">
      <!-- 逐字段生成表单项：span 决定宽度——多行文本与文件字段占满整行(24)，其余字段一行两个(12)；
           key 使用字段唯一 key，保证条件渲染/排序时组件状态稳定 -->
      <el-col v-for="field in fields" :key="field.key" :span="field.type === 'textarea' || field.type === 'file' ? 24 : 12">
        <!-- 表单项：label 直接取字段配置中的中文名 -->
        <el-form-item :label="field.label">
          <!-- 多行文本：textarea 类型用于备注/说明类长内容，固定 3 行高度；
               placeholder 优先取配置值，缺失时用“请输入+字段名”兜底 -->
          <el-input
            v-if="field.type === 'textarea'"
            v-model="data[field.key]"
            type="textarea"
            :rows="3"
            :placeholder="field.placeholder || '请输入' + field.label"
          />
          <!-- 数字输入：controls-position=right 把加减按钮放右侧，符合常规数值录入习惯；
               宽度 100% 与同一行的文本输入视觉对齐 -->
          <el-input-number
            v-else-if="field.type === 'number'"
            v-model="data[field.key]"
            :controls-position="'right'"
            style="width: 100%"
          />
          <!-- 日期选择：只取日期（不含时分秒），value-format 固定为 YYYY-MM-DD，
               保证提交给后端的是稳定字符串格式而不是 Date 对象 -->
          <el-date-picker
            v-else-if="field.type === 'date'"
            v-model="data[field.key]"
            type="date"
            value-format="YYYY-MM-DD"
            :placeholder="field.placeholder || '请选择' + field.label"
            style="width: 100%"
          />
          <!-- 下拉选择：select 与 dict 两种类型共用同一渲染逻辑（字典字段在配置阶段已展开为 options）；
               clearable 允许清空已选值 -->
          <el-select
            v-else-if="field.type === 'select' || field.type === 'dict'"
            v-model="data[field.key]"
            clearable
            :placeholder="field.placeholder || '请选择' + field.label"
            style="width: 100%"
          >
            <!-- 选项渲染：options 缺失时兜底空数组；这里假设选项为字符串数组，
                 label/value 均取字符串本身（若后端给出对象数组需另行适配） -->
            <el-option v-for="opt in field.options || []" :key="opt" :label="opt" :value="opt" />
          </el-select>
          <!-- 兜底分支：未识别的类型（含普通 text）一律按单行文本输入渲染，
               保证字段配置异常时仍可录入而不是空白 -->
          <el-input
            v-else
            v-model="data[field.key]"
            :placeholder="field.placeholder || '请输入' + field.label"
          />
        </el-form-item>
      </el-col>
    </el-row>
    <!-- 空态：流程未配置任何字段时给出明确提示，而不是渲染一个空白表单 -->
    <div v-if="!fields.length" class="wf-empty">该表单暂未配置字段</div>
  </el-form>
</template>

<script setup>
// 组件 props：
// · fields：字段配置数组，每项含 key（数据字段名）、label（显示名）、type（控件类型）、
//           placeholder（可选占位文案）、options（下拉选项）
// · data：表单数据对象，组件通过 v-model 直接读写其中的 field.key 属性（父组件持有真实状态）
// · readonly：只读开关，透传给 el-form 的 disabled，统一禁用全部控件（审批详情页使用）
defineProps({
  fields: { type: Array, default: () => [] },
  data: { type: Object, required: true },
  readonly: { type: Boolean, default: false }
})
</script>

<style scoped>
/* 表单项下边距：统一 16px，避免默认 18px 在多字段表单里显得过于松散 */
.wf-form-render :deep(.el-form-item) {
  margin-bottom: 16px;
}
/* 空态提示：上下 30px 留白 + 居中 + 次级文字色，让“未配置字段”看起来是有意的状态而非渲染错误 */
.wf-empty {
  padding: 30px 0;
  text-align: center;
  color: var(--el-text-color-secondary);
}
</style>
