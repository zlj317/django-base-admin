"""编码规则模块视图集。"""
from rest_framework.decorators import action

from common.response import fail, ok
from common.views import CrudViewSet

from apps.sys_no.models import SysNoLog, SysNoRule
from apps.sys_no.serializers import SysNoLogSerializer, SysNoRuleSerializer


class SysNoRuleViewSet(CrudViewSet):
    """编码规则表 CRUD。"""
    model = SysNoRule
    serializer_class = SysNoRuleSerializer
    perm_prefix = 'sys_no'
    filter_map = {
        'rule_key': 'icontains',
        'rule_name': 'icontains',
        'status': 'exact',
    }
    order_by = '-id'
    module_name = '编码规则管理'

    @action(detail=True, methods=['post'])
    def generate(self, request, pk=None):
        """模拟生成一个编号：拼接前缀+日期+流水号并记录日志。"""
        row = SysNoRule.objects.filter(pk=pk, is_deleted=0).first()
        if not row:
            return fail('规则不存在', code=404)
        import datetime
        now = datetime.datetime.now()
        row.seq_current = (row.seq_current or 0) + row.step
        row.save(update_fields=['seq_current', 'update_time'])
        date_part = now.strftime('%Y%m%d')
        seq = str(row.seq_current).zfill(row.seq_length or 4)
        sep = row.separator or ''
        no_value = f"{row.prefix}{sep}{date_part}{sep}{seq}"
        user = getattr(request, 'user_info', None)
        SysNoLog.objects.create(
            rule_id=row.id,
            no_value=no_value,
            biz_type=request.data.get('biz_type'),
            biz_id=request.data.get('biz_id'),
            gen_user_id=user.id if user else None,
            gen_time=now,
        )
        return ok({'no_value': no_value}, '生成成功')


class SysNoLogViewSet(CrudViewSet):
    """编码生成日志表 CRUD（无 BaseModel，覆写 get_queryset）。"""
    model = SysNoLog
    serializer_class = SysNoLogSerializer
    perm_prefix = 'sys_no'
    filter_map = {
        'rule_id': 'exact',
        'biz_type': 'icontains',
    }
    order_by = '-id'
    module_name = '编码生成日志'

    def get_queryset(self):
        return self.model.objects.order_by(self.order_by)
