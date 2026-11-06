
# 模块：apps/report/__init__.py —— 报表模块的 Python 包入口
# 用途：把 apps.report 声明为可导入包，供 settings INSTALLED_APPS 与路由 include 时加载。
# 数据表：本文件无模型定义；实际表映射见 apps/report/models.py 的 rp_* 系列表。
# 调用方：backend/config/settings.py 注册应用、backend/config/urls.py 挂载 apps.report.urls。
# 说明：不在包初始化阶段导入业务代码，避免模型加载与应用配置的循环依赖。
