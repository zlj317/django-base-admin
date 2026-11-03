"""学生信息表 路由（由代码生成器生成，可二次修改）。"""
from django.urls import path

from apps.student import views

list_view = views.BizStudentViewSet.as_view({
    'get': 'list', 'post': 'create', 'delete': 'delete'})

urlpatterns = [
    path('student/list', list_view),
    path('student/create', list_view),
    path('student/delete', list_view),
    path('student/update/<int:pk>',
         views.BizStudentViewSet.as_view({'put': 'update'})),
    path('student/importTemplate',
         views.BizStudentViewSet.as_view({'get': 'import_template'})),
    path('student/importData',
         views.BizStudentViewSet.as_view({'post': 'import_data'})),
    path('student/exportData',
         views.BizStudentViewSet.as_view({'get': 'export_data'})),
]
