# 模块：apps/notice/apps.py —— 公告模块的应用配置入口
# 用途：向 Django 注册公告应用的导入路径与默认主键类型，使模型、路由、种子脚本能被框架自动发现。
# 关键约定：name 必须与 settings.INSTALLED_APPS 中的 'apps.notice' 完全一致，否则模型会被重复注册。
from django.apps import AppConfig

# 公告模块的应用配置类：Django 启动时按 INSTALLED_APPS 自动实例化。
class NoticeConfig(AppConfig):
    # 模型未显式声明主键时使用的默认主键类型；本项目实际主键均由 SnowflakeIDField 指定。
    default_auto_field = 'django.db.models.BigAutoField'
    # 应用点分路径，Django 据此定位 apps/notice 目录并加载其中的 models。
    name = 'apps.notice'
