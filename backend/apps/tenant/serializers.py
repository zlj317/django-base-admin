"""多租户模块序列化器。"""
from rest_framework import serializers

from apps.tenant.models import SysTenant, SysTenantPackage, SysTenantUser


class SysTenantSerializer(serializers.ModelSerializer):
    class Meta:
        model = SysTenant
        fields = '__all__'


class SysTenantUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = SysTenantUser
        fields = '__all__'


class SysTenantPackageSerializer(serializers.ModelSerializer):
    class Meta:
        model = SysTenantPackage
        fields = '__all__'
