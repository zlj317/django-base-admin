"""认证路由。"""
from django.urls import path  # 路由声明函数

from apps.system.views import AuthViewSet  # 认证视图集合

login_view = AuthViewSet.as_view({'post': 'login'})  # 登录仅接受 POST
userinfo_view = AuthViewSet.as_view({'get': 'userinfo'})  # 用户信息仅接受 GET
logout_view = AuthViewSet.as_view({'post': 'logout', 'delete': 'logout'})  # 退出兼容 POST/DELETE

urlpatterns = [  # 认证相关路径：登录、当前用户信息、退出
    path('login', login_view),  # 登录接口
    path('userinfo', userinfo_view),  # 用户信息接口
    path('logout', logout_view),  # 退出接口
]
