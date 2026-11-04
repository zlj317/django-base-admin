"""文件模块序列化器。"""
from rest_framework import serializers  # DRF 序列化/反序列化组件

from apps.file.models import WfFile, WfFileConfig, WfFileRecycle  # 文件相关模型


class FileSerializer(serializers.ModelSerializer):
    """文件元信息序列化器：直接暴露全部字段。"""
    class Meta:
        """声明模型与全部字段。"""
        model = WfFile  # 目标模型
        fields = '__all__'  # 全字段输出


class FileConfigSerializer(serializers.ModelSerializer):
    """文件配置序列化器：直接暴露全部字段。"""
    class Meta:
        """声明模型与全部字段。"""
        model = WfFileConfig  # 目标模型
        fields = '__all__'  # 全字段输出


class FileRecycleSerializer(serializers.ModelSerializer):
    """文件回收站序列化器：直接暴露全部字段。"""
    class Meta:
        """声明模型与全部字段。"""
        model = WfFileRecycle  # 目标模型
        fields = '__all__'  # 全字段输出
