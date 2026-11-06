"""报表模块路由。"""
# 模块：apps/report/urls.py —— /api/rp/ 前缀下的报表接口路由表
# 用途：用 crud() 批量生成分类、数据源、模板、生成记录四组标准增删改查路由，并追加各自的自定义动作。
# 数据表：间接操作 rp_category、rp_datasource、rp_template、rp_generate_record。
# 调用方：backend/config/urls.py 以 include('apps.report.urls') 挂载，前端报表页面按此路径请求。
# 设计：四类资源的路由形态一致，抽成工厂函数，避免重复书写 path 条目。
from django.urls import path  # 路由声明函数

from apps.report import views  # 各资源 ViewSet


# 路由工厂：给定资源前缀与视图集，生成 list/create/delete/update 四条基础路由，再追加 extras
def crud(prefix, viewset, extras=None):
    # 保留函数：当前未使用，历史实现可能用于修正以 / 开头的后缀
    def _rp(s): return s if prefix else s.lstrip('/')
    # 拼接资源前缀与动作后缀；prefix 为空时直接返回后缀
    def _join(s): return f'{prefix}/{s}' if prefix else s
    # 列表/新增/删除共用一个视图，由 HTTP 方法分派到对应动作
    list_view = viewset.as_view({'get': 'list', 'post': 'create', 'delete': 'delete'})
    # 详情更新只接受 PUT
    item_view = viewset.as_view({'put': 'update'})
    # 四条基础路由，与前端封装的通用请求方法一一对应
    patterns = [
        # 列表：GET 查询
        path(_join('list'), list_view),
        # 新增：POST 创建
        path(_join('create'), list_view),
        # 删除：DELETE 批量逻辑删除
        path(_join('delete'), list_view),
        # 更新：PUT 按主键更新
        path(_join('update/<int:pk>'), item_view),
        # 基础四条路由定义结束
    ]
    # 追加资源专属动作：extras 的键是路径模板，值是 {HTTP 方法: 动作名}
    for suffix, methods in (extras or {}).items():
        # 动态注册自定义动作，如 status/preview/generate
        patterns.append(path(_join(suffix), viewset.as_view(methods)))
    # 返回 path 列表，由调用处拼接成完整 urlpatterns
    return patterns


# 四组资源按顺序拼接：分类 → 数据源 → 模板 → 生成记录
urlpatterns = crud('category', views.RpCategoryViewSet, {
    'status/<int:pk>': {'put': 'status'},  # 启用/停用分类
# 数据源：基础 CRUD 之上追加状态切换
}) + crud('datasource', views.RpDatasourceViewSet, {
    'status/<int:pk>': {'put': 'status'},  # 启用/停用数据源
# 模板：基础 CRUD 之上追加预览、生成与状态切换
}) + crud('template', views.RpTemplateViewSet, {
    # 预览只读，用 GET 传模板 ID，返回渲染后的图表数据
    'preview/<int:pk>': {'get': 'preview'},  # 报表预览（图表数据）
    # 手动生成用 POST，会写一条 rp_generate_record 并产出文件
    'generate/<int:pk>': {'post': 'generate'},  # 手动生成报表
    'status/<int:pk>': {'put': 'status'},  # 启用/停用模板
# 生成记录：只读查看与回放，覆盖默认的增删改入口
}) + crud('gen', views.RpGenerateRecordViewSet, {
    # 覆盖基础 list：生成记录只允许查询，不允许新增
    'list': {'get': 'list'},  # 生成记录列表（覆盖基础 list）
    # 按记录回放历史报表，模板已删除时仍可展示
    'preview/<int:pk>': {'get': 'preview'},  # 按生成记录回放报表
# 四组资源拼接完成，urlpatterns 即为最终路由表
})
