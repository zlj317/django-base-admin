"""学生信息表 应用配置。"""
# 模块用途：学生信息表模块的 Django 应用配置，向框架登记应用路径与后台展示名称。
# 对应表：本身不落库，只为 biz_student（学生信息表）模块提供加载配置。
# 被谁引用：settings.INSTALLED_APPS 中的 'apps.student' 触发 Django 自动发现并实例化本配置类。
# 生成约定：配置类名固定为 Biz{模块名}Config，name 必须与 INSTALLED_APPS 里的点分路径完全一致；
#           未声明 default_auto_field 时沿用 settings.DEFAULT_AUTO_FIELD（本项目为 BigAutoField）。
from django.apps import AppConfig  # 引入应用配置基类，用于声明应用元信息


# 继承 AppConfig：显式声明应用元信息，Django 启动时据此注册模型、信号与后台显示名称。
class BizStudentConfig(AppConfig):
    """学生信息表应用配置：注册应用路径与后台显示名称。"""

    name = 'apps.student'  # 应用的点分导入路径，Django 据此加载本应用
    verbose_name = '学生信息表'  # 后台应用列表展示的中文名称
