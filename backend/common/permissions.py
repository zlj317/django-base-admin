"""按钮/接口权限校验：权限标识如 system:user:list。

视图通过 perm_map 属性声明 action -> 权限标识映射，
PermissionCheck 读取用户角色菜单权限进行校验，'*:*:*' 为超管通配。
"""
from rest_framework import exceptions as drf_exceptions

from common.auth import LoginRequired


def get_user_perms(user):
    """查询用户权限标识集合（按 request 缓存）。"""
    from django.db import connection

    cache = getattr(user, '_perm_cache', None)
    if cache is not None:
        return cache
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT DISTINCT m.perms
            FROM sys_user_role ur
            JOIN sys_role r ON r.id = ur.role_id AND r.is_deleted = 0 AND r.status = 0
            JOIN sys_role_menu rm ON rm.role_id = r.id
            JOIN sys_menu m ON m.id = rm.menu_id AND m.is_deleted = 0
            WHERE ur.user_id = %s AND m.perms IS NOT NULL AND m.perms != ''
            """,
            [user.id],
        )
        perms = {row[0] for row in cursor.fetchall()}
        cursor.execute(
            "SELECT r.role_key FROM sys_user_role ur JOIN sys_role r ON r.id = ur.role_id "
            "AND r.is_deleted = 0 AND r.status = 0 WHERE ur.user_id = %s",
            [user.id],
        )
        role_keys = {row[0] for row in cursor.fetchall()}
    if 'admin' in role_keys:
        perms.add('*:*:*')
    user._perm_cache = perms
    return perms


class PermissionCheck(LoginRequired):
    """登录 + 权限标识校验。"""

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        perm_map = getattr(view, 'perm_map', None)
        if not perm_map:
            return True
        required = perm_map.get(view.action)
        if not required:
            return True
        perms = get_user_perms(request.user_info)
        if '*:*:*' in perms or required in perms:
            return True
        raise drf_exceptions.PermissionDenied(f'没有操作权限：{required}')
