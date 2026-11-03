"""WSGI 入口：供 gunicorn / uWSGI 等同步服务器加载调用。"""
import os  # 通过环境变量告知 Django 使用哪套配置

from django.core.wsgi import get_wsgi_application  # 把 Django 应用包装为 WSGI 可调用对象

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')  # 部署脚本未指定时回退到本项目配置

application = get_wsgi_application()  # 模块级 application，供 WSGI 服务器按路径导入
