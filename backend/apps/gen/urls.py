"""代码生成器路由。"""
from django.urls import path

from apps.gen.views import GenTableViewSet

list_view = GenTableViewSet.as_view({'get': 'list', 'post': 'import_tables',
                                     'delete': 'delete'})
item_view = GenTableViewSet.as_view({'get': 'retrieve', 'put': 'save'})

urlpatterns = [
    path('db/tables', GenTableViewSet.as_view({'get': 'db_tables'})),
    path('db/import', GenTableViewSet.as_view({'post': 'import_tables'})),
    path('table/list', list_view),
    path('table/create', list_view),
    path('table/delete', list_view),
    path('table/<int:pk>', item_view),
    path('table/<int:pk>/preview', GenTableViewSet.as_view({'get': 'preview'})),
    path('table/<int:pk>/ddl', GenTableViewSet.as_view({'get': 'ddl'})),
    path('table/<int:pk>/download', GenTableViewSet.as_view({'get': 'download'})),
]
