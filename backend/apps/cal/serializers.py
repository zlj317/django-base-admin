"""日历日程模块序列化器。"""
from rest_framework import serializers  # DRF 序列化/反序列化组件

from apps.cal.models import CalReminder, CalSchedule  # 日程相关模型


class CalScheduleSerializer(serializers.ModelSerializer):
    """日程序列化器：直接暴露全部字段。"""
    class Meta:
        model = CalSchedule
        fields = '__all__'


class CalReminderSerializer(serializers.ModelSerializer):
    """日程提醒序列化器：直接暴露全部字段。"""
    class Meta:
        model = CalReminder
        fields = '__all__'
