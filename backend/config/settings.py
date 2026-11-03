"""Django 项目配置：代码生成型后台管理系统。"""
from datetime import timedelta  # JWT 有效期/续期阈值用时间差表达，可读性更好
from pathlib import Path  # 跨平台路径拼接，用来定位项目根目录

BASE_DIR = Path(__file__).resolve().parent.parent  # 项目根目录（backend/），供路径类配置引用

SECRET_KEY = 'django-gen-admin-secret-key-please-change-in-production'  # 签名密钥，生产环境务必替换
DEBUG = True  # 开发期开启调试，便于查看错误堆栈
ALLOWED_HOSTS = ['*']  # 放开 Host 校验，适配内网调试与前后端分离访问

INSTALLED_APPS = [  # 已启用应用：contrib 基础能力 + DRF + 跨域 + 业务模块
    'django.contrib.contenttypes',  # 内容类型框架，DRF 与权限体系的基础依赖
    'django.contrib.staticfiles',  # 静态文件查找与收集
    'rest_framework',  # 序列化器、视图集、认证与异常处理钩子
    'corsheaders',  # 跨域响应头支持
    'apps.system',  # 系统管理：用户/角色/菜单/日志等
    'apps.gen',  # 代码生成器模块
    'core',  # 自定义管理命令（init_db）
    # ↓↓↓ 由代码生成器生成的业务模块（新增业务表后在此追加） ↓↓↓
    'apps.student',  # 示例业务模块：学生表
]

MIDDLEWARE = [  # 中间件按顺序包装请求/响应，越靠前越外层
    'corsheaders.middleware.CorsMiddleware',  # 最先处理跨域，保证预检请求与响应头正确
    'django.middleware.common.CommonMiddleware',  # 常见请求规范化（如补全结尾斜杠）
    'common.middleware.OperLogMiddleware',  # 把写操作记录到操作日志表
    'common.middleware.TokenRefreshMiddleware',  # 响应时按需下发续期 token
]

ROOT_URLCONF = 'config.urls'  # 根路由模块

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
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': ['common.auth.JWTAuthentication'],  # 统一 JWT 认证并挂载 user_info
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.AllowAny'],  # 默认放行，由视图按需叠加权限
    'EXCEPTION_HANDLER': 'common.exception.exception_handler',  # 统一错误码封装，HTTP 状态恒为 200
    'UNAUTHENTICATED_USER': None,  # 不用 Django 的 User 对象，认证结果由 user_info 承载
}

# JWT 配置
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
