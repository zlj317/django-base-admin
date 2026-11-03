"""登录认证 / 用户信息。"""
import time

from rest_framework import viewsets

from apps.system.models import SysLoginLog, SysMenu, SysUser
from common.auth import LoginRequired, create_token
from common.middleware import get_client_ip
from common.response import fail, ok
from common.utils import build_tree, check_password


def get_user_role_ids(user):
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT r.id, r.role_key FROM sys_user_role ur "
            "JOIN sys_role r ON r.id = ur.role_id AND r.is_deleted = 0 AND r.status = 0 "
            "WHERE ur.user_id = %s", [user.id])
        return cursor.fetchall()


def get_user_perms(user):
    from common.permissions import get_user_perms as _perms
    return sorted(_perms(user))


def get_user_menus(user):
    """侧边栏菜单树（M/C 类型），超管返回全部。"""
    role_keys = {key for _, key in get_user_role_ids(user)}
    qs = SysMenu.objects.filter(is_deleted=0, status='0', menu_type__in=['M', 'C'], visible='0')
    if 'admin' not in role_keys:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT DISTINCT rm.menu_id FROM sys_user_role ur "
                "JOIN sys_role_menu rm ON rm.role_id = ur.role_id WHERE ur.user_id = %s",
                [user.id])
            menu_ids = [r[0] for r in cursor.fetchall()]
        qs = qs.filter(id__in=menu_ids)
    rows = list(qs.values('id', 'parent_id', 'menu_name', 'path', 'component',
                          'menu_type', 'icon', 'order_num', 'visible', 'status'))
    return build_tree(rows)


def login_log(username, ip, status, msg, browser=''):
    SysLoginLog.objects.create(
        username=username, ip=ip, status=status,
        login_time=time.strftime('%Y-%m-%d %H:%M:%S'), browser=browser[:100], msg=msg[:255],
    )


class AuthViewSet(viewsets.ViewSet):
    module_name = '认证管理'
    permission_classes = []  # 登录接口自行控制

    def get_permissions(self):
        # userinfo/logout 需要登录（get_permissions 需返回实例，DRF 不会自动实例化）
        if self.action != 'login':
            return [LoginRequired()]
        return []

    def login(self, request):
        username = (request.data.get('username') or '').strip()
        password = (request.data.get('password') or '')
        ip = get_client_ip(request)
        browser = request.META.get('HTTP_USER_AGENT', '')

        if not username or not password:
            return fail('请输入用户名和密码')
        user = SysUser.objects.filter(username=username, is_deleted=0).first()
        if not user or not check_password(password, user.password):
            login_log(username, ip, 1, '用户名或密码错误', browser)
            return fail('用户名或密码错误')
        if user.status:
            login_log(username, ip, 1, '账号已被禁用', browser)
            return fail('账号已被禁用，请联系管理员')

        login_log(username, ip, 0, '登录成功', browser)
        data = {
            'token': create_token(user),
            'user': {'id': user.id, 'username': user.username,
                     'nickname': user.nickname, 'avatar': user.avatar},
            'perms': get_user_perms(user),
            'menus': get_user_menus(user),
        }
        return ok(data, '登录成功')

    def userinfo(self, request):
        user = request.user_info
        data = {
            'token': create_token(user),
            'user': {'id': user.id, 'username': user.username,
                     'nickname': user.nickname, 'avatar': user.avatar},
            'perms': get_user_perms(user),
            'menus': get_user_menus(user),
        }
        return ok(data)

    def logout(self, request):
        return ok(None, '退出成功')
