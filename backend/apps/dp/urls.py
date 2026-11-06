"""数据权限模块路由。"""
# 文件：backend/apps/dp/urls.py
# 用途：注册数据权限配置与角色授权关联两组 CRUD 路由，并挂载规则表的启停动作。
# 对应表：sys_data_permission、sys_role_data_permission。
# 路由前缀：由 config/urls.py 以 /api/dp/ 包含本模块，最终路径见文件末尾 urlpatterns。
# 数据范围生效方式：路由只暴露配置接口，未在任何业务列表接口上挂数据范围过滤；
#   因此本模块当前是配置/预留，数据权限规则不会自动生效。
# Django 路由函数：把 URL 模式映射到具体视图
from django.urls import path

# 本模块视图集：两个 CrudViewSet 子类
from apps.dp import views


# 通用路由生成器：按模块约定生成 list/create/delete/update 四条固定路径
# prefix 为资源前缀（permission/role_perm），viewset 为对应视图集，extras 用于追加自定义动作
def crud(prefix, viewset, extras=None):
    # 拼接资源子路径；约定统一用 "/" 分隔，避免手写时漏斜杠
    def _join(s): return f'{prefix}/{s}' if prefix else s
    # 列表视图同时承载 GET 列表、POST 新增、DELETE 批量删除三个 action
    # 这是本项目既有约定：删除走 /delete 而非 REST 的 DELETE /list/{id}
    list_view = viewset.as_view({'get': 'list', 'post': 'create', 'delete': 'delete'})
    # 详情视图只承载 PUT 修改；注意没有 GET 详情与 PATCH，前端需用列表数据回填
    item_view = viewset.as_view({'put': 'update'})
    # 固定生成四条基础路由：list、create、delete、update/<pk>
    patterns = [
        # 列表查询：GET /list
        path(_join('list'), list_view),
        # 新增：POST /create；与 list 复用同一视图分发不同 action
        path(_join('create'), list_view),
        # 批量删除：DELETE /delete，id 列表由请求体 ids 传递
        path(_join('delete'), list_view),
        # 修改：PUT /update/<pk>；int 转换器只匹配数字，雪花 ID 也是纯数字所以可正常匹配
        path(_join('update/<int:pk>'), item_view),
    ]
    # 追加调用方声明的自定义动作，如规则表的 status/<pk>
    for suffix, methods in (extras or {}).items():
        # 每个自定义动作单独生成一条 path，methods 形如 {'put': 'status'}
        patterns.append(path(_join(suffix), viewset.as_view(methods)))
    # 返回路由列表，供上层 urlpatterns 直接用 + 拼接
    return patterns


# 模块级路由：规则表带启停动作，关联表只保留基础 CRUD
urlpatterns = crud('permission', views.SysDataPermissionViewSet, {
    # 启停：PUT /permission/status/<pk>，实际调用 CrudViewSet.status 更新 status 字段
    'status/<int:pk>': {'put': 'status'},
}) + crud('role_perm', views.SysRoleDataPermissionViewSet)
