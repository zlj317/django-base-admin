// 首页可视化自测脚本（中间产物，不提交到交付目录）
// 用途：用本机 Edge + playwright-core 在 1440/1280 两种宽度、明暗与多配色下截图，
//      并检查面板宽度是否撑满栅格列、控制台是否有报错、关键入口能否跳转。
import { chromium } from 'playwright-core'
import fs from 'node:fs'

const EDGE = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe'
const BASE = 'http://127.0.0.1:5173'
const OUT = 'D:\\other\\django-base-admin\\docs\\images\\dashboard'
fs.mkdirSync(OUT, { recursive: true })

// 先通过后端登录接口拿到真实 token（避免前端登录流程带来的额外等待）
const loginRes = await fetch('http://127.0.0.1:8000/api/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ username: 'admin', password: '123456' })
})
const loginJson = await loginRes.json()
const token = loginJson?.data?.token || ''
const user = loginJson?.data?.user || {}
console.log('token length:', token.length, 'user:', user.username || user.nickname)

const browser = await chromium.launch({ executablePath: EDGE, headless: true })
const cases = [
  { width: 1440, mode: 'light', palette: 'blue' },
  { width: 1440, mode: 'dark', palette: 'blue' },
  { width: 1440, mode: 'light', palette: 'purple' },
  { width: 1440, mode: 'dark', palette: 'rose' },
  { width: 1280, mode: 'light', palette: 'blue' },
  { width: 1280, mode: 'dark', palette: 'purple' }
]
const errors = []

for (const c of cases) {
  const context = await browser.newContext({ viewport: { width: c.width, height: 1000 } })
  await context.addInitScript(({ token, user, mode, palette }) => {
    localStorage.setItem('da_token', token)
    localStorage.setItem('da_user', JSON.stringify(user))
    localStorage.setItem('app-theme', JSON.stringify({ mode, palette }))
  }, { token, user, mode: c.mode, palette: c.palette })
  const page = await context.newPage()
  page.on('console', msg => { if (msg.type() === 'error') errors.push(`[${c.width}-${c.mode}-${c.palette}] ${msg.text()}`) })
  page.on('pageerror', err => errors.push(`[${c.width}-${c.mode}-${c.palette}] PAGEERROR ${err.message}`))
  await page.goto(`${BASE}/dashboard`, { waitUntil: 'networkidle', timeout: 60000 })
  await page.waitForTimeout(1200)
  // 临时解除布局内部滚动容器的高度限制，便于 fullPage 截图看到整页（仅自测脚本内生效，不改源码）
  await page.addStyleTag({ content: `
    html, body, #app, .app-wrapper { height: auto !important; overflow: visible !important; }
    .app-main, .app-container { height: auto !important; max-height: none !important; overflow: visible !important; }
  ` })
  await page.waitForTimeout(400)
  const theme = await page.evaluate(() => ({
    mode: document.documentElement.classList.contains('dark') ? 'dark' : 'light',
    palette: document.documentElement.dataset.theme
  }))
  const layout = await page.evaluate(() => {
    const rows = [...document.querySelectorAll('.grid-row')]
    return rows.map(row => {
      const cols = [...row.querySelectorAll(':scope > .el-col')]
      const gaps = cols.map(col => {
        const panel = col.querySelector('.panel')
        if (!panel) return null
        const cw = col.getBoundingClientRect().width
        const pw = panel.getBoundingClientRect().width
        return { col: Math.round(cw), panel: Math.round(pw), fill: +(pw / cw).toFixed(3) }
      })
      return { rowBottom: Math.round(row.getBoundingClientRect().right), gaps }
    })
  })
  const scroll = await page.evaluate(() => ({ h: document.documentElement.scrollHeight, w: document.documentElement.scrollWidth }))
  await page.screenshot({ path: `${OUT}/dashboard-${c.width}-${c.mode}-${c.palette}.png`, fullPage: true })
  console.log(`shot ${c.width}-${c.mode}-${c.palette}`, JSON.stringify({ theme, scroll, layout }))
  await context.close()
}

// 单独验证关键跳转与控制台（1440 亮色）
{
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } })
  await context.addInitScript(({ token, user }) => {
    localStorage.setItem('da_token', token)
    localStorage.setItem('da_user', JSON.stringify(user))
    localStorage.setItem('app-theme', JSON.stringify({ mode: 'light', palette: 'blue' }))
  }, { token, user })
  const page = await context.newPage()
  page.on('console', msg => { if (msg.type() === 'error') errors.push(`[nav] ${msg.text()}`) })
  page.on('pageerror', err => errors.push(`[nav] PAGEERROR ${err.message}`))
  await page.goto(`${BASE}/dashboard`, { waitUntil: 'networkidle', timeout: 60000 })
  await page.waitForTimeout(800)
  const quick = await page.evaluate(() => {
    const first = document.querySelector('.quick-entry')
    const todo = document.querySelector('.todo-item')
    return { quickText: first ? first.textContent.trim() : 'none', todoText: todo ? todo.textContent.trim().slice(0, 30) : 'none' }
  })
  if (await page.$('.quick-entry')) {
    await page.click('.quick-entry')
    await page.waitForTimeout(900)
  }
  const afterQuick = page.url()
  await page.goto(`${BASE}/dashboard`, { waitUntil: 'networkidle' })
  await page.waitForTimeout(600)
  if (await page.$('.todo-item')) {
    await page.click('.todo-item')
    await page.waitForTimeout(900)
  }
  const afterTodo = page.url()
  console.log('nav:', JSON.stringify({ quick, afterQuick, afterTodo }))
  await context.close()
}

await browser.close()
console.log('CONSOLE_ERRORS:', errors.length)
errors.slice(0, 20).forEach(e => console.log(e))
