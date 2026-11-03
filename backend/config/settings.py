"""Django 项目配置：代码生成型后台管理系统。"""
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-gen-admin-secret-key-please-change-in-production'
DEBUG = True
ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'apps.system',
    'apps.gen',
    'core',
    # ↓↓↓ 由代码生成器生成的业务模块（新增业务表后在此追加） ↓↓↓
    'apps.student',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'common.middleware.OperLogMiddleware',
    'common.middleware.TokenRefreshMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {'context_processors': []},
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# 数据库：MySQL 8.0.21 本地实例（需求文档约定）
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'gen_admin',
        'USER': 'root',
        'PASSWORD': 'root',
        'HOST': '192.168.0.76',
        'PORT': '3306',
        'OPTIONS': {'charset': 'utf8mb4'},
    }
}

LANGUAGE_CODE = 'zh-hans'
TIME_ZONE = 'Asia/Shanghai'
USE_I18N = True
USE_TZ = False

STATIC_URL = 'static/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# 跨域：前后端分离开发环境
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_HEADERS = ('*',)

# DRF：统一认证与全局异常
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': ['common.auth.JWTAuthentication'],
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.AllowAny'],
    'EXCEPTION_HANDLER': 'common.exception.exception_handler',
    'UNAUTHENTICATED_USER': None,
}

# JWT 配置
JWT_CONFIG = {
    'SECRET': SECRET_KEY,
    'ALGORITHM': 'HS256',
    'EXPIRE': timedelta(hours=2),          # token 有效期
    'REFRESH_THRESHOLD': timedelta(minutes=30),  # 剩余小于该时长时下发新 token
}

# 分页默认配置
PAGE_DEFAULT_SIZE = 10

# 密码加密方式（bcrypt）
PASSWORD_HASHER = 'bcrypt'
