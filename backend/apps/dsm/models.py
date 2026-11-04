"""脱敏配置模块模型（表结构由 docs 建表 SQL 手工创建，managed=False）。"""
from django.db import models
from common.fields import SnowflakeIDField  # 雪花算法主键字段

from common.utils import BaseModel


class DesensitizeRule(BaseModel):
    """脱敏规则表：定义各类脱敏规则。"""

    id = SnowflakeIDField(primary_key=True)
    rule_name = models.CharField('规则名称', max_length=100)
    rule_type = models.CharField('规则类型', max_length=30, default='phone')
    mask_style = models.CharField('掩码样式', max_length=20, default='****')
    regular = models.CharField('正则表达式', max_length=255, blank=True, null=True)
    status = models.SmallIntegerField('状态', default=1)
    remark = models.CharField('备注', max_length=500, blank=True, null=True)

    class Meta:
        db_table = 'desensitize_rule'
        managed = False
        ordering = ['-id']


class DesensitizeField(models.Model):
    """脱敏字段表（不继承 BaseModel）：规则与字段的关联配置。"""

    id = SnowflakeIDField(primary_key=True)
    rule_id = models.BigIntegerField('规则ID')
    biz_type = models.CharField('业务类型', max_length=50, blank=True, null=True)
    field_name = models.CharField('字段名称', max_length=100, blank=True, null=True)
    status = models.SmallIntegerField('状态', default=1)
    create_time = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'desensitize_field'
        managed = False
        ordering = ['-id']


class DesensitizeRole(models.Model):
    """脱敏角色表（不继承 BaseModel）：角色与规则的关联。"""

    id = SnowflakeIDField(primary_key=True)
    role_id = models.BigIntegerField('角色ID')
    rule_id = models.BigIntegerField('规则ID')
    create_time = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'desensitize_role'
        managed = False
        ordering = ['-id']