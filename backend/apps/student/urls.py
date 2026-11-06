"""学生信息表 路由（由代码生成器生成，可二次修改）。"""
# 模块用途：学生信息表模块的 URL 路由，把 REST 动作映射到 BizStudentViewSet。
# 对应表：biz_student（本文件只负责路径映射，不直接访问数据库）。
# 被谁引用：config/urls.py 通过 include('apps.student.urls') 汇总到项目 API 前缀下。
# 生成约定：路由统一为 {模块名}/{动作}（如 student/list），不带结尾斜杠、不使用 DRF 自动路由；
#           列表/新增/删除共用一个入口，按 HTTP 方法区分，其余动作各自用 as_view 声明。
from django.urls import path  # 引入路径路由函数

from apps.student import views  # 引入本模块视图，便于按 action 映射

# 复用同一个 as_view 结果：三个路径的处理逻辑相同，只是 HTTP 方法不同，避免重复构造视图。
# as_view 字典的键是 HTTP 方法（小写）、值是 ViewSet 动作名；字典中未列出的方法会自动返回 405。
list_view = views.BizStudentViewSet.as_view({
    'get': 'list', 'post': 'create', 'delete': 'delete'})  # 列表入口复用：GET 查询、POST 新增、DELETE 批量删除

# 路由清单：list/create/delete 共用 list_view；update 需要主键故单独声明；导入模板用 GET、导入数据用 POST。
urlpatterns = [  # 学生信息模块路由表，统一挂在项目 API 前缀下
    path('student/list', list_view),  # 分页查询学生列表
    path('student/create', list_view),  # 新增学生（与 list 共用入口，按 POST 区分）
    path('student/delete', list_view),  # 批量逻辑删除
    # 更新接口需要主键，路径用 <int:pk> 捕获；DRF 会把 pk 作为关键字参数传给 update 动作。
    path('student/update/<int:pk>',
         views.BizStudentViewSet.as_view({'put': 'update'})),  # 按主键更新单条记录
    # 模板下载是 GET（只读文件流），单独映射 import_template 动作，避免与列表入口混淆。
    path('student/importTemplate',
         views.BizStudentViewSet.as_view({'get': 'import_template'})),  # 下载 Excel 导入模板
    # 数据导入是 POST（携带 multipart 文件），映射 import_data 动作，方法不符时由 as_view 返回 405。
    path('student/importData',
         views.BizStudentViewSet.as_view({'post': 'import_data'})),  # 上传 Excel 批量导入
    # 数据导出是 GET（按查询参数过滤），映射 export_data 动作，返回 xlsx 附件而非 JSON。
    path('student/exportData',
         views.BizStudentViewSet.as_view({'get': 'export_data'})),  # 按查询条件导出 Excel
]
