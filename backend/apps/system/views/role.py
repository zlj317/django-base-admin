"""角色管理。"""
from django.db import connection

from apps.system.models import SysRole
from apps.system.serializers import RoleSerializer
from common.response import fail, ok
from common.views import CrudViewSet


def save_role_menus(role_id, menu_ids):
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM sys_role_menu WHERE role_id = %s", [role_id])
        if menu_ids:
            cursor.executemany(
                "INSERT INTO sys_role_menu (role_id, menu_id) VALUES (%s, %s)",
                [(role_id, mid) for mid in menu_ids])


class RoleViewSet(CrudViewSet):
    model = SysRole
    serializer_class = RoleSerializer
    perm_prefix = 'system:role'
    module_name = '角色管理'
    filter_map = {'role_name': 'icontains', 'status': 'exact'}

    def list(self, request):
        """不分页：角色数量有限，直接全量返回便于下拉选择。"""
        if request.query_params.get('page'):
            return super().list(request)
        queryset = self.apply_filters(self.get_queryset(), request)
        return ok(RoleSerializer(queryset, many=True).data)

    def delete(self, request):
        ids = request.data.get('ids') or []
        if any(int(i) == 1 for i in ids):
            return fail('内置管理员角色不允许删除')
        return super().delete(request)

    def menu_ids(self, request, pk=None):
        with connection.cursor() as cursor:
            cursor.execute("SELECT menu_id FROM sys_role_menu WHERE role_id = %s", [pk])
            return ok({'menu_ids': [r[0] for r in cursor.fetchall()]})

    def assign_menus(self, request, pk=None):
        if not self.get_queryset().filter(pk=pk).exists():
            return fail('角色不存在', code=404)
        save_role_menus(pk, request.data.get('menu_ids') or [])
        return ok(None, '分配菜单权限成功')
