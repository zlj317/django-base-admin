"""项目配置包。

使用 PyMySQL 代替 mysqlclient 连接 MySQL（纯 Python 实现，Windows 下无需编译）。
"""
import pymysql

pymysql.version_info = (1, 4, 6, "final", 0)  # Django 会校验 mysqlclient 版本号
pymysql.install_as_MySQLdb()
