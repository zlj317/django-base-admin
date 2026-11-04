"""监控告警模块视图集。"""
from common.pagination import StandardPagination
from common.views import CrudViewSet

from apps.mon.models import MonitorAlarmRecord, MonitorAlarmRule
from apps.mon.serializers import MonitorAlarmRecordSerializer, MonitorAlarmRuleSerializer


class MonitorAlarmRuleViewSet(CrudViewSet):
    """监控告警规则 CRUD。"""
    model = MonitorAlarmRule
    serializer_class = MonitorAlarmRuleSerializer
    perm_prefix = 'mon:rule'
    filter_map = {
        'rule_name': 'icontains',
        'monitor_type': 'exact',
        'alarm_level': 'exact',
        'status': 'exact',
    }
    order_by = '-id'
    module_name = '告警规则'

    def list(self, request):
        queryset = self.apply_filters(self.get_queryset(), request)
        return StandardPagination(request).paginate(queryset, self.get_serializer_class())


class MonitorAlarmRecordViewSet(CrudViewSet):
    """告警记录 CRUD。"""
    model = MonitorAlarmRecord
    serializer_class = MonitorAlarmRecordSerializer
    perm_prefix = 'mon:record'
    filter_map = {
        'rule_id': 'exact',
        'alarm_level': 'exact',
        'handle_status': 'exact',
    }
    order_by = '-id'
    module_name = '告警记录'

    def get_queryset(self):
        return self.model.objects.order_by(self.order_by)

    def list(self, request):
        queryset = self.apply_filters(self.get_queryset(), request)
        return StandardPagination(request).paginate(queryset, self.get_serializer_class())
