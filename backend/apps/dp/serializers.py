"""数据权限模块序列化器。"""
from rest_framework import serializers

from apps.dp.models import SysDataPermission, SysRoleDataPermission


class SysDataPermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SysDataPermission
        fields = '__all__'


class SysRoleDataPermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SysRoleDataPermission
        fields = '__all__'
