"""代码生成器路由。"""
from django.urls import path  # 引入路径路由函数

from apps.gen.views import GenTableViewSet  # 引入生成器视图集，按 action 映射到不同处理方法

list_view = GenTableViewSet.as_view({'get': 'list', 'post': 'import_tables',
                                     'delete': 'delete'})  # 列表页复用同一入口：GET 查询、POST 导入、DELETE 批量删除
item_view = GenTableViewSet.as_view({'get': 'retrieve', 'put': 'save'})  # 单条配置：GET 详情、PUT 保存配置

urlpatterns = [
    path('db/tables', GenTableViewSet.as_view({'get': 'db_tables'})),  # 读取数据库中可导入的表清单
    path('db/import', GenTableViewSet.as_view({'post': 'import_tables'})),  # 导入选中的数据表生成默认配置
    path('table/list', list_view),  # 生成配置列表查询
    path('table/create', list_view),  # 兼容前端新增入口，实际走导入逻辑
    path('table/delete', list_view),  # 批量逻辑删除生成配置
    path('table/<int:pk>', item_view),  # 单条配置详情与保存
    path('table/<int:pk>/preview', GenTableViewSet.as_view({'get': 'preview'})),  # 预览渲染后的代码文件
    path('table/<int:pk>/ddl', GenTableViewSet.as_view({'get': 'ddl'})),  # 查看源表的建表语句
    path('table/<int:pk>/download', GenTableViewSet.as_view({'get': 'download'})),  # 打包下载生成代码 ZIP
]
