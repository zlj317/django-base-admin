from django.apps import AppConfig


class Task_schedConfig(AppConfig):  # 任务调度应用的配置类，Django 启动时按 name 找到它并加载本应用
    # 模型未显式声明主键时使用的默认主键类型；此处用 bigint，兼容手写建表 SQL 的 BIGINT 主键
    default_auto_field = 'django.db.models.BigAutoField'
    # Python 包路径，必须与 INSTALLED_APPS 中的注册名一致，否则模型与迁移无法关联
    name = 'apps.task_sched'
