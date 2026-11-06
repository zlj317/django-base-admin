"""3D 可视化应用配置。"""
# 模块：apps/scene3d/apps.py —— 3D 可视化（数字孪生）应用的 AppConfig 声明
# 用途：向 Django 注册应用 Python 路径、默认主键类型与后台中文名称，不定义任何模型。
# 调用方：INSTALLED_APPS 中的 'apps.scene3d'，Django 启动时自动加载本配置类。
# 幂等性：仅类属性声明，无数据库访问与副作用，重复加载不会产生重复数据。
# 涉及表：无（13 张 scene3d_* 物理表由 docs/scene3d_init.sql 手工创建，模型为 managed=False）。
from django.apps import AppConfig  # Django 应用配置基类


# 应用配置类：声明本应用的元信息，Django 通过它识别应用名称与主键策略
class Scene3dConfig(AppConfig):
    """3D 可视化/数字孪生模块：表由 docs/scene3d_init.sql 手工创建。"""

    default_auto_field = 'django.db.models.BigAutoField'  # 默认主键类型，与全站保持一致
    name = 'apps.scene3d'  # 应用 Python 路径，需与 INSTALLED_APPS 中登记的字符串一致
    verbose_name = '3D可视化'  # 后台展示的中文名称
