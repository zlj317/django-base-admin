"""登录认证 / 用户信息。"""
import time  # 生成时间戳字符串用于登录日志

from rest_framework import viewsets  # DRF 视图集合基类

from apps.system.models import SysLoginLog, SysMenu, SysUser  # 认证相关模型
from common.auth import LoginRequired, create_token  # 登录校验与令牌签发
from common.middleware import get_client_ip  # 从请求中解析客户端 IP
from common.response import fail, ok  # 统一响应封装
from common.utils import build_tree, check_password  # 树形组装与密码校验


def get_user_role_ids(user):
    """查询用户关联的未删除、启用状态的角色 (id, role_key) 列表。"""
    from django.db import connection  # 延迟导入，仅在需要时加载
    with connection.cursor() as cursor:  # 原始 SQL 需显式游标
        cursor.execute(
            "SELECT r.id, r.role_key FROM sys_user_role ur "  # 用户-角色中间表起手
            "JOIN sys_role r ON r.id = ur.role_id AND r.is_deleted = 0 AND r.status = 0 "  # 仅有效角色
            "WHERE ur.user_id = %s", [user.id])
        return cursor.fetchall()  # [(角色ID, 角色编码), ...]


def get_user_perms(user):
    """取用户权限标识集合，并排序保证输出稳定。"""
    from common.permissions import get_user_perms as _perms  # 延迟导入避免循环依赖
    return sorted(_perms(user))  # 排序后返回，便于前端比对


def get_user_menus(user):
    """侧边栏菜单树（M/C 类型），超管返回全部。"""
    role_keys = {key for _, key in get_user_role_ids(user)}  # 当前用户角色编码集合
    qs = SysMenu.objects.filter(is_deleted=0, status='0', menu_type__in=['M', 'C'], visible='0')  # 可见菜单
    if 'admin' not in role_keys:  # 非超管按角色授权过滤
        from django.db import connection  # 延迟导入，避免模块级依赖
        with connection.cursor() as cursor:  # 查询角色-菜单关联表
            cursor.execute(
                "SELECT DISTINCT rm.menu_id FROM sys_user_role ur "  # 用户-角色关联
                "JOIN sys_role_menu rm ON rm.role_id = ur.role_id WHERE ur.user_id = %s",  # 聚合角色菜单
                [user.id])
            menu_ids = [r[0] for r in cursor.fetchall()]  # 已授权菜单ID
        qs = qs.filter(id__in=menu_ids)  # 仅保留已授权菜单
    rows = list(qs.values('id', 'parent_id', 'menu_name', 'path', 'component',  # 只取菜单展示所需字段
                          'menu_type', 'icon', 'order_num', 'visible', 'status'))
    return build_tree(rows)  # 组装为前端可用的树结构


def login_log(username, ip, status, msg, browser=''):
    """写入登录日志，字段截断以匹配表长度。"""
    SysLoginLog.objects.create(  # 写入登录结果，字段按表长度截断，避免超长报错
        username=username, ip=ip, status=status,
        login_time=time.strftime('%Y-%m-%d %H:%M:%S'), browser=browser[:100], msg=msg[:255],
    )


class AuthViewSet(viewsets.ViewSet):
    """认证视图集合：登录、用户信息、退出。"""
    module_name = '认证管理'  # 操作日志模块名
    permission_classes = []  # 登录接口自行控制

    def get_permissions(self):
        """按动作返回权限：除登录外均需登录态。"""
        # userinfo/logout 需要登录（get_permissions 需返回实例，DRF 不会自动实例化）
        if self.action != 'login':
            return [LoginRequired()]  # 非登录接口校验令牌
        return []  # 登录接口放行

    def login(self, request):
        """账号密码登录：校验、记录日志、签发令牌并返回菜单权限。"""
        username = (request.data.get('username') or '').strip()  # 去除首尾空白
        password = (request.data.get('password') or '')  # 原始密码
        ip = get_client_ip(request)  # 客户端 IP
        browser = request.META.get('HTTP_USER_AGENT', '')  # 浏览器 UA

        if not username or not password:  # 必填校验
            return fail('请输入用户名和密码')  # 参数缺失
        user = SysUser.objects.filter(username=username, is_deleted=0).first()  # 查未删除用户
        if not user or not check_password(password, user.password):  # 用户不存在或密码错误
            login_log(username, ip, 1, '用户名或密码错误', browser)  # 记录失败日志
            return fail('用户名或密码错误')  # 返回失败
        if user.status:  # 状态为 True 表示已禁用
            login_log(username, ip, 1, '账号已被禁用', browser)  # 记录失败日志
            return fail('账号已被禁用，请联系管理员')  # 返回禁用提示

        login_log(username, ip, 0, '登录成功', browser)  # 记录成功日志
        data = {  # 登录成功返回结构：令牌 + 基础用户 + 权限标识 + 菜单树
            'token': create_token(user),  # 签发访问令牌
            'user': {'id': user.id, 'username': user.username,  # 返回基础用户信息
                     'nickname': user.nickname, 'avatar': user.avatar},  # 昵称与头像
            'perms': get_user_perms(user),  # 权限标识
            'menus': get_user_menus(user),  # 侧边栏菜单树
        }
        return ok(data, '登录成功')  # 统一成功响应

    def userinfo(self, request):
        """返回当前登录用户信息、权限与菜单（令牌续签）。"""
        user = request.user_info  # 中间件解析出的登录用户
        data = {  # 续签令牌并重新下发用户信息、权限与菜单
            'token': create_token(user),  # 重新签发令牌
            'user': {'id': user.id, 'username': user.username,  # 基础用户信息
                     'nickname': user.nickname, 'avatar': user.avatar},  # 昵称与头像
            'perms': get_user_perms(user),  # 权限标识
            'menus': get_user_menus(user),  # 侧边栏菜单树
        }
        return ok(data)  # 统一成功响应

    def logout(self, request):
        """退出登录：令牌由前端丢弃，服务端仅返回成功。"""
        return ok(None, '退出成功')  # 返回成功提示
