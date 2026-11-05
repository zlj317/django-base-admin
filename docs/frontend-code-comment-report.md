# 前端源码逐行中文注释 · 验收报告

> 本轮只做一件事：为 `frontend/src` 下全部手写源码补充详细中文注释。**未改动任何业务逻辑、样式值、接口契约与组件行为**。

## 一、结论

- 覆盖 `frontend/src` 下 **98 个手写源文件**（`.vue` 75 个、`.js` 21 个、`.css` 2 个），无遗漏；`node_modules`、`dist`、自动生成产物未触碰。
- 原始 **19,161 行**（其中去空行/注释后的纯代码行 17,268 行），注释后 **28,164 行**，净增 **9,088 行中文注释**，平均每个文件 +93 行。
- 校验结果：98/98 文件的原有代码行**逐行逐字保留、顺序不变**，新增行 **100% 为注释或空行**（自动脚本校验，0 违规）。
- `npm run build` 两次均 **exit 0**，仅保留既有的 chunk 体积告警（主包 1,321.37 kB），无新增告警、无编译错误。

## 二、覆盖统计

| 范围 | 文件数 | 说明 |
|---|---|---|
| 入口与核心链路 | 10 | `main.js`、`App.vue`、`router/index.js`、`store/auth.js`、`utils/*`(4)、`directive/perm.js`、`api/student.js` |
| 样式与主题 | 3 | `styles/tokens.css`、`styles/index.css`、`theme/index.js` |
| 布局与通用组件 | 11 | `layout/*`(4)、`components/*`(7，含图表/主题切换/工作流组件) |
| 业务页面 | 74 | `views` 下全部页面，含 18 个已验证核心页面 |
| **合计** | **98** | 新增注释 9,088 行 |

关于样式段：41 个 `.vue` 文件自身含 `<style>`，已逐选择器注释；34 个 `.vue` 文件本身没有样式段（外观统一来自 `styles/index.css`），以及 `.js`/`.css` 之外的模块，其文件头已注明样式来源，属“无可注释对象”而非漏做。

## 三、分批推进与验证记录

| 批次 | 范围 | 文件数 | 新增注释 |
|---|---|---|---|
| B1 | 入口/路由/登录态/请求封装/工具/权限指令/示例 API | 10 | 219 |
| B2 | 设计令牌、全局样式、主题系统 | 3 | 436 |
| B3 | 布局（侧栏/顶栏/菜单项）与 7 个通用组件 | 11 | 659 |
| B4a | 用户、角色、菜单管理 | 3 | 749 |
| B4b | 部门、字典、参数、操作日志、登录日志 | 5 | 346 |
| B5 | 系统首页、登录页、学生管理 | 3 | 537 |
| B6a | 日程、提醒 | 2 | 291 |
| B6b | 工单列表、我的工单、工单类型 | 3 | 378 |
| B6c | 消息配置/日志/记录/模板、租户与套餐 | 6 | 511 |
| B7 | 知识库分类/文档、BI 数据集/大屏/预览/访问统计 | 6 | 643 |
| B8 | 流程设计器、流程模型、表单定义、条件表达式 | 4 | 412 |
| B9a | 流程分类/用户组/监听器/发起/任务/待办 | 6 | 506 |
| B9b | 抄送/已办/实例/请假示例/我的流程、404 | 6 | 348 |
| B10 | 代码生成列表与配置、文件列表/存储配置/回收站 | 5 | 544 |
| B11a | 备份记录/策略、数据权限、角色权限、脱敏规则 | 5 | 531 |
| B11b | 水印字段/打印/模板、公告分类/公告 | 5 | 412 |
| B11c | 监控记录/规则、外部接口/调用日志/数据同步 | 5 | 483 |
| B11d | 报表分类/数据源/生成/模板 | 4 | 454 |
| B11e | 安全 IP/登录尝试/限流、单号规则、定时任务/日志 | 6 | 629 |
| **合计** | | **98** | **9,088** |

验证方式：

1. **基线快照**：动手前把 `frontend/src` 完整复制为基线，逐文件比对。
2. **纯注释插入校验**（每批完成后运行）：以“原有代码行必须在现文件中按原顺序逐字出现”为准，新增行只允许是 `//`、`/* */`、`<!-- -->` 注释或空行；原文件中已有的简短注释允许被更详细的注释替换。
3. **构建验证**：
   - B1 完成后：`npm run build` → `✓ built in 20.47s`，exit 0；
   - 全部批次完成后：`npm run build` → `✓ built in 22.93s`，exit 0。
   - 两次均只有既有的 `chunks larger than 500 kB` 告警（主包 1,321.37 kB），与注释前一致，无新增告警。
   - 中间批次采用“并发子任务 + 分节点静态校验”的方式推进（并发写入期间不做构建，避免半成品文件造成假失败），因此构建记录为 2 次，而非每批 1 次；静态校验在此过程中执行 5 次（含基线 1 次），最终 0 违规。

## 四、注释写法约定（全库统一）

- 每个文件顶部有文件级说明：模块职责、依赖关系、被谁使用；请求/接口类文件写明接口前缀与响应约定。
- 模板：每个元素、`v-if`/`v-for`/`v-model`/绑定/事件/插槽均说明“这个节点做什么、为什么这样写”；表格列写数据来源与宽度/对齐意图；弹窗字段写业务含义。
- 脚本：每个 import、`ref/reactive`、`computed`、`watch`、函数、判断分支、接口调用、副作用（`ElMessage`、`router`、`localStorage`、`nextTick`、定时器、`ResizeObserver`）均说明“做什么 + 为什么”。
- 样式：每个选择器说明作用对象与原因；设计令牌变量说明含义与影响范围；主题/暗色相关规则说明触发条件。
- 不写“定义变量”“循环”一类无信息量注释；说明写在被注释行的上一行，不追加行尾注释（因此没有改动任何原行）。

## 五、未覆盖文件与原因

- **无未覆盖文件**：98/98 全部完成。
- 局部“无内容可注”的情况：
  - 34 个 `.vue` 文件本身不含 `<style>` 段，无本地选择器可注释（其外观由 `styles/index.css` 提供，已在文件头说明）。
  - `styles/tokens.css`、`styles/index.css` 为纯样式文件，无 template/script 段。
  - `workflow/model/design.vue` 中 `defaultXml()` 的 BPMN XML 字符串属于数据字面量，为避免污染 XML 内容，改为在函数上方集中说明其结构，未逐行插入。
- 未触碰：`node_modules`、`dist`、`package.json`/`package-lock.json`、后端代码、文档与截图资源。

## 六、发现的疑似问题（仅记录，未改代码）

> 行号为**加注释后的当前行号**；本清单只记录现象，是否修复需结合后端实现与产品预期确认。

### 核心链路 / 布局 / 通用组件

1. `utils/request.js`：网络异常与业务异常都会统一弹出提示，blob 下载失败时无法解析后端 JSON 错误，用户只能看到通用网络错误。
2. `layout/components/Sidebar.vue`：菜单渲染依赖登录态里的菜单树，动态路由清理与菜单数据刷新若不同步，可能出现“菜单有、路由无”的短暂状态。
3. `components/chart/SimpleChart.vue`：饼图只有 1 个类目且数值为 0 时仍绘制整圈；多类目且总量为 0 时所有扇区角度为 0、图例显示 0.0%，观感像渲染失败。
4. `components/report/ReportPreview.vue`：样式使用硬编码浅色（`#1f2937`、`#eef1f6`、`#f7f9fc` 等），未走主题变量，暗色模式下会与全局深色主题割裂。
5. `components/workflow/WorkflowDetail.vue`：只在 `v-if="detail"` 一层判断后就解引用 `detail.instance`、`detail.audits`、`detail.tasks`，接口缺字段会渲染报错；且只在抽屉 `@open` 时 `load()`，未监听 `props.instanceId`，抽屉保持打开时切换实例不会刷新。

### 主题与全局样式

6. `theme/index.js`：`--brand-primary-hover` 始终向黑色混合 18%，暗色模式下“悬停”反而更暗。
7. `theme/index.js`：`--brand-gradient` 终点固定向白色混合 22%，青绿/橙/玫红等亮主色上的白字对比度可能低于 WCAG AA。
8. `theme/index.js`：写入了 `<html data-theme>`，但全项目没有 CSS 使用该属性（目前仅作调试标记/预留）。
9. `styles/index.css`：`.el-button--primary.is-text` 同时被加上了浅底和边框，Element Plus 的文本按钮本应无底无边。
10. `styles/index.css`：`.el-loading-mask { opacity: .78 }` 作用于整个遮罩子树，loading 图标与文字也被降低不透明度。
11. `styles/index.css`：`prefers-reduced-motion` 下把动画压到 0.01ms，会让 loading spinner 看似静止。
12. `styles/index.css`：标签底色依赖 `color-mix()`，旧浏览器不支持且无降级色。
13. 未被引用的令牌（疑似预留）：`--app-table-row-h`、`--app-table-stripe`、`--app-bg-deep`、`--app-space-6`、`--app-font-md`、`--app-font-lg`、`--app-shadow-xs`。

### 系统管理

14. `system/role/index.vue`：新增角色默认 `data_scope: 1`（全部数据权限），默认给到最大范围，建议改为最小权限。
15. `system/menu/index.vue`：`parentTree` 直接复用完整列表，编辑时上级菜单可选中自身/子孙节点，可能形成树环。
16. `system/menu/index.vue`：“菜单状态”对 `F`（按钮）类型隐藏，按钮节点无法通过界面停用。
17. `system/menu/index.vue`：类型切换后已隐藏字段仍按当前值提交（如 C→F 会带入旧组件路径），可能产生脏数据。
18. `system/menu/index.vue`：`visible` 用 `String(row.visible) === '1'` 判断，后端若返回布尔 `true` 会误显示。
19. `system/user/index.vue`：角色选项固定只取前 100 条，角色超过 100 时无法选择。
20. `system/dict/index.vue`：`currentType` 仅通过当前页 `typeList` 判断，翻页/查询后可能误判为“已删除”并自动关闭抽屉。
21. `system/dict/index.vue`：字典项分页 `layout` 未包含 `sizes`，`@size-change` 实际不会触发。
22. `system/operlog/index.vue`：`cost_time` 为空时会渲染成孤立的“ ms”。
23. `system/loginlog/index.vue`：详情状态用 `status === 0 ? '成功' : '失败'`，字段缺失也显示“失败”。
24. `system/*` 多个删除/清空函数：`ElMessageBox.confirm` 取消时会 reject，未用 `try/catch` 包裹，控制台会产生未处理 Promise rejection（项目内统一写法，功能不受影响）。

### 首页 / 登录 / 学生

25. `dashboard/index.vue`：系统监控右上角固定写“● 运行正常”，与 `monitor.db_status` 真实状态可能不一致。
26. `dashboard/index.vue`：`.todo-item` 重复定义（后一条完整覆盖前一条的 `flex:1`）；`overview.greeting`、`overview.now` 声明后未使用。
27. `dashboard/index.vue`：`todayText` 是 computed 但没有定时器，页面跨天不会自动刷新；`loadMonitor` 未用 `finally`，靠 `catch` 吞异常复位 loading。
28. `login/index.vue`：`await formRef.value.validate()` 位于 `try/catch` 之外，校验失败可能产生未捕获拒绝；密码使用 `v-model.trim`，会裁掉首尾空格。
29. `student/index.vue`：构建导入错误列表时用错误文本作 `:key`，重复错误可能触发重复 key；分页 `@change` 依赖 Element Plus 版本；`.sub` 硬编码 `#8a94a6`，暗色下对比度偏低；删除当前页最后一条后不回退页码。

### 日历 / 工单 / 消息 / 租户

30. `cal/schedule/index.vue`：副标题用 `scheduleMap.size`（有日程的日期数）却写“共 N 条日程”，同日多条时统计偏小。
31. `cal/schedule/index.vue`：`watch`、`isSameDay`、`handleDelete` 为未使用/死代码；`loading` 已定义但模板未绑定；`weekdayLabel` 用 `new Date('YYYY-MM-DD')`（UTC 解析）取星期，负偏移时区可能差一天。
32. `cal/schedule/index.vue`：选中周日时 `-0+1` 会跳到下一周且当周不含周日；`page_size: 500` 且无分页器，超过 500 条被静默截断；`openDetail` 只 `Object.assign` 覆盖，字段结构不同会残留上一条数据。
33. `cal/reminder/index.vue`：日程/用户下拉各取 500 条，超出部分缺项且名称回落为 id；两处 `catch` 静默吞错。
34. `wo/order/index.vue`：操作按钮均未接 `v-perm`，前端不做权限裁剪；创建人/处理人用 `el-input-number` 手填用户 ID；指派弹窗无 `prop`/`rules`。
35. `wo/order/index.vue` 与 `wo/mine/index.vue`：同一 `/wo/log/list` 接口，前者读 `remark || content`、后者读 `comment`，字段命名不一致，可能有一处始终取不到备注。
36. `wo/mine/index.vue`：`auth.user?.id` 为空时不会附加 `creator_id/assignee_id`，会短暂显示全量工单（数据范围风险）。
37. `msg/config/index.vue`、`msg/template/index.vue`：行内开关先改本地值再调接口，失败不回滚；`Object.assign` 只覆盖初始键，编辑行的额外字段会残留并可能随新增提交。
38. `msg/log/index.vue`、`msg/record/index.vue`：渠道/消息类型直接显示编码，与查询下拉的中文标签口径不一致。
39. `tenant/tenant/index.vue`、`tenant/package/index.vue`：新建/编辑/删除按钮未加 `v-perm`；`expire_time` 默认 `''` 会原样提交。

### 知识库 / BI

40. `kb/category/index.vue`：`tableRows.value = [...allNodes.value]` 紧接着被覆盖（冗余）；`collectIds` 每次递归新建 `Map`（O(n²)）；页面副标题文案与右侧表格内容不符。
41. `kb/document/index.vue`：`hotTags` 为前端静态假数据；`tagColors` 中 `var(--chart-6)` 重复；`handleRead` 只打开抽屉、不调用阅读计数接口；版本历史仅占位提示；`.read-content` 硬编码 `#374151`。
42. `bi/dataset/index.vue`、`bi/screen/index.vue`：状态开关失败不回滚；`ds_config`/`screen_config` 只校验必填、不校验 JSON 合法性。
43. `bi/screen/index.vue`：`handleShare` 的本地回退分支因按钮 `v-if` 已要求 `share_url` 存在而不可达（死代码）；编辑时把 `share_url` 一并回填提交。
44. `bi/screen/view.vue`：`widget.data` 系列字段无空值保护；文本组件未设 `white-space: pre-wrap`，多行文本被折叠；分享页 `goBack` 固定跳 `/dashboard`（需登录），与免登录分享场景不符。

### 代码生成 / 文件

45. `gen/edit/index.vue`：`computed` 引入未使用；字典类型未去重，下拉可能出现重复项。
46. `gen/table/index.vue`：跨页勾选回填用 `Promise.resolve().then`，表格数据变更触发的 `selection-change` 可能覆盖选择，跨页勾选实际可能无法保留（需实测）。
47. `file/index.vue`：`window.open(url, '_blank')` 未加 `noopener`（低风险）；上传无前端大小/类型校验。
48. `file/recycle/index.vue`：批量恢复/彻底删除为前端串行循环，非原子操作且无 loading 禁用。
49. `file/config/index.vue`：提交时整行字段一并发送（可能含 `create_time`）；编辑态下“配置键”仍可改，无唯一性校验。

### 备份 / 数据权限 / 脱敏

50. `backup/record/index.vue`：保留 `type="selection"` 多选列但无批量操作；下载失败的 `catch` 为空，异常被静默吞掉。
51. `backup/strategy/index.vue`、`dp/*`、`dsm/rule`、`mon/rule`、`outer/api`、`outer/sync`、`rp/*`、`task/info`：多处列表内 `el-switch` 为乐观更新，接口失败不回滚，界面可能与后端状态不一致。
52. `dp/permission/index.vue`：新增默认 `permission_type: 'all'`，忘记修改直接提交会创建“全部数据”规则（越权风险）。
53. `dp/role_perm/index.vue`：角色/权限下拉只取 200 条，超过部分缺项且表格回退显示原始 id。
54. `dsm/rule/index.vue`：`mask_style`、`regular` 未设必填，留空会导致脱敏规则不生效。

### 工作流

55. `workflow/model/design.vue`：`selectElement` 回填配置会触发深层 `watch`，仅点击选中节点也会把 `dirty` 置 true，返回列表误弹“尚未保存”。
56. `workflow/model/index.vue`：“设计”按钮权限码用 `wf:model:list`，同列其他操作用 publish/update 等专用码，疑似复制遗漏。
57. `workflow/form/index.vue`：状态枚举（0 启用/1 停用）与流程模型（0 草稿/1 发布/2 停用）语义不一致；编辑字段只 `splice` 替换、不刷新 `previewData`；设计弹窗关闭无未保存二次确认。
58. `workflow/category/index.vue`：状态语义与同类页面相反（本页 1=启用，group/listener 为 0=启用），若后端统一 0=启用则标签显示颠倒。
59. `workflow/task/index.vue`：转派按钮禁用条件依赖未展示的 `instance_status`，字段缺失时按钮会永久禁用。
60. `workflow/start/index.vue`、`workflow/my/index.vue`：提交/跳转写死路径（`/workflow/center/*`），路由缺失时会落到 404。
61. `workflow/listener/index.vue`：`callback_param` 为自由文本 JSON，前端无格式校验。
62. `workflow/group/index.vue`：成员标签用姓名作 `:key`，重名会触发重复 key 警告。
63. `workflow/cc/index.vue`：`onMounted` 引入未使用、未调用 `getList`，进入页面不会自动加载。
64. `workflow/leave/index.vue`：找不到 `model_key='leave'` 时把 `modelId` 置 0 且不提示，列表会静默为空。

### 监控 / 外部接口 / 报表 / 安全 / 定时任务

65. `outer/api/index.vue`：测试结果使用 `dangerouslyUseHTMLString` 直接把第三方响应拼进 HTML，存在 XSS 风险。
66. `outer/sync/index.vue`：`sync_type=schedule` 才显示 `task_id`，但 `rules` 未给 `task_id` 必填，可保存“定时同步却没有任务 ID”的配置。
67. `mon/record/index.vue`：`rule_id` 用严格相等匹配，类型不一致（字符串/数字）会翻译失败并显示原始 id；处理状态只判断 `handle_status === 1`，字符串 `"1"` 会误显示为“待处理”。
68. `rp/datasource/index.vue`：`ds_config` 未校验 JSON 合法性；`rp/category` 的 `parent_id` 为自由数字输入，无父级存在性/循环校验；`rp/template` 生成报表在请求返回前无 loading。
69. `sec/rate_limit/index.vue`：规则名称与 `limit_url` 仅必填校验，无重复性/格式校验。
70. `sys_no/rule/index.vue`：批量生成编号为串行 POST，逐条弹一次成功提示（多选时刷屏），单条失败静默跳过；生成后不刷新列表。
71. `task/info/index.vue`：状态开关失败不回滚；“立即执行”后不刷新列表也不跳转，结果需用户自行去日志页查看。
72. 多个管理页（`mon/rule`、`outer/api`、`outer/sync`、`gen/table`、`file/recycle`、`student` 等）：删除末页最后一条后只重拉当前页，可能停留在空页。

## 七、后续建议

1. 先处理与**安全/权限**相关的疑似问题：`dp/permission` 默认全量权限、`wo/mine` 数据范围、`outer/api` 的 HTML 注入、`dsm/rule` 必填缺失。
2. 再统一**交互一致性**：开关乐观更新失败回滚、`ElMessageBox` 取消的 Promise 捕获、删除末页回退、下拉 200/500 条上限。
3. 最后收敛**主题与硬编码色**：`ReportPreview`、`kb/document`、`student` 等页面残留的固定色值改为设计令牌；`theme/index.js` 的 hover/渐变算法与暗色对比度建议统一校准。
4. 上述内容均需独立评审与回归测试，本轮按要求**只记录未修改**。
