# 文件：backend/apps/dp/apps.py
# 用途：声明 Django 应用配置，让 config/settings.py 中的 'apps.dp' 能被正确加载。
# 对应表：sys_data_permission、sys_role_data_permission（模型在 apps/dp/models.py 中定义）。
# 路由前缀：/api/dp/（由 config/urls.py include apps.dp.urls）。
# 数据范围生效方式：应用配置本身不参与权限计算；数据权限规则当前仅为配置/预留。
# Django 应用配置基类，供 INSTALLED_APPS 注册使用
from django.apps import AppConfig


# 数据权限应用配置类：Django 启动时根据 apps.py 与 INSTALLED_APPS 中的 'apps.dp' 加载本应用
class DpConfig(AppConfig):
    # 默认主键类型：Django 4.x 对显式未声明主键的模型使用 BigAutoField
    # 本模块实际主键由 SnowflakeIDField 显式指定，该项只影响未显式声明主键的模型
    default_auto_field = 'django.db.models.BigAutoField'
    # 应用导入路径：必须与 settings.INSTALLED_APPS 中的字符串一致，否则模型注册与迁移检测会失败
    name = 'apps.dp'
