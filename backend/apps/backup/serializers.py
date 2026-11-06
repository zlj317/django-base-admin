"""数据备份模块序列化器。"""
# 文件：apps/backup/serializers.py —— 数据备份模块的序列化层
# 用途：在模型与 JSON 之间做双向转换；视图集的 list/create/update 与自定义动作都通过它输出数据。
# 对应表：backup_record（备份记录）、backup_strategy（备份策略）。
# 路由前缀：/api/backup/record/、/api/backup/strategy/。
# 幂等性：序列化器无状态，只负责字段转换与校验，重复调用不会写入数据库。
# DRF 序列化模块：提供 ModelSerializer 基类与字段校验能力
from rest_framework import serializers

# 备份相关模型：序列化器的字段来源与写入目标
from apps.backup.models import BackupRecord, BackupStrategy


# 备份记录序列化器：模型字段与 JSON 一一映射，新增/编辑时按字段类型自动校验
class BackupRecordSerializer(serializers.ModelSerializer):
    # 内部配置类：声明绑定的模型与字段范围
    class Meta:
        # 绑定备份记录模型，字段名、类型、可空等规则直接继承模型定义
        model = BackupRecord
        # '__all__' 表示输出全部模型字段（含主键与审计字段），前端无需再维护字段清单
        fields = '__all__'


# 备份策略序列化器：与记录序列化器结构一致，仅绑定的模型不同
class BackupStrategySerializer(serializers.ModelSerializer):
    # 内部配置类：声明绑定的模型与字段范围
    class Meta:
        # 绑定备份策略模型
        model = BackupStrategy
        # 全字段输出：包含 cron_expr、keep_days、status 等策略配置项
        fields = '__all__'
