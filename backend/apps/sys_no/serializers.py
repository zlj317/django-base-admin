"""编码规则模块序列化器。"""
from rest_framework import serializers

from apps.sys_no.models import SysNoLog, SysNoRule


class SysNoRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = SysNoRule
        fields = '__all__'


class SysNoLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = SysNoLog
        fields = '__all__'
