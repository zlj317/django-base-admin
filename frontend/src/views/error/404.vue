<template>
  <!-- 文件说明：404 兜底页，负责在路由未匹配或页面无权访问时向用户给出提示与返回入口。 -->
  <!-- 依赖 vue-router 实例做编程式跳转；由 router/index.js 中通配路由 /:pathMatch(.*)* 指向本组件。 -->
  <!-- 页面根容器：占满路由视图区域（高度 100%），让错误提示始终居中显示，避免出现半屏空白。 -->
  <div class="not-found">
    <!-- 状态码：静态大号数字，直接告知用户这是 404 错误。 -->
    <div class="code">404</div>
    <!-- 提示文案：统一说明页面不存在或无权访问，不暴露内部细节，兼顾安全与可读性。 -->
    <div class="text">抱歉，您访问的页面不存在或无权访问</div>
    <!-- 返回首页按钮：通过路由实例跳转仪表盘，给用户一个明确的离开路径，避免停留在死链页面。 -->
    <el-button type="primary" @click="router.push('/dashboard')">返回首页</el-button>
  </div>
</template>

<script setup>
// 引入路由组合式 API：在 setup 中取得路由实例，供模板里的“返回首页”按钮调用 push 跳转。
import { useRouter } from 'vue-router'

// 当前路由实例：只读取不修改，用于跳转到 /dashboard。
const router = useRouter()
</script>

<style scoped>
/* 页面根容器：纵向 flex + 双向居中，把错误码、文案和按钮聚在屏幕中央；浅灰背景与业务页面区分。 */
.not-found {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  background-color: #f0f2f5;
}

/* 状态码样式：超大字号和加粗提升辨识度，line-height:1 收紧行高，防止数字上下被多余留白撑开。 */
.code {
  font-size: 120px;
  font-weight: 700;
  color: #409eff;
  line-height: 1;
}

/* 提示文案样式：上下留白与状态码、按钮拉开间距；灰色文字降低视觉权重，突出状态码和主按钮。 */
.text {
  margin: 20px 0 28px;
  color: #909399;
  font-size: 15px;
}
</style>
