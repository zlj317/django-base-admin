"""外部接口模块序列化器。"""
# 模块用途：把外部对接三张表的模型实例转换为 DRF 可输出、可校验的数据结构。
# 对应模型：OuterApiConfig（接口配置）、OuterApiRequestLog（调用日志）、OuterSyncTask（同步任务）。
# 设计说明：三张表字段少且没有外键关联对象，统一用 fields='__all__' 直接暴露，不做字段裁剪或嵌套。
# 注意：target_table、sync_field_json 等是自由文本，序列化器不做白名单校验，写入前需业务侧保证正确。
from rest_framework import serializers  # DRF 序列化/反序列化组件

from apps.outer.models import OuterApiConfig, OuterApiRequestLog, OuterSyncTask  # 外部接口相关模型


# 接口配置序列化器：新增/编辑时由 DRF 按模型字段类型做基本校验（如 max_length、choices）。
class OuterApiConfigSerializer(serializers.ModelSerializer):
    """外部API配置序列化器：直接暴露全部字段。"""
    # Meta 只声明目标模型与字段集合，校验规则沿用模型字段定义。
    class Meta:
        """声明模型与全部字段。"""
        model = OuterApiConfig  # 目标模型
        fields = '__all__'  # 全字段输出


# 调用日志序列化器：只用于列表/详情输出，日志由调用逻辑自动写入，一般不通过接口新增。
class OuterApiRequestLogSerializer(serializers.ModelSerializer):
    """外部API调用日志序列化器：直接暴露全部字段。"""
    # Meta 只声明目标模型与字段集合；日志表没有关联对象，无需额外字段处理。
    class Meta:
        """声明模型与全部字段。"""
        model = OuterApiRequestLog  # 目标模型
        fields = '__all__'  # 全字段输出


# 同步任务序列化器：用于任务定义的增删改查，不包含执行状态字段（执行结果目前不落库）。
class OuterSyncTaskSerializer(serializers.ModelSerializer):
    """外部数据同步任务序列化器：直接暴露全部字段。"""
    # Meta 只声明目标模型与字段集合；task_id 只是普通整数，不会自动关联 task_info 对象。
    class Meta:
        """声明模型与全部字段。"""
        model = OuterSyncTask  # 目标模型
        fields = '__all__'  # 全字段输出
