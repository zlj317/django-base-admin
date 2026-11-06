# 模块：apps/system/__init__.py —— 平台基础模块的 Python 包入口
# 用途：把 apps.system 声明为可导入的包，供 settings.INSTALLED_APPS、路由与其它模块引用。
# 数据表：本文件无模型定义；实际表映射见 apps/system/models.py。
# 内容：仅包声明与说明，无业务代码，避免在包初始化阶段引入循环导入。
# 平台基础模块包入口：承载用户、角色、菜单、部门、字典、参数与日志等系统级能力
