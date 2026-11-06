# 文件：apps/backup/apps.py —— 数据备份应用的 AppConfig 配置
# 用途：向 Django 注册 backup 应用，声明应用路径与默认主键类型；
#       应用启动时 Django 会通过该配置定位 models.py、views.py、urls.py。
# 对应表：本文件不涉及数据表；实际模型为 backup_record / backup_strategy（见 models.py）。
# 路由前缀：/api/backup/record/、/api/backup/strategy/（由 config/urls.py 统一 include）。
# 幂等性：AppConfig 只做类声明，导入多次不会产生重复注册或数据写入。
# django.apps.AppConfig：Django 应用配置基类，用于描述单个应用的元信息
from django.apps import AppConfig


# 备份应用的配置类；Django 在 INSTALLED_APPS 中识别 'apps.backup' 时使用它
class BackupConfig(AppConfig):
    # 默认主键字段类型：显式指定 BigAutoField，避免旧版默认 AutoField 与新模型不一致的警告
    default_auto_field = 'django.db.models.BigAutoField'
    # 应用的点分导入路径；决定了 apps.backup.models / views / urls 的可导入位置
    name = 'apps.backup'
