# 模块：apps/imprint/apps.py —— Django 应用配置类。
# 用途：向 Django 注册 imprint 应用（导入模板 + 打印模板），使模型能被 ORM 发现。
# 对应表：imp_template、imp_template_column、print_template（模型定义在 models.py）。
# 路由前缀：/api/imprint/（config/urls.py include 本模块 urls.py）。
# 幂等性：只做应用元信息声明，加载过程不写库、不产生副作用。
from django.apps import AppConfig


# 应用配置：Django 4.x 推荐显式声明，便于将来在 ready() 中挂信号或启动检查。
class ImprintConfig(AppConfig):
    # 未显式指定主键的模型默认用 BigAutoField（本模块模型均已自定义主键）
    default_auto_field = 'django.db.models.BigAutoField'
    # 应用完整导入路径，必须与 INSTALLED_APPS 中的注册项一致
    name = 'apps.imprint'
