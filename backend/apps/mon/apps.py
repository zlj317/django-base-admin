# 模块：apps/mon/apps.py —— 监控告警模块的 Django 应用配置
# 用途：向 Django 注册 apps.mon 应用，声明默认主键字段类型。
# 对应表：monitor_alarm_rule / monitor_alarm_record（实际建表由 docs 的 SQL 完成）。
# 路由前缀：/api/mon/（在 config/urls.py 中 include 本模块 urls.py）。
# 告警生命周期：本文件不含业务逻辑，仅承载应用级配置。
# Django 应用配置基类
from django.apps import AppConfig


# 应用配置类：Django 启动时按 INSTALLED_APPS 中的 apps.mon 加载
class MonConfig(AppConfig):
    # 未显式声明主键时使用的默认主键类型（本模块模型均已显式使用雪花 ID）
    default_auto_field = 'django.db.models.BigAutoField'
    # 应用点路径：必须与 INSTALLED_APPS 中的注册名一致
    name = 'apps.mon'
