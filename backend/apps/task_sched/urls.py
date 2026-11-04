"""任务调度模块路由。"""
from django.urls import path  # 路由声明函数

from apps.task_sched import views  # 各资源 ViewSet


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


urlpatterns = crud('info', views.TaskInfoViewSet, {
    'run_once/<int:pk>': {'post': 'run_once'},  # 立即执行一次
    'status/<int:pk>': {'put': 'status'},  # 启用/暂停任务
}) + crud('log', views.TaskLogViewSet, {
    'list': {'get': 'list'},  # 任务日志列表（覆盖基础 list）
})
