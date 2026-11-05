<template>
<!-- ============================================================
     文件：登录页（views/login/index.vue）
     职责：管理员账号登录入口。左侧品牌介绍（窄屏隐藏），右侧登录表单。
     依赖：@/store/auth 的 login()（内部调用后端登录接口并写入 token）、
           vue-router（读取 redirect 参数并跳转）、Element Plus 表单与图标。
     被谁使用：router/index.js 中作为静态路由 /login 注册，不挂后台布局。
     主题：背景、卡片、按钮均引用主题 CSS 变量（app 与 brand 系列），支持多主题与暗色。
     ============================================================ -->
  <div class="login-page">
    <!-- 三个背景光晕：纯装饰（pointer-events:none 不拦截点击），
         用大面积模糊色块给纯色背景增加层次，位置与色值见 style 中的 .glow-* -->
    <div class="glow glow-1"></div>
    <div class="glow glow-2"></div>
    <div class="glow glow-3"></div>

    <!-- 登录卡片：左右两栏布局（左 46% 品牌区、右表单区），
         小屏（<=960px）时左侧整块隐藏，只保留表单 -->
    <div class="login-card">
      <!-- 左侧品牌区：品牌主色渐变背景 + 白色文案，用于产品说明与卖点展示 -->
      <div class="login-left">
        <!-- 品牌信息块：Logo、系统名、一句话简介 -->
        <div class="brand">
          <!-- Logo 底板：白底圆角方块，内部图标使用品牌主色 -->
          <div class="brand-logo">
            <el-icon :size="26"><Platform /></el-icon>
          </div>
          <!-- 系统名称 -->
          <h1>后台管理系统</h1>
          <!-- 技术栈与定位说明；<br /> 手动换行，保证两行文案节奏一致 -->
          <p>Django + Vue3 + MySQL<br />代码生成型后台管理平台</p>
        </div>
        <!-- 产品卖点列表：三条静态文案，图标为统一的对勾，
             属于纯展示内容，不参与任何业务逻辑 -->
        <ul class="feature-list">
          <!-- 卖点一：权限与菜单一体化 -->
          <li>
            <el-icon><CircleCheck /></el-icon>
            <span>权限菜单一体化，开箱即用</span>
          </li>
          <!-- 卖点二：代码生成能力 -->
          <li>
            <el-icon><CircleCheck /></el-icon>
            <span>数据表一键生成前后端代码</span>
          </li>
          <!-- 卖点三：生成后自动注册菜单 -->
          <li>
            <el-icon><CircleCheck /></el-icon>
            <span>生成即注册菜单，无需手工配置</span>
          </li>
        </ul>
        <!-- 右上角装饰圆环：只有边框没有背景，用于点缀品牌区留白 -->
        <div class="deco-ring"></div>
      </div>

      <!-- 右侧表单区：登录标题、表单、默认账号提示 -->
      <div class="login-right">
        <!-- 表单标题 -->
        <h2 class="login-title">欢迎登录</h2>
        <!-- 副标题：说明登录身份要求 -->
        <p class="login-sub">请使用管理员账号登录系统</p>
        <!-- 登录表单：ref 供 handleLogin 调用 validate；
             :model/:rules 绑定数据与校验规则；label-position=top 标签在输入框上方；
             @keyup.enter 让用户在任意输入框内按回车即可提交 -->
        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          size="large"
          label-position="top"
          @keyup.enter="handleLogin"
        >
          <!-- 用户名字段：v-model.trim 自动去掉首尾空格，避免“空格导致的账号不存在” -->
          <el-form-item prop="username" label="用户名">
            <el-input
              v-model.trim="form.username"
              placeholder="请输入用户名"
              :prefix-icon="User"
              clearable
            />
          </el-form-item>
          <!-- 密码字段：type=password 隐藏明文，show-password 提供“眼睛”按钮切换可见性；
               v-model.trim 同样去除首尾空格（注意这也会裁掉密码首尾空格，属现有行为） -->
          <el-form-item prop="password" label="密码">
            <el-input
              v-model.trim="form.password"
              type="password"
              placeholder="请输入密码"
              :prefix-icon="Lock"
              show-password
            />
          </el-form-item>
          <!-- 提交按钮行：独立 form-item 以对齐上方输入框；:loading 在请求期间禁用并显示转圈 -->
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
        <!-- 默认账号提示：便于首次体验，正式环境可考虑移除 -->
        <div class="login-tip">默认账号：admin / 123456</div>
      </div>
    </div>

    <!-- 页脚版权信息：固定文案，年份为硬编码 -->
    <div class="login-footer">Copyright © 2026 后台管理系统</div>
  </div>
</template>

<script setup>
// ============================================================
// 脚本说明：登录页逻辑集中在 handleLogin 一处，流程为
// 表单校验 → 调用 store 的 login()（内部请求后端并写 token）→ 成功提示 → 跳转。
// 失败提示由 request 拦截器统一弹出，本页只负责恢复 loading 状态。
// ============================================================
// reactive 用于创建可被 v-model 双向绑定的表单对象；ref 用于表单实例与 loading 标记
import { reactive, ref } from 'vue'
// useRoute 读取地址栏上的 redirect 参数；useRouter 执行登录后的跳转
import { useRoute, useRouter } from 'vue-router'
// 仅使用成功提示；失败提示已在请求拦截器中统一处理
import { ElMessage } from 'element-plus'
// 图标：User/Lock 作为输入框前缀图标，Platform/CircleCheck 用于左侧品牌区
import { User, Lock, Platform, CircleCheck } from '@element-plus/icons-vue'
// 登录动作从 auth store 引入：内部负责调用后端接口、保存 token 与用户信息
import { login } from '@/store/auth'

// 当前路由：用于读取 query.redirect
const route = useRoute()
// 路由实例：用于登录成功后进行编程式导航
const router = useRouter()

// 表单实例引用：提交时通过它调用 validate 触发校验
const formRef = ref()
// 提交中标记：驱动按钮 loading，避免重复提交
const loading = ref(false)
// 登录表单数据：仅用户名与密码两个字段，初始均为空串
const form = reactive({
  username: '',
  password: ''
})
// 校验规则：两个字段都必填，触发时机为失焦（blur），由 el-form 的 :rules 消费
const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

// 登录主流程：校验通过后调用接口，成功则跳转，失败由拦截器提示
async function handleLogin() {
  // 无回调形式调用 validate：校验不通过会 reject，因此这一行若失败会中断后续流程
  await formRef.value.validate()
  // 校验通过，进入请求中状态（按钮转圈并禁止重复点击）
  loading.value = true
  try {
    // store 的 login 负责请求后端、写入 token 与用户信息，失败时抛出异常
    await login(form)
    // 登录成功提示（store 内不弹提示，因此在这里提示一次）
    ElMessage.success('登录成功')
    // 优先回到被守卫拦截前的目标页（如超时后重新登录），否则默认去首页
    const redirect = route.query.redirect || '/dashboard'
    // String(redirect) 处理 query 可能是数组的情况，保证传参类型正确
    router.push(String(redirect))
  } catch (e) {
    // 错误提示已由 request 拦截器统一处理
    // 这里保持空 catch：不再重复弹窗，仅吞掉异常以继续执行 finally
  } finally {
    // 无论成功失败都解除 loading，保证按钮可再次点击
    loading.value = false
  }
}
</script>

<style scoped>
/* ============================================================
   样式区说明：scoped 限定作用域，避免影响其他页面。
   背景与卡片颜色引用 --app-* 主题变量，品牌区与按钮引用 --brand-*，
   因此切换主题（含暗色）时登录页无需额外适配。
   ============================================================ */
/* 页面根容器：铺满高度并让卡片水平垂直居中；overflow:hidden 裁掉背景光晕的溢出 */
.login-page {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  overflow: hidden;
  /* 页面底色跟随主题（亮色/暗色自动切换） */
  background: var(--app-bg);
}

/* 柔和色块光晕：极淡，营造层次但不抢眼 */
/* 公共部分：绝对定位的大圆 + 90px 模糊；
   pointer-events:none 保证光晕不会挡住表单的点击与输入 */
.glow {
  position: absolute;
  border-radius: 50%;
  filter: blur(90px);
  pointer-events: none;
}

/* 光晕 1：左上角，使用品牌光晕色 */
.glow-1 {
  top: -160px;
  left: -120px;
  width: 520px;
  height: 520px;
  background: var(--brand-glow);
}

/* 光晕 2：右下角，用 color-mix 把品牌主色调成 18% 透明，
   让光晕在暗色背景下也不会形成生硬的色块 */
.glow-2 {
  right: -140px;
  bottom: -180px;
  width: 560px;
  height: 560px;
  background: color-mix(in srgb, var(--brand-primary) 18%, transparent);
}

/* 光晕 3：右上方较小的一块，使用品牌浅色，补充中部亮度 */
.glow-3 {
  top: 12%;
  right: 18%;
  width: 300px;
  height: 300px;
  background: var(--brand-primary-soft);
}

/* 登录卡片：固定 880px 宽的双栏容器；
   z-index:2 让它浮在背景光晕之上；overflow:hidden 使子栏圆角被正确裁切 */
.login-card {
  position: relative;
  z-index: 2;
  display: flex;
  width: 880px;
  min-height: 470px;
  overflow: hidden;
  /* 卡片底色随主题变化 */
  background: var(--app-surface);
  border: 1px solid var(--app-border);
  border-radius: var(--app-radius-xl);
  box-shadow: var(--app-shadow-lg);
}

/* 左侧品牌区：主色渐变 */
/* 占卡片宽度 46%，纵向居中内容；overflow:hidden 裁切内部装饰元素 */
.login-left {
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: center;
  width: 46%;
  padding: 44px 42px;
  overflow: hidden;
  color: #fff;
  /* 155deg 的斜向渐变，起始色为品牌 hover 色，随主题切换 */
  background: linear-gradient(155deg, var(--brand-primary-hover) 0%, var(--brand-primary) 100%);
}

/* 左下角大圆：用伪元素实现，半透明白，作为渐变背景上的柔光装饰 */
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

/* 右上角线框圆环：只有 1px 半透明白边框，与实心圆形成对比 */
.deco-ring {
  position: absolute;
  top: 34px;
  right: 34px;
  width: 96px;
  height: 96px;
  border: 1px solid rgba(255, 255, 255, 0.22);
  border-radius: 50%;
}

/* 品牌文字块：抬高层级，避免被绝对定位的装饰元素覆盖 */
.brand {
  position: relative;
  z-index: 1;
}

/* Logo 底板：48x48 白色圆角方块，图标用品牌主色反衬；
   阴影让其在渐变背景上有轻微浮起感 */
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

/* 系统名称：26px 加粗，字距 2px 增强标题感 */
.brand h1 {
  margin: 0 0 10px;
  font-size: 26px;
  font-weight: 700;
  letter-spacing: 2px;
}

/* 品牌副文案：小号、行高 1.9，半透明白保证在渐变上的可读性 */
.brand p {
  margin: 0;
  font-size: 13px;
  line-height: 1.9;
  color: rgba(255, 255, 255, 0.76);
}

/* 卖点列表：去掉默认圆点，向上留 30px 与品牌文案拉开距离；
   z-index:1 同样是为了避开装饰元素 */
.feature-list {
  position: relative;
  z-index: 1;
  padding: 0;
  margin: 30px 0 0;
  list-style: none;
}

/* 单个卖点：图标与文字水平居中对齐，弱化白色文字 */
.feature-list li {
  display: flex;
  align-items: center;
  gap: 9px;
  margin-bottom: 12px;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.9);
}

/* 卖点图标：固定 15px，浅蓝紫色作为渐变背景上的点缀色 */
.feature-list .el-icon {
  font-size: 15px;
  color: #a9bcf5;
}

/* 右侧表单区 */
/* 表单区占剩余宽度，内边距上方更大以平衡左侧品牌区的视觉重量 */
.login-right {
  flex: 1;
  padding: 56px 52px 40px;
  background: var(--app-surface);
}

/* 登录标题：卡片内最大字号，使用主文字色 */
.login-title {
  margin: 0 0 6px;
  font-size: 24px;
  font-weight: 700;
  color: var(--app-text-1);
}

/* 登录副标题：小号弱化文字，与标题拉开层级 */
.login-sub {
  margin: 0 0 28px;
  font-size: 13px;
  color: var(--app-text-3);
}

/* 表单标签：通过 :deep 穿透到 Element Plus 内部节点；
   缩小字号与下内边距，让标签更紧凑 */
.login-right :deep(.el-form-item__label) {
  padding-bottom: 4px;
  font-size: 13px;
  font-weight: 500;
  color: var(--app-text-2);
}

/* 输入框外壳：圆角 + 次要背景色；用 inset box-shadow 画 1px 边框，
   避免边框影响布局尺寸；颜色全部取主题变量 */
.login-right :deep(.el-input__wrapper) {
  padding: 2px 14px;
  border-radius: var(--app-radius-md);
  background: var(--app-surface-2);
  box-shadow: 0 0 0 1px var(--app-border) inset;
}

/* 聚焦态：背景回到主表面色，并叠加品牌色 1px 描边 + 4px 浅色光晕，
   给出明确的焦点反馈（暗色主题下光晕同样由变量控制） */
.login-right :deep(.el-input__wrapper.is-focus) {
  background: var(--app-surface);
  box-shadow: 0 0 0 1px var(--brand-primary) inset, 0 0 0 4px var(--brand-primary-soft);
}

/* 提交按钮所在表单项：与上方字段拉开距离，并去掉默认下边距 */
.login-submit {
  margin-top: 26px;
  margin-bottom: 0;
}

/* 登录按钮：通栏、46px 高、字距 4px；
   背景为品牌渐变，阴影取品牌光晕色，主题切换时自动更新 */
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

/* 按钮悬停：整体提亮 6%，比改变背景色更简单且不破坏渐变 */
.login-btn:hover {
  filter: brightness(1.06);
}

/* 默认账号提示：居中弱化文字，帮助首次使用者快速登录 */
.login-tip {
  margin-top: 22px;
  font-size: 12px;
  text-align: center;
  color: var(--app-text-3);
}

/* 页脚版权：位于卡片下方，z-index 保证不被光晕遮挡；颜色随主题变化 */
.login-footer {
  position: relative;
  z-index: 2;
  margin-top: 26px;
  font-size: 12px;
  color: var(--app-text-3);
}

/* 窄屏适配：卡片改为 92% 宽并取消最小高度，避免手机端出现大片空白 */
@media (max-width: 960px) {
  .login-card {
    width: 92%;
    min-height: auto;
  }

  /* 直接隐藏左侧品牌栏，只留表单，保证小屏可操作区域充足 */
  .login-left {
    display: none;
  }

  /* 减小表单区内边距，给小屏腾出更多空间 */
  .login-right {
    padding: 40px 32px;
  }
}
</style>
