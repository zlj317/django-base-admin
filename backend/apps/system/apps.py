# 模块：apps/system/apps.py —— 系统模块的 Django 应用配置
# 用途：向 Django 声明应用路径与后台显示名称，settings.INSTALLED_APPS 中的 'apps.system' 据此加载。
# 数据表：本文件不涉及模型与数据表，仅提供应用元信息。
# 引用：config/settings.py 的 INSTALLED_APPS 通过点分路径加载本配置类。
from django.apps import AppConfig  # Django 应用配置基类，用于声明应用元信息


# 应用配置类：Django 加载 INSTALLED_APPS 时实例化，用于登记应用路径与展示名称
class SystemConfig(AppConfig):
    """平台基础模块应用配置：注册应用路径与后台显示名称。"""
    name = 'apps.system'  # 应用的点分导入路径
    verbose_name = '平台基础模块'  # 后台展示的中文模块名
