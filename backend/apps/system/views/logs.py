"""操作日志 / 登录日志。"""
from apps.system.models import SysLoginLog, SysOperLog
from apps.system.serializers import LoginLogSerializer, OperLogSerializer
from common.response import ok
from common.views import CrudViewSet


class OperLogViewSet(CrudViewSet):
    model = SysOperLog
    serializer_class = OperLogSerializer
    perm_prefix = 'system:operlog'
    module_name = '操作日志'
    filter_map = {'oper_user': 'icontains', 'module_name': 'icontains', 'oper_type': 'exact'}

    def clear(self, request):
        self.get_queryset().update(is_deleted=1)
        return ok(None, '日志已清空')


class LoginLogViewSet(CrudViewSet):
    model = SysLoginLog
    serializer_class = LoginLogSerializer
    perm_prefix = 'system:loginlog'
    module_name = '登录日志'
    filter_map = {'username': 'icontains', 'status': 'exact'}

    def clear(self, request):
        self.get_queryset().update(is_deleted=1)
        return ok(None, '日志已清空')
