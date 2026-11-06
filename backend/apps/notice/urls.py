"""公告模块路由。"""
# 模块：apps/notice/urls.py —— /api/notice/ 前缀下的公告模块路由表
# 用途：用 crud() 批量生成分类、公告、阅读记录三组标准增删改查路由，并追加启停/发布/下线/已读等自定义动作。
# 对应表：notice_category、notice_info、notice_read
# 关键约定：路由形如 category/list、info/my、read/list，由 config/urls.py 统一 include 到 /api/notice/。
from django.urls import path  # 路由声明函数

from apps.notice import views  # 各资源 ViewSet


def crud(prefix, viewset, extras=None):
    # 保留函数：当前未使用，历史实现可能用于修正以 / 开头的后缀。
    def _rp(s): return s if prefix else s.lstrip('/')
    # 拼接资源前缀与动作路径；prefix 为空（根资源）时直接返回后缀，避免多余斜杠。
    def _join(s): return f'{prefix}/{s}' if prefix else s
    # 列表/新增/删除共用同一视图，由 HTTP 方法分派到 list/create/delete。
    list_view = viewset.as_view({'get': 'list', 'post': 'create', 'delete': 'delete'})
    # 详情视图只处理 PUT 更新。
    item_view = viewset.as_view({'put': 'update'})
    # 固定四条基础路由，保证前端接口约定一致。
    patterns = [
        path(_join('list'), list_view),
        path(_join('create'), list_view),
        path(_join('delete'), list_view),
        path(_join('update/<int:pk>'), item_view),
    ]
    # 追加自定义动作路由：extras 形如 {'my': {'get': 'my'}}，键是路径、值是 {HTTP 方法: 动作名}。
    for suffix, methods in (extras or {}).items():
        patterns.append(path(_join(suffix), viewset.as_view(methods)))
    return patterns


# 三组资源直接拼接：分类（含启停）+ 公告（含我的/发布/下线/已读）+ 阅读记录。
urlpatterns = crud('category', views.NoticeCategoryViewSet, {
    'status/<int:pk>': {'put': 'status'},  # 启用/停用分类
}) + crud('info', views.NoticeInfoViewSet, {
    # 公告自定义动作：与基础 CRUD 路由并列注册，路径前缀统一为 info/。
    'my': {'get': 'my'},  # 我的可见公告
    'publish/<int:pk>': {'put': 'publish'},  # 发布公告
    'offline/<int:pk>': {'put': 'offline'},  # 下线公告
    'read/<int:pk>': {'post': 'read'},  # 标记单条已读
}) + crud('read', views.NoticeReadViewSet, {})
