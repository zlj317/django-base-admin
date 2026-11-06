
# 文件：apps/bi/__init__.py —— 大屏 BI 应用的包入口
# 用途：声明 apps.bi 为一个 Python 包，使 Django 能按点分路径加载 AppConfig、models、views、urls。
# 数据表：本文件无逻辑；该应用涉及 bi_screen（大屏）、bi_dataset（数据集）、bi_visit_log（访问日志）。
# 路由前缀：/api/bi/screen、/api/bi/dataset、/api/bi/visit，以及分享入口 /api/bi/screen/share/<token>。
# 说明：包初始化不放任何代码，避免应用加载阶段产生循环导入或提前访问数据库。
