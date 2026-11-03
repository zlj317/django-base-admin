"""{{ table.module_comment }} 路由（由代码生成器生成，可二次修改）。"""
from django.urls import path

from apps.{{ table.module_name }} import views

list_view = views.{{ table.class_name }}ViewSet.as_view({
    'get': 'list', 'post': 'create', 'delete': 'delete'})

urlpatterns = [
    path('{{ route }}/list', list_view),
    path('{{ route }}/create', list_view),
    path('{{ route }}/delete', list_view),
    path('{{ route }}/update/<int:pk>',
         views.{{ table.class_name }}ViewSet.as_view({'put': 'update'})),
{% if table.import_enable %}    path('{{ route }}/importTemplate',
         views.{{ table.class_name }}ViewSet.as_view({'get': 'import_template'})),
    path('{{ route }}/importData',
         views.{{ table.class_name }}ViewSet.as_view({'post': 'import_data'})),
{% endif %}{% if table.export_enable %}    path('{{ route }}/exportData',
         views.{{ table.class_name }}ViewSet.as_view({'get': 'export_data'})),
{% endif %}]
