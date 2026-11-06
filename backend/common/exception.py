"""全局异常处理：统一错误码返回。"""
# 模块定位：项目唯一的 DRF 异常出口，把各层抛出的异常压成 {"code","msg","data"} 结构。
# 调用登记：settings.REST_FRAMEWORK['EXCEPTION_HANDLER'] 指向 exception_handler。
# 关键约定：HTTP 状态码恒为 200，业务错误码放在 body.code，与 common.response.ok/fail 保持一致；
# 已知异常按类型映射 400/401/403/404，未登记异常一律 500 并打印堆栈，不向前端暴露 traceback。
import logging  # 记录未捕获异常，便于线上排查

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied  # 起别名区分 DRF 的同名异常
from django.http import Http404  # 非 DRF 视图也可能抛出 404
from rest_framework import exceptions as drf_exceptions  # DRF 异常类型，用于分类映射错误码
from rest_framework.response import Response  # 直接构造统一结构的响应体

logger = logging.getLogger(__name__)  # 以模块名为 logger 名，方便按模块配置日志级别

# 异常类型 -> 业务码的映射表：仅登记与默认 500 不同、且能确定语义的异常
CODE_MAP = {  # DRF 异常类型 -> 业务错误码
    drf_exceptions.NotAuthenticated: 401,  # 未登录
    drf_exceptions.AuthenticationFailed: 401,  # 认证失败（token 无效/过期等）
    drf_exceptions.PermissionDenied: 403,  # 已登录但无权限
}


# DRF 约定的异常处理入口：收到异常与上下文，返回 Response 或 None（None 才会继续向上抛）
def exception_handler(exc, context):
    """DRF 异常处理器：HTTP 状态恒为 200，业务码放 body.code。"""
    # 1) 404：路由不存在或 get_object_or_404 找不到对象，统一提示避免泄露资源细节
    if isinstance(exc, Http404):
        return Response({'code': 404, 'msg': '资源不存在', 'data': None})  # 路由或对象不存在统一提示
    # 2) Django 原生权限异常：非 DRF 视图（如中间件/管理命令）也可能抛这类异常
    if isinstance(exc, DjangoPermissionDenied):
        return Response({'code': 403, 'msg': '没有操作权限', 'data': None})  # Django 原生权限异常

    # 3) 参数校验异常：detail 可能是 dict（字段错误）也可能是 list，需要先归一成一条可读文案
    if isinstance(exc, drf_exceptions.ValidationError):
        msg = exc.detail  # 校验错误可能是 dict/list，先归一成一条可读文案
        # 字段级错误：detail 形如 {'username': ['该字段必填']}
        if isinstance(msg, dict):
            first = next(iter(msg.values()))  # 取第一个字段的错误，前端只需展示一条
            msg = first[0] if isinstance(first, (list, tuple)) else first  # 字段错误常为列表，取首项
        # 非字段错误：detail 直接是错误列表，空列表时保持原值避免取下标异常
        elif isinstance(msg, (list, tuple)) and msg:
            msg = msg[0]  # 非字段错误时同样取首条
        return Response({'code': 400, 'msg': str(msg), 'data': None})  # 参数校验失败固定 400

    # 4) 其余 DRF 异常：按 CODE_MAP 查表，未登记的按服务端错误处理（如 Throttled、ParseError）
    if isinstance(exc, drf_exceptions.APIException):
        code = CODE_MAP.get(type(exc), 500)  # 已知异常查表，未登记的按服务端错误处理
        # 保留原始提示文案，便于前端展示具体原因
        return Response({'code': code, 'msg': str(exc.detail if hasattr(exc, 'detail') else exc), 'data': None})

    # 5) 非 DRF 异常：属于代码缺陷，必须打印堆栈便于定位，同时对前端隐藏内部细节
    logger.exception('未捕获异常: %s', exc)  # 未知异常打印堆栈，方便定位根因
    return Response({'code': 500, 'msg': f'服务器内部错误: {exc}', 'data': None})  # 兜底 500，避免把堆栈暴露给前端
