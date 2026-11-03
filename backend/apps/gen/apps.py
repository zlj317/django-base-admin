"""代码生成器应用配置。"""
from django.apps import AppConfig  # 引入应用配置基类，用于声明应用元信息


class GenConfig(AppConfig):
    """代码生成器应用配置：注册应用路径与后台显示名称。"""

    name = 'apps.gen'  # 应用的点分导入路径，Django 据此加载本应用
    verbose_name = '代码生成器'  # 后台应用列表展示的中文名称
