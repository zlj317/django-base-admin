# 模块：backend/apps/dsm/__init__.py —— 脱敏配置应用的包标记文件（原文件为空）
# 用途：让 Python 把 apps/dsm 识别为普通包，便于导入 models/serializers/views/urls/seed。
# 内容策略：这里不放置任何初始化逻辑，避免应用导入时产生副作用（Django 的启动逻辑放在 apps.py）。
# 脱敏策略：本文件不参与脱敏；脱敏规则为配置/预留，未接入任何序列化器或中间件的输出链路。
