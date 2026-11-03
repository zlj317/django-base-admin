"""系统模块序列化器。"""
from rest_framework import serializers

from apps.system.models import (SysConfig, SysDept, SysDictData, SysDictType,
                                SysLoginLog, SysMenu, SysOperLog, SysRole,
                                SysUser)
from common.utils import hash_password


class UniqueExcludingDeleted:
    """唯一性校验（排除已逻辑删除的记录）。"""

    def __init__(self, model, field_name, message='该值已存在'):
        self.model = model
        self.field_name = field_name
        self.message = message

    def __call__(self, value):
        serializer = serializers.CharField()
        value = serializer.to_internal_value(value)
        qs = self.model.objects.filter(**{self.field_name: value}, is_deleted=0)
        if self.model.pk_value:
            qs = qs.exclude(pk=self.model.pk_value)
        if qs.exists():
            raise serializers.ValidationError(self.message)
        return value


def set_pk_value(model, pk):
    model.pk_value = pk


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = SysUser
        fields = ['id', 'username', 'password', 'nickname', 'phone', 'email',
                  'avatar', 'dept_id', 'status']

    def validate_username(self, value):
        if SysUser.objects.filter(username=value, is_deleted=0).exists():
            raise serializers.ValidationError('用户名已存在')
        return value

    def validate_password(self, value):
        return hash_password(value) if value else hash_password('123456')

    def validate_status(self, value):
        return int(bool(value))


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SysUser
        fields = ['id', 'username', 'nickname', 'phone', 'email', 'avatar',
                  'dept_id', 'status']

    def validate_username(self, value):
        qs = SysUser.objects.filter(username=value, is_deleted=0)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('用户名已存在')
        return value

    def validate_status(self, value):
        return int(bool(value))


class UserListSerializer(serializers.ModelSerializer):
    dept_name = serializers.SerializerMethodField()
    roles = serializers.SerializerMethodField()
    # 模型中 status 为 BooleanField（False=正常，True=停用），前端统一使用 0/1
    status = serializers.SerializerMethodField()

    class Meta:
        model = SysUser
        fields = ['id', 'username', 'nickname', 'phone', 'email', 'avatar',
                  'dept_id', 'dept_name', 'status', 'roles', 'create_time']

    def get_status(self, obj):
        return 1 if obj.status else 0

    def get_dept_name(self, obj):
        if obj.dept_id:
            return SysDept.objects.filter(id=obj.dept_id).values_list('dept_name', flat=True).first()
        return None

    def get_roles(self, obj):
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT r.id, r.role_name FROM sys_user_role ur "
                "JOIN sys_role r ON r.id = ur.role_id AND r.is_deleted = 0 "
                "WHERE ur.user_id = %s", [obj.id])
            return [{'id': r[0], 'role_name': r[1]} for r in cursor.fetchall()]


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = SysRole
        fields = ['id', 'role_name', 'role_key', 'role_sort', 'status',
                  'data_scope', 'remark', 'create_time']

    def validate_role_key(self, value):
        qs = SysRole.objects.filter(role_key=value, is_deleted=0)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('角色编码已存在')
        return value

    def validate_status(self, value):
        return int(bool(value))


class MenuSerializer(serializers.ModelSerializer):
    class Meta:
        model = SysMenu
        fields = ['id', 'parent_id', 'menu_name', 'path', 'component', 'perms',
                  'menu_type', 'icon', 'order_num', 'visible', 'status']

    def validate(self, attrs):
        instance = getattr(self, 'instance', None)
        pk = instance.pk if instance else None
        if attrs.get('parent_id') and attrs.get('parent_id') == pk:
            raise serializers.ValidationError('上级菜单不能选择自己')
        return attrs


class DeptSerializer(serializers.ModelSerializer):
    class Meta:
        model = SysDept
        fields = ['id', 'parent_id', 'dept_name', 'order_num', 'leader', 'phone', 'status']

    def validate(self, attrs):
        instance = getattr(self, 'instance', None)
        pk = instance.pk if instance else None
        if attrs.get('parent_id') and attrs.get('parent_id') == pk:
            raise serializers.ValidationError('上级部门不能选择自己')
        return attrs


class DictTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = SysDictType
        fields = ['id', 'dict_name', 'dict_type', 'status', 'remark', 'create_time']

    def validate_dict_type(self, value):
        qs = SysDictType.objects.filter(dict_type=value, is_deleted=0)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('字典类型编码已存在')
        return value

    def validate_status(self, value):
        return int(bool(value))


class DictDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = SysDictData
        fields = ['id', 'dict_type_id', 'dict_label', 'dict_value', 'dict_sort',
                  'status', 'remark', 'create_time']

    def validate_status(self, value):
        return int(bool(value))


class ConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = SysConfig
        fields = ['id', 'config_key', 'config_value', 'config_name', 'remark', 'create_time']

    def validate_config_key(self, value):
        qs = SysConfig.objects.filter(config_key=value, is_deleted=0)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('配置键已存在')
        return value


class OperLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = SysOperLog
        fields = '__all__'


class LoginLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = SysLoginLog
        fields = '__all__'
