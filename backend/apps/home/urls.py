"""首页聚合接口路由。"""
from django.urls import path

from apps.home import views

urlpatterns = [
    path('overview/', views.HomeViewSet.as_view({'get': 'overview'})),
    # 首页增强聚合：补充趋势、文件、任务、告警、用户、报表、BI、知识库、日程等块
    # 保留原有 overview/monitor 不变，新增接口只做只读聚合，故沿用首页的匿名只读策略
    path('rich/', views.HomeViewSet.as_view({'get': 'rich'})),
    path('monitor/', views.HomeViewSet.as_view({'get': 'monitor'})),
]
