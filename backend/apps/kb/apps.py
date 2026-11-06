# 文件：apps/kb/apps.py —— 知识库模块的 Django 应用配置
# 用途：向 Django 注册 apps.kb 应用，声明默认主键类型与应用点分路径。
# 对应表：无（本文件不直接操作数据库）。
# 路由前缀：api/kb/（由 config/urls.py 以 include('apps.kb.urls') 挂载）。
# 关键约定：业务表由手工建表 SQL 创建，models 中 managed=False，本配置不参与 migrate 建表。
# Django 应用配置基类；每个 app 用它描述自身元信息
from django.apps import AppConfig

# 应用配置类：Django 启动时按 INSTALLED_APPS 里的 'apps.kb' 自动发现该默认配置
class KbConfig(AppConfig):
    # 未显式声明主键的模型默认使用 BigAutoField（64 位自增），避免旧默认 32 位溢出
    default_auto_field = 'django.db.models.BigAutoField'
    # 应用点分路径，必须与 INSTALLED_APPS 中的注册名完全一致，否则模型不会被加载
    name = 'apps.kb'
