# 模块：apps/report/apps.py —— 报表模块的应用配置入口
# 用途：向 Django 注册报表应用的导入路径与默认自增字段类型，使模型、路由、模板可被框架发现。
# 数据表：本文件不定义表；报表分类/数据源/模板/生成记录见 apps/report/models.py。
# 调用方：settings.INSTALLED_APPS 中的 'apps.report'，Django 启动时自动实例化为 ReportConfig。
# 说明：default_auto_field 只影响本应用内模型的默认主键类型，本项目主键实际使用雪花 ID 字段。
from django.apps import AppConfig

# Django 要求每个应用提供 AppConfig 子类，作为注册与初始化入口
class ReportConfig(AppConfig):
    # 未显式声明主键时的默认自增类型（BigAutoField 避免 32 位溢出）
    default_auto_field = 'django.db.models.BigAutoField'
    # 应用的点分导入路径，Django 据此定位本应用下的模块与模板
    name = 'apps.report'
