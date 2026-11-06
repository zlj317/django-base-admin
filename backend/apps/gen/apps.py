"""代码生成器应用配置。"""
# 模块：apps/gen/apps.py —— 代码生成器（在线建表/配置/出码）的应用入口配置
# 用途：向 Django 注册应用导入路径与后台展示名称，使模型、路由、模板能被框架发现。
# 数据表：本文件不定义表；生成配置存于 sys_gen_table、sys_gen_table_column（managed=False）。
# 调用方：settings.INSTALLED_APPS 中的 'apps.gen'，Django 启动时自动实例化为 GenConfig。
from django.apps import AppConfig  # 引入应用配置基类，用于声明应用元信息


# Django 要求每个应用提供一个 AppConfig 子类，作为注册与应用初始化的入口
class GenConfig(AppConfig):
    """代码生成器应用配置：注册应用路径与后台显示名称。"""

    name = 'apps.gen'  # 应用的点分导入路径，Django 据此加载本应用
    verbose_name = '代码生成器'  # 后台应用列表展示的中文名称
