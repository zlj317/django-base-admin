"""按钮/接口权限校验：权限标识如 system:user:list。

视图通过 perm_map 属性声明 action -> 权限标识映射，
PermissionCheck 读取用户角色菜单权限进行校验，'*:*:*' 为超管通配。
"""
from rest_framework import exceptions as drf_exceptions  # 权限异常交给全局处理器转 403

from common.auth import LoginRequired  # 复用登录校验，权限校验在其基础上追加


def get_user_perms(user):
    """查询用户权限标识集合（按 request 缓存）。"""
    from django.db import connection  # 局部导入，避免模块加载期就依赖数据库配置

    cache = getattr(user, '_perm_cache', None)  # 同一请求内多次校验可复用结果
    if cache is not None:
        return cache  # 已有缓存直接返回，减少重复 SQL
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
        )  # 一条 SQL 关联用户-角色-菜单，取出全部按钮权限标识
        perms = {row[0] for row in cursor.fetchall()}  # 转成去重集合，便于 O(1) 判断
        cursor.execute(
            "SELECT r.role_key FROM sys_user_role ur JOIN sys_role r ON r.id = ur.role_id "
            "AND r.is_deleted = 0 AND r.status = 0 WHERE ur.user_id = %s",
            [user.id],
        )  # 再查角色标识，用于识别超级管理员
        role_keys = {row[0] for row in cursor.fetchall()}  # 用户拥有的角色 key 集合
    if 'admin' in role_keys:
        perms.add('*:*:*')  # 超管直接给通配权限，免去逐项配置
    user._perm_cache = perms  # 挂到用户对象上，随请求结束自动释放
    return perms  # 返回最终权限集合


class PermissionCheck(LoginRequired):
    """登录 + 权限标识校验。"""

    def has_permission(self, request, view):
        """先校验登录，再按 perm_map 比对用户权限，缺失即抛 403。"""
        if not super().has_permission(request, view):
            return False  # 登录校验失败（内部已抛 401），此处仅兜底
        perm_map = getattr(view, 'perm_map', None)  # 视图声明的 action -> 权限标识映射
        if not perm_map:
            return True  # 未声明映射视为无需细粒度权限
        required = perm_map.get(view.action)  # 当前 action 对应的权限标识
        if not required:
            return True  # 该 action 未配置权限要求，直接放行
        perms = get_user_perms(request.user_info)  # 取用户权限集合（已带缓存）
        if '*:*:*' in perms or required in perms:
            return True  # 超管通配或已明确授权
        raise drf_exceptions.PermissionDenied(f'没有操作权限：{required}')  # 明确提示缺少哪个权限，便于排查
