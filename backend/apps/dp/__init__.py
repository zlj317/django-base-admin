
# 文件：backend/apps/dp/__init__.py
# 用途：标记 apps/dp 为 Python 包，Django 通过 apps.dp 导入本模块下的 models/views/urls/seed。
# 对应表：sys_data_permission、sys_role_data_permission（由 models.py 映射）。
# 路由前缀：/api/dp/（由 config/urls.py 注册）。
# 数据范围生效方式：本文件不含逻辑，数据权限规则在当前代码中仅做配置/预留，未接入业务列表过滤。
