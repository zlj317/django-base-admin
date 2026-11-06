
# 外部对接（outer）模块包入口。
# 模块用途：集中提供「外部 API 配置 / 调用请求日志 / 数据同步任务」三类管理接口。
# 对应表：outer_api_config、outer_api_request_log、outer_sync_task（均由 docs 建表 SQL 手工创建，managed=False）。
# 路由前缀：config/urls.py 将其挂载到 /api/outer/，前端页面为 outer/api、outer/log、outer/sync。
# 现状：以接口配置与调试为主；同步任务仅登记定义并通过 task_id 关联 task_info，未真正驱动报表或大屏。
