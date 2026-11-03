from django.apps import AppConfig  # Django 应用配置基类，用于声明应用元信息


class SystemConfig(AppConfig):
    """平台基础模块应用配置：注册应用路径与后台显示名称。"""
    name = 'apps.system'  # 应用的点分导入路径
    verbose_name = '平台基础模块'  # 后台展示的中文模块名
