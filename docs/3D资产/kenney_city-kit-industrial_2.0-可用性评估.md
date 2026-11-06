# Kenney City Kit Industrial 2.0 可用性评估

- 评估对象：`docs/3D资产/kenney_city-kit-industrial_2.0`
- 评估目标：能否用于当前项目 3D 可视化模块（`apps/scene3d` + `SceneViewer.vue`）
- 评估方式：只读盘点（文件清单、GLB 结构解析、面数统计、License 核对、现有代码对照），**未修改任何代码与素材**
- 评估日期：2026-11-06
- 结论：**部分使用**——适合做园区/厂房/集装箱机房等“外壳与氛围”，**不适合做机房内部设备**（包内无机柜、服务器、空调、UPS、密集架、传感器）。

---

## 一、包里到底有什么

### 1.1 总体构成

| 项目 | 数值 |
|---|---|
| 文件总数 | 201 个 |
| 总体积 | 10.54 MB |
| 模型数量 | 37 个（每个模型同时提供 FBX / OBJ+MTL / GLB 三种格式） |
| 贴图 | 1 张共用色板图集 `colormap.png`（512×512）+ 3 套配色变体 `variation-a/b/c.png`（512×512） |
| 预览图 | 37 张单模型预览 + 根目录 5 张总览/配色图 |
| 授权文件 | `License.txt`（CC0 1.0） |

各目录体积（实测）：

| 目录 | 文件数 | 体积 |
|---|---|---|
| `Models/FBX format` | 38（37 模型 + 目录项） | 1.91 MB |
| `Models/OBJ format` | 75（37 .obj + 37 .mtl + 目录项） | 3.15 MB |
| `Models/GLB format` | 38（37 .glb + 目录项） | 3.01 MB |
| `Models/Textures` | 3（配色变体） | 0.03 MB |
| `Previews` | 37 张 PNG | 0.08 MB |
| 根目录预览图 | 5 张 PNG | 约 2.25 MB |

### 1.2 格式与材质方式

- **模型格式**：FBX、OBJ（附 MTL）、GLB 2.0（glTF 二进制）。三种格式内容一致，GLB 可直接被 three.js `GLTFLoader` 加载，**不需要格式转换**。
- **贴图**：所有模型共用一张 **512×512 色板图集**（atlas），UV 直接指向图集色块；另提供 `variation-a/b/c` 三套换色贴图（同样 512×512、约 12 KB）。
- **材质**：GLB 内每个模型含 2 个材质 `colormap` / `colormap-specular`，均为 `pbrMetallicRoughness`：
  - `baseColorTexture` 指向外部文件 `Textures/colormap.png`；
  - `metallicFactor = 0.0`，无 roughness/normal/AO 贴图；
  - `doubleSided = true`；
  - 使用 `KHR_texture_transform` 扩展。
- **重要细节**：GLB **没有内嵌贴图**，`images[0].uri = "Textures/colormap.png"`。只上传单个 `.glb` 而不带 `Textures/colormap.png`，前端会渲染成白模/紫黑（贴图 404）。
- **OBJ 面数翻倍**：OBJ 的 `f` 行数量恰好是 GLB 三角面的 2 倍（同一几何按两个材质各导出一次）。统计面数应以 GLB 为准。

### 1.3 分类与代表性文件名

| 分类 | 数量 | 文件（代表） |
|---|---|---|
| 厂房/仓库/办公楼 | 20 | `building-a` … `building-t`（如 `building-a`、`building-b`、`building-c`） |
| 烟囱 | 4 | `chimney-basic`、`chimney-small`、`chimney-medium`、`chimney-large` |
| 储罐 | 2 | `detail-tank`、`detail-tank-large` |
| 集装箱 | 3 | `shipping-container-a`、`shipping-container-b`、`shipping-container-c` |
| 光伏板 | 5 | `solar-panel-flat`、`solar-panel-landscape`、`solar-panel-landscape-group`、`solar-panel-portrait`、`solar-panel-portrait-group` |
| 水塔/风机 | 3 | `water-tower`、`windmill`、`windmill-low` |

> 包内**没有**：机柜、服务器、精密空调、UPS、密集架/档案架、传感器、桥架、防静电地板、门禁、消防设备、摄像头等机房设备。

### 1.4 三角面与体积（GLB 实测）

| 指标 | 数值 |
|---|---|
| 37 个模型三角面合计 | **35,390** |
| 单模型平均 | 956 |
| 最小 | 88（`chimney-basic`） |
| 最大 | 2,422（`building-b`） |
| 面数前 5 | `building-b` 2,422 / `building-q` 2,062 / `building-a` 2,046 / `building-c` 1,928 / `building-r` 1,912 |
| 单模型 GLB 体积 | 8.8 KB（`chimney-basic`）～ 207.1 KB（`building-b`），平均约 81 KB |
| 共用贴图 | 512×512，11.7 KB |

整体属于**极低模**级别：37 个模型全部加载也只有约 3 MB / 3.5 万三角面。

### 1.5 尺寸与坐标（GLB 包围盒实测）

| 模型 | 包围盒（宽×高×深，单位：模型单位） |
|---|---|
| `building-a` | 2.08 × 1.47 × 1.24 |
| `building-b` | 2.08 × 1.47 × 1.26 |
| `shipping-container-a` | 1.38 × 1.29 × 3.05 |
| `detail-tank` | 0.85 × 0.42 × 0.52 |
| `water-tower` | 0.91 × 2.28 × 0.88 |
| `solar-panel-flat` | 0.42 × 0.06 × 0.71 |

- 坐标系：glTF 原生 **Y 轴向上**，模型底部 `min.y ≈ 0`（落地对齐，可直接放到地面）。
- 单位：**不是严格的米制**。集装箱长 3.05 个模型单位，×2 后约 6.1 m，正好接近 20 英尺箱（6.06 m）；而 3 层建筑仅 1.47 个单位高，说明这是 Kenney 一贯的“风格化压缩比例”，**各资产之间比例不严格一致**，接入时必须逐模型按目标尺寸归一化。

---

## 二、授权

`License.txt` 原文要点：

- 许可类型：**Creative Commons Zero（CC0 1.0 Universal）**，即公共领域奉献。
- 可商用：允许个人、教育、商业项目使用。
- 可再分发：CC0 不限制再分发与修改（可随项目、可改色、可合并进产品）。
- 署名：**非强制**，作者仅“希望”署名 `Kenney` 或 `www.kenney.nl`（Support by crediting，this is not a requirement）。
- 建议：在项目 `docs/3D资产/` 保留本 `License.txt`，并在 README/资产说明中附一句“部分 3D 资产来自 Kenney (CC0)”，既是礼貌也便于后续审计。

结论：**授权层面无风险**，可安全用于商业交付。

---

## 三、与当前项目的契合度

### 3.1 项目现状（代码事实）

1. **对象类型是“按名称识别 + 程序化几何占位”**，见 [SceneViewer.vue](file:///d:/other/django-base-admin/frontend/src/components/scene3d/SceneViewer.vue#L63-L72)：
   - `机柜` → 长方体 1.6 × 3.2 × 1.2
   - `服务器` → 长方体 0.55 × 0.14 × 0.8
   - `空调` → 长方体 1.2 × 2.4 × 1.2
   - `UPS/电源` → 长方体 1.2 × 2.2 × 1.2
   - `密集架/档案` → 长方体 2.4 × 2.2 × 0.9
   - `传感器` → 球体 0.5
   - 其它 → 1×1×1 立方体
2. **前端尚未支持 GLTF/GLB**：`frontend/src` 中没有任何 `GLTFLoader` / `DRACOLoader` / `useGLTF` 引用；渲染链路只有 `BoxGeometry` / `SphereGeometry` / `PlaneGeometry`，**加载模型需要新增加载器与异步加载队列**。
3. **模型资源字段已预留**，见 [scene3d/models.py](file:///d:/other/django-base-admin/backend/apps/scene3d/models.py#L95-L118)：`model_code`、`model_type`（model/texture/material/env）、`file_id`（→ `wf_file.id`，0 表示占位）、`triangle_count`、`file_size`、`thumbnail_file_id`。
4. **上传存储方式**，见 [scene3d/views.py](file:///d:/other/django-base-admin/backend/apps/scene3d/views.py#L883-L927)：
   - 落盘目录 `uploads/scene3d/YYYY/MM/<uuid>_原文件名`，同时登记 `wf_file`（`biz_type='scene3d_model'`）；
   - 扩展名白名单：`.glb/.gltf/.jpg/.jpeg/.png/.webp/.hdr`，**不含 `.bin`**；
   - 单文件上限 50 MB；
   - 预览接口返回 `/uploads/...` 相对 URL。
5. **Django 侧未配置 `MEDIA_URL` / `MEDIA_ROOT`，`config/urls.py` 也没有 `/uploads/` 静态路由**；当前上传物需由 Nginx 或额外路由提供访问（部署时需确认，否则 GLB 与贴图都取不到）。

### 3.2 逐条对应现有对象类型

| 项目对象类型 | 包内可用资产 | 结论 |
|---|---|---|
| 机柜（42U，1.6×3.2×1.2 占位） | 无。`shipping-container-*` 只能当“集装箱机房外壳”，尺寸/结构都不是机柜 | **不可用** |
| 服务器（2U，0.55×0.14×0.8） | 无 | **不可用** |
| 精密空调（1.2×2.4×1.2） | 无。`detail-tank` 是卧式储罐，只能勉强当冷水罐/冷却水箱 | **勉强/不可用** |
| UPS 主机（1.2×2.2×1.2） | 无。`detail-tank` 形态、面板都不符 | **不可用** |
| 密集架/档案架（2.4×2.2×0.9） | 无。`building-*` 只能当库房外壳 | **不可用** |
| 传感器/温湿度探头（球体） | 无 | **不可用** |
| 机房/园区建筑外壳 | `building-a` … `building-t` | **可直接用**（需缩放与统一风格） |
| 集装箱机房/临时机房 | `shipping-container-a/b/c` | **部分可用**（需 ×2 左右缩放） |
| 冷却设施/水系统 | `water-tower`、`detail-tank(-large)` | **部分可用**（冷却塔/储液罐） |
| 园区能源/氛围 | `solar-panel-*`、`windmill(-low)`、`chimney-*` | **部分可用**（纯装饰，无业务绑定价值） |

**核心缺口**：本项目最核心的机房内部设备（机柜、服务器、空调、UPS、密集架、传感器）在包内 **一个都没有**。这是“不建议直接用”的决定性原因。

### 3.3 风格契合度

- Kenney 是典型**低多边形 + 色板图集**的卡通/扁平风格，与当前项目“纯色程序化几何”的简洁风格能共存，但和“数字孪生机房”常见的写实风格差距明显。
- 本项目占位几何本身也做了夸张比例（机柜 3.2 m 高，大于真实 42U 的约 2.0 m），说明项目并不追求严格物理尺寸；这反而降低了“造型不符”的违和感。
- 但机房内部需要“一眼认出是机柜/服务器/空调”，Kenney 的建筑/集装箱形态无法承担这种识别功能。

---

## 四、落地成本

### 4.1 格式与贴图（必须处理）

| 步骤 | 说明 | 成本 |
|---|---|---|
| GLB 直接使用 | 已是 GLB 2.0，`GLTFLoader.load(url)` 即可 | 低 |
| 贴图 sidecar | 37 个 GLB 全部引用 `Textures/colormap.png`；上传链路只允许单文件、且白名单无 `.bin`，不会自动带上贴图目录 | 中：需在入库前把贴图**内嵌进 GLB**（`gltf-transform embed` / `gltfpack -tc`），或改造上传接口支持“模型包” |
| 贴图压缩 | 512×512、11.7 KB，已足够小 | 无需处理 |

**关键风险**：若直接上传仓库里的 `.glb`，前端会因贴图 404 显示白模；必须重新打包（内嵌贴图）后再上传。

### 4.2 缩放与单位统一

- glTF 为 Y-up、底部落地，方向无需转换。
- 单位不统一：建议在加载后按包围盒做“目标尺寸归一化”（例如集装箱目标 6.06 m、水塔目标 12 m），或按资产类别配置 `scale` 基准表。
- 现有 `Scene3dSceneObject.scale` 是 JSON 三轴缩放，可承载归一化系数；但**同一资源被多场景复用时**，建议把归一化写进资源元数据（`remark`/新增字段）或统一在加载器里做，避免每个对象手调。

### 4.3 材质与压缩

- 材质是“图集 + metallic 0 + 双面”，无 PBR 贴图；保留卡通风格即可，无需烘焙。
- 若要并入写实 PBR 场景，需要重新烘焙/改材质，成本高且收益低，**不建议**。
- 体积极小（平均 81 KB），**不需要 Draco/meshopt**；引入 Draco 反而要额外部署 decoder（wasm/js），得不偿失。

### 4.4 前端性能影响

| 指标 | 估算 |
|---|---|
| 单模型 GLB | 8.8–207 KB，平均 81 KB |
| 单场景放 20 个建筑/集装箱 | 约 1.0–2.5 MB（首次，之后浏览器缓存） |
| 三角面 | 单模型 ≤ 2,422；20 个约 2 万，远低于 10 万预算 |
| 贴图 | 1 张 512×512（约 12 KB），共享 |
| 首屏影响 | 小：建议**按需/懒加载 + 缓存 + 视距剔除**；园区级场景可忽略 |

### 4.5 加载链路改造量

当前链路完全未支持模型文件，需要：

1. 引入 `GLTFLoader`（three/examples），封装 `loadModel(fileId/fileUrl)`，带缓存与并发限制；
2. `buildContent` 从“按名称生成 Box/Sphere”改为“有 `file_id` 则加载 GLB，失败或无文件回退占位几何”；
3. 异步加载完成后替换占位体，处理克隆（`SkeletonUtils.clone` 或 `scene.clone(true)`）、材质共享、`dispose()` 释放；
4. 选择/高亮/标签高度改为按模型包围盒计算（当前按占位尺寸写死）；
5. 后端补 `/uploads/` 访问（Nginx 或 Django `static()` 路由），并支持贴图 sidecar 或内嵌 GLB；
6. 可选：上传时自动解析三角面数/包围盒、生成缩略图（当前 `triangle_count` 依赖手工传参）。

粗略工作量：加载器与渲染改造约 **2–4 人日**；资产入库/归一化/打包约 **1–2 人日**（仅做园区外观的前提下）。

---

## 五、明确建议

### 结论：**部分使用（不建议整体采用）**

**可以用的部分（园区/建筑外观层）**

1. `building-a` … `building-t`：园区厂房、仓库、办公楼、机房建筑外壳；
2. `shipping-container-a/b/c`：集装箱机房、临时机房、户外设备舱外观；
3. `water-tower`、`detail-tank(-large)`：冷却塔/水塔、储液罐等水系统设备；
4. `solar-panel-*`、`windmill(-low)`、`chimney-*`：光伏、风机、烟囱等园区氛围装饰。

**不能用的部分（机房内部）**

- 机柜、服务器、精密空调、UPS、密集架、传感器、桥架、地板、门禁、消防、摄像头——包内均无，且形态无法替代。

**替代方案（按优先级）**

1. **自建低模（推荐）**：用 Blender 按项目占位尺寸建 42U 机柜（1.6×3.2×1.2）、2U 服务器、精密空调、UPS、密集架、传感器，导出 GLB + 共用色板贴图。尺寸精确、面数可控、授权完全自主。
2. **Quaternius（CC0）** 的工业/科幻模块化套件，用于补充设备与管线（授权同为 CC0）。
3. **Poly Pizza / Sketchfab** 按 CC0 过滤检索 `server rack` / `data center` / `UPS`，逐件核对授权与面数。
4. **短期过渡**：继续使用现有程序化几何（[SceneViewer.vue](file:///d:/other/django-base-admin/frontend/src/components/scene3d/SceneViewer.vue#L63-L72) 已实现），先把加载链路打通，再替换高质量模型。

**判定标准**：若项目目标是“园区级数字孪生/厂房外观展示”，本包足够且性价比极高；若目标是“机房级设备监控可视化”，本包只能当背景，核心设备必须另找/自建。

---

## 六、预览图说明

包内提供 `Preview.png`（资产拼图）、`Preview (Variation A/B/C).png`（三套配色总览）、`Sample.png`（示例场景），以及 `Previews/` 下 37 张单模型缩略图。抽查 3 张：

1. **`Previews/building-a.png`**：3 层灰蓝色厂房/办公楼，规则排列的蓝色发光窗格，平屋顶带设备凸起，硬边低模，典型 Kenney 工业风。
2. **`Previews/shipping-container-a.png`**：橙色 20 英尺集装箱，侧板有波纹，端部带蓝色锁杆/门把手，比例接近真实集装箱。
3. **`Previews/water-tower.png`**：蓝色锥顶罐体 + 橙黄色环带 + 深色四腿支架，卡通化水塔，适合做冷却塔/水塔装饰。

---

## 附录 A：37 个模型全清单

- 建筑：`building-a`、`building-b`、`building-c`、`building-d`、`building-e`、`building-f`、`building-g`、`building-h`、`building-i`、`building-j`、`building-k`、`building-l`、`building-m`、`building-n`、`building-o`、`building-p`、`building-q`、`building-r`、`building-s`、`building-t`
- 烟囱：`chimney-basic`、`chimney-small`、`chimney-medium`、`chimney-large`
- 储罐：`detail-tank`、`detail-tank-large`
- 集装箱：`shipping-container-a`、`shipping-container-b`、`shipping-container-c`
- 光伏：`solar-panel-flat`、`solar-panel-landscape`、`solar-panel-landscape-group`、`solar-panel-portrait`、`solar-panel-portrait-group`
- 水塔/风机：`water-tower`、`windmill`、`windmill-low`

## 附录 B：实测方法

- 面数：解析每个 GLB 的 JSON chunk，取 `accessors[indices].count / 3` 求和；
- 体积/尺寸：文件字节数、`POSITION` accessor 的 `min/max` 包围盒；
- 材质：读取 `materials` / `images` / `extensionsUsed`；
- 贴图：读取 PNG 头获取 512×512；
- 授权：逐行阅读 `License.txt` 与 `Overview.html`；
- 项目侧：阅读 `SceneViewer.vue`、`scene3d/models.py`、`scene3d/views.py`、`config/urls.py`，并在 `frontend/src` 全量检索 `GLTFLoader/DRACOLoader`（0 命中）。
