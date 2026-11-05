"""3D 可视化应用配置。"""
from django.apps import AppConfig  # Django 应用配置基类


class Scene3dConfig(AppConfig):
    """3D 可视化/数字孪生模块：表由 docs/scene3d_init.sql 手工创建。"""

    default_auto_field = 'django.db.models.BigAutoField'  # 默认主键类型，与全站保持一致
    name = 'apps.scene3d'  # 应用 Python 路径，需与 INSTALLED_APPS 中登记的字符串一致
    verbose_name = '3D可视化'  # 后台展示的中文名称
