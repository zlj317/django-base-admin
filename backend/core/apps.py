# 应用配置模块：向 Django 声明 core 应用的元信息，供 INSTALLED_APPS 加载。
from django.apps import AppConfig  # AppConfig 是应用配置基类，用于登记应用名与后台展示名


class CoreConfig(AppConfig):
    # core 应用配置类：该应用只承载自定义管理命令（init_db / seed_new_modules），不含数据模型
    name = 'core'  # 应用模块的 Python 导入路径，必须与 INSTALLED_APPS 中的字符串保持一致
    verbose_name = '核心命令'  # Django 后台显示的中文应用名，便于运营人员识别用途
