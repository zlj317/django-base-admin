"""角色管理。"""
from django.db import connection  # 角色-菜单关联表使用原始 SQL

from apps.system.models import SysRole  # 角色模型
from apps.system.serializers import RoleSerializer  # 角色序列化器
from common.response import fail, ok  # 统一响应封装
from common.views import CrudViewSet  # 通用 CRUD 基类


def save_role_menus(role_id, menu_ids):
    """覆盖式保存角色菜单授权：先清空旧关联再批量插入。"""
    with connection.cursor() as cursor:  # 原始 SQL 需显式游标
        cursor.execute("DELETE FROM sys_role_menu WHERE role_id = %s", [role_id])  # 清除旧授权
        if menu_ids:  # 有授权项才插入
            cursor.executemany(
                "INSERT INTO sys_role_menu (role_id, menu_id) VALUES (%s, %s)",
                [(role_id, mid) for mid in menu_ids])  # 批量写入关联


class RoleViewSet(CrudViewSet):
    """角色管理视图：列表可全量返回，内置管理员角色禁止删除。"""
    model = SysRole  # 目标模型
    serializer_class = RoleSerializer  # 序列化器
    perm_prefix = 'system:role'  # 权限标识前缀
    module_name = '角色管理'  # 操作日志模块名
    filter_map = {'role_name': 'icontains', 'status': 'exact'}  # 列表筛选字段

    def list(self, request):
        """不分页：角色数量有限，直接全量返回便于下拉选择。"""
        if request.query_params.get('page'):  # 显式要求分页时走基类逻辑
            return super().list(request)  # 分页返回
        queryset = self.apply_filters(self.get_queryset(), request)  # 应用筛选条件
        return ok(RoleSerializer(queryset, many=True).data)  # 全量返回

    def delete(self, request):
        """删除角色：内置管理员角色（id=1）不允许删除。"""
        ids = request.data.get('ids') or []  # 待删除角色ID
        if any(int(i) == 1 for i in ids):  # 含内置管理员角色
            return fail('内置管理员角色不允许删除')  # 拒绝删除
        return super().delete(request)  # 走基类逻辑删除

    def menu_ids(self, request, pk=None):
        """查询角色已授权的菜单ID列表。"""
        with connection.cursor() as cursor:  # 原始 SQL 需显式游标
            cursor.execute("SELECT menu_id FROM sys_role_menu WHERE role_id = %s", [pk])
            return ok({'menu_ids': [r[0] for r in cursor.fetchall()]})  # 返回ID数组

    def assign_menus(self, request, pk=None):
        """为指定角色保存菜单授权（覆盖式）。"""
        if not self.get_queryset().filter(pk=pk).exists():  # 先校验角色存在
            return fail('角色不存在', code=404)  # 角色不存在
        save_role_menus(pk, request.data.get('menu_ids') or [])  # 覆盖保存授权
        return ok(None, '分配菜单权限成功')  # 返回成功
