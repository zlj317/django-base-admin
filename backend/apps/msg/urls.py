"""消息模块路由。"""
from django.urls import path  # 路由声明函数

from apps.msg import views  # 各资源 ViewSet


def crud(prefix, viewset, extras=None):
    # 保留函数：当前未使用，历史实现可能用于修正以 / 开头的后缀
    def _rp(s): return s if prefix else s.lstrip('/')
    # 拼接资源前缀与动作路径；prefix 为空时直接返回后缀
    def _join(s): return f'{prefix}/{s}' if prefix else s
    # 列表/新增/删除共用视图，由 HTTP 方法分派到对应动作
    list_view = viewset.as_view({'get': 'list', 'post': 'create', 'delete': 'delete'})
    # 详情视图只处理 PUT 更新
    item_view = viewset.as_view({'put': 'update'})
    patterns = [
        path(_join('list'), list_view),
        path(_join('create'), list_view),
        path(_join('delete'), list_view),
        path(_join('update/<int:pk>'), item_view),
    ]
    # 追加自定义动作路由，extras 的键是路径、值是 {HTTP 方法: 动作名}
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
