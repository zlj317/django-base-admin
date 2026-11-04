"""消息模块路由。"""
from django.urls import path  # 路由声明函数

from apps.msg import views  # 各资源 ViewSet


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


urlpatterns = crud('template', views.MsgTemplateViewSet, {
    'status/<int:pk>': {'put': 'status'},  # 启用/停用模板
}) + crud('record', views.MsgRecordViewSet, {
    'my': {'get': 'my'},  # 我的消息（当前用户接收的）
    'read/<int:pk>': {'post': 'read'},  # 标记单条已读
    'read_all': {'post': 'read_all'},  # 全部标记已读
}) + crud('push_log', views.MsgPushLogViewSet, {
    'list': {'get': 'list'},  # 推送日志列表（覆盖基础 list）
}) + crud('push_config', views.MsgPushConfigViewSet, {
    'status/<int:pk>': {'put': 'status'},  # 启用/停用推送渠道
})
