# 模块：apps/sys_no/apps.py —— 编码规则模块的 Django 应用配置
# 用途：向 Django 声明本模块的 AppConfig（应用路径 apps.sys_no），供 INSTALLED_APPS 加载、
#       模型注册与信号发现使用；Django 3.2+ 要求显式声明默认主键类型。
# 关联：本模块的表 sys_no_rule / sys_no_log 均由手工 SQL 建表，模型侧 managed=False（见 models.py）。
from django.apps import AppConfig


# 应用配置类：Django 启动时按 INSTALLED_APPS 中的 'apps.sys_no' 自动定位到本类
class SysNoConfig(AppConfig):
    # 默认主键类型：本模块模型已显式使用雪花 ID（SnowflakeIDField），
    # 该配置仅用于满足 Django 对未显式声明主键模型的默认值要求。
    default_auto_field = 'django.db.models.BigAutoField'
    # 应用路径必须与 INSTALLED_APPS 注册值一致，否则模型无法归属到本应用
    name = 'apps.sys_no'
