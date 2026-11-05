"""数据备份模块路由。"""
from django.urls import path

from apps.backup import views


def crud(prefix, viewset, extras=None):
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


urlpatterns = crud('record', views.BackupRecordViewSet, {
    'manual': {'post': 'manual_backup'},
    'download/<int:pk>': {'get': 'download'},  # 下载备份（演示环境返回元信息）
}) + crud('strategy', views.BackupStrategyViewSet, {
    'status/<int:pk>': {'put': 'status'},
})
