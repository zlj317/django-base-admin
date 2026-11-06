"""大屏BI模块路由。"""
# 文件：apps/bi/urls.py —— 大屏 BI 模块的路由表
# 用途：用 crud() 工厂批量生成 screen/dataset/visit 的增删改查路由，并附加预览、发布、分享等业务动作。
# 数据表：对应 bi_screen、bi_dataset、bi_visit_log 三张表。
# 路由前缀：/api/bi/screen、/api/bi/dataset、/api/bi/visit，分享入口 /api/bi/screen/share/<str:token>。
# 说明：所有资源都走统一的 list/create/delete/update/<pk> 四段式路径，便于前端复用请求封装。
from django.urls import path  # 路由声明函数

from apps.bi import views  # 各资源 ViewSet


# 路由工厂：生成某个资源的基础 CRUD 路由，并按 extras 追加业务动作路由
def crud(prefix, viewset, extras=None):
    # 内部工具：prefix 为空时去掉路径前导斜杠（当前保留以兼容旧写法）
    def _rp(s): return s if prefix else s.lstrip('/')
    # 内部工具：把资源前缀与动作名拼成完整路径
    def _join(s): return f'{prefix}/{s}' if prefix else s
    # 列表、新增、删除共用同一视图函数，由 HTTP 方法分发到对应动作
    list_view = viewset.as_view({'get': 'list', 'post': 'create', 'delete': 'delete'})
    # 更新按主键寻址，故单独生成一个视图
    item_view = viewset.as_view({'put': 'update'})
    # 基础四段式路由：list / create / delete / update/<pk>
    patterns = [
        # 列表：GET 查询分页列表
        path(_join('list'), list_view),
        # 新增：POST 创建记录
        path(_join('create'), list_view),
        # 删除：DELETE 批量删除（ids 放在请求体）
        path(_join('delete'), list_view),
        # 更新：PUT 按主键更新记录
        path(_join('update/<int:pk>'), item_view),
    ]
    # 追加业务动作路由：key 为路径后缀，value 为 {HTTP 方法: 动作名}
    for suffix, methods in (extras or {}).items():
        # 把动作后缀映射到 ViewSet 对应的 action 方法
        patterns.append(path(_join(suffix), viewset.as_view(methods)))
    # 返回该资源的路由列表，供上层用 + 拼接
    return patterns


# 大屏路由：基础 CRUD + 预览 / 发布动作
urlpatterns = crud('screen', views.BiScreenViewSet, {
    'preview/<int:pk>': {'get': 'preview'},  # 大屏预览（画布与组件数据）
    'publish/<int:pk>': {'post': 'publish'},  # 发布大屏
    # 大屏路由结束，继续拼接数据集路由
}) + crud('dataset', views.BiDatasetViewSet, {
    'list': {'get': 'list'},  # 数据集列表（覆盖基础 list）
    'status/<int:pk>': {'put': 'status'},  # 启用/停用数据集
    # 数据集路由结束，继续拼接访问日志路由
}) + crud('visit', views.BiVisitLogViewSet, {
    'list': {'get': 'list'},  # 访问日志列表（覆盖基础 list）
    # 访问日志路由结束，继续拼接分享入口
}) + [
    path('screen/share/<str:token>', views.BiScreenViewSet.as_view({'get': 'share'})),  # 分享链接访问
]
