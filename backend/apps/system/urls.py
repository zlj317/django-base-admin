"""平台基础模块路由。"""
from django.urls import path

from apps.system import views


def crud(prefix, viewset, extras=None):
    """生成标准 CRUD 路由：/list /create /update/<pk> /delete"""
    list_view = viewset.as_view({'get': 'list', 'post': 'create', 'delete': 'delete'})
    item_view = viewset.as_view({'put': 'update'})
    patterns = [
        path(f'{prefix}/list', list_view),
        path(f'{prefix}/create', list_view),
        path(f'{prefix}/delete', list_view),
        path(f'{prefix}/update/<int:pk>', item_view),
    ]
    for suffix, methods in (extras or {}).items():
        patterns.append(path(f'{prefix}/{suffix}', viewset.as_view(methods)))
    return patterns


urlpatterns = crud('user', views.UserViewSet, {
    'reset_pwd/<int:pk>': {'put': 'reset_pwd'},
    'status/<int:pk>': {'put': 'status'},
    'assign_roles/<int:pk>': {'put': 'assign_roles'},
}) + crud('role', views.RoleViewSet, {
    'menu_ids/<int:pk>': {'get': 'menu_ids'},
    'assign_menus/<int:pk>': {'put': 'assign_menus'},
}) + crud('menu', views.MenuViewSet, {
    'tree': {'get': 'tree'},
    'delete/<int:pk>': {'delete': 'delete'},
}) + crud('dept', views.DeptViewSet, {
    'tree': {'get': 'tree'},
    'delete/<int:pk>': {'delete': 'delete'},
}) + crud('dict/type', views.DictTypeViewSet, {}) + crud('dict/data', views.DictDataViewSet, {
    'all': {'get': 'all'},
}) + crud('config', views.ConfigViewSet, {}) + crud('operlog', views.OperLogViewSet, {
    'clear': {'post': 'clear'},
}) + crud('loginlog', views.LoginLogViewSet, {
    'clear': {'post': 'clear'},
})
