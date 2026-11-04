"""脱敏配置模块序列化器。"""
from rest_framework import serializers

from apps.dsm.models import DesensitizeField, DesensitizeRole, DesensitizeRule


class DesensitizeRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = DesensitizeRule
        fields = '__all__'


class DesensitizeFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = DesensitizeField
        fields = '__all__'


class DesensitizeRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = DesensitizeRole
        fields = '__all__'
