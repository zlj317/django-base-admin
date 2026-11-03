"""认证路由。"""
from django.urls import path  # 路由声明函数

from apps.system.views import AuthViewSet  # 认证视图集合

auth = AuthViewSet.as_view({
    'post': 'login',  # 登录
    'get': 'userinfo',  # 获取当前用户信息
    'delete': 'logout',  # 退出登录
})

urlpatterns = [
    path('login', auth),  # 登录接口
    path('userinfo', auth),  # 用户信息接口
    path('logout', auth),  # 退出接口
]
