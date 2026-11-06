# 模块：backend/apps/__init__.py —— 后端各业务应用的包标记文件（原文件为空）
# 用途：把 apps 目录声明为 Python 包，使 'apps.dsm'、'apps.system' 等点分导入路径可被解析。
# 内容策略：保持空初始化，不在此处导入任何子应用，避免 Django 启动阶段出现循环导入或副作用。
# 应用注册：具体应用的配置类位于各自目录的 apps.py，由 settings.INSTALLED_APPS 统一加载。
