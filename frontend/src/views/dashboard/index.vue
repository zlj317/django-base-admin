<template>
  <div class="app-container">
    <!-- 欢迎横幅 -->
    <div class="hero">
      <div class="hero-bg"></div>
      <div class="hero-content">
        <el-avatar :size="54" :src="auth.user.avatar || undefined" class="hero-avatar">
          {{ displayName.slice(0, 1).toUpperCase() }}
        </el-avatar>
        <div class="hero-text">
          <div class="hello">{{ greeting }}，{{ displayName }}，欢迎回来！</div>
          <div class="sub">今天也是充满效率的一天 ~</div>
        </div>
      </div>
      <div class="hero-badge">Django · Vue3 · MySQL</div>
    </div>

    <el-row :gutter="16" class="mt12">
      <el-col :xs="24" :sm="12" :md="6" v-for="card in quickCards" :key="card.path" class="stat-col">
        <div class="stat-card" @click="go(card.path)">
          <div class="stat-icon" :style="{ background: card.bg }">
            <el-icon :size="22"><component :is="card.icon" /></el-icon>
          </div>
          <div class="stat-text">
            <div class="stat-title">{{ card.title }}</div>
            <div class="stat-desc">{{ card.desc }}</div>
          </div>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="16" class="mt12">
      <el-col :xs="24" :md="15">
        <el-card shadow="never" class="panel">
          <template #header>
            <div class="panel-header">
              <span class="panel-dot"></span>
              <span>系统简介</span>
            </div>
          </template>
          <p class="desc">
            本系统是一套基于 <b>Django + Vue3 + MySQL</b> 的代码生成型后台管理系统，
            内置用户管理、角色管理、菜单管理、部门管理、字典管理、参数配置、
            操作日志与登录日志等系统模块，并提供强大的代码生成器：
            选择数据库业务表并完成字段配置后，可一键生成后端 Django 代码与
            前端 Vue 页面，快速交付常规增删改查业务模块。
          </p>
          <div class="tags">
            <el-tag effect="light">Django</el-tag>
            <el-tag type="success" effect="light">Vue 3</el-tag>
            <el-tag type="warning" effect="light">Element Plus</el-tag>
            <el-tag type="danger" effect="light">MySQL</el-tag>
            <el-tag type="info" effect="light">Vite</el-tag>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :md="9">
        <el-card shadow="never" class="panel">
          <template #header>
            <div class="panel-header">
              <span class="panel-dot"></span>
              <span>使用流程</span>
            </div>
          </template>
          <ul class="steps">
            <li><span class="step-no">1</span><span>在代码生成器中选择业务数据表并导入</span></li>
            <li><span class="step-no">2</span><span>配置字段的查询、表单、字典与校验方式</span></li>
            <li><span class="step-no">3</span><span>预览代码并下载 ZIP，自动注册业务菜单</span></li>
          </ul>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { auth } from '@/store/auth'
import {
  UserFilled,
  Setting,
  MagicStick,
  Menu as MenuIcon,
  OfficeBuilding,
  Collection
} from '@element-plus/icons-vue'

const router = useRouter()

const displayName = computed(() => auth.user.nickname || auth.user.username || '用户')

const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 6) return '凌晨好'
  if (h < 9) return '早上好'
  if (h < 12) return '上午好'
  if (h < 14) return '中午好'
  if (h < 18) return '下午好'
  return '晚上好'
})

const quickCards = [
  {
    title: '用户管理',
    desc: '账号与角色分配',
    path: '/system/user',
    icon: UserFilled,
    bg: 'linear-gradient(135deg, #4a6cf7, #7a92f9)'
  },
  {
    title: '菜单管理',
    desc: '目录与按钮权限',
    path: '/system/menu',
    icon: MenuIcon,
    bg: 'linear-gradient(135deg, #12b76a, #4ad991)'
  },
  {
    title: '部门管理',
    desc: '组织架构维护',
    path: '/system/dept',
    icon: OfficeBuilding,
    bg: 'linear-gradient(135deg, #f79009, #fdb022)'
  },
  {
    title: '代码生成',
    desc: '一键生成前后端',
    path: '/gen/table',
    icon: MagicStick,
    bg: 'linear-gradient(135deg, #8b5cf6, #b08bfa)'
  }
]

function go(path) {
  router.push(path).catch(() => {})
}
</script>

<style scoped>
/* 欢迎横幅 */
.hero {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 26px 30px;
  overflow: hidden;
  color: #fff;
  background: linear-gradient(120deg, #4a6cf7 0%, #6a83f9 45%, #8b5cf6 100%);
  border-radius: 14px;
  box-shadow: 0 12px 30px rgba(74, 108, 247, 0.3);
}

.hero-bg {
  position: absolute;
  top: -80px;
  right: 60px;
  width: 240px;
  height: 240px;
  background: rgba(255, 255, 255, 0.14);
  border-radius: 50%;
}

.hero-bg::after {
  content: '';
  position: absolute;
  right: -140px;
  bottom: -150px;
  width: 180px;
  height: 180px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 50%;
}

.hero-content {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 16px;
}

.hero-avatar {
  color: #4a6cf7;
  font-size: 20px;
  font-weight: 700;
  background: #fff;
  box-shadow: 0 6px 18px rgba(15, 23, 42, 0.18);
}

.hello {
  font-size: 19px;
  font-weight: 600;
  letter-spacing: 0.5px;
}

.sub {
  margin-top: 7px;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.85);
}

.hero-badge {
  position: relative;
  z-index: 1;
  padding: 7px 14px;
  font-size: 12px;
  letter-spacing: 1px;
  color: rgba(255, 255, 255, 0.92);
  background: rgba(255, 255, 255, 0.18);
  border: 1px solid rgba(255, 255, 255, 0.26);
  border-radius: 20px;
}

/* 快捷卡片 */
.stat-col {
  margin-bottom: 16px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 18px 20px;
  cursor: pointer;
  background: #fff;
  border: 1px solid #eef1f6;
  border-radius: 12px;
  box-shadow: 0 2px 10px rgba(30, 41, 59, 0.05);
  transition: transform 0.22s ease, box-shadow 0.22s ease;
}

.stat-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 12px 26px rgba(30, 41, 59, 0.11);
}

.stat-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 46px;
  height: 46px;
  color: #fff;
  border-radius: 12px;
  flex-shrink: 0;
  box-shadow: 0 6px 14px rgba(30, 41, 59, 0.16);
}

.stat-title {
  font-size: 15px;
  font-weight: 600;
  color: #1f2937;
}

.stat-desc {
  margin-top: 5px;
  font-size: 12px;
  color: #8a94a6;
}

/* 内容面板 */
.panel {
  height: 100%;
}

.panel-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.panel-dot {
  width: 4px;
  height: 15px;
  background: linear-gradient(180deg, #4a6cf7, #8b5cf6);
  border-radius: 3px;
}

.desc {
  margin: 0 0 18px;
  font-size: 13.5px;
  line-height: 2;
  color: #4b5563;
}

.desc b {
  color: #4a6cf7;
}

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

/* 流程 */
.steps {
  padding: 0;
  margin: 0;
  list-style: none;
}

.steps li {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-bottom: 14px;
  font-size: 13px;
  line-height: 1.6;
  color: #4b5563;
}

.steps li:last-child {
  margin-bottom: 0;
}

.step-no {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  font-size: 12px;
  font-weight: 600;
  color: #4a6cf7;
  background: #eef1ff;
  border-radius: 50%;
  flex-shrink: 0;
  margin-top: 1px;
}
</style>
