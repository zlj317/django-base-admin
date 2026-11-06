"""项目配置包。

使用 PyMySQL 代替 mysqlclient 连接 MySQL（纯 Python 实现，Windows 下无需编译）。
"""
# ============================== 文件说明 ==============================
# 作用：config 包的初始化文件，导入 config 包时自动执行（Python 包的固有行为）。
# 被谁加载：当 DJANGO_SETTINGS_MODULE=config.settings 时，Django 先导入 config 包，
#           再导入 config.settings，因此本文件会早于 settings.py 执行。
# 关键约定：
#   1) 必须在建立数据库连接之前完成 PyMySQL 伪装，否则 MySQL 后端会尝试导入
#      mysqlclient 并抛出 ImproperlyConfigured；
#   2) 本文件只做驱动适配，不放置业务代码或数据库访问，避免扩大启动副作用；
#   3) version_info 是 Django 校验数据库驱动版本的依据，缺失会被判定版本过低；
#   4) 依赖 pymysql 已写入 requirements.txt，未安装时配置导入会直接失败（属预期）。
# 注意：不要在此 import Django 配置，否则会与 settings 的加载顺序形成循环导入。
# ============================== 驱动适配 ==============================
# 纯 Python 的 MySQL 驱动，替代需要本地编译的 mysqlclient（Windows 下尤其友好）
import pymysql

# 伪造 mysqlclient 的版本元组：Django 会读取该属性并校验最低版本要求
# 取值 1.4.6 为 mysqlclient 常见版本号，格式为 (主,次,微,发布级别,序号)
pymysql.version_info = (1, 4, 6, "final", 0)  # Django 会校验 mysqlclient 版本号
# 将 pymysql 注册为 MySQLdb：使 django.db.backends.mysql 能按原名导入
# 这是一次全局猴子补丁，只需执行一次，后续所有 MySQL 连接都走 pymysql
pymysql.install_as_MySQLdb()
# 至此驱动适配完成；后续 settings 中 ENGINE=django.db.backends.mysql 才能正常加载
# 若运行时报 "Error loading MySQLdb module"，优先检查本文件是否被提前执行
# 说明：本包不导出任何公开符号，业务代码请直接 import config.settings 的属性
