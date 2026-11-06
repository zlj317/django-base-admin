"""按钮/接口权限校验：权限标识如 system:user:list。

视图通过 perm_map 属性声明 action -> 权限标识映射，
PermissionCheck 读取用户角色菜单权限进行校验，'*:*:*' 为超管通配。
"""
# 模块定位：登录之后的细粒度接口/按钮权限校验，是 LoginRequired 的增强版。
# 调用方：各业务视图通过 permission_classes = [PermissionCheck] 并声明 perm_map 使用；
# 登录接口也复用 get_user_perms 以便前端一次性拿到按钮权限列表。
# 关键约定：权限标识统一为 模块:资源:动作 形式；role_key=admin 额外获得 '*:*:*' 通配；
# 查询结果缓存在 user._perm_cache 上，同一次请求内多次校验不会重复查库。
# 异常与响应：无权限抛 PermissionDenied，由 common.exception 统一转成 code=403。
from rest_framework import exceptions as drf_exceptions  # 权限异常交给全局处理器转 403

from common.auth import LoginRequired  # 复用登录校验，权限校验在其基础上追加


def get_user_perms(user):
    """查询用户权限标识集合（按 request 缓存）。"""
    from django.db import connection  # 局部导入，避免模块加载期就依赖数据库配置

    # 先读缓存：同一请求内视图可能多次调用（列表 + 详情），避免重复 SQL
    cache = getattr(user, '_perm_cache', None)  # 同一请求内多次校验可复用结果
    # 缓存命中（包括空集合）直接返回，避免对同一用户重复执行两条 SQL
    if cache is not None:
        return cache  # 已有缓存直接返回，减少重复 SQL
    # 未命中缓存：用原生游标执行两条聚合查询，绕开 ORM 拼接多表 JOIN
    with connection.cursor() as cursor:
        # 第一条：用户 -> 角色 -> 菜单，取所有非空 perms 标识（DISTINCT 去重）
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
        # 第二条：单独查角色 key，用于识别 admin（角色表不区分删除/禁用则会被误判为超管）
        cursor.execute(
            "SELECT r.role_key FROM sys_user_role ur JOIN sys_role r ON r.id = ur.role_id "
            "AND r.is_deleted = 0 AND r.status = 0 WHERE ur.user_id = %s",
            [user.id],
        )  # 再查角色标识，用于识别超级管理员
        role_keys = {row[0] for row in cursor.fetchall()}  # 用户拥有的角色 key 集合
    # 超级管理员直接补一个通配标识，校验时无需逐条比对
    if 'admin' in role_keys:
        perms.add('*:*:*')  # 超管直接给通配权限，免去逐项配置
    # 回写缓存：挂在 user 实例上，随请求对象生命周期自动释放，无需显式清理
    user._perm_cache = perms  # 挂到用户对象上，随请求结束自动释放
    return perms  # 返回最终权限集合


# 权限类：先登录，再按视图声明的 perm_map 做按钮级校验
class PermissionCheck(LoginRequired):
    """登录 + 权限标识校验。"""

    # 依次做「是否登录」和「是否有该 action 的权限」两级判断
    def has_permission(self, request, view):
        """先校验登录，再按 perm_map 比对用户权限，缺失即抛 403。"""
        # 第一级：未登录由父类抛 401，这里只做防御性返回
        if not super().has_permission(request, view):
            return False  # 登录校验失败（内部已抛 401），此处仅兜底
        # 第二级：视图未声明 perm_map 说明该资源不做按钮级控制，直接放行
        perm_map = getattr(view, 'perm_map', None)  # 视图声明的 action -> 权限标识映射
        # 没有映射表（或为空字典）即视为该视图不参与按钮权限校验
        if not perm_map:
            return True  # 未声明映射视为无需细粒度权限
        # 当前请求动作（ViewSet 的 list/create/update 等）对应的权限标识
        required = perm_map.get(view.action)  # 当前 action 对应的权限标识
        # 映射表存在但未给该 action 配置标识，说明此动作无需权限
        if not required:
            return True  # 该 action 未配置权限要求，直接放行
        # 取用户权限集合（已带缓存），再做通配/精确匹配
        perms = get_user_perms(request.user_info)  # 取用户权限集合（已带缓存）
        # 超管通配直接放行；普通用户要求权限标识与声明值完全一致
        if '*:*:*' in perms or required in perms:
            return True  # 超管通配或已明确授权
        raise drf_exceptions.PermissionDenied(f'没有操作权限：{required}')  # 明确提示缺少哪个权限，便于排查
