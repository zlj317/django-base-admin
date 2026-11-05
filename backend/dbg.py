# 调试脚本：不启动 HTTP 服务，直接在进程内伪造请求，验证代码生成器详情接口的渲染结果。
import os, sys, traceback  # os 设置环境变量，sys 调整模块搜索路径，traceback 打印异常堆栈
sys.path.insert(0, r"d:\other\django-base-admin\backend")  # 把后端根目录加入搜索路径，保证能直接导入 apps/common
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")  # 指定配置模块，供下面的 django.setup() 使用
import django  # 延迟导入 Django，确保配置变量已设置后再初始化
django.setup()  # 加载应用、模型与中间件，使 ORM 和视图可以正常工作
from django.test import RequestFactory  # 请求工厂，用于构造不经过网络的 WSGI 请求对象
from apps.gen.views import GenTableViewSet  # 被测视图：代码生成器的表配置视图集
from apps.system.models import SysUser  # 取真实用户记录，复用生产认证逻辑签发 token
from common.auth import create_token  # 项目统一的 JWT 签发函数，避免调试逻辑与线上不一致
token = create_token(SysUser.objects.filter(username="admin").first())  # 用 admin 账号生成可直接使用的 Bearer token
rf = RequestFactory()  # 创建请求构造器
req = rf.get("/api/gen/table/1", HTTP_AUTHORIZATION=f"Bearer {token}")  # 模拟带认证头的详情请求
view = GenTableViewSet.as_view({"get": "retrieve"})  # 把视图集的 action 映射成可直接调用的视图函数
resp = view(req, pk=1)  # 直接调用视图，pk 对应 URL 中的主键参数
try:
    content = resp.rendered_content  # 主动触发序列化与渲染，提前暴露渲染阶段异常
    print("render ok, len:", len(content))  # 渲染成功时打印长度，帮助判断返回体是否正常
except Exception:
    traceback.print_exc()  # 渲染失败时输出完整堆栈，便于定位具体出错位置
