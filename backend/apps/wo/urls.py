"""工单模块路由。"""
# 文件：apps/wo/urls.py —— 工单模块的 URL 路由表
# 用途：按项目统一的 CRUD 约定生成工单类型、工单、工单日志三组接口，并为工单挂载 assign/solve/close 流转动作。
# 对应表：work_order_type、work_order、work_order_log。
# 路由前缀：本文件内为 type / order / log，追加到 config/urls.py 的 /api/wo/ 之后。
# 生成结果：/api/wo/type/list|create|delete|update/<pk>、/api/wo/order/... 以及
#           /api/wo/order/assign/<pk>、solve/<pk>、close/<pk>、/api/wo/log/...
# 幂等性：路由定义是纯声明，重复加载不会产生数据；接口幂等性由视图与数据库约束保证。
# Django 路由函数：path() 用于把 URL 模式绑定到视图函数/ViewSet
from django.urls import path

# 导入本模块视图集，路由直接引用其中的 ViewSet 类
from apps.wo import views


# 通用 CRUD 路由生成器：拼出 list/create/delete/update 四条基础路径，再追加模块自定义动作
def crud(prefix, viewset, extras=None):
    # 三个模块（type/order/log）共用同一套路径规则，保证前端请求地址风格一致
    """与 bi/urls.py 保持一致的 CRUD 路由生成器。"""
    # 内部工具函数：前缀非空时补斜杠，保证拼出 "order/list" 而不是 "orderlist"
    def _join(s): return f'{prefix}/{s}' if prefix else s
    # 列表视图：同一路径按 HTTP 方法分派，GET=列表查询、POST=新增、DELETE=批量删除
    list_view = viewset.as_view({'get': 'list', 'post': 'create', 'delete': 'delete'})
    # 单条编辑视图：只暴露 PUT（update），本模块不提供单条详情 GET
    item_view = viewset.as_view({'put': 'update'})
    # 基础四条路由：与前端通用 CRUD 组件的请求地址一一对应
    patterns = [
        # 列表查询：GET /{prefix}/list（同时承担筛选与分页）
        path(_join('list'), list_view),
        # 新增：POST /{prefix}/create
        path(_join('create'), list_view),
        # 批量删除：DELETE /{prefix}/delete，ids 放请求体避免 URL 过长
        path(_join('delete'), list_view),
        # 编辑：PUT /{prefix}/update/<pk>，pk 为整数以匹配雪花 ID 的十进制写法
        path(_join('update/<int:pk>'), item_view),
    # 四条基础路由到此结束，下面按 extras 追加模块自定义动作
    ]
    # 追加自定义动作：extras 为 {路径后缀: {HTTP 方法: 动作名}} 映射
    for suffix, methods in (extras or {}).items():
        # 每个动作独立注册，由 DRF 的 as_view 解析到 ViewSet 中对应的方法
        patterns.append(path(_join(suffix), viewset.as_view(methods)))
    # 返回路由列表，供 urlpatterns 直接拼接
    return patterns


# 模块路由表：三组 CRUD 拼接；工单组额外注册指派、解决、关闭三个流转动作
urlpatterns = crud('type', views.WOTypeViewSet) + crud('order', views.WorkOrderViewSet, {
    # 指派处理人：PUT /api/wo/order/assign/<pk>，对应 WorkOrderViewSet.assign
    'assign/<int:pk>': {'put': 'assign'},
    # 标记已解决：PUT /api/wo/order/solve/<pk>，对应 WorkOrderViewSet.solve
    'solve/<int:pk>': {'put': 'solve'},
    # 关闭工单：PUT /api/wo/order/close/<pk>，对应 WorkOrderViewSet.close
    'close/<int:pk>': {'put': 'close'},
# 日志组只有标准 CRUD（无自定义动作），因此 extras 省略，直接拼到同一 urlpatterns 中
}) + crud('log', views.WOLogViewSet)
