# 首页（Dashboard）充实改造 —— 实现规格（Spec）

> 触发：用户优先级变更——**暂停 3D 需求**，先把首页做充实；已创建/改动的 3D 文件保留不删。
> 依据：用户反馈截图 + 实测 `GET /api/home/overview/`（有真实数据）。
> 审批：确认本规格后按 `tasks.md` 执行。

---

## 1. 空白区域根因（实测定位，非猜测）

截图 `docs/images/ui/02-dashboard-light.png` 对照代码 `frontend/src/views/dashboard/index.vue`：

| 现象 | 根因 |
| --- | --- |
| 中部/右上两块面板只占列宽的一半，右侧留出大片横向空洞 | `.content-row > .el-col { display: flex }` 让栅格列成为 flex 容器；`.panel` 也是 `display:flex`，作为 flex 子项默认 `flex: 0 1 auto`，**宽度收缩到内容宽度**。全文件只给 `.stat-card` 补了 `width:100%`，`.panel` 没有补，因此待办/动态/监控/常用功能四个面板全部“缩水” |
| 同一行两张卡高度一致但内容只占上半部分，下半空白 | `height:100%` 等高的副作用：内容少的一侧被拉高，没有内容填充 |
| 左下、右下同样出现空白 | 与上面同一原因（`.bottom-row > .el-col` 也是 flex 容器，`.panel` 未撑满） |
| 待办/动态内容偏薄 | 每个卡片只放 5 条列表，缺少图表、统计、分组入口等信息密度 |

**结论**：不是接口无数据（实测已返回 5 条待办、5 条动态、公告与消息各 3 条），也不是 ECharts 容器高度为 0（本页根本未引入图表库），而是**CSS 弹性布局导致面板宽度收缩 + 内容密度不足 + 等高拉伸留白**。

---

## 2. 改造目标

1. 修复 `.panel` 宽度（`width:100%; min-width:0`），桌面 1440 以上无横向空洞，1280 不拥挤。
2. 用既有模块真实数据补充 10 个以上信息块；无数据的模块做“引导型卡片”（用途说明 + 跳转按钮），不留空。
3. 顶部 4 个指标卡保留，补真实 7 日迷你趋势与环比（不再用静态装饰折线）。
4. “常用功能”改为按模块分组的索引（系统管理 / 业务协作 / 数据可视化 / 平台运维），每项可跳转。
5. 全部颜色走主题令牌；明暗 × 5 配色可切换，图表颜色随 `--chart-*` 变化。
6. 逐行中文注释。

---

## 3. 后端设计

新增接口 **`GET /api/home/rich/`**（`apps/home/views.py` 新增 `rich` 方法，`apps/home/urls.py` 加一条路由），**不改动现有 `/home/overview/` 与 `/home/monitor/`**，避免影响既有调用。

返回结构（所有查询沿用现有 `_raw_query` / `_raw_count` 的防御式写法，表缺失返回空，不抛 500）：

```json
{
  "stats": {
    "todos": 5, "messages": 0, "workflows": 6, "new_users": 0,
    "todo_delta": 0, "message_delta": 0, "workflow_delta": 0, "user_delta": 0,
    "file_count": 5, "file_size": 0, "wo_open": 0, "alarm_open": 0
  },
  "trends": {
    "dates": ["11-05", ... 7 天],
    "wo": [0,0,...], "wf": [...], "msg": [...], "file": [...]
  },
  "todos": [ {title,typeLabel,time,path,creator} ... 8 ],
  "notices": [ {id,title,content,time} ... 4 ],
  "messages": [ {id,title,content,read,time} ... 4 ],
  "workflows": [ {id,proc_name/node_name,status,time} ... 5 ],
  "files": { "count":5, "size":0, "by_ext":[{"ext":"xlsx","count":2,"size":123}] },
  "tasks": { "total":n, "enabled":n, "recent":[{name,status,time}] },
  "alarms": { "total":n, "open":n, "by_level":[{"level":1,"count":n}...], "recent":[{content,level,time}] },
  "users": { "total":n, "today":n, "by_dept":[{"name":"信息中心","count":n}] },
  "reports": { "templates":n, "generated":n, "recent":[{name,time}] },
  "bi": { "total":n, "published":n, "list":[{name,status}] },
  "kb": { "docs":n, "categories":n, "hot":[{title,read_count}] },
  "cal": { "today":n, "list":[{title,start_time}] }
}
```

数据来源（以实际 `models.py` 字段为准，全部 `_raw_query` 容错）：

| 信息块 | 表 |
| --- | --- |
| 待办/趋势 | `wf_task`、`work_order`、`cal_schedule` |
| 公告/消息/动态趋势 | `notice_info`、`msg_record` |
| 工作流实例 | `wf_instance` |
| 文件与存储 | `wf_file`（`file_size`、`file_ext`） |
| 定时任务 | `task_job` / `task_log`（以 `apps/task_sched/models.py` 为准） |
| 监控告警 | `monitor_alarm_record`、`monitor_alarm_rule` |
| 用户/部门 | `sys_user`、`sys_dept` |
| 报表/BI | `report_rp_template`、`rp_generate_record`、`bi_screen` |
| 知识库 | `kb_document`、`kb_category` |
| 日程 | `cal_schedule` |

环比口径：今日计数 vs 昨日计数（`DATE(create_time)` 过滤），差值写入 `*_delta`。

---

## 4. 前端设计

### 4.1 修改文件

| 文件 | 改动 |
| --- | --- |
| `frontend/src/views/dashboard/index.vue` | 整体重排栅格与面板；保留 Banner、4 指标卡、4 原面板（待办/动态/监控/常用功能）；新增公告、消息、工作流实例、文件存储、定时任务、监控告警、报表/BI、知识库、今日日程、引导卡；修复 `.panel { width:100%; min-width:0 }`；接入 `/home/rich/`；逐行注释 |
| `frontend/src/components/dashboard/TrendChart.vue`（新增） | 纯 SVG 7 日折线/面积图：props `series`/`labels`/`color`；坐标与网格用 `--app-*` 令牌；无图表库依赖 |
| `frontend/src/components/dashboard/DistributionBar.vue`（新增） | 纯 SVG/CSS 分布条（告警级别、文件类型）：props `items`；颜色用 `--chart-*` |
| `backend/apps/home/views.py` | 新增 `rich()` 方法（不改旧方法） |
| `backend/apps/home/urls.py` | 新增 `path('rich/', ...)` |
| `docs/需求6 django-base-admin系统首页需求文档.md` | 追加“实现状态”章节（改造内容与接口） |
| `README.md` | 首页模块清单补充新增信息块（仅相关章节，不动架构图） |

### 4.2 布局（24 栅格，桌面断点）

```
Hero Banner（保留）
指标卡 ×4（xs=12 sm=12 md=6，含真实 sparkline + 环比）
Row A：业务趋势（md=16，2 张 TrendChart：工单/流程） | 待办事项（md=8）
Row B：公告通知（md=8） | 站内消息（md=8） | 工作流实例（md=8）
Row C：系统监控（md=8） | 文件与存储（md=8） | 定时任务与告警（md=8）
Row D：报表与 BI（md=8） | 知识库（md=8） | 今日日程（md=8）
Row E：常用功能（md=24，按 4 组模块分区，每组 4-6 个入口）
```

- 所有 `el-col` 保持 `display:flex`，`.panel` 补 `width:100%; min-width:0` → 消除横向空洞。
- 每行 `align-items: stretch`，面板 `height:100%`，但**只给需要对齐的行使用**；内容少的卡片用 `justify-content:space-between` + 底部“查看全部”链接填满视觉。
- 1280（md 断点）下每行 3 列宽度约 340px，文案 `min-width:0` + 省略，避免拥挤。
- 图表固定高度 150–170px，避免容器高度为 0。

### 4.3 主题适配

- 新增/修改样式只允许 `var(--app-*)`、`var(--brand-*)`、`var(--chart-*)`、`var(--el-*)`。
- 修复现有硬编码色：`#c0c4cc`（空状态图标）、`#22c55e/#ef4444`（监控进度）、`#fff`/`rgba(255,255,255,...)`（Banner 内白字与装饰圆属品牌渐变上的固定反白，保留并注释说明）。
- TrendChart 的系列色由父级传入 `var(--chart-1..6)`，切换主题时通过 `themeState` 重新取色即可（组件内用 class 映射，无需重建实例）。

---

## 5. 验证方案

1. **接口**：PowerShell 登录后调 `GET /api/home/rich/`，确认 `code=200` 且各块字段存在；异常场景（无 token）返回 401。
2. **页面**：浏览器实际打开 `/dashboard`：
   - 1440 与 1280 两个宽度截图（保存 `docs/images/dashboard/`），核对无横向空洞、同行等高、文字不溢出；
   - 主题：亮色 blue、暗色 blue、亮色 purple、暗色 rose，共 4 组截图；
   - 点击关键卡片：待办 → `/workflow/todo` 或 `/wo/mine`；公告 → `/notice/info`；消息 → `/msg/record`；文件 → `/file`；任务 → `/task`；报表 → `/rp/template`；BI → `/bi`；知识库 → `/kb/document`；日程 → `/cal/schedule`；常用功能各入口；
   - 控制台无报错（重点看 `undefined`/`Cannot read`）。
3. **构建**：`npm run build` 必须 exit 0，记录主包体积（不新增依赖，体积增量应 < 10 kB）。
4. 清理：本次不写测试数据；仅新增文档与截图。

---

## 6. 明确不做 / 受限

| 项 | 说明 |
| --- | --- |
| 引入 ECharts | 首页只需 7 日折线与分布条，用 SVG 手绘可避免 +300 kB 依赖；与“3D/图表后续可能引入 echarts”不冲突 |
| 实时推送/定时刷新 | 首页保持一次性加载 + 手动刷新按钮；不新增 WebSocket |
| 自定义首页布局 | 现有 `home_user_config` 表暂不接入（保持范围最小） |
| 无数据模块 | 统一用“引导型卡片”：图标 + 用途说明 + “去配置/去使用”按钮，明确指向对应菜单 |

---

## 7. 验收口径

1. 1440 宽度下首页所有行右侧无 > 20px 的横向空洞；1280 下无卡片重叠/文字截断。
2. 新增信息块 ≥ 10 个，全部来自真实接口数据或明确的引导卡。
3. 明暗 × 2 套配色截图无硬编码颜色导致的低对比/不可读。
4. 关键跳转全通，控制台无报错。
5. `npm run build` exit 0。
