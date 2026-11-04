"""安全策略模块路由。"""
from django.urls import path

from apps.sec import views


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


urlpatterns = crud('ip', views.SysIpControlViewSet, {
    'status/<int:pk>': {'put': 'status'},
}) + crud('login_attempt', views.SysLoginAttemptViewSet) + crud('rate_limit', views.SysRateLimitViewSet, {
    'status/<int:pk>': {'put': 'status'},
})
