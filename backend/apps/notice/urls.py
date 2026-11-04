"""公告模块路由。"""
from django.urls import path  # 路由声明函数

from apps.notice import views  # 各资源 ViewSet


def crud(prefix, viewset, extras=None):
    def _rp(s): return s if prefix else s.lstrip('/')
    def _join(s): return f'{prefix}/{s}' if prefix else s
    list_view = viewset.as_view({'get': 'list', 'post': 'create', 'delete': 'delete'})
    item_view = viewset.as_view({'put': 'update'})
    patterns = [
        path(_join('list'), list_view),
        path(_join('create'), list_view),
        path(_join('delete'), list_view),
        path(_join('update/<int:pk>'), item_view),
    ]
    for suffix, methods in (extras or {}).items():
        patterns.append(path(_join(suffix), viewset.as_view(methods)))
    return patterns


urlpatterns = crud('category', views.NoticeCategoryViewSet, {
    'status/<int:pk>': {'put': 'status'},  # 启用/停用分类
}) + crud('info', views.NoticeInfoViewSet, {
    'my': {'get': 'my'},  # 我的可见公告
    'publish/<int:pk>': {'put': 'publish'},  # 发布公告
    'offline/<int:pk>': {'put': 'offline'},  # 下线公告
    'read/<int:pk>': {'post': 'read'},  # 标记单条已读
}) + crud('read', views.NoticeReadViewSet, {})
