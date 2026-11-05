<template>
  <div class="login-page">
    <div class="glow glow-1"></div>
    <div class="glow glow-2"></div>
    <div class="glow glow-3"></div>

    <div class="login-card">
      <div class="login-left">
        <div class="brand">
          <div class="brand-logo">
            <el-icon :size="26"><Platform /></el-icon>
          </div>
          <h1>后台管理系统</h1>
          <p>Django + Vue3 + MySQL<br />代码生成型后台管理平台</p>
        </div>
        <ul class="feature-list">
          <li>
            <el-icon><CircleCheck /></el-icon>
            <span>权限菜单一体化，开箱即用</span>
          </li>
          <li>
            <el-icon><CircleCheck /></el-icon>
            <span>数据表一键生成前后端代码</span>
          </li>
          <li>
            <el-icon><CircleCheck /></el-icon>
            <span>生成即注册菜单，无需手工配置</span>
          </li>
        </ul>
        <div class="deco-ring"></div>
      </div>

      <div class="login-right">
        <h2 class="login-title">欢迎登录</h2>
        <p class="login-sub">请使用管理员账号登录系统</p>
        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          size="large"
          label-position="top"
          @keyup.enter="handleLogin"
        >
          <el-form-item prop="username" label="用户名">
            <el-input
              v-model.trim="form.username"
              placeholder="请输入用户名"
              :prefix-icon="User"
              clearable
            />
          </el-form-item>
          <el-form-item prop="password" label="密码">
            <el-input
              v-model.trim="form.password"
              type="password"
              placeholder="请输入密码"
              :prefix-icon="Lock"
              show-password
            />
          </el-form-item>
          <el-form-item class="login-submit">
            <el-button
              type="primary"
              class="login-btn"
              size="large"
              :loading="loading"
              @click="handleLogin"
            >
              登 录
            </el-button>
          </el-form-item>
        </el-form>
        <div class="login-tip">默认账号：admin / 123456</div>
      </div>
    </div>

    <div class="login-footer">Copyright © 2026 后台管理系统</div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock, Platform, CircleCheck } from '@element-plus/icons-vue'
import { login } from '@/store/auth'

const route = useRoute()
const router = useRouter()

const formRef = ref()
const loading = ref(false)
const form = reactive({
  username: '',
  password: ''
})
const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

async function handleLogin() {
  await formRef.value.validate()
  loading.value = true
  try {
    await login(form)
    ElMessage.success('登录成功')
    const redirect = route.query.redirect || '/dashboard'
    router.push(String(redirect))
  } catch (e) {
    // 错误提示已由 request 拦截器统一处理
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  overflow: hidden;
  background: var(--app-bg);
}

/* 柔和色块光晕：极淡，营造层次但不抢眼 */
.glow {
  position: absolute;
  border-radius: 50%;
  filter: blur(90px);
  pointer-events: none;
}

.glow-1 {
  top: -160px;
  left: -120px;
  width: 520px;
  height: 520px;
  background: var(--brand-glow);
}

.glow-2 {
  right: -140px;
  bottom: -180px;
  width: 560px;
  height: 560px;
  background: color-mix(in srgb, var(--brand-primary) 18%, transparent);
}

.glow-3 {
  top: 12%;
  right: 18%;
  width: 300px;
  height: 300px;
  background: var(--brand-primary-soft);
}

.login-card {
  position: relative;
  z-index: 2;
  display: flex;
  width: 880px;
  min-height: 470px;
  overflow: hidden;
  background: var(--app-surface);
  border: 1px solid var(--app-border);
  border-radius: var(--app-radius-xl);
  box-shadow: var(--app-shadow-lg);
}

/* 左侧品牌区：主色渐变 */
.login-left {
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: center;
  width: 46%;
  padding: 44px 42px;
  overflow: hidden;
  color: #fff;
  background: linear-gradient(155deg, var(--brand-primary-hover) 0%, var(--brand-primary) 100%);
}

.login-left::after {
  content: '';
  position: absolute;
  right: -70px;
  bottom: -90px;
  width: 240px;
  height: 240px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.08);
}

.deco-ring {
  position: absolute;
  top: 34px;
  right: 34px;
  width: 96px;
  height: 96px;
  border: 1px solid rgba(255, 255, 255, 0.22);
  border-radius: 50%;
}

.brand {
  position: relative;
  z-index: 1;
}

.brand-logo {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  margin-bottom: 20px;
  color: var(--brand-primary);
  background: #fff;
  border-radius: var(--app-radius-lg);
  box-shadow: 0 8px 22px rgba(15, 23, 42, 0.18);
}

.brand h1 {
  margin: 0 0 10px;
  font-size: 26px;
  font-weight: 700;
  letter-spacing: 2px;
}

.brand p {
  margin: 0;
  font-size: 13px;
  line-height: 1.9;
  color: rgba(255, 255, 255, 0.76);
}

.feature-list {
  position: relative;
  z-index: 1;
  padding: 0;
  margin: 30px 0 0;
  list-style: none;
}

.feature-list li {
  display: flex;
  align-items: center;
  gap: 9px;
  margin-bottom: 12px;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.9);
}

.feature-list .el-icon {
  font-size: 15px;
  color: #a9bcf5;
}

/* 右侧表单区 */
.login-right {
  flex: 1;
  padding: 56px 52px 40px;
  background: var(--app-surface);
}

.login-title {
  margin: 0 0 6px;
  font-size: 24px;
  font-weight: 700;
  color: var(--app-text-1);
}

.login-sub {
  margin: 0 0 28px;
  font-size: 13px;
  color: var(--app-text-3);
}

.login-right :deep(.el-form-item__label) {
  padding-bottom: 4px;
  font-size: 13px;
  font-weight: 500;
  color: var(--app-text-2);
}

.login-right :deep(.el-input__wrapper) {
  padding: 2px 14px;
  border-radius: var(--app-radius-md);
  background: var(--app-surface-2);
  box-shadow: 0 0 0 1px var(--app-border) inset;
}

.login-right :deep(.el-input__wrapper.is-focus) {
  background: var(--app-surface);
  box-shadow: 0 0 0 1px var(--brand-primary) inset, 0 0 0 4px var(--brand-primary-soft);
}

.login-submit {
  margin-top: 26px;
  margin-bottom: 0;
}

.login-btn {
  width: 100%;
  height: 46px;
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 4px;
  border-radius: var(--app-radius-md);
  background: var(--brand-gradient);
  border: none;
  box-shadow: 0 10px 24px var(--brand-glow);
}

.login-btn:hover {
  filter: brightness(1.06);
}

.login-tip {
  margin-top: 22px;
  font-size: 12px;
  text-align: center;
  color: var(--app-text-3);
}

.login-footer {
  position: relative;
  z-index: 2;
  margin-top: 26px;
  font-size: 12px;
  color: var(--app-text-3);
}

@media (max-width: 960px) {
  .login-card {
    width: 92%;
    min-height: auto;
  }

  .login-left {
    display: none;
  }

  .login-right {
    padding: 40px 32px;
  }
}
</style>
