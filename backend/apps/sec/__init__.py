
# 文件：apps/sec/__init__.py —— 安全策略应用的包入口
# 用途：声明 apps.sec 是一个 Python 包，使 Django 能按点分路径加载 apps.py、models.py、views.py 等模块。
# 对应表：本文件无任何逻辑；该应用涉及 sys_ip_control（IP 黑白名单）、
#         sys_login_attempt（登录尝试流水）、sys_rate_limit（接口限流规则）三张表。
# 路由前缀：包本身不含路由，实际接口由 apps/sec/urls.py 提供，挂载在 /api/sec/ 下。
# 生效范围：仅包初始化，不包含 IP 匹配或限流判定；这些策略是否接入登录链路以实际代码为准（当前以配置与演示为主）。
# 说明：刻意保持为空，避免应用加载阶段执行代码导致循环导入或提前访问数据库。
