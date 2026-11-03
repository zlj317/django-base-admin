"""全局路由。"""
from django.urls import include, path

urlpatterns = [
    path('api/auth/', include('apps.system.urls_auth')),
    path('api/system/', include('apps.system.urls')),
    path('api/gen/', include('apps.gen.urls')),
    # ↓↓↓ 由代码生成器生成的业务模块路由（新增业务表后在此追加） ↓↓↓
    path('api/', include('apps.student.urls')),
]
