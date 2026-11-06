"""导入模板 + 打印模板模块路由。"""
# 模块：apps/imprint/urls.py —— 本模块的 URL 声明。
# 用途：用工厂函数 crud() 给三个 ViewSet 各生成一套风格一致的 CRUD 路由，并追加 status 启停路由。
# 对应表：imp_template、imp_template_column、print_template。
# 路由前缀：/api/imprint/（config/urls.py 已 include），最终形如 /api/imprint/template/list。
# 幂等性：读接口幂等；写接口语义同 CrudViewSet（delete 为逻辑删除，status 仅改状态）。
from django.urls import path

# 引用同模块视图集，避免循环导入（views 不反向导入 urls）
from apps.imprint import views


# 路由工厂：统一生成 list/create/delete/update 四条基础路由，并按 extras 追加自定义动作。
def crud(prefix, viewset, extras=None):
    # 拼接子路径：prefix 为空时直接返回 suffix，便于将来挂到根路径复用
    def _join(s): return f'{prefix}/{s}' if prefix else s
    # list 视图同时承担查询、新增、删除三种 HTTP 方法，减少重复的 as_view 映射
    list_view = viewset.as_view({'get': 'list', 'post': 'create', 'delete': 'delete'})
    # 详情视图只暴露 PUT 更新；未提供 GET 详情，前端依靠列表数据回显
    item_view = viewset.as_view({'put': 'update'})
    patterns = [
        # GET /list 列表（内部含筛选与分页）
        path(_join('list'), list_view),
        # POST /create 新增（同一视图，按方法分发）
        path(_join('create'), list_view),
        # DELETE /delete 批量逻辑删除（ids 放请求体）
        path(_join('delete'), list_view),
        # PUT /update/<pk> 按主键更新
        path(_join('update/<int:pk>'), item_view),
    ]
    # extras 形如 {'status/<int:pk>': {'put': 'status'}}，用于批量注册非标准动作
    for suffix, methods in (extras or {}).items():
        # 复用基类 status 动作实现启停
        patterns.append(path(_join(suffix), viewset.as_view(methods)))
    # 返回 path 列表，供 urlpatterns 拼接
    return patterns


# 三组路由串接成单一列表；顺序不影响匹配，因为各前缀互不重叠
urlpatterns = crud('template', views.ImpTemplateViewSet, {
    # 导入模板启停：PUT /api/imprint/template/status/<pk>
    'status/<int:pk>': {'put': 'status'},
}) + crud('column', views.ImpTemplateColumnViewSet, {
    # 列模型无 status/enabled 字段，该路由沿用基类动作但不会真正落库状态
    'status/<int:pk>': {'put': 'status'},
}) + crud('print', views.PrintTemplateViewSet, {
    # 打印模板启停：PUT /api/imprint/print/status/<pk>
    'status/<int:pk>': {'put': 'status'},
})
