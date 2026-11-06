"""编码规则模块序列化器。"""
# 模块：apps/sys_no/serializers.py —— 编码规则与生成日志的 DRF 序列化器
# 用途：把 SysNoRule / SysNoLog 模型实例与 JSON 互转，供 views.py 中 ViewSet 的增删改查与生成动作使用。
# 约定：两张表都是简单标量字段（无嵌套关系），因此直接用 ModelSerializer + fields='__all__'，
#       不额外声明字段，避免字段白名单与模型定义脱节；必填、长度、唯一等校验由模型字段自动推导。
from rest_framework import serializers

from apps.sys_no.models import SysNoLog, SysNoRule


# 规则序列化器：用于列表输出、新增校验与编辑（partial=True）校验
class SysNoRuleSerializer(serializers.ModelSerializer):
    # 元信息：声明绑定模型与输出字段范围
    class Meta:
        # 绑定规则模型，ModelSerializer 据此自动生成字段与校验器
        model = SysNoRule
        # 输出模型全部字段；rule_key 的 unique 约束会自动转成唯一性校验器
        fields = '__all__'


# 日志序列化器：日志以只读查询为主，此序列化器负责列表/详情输出
class SysNoLogSerializer(serializers.ModelSerializer):
    # 元信息：声明绑定模型与输出字段范围
    class Meta:
        # 绑定日志模型
        model = SysNoLog
        # 输出全部字段；create_time 由模型 auto_now_add 自动填充，无需前端提交
        fields = '__all__'
