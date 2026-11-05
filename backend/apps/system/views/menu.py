"""菜单管理。"""
from rest_framework.decorators import action  # 声明自定义动作路由

from apps.system.models import SysMenu  # 菜单模型
from apps.system.serializers import MenuSerializer  # 菜单序列化器
from common.auth import LoginRequired  # 树查询只要求登录
from common.response import fail, ok  # 统一响应封装
from common.utils import build_tree  # 列表组装为树
from common.views import CrudViewSet  # 通用 CRUD 基类


class MenuViewSet(CrudViewSet):
    """菜单管理视图：提供菜单树与带子节点校验的单条删除。"""
    model = SysMenu  # 目标模型
    serializer_class = MenuSerializer  # 序列化器
    perm_prefix = 'system:menu'  # 权限标识前缀
    module_name = '菜单管理'  # 操作日志模块名

    @property  # 以属性形式按 action 动态返回权限类，供 DRF 在每次请求前装配
    def permission_classes(self):
        """树接口仅需登录，其余动作沿用基类的权限校验。"""
        if self.action in ('tree',):  # 菜单树用于角色授权页，登录即可
            return [LoginRequired]  # 登录校验
        return super().permission_classes  # 基类按 perm_prefix 校验

    @action(detail=False, methods=['get'])  # 注册集合级自定义动作：GET /menu/tree
    def tree(self, request):
        """菜单树（含按钮），供菜单管理与角色授权使用。"""
        queryset = self.get_queryset()  # 未删除菜单
        menu_name = request.query_params.get('menu_name')  # 按名称模糊查询
        status = request.query_params.get('status')  # 按状态精确查询
        if menu_name:
            queryset = queryset.filter(menu_name__icontains=menu_name)  # 名称过滤
        if status not in (None, ''):
            queryset = queryset.filter(status=status)  # 状态过滤
        rows = MenuSerializer(queryset, many=True).data  # 序列化为字典列表
        return ok(build_tree(rows))  # 组装树返回

    def delete(self, request, pk=None):
        """单删：存在子菜单时禁止删除。"""
        menu = self.get_queryset().filter(pk=pk).first()  # 查未删除菜单
        if not menu:  # 未命中说明菜单已被逻辑删除或主键不存在
            return fail('菜单不存在', code=404)  # 菜单不存在
        if self.get_queryset().filter(parent_id=pk).exists():  # 是否有子菜单
            return fail('存在子菜单，不允许删除')  # 拒绝删除
        menu.is_deleted = 1  # 逻辑删除
        menu.save(update_fields=['is_deleted'])  # 只更新删除标记
        return ok(None, '删除成功')  # 返回成功
