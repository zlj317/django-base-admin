"""数据备份模块模型。"""
from django.db import models
from common.fields import SnowflakeIDField  # 雪花算法主键字段

from common.utils import BaseModel


class BackupRecord(BaseModel):
    """备份记录表。"""

    id = SnowflakeIDField(primary_key=True)
    backup_name = models.CharField('备份名称', max_length=100)
    backup_type = models.CharField('备份类型', max_length=20, blank=True, default='manual')
    db_name = models.CharField('数据库名', max_length=100, blank=True, null=True)
    file_id = models.BigIntegerField('备份文件ID', blank=True, null=True)
    file_size = models.BigIntegerField('文件大小(字节)', blank=True, null=True)
    encrypt_flag = models.SmallIntegerField('是否加密', default=0)
    backup_status = models.SmallIntegerField('备份状态', default=0)
    backup_time = models.DateTimeField('备份时间', blank=True, null=True)
    remark = models.CharField('备注', max_length=500, blank=True, null=True)

    class Meta:
        db_table = 'backup_record'
        managed = False
        ordering = ['-id']


class BackupStrategy(BaseModel):
    """备份策略表。"""

    id = SnowflakeIDField(primary_key=True)
    strategy_name = models.CharField('策略名称', max_length=100)
    cron_expr = models.CharField('Cron表达式', max_length=100, blank=True, null=True)
    keep_days = models.IntegerField('保留天数', default=7)
    encrypt_flag = models.SmallIntegerField('是否加密', default=0)
    status = models.SmallIntegerField('状态', default=1)
    remark = models.CharField('备注', max_length=500, blank=True, null=True)

    class Meta:
        db_table = 'backup_strategy'
        managed = False
        ordering = ['-id']