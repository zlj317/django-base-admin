"""安全策略模块序列化器。"""
from rest_framework import serializers

from apps.sec.models import SysIpControl, SysLoginAttempt, SysRateLimit


class SysIpControlSerializer(serializers.ModelSerializer):
    class Meta:
        model = SysIpControl
        fields = '__all__'


class SysLoginAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = SysLoginAttempt
        fields = '__all__'


class SysRateLimitSerializer(serializers.ModelSerializer):
    class Meta:
        model = SysRateLimit
        fields = '__all__'
