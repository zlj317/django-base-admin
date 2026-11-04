"""知识库模块序列化器。"""
from rest_framework import serializers  # DRF 序列化/反序列化组件

from apps.kb.models import KBCategory, KBDocument, KBFavorite  # 知识库相关模型


class KBCategorySerializer(serializers.ModelSerializer):
    """知识库分类序列化器：直接暴露全部字段。"""
    class Meta:
        model = KBCategory
        fields = '__all__'


class KBDocumentSerializer(serializers.ModelSerializer):
    """知识库文档序列化器：直接暴露全部字段。"""
    class Meta:
        model = KBDocument
        fields = '__all__'


class KBFavoriteSerializer(serializers.ModelSerializer):
    """知识收藏序列化器：直接暴露全部字段。"""
    class Meta:
        model = KBFavorite
        fields = '__all__'
