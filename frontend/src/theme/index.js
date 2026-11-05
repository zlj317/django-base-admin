/**
 * 主题系统：明暗模式 + 多主题色
 * 统一把主题色写入 CSS 变量，同时驱动 Element Plus、Arco Design 与自研样式，
 * 保证表格、弹窗、图表、暗色边框都跟随主题，避免页面里出现硬编码颜色。
 * 依赖：仅 Vue 的 reactive / watch；不引入 Element Plus / Arco 的运行时，只写它们的 CSS 变量。
 * 被谁使用：src/main.js 在 createApp 之前调用 initTheme()；src/components/ThemeSwitch.vue 读取 themeState
 *           并调用 setMode / setPalette 完成用户切换。
 * 设计约定：
 *   1) 状态只有"明暗模式 + 配色 key"两个维度，全部集中在 themeState，各页面不各自维护副本；
 *   2) 换肤不靠重渲染，而是改写 <html>/<body> 的属性与根节点 CSS 变量，
 *      因此切换几乎零成本，Element Plus、Arco、自研样式与 SVG 图表会在同一帧跟随；
 *   3) 状态变化统一由文件末尾的 watch 负责"持久化 + 重新应用"，调用方只改状态，不手动调 applyTheme。
 */
/* reactive：让 themeState 能被模板直接绑定（ThemeSwitch.vue 读取 themeState.mode / palette）；
   watch：把"状态变化 → 写 localStorage + 重算变量"这一副作用集中到一处，避免在每个 setter 里重复实现。 */
import { reactive, watch } from 'vue'

/* localStorage 键名，值形如 {"mode":"dark","palette":"teal"}。
   键名保持稳定（不随版本变化），避免升级后老用户的主题偏好凭空丢失。 */
const STORAGE_KEY = 'app-theme'  // 本地持久化键

/** 可选主题色方案：主色 + 图表色板 + 展示名 */
/* 配色白名单：新增主题只需在此追加一项——设置面板（ThemeSwitch.vue）与持久化校验
   都以本数组为准，因此不要在别处硬编码配色 key。
   字段含义：
   - key    ：稳定标识，会写进 localStorage 与 <html data-theme>；改名会导致老用户配置失效；
   - name   ：设置面板展示的中文名，仅用于 UI；
   - primary：主色，applyPalette 据此推导 Element Plus / Arco / 自研的全部梯度；
   - charts ：6 色图表色板，第一色固定与 primary 相同，保证图表主系列与界面主色一致。 */
export const PALETTES = [
  /* 深海蓝：默认配色，与 tokens.css 的 :root 默认值完全一致（JS 未执行时首帧也不会闪色） */
  {
    key: 'blue',
    name: '深海蓝',
    primary: '#165dff',
    charts: ['#165dff', '#14c9c9', '#ff7d00', '#722ed1', '#00b42a', '#f53f3f']
  },
  /* 青碧绿：偏冷的高饱和绿松石色，图表里用作与蓝色对比的系列色 */
  {
    key: 'teal',
    name: '青碧绿',
    primary: '#0fc6c2',
    charts: ['#0fc6c2', '#165dff', '#ffb400', '#722ed1', '#00b42a', '#f53f3f']
  },
  /* 幻夜紫：低明度高饱和，适合长时间浏览，暗色模式下观感最协调 */
  {
    key: 'purple',
    name: '幻夜紫',
    primary: '#722ed1',
    charts: ['#722ed1', '#f5319d', '#14c9c9', '#ff7d00', '#165dff', '#00b42a']
  },
  /* 活力橙：暖色系，用于需要强调"活跃/增长"的场景 */
  {
    key: 'orange',
    name: '活力橙',
    primary: '#ff7d00',
    charts: ['#ff7d00', '#ffb400', '#165dff', '#14c9c9', '#722ed1', '#f53f3f']
  },
  /* 玫瑰红：品红主色，视觉冲击最强，适合品牌化展示 */
  {
    key: 'rose',
    name: '玫瑰红',
    primary: '#f5319d',
    charts: ['#f5319d', '#722ed1', '#ff7d00', '#14c9c9', '#165dff', '#00b42a']
  }
]

/* 当前主题状态：全局唯一数据源，视图层只读，修改只能走 setMode / setPalette。
   用 reactive 而非 ref：模板里可直接写 themeState.mode，不必到处补 .value。
   默认值必须与 tokens.css 的 :root 保持一致（light + blue），否则 initTheme 之前的第一帧会闪另一套配色；
   真实初值由 initTheme() 里的 restore() 从 localStorage 覆盖。 */
export const themeState = reactive({
  /* 明暗模式，取值只有 'light' | 'dark'；setMode 会把非法入参归一化为 light */
  mode: 'light',  // light | dark
  /* 当前配色 key，必须存在于 PALETTES；由 setPalette / restore 校验后才写入 */
  palette: 'blue'
})

/** 十六进制颜色转 RGB 数组 */
/* 用途：mix() 做通道级线性插值，以及拼 rgba() 时需要的 "r, g, b" 文本。
   入参只来自本文件内的常量色（#rgb / #rrggbb），因此不做非法输入校验。 */
function hexToRgb(hex) {
  /* 去掉前缀 #，统一按"无 # 的数字串"处理 */
  const value = hex.replace('#', '')
  /* 3 位缩写（#abc）先展开成 6 位（#aabbcc），否则后面按两位切片取不到有效字节 */
  const full = value.length === 3 ? value.split('').map(c => c + c).join('') : value
  /* 返回 [r, g, b]，按顺序对应 RR / GG / BB；既供 mix() 逐通道插值，也供 rgb()/rgba() 拼接 */
  return [
    parseInt(full.slice(0, 2), 16),
    parseInt(full.slice(2, 4), 16),
    parseInt(full.slice(4, 6), 16)
  ]
}

/** 颜色混合：weight 表示向 target 靠拢的比例（0~1） */
/* 这是整套主题梯度的核心：Element Plus 的 light-N、Arco 的 primary-N、自研的 soft / border
   全部由"主色向底色或黑色按比例插值"得到，因此任意主色都能自动生成协调的深浅档位。 */
function mix(color, target, weight) {
  /* 两个颜色先转成 [r, g, b]，后面按通道逐一插值 */
  const source = hexToRgb(color)
  const dest = hexToRgb(target)
  /* 把比例夹在 0~1：调用方传入的 level/10 等系数理论上已在范围内，夹一下可防手误越界 */
  const ratio = Math.min(Math.max(weight, 0), 1)
  /* 线性插值：source*(1-ratio) + dest*ratio，四舍五入成整数通道，避免输出小数 rgb 值 */
  const values = source.map((item, index) => Math.round(item * (1 - ratio) + dest[index] * ratio))
  /* 直接用 rgb() 字符串返回，省去再写一段 RGB→HEX 的转换 */
  return `rgb(${values.join(', ')})`
}

/** 按 key 取主题色方案，找不到时回退到第一套 */
/* 必须兜底而不能返回 undefined：localStorage 里可能残留已删除的配色 key（版本回滚等场景），
   若直接返回 undefined，applyPalette 读 palette.primary 时会抛错，主题初始化整体失败。 */
function getPalette(key) {
  /* 命中即返回对应配色；未命中时短路到 PALETTES[0]（深海蓝） */
  return PALETTES.find(item => item.key === key) || PALETTES[0]
}

/** 把主题色写入根节点变量：覆盖 Element Plus、Arco 与自研变量 */
/* 参数：palette 为 PALETTES 中的一项；dark 表示当前是否暗色。
   写入顺序为 Element Plus → Arco → 自研 --brand-* / --chart-*；四段都写在同一元素的行内 style 上，
   越晚写入的同名变量覆盖越早的，但四段变量互不重名，顺序只影响可读性。
   所有梯度都在 JS 里算好再写入，而不是交给 CSS color-mix，好处是兼容性稳、梯度档位完全可控。 */
function applyPalette(palette, dark) {
  /* 行内 style 的优先级高于任何样式表，因此能覆盖 tokens.css 中 :root 的默认值 */
  const root = document.documentElement  // 变量统一挂在根节点
  /* 浅色梯度的混合终点：暗色模式向深灰 #141414 靠拢（而不是纯黑，避免浅色档变成脏灰）；
     亮色模式向纯白靠拢。整套 light-N / primary-N 的浅色档都由它决定观感 */
  const base = dark ? '#141414' : '#ffffff'  // 暗色下浅色梯度向深底靠拢

  /* ---------- 第一段：Element Plus ---------- */
  root.style.setProperty('--el-color-primary', palette.primary)  // Element Plus 主色
  /* 只生成 Element Plus 实际会用到的 3 / 5 / 7 / 8 / 9 档浅色梯度（4、6 档官方未定义，跳过以免产生无用变量）；
     level 越大越接近底色，因此直接把 level/10 作为向 base 的混合比例 */
  ;[3, 5, 7, 8, 9].forEach(level => {
    root.style.setProperty(`--el-color-primary-light-${level}`, mix(palette.primary, base, level / 10))
  })
  /* 深色档：向纯黑混合 20%，用于按下态或需要加深的描边 */
  root.style.setProperty('--el-color-primary-dark-2', mix(palette.primary, '#000000', 0.2))

  /* ---------- 第二段：Arco Design ---------- */
  // Arco Design 主色梯度：1 最浅，6 为主色，10 最深
  /* 1~5 是比主色更浅的档位：离 6 越远越接近底色，因此用 (6-level)/6 作为向 base 的混合比例 */
  ;[1, 2, 3, 4, 5].forEach(level => {
    root.style.setProperty(`--primary-${level}`, mix(palette.primary, base, (6 - level) / 6))
  })
  /* 6 档必须等于主色本身，Arco 组件把它当作品牌主色使用 */
  root.style.setProperty('--primary-6', palette.primary)
  /* 7~10 是比主色更深的档位：用 (level-6)/12 向黑靠拢；系数取 12 而非 4，是为了让最深的 10 档不至于发黑 */
  ;[7, 8, 9, 10].forEach(level => {
    root.style.setProperty(`--primary-${level}`, mix(palette.primary, '#000000', (level - 6) / 12))
  })

  /* ---------- 第三段：自研 --brand-* ---------- */
  // 自研组件与业务页面使用的主色变量
  /* 先取一次 RGB 三元组，供 --brand-primary-rgb 与 glow 的 rgba() 复用，避免重复解析字符串 */
  const rgb = hexToRgb(palette.primary)
  /* 与 Element Plus / Arco 主色同步，供 index.css 与各页面样式引用 */
  root.style.setProperty('--brand-primary', palette.primary)
  /* "r, g, b" 文本，供 rgba(var(--brand-primary-rgb), 透明度) 这类写法拼接半透明色 */
  root.style.setProperty('--brand-primary-rgb', rgb.join(', '))
  /* 悬停深色：向黑 18%，用于需要实色反馈的 hover/active */
  root.style.setProperty('--brand-primary-hover', mix(palette.primary, '#000000', 0.18))
  /* 浅底：暗色 0.82 / 亮色 0.9 向底色混合；暗色比例略小，避免浅底在深色底上显得发灰脏 */
  root.style.setProperty('--brand-primary-soft', mix(palette.primary, base, dark ? 0.82 : 0.9))
  /* 描边色：暗色 0.62 / 亮色 0.68，比浅底更靠近主色，保证边框在两种模式下都清晰可见 */
  root.style.setProperty('--brand-primary-border', mix(palette.primary, base, dark ? 0.62 : 0.68))
  /* 主按钮渐变：终点固定向白混合 22%（不随暗色反转），以保留按钮"上亮下暗"的立体感 */
  root.style.setProperty('--brand-gradient', `linear-gradient(135deg, ${palette.primary} 0%, ${mix(palette.primary, '#ffffff', 0.22)} 100%)`)
  /* 光晕：暗色用 0.35 的高透明度（深底上才看得见），亮色用 0.28 */
  root.style.setProperty('--brand-glow', `rgba(${rgb.join(', ')}, ${dark ? 0.35 : 0.28})`)

  /* ---------- 第四段：图表色板 ---------- */
  // 图表配色：SVG 中直接引用这些变量即可跟随主题
  /* index 从 0 开始，而变量名从 --chart-1 开始，因此 +1 与 tokens.css 的命名对齐 */
  palette.charts.forEach((color, index) => {
    root.style.setProperty(`--chart-${index + 1}`, color)
  })
}

/** 应用当前主题：模式 + 主题色 + 第三方库的暗色标记 */
/* 这是"状态 → DOM"的唯一出口：先切属性/类名，再写变量。
   先属性后变量的顺序是有意的——属性切换的瞬间，部分第三方组件会立刻读取变量，
   若变量还是旧的，会出现一帧"属性已暗但颜色仍亮"的闪动。 */
export function applyTheme() {
  /* 只算一次布尔值，供后面的类名、Arco 属性与梯度计算复用，防止读取过程中状态变化导致前后不一致 */
  const dark = themeState.mode === 'dark'
  /* 取配色对象：非法 key 会在 getPalette 内回退到默认配色，这里无需再判空 */
  const palette = getPalette(themeState.palette)
  /* 缓存根节点引用，避免下面多次查询 document.documentElement */
  const root = document.documentElement

  /* 切换 html.dark：tokens.css 的暗色令牌与 Element Plus 内置暗色方案都以该类名为开关；
     用 toggle 而不是 add/remove，重复调用也保持幂等 */
  root.classList.toggle('dark', dark)  // Element Plus 暗色主题依赖 html.dark
  /* 把当前配色 key 挂到 data-theme，便于用 CSS 属性选择器按配色做微调，也方便在 DevTools 中确认当前主题 */
  root.dataset.theme = palette.key  // 便于按主题色做额外微调
  /* Arco 的暗色标记约定挂在 body 的 arco-theme 属性上（不是 html），写错位置会导致 Arco 组件不换肤 */
  document.body.setAttribute('arco-theme', dark ? 'dark' : 'light')  // Arco 暗色标记

  /* 属性就位后再写变量，保证所有组件在同一帧读到一致的新配色 */
  applyPalette(palette, dark)
}

/** 切换明暗模式 */
/* 归一化处理：只有 'dark' 进入暗色，其余（'light'、'auto'、拼写错误、undefined）一律落回 light，
   避免非法值被写进状态后持久化成脏数据；持久化与应用由末尾的 watch 统一完成。 */
export function setMode(mode) {
  themeState.mode = mode === 'dark' ? 'dark' : 'light'
}

/** 切换主题色 */
/* 白名单校验：只接受 PALETTES 中存在的 key；非法 key 静默忽略（例如从旧版缓存里读到已删除的配色），
   这样不会把不存在的配色写进状态，也避免 ThemeSwitch 的选中态错乱。 */
export function setPalette(key) {
  if (PALETTES.some(item => item.key === key)) {
    themeState.palette = key
  }
}

/** 在明暗模式之间切换 */
/* 只需取反后交给 setMode，归一化逻辑集中在一处，不会出现两个函数各写一套判断 */
export function toggleMode() {
  setMode(themeState.mode === 'dark' ? 'light' : 'dark')
}

/** 从本地缓存恢复主题，并在变化时写回 */
/* 只读取不应用：应用动作由 initTheme 统一在恢复之后执行一次，
   这样不会出现"先渲染默认蓝色、再跳到用户配色"的闪变。 */
function restore() {
  /* localStorage 可能被浏览器禁用、值也可能被手工改成非法 JSON，因此整段包在 try/catch 中 */
  try {
    /* 读不到时兜底 '{}'，避免 JSON.parse(null) 抛错 */
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}')
    /* 模式做白名单校验：缓存里可能是旧版本写下的 'auto' 或其他历史值 */
    if (saved.mode === 'dark' || saved.mode === 'light') themeState.mode = saved.mode
    /* 配色做白名单校验：防止缓存指向已删除的 PALETTES 项，导致 applyPalette 拿不到主色 */
    if (PALETTES.some(item => item.key === saved.palette)) themeState.palette = saved.palette
  } catch (e) {
    // 缓存损坏时忽略，使用默认主题
    /* 这里是刻意空捕获：主题只是外观偏好，读失败不应阻断应用启动，保持 themeState 的默认值即可 */
  }
}

/* 统一副作用：themeState 任意字段变化 → 写回 localStorage 并重新应用主题。
   监听整个对象而不是分别监听两个字段，日后新增主题维度（如圆角风格）时不必再补一段 watch。
   不做防抖：切换由用户手动触发、频率极低，立即生效比节流更重要。 */
watch(
  themeState,
  value => {
    /* 只持久化两个业务字段，不序列化整个对象，避免把将来的内部派生字段写进缓存 */
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ mode: value.mode, palette: value.palette }))
    /* 状态变化后立即重算变量，UI 在同一帧更新 */
    applyTheme()
  },
  /* deep 是必需的：themeState 是对象，浅监听只有在整体被替换时才会触发，而 setMode/setPalette 都是改属性 */
  { deep: true }
)

/** 初始化：先恢复缓存再应用，避免首屏闪烁 */
/* 调用时机：main.js 在 createApp 之前调用（见 main.js 中的说明），越早写属性越能避免"先白后黑"的闪屏。
   顺序不能颠倒：若先 applyTheme 再 restore，会先按默认主题渲染一帧，再跳到用户主题。 */
export function initTheme() {
  /* 第一步：从 localStorage 覆盖默认状态 */
  restore()
  /* 第二步：把最终状态一次性写入 DOM 与 CSS 变量 */
  applyTheme()
}
