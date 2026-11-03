"""ASGI 入口：供 uvicorn / daphne 等异步服务器加载调用。"""
import os  # 通过环境变量告知 Django 使用哪套配置

from django.core.asgi import get_asgi_application  # 把 Django 应用包装为 ASGI 可调用对象

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')  # 异步部署未指定时回退到本项目配置

application = get_asgi_application()  # 模块级 application，供 ASGI 服务器按路径导入
