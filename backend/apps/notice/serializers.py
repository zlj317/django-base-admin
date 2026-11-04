"""公告模块序列化器。"""
from rest_framework import serializers  # DRF 序列化/反序列化组件

from apps.notice.models import NoticeCategory, NoticeInfo, NoticeRead  # 公告相关模型


class NoticeCategorySerializer(serializers.ModelSerializer):
    """公告分类序列化器：直接暴露全部字段。"""
    class Meta:
        """声明模型与全部字段。"""
        model = NoticeCategory  # 目标模型
        fields = '__all__'  # 全字段输出


class NoticeInfoSerializer(serializers.ModelSerializer):
    """公告信息序列化器：直接暴露全部字段。"""
    class Meta:
        """声明模型与全部字段。"""
        model = NoticeInfo  # 目标模型
        fields = '__all__'  # 全字段输出


class NoticeReadSerializer(serializers.ModelSerializer):
    """公告阅读记录序列化器：直接暴露全部字段。"""
    class Meta:
        """声明模型与全部字段。"""
        model = NoticeRead  # 目标模型
        fields = '__all__'  # 全字段输出
