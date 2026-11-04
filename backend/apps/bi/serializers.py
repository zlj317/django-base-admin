"""大屏BI模块序列化器。"""
from rest_framework import serializers  # DRF 序列化/反序列化组件

from apps.bi.models import BiDataset, BiScreen, BiVisitLog  # BI 相关模型


class BiScreenSerializer(serializers.ModelSerializer):
    """大屏信息序列化器：直接暴露全部字段。"""
    class Meta:
        """声明模型与全部字段。"""
        model = BiScreen  # 目标模型
        fields = '__all__'  # 全字段输出


class BiDatasetSerializer(serializers.ModelSerializer):
    """大屏数据集序列化器：直接暴露全部字段。"""
    class Meta:
        """声明模型与全部字段。"""
        model = BiDataset  # 目标模型
        fields = '__all__'  # 全字段输出


class BiVisitLogSerializer(serializers.ModelSerializer):
    """大屏访问日志序列化器：直接暴露全部字段。"""
    class Meta:
        """声明模型与全部字段。"""
        model = BiVisitLog  # 目标模型
        fields = '__all__'  # 全字段输出
