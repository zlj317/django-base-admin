"""日历日程模块视图集。"""
from common.views import CrudViewSet  # 通用 CRUD 基类

from apps.cal.models import CalReminder, CalSchedule  # 日程相关模型
from apps.cal.serializers import CalReminderSerializer, CalScheduleSerializer  # 对应序列化器


class ScheduleViewSet(CrudViewSet):
    """日程 CRUD。"""
    model = CalSchedule
    serializer_class = CalScheduleSerializer
    perm_prefix = 'cal'
    filter_map = {
        'title': 'icontains',
        'owner_id': 'exact',
        'status': 'exact',
    }
    order_by = '-start_time'
    module_name = '日程管理'


class ReminderViewSet(CrudViewSet):
    """日程提醒 CRUD（不继承 BaseModel，覆写 get_queryset）。"""
    model = CalReminder
    serializer_class = CalReminderSerializer
    perm_prefix = 'cal'
    filter_map = {
        'schedule_id': 'exact',
        'remind_status': 'exact',
    }
    order_by = '-id'
    module_name = '日程提醒'

    def get_queryset(self):
        """CalReminder 无 is_deleted 字段，直接返回全部。"""
        return CalReminder.objects.order_by(self.order_by)
