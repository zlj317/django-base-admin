// 应用入口文件。
// 职责：创建 Vue 应用实例、注册全局插件/图标/权限指令、初始化主题，并把根组件挂载到 #app。
// 依赖关系：Element Plus（存量组件与图标）、Arco Design Vue（本轮 UI 设计体系）、router（静态+动态路由）、theme（明暗与配色）、styles/index.css（全局设计令牌）。

// Vue 3 的应用工厂函数，用来创建一个独立的根应用实例
import { createApp } from 'vue'
// Element Plus 组件库本体：存量页面仍在使用，保留以兼容尚未迁移到 Arco 的页面
import ElementPlus from 'element-plus'
// Element Plus 中文语言包，让分页、表格、日期等内置文案显示为中文
import zhCn from 'element-plus/es/locale/lang/zh-cn'
// Element Plus 基础样式，其组件渲染依赖这里定义的 CSS 变量与类名
import 'element-plus/dist/index.css'
// Element Plus 暗色模式变量：html 上出现 dark 类后，其组件自动切换到深色配色
import 'element-plus/theme-chalk/dark/css-vars.css'
// Arco Design Vue 全量样式：本项目通过覆盖其主题变量统一视觉，不改变组件的原有用法
import '@arco-design/web-vue/dist/arco.css'
// Element Plus 图标集合，下面会以「图标名 → 组件」的方式全局注册
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
// 根组件，内部只有一个 router-view，负责渲染当前路由匹配到的页面
import App from './App.vue'
// 全局唯一的路由实例（静态路由 + 登录后按菜单动态注入的路由）
import router from './router'
// 按钮级权限指令的实现（模板中写作 v-perm="'system:user:create'"）
import { perm } from './directive/perm'
// 主题系统入口：读取 localStorage 中保存的模式/配色并写入 html 属性
import { initTheme } from './theme'
// 全局样式入口：设计令牌（颜色、间距、圆角、阴影）以及通用页面样式
import './styles/index.css'

// 必须在创建应用之前恢复主题：
// 1) 主题以 data 属性写在 <html> 上，越早写入越能避免刷新时“先白后黑”的闪烁；
// 2) Arco / Element Plus 的颜色变量都依赖该属性，执行过晚会导致首屏组件配色错误。
initTheme()

// 创建根应用实例（此后才能挂载插件、指令与全局组件）
const app = createApp(App)

// 全局注册 Element Plus 图标：
// 模板中可直接写 <el-icon><User /></el-icon>，无需每个页面单独 import，减少了各页面的重复样板代码。
// 代价是所有图标都会打进主包；本项目使用的图标数量有限，体积影响在可接受范围内。
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

// 安装 Element Plus 并指定中文语言包（影响“暂无数据”“条/页”“确定/取消”等内置文案）
app.use(ElementPlus, { locale: zhCn })
// 安装路由：挂载后才会开始解析地址并触发全局前置守卫
app.use(router)
// 注册 v-perm 指令：元素挂载/更新时按当前用户权限决定显示或隐藏
app.directive('perm', perm)
// 挂载到 index.html 中的 #app 容器，执行后页面开始渲染
app.mount('#app')
