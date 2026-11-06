# 模块：apps/system/urls_auth.py —— 认证相关路由表
# 用途：提供登录、当前登录用户信息、退出登录三个接口，供前端登录页与全局路由守卫调用。
# 数据表：路由本身不含模型，视图内部会读写 sys_user 与 sys_login_log 等表。
# 挂载：config/urls.py 以 'api/auth/' 前缀 include 本文件。
"""认证路由。"""
from django.urls import path  # 路由声明函数

from apps.system.views import AuthViewSet  # 认证视图集合

# 登录视图：仅绑定 POST，避免账号密码出现在 URL 查询串中；对应 POST /api/auth/login
login_view = AuthViewSet.as_view({'post': 'login'})  # 登录仅接受 POST
# 用户信息视图：仅绑定 GET，返回当前登录用户、角色与权限，供前端渲染菜单；对应 GET /api/auth/userinfo
userinfo_view = AuthViewSet.as_view({'get': 'userinfo'})  # 用户信息仅接受 GET
# 退出视图：同时绑定 POST 与 DELETE，前端可按既有习惯任选一种方式调用；对应 /api/auth/logout
logout_view = AuthViewSet.as_view({'post': 'logout', 'delete': 'logout'})  # 退出兼容 POST/DELETE

# 认证路由列表：路径均不带前导斜杠，由 config/urls.py 的 'api/auth/' 前缀统一拼接
urlpatterns = [  # 认证相关路径：登录、当前用户信息、退出
    path('login', login_view),  # 登录接口
    path('userinfo', userinfo_view),  # 用户信息接口
    path('logout', logout_view),  # 退出接口
]
