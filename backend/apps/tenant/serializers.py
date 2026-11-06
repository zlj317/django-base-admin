"""多租户模块序列化器。"""
# 文件：apps/tenant/serializers.py —— 多租户模块的 DRF 序列化器
# 用途：把三张租户表的模型实例与 JSON 双向转换，供视图集的新增、编辑、列表复用。
# 对应表：sys_tenant（租户主体）、sys_tenant_user（租户成员）、sys_tenant_package（租户套餐）。
# 路由前缀：/api/tenant/tenant/、/api/tenant/tenant_user/、/api/tenant/package/。
# 租户隔离：序列化层不做 tenant_id 归属校验或数据过滤，隔离能力仅为数据结构预留。
# 设计：统一使用 ModelSerializer + fields='__all__'，字段与模型一一对应，不额外做自定义校验。
# DRF 序列化器基类与 ModelSerializer
from rest_framework import serializers

# 三张租户表对应的模型
from apps.tenant.models import SysTenant, SysTenantPackage, SysTenantUser


# 租户主体序列化器：全字段读写；tenant_code 唯一性由模型 unique 约束与基类 create 预检共同保证
class SysTenantSerializer(serializers.ModelSerializer):
    class Meta:
        # 指定序列化目标模型，ModelSerializer 据此自动推断字段类型
        model = SysTenant
        # 输出/接收模型全部字段；雪花主键因 editable=False 不会要求前端传入
        fields = '__all__'


# 租户成员序列化器：用于新增/编辑"租户-用户"关系，并标记租户管理员
class SysTenantUserSerializer(serializers.ModelSerializer):
    class Meta:
        # 目标模型为租户成员关系表
        model = SysTenantUser
        # 全字段输出；create_time 为 auto_now_add，序列化时只读
        fields = '__all__'


# 租户套餐序列化器：负责套餐档位（用户数/存储/价格/上下架）的读写
class SysTenantPackageSerializer(serializers.ModelSerializer):
    class Meta:
        # 目标模型为租户套餐表
        model = SysTenantPackage
        # 全字段输出；is_deleted 由视图集查询层过滤，接口不额外暴露删除逻辑
        fields = '__all__'
