"""JWT 认证：签发 / 校验 token，认证类附加 request.user_info。"""
import time  # 生成 exp 时间戳，需要用当前时间加上有效期

import jwt  # PyJWT：负责 token 的编码、解码与过期校验
from django.conf import settings  # 读取 JWT_CONFIG 中的密钥/算法/有效期
from rest_framework import exceptions as drf_exceptions  # 复用 DRF 异常，交给全局处理器转错误码
from rest_framework.authentication import BaseAuthentication, get_authorization_header  # 认证基类 + 取头工具


class AuthFailed(drf_exceptions.AuthenticationFailed):
    """认证失败，统一转成 code=401 响应。"""

    def __init__(self, msg):
        """用 msg 作为 detail，便于全局异常处理器直接取出提示文案。"""
        super().__init__(detail=msg)  # 交给父类保存 detail，保持 DRF 既有行为


def create_token(user):
    """为模型实例或字典形式用户签发 JWT，载荷包含 uid/username/exp。"""
    cfg = settings.JWT_CONFIG  # 取配置，避免在函数内硬编码密钥与算法
    payload = {  # 载荷保持精简，只放认证与展示所需字段
        'uid': user['id'] if isinstance(user, dict) else user.id,  # 兼容字典与模型两种入参
        'username': user['username'] if isinstance(user, dict) else user.username,  # 同上，便于日志展示
        'exp': int(time.time() + cfg['EXPIRE'].total_seconds()),  # 秒级过期时间戳，由 PyJWT 自动校验
    }
    return jwt.encode(payload, cfg['SECRET'], algorithm=cfg['ALGORITHM'])  # 对称签名，返回字符串 token


def decode_token(token):
    """校验签名与过期时间后返回载荷，异常交由调用方分类处理。"""
    cfg = settings.JWT_CONFIG  # 与签发共用同一套配置，保证密钥/算法一致
    return jwt.decode(token, cfg['SECRET'], algorithms=[cfg['ALGORITHM']])  # 显式指定算法，防算法混淆攻击


class JWTAuthentication(BaseAuthentication):
    """从 Authorization: Bearer <token> 解析用户，失败抛 AuthFailed（code 401）。"""

    def authenticate(self, request):
        """解析请求头中的 token；无凭证返回 None，成功返回 (用户, 载荷)。"""
        auth = get_authorization_header(request).split()  # 拆成 [认证方案, token] 两段
        if not auth or auth[0].lower() != b'bearer':
            return None  # 非 Bearer 方案视为未认证，交给后续认证类处理
        if len(auth) != 2:
            raise AuthFailed('token 格式错误')  # 缺少 token 或多段内容都属格式错误
        token = auth[1].decode()  # 字节转字符串，PyJWT 只接受 str
        try:
            payload = decode_token(token)  # 解析并验证签名与有效期
        except jwt.ExpiredSignatureError:
            raise AuthFailed('登录已过期，请重新登录')  # 过期单独提示，前端可引导重新登录
        except jwt.InvalidTokenError:
            raise AuthFailed('无效的登录凭证')  # 签名错误、被篡改等统一提示

        from apps.system.models import SysUser  # 延迟导入，避免与应用初始化顺序耦合
        user = SysUser.objects.filter(id=payload['uid'], is_deleted=0, status=0).first()  # 只认未删除且启用的账号
        if not user:
            raise AuthFailed('用户不存在或已被禁用')  # 账号删除/禁用后旧 token 立即失效
        request.user_info = user  # 挂到 DRF request，供视图与权限类使用
        request.jwt_payload = payload  # 挂原始载荷，续期中间件需要其中的 exp
        # 同步挂到底层 Django request，供中间件（操作日志/续期）使用
        request._request.user_info = user  # 中间件拿到的是原生 HttpRequest，只能从这里读取
        request._request.jwt_payload = payload  # 同上，保证两处引用一致
        return (user, payload)  # DRF 约定二元组，第二项可通过 request.auth 访问


class LoginRequired:
    """权限基类：要求登录。"""

    def has_permission(self, request, view):
        """未携带有效用户信息时抛 401，否则放行给后续权限类。"""
        if getattr(request, 'user_info', None) is None:
            raise drf_exceptions.NotAuthenticated('请先登录')  # 用 NotAuthenticated 让全局处理器映射为 401
        return True  # 已登录，继续后续校验
