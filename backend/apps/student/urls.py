"""学生信息表 路由（由代码生成器生成，可二次修改）。"""
from django.urls import path  # 引入路径路由函数

from apps.student import views  # 引入本模块视图，便于按 action 映射

list_view = views.BizStudentViewSet.as_view({
    'get': 'list', 'post': 'create', 'delete': 'delete'})  # 列表入口复用：GET 查询、POST 新增、DELETE 批量删除

urlpatterns = [  # 学生信息模块路由表，统一挂在项目 API 前缀下
    path('student/list', list_view),  # 分页查询学生列表
    path('student/create', list_view),  # 新增学生（与 list 共用入口，按 POST 区分）
    path('student/delete', list_view),  # 批量逻辑删除
    path('student/update/<int:pk>',
         views.BizStudentViewSet.as_view({'put': 'update'})),  # 按主键更新单条记录
    path('student/importTemplate',
         views.BizStudentViewSet.as_view({'get': 'import_template'})),  # 下载 Excel 导入模板
    path('student/importData',
         views.BizStudentViewSet.as_view({'post': 'import_data'})),  # 上传 Excel 批量导入
    path('student/exportData',
         views.BizStudentViewSet.as_view({'get': 'export_data'})),  # 按查询条件导出 Excel
]
