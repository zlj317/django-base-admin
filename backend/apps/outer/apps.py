# 外部对接（outer）模块的 Django 应用配置。
# 作用：向框架注册 apps.outer，Django 启动时据此加载本模块的模型与配置。
# 对应表：outer_api_config / outer_api_request_log / outer_sync_task，均由 docs 建表 SQL 手工创建。
# 路由：config/urls.py 将 apps/outer/urls.py 挂载在 /api/outer/ 前缀下。
from django.apps import AppConfig


# 应用配置类：INSTALLED_APPS 中写 'apps.outer' 时，框架优先使用本类的配置项。
class OuterConfig(AppConfig):
    # 默认自增主键类型；本项目模型主键均显式使用 SnowflakeIDField，该配置仅作兜底。
    default_auto_field = 'django.db.models.BigAutoField'
    # 应用的 Python 导入路径，必须与 INSTALLED_APPS 中的字符串一致，否则模型不会注册。
    name = 'apps.outer'
