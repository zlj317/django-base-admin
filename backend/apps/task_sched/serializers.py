"""任务调度模块序列化器。"""
from rest_framework import serializers  # DRF 序列化/反序列化组件

from apps.task_sched.models import TaskInfo, TaskLog  # 任务相关模型


class TaskInfoSerializer(serializers.ModelSerializer):
    """任务信息序列化器：直接暴露全部字段。"""
    class Meta:
        """声明模型与全部字段。"""
        model = TaskInfo  # 目标模型
        fields = '__all__'  # 全字段输出


class TaskLogSerializer(serializers.ModelSerializer):
    """任务执行日志序列化器：直接暴露全部字段。"""
    class Meta:
        """声明模型与全部字段。"""
        model = TaskLog  # 目标模型
        fields = '__all__'  # 全字段输出
