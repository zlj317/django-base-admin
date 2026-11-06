
# 文件：apps/backup/__init__.py —— 数据备份模块的包入口
# 用途：声明 apps.backup 是一个 Python 包，使 Django 能按点分路径加载 AppConfig、models、views、urls。
# 对应表：本文件无逻辑；该应用涉及 backup_record（备份记录）与 backup_strategy（备份策略）两张表。
# 路由前缀：/api/backup/record/（记录）、/api/backup/strategy/（策略），由 config/urls.py 挂载。
# 幂等性：包初始化不放任何代码，重复导入不会产生副作用，也不会提前访问数据库或产生循环导入。
# 约定：保持空实现，仅用于包声明；业务初始化统一放在 apps.py 的 AppConfig 中。
