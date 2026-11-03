"""全局异常处理：统一错误码返回。"""
import logging

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404
from rest_framework import exceptions as drf_exceptions
from rest_framework.response import Response

logger = logging.getLogger(__name__)

CODE_MAP = {
    drf_exceptions.NotAuthenticated: 401,
    drf_exceptions.AuthenticationFailed: 401,
    drf_exceptions.PermissionDenied: 403,
}


def exception_handler(exc, context):
    """DRF 异常处理器：HTTP 状态恒为 200，业务码放 body.code。"""
    if isinstance(exc, Http404):
        return Response({'code': 404, 'msg': '资源不存在', 'data': None})
    if isinstance(exc, DjangoPermissionDenied):
        return Response({'code': 403, 'msg': '没有操作权限', 'data': None})

    if isinstance(exc, drf_exceptions.ValidationError):
        msg = exc.detail
        if isinstance(msg, dict):
            first = next(iter(msg.values()))
            msg = first[0] if isinstance(first, (list, tuple)) else first
        elif isinstance(msg, (list, tuple)) and msg:
            msg = msg[0]
        return Response({'code': 400, 'msg': str(msg), 'data': None})

    if isinstance(exc, drf_exceptions.APIException):
        code = CODE_MAP.get(type(exc), 500)
        return Response({'code': code, 'msg': str(exc.detail if hasattr(exc, 'detail') else exc), 'data': None})

    logger.exception('未捕获异常: %s', exc)
    return Response({'code': 500, 'msg': f'服务器内部错误: {exc}', 'data': None})
