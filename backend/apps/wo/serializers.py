"""工单模块序列化器。"""
from rest_framework import serializers  # DRF 序列化/反序列化组件

from apps.wo.models import WorkOrder, WorkOrderLog, WorkOrderType  # 工单相关模型


class WorkOrderTypeSerializer(serializers.ModelSerializer):
    """工单类型序列化器：直接暴露全部字段。"""
    class Meta:
        model = WorkOrderType
        fields = '__all__'


class WorkOrderSerializer(serializers.ModelSerializer):
    """工单序列化器：直接暴露全部字段。"""
    class Meta:
        model = WorkOrder
        fields = '__all__'


class WorkOrderLogSerializer(serializers.ModelSerializer):
    """工单日志序列化器：直接暴露全部字段。"""
    class Meta:
        model = WorkOrderLog
        fields = '__all__'
