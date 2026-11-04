"""安全策略模块视图集。"""
from common.pagination import StandardPagination
from common.views import CrudViewSet

from apps.sec.models import SysIpControl, SysLoginAttempt, SysRateLimit
from apps.sec.serializers import (
    SysIpControlSerializer,
    SysLoginAttemptSerializer,
    SysRateLimitSerializer,
)


class SysIpControlViewSet(CrudViewSet):
    """IP 黑白名单 CRUD。"""
    model = SysIpControl
    serializer_class = SysIpControlSerializer
    perm_prefix = 'sec:ip'
    filter_map = {
        'ip': 'icontains',
        'control_type': 'exact',
        'status': 'exact',
    }
    order_by = '-id'
    module_name = 'IP黑白名单'


class SysLoginAttemptViewSet(CrudViewSet):
    """登录尝试记录 CRUD。"""
    model = SysLoginAttempt
    serializer_class = SysLoginAttemptSerializer
    perm_prefix = 'sec:login_attempt'
    filter_map = {
        'username': 'icontains',
    }
    order_by = '-id'
    module_name = '登录记录'

    def get_queryset(self):
        return self.model.objects.order_by(self.order_by)

    def list(self, request):
        queryset = self.apply_filters(self.get_queryset(), request)
        return StandardPagination(request).paginate(queryset, self.get_serializer_class())


class SysRateLimitViewSet(CrudViewSet):
    """限流规则 CRUD。"""
    model = SysRateLimit
    serializer_class = SysRateLimitSerializer
    perm_prefix = 'sec:rate_limit'
    filter_map = {
        'rule_name': 'icontains',
        'limit_url': 'icontains',
        'status': 'exact',
    }
    order_by = '-id'
    module_name = '限流规则'
