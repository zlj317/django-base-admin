"""脱敏配置模块视图集。"""
from common.pagination import StandardPagination
from common.views import CrudViewSet

from apps.dsm.models import DesensitizeField, DesensitizeRole, DesensitizeRule
from apps.dsm.serializers import (
    DesensitizeFieldSerializer,
    DesensitizeRoleSerializer,
    DesensitizeRuleSerializer,
)


class DesensitizeRuleViewSet(CrudViewSet):
    """脱敏规则 CRUD。"""
    model = DesensitizeRule
    serializer_class = DesensitizeRuleSerializer
    perm_prefix = 'dsm:rule'
    filter_map = {
        'rule_name': 'icontains',
        'rule_type': 'exact',
        'status': 'exact',
    }
    order_by = '-id'
    module_name = '脱敏规则'


class DesensitizeFieldViewSet(CrudViewSet):
    """脱敏字段 CRUD。"""
    model = DesensitizeField
    serializer_class = DesensitizeFieldSerializer
    perm_prefix = 'dsm:field'
    filter_map = {
        'rule_id': 'exact',
        'biz_type': 'icontains',
    }
    order_by = '-id'
    module_name = '脱敏字段'

    def get_queryset(self):
        return self.model.objects.order_by(self.order_by)

    def list(self, request):
        queryset = self.apply_filters(self.get_queryset(), request)
        return StandardPagination(request).paginate(queryset, self.get_serializer_class())


class DesensitizeRoleViewSet(CrudViewSet):
    """脱敏角色 CRUD。"""
    model = DesensitizeRole
    serializer_class = DesensitizeRoleSerializer
    perm_prefix = 'dsm:role'
    filter_map = {
        'role_id': 'exact',
        'rule_id': 'exact',
    }
    order_by = '-id'
    module_name = '脱敏角色'

    def get_queryset(self):
        return self.model.objects.order_by(self.order_by)

    def list(self, request):
        queryset = self.apply_filters(self.get_queryset(), request)
        return StandardPagination(request).paginate(queryset, self.get_serializer_class())
