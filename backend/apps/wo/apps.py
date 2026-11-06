# 文件：apps/wo/apps.py —— 工单应用的 AppConfig 配置
# 用途：向 Django 注册 wo 应用，声明应用点分路径与默认主键类型；
#       应用启动时 Django 依据该配置加载 apps.wo 下的 models、views、urls。
# 对应表：本文件不涉及数据表；业务模型见 models.py（work_order_type / work_order / work_order_log）。
# 路由前缀：/api/wo/type/、/api/wo/order/、/api/wo/log/（由 config/urls.py 统一 include）。
# 幂等性：AppConfig 仅是类声明，重复导入不会产生重复注册或数据写入。
from django.apps import AppConfig

# 工单应用的配置类；INSTALLED_APPS 中出现 'apps.wo' 时由 Django 使用它
class WoConfig(AppConfig):
    # 默认主键字段类型：显式声明 BigAutoField，避免 Django 默认值变化带来的迁移告警
    default_auto_field = 'django.db.models.BigAutoField'
    # 应用点分路径：决定 apps.wo.models / views / urls 的可导入位置
    name = 'apps.wo'
