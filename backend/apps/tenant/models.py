"""多租户模块模型（表结构由 docs 建表 SQL 手工创建，managed=False）。"""
from django.db import models
from common.fields import SnowflakeIDField  # 雪花算法主键字段

from common.utils import BaseModel


class SysTenant(BaseModel):
    """租户表。"""

    id = SnowflakeIDField(primary_key=True)
    tenant_name = models.CharField('租户名称', max_length=100)
    tenant_code = models.CharField('租户编码', max_length=100, unique=True)
    status = models.SmallIntegerField('状态', default=1)
    expire_time = models.DateTimeField('过期时间', blank=True, null=True)
    max_user_count = models.IntegerField('最大用户数', default=100)
    max_storage_mb = models.BigIntegerField('最大存储空间(MB)', default=2048)
    config_json = models.TextField('配置JSON', blank=True, null=True)
    remark = models.CharField('备注', max_length=500, blank=True, null=True)

    class Meta:
        db_table = 'sys_tenant'
        managed = False
        ordering = ['-id']


class SysTenantUser(models.Model):
    """租户用户关联表（不继承 BaseModel）。"""

    id = SnowflakeIDField(primary_key=True)
    tenant_id = models.BigIntegerField('租户ID')
    user_id = models.BigIntegerField('用户ID')
    is_tenant_admin = models.SmallIntegerField('是否租户管理员', default=0)
    join_time = models.DateTimeField('加入时间', blank=True, null=True)
    create_time = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'sys_tenant_user'
        managed = False
        ordering = ['-id']


class SysTenantPackage(models.Model):
    """租户套餐表（不继承 BaseModel，手动定义审计字段）。"""

    id = SnowflakeIDField(primary_key=True)
    package_name = models.CharField('套餐名称', max_length=100)
    max_user_count = models.IntegerField('最大用户数', default=100)
    max_storage_mb = models.BigIntegerField('最大存储空间(MB)', default=2048)
    price = models.DecimalField('价格', max_digits=10, decimal_places=2, default=0)
    status = models.SmallIntegerField('状态', default=1)
    remark = models.CharField('备注', max_length=500, blank=True, null=True)
    create_time = models.DateTimeField('创建时间', auto_now_add=True)
    update_time = models.DateTimeField('更新时间', auto_now_add=True)
    is_deleted = models.SmallIntegerField('逻辑删除', default=0)

    class Meta:
        db_table = 'sys_tenant_package'
        managed = False
        ordering = ['-id']