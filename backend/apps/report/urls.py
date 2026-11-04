"""报表模块路由。"""
from django.urls import path  # 路由声明函数

from apps.report import views  # 各资源 ViewSet


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


urlpatterns = crud('category', views.RpCategoryViewSet, {
    'status/<int:pk>': {'put': 'status'},  # 启用/停用分类
}) + crud('datasource', views.RpDatasourceViewSet, {
    'status/<int:pk>': {'put': 'status'},  # 启用/停用数据源
}) + crud('template', views.RpTemplateViewSet, {
    'preview/<int:pk>': {'get': 'preview'},  # 报表预览（图表数据）
    'generate/<int:pk>': {'post': 'generate'},  # 手动生成报表
    'status/<int:pk>': {'put': 'status'},  # 启用/停用模板
}) + crud('gen', views.RpGenerateRecordViewSet, {
    'list': {'get': 'list'},  # 生成记录列表（覆盖基础 list）
    'preview/<int:pk>': {'get': 'preview'},  # 按生成记录回放报表
})
