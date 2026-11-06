# 模块：apps/mon/__init__.py —— 监控告警模块的包标识文件
# 用途：把 apps/mon 声明为 Python 包，供 Django 以应用形式加载（无需导出任何符号）。
# 对应表：monitor_alarm_rule / monitor_alarm_record（见同目录 models.py）。
# 路由前缀：/api/mon/（见同目录 urls.py，由 config/urls.py include）。
# 说明：本文件保持无业务代码，仅作包入口；告警生命周期的实现见 models.py / views.py。
