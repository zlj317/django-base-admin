"""安全策略模块模型（表结构由 docs 建表 SQL 手工创建，managed=False）。"""
from django.db import models
from common.fields import SnowflakeIDField  # 雪花算法主键字段

from common.utils import BaseModel


class SysIpControl(BaseModel):
    """IP 黑白名单表。"""

    id = SnowflakeIDField(primary_key=True)
    ip = models.CharField('IP地址', max_length=50)
    control_type = models.CharField('控制类型', max_length=10, default='black')
    reason = models.CharField('原因', max_length=255, blank=True, null=True)
    status = models.SmallIntegerField('状态', default=1)
    expire_time = models.DateTimeField('过期时间', blank=True, null=True)

    class Meta:
        db_table = 'sys_ip_control'
        managed = False
        ordering = ['-id']


class SysLoginAttempt(models.Model):
    """登录尝试记录表（不继承 BaseModel）。"""

    id = SnowflakeIDField(primary_key=True)
    username = models.CharField('用户名', max_length=64, blank=True, null=True)
    ip = models.CharField('IP地址', max_length=50, blank=True, null=True)
    attempt_time = models.DateTimeField('尝试时间', blank=True, null=True)
    success_flag = models.SmallIntegerField('是否成功', default=0)
    create_time = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'sys_login_attempt'
        managed = False
        ordering = ['-id']


class SysRateLimit(BaseModel):
    """限流规则表。"""

    id = SnowflakeIDField(primary_key=True)
    rule_name = models.CharField('规则名称', max_length=100)
    limit_url = models.CharField('限制URL', max_length=255, blank=True, null=True)
    period_sec = models.IntegerField('时间周期(秒)', default=60)
    max_count = models.IntegerField('最大请求数', default=100)
    status = models.SmallIntegerField('状态', default=1)

    class Meta:
        db_table = 'sys_rate_limit'
        managed = False
        ordering = ['-id']