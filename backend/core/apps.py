# ----------------------------------------------------------------------------
# core 应用配置模块
# 用途：向 Django 注册 core 应用，声明应用导入路径与后台显示名；
#       本应用只提供管理命令，不定义模型、视图和路由。
# 调用：settings.py 的 INSTALLED_APPS 中登记 "core"（或 "core.apps.CoreConfig"），
#       Django 启动时自动加载本配置，随后才能使用 `python manage.py init_db`。
# 依赖表：无（应用本身不建表）。
# ----------------------------------------------------------------------------
# 应用配置模块：向 Django 声明 core 应用的元信息，供 INSTALLED_APPS 加载。
from django.apps import AppConfig  # AppConfig 是应用配置基类，用于登记应用名与后台展示名


class CoreConfig(AppConfig):
    # core 应用配置类：该应用只承载自定义管理命令（init_db / seed_new_modules），不含数据模型
    name = 'core'  # 应用模块的 Python 导入路径，必须与 INSTALLED_APPS 中的字符串保持一致
    verbose_name = '核心命令'  # Django 后台显示的中文应用名，便于运营人员识别用途
