"""认证路由。"""
from django.urls import path

from apps.system.views import AuthViewSet

auth = AuthViewSet.as_view({
    'post': 'login',
    'get': 'userinfo',
    'delete': 'logout',
})

urlpatterns = [
    path('login', auth),
    path('userinfo', auth),
    path('logout', auth),
]
