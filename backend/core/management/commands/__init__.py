# ----------------------------------------------------------------------------
# core.management.commands 包（管理命令实现目录）
# 用途：存放可被 Django 自动发现的命令模块，文件名决定命令名：
#       init_db.py          -> python manage.py init_db
#       seed_new_modules.py -> python manage.py seed_new_modules
# 调用：在 backend 目录执行上述命令；每个模块必须提供 Command(BaseCommand) 子类。
# 依赖表：无；具体命令涉及的表清单见对应文件头注释。
# ----------------------------------------------------------------------------
# commands 包初始化文件：标识目录为 Python 包，Django 据此扫描其中的管理命令模块。
# 每个命令文件需定义 Command 类，文件名即 `python manage.py <命令名>` 使用的命令名。
