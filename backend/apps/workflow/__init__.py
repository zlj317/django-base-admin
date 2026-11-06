# 模块：apps/workflow/__init__.py —— 工作流（审批）模块的 Python 包入口
# 用途：把 apps.workflow 声明为可导入包，供 settings.INSTALLED_APPS 与 /api/wf/ 路由 include 时加载。
# 数据表：本文件不定义模型；11 张表见 apps/workflow/models.py：
#         wf_category、wf_form、wf_group、wf_group_user、wf_model、wf_instance、wf_task、
#         wf_audit、wf_cc、wf_listener、wf_expression（全部 managed=False，由建表 SQL 维护）。
# 路由前缀：wf（/api/wf/，见 apps/workflow/urls.py），视图与引擎分别在 views.py、engine.py。
# 关键约定：包初始化阶段不导入任何业务代码，避免模型加载与应用配置产生循环依赖。
