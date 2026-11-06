
# 任务调度模块包初始化文件。
# 模块用途：聚合定时任务主表 task_info 与任务日志表 task_log 的模型、序列化器、视图与路由。
# 对应路由：apps/task_sched/urls.py，最终由 config/urls.py 的 include 挂载到 /api/task/ 前缀。
# 权限：视图层通过 perm_prefix='task' 生成 task:list/create/update/delete 等权限标识。
# 被谁调用：config/settings.py 的 INSTALLED_APPS 注册 apps.task_sched，Django 启动时导入本包。
