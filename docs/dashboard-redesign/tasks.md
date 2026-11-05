# 首页充实改造 —— 任务清单（Tasks）

> 对应 `docs/dashboard-redesign/spec.md`。按顺序执行，每完成一项即更新状态。

## T1 后端聚合接口
- [x] `apps/home/views.py` 新增 `rich()`：统计卡 + 7 日趋势 + 待办/公告/消息/工作流 + 文件/任务/告警/用户/报表/BI/知识库/日程。
- [x] `apps/home/urls.py` 新增 `rich/` 路由。
- [x] 防御式查询，表/列缺失返回空，不抛 500。
- [x] 中文注释逐行覆盖。

## T2 前端图表组件
- [x] `components/dashboard/TrendChart.vue`：SVG 折线/面积图，主题令牌配色。
- [x] `components/dashboard/DistributionBar.vue`：分布条，主题令牌配色。
- [x] 逐行中文注释。

## T3 首页重构（核心）
- [x] 修复 `.panel` 宽度收缩根因（`width:100%; min-width:0`）。
- [x] 指标卡补真实 sparkline + 环比。
- [x] 新增 Row A-D 各面板与 Row E 分组常用功能。
- [x] 接入 `/api/home/rich/`，保留 `/overview/` 兜底。
- [x] 空数据 → 引导型卡片（用途 + 跳转）。
- [x] 关键跳转全部可点击。
- [x] 逐行中文注释（template/script/style）。

## T4 主题适配
- [x] 清理本次涉及区域内的硬编码色；图表颜色走 `--chart-*`。
- [x] 亮色/暗色下卡片、图表、标签对比度检查。

## T5 实测与修复
- [x] 后端 `GET /api/home/rich/` 真实验证（正常/无 token）。
- [x] 浏览器 1440 / 1280 截图，确认无横向空洞、同行等高。
- [x] 主题 4 组（亮 blue / 暗 blue / 亮 purple / 暗 rose）截图。
- [x] 点击跳转与控制台报错检查。
- [x] `npm run build` exit 0（1,321.42 kB 主包，未新增依赖）。
- [x] 发现问题最小改动修复并回归。

## T6 文档
- [x] 需求文档追加“实现状态”。
- [x] README 首页模块清单同步（不动架构图）。
- [x] 截图归档 `docs/images/dashboard/`。

## T7 汇报
- [x] 根因、新增卡片与数据来源、改动文件、验证记录、限制、截图路径。
