"""外部接口模块序列化器。"""
from rest_framework import serializers  # DRF 序列化/反序列化组件

from apps.outer.models import OuterApiConfig, OuterApiRequestLog, OuterSyncTask  # 外部接口相关模型


class OuterApiConfigSerializer(serializers.ModelSerializer):
    """外部API配置序列化器：直接暴露全部字段。"""
    class Meta:
        """声明模型与全部字段。"""
        model = OuterApiConfig  # 目标模型
        fields = '__all__'  # 全字段输出


class OuterApiRequestLogSerializer(serializers.ModelSerializer):
    """外部API调用日志序列化器：直接暴露全部字段。"""
    class Meta:
        """声明模型与全部字段。"""
        model = OuterApiRequestLog  # 目标模型
        fields = '__all__'  # 全字段输出


class OuterSyncTaskSerializer(serializers.ModelSerializer):
    """外部数据同步任务序列化器：直接暴露全部字段。"""
    class Meta:
        """声明模型与全部字段。"""
        model = OuterSyncTask  # 目标模型
        fields = '__all__'  # 全字段输出
