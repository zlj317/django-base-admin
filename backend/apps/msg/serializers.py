"""消息模块序列化器。"""
from rest_framework import serializers  # DRF 序列化/反序列化组件

from apps.msg.models import MsgRecord, MsgPushConfig, MsgPushLog, MsgTemplate  # 消息相关模型


class MsgTemplateSerializer(serializers.ModelSerializer):
    """消息模板序列化器：直接暴露全部字段。"""
    class Meta:
        """声明模型与全部字段。"""
        model = MsgTemplate  # 目标模型
        fields = '__all__'  # 全字段输出


class MsgRecordSerializer(serializers.ModelSerializer):
    """消息记录序列化器：直接暴露全部字段。"""
    class Meta:
        """声明模型与全部字段。"""
        model = MsgRecord  # 目标模型
        fields = '__all__'  # 全字段输出


class MsgPushLogSerializer(serializers.ModelSerializer):
    """消息推送日志序列化器：直接暴露全部字段。"""
    class Meta:
        """声明模型与全部字段。"""
        model = MsgPushLog  # 目标模型
        fields = '__all__'  # 全字段输出


class MsgPushConfigSerializer(serializers.ModelSerializer):
    """消息推送配置序列化器：直接暴露全部字段。"""
    class Meta:
        """声明模型与全部字段。"""
        model = MsgPushConfig  # 目标模型
        fields = '__all__'  # 全字段输出
