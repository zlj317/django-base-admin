"""大屏BI模块路由。"""
from django.urls import path  # 路由声明函数

from apps.bi import views  # 各资源 ViewSet


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


urlpatterns = crud('screen', views.BiScreenViewSet, {
    'preview/<int:pk>': {'get': 'preview'},  # 大屏预览（画布与组件数据）
    'publish/<int:pk>': {'post': 'publish'},  # 发布大屏
}) + crud('dataset', views.BiDatasetViewSet, {
    'list': {'get': 'list'},  # 数据集列表（覆盖基础 list）
    'status/<int:pk>': {'put': 'status'},  # 启用/停用数据集
}) + crud('visit', views.BiVisitLogViewSet, {
    'list': {'get': 'list'},  # 访问日志列表（覆盖基础 list）
}) + [
    path('screen/share/<str:token>', views.BiScreenViewSet.as_view({'get': 'share'})),  # 分享链接访问
]
