"""JWT 认证：签发 / 校验 token，认证类附加 request.user_info。"""
import time

import jwt
from django.conf import settings
from rest_framework import exceptions as drf_exceptions
from rest_framework.authentication import BaseAuthentication, get_authorization_header


class AuthFailed(drf_exceptions.AuthenticationFailed):
    """认证失败，统一转成 code=401 响应。"""

    def __init__(self, msg):
        super().__init__(detail=msg)


def create_token(user):
    cfg = settings.JWT_CONFIG
    payload = {
        'uid': user['id'] if isinstance(user, dict) else user.id,
        'username': user['username'] if isinstance(user, dict) else user.username,
        'exp': int(time.time() + cfg['EXPIRE'].total_seconds()),
    }
    return jwt.encode(payload, cfg['SECRET'], algorithm=cfg['ALGORITHM'])


def decode_token(token):
    cfg = settings.JWT_CONFIG
    return jwt.decode(token, cfg['SECRET'], algorithms=[cfg['ALGORITHM']])


class JWTAuthentication(BaseAuthentication):
    """从 Authorization: Bearer <token> 解析用户，失败抛 AuthFailed（code 401）。"""

    def authenticate(self, request):
        auth = get_authorization_header(request).split()
        if not auth or auth[0].lower() != b'bearer':
            return None
        if len(auth) != 2:
            raise AuthFailed('token 格式错误')
        token = auth[1].decode()
        try:
            payload = decode_token(token)
        except jwt.ExpiredSignatureError:
            raise AuthFailed('登录已过期，请重新登录')
        except jwt.InvalidTokenError:
            raise AuthFailed('无效的登录凭证')

        from apps.system.models import SysUser
        user = SysUser.objects.filter(id=payload['uid'], is_deleted=0, status=0).first()
        if not user:
            raise AuthFailed('用户不存在或已被禁用')
        request.user_info = user
        request.jwt_payload = payload
        # 同步挂到底层 Django request，供中间件（操作日志/续期）使用
        request._request.user_info = user
        request._request.jwt_payload = payload
        return (user, payload)


class LoginRequired:
    """权限基类：要求登录。"""

    def has_permission(self, request, view):
        if getattr(request, 'user_info', None) is None:
            raise drf_exceptions.NotAuthenticated('请先登录')
        return True
