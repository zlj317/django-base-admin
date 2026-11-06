# 文件：apps/sec/apps.py —— 安全策略应用的 Django 配置
# 用途：向 Django 登记本应用的导入路径与默认主键类型，使框架能加载模型、视图与路由。
# 对应表：本文件不落库；它服务的模块涉及 sys_ip_control（IP 黑白名单）、
#         sys_login_attempt（登录尝试流水）、sys_rate_limit（接口限流规则）三张表。
# 路由前缀：应用本身不声明路由，实际接口地址由 config/urls.py 挂载为 /api/sec/。
# 生效范围：仅应用加载配置，与 IP 拦截/限流策略是否生效无关（策略执行与否以实际调用代码为准，
#           当前以配置与演示为主，未接入登录链路）。
# 引用关系：settings.INSTALLED_APPS 中的 'apps.sec' 会让 Django 自动发现并实例化本配置类。
from django.apps import AppConfig

# 上一行引入 Django 应用配置基类：负责注册应用、设置默认字段类型。


# 应用配置类：Django 启动时按 name 指定的路径找到这里，注册应用元信息
class SecConfig(AppConfig):
    # 模型未显式声明主键时使用的默认主键类型；本项目模型多用雪花 ID，此处只是框架级兜底
    default_auto_field = 'django.db.models.BigAutoField'
    # 应用的点分导入路径，必须与 INSTALLED_APPS 中登记的字符串完全一致，否则模型无法关联
    name = 'apps.sec'
