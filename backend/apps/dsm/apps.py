# 模块：apps/dsm/apps.py —— 脱敏配置模块的 Django 应用配置入口
# 用途：向 Django 注册本应用的导入路径与默认主键类型，使模型、路由、种子脚本能被框架发现。
# 对应表：本文件不定义表；脱敏规则/字段/角色见 apps/dsm/models.py。
# 调用方：settings.INSTALLED_APPS 中的 'apps.dsm'，Django 启动时自动加载 DsmConfig。
# 脱敏策略：本文件只做应用注册，不涉及任何脱敏逻辑；脱敏规则目前仅为配置项，不会自动作用于接口输出。
from django.apps import AppConfig


# 应用配置类：Django 用它在 ready 阶段定位应用并初始化（本类未重写 ready，无额外启动逻辑）
class DsmConfig(AppConfig):
    # 未显式声明主键的模型默认使用 64 位自增主键；本模块模型实际都用雪花 ID 主键
    default_auto_field = 'django.db.models.BigAutoField'
    # 应用的点分导入路径，必须与 INSTALLED_APPS 中的 'apps.dsm' 完全一致
    name = 'apps.dsm'
