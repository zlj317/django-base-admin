"""WSGI 入口：供 gunicorn / uWSGI 等同步服务器加载调用。"""
# ============================== 文件说明 ==============================
# 作用：同步部署入口，向 WSGI 服务器导出模块级可调用对象 application。
# 被谁加载：生产环境 WSGI 服务器以 'config.wsgi:application' 形式导入本模块。
# 关键约定：
#   1) 导入本模块前必须能 import Django 与项目配置，否则服务进程启动即失败；
#   2) application 在模块导入时创建一次，服务器复用同一实例，避免重复初始化；
#   3) 同步模型不支持 WebSocket/长连接，需要异步能力时改用 config/asgi.py；
#   4) 开发环境通常用 manage.py runserver，不经过本文件。
import os  # 通过环境变量告知 Django 使用哪套配置

from django.core.wsgi import get_wsgi_application  # 把 Django 应用包装为 WSGI 可调用对象

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')  # 部署脚本未指定时回退到本项目配置

application = get_wsgi_application()  # 模块级 application，供 WSGI 服务器按路径导入
