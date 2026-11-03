"""中间件：操作日志记录 + token 静默续期。"""
import json
import logging
import time

from apps.system.models import SysOperLog

logger = logging.getLogger(__name__)

OPER_TYPE_MAP = [
    ('importTemplate', '导入'),
    ('importData', '导入'),
    ('import', '导入'),
    ('export', '导出'),
    ('create', '新增'),
    ('update', '编辑'),
    ('delete', '删除'),
    ('assign', '编辑'),
    ('reset_pwd', '编辑'),
    ('status', '编辑'),
]

SKIP_PATHS = ('/api/auth/login', '/api/auth/logout')


def get_client_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    return xff.split(',')[0].strip() if xff else request.META.get('REMOTE_ADDR', '')


class OperLogMiddleware:
    """记录写操作到 sys_oper_log。"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        started = time.time()
        body = b''
        if request.method in ('POST', 'PUT', 'DELETE') and not request.path.startswith(SKIP_PATHS):
            try:
                body = request.body[:2000]
            except Exception:
                body = b''
        response = self.get_response(request)
        if request.method in ('POST', 'PUT', 'DELETE') and request.path.startswith('/api/') \
                and not request.path.startswith(SKIP_PATHS):
            try:
                self.save_log(request, response, body, int((time.time() - started) * 1000))
            except Exception:
                logger.exception('记录操作日志失败: %s %s', request.method, request.path)
        return response

    def save_log(self, request, response, body, cost_ms):
        oper_type = '其他'
        path = request.path.rstrip('/')
        for keyword, label in OPER_TYPE_MAP:
            if keyword in path:
                oper_type = label
                break
        try:
            param = body.decode('utf-8', errors='ignore') if body else ''
        except Exception:
            param = ''
        try:
            if isinstance(response.content, bytes):
                result = response.content[:2000].decode('utf-8', errors='ignore')
            else:
                result = ''
        except Exception:
            result = ''

        user = getattr(request, 'user_info', None)
        # 未认证的写请求（401）不记录
        if user is None and getattr(response, 'status_code', 200) != 200:
            return
        module_name = ''
        match = getattr(request, 'resolver_match', None)
        func = getattr(match, 'func', None) if match else None
        # Django View 设置 view_class；DRF ViewSet 只设置 cls
        view_class = getattr(func, 'view_class', None) or getattr(func, 'cls', None)
        if view_class is not None:
            module_name = getattr(view_class, 'module_name', '')
        SysOperLog.objects.create(
            oper_user=user.username if user else '',
            module_name=module_name,
            oper_type=oper_type,
            request_url=request.path,
            request_param=param,
            response_result=result,
            cost_time=cost_ms,
            oper_time=time.strftime('%Y-%m-%d %H:%M:%S'),
        )


class TokenRefreshMiddleware:
    """token 剩余有效期不足阈值时，在响应头下发新 token（X-Refresh-Token）。"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        payload = getattr(request, 'jwt_payload', None)
        if payload and 'exp' in payload:
            from datetime import datetime, timedelta
            from django.conf import settings
            from common.auth import create_token

            remain = datetime.fromtimestamp(payload['exp']) - datetime.now()
            threshold = settings.JWT_CONFIG['REFRESH_THRESHOLD']
            if remain < threshold and remain.total_seconds() > 0:
                user = getattr(request, 'user_info', None)
                if user is not None:
                    response['X-Refresh-Token'] = create_token(user)
        return response
