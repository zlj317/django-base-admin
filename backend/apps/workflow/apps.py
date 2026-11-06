"""工作流模块应用配置。"""
# 模块：apps/workflow/apps.py —— 工作流（审批）模块的应用配置入口
# 用途：向 Django 注册 apps.workflow，使 11 张 wf_ 表模型、/api/wf/ 路由可被框架发现与加载。
# 数据表：wf_category、wf_form、wf_group、wf_group_user、wf_model、wf_instance、wf_task、
#         wf_audit、wf_cc、wf_listener、wf_expression（均 managed=False，由建表 SQL 维护）。
# 调用方：settings.INSTALLED_APPS 中的 'apps.workflow'，Django 启动时自动实例化 WorkflowConfig。
# 关键约定：本文件不定义模型、不注册路由，只声明应用元信息，避免启动阶段产生额外副作用。
# Django 应用配置基类：每个 app 用它声明导入路径、默认主键类型与后台显示名
from django.apps import AppConfig  # Django 应用配置基类


# 应用配置类：Django 通过它识别应用并完成模型加载，名称必须与 INSTALLED_APPS 一致
class WorkflowConfig(AppConfig):
    # 应用元信息：默认主键类型、导入路径、后台显示名
    """工作流应用：默认主键类型与显示名称。"""

    # 主键与标识：default_auto_field 仅影响未显式声明主键的模型，本项目实际主键均为雪花 ID
    default_auto_field = 'django.db.models.BigAutoField'  # 默认 bigint 主键
    # 应用的点分导入路径，Django 据此定位 apps/workflow 下的模型、视图与模板
    name = 'apps.workflow'  # Python 包路径
    # 后台/管理界面展示名称，便于运维识别模块归属
    verbose_name = '工作流审批'  # 后台显示名称
