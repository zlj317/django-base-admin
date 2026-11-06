# 首页聚合模块的 AppConfig。
# 该模块不建表（除 home_user_config 外以只读聚合为主），只注册配置供 Django 识别应用。
from django.apps import AppConfig  # Django 应用配置基类


class HomeConfig(AppConfig):
    # 主键类型：与项目其它模块保持一致，使用 BigAutoField 兜底
    default_auto_field = 'django.db.models.BigAutoField'
    # 应用导入路径，需与 backend/apps/home 目录一致
    name = 'apps.home'
