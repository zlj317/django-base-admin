"""数据备份模块视图集。"""
import datetime
import time as _time

from rest_framework.decorators import action

from common.response import ok
from common.views import CrudViewSet

from apps.backup.models import BackupRecord, BackupStrategy
from apps.backup.serializers import BackupRecordSerializer, BackupStrategySerializer


class BackupRecordViewSet(CrudViewSet):
    """备份记录表 CRUD。"""
    model = BackupRecord
    serializer_class = BackupRecordSerializer
    perm_prefix = 'backup'
    filter_map = {
        'backup_name': 'icontains',
        'backup_type': 'exact',
        'backup_status': 'exact',
    }
    order_by = '-id'
    module_name = '备份记录管理'

    @action(detail=False, methods=['post'])
    def manual_backup(self, request):
        """手动触发一次备份（模拟）：新增一条手动备份记录。"""
        from django.conf import settings
        now = datetime.datetime.now()
        row = BackupRecord.objects.create(
            backup_name=f'手动备份_{now.strftime("%Y%m%d%H%M%S")}',
            backup_type='manual',
            db_name=settings.DATABASES['default'].get('NAME') or '',
            backup_status=1,  # 模拟备份直接标记成功
            backup_time=now,
            remark='手动触发的模拟备份',
        )
        return ok(BackupRecordSerializer(row).data, '手动备份成功')


class BackupStrategyViewSet(CrudViewSet):
    """备份策略表 CRUD。"""
    model = BackupStrategy
    serializer_class = BackupStrategySerializer
    perm_prefix = 'backup'
    filter_map = {
        'strategy_name': 'icontains',
        'status': 'exact',
    }
    order_by = '-id'
    module_name = '备份策略管理'
