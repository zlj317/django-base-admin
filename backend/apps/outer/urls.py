"""外部接口模块路由。"""
# 模块用途：把前端「外部接口 / 请求日志 / 同步任务」页面的动作映射到三个 ViewSet。
# 路由前缀：config/urls.py 以 /api/outer/ 引入，实际地址为 /api/outer/api/…、/api/outer/log/…、/api/outer/sync/…。
# 设计说明：未使用 DRF Router，改由 crud() 工厂产出固定四条基础路由，再按 extras 追加自定义动作。
# 现状：test/call 会真实发起 HTTP 请求；同步任务仅有配置 CRUD 与启停，未接入真实调度。
from django.urls import path  # 路由声明函数

from apps.outer import views  # 各资源 ViewSet


# 路由工厂：为每个资源生成 list/create/delete/update 四条约定路径，并按 extras 追加动作路由。
def crud(prefix, viewset, extras=None):
    # 历史遗留：当前未被调用，原意是在 prefix 为空时去掉后缀开头的斜杠。
    def _rp(s): return s if prefix else s.lstrip('/')
    # 拼接资源前缀与动作后缀，如 prefix='api'、suffix='list' 得到 'api/list'。
    def _join(s): return f'{prefix}/{s}' if prefix else s
    # 列表、新增、删除共用同一个视图函数，由 HTTP 方法分派到 list/create/delete。
    list_view = viewset.as_view({'get': 'list', 'post': 'create', 'delete': 'delete'})
    # 详情路由当前只开放 PUT 更新；查询详情由列表接口承担。
    item_view = viewset.as_view({'put': 'update'})
    # 四个基础路由固定输出，保证前端各模块调用方式一致。
    patterns = [
        # 列表路由：GET /{prefix}/list/ 查询分页数据。
        path(_join('list'), list_view),
        # 新增路由：POST /{prefix}/create/ 写入一条记录。
        path(_join('create'), list_view),
        # 删除路由：DELETE /{prefix}/delete/，请求体传 ids。
        path(_join('delete'), list_view),
        # 更新路由：PUT /{prefix}/update/<pk>/，只开放更新动作。
        path(_join('update/<int:pk>'), item_view),
        # 四条基础路由收集结束。
    ]
    # extras 的键是路径后缀、值是 {HTTP 方法: ViewSet 动作名}，逐个转成 path 追加到路由表。
    for suffix, methods in (extras or {}).items():
        # 动作路由：如 test/<pk> 映射到 ViewSet.test。
        patterns.append(path(_join(suffix), viewset.as_view(methods)))
    # 返回 path 列表，供下方 urlpatterns 用 + 拼接。
    return patterns


# 接口配置资源：基础 CRUD + 连通性测试、正式调用、启停三个自定义动作。
# 路由分组：api=接口配置（含 test/call/status）、log=调用日志、sync=同步任务。
urlpatterns = crud('api', views.OuterApiConfigViewSet, {
    'test/<int:pk>': {'post': 'test'},  # 测试接口连通性
    'call/<int:pk>': {'post': 'call'},  # 调用接口
    'status/<int:pk>': {'put': 'status'},  # 启用/停用接口
}) + crud('log', views.OuterApiRequestLogViewSet, {
    # 日志表不继承 BaseModel，基类默认的 is_deleted 过滤会报错，故 list 由子类单独实现。
    'list': {'get': 'list'},  # 调用日志列表（覆盖基础 list）
}) + crud('sync', views.OuterSyncTaskViewSet, {
    # 启停只切换 status 字段；当前没有 run_once 路由入口。
    'status/<int:pk>': {'put': 'status'},  # 启用/停用同步任务
})
