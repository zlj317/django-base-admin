"""脱敏配置模块序列化器。"""
# 模块：apps/dsm/serializers.py —— 脱敏配置三张表的 DRF 序列化器
# 用途：为 /api/dsm/rule|field|role 的 CRUD 接口提供出参序列化与入参校验。
# 对应表：desensitize_rule、desensitize_field、desensitize_role（表由 SQL 手工创建，模型 managed=False）。
# 脱敏策略：序列化器只做字段透传，不做任何值替换；
#   当前项目没有任何输出链路读取脱敏规则并改写字段值，故脱敏仍属"配置/预留"，不会真正生效。
# 字段策略：三个序列化器都用 fields='__all__'，即整表字段原样暴露（含审计字段与雪花主键）。
# DRF 序列化器框架，ModelSerializer 自动映射模型字段
from rest_framework import serializers

from apps.dsm.models import DesensitizeField, DesensitizeRole, DesensitizeRule


# 脱敏规则序列化器：规则配置页的列表/新增/编辑共用
class DesensitizeRuleSerializer(serializers.ModelSerializer):
    class Meta:
        # 绑定规则主表模型，字段类型、max_length、默认值、可空性均由模型映射而来
        model = DesensitizeRule
        # 输出全部字段：id、rule_name、rule_type、mask_style、regular、status、remark 及审计字段；
        # 雪花主键因 editable=False 不会从请求体中接收，其余字段前端可原样提交
        fields = '__all__'


# 脱敏字段配置序列化器：维护"规则 → 业务字段"的绑定关系
class DesensitizeFieldSerializer(serializers.ModelSerializer):
    class Meta:
        # 绑定字段配置表；该表无 is_deleted/审计字段，故输出里也不会出现这些键
        model = DesensitizeField
        # 输出全部字段：id、rule_id、biz_type、field_name、status、create_time
        # create_time 为 auto_now_add，新增时只读，由 ORM 自动写入
        fields = '__all__'


# 脱敏角色关联序列化器：维护"角色 → 规则"的明文权限
class DesensitizeRoleSerializer(serializers.ModelSerializer):
    class Meta:
        # 绑定角色关联表
        model = DesensitizeRole
        # 输出全部字段：id、role_id、rule_id、create_time
        # 唯一性（uk_role_rule）由数据库索引保证，序列化器未额外校验，重复绑定会由数据库报错
        fields = '__all__'
