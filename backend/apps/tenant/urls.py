"""多租户模块路由。"""
# 文件：apps/tenant/urls.py —— 多租户模块的 URL 路由表
# 用途：把租户、租户成员、租户套餐三组 CRUD 接口注册到 Django 路由，供前端调用。
# 对应表：sys_tenant、sys_tenant_user、sys_tenant_package。
# 路由前缀：整个模块挂在 /api/tenant/ 下（见 config/urls.py 的 include('apps.tenant.urls')）。
# 最终地址示例：/api/tenant/tenant/list、/api/tenant/tenant/create、/api/tenant/tenant/update/<pk>、
#               /api/tenant/tenant/delete、/api/tenant/tenant/status/<pk>，成员与套餐规则相同。
# 租户隔离：路由中不携带租户标识，也没有按租户前缀分库/分表，隔离仍只停留在成员关系数据层。
# 逐条注册 URL 与视图映射
from django.urls import path

# 本模块三个 ViewSet 的实现
from apps.tenant import views


# 通用路由生成器：一个资源前缀生成 list/create/update/delete 四个标准入口，并可按需追加自定义动作
def crud(prefix, viewset, extras=None):
    # 去掉 path 前导斜杠的辅助函数；当前实现未调用（历史遗留，保留不影响路由结果）
    def _rp(s): return s if prefix else s.lstrip('/')
    # 把子路径拼到资源前缀；prefix 为空时原样返回，避免出现多余斜杠
    def _join(s): return f'{prefix}/{s}' if prefix else s
    # 同一个视图函数处理列表/新增/删除：三者都用请求体或查询参数区分，URL 不同但方法分派一致
    list_view = viewset.as_view({'get': 'list', 'post': 'create', 'delete': 'delete'})
    # 编辑只开放 PUT（部分更新由基类 serializer partial=True 实现），不提供 PATCH
    item_view = viewset.as_view({'put': 'update'})
    # 标准四个入口：list 查询、create 新增、delete 批量逻辑删除、update 按主键编辑
    patterns = [
        # GET 分页列表
        path(_join('list'), list_view),
        # POST 新增
        path(_join('create'), list_view),
        # DELETE 请求体传 ids 批量删除
        path(_join('delete'), list_view),
        # PUT 按主键更新，路径参数名必须为 pk
        path(_join('update/<int:pk>'), item_view),
    ]
    # extras 形如 {'status/<int:pk>': {'put': 'status'}}，为资源追加非标准动作路由
    for suffix, methods in (extras or {}).items():
        # 把 HTTP 方法映射到 ViewSet 方法名，再注册到统一前缀下
        patterns.append(path(_join(suffix), viewset.as_view(methods)))
    # 返回 path 列表，由调用方用 + 拼接成完整 urlpatterns
    return patterns


# 租户主体：标准 CRUD + status 动作（PUT /api/tenant/tenant/status/<pk> 启用/停用）
urlpatterns = crud('tenant', views.SysTenantViewSet, {
    'status/<int:pk>': {'put': 'status'},
}) + crud('tenant_user', views.SysTenantUserViewSet) + crud('package', views.SysTenantPackageViewSet, {
    # 租户成员：只有标准 CRUD，没有状态字段；租户套餐：额外提供上下架状态切换
    'status/<int:pk>': {'put': 'status'},
})
