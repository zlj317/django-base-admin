"""报表模块序列化器。"""
from rest_framework import serializers  # DRF 序列化/反序列化组件

from apps.report.models import RpCategory, RpDatasource, RpGenerateRecord, RpTemplate  # 报表相关模型


class RpCategorySerializer(serializers.ModelSerializer):
    """报表分类序列化器：直接暴露全部字段。"""
    class Meta:
        """声明模型与全部字段。"""
        model = RpCategory  # 目标模型
        fields = '__all__'  # 全字段输出


class RpDatasourceSerializer(serializers.ModelSerializer):
    """报表数据源序列化器：直接暴露全部字段。"""
    class Meta:
        """声明模型与全部字段。"""
        model = RpDatasource  # 目标模型
        fields = '__all__'  # 全字段输出


class RpTemplateSerializer(serializers.ModelSerializer):
    """报表模板序列化器：直接暴露全部字段。"""
    class Meta:
        """声明模型与全部字段。"""
        model = RpTemplate  # 目标模型
        fields = '__all__'  # 全字段输出


class RpGenerateRecordSerializer(serializers.ModelSerializer):
    """报表生成记录序列化器：直接暴露全部字段。"""
    class Meta:
        """声明模型与全部字段。"""
        model = RpGenerateRecord  # 目标模型
        fields = '__all__'  # 全字段输出
