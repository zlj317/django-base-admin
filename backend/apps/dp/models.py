"""数据权限模块模型。"""
from django.db import models
from common.fields import SnowflakeIDField  # 雪花算法主键字段

from common.utils import BaseModel


class SysDataPermission(BaseModel):
    """数据权限表。"""

    id = SnowflakeIDField(primary_key=True)
    permission_name = models.CharField('权限名称', max_length=100)
    permission_type = models.CharField('权限类型', max_length=30, blank=True, default='all')
    scope_value = models.CharField('范围值', max_length=500, blank=True, null=True)
    sql_condition = models.CharField('SQL条件', max_length=1000, blank=True, null=True)
    sort = models.IntegerField('排序', default=0)
    status = models.SmallIntegerField('状态', default=1)
    remark = models.CharField('备注', max_length=500, blank=True, null=True)

    class Meta:
        db_table = 'sys_data_permission'
        managed = False
        ordering = ['sort', '-id']


class SysRoleDataPermission(models.Model):
    """角色-数据权限关联表（不继承 BaseModel）。"""

    id = SnowflakeIDField(primary_key=True)
    role_id = models.BigIntegerField('角色ID')
    permission_id = models.BigIntegerField('数据权限ID')
    create_time = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'sys_role_data_permission'
        managed = False
        ordering = ['-id']