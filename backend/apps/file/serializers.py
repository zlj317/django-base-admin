"""文件模块序列化器。"""
# 本模块把三张文件相关表直接映射成 DRF 序列化器：
# 字段全部由模型声明自动生成，接口层不需要再做逐字段转换。
from rest_framework import serializers  # DRF 序列化/反序列化组件

from apps.file.models import WfFile, WfFileConfig, WfFileRecycle  # 文件相关模型


class FileSerializer(serializers.ModelSerializer):  # 附件主表序列化器
    """文件元信息序列化器：直接暴露全部字段。"""
    class Meta:  # 元信息：绑定模型与字段范围
        """声明模型与全部字段。"""
        model = WfFile  # 目标模型
        fields = '__all__'  # 全字段输出


class FileConfigSerializer(serializers.ModelSerializer):  # 上传配置表序列化器
    """文件配置序列化器：直接暴露全部字段。"""
    class Meta:  # 元信息：绑定模型与字段范围
        """声明模型与全部字段。"""
        model = WfFileConfig  # 目标模型
        fields = '__all__'  # 全字段输出


class FileRecycleSerializer(serializers.ModelSerializer):  # 附件回收站序列化器
    """文件回收站序列化器：直接暴露全部字段。"""
    class Meta:  # 元信息：绑定模型与字段范围
        """声明模型与全部字段。"""
        model = WfFileRecycle  # 目标模型
        fields = '__all__'  # 全字段输出
