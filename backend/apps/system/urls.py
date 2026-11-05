"""平台基础模块路由。"""
from django.urls import path  # 路由声明函数

from apps.system import views  # 各资源 ViewSet


def crud(prefix, viewset, extras=None):
    """生成标准 CRUD 路由：/list /create /update/<pk> /delete"""
    list_view = viewset.as_view({'get': 'list', 'post': 'create', 'delete': 'delete'})  # 集合
    item_view = viewset.as_view({'put': 'update'})  # 单条更新视图
    patterns = [
        path(f'{prefix}/list', list_view),  # 分页列表
        path(f'{prefix}/create', list_view),  # 新增
        path(f'{prefix}/delete', list_view),  # 批量删除
        path(f'{prefix}/update/<int:pk>', item_view),  # 按主键更新
    ]
    for suffix, methods in (extras or {}).items():
        patterns.append(path(f'{prefix}/{suffix}', viewset.as_view(methods)))  # 追加自定义动作
    return patterns  # 返回路由列表供拼接


urlpatterns = crud('user', views.UserViewSet, {
    '<int:pk>': {'get': 'retrieve'},  # 用户详情（编辑回填）
    'reset_pwd/<int:pk>': {'put': 'reset_pwd'},  # 重置密码
    'status/<int:pk>': {'put': 'status'},  # 启用/停用
    'assign_roles/<int:pk>': {'put': 'assign_roles'},  # 分配角色
}) + crud('role', views.RoleViewSet, {
    'menu_ids/<int:pk>': {'get': 'menu_ids'},  # 查询角色已授权菜单
    'assign_menus/<int:pk>': {'put': 'assign_menus'},  # 保存菜单授权
}) + crud('menu', views.MenuViewSet, {
    'tree': {'get': 'tree'},  # 菜单树
    'delete/<int:pk>': {'delete': 'delete'},  # 单条删除（带子节点校验）
}) + crud('dept', views.DeptViewSet, {
    'tree': {'get': 'tree'},  # 部门树
    'delete/<int:pk>': {'delete': 'delete'},  # 单条删除（带下级校验）
}) + crud('dict/type', views.DictTypeViewSet, {}) + crud('dict/data', views.DictDataViewSet, {
    'all': {'get': 'all'},  # 全部启用字典项（前端缓存用）
}) + crud('config', views.ConfigViewSet, {}) + crud('operlog', views.OperLogViewSet, {
    'clear': {'post': 'clear'},  # 清空操作日志
}) + crud('loginlog', views.LoginLogViewSet, {
    'clear': {'post': 'clear'},  # 清空登录日志
})
