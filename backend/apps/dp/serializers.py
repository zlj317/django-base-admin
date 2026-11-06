"""数据权限模块序列化器。"""
# 文件：backend/apps/dp/serializers.py
# 用途：把两张数据权限表映射为 DRF 序列化器，供 /api/dp/ 下的 CRUD 接口做入参校验与出参序列化。
# 对应表：sys_data_permission、sys_role_data_permission。
# 数据范围生效方式：序列化器只负责字段透传，不解析 permission_type/scope_value/sql_condition；
#   当前没有业务查询使用这些规则，属于配置/预留能力，不会自动限制任何列表数据。
# DRF 序列化器框架：提供 ModelSerializer 与字段校验能力
from rest_framework import serializers

# 本模块的两张表模型：规则主表与角色授权关联表
from apps.dp.models import SysDataPermission, SysRoleDataPermission


# 数据权限规则序列化器：直接复用模型字段定义，避免重复声明字段造成校验规则不一致
class SysDataPermissionSerializer(serializers.ModelSerializer):
    # Meta 决定序列化的模型、字段集合与自动生成的校验器
    class Meta:
        # 绑定规则主表模型；字段类型、max_length、blank/null 等约束由模型自动映射到序列化字段
        model = SysDataPermission
        # 输出全部字段：配置页需要完整展示审计字段、范围类型、范围值、SQL 条件与状态
        # 同时新增/编辑时接受这些字段；序列化器未限制 id、is_deleted 等，基类只会强制覆盖部分审计字段
        fields = '__all__'


# 角色-数据权限关联序列化器：用于维护"角色 → 数据权限规则"的授权关系
class SysRoleDataPermissionSerializer(serializers.ModelSerializer):
    # Meta 仅声明模型与字段，不额外做唯一性约束，因此同一角色可重复绑定同一规则
    class Meta:
        # 绑定角色授权关联表
        model = SysRoleDataPermission
        # 输出全部字段：id、role_id、permission_id、create_time
        # create_time 是 auto_now_add，序列化时只读；新增时由数据库/ORM 自动写入，不依赖前端传值
        fields = '__all__'
