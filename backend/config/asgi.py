"""ASGI 入口：供 uvicorn / daphne 等异步服务器加载调用。"""
# ============================== 文件说明 ==============================
# 作用：异步部署入口，向 ASGI 服务器导出模块级可调用对象 application。
# 被谁加载：生产环境 ASGI 服务器以 'config.asgi:application' 形式导入本模块。
# 关键约定：
#   1) 导入本模块前必须能 import Django 与项目配置，否则服务进程启动即失败；
#   2) application 在模块导入时创建一次，服务器复用同一实例；
#   3) 当前项目为纯 HTTP 接口，未额外注册 WebSocket 路由（未挂 channels）；
#   4) 同步部署或本地调试可继续使用 config/wsgi.py 与 manage.py runserver。
import os  # 通过环境变量告知 Django 使用哪套配置

from django.core.asgi import get_asgi_application  # 把 Django 应用包装为 ASGI 可调用对象

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')  # 异步部署未指定时回退到本项目配置

application = get_asgi_application()  # 模块级 application，供 ASGI 服务器按路径导入
