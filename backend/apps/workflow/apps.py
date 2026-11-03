"""工作流模块应用配置。"""
from django.apps import AppConfig  # Django 应用配置基类


class WorkflowConfig(AppConfig):
    """工作流应用：默认主键类型与显示名称。"""
    default_auto_field = 'django.db.models.BigAutoField'  # 默认 bigint 主键
    name = 'apps.workflow'  # Python 包路径
    verbose_name = '工作流审批'  # 后台显示名称
