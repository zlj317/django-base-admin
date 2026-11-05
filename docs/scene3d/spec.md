# 需求7：3D 可视化 / 数字孪生模块 —— 实现规格（Spec）

> 依据：`docs/需求7 django-base-admin_3D可视化模块需求文档.md`
> 目标：在不破坏现有 RBAC、附件、报表大屏、工作流、消息中心、主题系统的前提下，新增 3D 可视化模块的后端数据/接口与前端页面，并完成可复现的深度自测。
> 审批：本规格为执行前的最终口径，确认后再按 `tasks.md` 逐项实现。

---

## 1. 现状与约束（已核实）

| 项 | 现状 |
| --- | --- |
| 后端 | Django 4.2 LTS + DRF；`config/settings.py` 使用 MySQL `gen_admin`（192.168.0.76）；`config/urls.py` 按模块挂载 `/api/<module>/` |
| 建表方式 | **不使用 Django migrations**：业务表由 `docs/*.sql` 手工创建，模型统一 `managed = False`（参考 `apps/kb/models.py`、`apps/bi/models.py`） |
| 通用基类 | `common.views.CrudViewSet`（list/create/update/delete/status + 钩子）；`common.utils.BaseModel`（create_by/create_time/update_by/update_time/is_deleted） |
| 响应 | `common.response.ok/fail` → `{code, msg, data}`；`common.pagination.StandardPagination` → `{total, page, page_size, list}` |
| 权限 | `PermissionCheck` 读取 `perm_prefix` 生成的 `list/create/update/delete` 权限；超管 `*:*:*` |
| 菜单种子 | 各 app 的 `seed.py` 幂等写入 `sys_menu` + `sys_role_menu`；`init_db` 命令统一调用 |
| 主键 | `common.fields.SnowflakeIDField`（雪花 ID，前端按字符串处理） |
| 前端 | Vue3 + Vite；**主体 Element Plus**（Arco 仅顶栏主题面板）；路由由后端菜单树动态生成（`menu_type='C'` 的 `component` 字符串映射 `views/**/*.vue`） |
| 主题 | `html.dark` + `html[data-theme]` + CSS 变量；令牌在 `styles/tokens.css`，切换在 `theme/index.js`；5 套配色 × 明暗 2 模式 |
| 现有资产 | `docs/scene3d_init.sql` 已存在（13 张表 + 少量样例数据），列名与需求文档略有差异，可直接沿用并做兼容修正 |
| 运行环境 | 后端 `http://127.0.0.1:8000` 与前端 `http://127.0.0.1:5173` 当前均已在运行；admin/123456 登录可用 |

**关键约束**
1. 不修改既有表、既有接口、既有页面行为；仅新增文件 + 少量注册点修改（`settings.py`、`config/urls.py`、`init_db.py`、`package.json`、`README.md`、需求文档状态）。
2. 所有新增代码逐行中文注释（template / script / style 全覆盖），与仓库既有风格一致。
3. 无硬编码颜色：3D 场景的材质、光照、背景、雾、网格、标签、选中框颜色全部从 `getComputedStyle` 读取 `--brand-*` / `--chart-*` / `--el-*` 令牌，主题切换时重建材质与光照。
4. `three.js` 采用**动态 import**，只在 3D 页面加载，独立 chunk，不影响主包首屏。
5. 自测数据统一带 `AUTO-SELFTEST` 前缀/标记，验证后删除，不触碰既有数据。

---

## 2. 后端设计

### 2.1 新 app：`backend/apps/scene3d/`

新增文件：

| 文件 | 内容 |
| --- | --- |
| `__init__.py` | 包声明 |
| `apps.py` | `Scene3dConfig`，`name='apps.scene3d'`，中文 verbose_name |
| `models.py` | 13 个模型，全部 `managed=False`，表名沿用 `scene3d_init.sql` |
| `serializers.py` | 每个模型一个 `ModelSerializer`（`fields='__all__'`），场景详情额外返回分类名/模板名/对象数 |
| `views.py` | 13 个 ViewSet + 自定义 action |
| `urls.py` | 与 `apps/file/urls.py` 相同的 `crud()` 生成器 + 自定义路由 |
| `seed.py` | `seed_scene3d()`：菜单/按钮权限 + 演示数据（幂等，可重复执行） |

注册点修改：
- `config/settings.py`：`INSTALLED_APPS` 追加 `'apps.scene3d'`。
- `config/urls.py`：追加 `path('api/scene3d/', include('apps.scene3d.urls'))`。
- `core/management/commands/init_db.py`：新增 `SQL_SCENE3D = docs/scene3d_init.sql` 执行；调用 `seed_scene3d()`。

### 2.2 数据表（13 张，沿用 `docs/scene3d_init.sql`）

对现有 SQL 做**非破坏性修正**后作为唯一建表来源：
1. 去掉 `DROP TABLE IF EXISTS`，改为 `CREATE TABLE IF NOT EXISTS`（避免重复执行清空数据）。
2. 公共字段改为与 `BaseModel` 一致：`create_by varchar(64)`、`update_by varchar(64)`（原为 `BIGINT`），`create_time/update_time datetime`。
3. 保留 JSON 列（MySQL 5.7+/8.0 支持），Django 侧用 `models.JSONField`。
4. 为 `scene3d_alarm_record` / `scene3d_patrol_record` / `scene3d_scene_version` / `scene3d_access_log` 补 `create_time/update_time/is_deleted`（已有）。
5. 样例数据保留并补充：3 个分类、3 个模板、3 个场景、6 个机柜模型对象、3 台设备对象、2 条数据绑定、2 条告警规则、1 条巡检路线、3 条版本、2 条访问日志（全部使用雪花 ID，幂等插入 `INSERT IGNORE`）。

表 ↔ 需求文档 4.x 对应关系：

| 需求表 | 实际表 | 模型 |
| --- | --- | --- |
| 4.1 scene_3d | `scene3d_scene` | `Scene3dScene` |
| 4.2 场景分类 | `scene3d_category` | `Scene3dCategory` |
| 4.3 场景模板 | `scene3d_template` | `Scene3dTemplate` |
| 4.4 模型资源 | `scene3d_model_resource` | `Scene3dModelResource` |
| 4.5 场景对象 | `scene3d_scene_object` | `Scene3dSceneObject` |
| 4.6 数据绑定 | `scene3d_data_bind` | `Scene3dDataBind` |
| 4.7 告警规则 | `scene3d_alarm_rule` | `Scene3dAlarmRule` |
| 4.8 告警记录 | `scene3d_alarm_record` | `Scene3dAlarmRecord` |
| 4.9 巡检路线 | `scene3d_patrol_route` | `Scene3dPatrolRoute` |
| 4.10 巡检记录 | `scene3d_patrol_record` | `Scene3dPatrolRecord` |
| 4.11 场景版本 | `scene3d_scene_version` | `Scene3dSceneVersion` |
| 4.12 场景权限 | `scene3d_scene_permission` | `Scene3dScenePermission` |
| 4.13 访问记录 | `scene3d_access_log` | `Scene3dAccessLog` |

### 2.3 接口清单（统一 `/api/scene3d/` 前缀，返回 `{code,msg,data}`）

| 方法 | 路径 | 说明 | 权限标识 |
| --- | --- | --- | --- |
| GET/POST/DELETE | `category/list`、`category/create`、`category/delete` | 分类 | `scene3d:category:*` |
| PUT | `category/update/<pk>`、`category/status/<pk>` | 分类编辑/启停 | 同上 |
| GET/POST/DELETE/PUT | `template/list`、`template/create`、`template/delete`、`template/update/<pk>` | 模板 | `scene3d:template:*` |
| GET/POST/DELETE/PUT | `list`、`create`、`delete`、`update/<pk>` | 场景 CRUD | `scene3d:scene:*` |
| GET | `<pk>/detail` | 详情（场景+对象+绑定+告警规则+权限） | `scene3d:scene:list` |
| POST | `<pk>/save` | 保存配置并生成版本快照 | `scene3d:scene:save` |
| POST | `<pk>/publish` | 发布（前置校验：至少 1 个对象、模型存在） | `scene3d:scene:publish` |
| POST | `<pk>/offline` | 下线 | `scene3d:scene:publish` |
| POST | `<pk>/copy` | 复制场景（含对象/绑定/规则） | `scene3d:scene:create` |
| GET | `<pk>/versions` | 版本列表 | `scene3d:scene:list` |
| POST | `<pk>/rollback` | 回滚到指定版本（回滚也生成新版本） | `scene3d:scene:save` |
| POST | `<pk>/share` | 生成带随机 token 的分享链接（默认 7 天，最长 30 天） | `scene3d:scene:share` |
| GET | `<pk>/visit-log` | 访问记录 | `scene3d:scene:list` |
| GET | `<pk>/export` | 导出场景 JSON | `scene3d:scene:list` |
| GET/POST/DELETE/PUT | `model/list`、`model/create`、`model/delete`、`model/update/<pk>` | 模型资源 | `scene3d:model:*` |
| POST | `model/upload` | 上传 glb/gltf/zip，校验 ≤50MB | `scene3d:model:upload` |
| GET | `model/<pk>/preview` | 返回模型文件访问 URL | `scene3d:model:list` |
| GET/POST/DELETE/PUT | `object/list`、`object/create`、`object/delete`、`object/update/<pk>` | 场景对象 | `scene3d:object:*` |
| GET/POST/DELETE/PUT | `binding/list`、`binding/create`、`binding/delete`、`binding/update/<pk>` | 数据绑定 | `scene3d:binding:*` |
| GET | `binding/<pk>/preview` | 返回模拟/真实数据（table 白名单校验，api 走已配置接口） | `scene3d:binding:list` |
| GET/POST/DELETE/PUT | `alarm/rule/list`、`alarm/rule/create`、`alarm/rule/delete`、`alarm/rule/update/<pk>` | 告警规则 | `scene3d:alarm:*` |
| GET | `alarm/records` | 告警记录（scene_id/level/status/time 筛选） | `scene3d:alarm:list` |
| POST | `alarm/<pk>/confirm` | 确认告警（幂等） | `scene3d:alarm:confirm` |
| GET | `alarm/stats` | 场景告警统计（数量/级别分布） | `scene3d:alarm:list` |
| GET/POST/DELETE/PUT | `route/list`、`route/create`、`route/delete`、`route/update/<pk>` | 巡检路线 | `scene3d:route:*` |
| POST | `route/<pk>/play` | 生成巡检记录并返回路径点 | `scene3d:route:play` |
| GET | `route/record/list` | 巡检记录 | `scene3d:route:list` |
| GET/POST/DELETE/PUT | `permission/list`、`permission/create`、`permission/delete`、`permission/update/<pk>` | 场景授权 | `scene3d:permission:*` |
| GET | `visit-log/list` | 访问日志 | `scene3d:scene:list` |
| GET | `share/<token>` | 分享链接解析（免登录，仅只读，校验有效期） | 免鉴权 |
| GET | `screen/data` | 3D 大屏聚合数据（场景+告警统计+指标） | `scene3d:screen:view` |
| WS | `/ws/scene3d/<id>` | **本期不实现**：仓库未启用 Channels/Redis；以 30s 轮询 + 手动刷新替代，详见第 5 节 |

**实现说明**
- 自定义 action 的权限通过覆写 `permission_classes` 属性，把 `save/publish/share/confirm/play/upload` 等补进 `perm_map`。
- 保存/发布/回滚/删除/授权变更调用 `common.middleware` 既有操作日志机制（URL 命中即记录，无需额外代码）。
- 场景 JSON 服务端校验：`scene_config` 必须是可解析 JSON 对象且不超过 2MB；`position/rotation/scale` 必须是 `{x,y,z}` 对象。
- 告警确认幂等：已确认记录再次确认直接返回成功，不重复写库。
- 数据绑定预览安全：`source_config.table` 必须在白名单（`scene3d_scene` 伪造的台账表 → 使用 `scene3d_scene_object`/`monitor_alarm_record` 等既有表）内，**禁止任何用户输入 SQL**；本期用内置模拟器返回 `{value, unit, time}`，避免与业务表强耦合。

### 2.4 菜单与权限种子

一级目录：`3D可视化`（`path='scene3d'`, `menu_type='M'`, icon `DataBoard`，order 16）。
二级页面（`menu_type='C'`）：

| 菜单名 | path | component | perms |
| --- | --- | --- | --- |
| 场景管理 | `scene` | `scene3d/scene/index` | `scene3d:scene:list` |
| 场景编辑器 | `editor` | `scene3d/editor/index` | `scene3d:scene:save` |
| 模型资源库 | `model` | `scene3d/model/index` | `scene3d:model:list` |
| 数据绑定 | `binding` | `scene3d/binding/index` | `scene3d:binding:list` |
| 告警可视化 | `alarm` | `scene3d/alarm/index` | `scene3d:alarm:list` |
| 巡检路线 | `route` | `scene3d/route/index` | `scene3d:route:list` |
| 场景发布 | `publish` | `scene3d/publish/index` | `scene3d:scene:share` |
| 3D大屏 | `screen` | `scene3d/screen/index` | `scene3d:screen:view` |

按钮权限（`F`）：`scene3d:scene:create/update/delete/save/publish/share`、`scene3d:model:upload`、`scene3d:binding:preview`、`scene3d:alarm:confirm`、`scene3d:route:play`、`scene3d:permission:update` 等。
写入方式：复用 `_ensure_menu` 幂等逻辑，并把新菜单授予全部启用角色（与 `apps/kb/seed.py` 一致）。

---

## 3. 前端设计

### 3.1 依赖与体积

| 依赖 | 版本 | 引入方式 | 体积影响 |
| --- | --- | --- | --- |
| `three` | `^0.170.0` | `await import('three')` + `GLTFLoader`/`OrbitControls` 按需 import | 独立 async chunk（约 600–700 kB，gzip ≈ 170 kB），**不进主包**；仅 3D 页面触发下载 |
| 无 | `echarts-gl` | 不引入 | 3D 场景用原生 Three.js，2D 图表继续用现有 SVG/CSS 轻量实现，避免重复引入 |

`vite.config.js` 不改动：动态 import 天然分包；如构建后仍出现主包告警，保持现有告警口径（既有告警，不新增）。

### 3.2 新增页面/组件

| 文件 | 职责 |
| --- | --- |
| `src/api/scene3d.js` | 全部接口封装（list/create/update/delete + 各业务 action） |
| `src/components/scene3d/SceneViewer.vue` | Three.js 渲染核心：场景/相机/光照/网格/模型占位/标签/选中框/告警闪烁/巡检漫游/WASD；`mode='view'|'edit'|'screen'`；主题令牌驱动颜色；暴露 `focusObject`、`resetCamera`、`playRoute` |
| `src/views/scene3d/scene/index.vue` | 场景管理（列表/筛选/新建/编辑/复制/发布/下线/删除/分类管理/预览跳转） |
| `src/views/scene3d/editor/index.vue` | 场景编辑器（对象树、画布、属性面板、添加/删除对象、变换、材质、标签、网格/坐标轴开关、撤销重做、保存/预览） |
| `src/views/scene3d/model/index.vue` | 模型资源库（列表/上传/预览弹窗旋转查看/编辑/删除） |
| `src/views/scene3d/binding/index.vue` | 数据绑定（列表/按场景筛选/编辑/预览数据/启停） |
| `src/views/scene3d/alarm/index.vue` | 告警可视化（规则 Tab + 记录 Tab + 统计卡 + 确认 + 定位跳转） |
| `src/views/scene3d/route/index.vue` | 巡检路线（路线 CRUD + 路径点编辑 + 播放 + 巡检记录） |
| `src/views/scene3d/publish/index.vue` | 场景发布（已发布场景 + 分享链接 + 授权 + 访问日志） |
| `src/views/scene3d/screen/index.vue` | 3D 大屏（三维主视觉 + 2D 指标卡/告警列表 + 全屏 + 视角轮播） |
| `src/views/scene3d/view/index.vue` | 只读场景查看页（静态路由 `/scene3d/view/:id`，支持 `?route=` 自动漫游） |
| `src/views/scene3d/share/index.vue` | 分享链接访问页（静态路由 `/scene3d/share/:token`，免登录只读） |

静态路由追加（`src/router/index.js`）：`/scene3d/view/:id`、`/scene3d/share/:token`（不挂 Layout 中的分享页铺满窗口）。

### 3.3 主题适配

- `SceneViewer.vue` 在 `onMounted` 与 `watch(themeState)` 时读取 `getComputedStyle(document.documentElement)` 的 `--brand-primary`、`--brand-glow`、`--chart-1..6`、`--el-bg-color`、`--el-text-color-primary`。
- 暗色模式：`renderer.setClearColor` 使用 `--el-bg-color`；环境光强度 +15%，平行光强度 -10%，雾颜色取背景色；材质 `metalness/roughness` 根据明暗微调；网格/坐标轴/选中框颜色使用 `--brand-primary` 与 `--el-border-color`。
- 所有页面样式只使用 `var(--...)` 令牌，禁止 `#hex` / `rgb()` 常量（3D 内置兜底色仅作为 `getComputedStyle` 取不到变量时的 fallback，并在注释中说明）。

### 3.4 编辑器能力边界（与需求对照）

| 需求条目 | 本期实现 |
| --- | --- |
| 模型导入摆放（位置/旋转/缩放） | ✅ 通过属性面板 + 拖拽手柄（TransformControls 简化为输入框 + 拖动平面） |
| 层级树/分组/重命名/显隐/锁定 | ✅ 对象树（父子层级展示、重命名、显隐、锁定、删除） |
| 多选/框选/对齐/吸附/撤销重做 | ⚠️ 撤销/重做 ✅；多选/框选/吸附 ❌（列入"未完成/受限"） |
| 光照/天空盒/雾/材质 | ⚠️ 环境光/平行光强度与颜色、背景色、雾 ✅；点光/聚光/天空盒 HDR ❌ |
| 相机预设/透视正交 | ✅ 预设视角保存与切换（存 scene_config） |
| 后处理（辉光/抗锯齿/阴影） | ⚠️ 抗锯齿 + 阴影开关 ✅；辉光 ❌ |
| 文字标签/图标/2D 面板/引导线 | ⚠️ 标签（始终面向相机）✅；图标/2D 面板/引导线 ❌ |
| 点击交互（面板/跳转/下钻/报表/审批） | ⚠️ 点击弹信息面板 + 查看告警 ✅；跳转/下钻/审批入口以按钮占位并说明 |
| 预览/导出 JSON | ✅ |
| 数据绑定/告警/巡检/发布/大屏/版本 | ✅ 见接口清单 |

---

## 4. 深度自测方案

1. **后端真实 HTTP**（PowerShell + Invoke-RestMethod，token 来自登录）：
   - 正常：分类/模板/场景 CRUD、detail、save、publish、copy、versions、rollback、share、model 上传、binding preview、alarm confirm、route play、permission、visit-log、screen/data。
   - 异常：缺参、非法 JSON、不存在 ID、超 50MB（用假文件头模拟）、未发布场景分享、重复确认。
   - 权限：用非 admin 账号（若无则创建临时用户/角色）验证缺权限返回 403；分享接口免登录可访问。
   - 数据：迁移（执行 SQL）后 13 张表存在且 `SELECT COUNT(*)` 与种子一致；清理 `AUTO-SELFTEST` 数据。
2. **前端**：启动 dev server，浏览器打开 8 个页面 + 查看页：
   - 渲染、交互（新增/编辑/删除/筛选/保存/预览）；
   - 主题切换：亮色 `blue`、暗色 `blue`、亮色 `purple`、暗色 `purple`，检查 3D 背景/材质/标签/图表无硬编码颜色、文字可读；
   - 截图保存到 `docs/images/scene3d/`。
3. **构建**：`npm run build` 必须 exit 0；记录主包与 three chunk 体积。
4. **清理**：删除自测产生的记录（`AUTO-SELFTEST` 前缀）与临时文件。

---

## 5. 明确不实现 / 受限项（需人工确认）

| 项 | 原因 | 替代方案 |
| --- | --- | --- |
| Django Channels + Redis 实时 WebSocket | 当前仓库 `asgi.py` 未启用 Channels，`INSTALLED_APPS` 无 `daphne/channels`，Redis 未配置；引入会改变部署形态与依赖 | 30 秒轮询 + 手动刷新 + "数据更新时间/过期半透明"标记，接口预留 `ws` 分支 |
| MinIO 对象存储 | 仓库实际使用本地 `MEDIA_ROOT`（`wf_file` 的 `storage_type='local'`），MinIO 未部署 | 模型文件落本地 `media/uploads/scene3d/`，字段保留 `file_id` 便于后续切换 |
| glTF→glb 压缩、KTX2、LOD、实例化、分楼层按需加载 | 需离线工具链与大模型资源；本期对象以程序化几何体占位 | 上传校验 ≤50MB；场景加载采用按需 `GLTFLoader` + 同一模型缓存（`cache` Map）；FPS 面板与低帧率降级（关阴影/降 pixelRatio）✅ |
| 完整框选/多选/对齐/吸附、点光/聚光/天空盒 HDR、辉光后处理、2D HTML 面板/引导线 | 编辑器工作量过大（需求文档 8.4 建议一期先落查看+绑定+告警） | 一期实现核心编辑（树/变换/材质/标签/视角/撤销重做/保存）；其余列入后续迭代 |
| 一键发起工单/审批的真实联动 | 需与 `apps/wo`、`apps/workflow` 的启动接口做适配 | 告警面板提供"发起工单/审批"按钮，跳转对应模块列表并携带参数（不自动创建实例，避免污染业务数据） |
| 定时任务自动巡检/快照归档 | `apps/task_sched` 为配置管理，无实际调度器执行环境 | 巡检播放为手动触发 + 记录；文档标注 |
| 国产浏览器实机验证（银河麒麟/360/奇安信） | 无对应环境 | 提供 WebGL 能力检测与降级提示页；记录为"需人工实机验证" |

---

## 6. 验收口径（需人工确认）

1. 9 个页面可访问，8 个菜单出现在侧边栏，按钮权限生效。
2. 全部接口 HTTP 200 + `code=200`（异常场景返回明确中文 `msg`，权限不足 `code=403`）。
3. `npm run build` exit 0，three 独立 chunk，主包体积增量 ≤ 5 kB。
4. 明暗 × 至少 2 套配色下无硬编码颜色、3D 场景可正常辨识。
5. 文档更新：需求文档追加"实现状态"章节；README 模块清单与技术栈（three.js）同步。
