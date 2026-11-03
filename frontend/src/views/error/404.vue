<template>
  <div class="not-found">
    <div class="code">404</div>
    <div class="text">抱歉，您访问的页面不存在或无权访问</div>
    <el-button type="primary" @click="router.push('/dashboard')">返回首页</el-button>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()
</script>

<style scoped>
.not-found {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  background-color: #f0f2f5;
}

.code {
  font-size: 120px;
  font-weight: 700;
  color: #409eff;
  line-height: 1;
}

.text {
  margin: 20px 0 28px;
  color: #909399;
  font-size: 15px;
}
</style>
