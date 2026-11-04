"""工单模块视图集。"""
import time  # 生成日志时间

from rest_framework.decorators import action  # 自定义路由装饰器

from common.pagination import StandardPagination  # 统一分页
from common.response import fail, ok  # 统一响应封装
from common.views import CrudViewSet  # 通用 CRUD 基类

from apps.wo.models import WorkOrder, WorkOrderLog, WorkOrderType  # 工单相关模型
from apps.wo.serializers import WorkOrderLogSerializer, WorkOrderSerializer, WorkOrderTypeSerializer  # 对应序列化器


class WOTypeViewSet(CrudViewSet):
    """工单类型 CRUD。"""
    model = WorkOrderType
    serializer_class = WorkOrderTypeSerializer
    perm_prefix = 'wo'
    filter_map = {
        'type_name': 'icontains',
        'status': 'exact',
    }
    order_by = 'sort'
    module_name = '工单类型'


class WorkOrderViewSet(CrudViewSet):
    """工单 CRUD + assign/solve/close 动作。"""
    model = WorkOrder
    serializer_class = WorkOrderSerializer
    perm_prefix = 'wo'
    filter_map = {
        'title': 'icontains',
        'order_no': 'icontains',
        'status': 'exact',
        'priority': 'exact',
        'creator_id': 'exact',
        'assignee_id': 'exact',
    }
    order_by = '-id'
    module_name = '工单管理'

    def _write_log(self, order_id, operator_id, action, comment=''):
        """内部方法：向 work_order_log 插入一条日志。"""
        WorkOrderLog.objects.create(
            order_id=order_id,
            operator_id=operator_id,
            action=action,
            comment=comment,
            create_time=time.strftime('%Y-%m-%d %H:%M:%S'),
        )

    @action(detail=True, methods=['put'])
    def assign(self, request, pk=None):
        """指派处理人：assignee_id + 写 assign 日志。"""
        row = WorkOrder.objects.filter(pk=pk, is_deleted=0).first()
        if not row:
            return fail('工单不存在', code=404)
        user = getattr(request, 'user_info', None)
        assignee_id = request.data.get('assignee_id')
        if assignee_id is None:
            return fail('请指定处理人', code=400)
        now = time.strftime('%Y-%m-%d %H:%M:%S')
        row.assignee_id = assignee_id
        row.update_by = user.username if user else ''
        row.update_time = now
        row.save()
        self._write_log(pk, getattr(user, 'id', None), 'assign',
                        f'指派给用户ID {assignee_id}')
        return ok(WorkOrderSerializer(row).data, '指派成功')

    @action(detail=True, methods=['put'])
    def solve(self, request, pk=None):
        """标记已解决：status=2 + 写 solve 日志。"""
        row = WorkOrder.objects.filter(pk=pk, is_deleted=0).first()
        if not row:
            return fail('工单不存在', code=404)
        user = getattr(request, 'user_info', None)
        now = time.strftime('%Y-%m-%d %H:%M:%S')
        row.status = 2
        row.update_by = user.username if user else ''
        row.update_time = now
        row.save()
        self._write_log(pk, getattr(user, 'id', None), 'solve',
                        request.data.get('comment', '已解决'))
        return ok(WorkOrderSerializer(row).data, '解决成功')

    @action(detail=True, methods=['put'])
    def close(self, request, pk=None):
        """关闭工单：status=3 + close_time + 写 close 日志。"""
        row = WorkOrder.objects.filter(pk=pk, is_deleted=0).first()
        if not row:
            return fail('工单不存在', code=404)
        user = getattr(request, 'user_info', None)
        now = time.strftime('%Y-%m-%d %H:%M:%S')
        row.status = 3
        row.close_time = now
        row.update_by = user.username if user else ''
        row.update_time = now
        row.save()
        self._write_log(pk, getattr(user, 'id', None), 'close',
                        request.data.get('comment', '已关闭'))
        return ok(WorkOrderSerializer(row).data, '关闭成功')


class WOLogViewSet(CrudViewSet):
    """工单日志 CRUD（不继承 BaseModel，覆写 get_queryset）。"""
    model = WorkOrderLog
    serializer_class = WorkOrderLogSerializer
    perm_prefix = 'wo'
    filter_map = {
        'order_id': 'exact',
    }
    order_by = '-id'
    module_name = '工单日志'

    def get_queryset(self):
        """WorkOrderLog 无 is_deleted 字段，直接返回全部。"""
        return WorkOrderLog.objects.order_by(self.order_by)
