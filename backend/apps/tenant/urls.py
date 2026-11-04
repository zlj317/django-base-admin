"""多租户模块路由。"""
from django.urls import path

from apps.tenant import views


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


urlpatterns = crud('tenant', views.SysTenantViewSet, {
    'status/<int:pk>': {'put': 'status'},
}) + crud('tenant_user', views.SysTenantUserViewSet) + crud('package', views.SysTenantPackageViewSet, {
    'status/<int:pk>': {'put': 'status'},
})
