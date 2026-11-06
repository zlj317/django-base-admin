"""登录认证 / 用户信息。"""
# 模块用途：系统登录认证相关接口：账号登录、获取当前登录用户信息（含令牌续签）、退出登录。
# 对应路由前缀：认证路由挂载在 /api/auth/ 下，login 匿名可访问，userinfo/logout 需登录。
# 权限要求：login 由本文件 get_permissions 放行；其余动作强制 LoginRequired 校验令牌。
# 关键约定：登录成功统一返回 token + 用户基础信息 + 权限标识 + 侧边栏菜单树；菜单按角色授权过滤，admin 放行全部。
import time  # 生成时间戳字符串用于登录日志

from rest_framework import viewsets  # DRF 视图集合基类

from apps.system.models import SysLoginLog, SysMenu, SysUser  # 认证相关模型
from common.auth import LoginRequired, create_token  # 登录校验与令牌签发
from common.middleware import get_client_ip  # 从请求中解析客户端 IP
from common.response import fail, ok  # 统一响应封装
from common.utils import build_tree, check_password  # 树形组装与密码校验


# 内部工具：查询用户持有的有效角色，返回 [(角色ID, 角色编码), ...]。
# 用原生 SQL 的原因：用户-角色是多对多关系，数据存放在中间表 sys_user_role，模型层未建 M2M 字段。
def get_user_role_ids(user):
    """查询用户关联的未删除、启用状态的角色 (id, role_key) 列表。"""
    from django.db import connection  # 延迟导入，仅在需要时加载
    # 游标上下文负责自动关闭游标，异常时也不会泄漏数据库资源。
    with connection.cursor() as cursor:  # 原始 SQL 需显式游标
        # 中间表 JOIN 角色表：is_deleted=0 排除逻辑删除，status=0 表示启用，两者缺一不可。
        cursor.execute(
            "SELECT r.id, r.role_key FROM sys_user_role ur "  # 用户-角色中间表起手
            "JOIN sys_role r ON r.id = ur.role_id AND r.is_deleted = 0 AND r.status = 0 "  # 仅有效角色
            "WHERE ur.user_id = %s", [user.id])
        # fetchall 返回元组列表，列顺序与 SELECT 一致，调用方按位置解包。
        return cursor.fetchall()  # [(角色ID, 角色编码), ...]


# 内部工具：包装 common.permissions.get_user_perms，输出排序后的权限标识列表。
# 排序保证 /login 与 /userinfo 返回顺序一致，前端可直接做数组比较。
def get_user_perms(user):
    """取用户权限标识集合，并排序保证输出稳定。"""
    from common.permissions import get_user_perms as _perms  # 延迟导入避免循环依赖
    # 底层返回 set，这里转成有序 list；权限随请求实时计算，角色变更后无需重新登录即可生效。
    return sorted(_perms(user))  # 排序后返回，便于前端比对


# 内部工具：组装当前用户可见的侧边栏菜单树，供前端渲染菜单与动态路由。
# 只取目录(M)与菜单(C)，按钮(F)不参与导航；隐藏(visible='1')的菜单同样不下发。
def get_user_menus(user):
    """侧边栏菜单树（M/C 类型），超管返回全部。"""
    # 先取角色编码集合，用于判断是否超管（admin 拥有全部菜单，无需再查授权表）。
    role_keys = {key for _, key in get_user_role_ids(user)}  # 当前用户角色编码集合
    # 基础过滤：未删除、启用(status='0')、类型为目录/菜单、可见(visible='0')。
    qs = SysMenu.objects.filter(is_deleted=0, status='0', menu_type__in=['M', 'C'], visible='0')  # 可见菜单
    # 超管跳过按角色授权的裁剪，普通用户只保留其角色关联到的菜单。
    if 'admin' not in role_keys:  # 非超管按角色授权过滤
        from django.db import connection  # 延迟导入，避免模块级依赖
        # 原生 SQL 直查中间表：用户 -> 角色 -> 角色菜单，一次拿到全部已授权 menu_id。
        with connection.cursor() as cursor:  # 查询角色-菜单关联表
            cursor.execute(
                "SELECT DISTINCT rm.menu_id FROM sys_user_role ur "  # 用户-角色关联
                "JOIN sys_role_menu rm ON rm.role_id = ur.role_id WHERE ur.user_id = %s",  # 聚合角色菜单
                [user.id])
            # DISTINCT 防止多角色重复授权导致菜单重复；结果顺序与前端展示无关。
            menu_ids = [r[0] for r in cursor.fetchall()]  # 已授权菜单ID
        # id__in 一次性过滤；无授权时列表为空，结果自然为空集。
        qs = qs.filter(id__in=menu_ids)  # 仅保留已授权菜单
    # values 只取前端需要的展示字段，减少序列化开销与响应体积。
    rows = list(qs.values('id', 'parent_id', 'menu_name', 'path', 'component',  # 只取菜单展示所需字段
                          'menu_type', 'icon', 'order_num', 'visible', 'status'))
    # 按 parent_id 组装嵌套树；父节点缺失的孤儿节点会被 build_tree 提升为根节点。
    return build_tree(rows)  # 组装为前端可用的树结构


# 内部工具：写一条登录日志，成功与失败都会调用，用于安全审计与异常排查。
# status 约定：0=成功，1=失败；browser/msg 截断到列长度，避免超长插入报错。
def login_log(username, ip, status, msg, browser=''):
    """写入登录日志，字段截断以匹配表长度。"""
    # 直接 create 落库；登录日志不参与业务事务，写失败也不应阻断登录主流程。
    SysLoginLog.objects.create(  # 写入登录结果，字段按表长度截断，避免超长报错
        username=username, ip=ip, status=status,
        login_time=time.strftime('%Y-%m-%d %H:%M:%S'), browser=browser[:100], msg=msg[:255],
    )


# 认证视图集合：不继承 CrudViewSet，因为登录只读写用户表，且响应结构与标准 CRUD 不同。
class AuthViewSet(viewsets.ViewSet):
    """认证视图集合：登录、用户信息、退出。"""
    module_name = '认证管理'  # 操作日志模块名
    # 类级空列表只是占位；实际权限由下面的 get_permissions 按 action 动态决定。
    permission_classes = []  # 登录接口自行控制

    # DRF 每次请求都会调用本方法；注意返回的是「权限类实例列表」，而不是类本身。
    def get_permissions(self):
        """按动作返回权限：除登录外均需登录态。"""
        # userinfo/logout 需要登录（get_permissions 需返回实例，DRF 不会自动实例化）
        if self.action != 'login':
            return [LoginRequired()]  # 非登录接口校验令牌
        # 登录接口必须允许匿名访问，空列表表示不做任何权限校验。
        return []  # 登录接口放行

    # 登录主流程：参数校验 -> 账号/密码校验 -> 禁用校验 -> 记日志 -> 签发令牌 -> 返回权限与菜单。
    def login(self, request):
        """账号密码登录：校验、记录日志、签发令牌并返回菜单权限。"""
        # strip 去掉首尾空白，避免复制粘贴带入空格导致按用户名查不到记录。
        username = (request.data.get('username') or '').strip()  # 去除首尾空白
        # 密码不做 strip：前后空格也可能是用户真实输入的一部分。
        password = (request.data.get('password') or '')  # 原始密码
        # 客户端 IP 由公共工具解析（优先取反向代理透传的 X-Forwarded-For）。
        ip = get_client_ip(request)  # 客户端 IP
        # 记录 UA 便于安全审计；请求头缺失时用空串，避免 None 入库。
        browser = request.META.get('HTTP_USER_AGENT', '')  # 浏览器 UA

        # 用户名与密码都必填；参数缺失不写日志（本身不构成一次有效登录尝试）。
        if not username or not password:  # 必填校验
            return fail('请输入用户名和密码')  # 参数缺失
        # 只查未逻辑删除的用户；first() 避免用户名异常重复时抛异常（取最早一条）。
        user = SysUser.objects.filter(username=username, is_deleted=0).first()  # 查未删除用户
        # 统一提示「用户名或密码错误」，不暴露账号是否存在，降低账号枚举风险。
        if not user or not check_password(password, user.password):  # 用户不存在或密码错误
            login_log(username, ip, 1, '用户名或密码错误', browser)  # 记录失败日志
            return fail('用户名或密码错误')  # 返回失败
        # status=1 表示禁用（与 sys_user.status 约定一致），禁用账号即使密码正确也不允许登录。
        if user.status:  # 状态为 True 表示已禁用
            login_log(username, ip, 1, '账号已被禁用', browser)  # 记录失败日志
            return fail('账号已被禁用，请联系管理员')  # 返回禁用提示

        # 校验通过后记录成功日志，再签发令牌；日志只记结果，不记录密码等敏感信息。
        login_log(username, ip, 0, '登录成功', browser)  # 记录成功日志
        # 一次返回完整上下文：前端登录后即可渲染布局、菜单与按钮权限，无需再发多个请求。
        data = {  # 登录成功返回结构：令牌 + 基础用户 + 权限标识 + 菜单树
            'token': create_token(user),  # 签发访问令牌
            'user': {'id': user.id, 'username': user.username,  # 返回基础用户信息
                     'nickname': user.nickname, 'avatar': user.avatar},  # 昵称与头像
            'perms': get_user_perms(user),  # 权限标识
            'menus': get_user_menus(user),  # 侧边栏菜单树
        }
        return ok(data, '登录成功')  # 统一成功响应

    # 前端刷新页面或定时续签时调用，保证权限/菜单变更能及时生效。
    def userinfo(self, request):
        """返回当前登录用户信息、权限与菜单（令牌续签）。"""
        # user_info 由 LoginRequired 认证类写入；能走到这里说明令牌已校验通过。
        user = request.user_info  # 中间件解析出的登录用户
        # 返回结构与登录保持一致，前端可复用同一套解析逻辑。
        data = {  # 续签令牌并重新下发用户信息、权限与菜单
            'token': create_token(user),  # 重新签发令牌
            'user': {'id': user.id, 'username': user.username,  # 基础用户信息
                     'nickname': user.nickname, 'avatar': user.avatar},  # 昵称与头像
            'perms': get_user_perms(user),  # 权限标识
            'menus': get_user_menus(user),  # 侧边栏菜单树
        }
        return ok(data)  # 统一成功响应

    # 退出登录不维护服务端会话：令牌无状态，前端删除本地 token 即可。
    def logout(self, request):
        """退出登录：令牌由前端丢弃，服务端仅返回成功。"""
        # 返回成功让前端统一走「清理本地状态 -> 跳转登录页」流程。
        return ok(None, '退出成功')  # 返回成功提示
