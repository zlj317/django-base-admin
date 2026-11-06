# 模块：apps/scene3d/__init__.py —— 3D 可视化（数字孪生）应用的包入口文件
# 用途：把 apps/scene3d 标记为可导入的 Python 包，Django 据此加载 apps.py 与子模块。
# 调用方：config/settings.py 的 INSTALLED_APPS 登记 'apps.scene3d'，启动时由 Django 自动导入本包。
# 幂等性：本文件只有包声明，不执行任何逻辑、不访问数据库，重复导入安全。
# 涉及表：无（模型声明见 models.py，表结构见 docs/scene3d_init.sql）。
"""3D 可视化（数字孪生）模块包。"""  # 包声明，供 Django 识别应用包
