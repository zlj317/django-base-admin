# 学生信息模块包入口：提供学生档案的增删改查与 Excel 导入导出能力
# 模块用途：apps/student 包的入口文件，标记该目录为可导入的 Python 包，并说明模块整体职责。
# 对应表：biz_student（模型见 apps/student/models.py，表由建表脚本维护，managed=False）。
# 被谁引用：config/settings.py 的 INSTALLED_APPS 以 'apps.student' 注册；config/urls.py 汇总本模块 urls.py。
# 生成约定：代码生成器为每张业务表固定生成六件套（__init__/apps/models/serializers/urls/views），
#           本文件通常只保留说明、不放业务代码，避免包初始化时产生副作用或循环导入。
