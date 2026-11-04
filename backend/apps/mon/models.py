"""监控告警模块模型（表结构由 docs 建表 SQL 手工创建，managed=False）。"""
from django.db import models
from common.fields import SnowflakeIDField  # 雪花算法主键字段

from common.utils import BaseModel


class MonitorAlarmRule(BaseModel):
    """监控告警规则表：定义告警触发条件。"""

    id = SnowflakeIDField(primary_key=True)
    rule_name = models.CharField('规则名称', max_length=100)
    monitor_type = models.CharField('监控类型', max_length=30, default='service')
    compare_op = models.CharField('比较操作符', max_length=10, default='>')
    threshold = models.CharField('阈值', max_length=50, blank=True, null=True)
    alarm_level = models.SmallIntegerField('告警级别', default=1)
    channel = models.CharField('通知渠道', max_length=30, default='site')
    status = models.SmallIntegerField('状态', default=1)
    remark = models.CharField('备注', max_length=500, blank=True, null=True)

    class Meta:
        db_table = 'monitor_alarm_rule'
        managed = False
        ordering = ['-id']


class MonitorAlarmRecord(models.Model):
    """告警记录表（不继承 BaseModel）：已产生的告警事件。"""

    id = SnowflakeIDField(primary_key=True)
    rule_id = models.BigIntegerField('规则ID', blank=True, null=True)
    alarm_level = models.SmallIntegerField('告警级别', default=1)
    alarm_content = models.CharField('告警内容', max_length=1000, blank=True, null=True)
    alarm_time = models.DateTimeField('告警时间', blank=True, null=True)
    handle_status = models.SmallIntegerField('处理状态', default=0)
    handler_id = models.BigIntegerField('处理人ID', blank=True, null=True)
    handle_time = models.DateTimeField('处理时间', blank=True, null=True)
    create_time = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'monitor_alarm_record'
        managed = False
        ordering = ['-id']