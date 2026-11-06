# ============================================================================
# core 应用包（backend/core）
# 用途：承载项目级自定义管理命令（init_db 建库建表、seed_new_modules 演示数据），
#       应用自身不定义数据模型，因此没有 models.py / migrations 目录。
# 调用：无需导入本包；Django 依据 settings.INSTALLED_APPS 中的 "core"
#       加载应用，命令通过 `python manage.py <命令名>` 触发。
# 依赖表：本包无直接表依赖；其命令会读写 sys_menu / sys_role_menu / sys_user
#         以及各业务模块演示数据表（详见 commands/ 下两个命令的文件头）。
# ============================================================================
# core 应用包初始化文件：标识目录为 Python 包，本文件不执行任何初始化逻辑。
# 应用级配置（应用名、后台展示名）统一放在 apps.py 的 CoreConfig 中。
