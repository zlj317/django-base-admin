"""首页聚合接口路由。"""
from django.urls import path

from apps.home import views

urlpatterns = [
    path('overview/', views.HomeViewSet.as_view({'get': 'overview'})),
    path('monitor/', views.HomeViewSet.as_view({'get': 'monitor'})),
]
