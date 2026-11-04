"""知识库模块路由。"""
from django.urls import path

from apps.kb import views


def crud(prefix, viewset, extras=None):
    """与 bi/urls.py 保持一致的 CRUD 路由生成器。"""
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


urlpatterns = crud('category', views.KBCategoryViewSet) + crud('document', views.KBDocumentViewSet, {
    'stats': {'get': 'stats'},
}) + crud('favorite', views.KBFavoriteViewSet)
