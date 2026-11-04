"""编码规则模块模型。"""
from django.db import models
from common.fields import SnowflakeIDField  # 雪花算法主键字段

from common.utils import BaseModel


class SysNoRule(BaseModel):
    """编码规则表：定义业务编号的生成规则。"""

    id = SnowflakeIDField(primary_key=True)
    rule_key = models.CharField('规则编码', max_length=100, unique=True)
    rule_name = models.CharField('规则名称', max_length=100)
    prefix = models.CharField('前缀', max_length=50, blank=True, default='')
    date_format = models.CharField('日期格式', max_length=20, blank=True, default='YYYYMMDD')
    seq_length = models.IntegerField('流水号长度', default=4)
    seq_current = models.IntegerField('当前流水', default=0)
    step = models.IntegerField('步长', default=1)
    separator = models.CharField('分隔符', max_length=10, blank=True, default='')
    reset_type = models.CharField('重置方式', max_length=20, blank=True, default='none')
    reset_time = models.DateField('重置时间', blank=True, null=True)
    status = models.SmallIntegerField('状态', default=1)
    remark = models.CharField('备注', max_length=500, blank=True, null=True)

    class Meta:
        db_table = 'sys_no_rule'
        managed = False
        ordering = ['-id']


class SysNoLog(models.Model):
    """编码生成日志表（不继承 BaseModel）。"""

    id = SnowflakeIDField(primary_key=True)
    rule_id = models.BigIntegerField('规则ID')
    no_value = models.CharField('生成编号', max_length=100)
    biz_type = models.CharField('业务类型', max_length=50, blank=True, null=True)
    biz_id = models.BigIntegerField('业务ID', blank=True, null=True)
    gen_user_id = models.BigIntegerField('生成用户ID', blank=True, null=True)
    gen_time = models.DateTimeField('生成时间', blank=True, null=True)
    create_time = models.DateTimeField('入库时间', auto_now_add=True)

    class Meta:
        db_table = 'sys_no_log'
        managed = False
        ordering = ['-id']