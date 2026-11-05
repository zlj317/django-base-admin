import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import 'element-plus/dist/index.css'
import 'element-plus/theme-chalk/dark/css-vars.css'
import '@arco-design/web-vue/dist/arco.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import App from './App.vue'
import router from './router'
import { perm } from './directive/perm'
import { initTheme } from './theme'
import './styles/index.css'

// 先恢复本地主题（明暗 + 主题色），再挂载应用，避免首屏闪烁
initTheme()

const app = createApp(App)

// 全局注册 Element Plus 图标组件
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.use(ElementPlus, { locale: zhCn })
app.use(router)
app.directive('perm', perm)
app.mount('#app')
