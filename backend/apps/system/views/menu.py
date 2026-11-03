"""菜单管理。"""
from rest_framework.decorators import action

from apps.system.models import SysMenu
from apps.system.serializers import MenuSerializer
from common.auth import LoginRequired
from common.response import fail, ok
from common.utils import build_tree
from common.views import CrudViewSet


class MenuViewSet(CrudViewSet):
    model = SysMenu
    serializer_class = MenuSerializer
    perm_prefix = 'system:menu'
    module_name = '菜单管理'

    @property
    def permission_classes(self):
        if self.action in ('tree',):
            return [LoginRequired]
        return super().permission_classes

    @action(detail=False, methods=['get'])
    def tree(self, request):
        """菜单树（含按钮），供菜单管理与角色授权使用。"""
        queryset = self.get_queryset()
        menu_name = request.query_params.get('menu_name')
        status = request.query_params.get('status')
        if menu_name:
            queryset = queryset.filter(menu_name__icontains=menu_name)
        if status not in (None, ''):
            queryset = queryset.filter(status=status)
        rows = MenuSerializer(queryset, many=True).data
        return ok(build_tree(rows))

    def delete(self, request, pk=None):
        """单删：存在子菜单时禁止删除。"""
        menu = self.get_queryset().filter(pk=pk).first()
        if not menu:
            return fail('菜单不存在', code=404)
        if self.get_queryset().filter(parent_id=pk).exists():
            return fail('存在子菜单，不允许删除')
        menu.is_deleted = 1
        menu.save(update_fields=['is_deleted'])
        return ok(None, '删除成功')
