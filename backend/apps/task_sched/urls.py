"""任务调度模块路由。"""
from django.urls import path  # 路由声明函数

from apps.task_sched import views  # 各资源 ViewSet


def crud(prefix, viewset, extras=None):
    # DRF 的 ViewSet 同一方法可复用于不同 HTTP 动作，这里用 as_view 一次性挂载列表/新增/删除
    def _rp(s): return s if prefix else s.lstrip('/')  # 预留的路径规整函数：当前前缀恒非空，实际未被调用
    def _join(s): return f'{prefix}/{s}' if prefix else s  # 统一拼接“资源前缀/动作”，保证路径一致
    # 集合入口：GET 查询列表、POST 新增、DELETE 批量删除，三者共用一个 URL
    list_view = viewset.as_view({'get': 'list', 'post': 'create', 'delete': 'delete'})
    # 单条入口：PUT 按主键更新（路由中的 <int:pk> 会作为 pk 参数传给 update）
    item_view = viewset.as_view({'put': 'update'})
    # 标准 CRUD 的四条路由，路径统一不带结尾斜杠，与项目其它模块保持一致
    patterns = [
        path(_join('list'), list_view),
        path(_join('create'), list_view),
        path(_join('delete'), list_view),
        path(_join('update/<int:pk>'), item_view),
    ]
    # 追加资源自定义动作：extras 形如 {'动作路径': {'HTTP方法': 'ViewSet方法名'}}
    for suffix, methods in (extras or {}).items():
        patterns.append(path(_join(suffix), viewset.as_view(methods)))
    return patterns


# 任务信息：标准 CRUD + 立即执行 + 启停（启停动作在视图集中尚未实现，见下方注释）
urlpatterns = crud('info', views.TaskInfoViewSet, {
    'run_once/<int:pk>': {'post': 'run_once'},  # 立即执行一次
    'status/<int:pk>': {'put': 'status'},  # 启用/暂停任务
}) + crud('log', views.TaskLogViewSet, {
    'list': {'get': 'list'},  # 任务日志列表（覆盖基础 list）
})
