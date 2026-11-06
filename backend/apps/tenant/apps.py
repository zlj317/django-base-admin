# 文件：apps/tenant/apps.py —— 多租户应用的 AppConfig 配置
# 用途：声明 apps.tenant 应用的名称与默认主键类型，Django 启动时据此加载模型、信号与路由。
# 对应表：sys_tenant、sys_tenant_user、sys_tenant_package（模型文件 apps/tenant/models.py）。
# 路由前缀：/api/tenant/（在 config/urls.py 中 include 本应用 urls.py）。
# 租户隔离：AppConfig 不注册任何租户上下文中间件，因此应用启动阶段不存在自动租户隔离。
# Django 应用配置基类
from django.apps import AppConfig


# 应用配置类：Django 1.9+ 默认从 apps.py 自动发现，无需在 __init__.py 中设置 default_app_config
class TenantConfig(AppConfig):
    # 未显式声明主键类型时的默认值；本应用模型均使用 SnowflakeIDField，实际不依赖该配置
    default_auto_field = 'django.db.models.BigAutoField'
    # 应用的点分路径，必须与 INSTALLED_APPS 中的 'apps.tenant' 完全一致，否则模型无法注册
    name = 'apps.tenant'
