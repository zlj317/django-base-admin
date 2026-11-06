"""文件模块路由。"""
from django.urls import path  # 路由声明函数

from apps.file import views  # 各资源 ViewSet


def crud(prefix, viewset, extras=None):
    # 把路径片段拼到资源前缀上；prefix 为空时直接返回片段，避免出现多余斜杠
    def _join(s): return f'{prefix}/{s}' if prefix else s
    # 列表/新增/删除共用同一视图：因为路由按 HTTP 方法分派到 list/create/delete
    list_view = viewset.as_view({'get': 'list', 'post': 'create', 'delete': 'delete'})
    # 详情视图只接受 PUT，用于按主键更新
    item_view = viewset.as_view({'put': 'update'})
    patterns = [
        path(_join('list'), list_view),
        path(_join('create'), list_view),
        path(_join('delete'), list_view),
        path(_join('update/<int:pk>'), item_view),
    ]
    # 追加自定义动作路由：extras 形如 {'upload': {'post': 'upload'}}，键是路径、值是方法映射
    for suffix, methods in (extras or {}).items():
        patterns.append(path(_join(suffix), viewset.as_view(methods)))
    return patterns


urlpatterns = crud('', views.FileViewSet, {
    'upload': {'post': 'upload'},  # 文件上传
    'download/<int:pk>': {'get': 'download'},  # 文件下载
    'preview_url/<int:pk>': {'get': 'preview_url'},  # 获取预览 URL
    'office_url/<int:pk>': {'get': 'office_url'},  # 获取 Office 在线预览 URL
}) + crud('config', views.FileConfigViewSet, {}) + crud('recycle', views.FileRecycleViewSet, {
    'list': {'get': 'list'},  # 回收站列表（覆盖基础 list）
    'restore/<int:pk>': {'post': 'restore'},  # 恢复回收站文件
    'hard_delete/<int:pk>': {'delete': 'hard_delete'},  # 彻底删除回收站文件
})
