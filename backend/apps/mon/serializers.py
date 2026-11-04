"""监控告警模块序列化器。"""
from rest_framework import serializers

from apps.mon.models import MonitorAlarmRecord, MonitorAlarmRule


class MonitorAlarmRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = MonitorAlarmRule
        fields = '__all__'


class MonitorAlarmRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = MonitorAlarmRecord
        fields = '__all__'
