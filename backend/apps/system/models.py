"""系统基础模块模型（表结构由 docs 建表 SQL 手工创建，managed=False）。"""
from django.db import models

from common.utils import BaseModel


class SysDept(BaseModel):
    id = models.BigAutoField(primary_key=True)
    parent_id = models.BigIntegerField('父部门ID', default=0)
    dept_name = models.CharField('部门名称', max_length=50)
    order_num = models.IntegerField('排序', default=0)
    leader = models.CharField('负责人', max_length=50, blank=True, null=True)
    phone = models.CharField('联系电话', max_length=20, blank=True, null=True)
    status = models.CharField('状态', max_length=1, default='0')

    class Meta:
        db_table = 'sys_dept'
        managed = False
        ordering = ['order_num', 'id']


class SysUser(BaseModel):
    id = models.BigAutoField(primary_key=True)
    username = models.CharField('用户名', max_length=50, unique=True)
    password = models.CharField('密码', max_length=100)
    nickname = models.CharField('昵称', max_length=50, blank=True, null=True)
    phone = models.CharField('手机号', max_length=20, blank=True, null=True)
    email = models.CharField('邮箱', max_length=100, blank=True, null=True)
    avatar = models.CharField('头像地址', max_length=255, blank=True, null=True)
    dept_id = models.BigIntegerField('所属部门ID', blank=True, null=True)
    status = models.BooleanField('状态', default=False)  # 0启用 1禁用

    class Meta:
        db_table = 'sys_user'
        managed = False


class SysRole(BaseModel):
    id = models.BigAutoField(primary_key=True)
    role_name = models.CharField('角色名称', max_length=50)
    role_key = models.CharField('角色编码', max_length=50, unique=True)
    role_sort = models.IntegerField('角色排序', default=0)
    status = models.BooleanField('状态', default=False)
    data_scope = models.SmallIntegerField('数据权限', default=1)
    remark = models.CharField('备注', max_length=500, blank=True, null=True)

    class Meta:
        db_table = 'sys_role'
        managed = False
        ordering = ['role_sort', 'id']


class SysMenu(BaseModel):
    TYPE_CHOICES = (('M', '目录'), ('C', '菜单'), ('F', '按钮'))

    id = models.BigAutoField(primary_key=True)
    parent_id = models.BigIntegerField('父级菜单ID', default=0)
    menu_name = models.CharField('菜单名称', max_length=50)
    path = models.CharField('路由地址', max_length=200, blank=True, null=True)
    component = models.CharField('前端组件路径', max_length=255, blank=True, null=True)
    perms = models.CharField('权限标识', max_length=100, blank=True, null=True)
    menu_type = models.CharField('菜单类型', max_length=1, choices=TYPE_CHOICES, default='M')
    icon = models.CharField('图标', max_length=100, blank=True, null=True)
    order_num = models.IntegerField('排序', default=0)
    visible = models.CharField('是否可见', max_length=1, default='0')
    status = models.CharField('状态', max_length=1, default='0')

    class Meta:
        db_table = 'sys_menu'
        managed = False
        ordering = ['order_num', 'id']


class SysDictType(BaseModel):
    id = models.BigAutoField(primary_key=True)
    dict_name = models.CharField('字典名称', max_length=100)
    dict_type = models.CharField('字典类型编码', max_length=100, unique=True)
    status = models.BooleanField('状态', default=False)
    remark = models.CharField('备注', max_length=500, blank=True, null=True)

    class Meta:
        db_table = 'sys_dict_type'
        managed = False


class SysDictData(BaseModel):
    id = models.BigAutoField(primary_key=True)
    dict_type_id = models.BigIntegerField('字典类型ID')
    dict_label = models.CharField('字典标签', max_length=100)
    dict_value = models.CharField('字典键值', max_length=100)
    dict_sort = models.IntegerField('排序', default=0)
    status = models.BooleanField('状态', default=False)
    remark = models.CharField('备注', max_length=500, blank=True, null=True)

    class Meta:
        db_table = 'sys_dict_data'
        managed = False
        ordering = ['dict_sort', 'id']


class SysOperLog(models.Model):
    """日志表在 SQL 中无 create_by/update_by/update_time 公共字段，独立定义。"""

    id = models.BigAutoField(primary_key=True)
    oper_user = models.CharField('操作人', max_length=64, blank=True, null=True)
    module_name = models.CharField('操作模块', max_length=50, blank=True, null=True)
    oper_type = models.CharField('操作类型', max_length=20, blank=True, null=True)
    request_url = models.CharField('请求地址', max_length=255, blank=True, null=True)
    request_param = models.TextField('请求参数', blank=True, null=True)
    response_result = models.TextField('响应结果', blank=True, null=True)
    cost_time = models.BigIntegerField('耗时毫秒', blank=True, null=True)
    oper_time = models.DateTimeField('操作时间', blank=True, null=True)
    create_time = models.DateTimeField('创建时间', blank=True, null=True)
    is_deleted = models.BooleanField('逻辑删除', default=False)

    class Meta:
        db_table = 'sys_oper_log'
        managed = False
        ordering = ['-id']


class SysLoginLog(models.Model):
    id = models.BigAutoField(primary_key=True)
    username = models.CharField('登录账号', max_length=50, blank=True, null=True)
    ip = models.CharField('登录IP', max_length=50, blank=True, null=True)
    login_time = models.DateTimeField('登录时间', blank=True, null=True)
    status = models.BooleanField('登录状态', default=False)  # 0成功 1失败
    browser = models.CharField('浏览器信息', max_length=100, blank=True, null=True)
    msg = models.CharField('提示消息', max_length=255, blank=True, null=True)
    create_time = models.DateTimeField('创建时间', blank=True, null=True)
    is_deleted = models.BooleanField('逻辑删除', default=False)

    class Meta:
        db_table = 'sys_login_log'
        managed = False
        ordering = ['-id']


class SysConfig(BaseModel):
    id = models.BigAutoField(primary_key=True)
    config_key = models.CharField('配置键', max_length=100, unique=True)
    config_value = models.CharField('配置值', max_length=500, blank=True, null=True)
    config_name = models.CharField('配置名称', max_length=100, blank=True, null=True)
    remark = models.CharField('备注', max_length=500, blank=True, null=True)

    class Meta:
        db_table = 'sys_config'
        managed = False
