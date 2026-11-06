# 模块：apps/gen/__init__.py —— 代码生成器应用的 Python 包入口
# 用途：把 apps.gen 声明为可导入包，供 settings INSTALLED_APPS 与路由 include 时加载。
# 数据表：本文件无模型定义；实际表映射见 apps/gen/models.py 的 sys_gen_table 与 sys_gen_table_column。
# 调用方：backend/config/settings.py 注册应用、backend/config/urls.py 挂载 apps.gen.urls。
# 说明：包初始化阶段不引入任何业务代码，避免与应用配置、模型加载形成循环导入。
