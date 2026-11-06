# 文件：apps/bi/apps.py —— 大屏 BI 应用的 AppConfig 声明
# 用途：Django 启动时按 name='apps.bi' 注册本应用，进而加载 models 与 urls。
# 数据表：本文件不定义表；所属应用使用 bi_screen / bi_dataset / bi_visit_log。
# 路由前缀：/api/bi/（screen、dataset、visit、screen/share/<token>）。
# 说明：该应用的表由 docs 下的 SQL 手工创建，模型统一 managed=False，因此这里无需额外配置。

# 引入应用配置基类，Django 启动时据此完成应用注册
from django.apps import AppConfig


# 大屏 BI 应用配置类：INSTALLED_APPS 中的 'apps.bi' 会实例化它
class BiConfig(AppConfig):
    # 未显式声明主键的模型默认使用 BigAutoField，避免系统检查出现 W042 警告
    default_auto_field = 'django.db.models.BigAutoField'
    # 应用的点分路径，必须与 INSTALLED_APPS 中的条目完全一致
    name = 'apps.bi'
