"""导入模板 + 打印模板模块序列化器。"""
from rest_framework import serializers

from apps.imprint.models import ImpTemplate, ImpTemplateColumn, PrintTemplate


class ImpTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImpTemplate
        fields = '__all__'


class ImpTemplateColumnSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImpTemplateColumn
        fields = '__all__'


class PrintTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrintTemplate
        fields = '__all__'
