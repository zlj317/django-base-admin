"""Django 项目配置：代码生成型后台管理系统。"""
# ============================== 文件说明 ==============================
# 作用：项目唯一的静态配置中心，集中声明应用清单、中间件、数据库、DRF、JWT 等全局参数。
# 被谁加载：manage.py / config/wsgi.py / config/asgi.py 通过环境变量
#           DJANGO_SETTINGS_MODULE=config.settings 指定本模块，Django 启动时导入一次。
# 关键约定：
#   1) 本文件只做静态声明，不执行数据库访问等 I/O，避免启动阶段产生副作用；
#   2) 业务可调参数统一放这里，各 apps 通过 django.conf.settings 按名读取；
#   3) SECRET_KEY、数据库账号等敏感项当前为硬编码，生产环境应改为环境变量注入；
#   4) USE_TZ=False 表示全项目使用本地时间，与手工 SQL 写入的时间字段保持一致；
#   5) INSTALLED_APPS、MIDDLEWARE 的顺序有语义，新增项请追加到对应分组的末尾。
# 修改提醒：不要在本文件里导入 apps 内的模块，否则会造成循环导入。
from datetime import timedelta  # JWT 有效期/续期阈值用时间差表达，可读性更好
from pathlib import Path  # 跨平台路径拼接，用来定位项目根目录

BASE_DIR = Path(__file__).resolve().parent.parent  # 项目根目录（backend/），供路径类配置引用

SECRET_KEY = 'django-gen-admin-secret-key-please-change-in-production'  # 签名密钥，生产环境务必替换
DEBUG = True  # 开发期开启调试，便于查看错误堆栈
ALLOWED_HOSTS = ['*']  # 放开 Host 校验，适配内网调试与前后端分离访问

INSTALLED_APPS = [  # 已启用应用：contrib 基础能力 + DRF + 跨域 + 业务模块
    # 分组一：Django contrib 基础能力，只保留接口项目实际用到的两项
    # 分组二：第三方依赖，DRF 提供接口能力，corsheaders 负责跨域
    # 分组三：自研核心模块（system/gen/workflow/core）
    # 分组四：代码生成器产出的业务模块，新增业务表后在此追加
    # 分组五/六：需求 4、需求 5 的标准化与高级可选功能
    # 注意：django.contrib.admin/sessions/auth 未启用，认证由 common.auth 自行实现
    'django.contrib.contenttypes',  # 内容类型框架，DRF 与权限体系的基础依赖
    'django.contrib.staticfiles',  # 静态文件查找与收集
    'rest_framework',  # 序列化器、视图集、认证与异常处理钩子
    'corsheaders',  # 跨域响应头支持
    'apps.system',  # 系统管理：用户/角色/菜单/日志等
    'apps.gen',  # 代码生成器模块
    'apps.workflow',  # 工作流（审批）模块：BPMN 引擎、待办、表单、抄送
    'core',  # 自定义管理命令（init_db）
    # ↓↓↓ 由代码生成器生成的业务模块（新增业务表后在此追加） ↓↓↓
    'apps.student',  # 示例业务模块：学生表
    'apps.file',  # 文件管理模块
    'apps.msg',  # 消息通知模块
    'apps.notice',  # 公告模块
    'apps.task_sched',  # 任务调度模块
    'apps.report',  # 报表模块
    'apps.bi',  # 大屏BI模块
    'apps.outer',  # 外部接口模块
    # ↓↓↓ 需求4：通用标配功能 ↓↓↓
    'apps.sys_no',  # 编码规则
    'apps.imprint',  # 导入模板 + 打印模板
    'apps.backup',  # 数据备份
    'apps.dp',  # 数据权限
    'apps.dsm',  # 脱敏配置
    'apps.mon',  # 监控告警
    'apps.sec',  # 安全策略
    # ↓↓↓ 需求5：高级可选功能 ↓↓↓
    'apps.tenant',  # 多租户
    'apps.wo',  # 工单
    'apps.cal',  # 日历日程
    'apps.kb',  # 知识库
    'apps.scene3d',  # 3D 可视化（数字孪生）
]

MIDDLEWARE = [  # 中间件按顺序包装请求/响应，越靠前越外层
    # 顺序说明：请求阶段自上而下执行，响应阶段自下而上返回
    # 跨域中间件必须最外层，才能保证 OPTIONS 预检请求在进入业务逻辑前就被正确应答
    # 操作日志与 token 续期放在其后，确保它们拿到的是已完成跨域处理的响应
    'corsheaders.middleware.CorsMiddleware',  # 最先处理跨域，保证预检请求与响应头正确
    'django.middleware.common.CommonMiddleware',  # 常见请求规范化（如补全结尾斜杠）
    'common.middleware.OperLogMiddleware',  # 把写操作记录到操作日志表
    'common.middleware.TokenRefreshMiddleware',  # 响应时按需下发续期 token
]

ROOT_URLCONF = 'config.urls'  # 根路由模块

# 模板配置：保留最小可用配置，满足 DRF 的 browsable API 与后台异常页渲染需要
# DIRS 为空、APP_DIRS=True 表示只从各应用内部 templates 目录查找，不额外挂载全局目录
TEMPLATES = [  # 模板引擎配置，本项目以接口为主，基本不渲染 HTML
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',  # 使用 Django 内置模板引擎
        'DIRS': [],  # 不额外指定模板目录，只从各应用的 templates 下查找
        'APP_DIRS': True,  # 自动搜索已安装应用内的 templates 目录
        'OPTIONS': {'context_processors': []},  # 不注入上下文处理器，避免无谓开销
    },
]

WSGI_APPLICATION = 'config.wsgi.application'  # 同步部署入口，供 gunicorn/uwsgi 引用

# 数据库：MySQL 8.0.21 本地实例（需求文档约定）
# 取值来源：ENGINE/NAME/USER/PASSWORD/HOST/PORT 全部为硬编码，未读取环境变量
# 安全提醒：账号密码明文存放在代码中，仅适合内网开发，上线前必须改为环境变量注入
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',  # 使用 MySQL 后端驱动
        'NAME': 'gen_admin',  # 业务库名，由 init_db 命令负责创建
        'USER': 'root',  # 数据库账号（内网开发环境）
        'PASSWORD': 'root',  # 数据库密码，生产环境应改为环境变量注入
        'HOST': '192.168.0.76',  # 数据库实例地址
        'PORT': '3306',  # 默认端口
        'OPTIONS': {'charset': 'utf8mb4'},  # 支持中文与 emoji 的字符集
    }
}

LANGUAGE_CODE = 'zh-hans'  # 后台提示与本地化使用简体中文
TIME_ZONE = 'Asia/Shanghai'  # 时区与业务所在地一致，避免时间偏移
USE_I18N = True  # 启用国际化框架
USE_TZ = False  # 存本地时间，避免与手工 SQL 写入的时间字段出现时区差

STATIC_URL = 'static/'  # 静态资源访问前缀

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'  # 默认主键用 bigint，防止自增溢出

# 跨域：前后端分离开发环境
CORS_ALLOW_ALL_ORIGINS = True  # 开发期放开全部来源，生产应改为白名单
CORS_ALLOW_HEADERS = ('*',)  # 允许自定义请求头（如 Authorization、X-Refresh-Token）

# DRF：统一认证与全局异常
# 约定：所有接口 HTTP 状态码恒为 200，业务成功与否由响应体中的 code 字段表达
# 因此异常处理、认证失败、权限不足都由 common.exception.exception_handler 统一封装
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': ['common.auth.JWTAuthentication'],  # 统一 JWT 认证并挂载 user_info
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.AllowAny'],  # 默认放行，由视图按需叠加权限
    'EXCEPTION_HANDLER': 'common.exception.exception_handler',  # 统一错误码封装，HTTP 状态恒为 200
    'UNAUTHENTICATED_USER': None,  # 不用 Django 的 User 对象，认证结果由 user_info 承载
    'DEFAULT_RENDERER_CLASSES': ['common.response.BigIntJSONRenderer'],  # 雪花主键转字符串，避免前端精度丢失
    'DATETIME_FORMAT': '%Y-%m-%d %H:%M:%S',  # 时间统一输出 yyyy-MM-dd HH:mm:ss，避免 ISO 的 T 分隔
    'DATE_FORMAT': '%Y-%m-%d',  # 日期统一输出 yyyy-MM-dd
    'TIME_FORMAT': '%H:%M:%S',  # 时间仅输出时分秒
}

# JWT 配置
# 取值来源：SECRET 复用上方 SECRET_KEY；有效期与续期阈值为硬编码的 timedelta
# 注意：EXPIRE 指 token 总有效期，REFRESH_THRESHOLD 由 TokenRefreshMiddleware 使用
JWT_CONFIG = {
    'SECRET': SECRET_KEY,  # 复用项目密钥，避免多维护一份签名配置
    'ALGORITHM': 'HS256',  # 对称签名，实现简单且性能足够
    'EXPIRE': timedelta(hours=2),          # token 有效期
    'REFRESH_THRESHOLD': timedelta(minutes=30),  # 剩余小于该时长时下发新 token
}

# 分页默认配置
PAGE_DEFAULT_SIZE = 10  # 列表接口未传 page_size 时的默认条数

# 密码加密方式（bcrypt）
PASSWORD_HASHER = 'bcrypt'  # 业务层直接调用 bcrypt，这里记录选型以便统一
