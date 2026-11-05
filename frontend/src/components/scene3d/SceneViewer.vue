<!--
  文件级说明：
  职责：3D 场景渲染器（three.js 按需加载），负责模型占位几何、灯光、网格、标签、点击拾取、巡检漫游与主题跟随。
  依赖：three（动态 import，首屏不加载）、three/examples 的 OrbitControls、@/theme（明暗与配色状态）。
  被谁使用：场景编辑器、只读查看页、分享页、巡检播放。
  设计约定：
  1) 本项目暂无真实 glb 文件，模型按“资源名称/对象名称”规则生成占位几何体，保证页面可交互；
  2) 颜色全部从 CSS 令牌读取（--brand-*、--chart-*、--app-*），主题切换时重建场景，避免写死色值；
  3) 仅动态 import three，未打开 3D 页面时不增加首屏包体。
-->
<template>
  <!-- 渲染容器：父级需给定高度；canvas 由 three 动态插入 -->
  <div ref="host" class="scene-viewer">
    <!-- 加载态：three 按需加载与场景构建期间展示 -->
    <div v-if="!ready" class="sv-loading">
      <el-icon class="is-loading" :size="20"><Loading /></el-icon>
      <span>3D 引擎加载中…</span>
    </div>
    <!-- 空态：场景没有对象时给出操作引导 -->
    <div v-if="ready && !objects.length" class="sv-empty">
      <el-icon :size="24"><Box /></el-icon>
      <span>场景暂无对象，请先在编辑器添加模型</span>
    </div>
    <!-- 交互提示：仅可交互模式展示，说明鼠标操作方式 -->
    <div v-if="ready && interactive" class="sv-tip">左键旋转 · 滚轮缩放 · 右键平移 · 点击对象查看</div>
  </div>
</template>

<script setup>
// Vue API：ref 保存容器、watch 监听数据与主题、onMounted/onBeforeUnmount 管理生命周期
import { ref, watch, onMounted, onBeforeUnmount, shallowRef } from 'vue'
// 主题状态：切换明暗或配色时重建材质与网格颜色
import { themeState } from '@/theme'
// Element Plus 图标：加载与空态
import { Loading, Box } from '@element-plus/icons-vue'

// 组件参数定义
const props = defineProps({
  objects: { type: Array, default: () => [] }, // 场景对象数组（position/rotation/scale/resource_name）
  config: { type: Object, default: () => ({}) }, // 场景全局配置（相机、背景）
  selectedId: { type: [Number, String], default: null }, // 当前选中对象主键
  wayPoints: { type: Array, default: () => [] }, // 巡检路径点位
  playing: { type: Boolean, default: false }, // 是否播放巡检漫游
  speed: { type: Number, default: 1 }, // 漫游速度（点位/秒）
  interactive: { type: Boolean, default: true } // 是否启用鼠标控制
})
// 向外抛出的事件：对象点击、引擎就绪
const emit = defineEmits(['select', 'ready'])

// DOM 引用与运行状态
const host = ref(null) // 渲染容器
const ready = ref(false) // three 是否就绪
const THREE = shallowRef(null) // three 命名空间（浅响应，避免深度代理影响性能）
const runtime = { renderer: null, scene: null, camera: null, controls: null, group: null, labels: null, raycaster: null, observer: null, frame: 0, clock: null, meshes: [], patrolIndex: 0, patrolT: 0, disposed: false } // 非响应式运行时对象，避免 Vue 代理 WebGL 对象

// 读取 CSS 令牌值，令牌缺失时回退到传入默认值
function token(name, fallback) {
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim() // 从根节点读取
  return value || fallback // 空值时用默认色
}

// 生成对象占位几何体尺寸：按资源名称/对象名称匹配常见机房设备
function shapeOf(obj) {
  const name = `${obj.resource_name || ''}${obj.object_name || ''}` // 合并两个名称提高命中率
  if (/机柜|cabinet/i.test(name)) return { w: 1.6, h: 3.2, d: 1.2, type: 'box' } // 42U 机柜
  if (/服务器|server/i.test(name)) return { w: 0.55, h: 0.14, d: 0.8, type: 'box' } // 2U 服务器
  if (/空调|air|ac_/i.test(name)) return { w: 1.2, h: 2.4, d: 1.2, type: 'box' } // 精密空调
  if (/UPS|电源/i.test(name)) return { w: 1.2, h: 2.2, d: 1.2, type: 'box' } // UPS 主机
  if (/密集架|档案|archive/i.test(name)) return { w: 2.4, h: 2.2, d: 0.9, type: 'box' } // 档案密集架
  if (/传感器|sensor/i.test(name)) return { w: 0.5, h: 0.5, d: 0.5, type: 'sphere' } // 吸顶传感器
  return { w: 1, h: 1, d: 1, type: 'box' } // 兜底立方体
}

// 取对象坐标（后端 JSONField 已归一化为 {x,y,z}）
function posOf(obj, key = 'position') {
  const p = obj[key] || {} // 字段缺失时用空对象
  return { x: Number(p.x) || 0, y: Number(p.y) || 0, z: Number(p.z) || 0 } // 全部转数字并兜底 0
}

// 创建文本标签精灵：用 CanvasTexture，避免额外依赖字体加载器
function makeLabel(text, color) {
  const canvas = document.createElement('canvas') // 离屏画布
  const ctx = canvas.getContext('2d') // 2D 上下文
  const pad = 18 // 左右内边距
  const fontSize = 40 // 字体大小（画布像素）
  ctx.font = `600 ${fontSize}px "Microsoft YaHei", sans-serif` // 与系统字体保持一致
  const width = Math.ceil(ctx.measureText(text).width) + pad * 2 // 按文字宽度自适应
  canvas.width = width // 设置画布宽
  canvas.height = 68 // 设置画布高
  const bg = token('--app-surface', '#ffffff') // 标签底色跟随主题
  const border = token('--app-border', '#e5e8ef') // 标签描边
  const c = canvas.getContext('2d') // 尺寸变化后重新获取上下文
  c.clearRect(0, 0, canvas.width, canvas.height) // 清空画布
  c.fillStyle = bg // 填充底色
  c.strokeStyle = border // 描边色
  c.lineWidth = 2 // 细描边
  c.beginPath() // 开始圆角矩形路径
  c.roundRect(1, 1, canvas.width - 2, canvas.height - 2, 12) // 圆角矩形
  c.fill() // 填充
  c.stroke() // 描边
  c.font = `600 ${fontSize}px "Microsoft YaHei", sans-serif` // 再次设置字体（重置上下文后需重设）
  c.fillStyle = color // 文字色
  c.textAlign = 'center' // 水平居中
  c.textBaseline = 'middle' // 垂直居中
  c.fillText(text, canvas.width / 2, canvas.height / 2) // 绘制文字
  const texture = new THREE.value.CanvasTexture(canvas) // 画布转纹理
  texture.needsUpdate = true // 标记更新
  const material = new THREE.value.SpriteMaterial({ map: texture, transparent: true, depthWrite: false }) // 精灵材质
  const sprite = new THREE.value.Sprite(material) // 创建精灵
  sprite.scale.set(canvas.width / 170, canvas.height / 170, 1) // 世界单位缩放（约 0.4 高，避免标签过大互相遮挡）
  return sprite // 返回精灵
}

// 清理场景内所有几何体/材质/纹理，防止切换主题时显存泄漏
function disposeGroup(group) {
  if (!group) return // 空对象直接返回
  group.traverse(child => {
    if (child.geometry) child.geometry.dispose() // 释放几何体
    if (child.material) {
      const mats = Array.isArray(child.material) ? child.material : [child.material] // 兼容多材质
      mats.forEach(m => {
        if (m.map) m.map.dispose() // 释放纹理（标签贴图）
        m.dispose() // 释放材质
      })
    }
  })
  group.clear() // 摘除子节点，便于重新构建
}

// 构建场景内容：地面、网格、灯光、对象与标签、巡检点位
function buildContent() {
  const T = THREE.value // three 命名空间
  const rt = runtime // 运行时引用
  disposeGroup(rt.group) // 先清理旧内容
  if (!rt.group || !rt.scene) return // 未初始化时跳过
  const bg = token('--app-bg', '#f2f4f8') // 背景色跟随页面底色
  rt.scene.background = new T.Color(bg) // 设置背景
  rt.renderer.setClearColor(bg, 1) // 同步清屏色

  // 灯光：环境光 + 两盏方向光，保证机柜正面与顶部都有层次
  const ambient = new T.AmbientLight(0xffffff, 0.75) // 环境光
  const key = new T.DirectionalLight(0xffffff, 1.1) // 主光
  key.position.set(8, 12, 6) // 右上前方，形成明暗面
  const fill = new T.DirectionalLight(0xffffff, 0.5) // 补光
  fill.position.set(-8, 6, -8) // 左下后方
  rt.group.add(ambient, key, fill) // 加入场景组

  // 地面：大平面 + 网格，网格色取主题边框令牌
  const surface = new T.Mesh(
    new T.PlaneGeometry(40, 40), // 40×40 地面
    new T.MeshStandardMaterial({ color: token('--app-surface-2', '#f7f8fa'), roughness: 0.95, metalness: 0.05 }) // 哑光表面
  )
  surface.rotation.x = -Math.PI / 2 // 平放
  surface.position.y = -0.01 // 略低于网格，避免闪烁
  const grid = new T.GridHelper(40, 40, token('--app-border-strong', '#d4d9e3'), token('--app-border-light', '#eef1f6')) // 网格辅助线
  rt.group.add(surface, grid) // 加入场景

  // 调色板：取图表色板 1~6，供对象循环着色
  const palette = [1, 2, 3, 4, 5, 6].map(i => token(`--chart-${i}`, '#165dff'))
  rt.meshes = [] // 重置拾取集合

  // 逐对象创建占位模型
  props.objects.forEach((obj, objIndex) => {
    const shape = shapeOf(obj) // 根据名称确定尺寸/形状
    let geometry // 几何体
    if (shape.type === 'sphere') geometry = new T.SphereGeometry(shape.w / 2, 24, 18) // 传感器球体
    else geometry = new T.BoxGeometry(shape.w, shape.h, shape.d) // 设备立方体
    const baseColor = palette[objIndex % palette.length] // 按顺序循环取色
    const selected = String(props.selectedId) === String(obj.id) // 是否为当前选中
    const material = new T.MeshStandardMaterial({
      color: baseColor, // 主体颜色
      roughness: 0.55, // 轻微反光
      metalness: 0.25, // 稍带金属质感
      emissive: selected ? baseColor : 0x000000, // 选中对象自发光
      emissiveIntensity: selected ? 0.55 : 0 // 选中高亮强度
    })
    const mesh = new T.Mesh(geometry, material) // 创建网格
    const p = posOf(obj) // 位置
    const s = posOf(obj, 'scale') // 缩放
    const r = posOf(obj, 'rotation') // 旋转（弧度）
    mesh.position.set(p.x, p.y + shape.h / 2 * (s.y || 1), p.z) // 底部贴地，避免模型悬空
    mesh.scale.set(s.x || 1, s.y || 1, s.z || 1) // 应用缩放
    mesh.rotation.set(r.x, r.y, r.z) // 应用旋转
    mesh.userData.objectId = obj.id // 记录业务主键，供点击拾取
    mesh.userData.objectName = obj.object_name // 记录名称
    rt.group.add(mesh) // 加入场景组
    rt.meshes.push(mesh) // 加入拾取集合

    // 标签：默认显示，文字优先取 label_text，其次对象名称
    if (obj.is_show_label) {
      const color = token('--app-text-1', '#1d2129') // 文字色
      const sprite = makeLabel(obj.label_text || obj.object_name || '', color) // 生成标签
      sprite.position.set(p.x, p.y + shape.h * (s.y || 1) + 0.45 + (objIndex % 3) * 0.42, p.z) // 放在模型顶部，按序号错层减少标签重叠
      rt.group.add(sprite) // 加入场景
    }
  })

  // 巡检点位：小体积高亮球，便于确认漫游路径
  if (props.wayPoints.length) {
    const wpColor = token('--chart-2', '#14c9c9') // 路径点颜色
    props.wayPoints.forEach(wp => {
      const dot = new T.Mesh(new T.SphereGeometry(0.12, 12, 10), new T.MeshBasicMaterial({ color: wpColor })) // 小球
      dot.position.set(Number(wp.x) || 0, Number(wp.y) || 0, Number(wp.z) || 0) // 点位坐标
      rt.group.add(dot) // 加入场景
    })
  }

  // 相机初始化：优先使用场景配置中的相机参数，否则用默认俯视视角
  const cam = props.config && props.config.camera ? props.config.camera : {} // 场景配置相机段
  const cp = cam.position || { x: 9, y: 7, z: 11 } // 默认相机位
  const ct = cam.target || { x: 0, y: 1.2, z: 0 } // 默认观察点
  rt.camera.position.set(Number(cp.x) || 9, Number(cp.y) || 7, Number(cp.z) || 11) // 设置相机
  if (rt.controls) {
    rt.controls.target.set(Number(ct.x) || 0, Number(ct.y) || 1.2, Number(ct.z) || 0) // 设置控制目标
    rt.controls.update() // 同步控制状态
  }
}

// 启动渲染循环：处理交互、巡检漫游与 resize
function startLoop() {
  const rt = runtime // 运行时引用
  const T = THREE.value // three 命名空间
  const loop = () => {
    if (rt.disposed) return // 组件已卸载
    rt.frame = requestAnimationFrame(loop) // 持续排队下一帧
    const width = host.value ? host.value.clientWidth : 0 // 容器宽
    const height = host.value ? host.value.clientHeight : 0 // 容器高
    if (width && height && (rt.renderer.domElement.width !== Math.floor(width * rt.renderer.getPixelRatio()) || rt.renderer.domElement.height !== Math.floor(height * rt.renderer.getPixelRatio()))) {
      rt.renderer.setSize(width, height, false) // 尺寸变化时同步画布
      rt.camera.aspect = width / height // 同步相机比例
      rt.camera.updateProjectionMatrix() // 重算投影矩阵
    }
    // 巡检漫游：按 speed 在相邻点位之间插值相机位置与朝向
    if (props.playing && props.wayPoints.length > 1) {
      const now = rt.clock.getElapsedTime() // 当前时间
      const delta = Math.min(now - rt.patrolT, 0.5) // 单帧最大步长，避免切页后跳变
      rt.patrolT = now // 记录时间
      rt.patrolProgress = (rt.patrolProgress || 0) + delta * Math.max(props.speed, 0.1) // 进度按速度推进
      if (rt.patrolProgress >= 1) {
        rt.patrolProgress = 0 // 到达下一段
        rt.patrolIndex = (rt.patrolIndex + 1) % (props.wayPoints.length - 1) // 循环到下一段
      }
      const from = props.wayPoints[rt.patrolIndex] // 起点
      const to = props.wayPoints[(rt.patrolIndex + 1) % props.wayPoints.length] // 终点
      const k = rt.patrolProgress // 插值系数
      rt.camera.position.set(
        (Number(from.x) || 0) * (1 - k) + (Number(to.x) || 0) * k,
        (Number(from.y) || 0) * (1 - k) + (Number(to.y) || 0) * k,
        (Number(from.z) || 0) * (1 - k) + (Number(to.z) || 0) * k
      ) // 位置插值
      const laFrom = from.lookAt || { x: 0, y: 1, z: 0 } // 起点朝向
      const laTo = to.lookAt || { x: 0, y: 1, z: 0 } // 终点朝向
      rt.camera.lookAt(
        (Number(laFrom.x) || 0) * (1 - k) + (Number(laTo.x) || 0) * k,
        (Number(laFrom.y) || 0) * (1 - k) + (Number(laTo.y) || 0) * k,
        (Number(laFrom.z) || 0) * (1 - k) + (Number(laTo.z) || 0) * k
      ) // 朝向插值
    } else if (rt.controls) {
      rt.controls.update() // 普通模式交给 OrbitControls
    }
    rt.renderer.render(rt.scene, rt.camera) // 渲染一帧
  }
  rt.clock = new T.Clock() // 计时器
  rt.patrolT = 0 // 初始时间
  rt.patrolProgress = 0 // 初始进度
  rt.patrolIndex = 0 // 初始段索引
  loop() // 启动
}

// 点击拾取：射线检测命中的模型并抛给父组件
function onPointerDown(event) {
  if (!props.interactive || !runtime.raycaster) return // 只读或未初始化时不处理
  const rect = host.value.getBoundingClientRect() // 画布区域
  const pointer = new THREE.value.Vector2(
    ((event.clientX - rect.left) / rect.width) * 2 - 1,
    -((event.clientY - rect.top) / rect.height) * 2 + 1
  ) // 归一化设备坐标
  runtime.raycaster.setFromCamera(pointer, runtime.camera) // 从相机发射射线
  const hits = runtime.raycaster.intersectObjects(runtime.meshes, false) // 与模型求交
  if (hits.length) {
    const mesh = hits[0].object // 最近的一个
    emit('select', { id: mesh.userData.objectId, object_name: mesh.userData.objectName }) // 抛出业务对象
  }
}

// 初始化引擎：动态加载 three 与控制插件
async function init() {
  try {
    const mod = await import('three') // 按需加载 three，不进首屏包
    const ctrl = await import('three/examples/jsm/controls/OrbitControls.js') // 轨道控制插件
    THREE.value = mod // 缓存命名空间
    const T = mod // 局部别名
    const rt = runtime // 运行时引用

    rt.scene = new T.Scene() // 场景
    rt.camera = new T.PerspectiveCamera(45, 1, 0.1, 200) // 透视相机，宽高比先设 1，循环中修正
    rt.renderer = new T.WebGLRenderer({ antialias: true, alpha: false, powerPreference: 'high-performance' }) // WebGL 渲染器
    rt.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2)) // 限制像素比，避免 4K 屏过载
    rt.renderer.outputColorSpace = T.SRGBColorSpace // 正确的颜色空间
    rt.renderer.shadowMap.enabled = false // 关闭阴影，降低移动端/低配设备开销
    host.value.appendChild(rt.renderer.domElement) // 挂载画布

    rt.controls = new ctrl.OrbitControls(rt.camera, rt.renderer.domElement) // 轨道控制
    rt.controls.enableDamping = true // 惯性阻尼
    rt.controls.dampingFactor = 0.08 // 阻尼系数
    rt.controls.minDistance = 2 // 最近缩放距离
    rt.controls.maxDistance = 40 // 最远缩放距离
    rt.controls.maxPolarAngle = Math.PI / 2.05 // 禁止钻到地面以下
    rt.controls.enableRotate = props.interactive // 只读模式禁用旋转
    rt.controls.enablePan = props.interactive // 只读模式禁用平移
    rt.controls.enableZoom = props.interactive // 只读模式禁用缩放

    rt.group = new T.Group() // 统一管理可销毁内容
    rt.scene.add(rt.group) // 加入场景
    rt.raycaster = new T.Raycaster() // 拾取射线
    rt.renderer.domElement.addEventListener('pointerdown', onPointerDown) // 绑定点击

    buildContent() // 构建内容
    startLoop() // 启动渲染
    ready.value = true // 标记就绪
    emit('ready') // 通知父组件
  } catch (err) {
    // 引擎加载失败时给出可读提示，避免整页白屏
    ready.value = true // 关闭加载动画
    console.error('3D 引擎加载失败', err) // 保留排查信息
  }
}

// 监听对象数组/选中态/巡检参数变化：重建内容（数据量不大，重建比增量 diff 更稳）
watch(() => [props.objects, props.selectedId, props.wayPoints], () => {
  if (ready.value && runtime.scene) buildContent() // 引擎就绪后重绘
}, { deep: true })

// 主题变化：重建材质与背景，保证明暗/五套配色都能跟随令牌
watch(() => [themeState.mode, themeState.palette], () => {
  if (ready.value && runtime.scene) buildContent() // 令牌已由主题系统写入，直接重建
})

// 交互开关变化：同步控制器状态
watch(() => props.interactive, value => {
  if (!runtime.controls) return // 未初始化
  runtime.controls.enableRotate = value // 旋转
  runtime.controls.enablePan = value // 平移
  runtime.controls.enableZoom = value // 缩放
})

// 挂载即初始化
onMounted(init)

// 卸载时彻底释放 GPU 资源，避免页面切换后显存持续增长
onBeforeUnmount(() => {
  runtime.disposed = true // 停止渲染循环
  cancelAnimationFrame(runtime.frame) // 取消未执行的帧
  if (runtime.observer) runtime.observer.disconnect() // 断开尺寸监听
  if (runtime.renderer) {
    runtime.renderer.domElement.removeEventListener('pointerdown', onPointerDown) // 解绑事件
    disposeGroup(runtime.group) // 释放几何与材质
    runtime.renderer.dispose() // 释放渲染器
    runtime.renderer.domElement.remove() // 移除画布
  }
  if (runtime.controls) runtime.controls.dispose() // 释放控制器
})
</script>

<style scoped>
/* 容器铺满父级，父级负责高度 */
.scene-viewer {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 320px;
  overflow: hidden;
  border-radius: var(--app-radius-md);
  background: var(--app-bg);
}
/* three 画布铺满容器 */
.scene-viewer :deep(canvas) {
  display: block;
  width: 100%;
  height: 100%;
}
/* 加载态：居中，文字色跟随后台令牌 */
.sv-loading,
.sv-empty {
  position: absolute;
  inset: 0;
  z-index: 2;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: var(--app-text-3);
  font-size: 13px;
  background: var(--app-surface);
  pointer-events: none;
}
/* 交互提示：左下角浮层 */
.sv-tip {
  position: absolute;
  left: 12px;
  bottom: 10px;
  z-index: 3;
  padding: 4px 10px;
  border: 1px solid var(--app-border-light);
  border-radius: 999px;
  color: var(--app-text-3);
  font-size: 12px;
  background: color-mix(in srgb, var(--app-surface) 86%, transparent);
  pointer-events: none;
}
</style>
