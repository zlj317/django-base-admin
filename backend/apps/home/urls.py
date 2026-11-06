"""首页聚合接口路由。"""
# 引入 path 构造单级路由，不用 router 是因为这里只有三个只读入口，无需标准 CRUD
from django.urls import path

# 复用首页视图集，三个 URL 分别映射到不同 action
from apps.home import views

urlpatterns = [
    # 基础概览：指标卡与基础统计
    path('overview/', views.HomeViewSet.as_view({'get': 'overview'})),
    # 首页增强聚合：补充趋势、文件、任务、告警、用户、报表、BI、知识库、日程等块
    # 保留原有 overview/monitor 不变，新增接口只做只读聚合，故沿用首页的匿名只读策略
    path('rich/', views.HomeViewSet.as_view({'get': 'rich'})),
    # 监控概览：服务器/任务/告警等运行态指标
    path('monitor/', views.HomeViewSet.as_view({'get': 'monitor'})),
]
