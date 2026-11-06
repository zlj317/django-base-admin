"""脱敏配置模块模型（表结构由 docs 建表 SQL 手工创建，managed=False）。"""
# 模块：apps/dsm/models.py —— 脱敏配置模块的 ORM 模型定义
# 用途：把三张脱敏配置表映射为 Django 模型，供序列化器与 CRUD 视图集读写。
# 对应表：desensitize_rule（规则主表）、desensitize_field（规则 → 业务字段）、
#         desensitize_role（角色 → 规则，语义是"该角色可看明文/豁免脱敏"）。
# 路由前缀：由 config/urls.py 以 /api/dsm/ 包含，最终为 /api/dsm/rule/*、/api/dsm/field/*、/api/dsm/role/*。
# 脱敏策略：本文件只保存规则元数据（rule_type=phone/idcard/bank/email/custom、mask_style 掩码样式、regular 可选正则）。
#   注意：全项目没有任何序列化器、中间件或查询出口读取这三张表并改写响应字段，
#   因此脱敏目前是"配置/预留"，不会真正作用在接口输出链路上（以代码为准）。
# 建表方式：三张表由 docs/new_features_init.sql 手工创建，Django 不参与建表与迁移，故 Meta.managed=False。
# 主键：统一用雪花算法 BigInt 主键（SnowflakeIDField），由后端生成，避免自增 ID 暴露数据量。
# Django ORM 基类与字段类型
from django.db import models
from common.fields import SnowflakeIDField  # 雪花算法主键字段

from common.utils import BaseModel


# 脱敏规则主表：一条规则描述"哪类数据怎么打码"，是字段配置与角色授权的被引用方
class DesensitizeRule(BaseModel):
    """脱敏规则表：定义各类脱敏规则。"""

    # 主键：雪花 ID，创建时由字段 default 自动生成，序列化器不接受前端传值
    id = SnowflakeIDField(primary_key=True)
    # 规则名称：展示用，如"手机号脱敏"；数据库为 NOT NULL，故未设 blank/null
    rule_name = models.CharField('规则名称', max_length=100)
    # 规则类型：决定脱敏算法分支；默认 phone，种子数据还有 idcard/bank/email/custom
    # 注意：前端页面下拉取值是 id_card/bank_card，与种子值的 idcard/bank 不一致（疑似问题，仅记录未改）
    rule_type = models.CharField('规则类型', max_length=30, default='phone')
    # 掩码样式：打码时使用的占位串（如 ****），长度上限 20；当前代码只存不用
    mask_style = models.CharField('掩码样式', max_length=20, default='****')
    # 正则表达式：custom 类型规则的匹配模板，可为空；当前没有代码编译/执行该正则
    regular = models.CharField('正则表达式', max_length=255, blank=True, null=True)
    # 状态：1=启用、0=停用；启停接口会直接改这个字段，但没有任何查询按它过滤脱敏行为
    status = models.SmallIntegerField('状态', default=1)
    # 备注：说明脱敏效果，如"只显示前3后4位"；500 字符足够，允许为空
    remark = models.CharField('备注', max_length=500, blank=True, null=True)

    class Meta:
        # 显式绑定已存在的物理表名，避免 Django 按 app_label+类名拼出错误表名
        db_table = 'desensitize_rule'
        # managed=False：表由 SQL 脚本维护，Django 不建表、不改表、不生成迁移
        managed = False
        # 默认按雪花 ID 倒序：ID 随时间递增，等价于"新建的在前"，列表分页结果稳定
        ordering = ['-id']


# 脱敏字段配置表：把规则挂到"业务类型 + 字段名"上（如 biz_type=system_user、field_name=phone）
# 该表未继承 BaseModel，因此没有 update_by/update_time/is_deleted 列，删除会走物理删除分支
class DesensitizeField(models.Model):
    """脱敏字段表（不继承 BaseModel）：规则与字段的关联配置。"""

    # 主键：雪花 ID，与其它业务表保持同一套 ID 生成策略
    id = SnowflakeIDField(primary_key=True)
    # 规则 ID：逻辑外键，指向 desensitize_rule.id；数据库未建外键约束，删除规则不会级联
    rule_id = models.BigIntegerField('规则ID')
    # 业务类型：标识数据所属业务（如 system_user），用于区分不同表里的同名字段；可空
    biz_type = models.CharField('业务类型', max_length=50, blank=True, null=True)
    # 字段名称：需要脱敏的具体列名（如 phone/id_card/email）；可空
    field_name = models.CharField('字段名称', max_length=100, blank=True, null=True)
    # 状态：1=启用、0=停用；当前没有脱敏逻辑读取它，仅作为配置项保存
    status = models.SmallIntegerField('状态', default=1)
    # 创建时间：auto_now_add=True 由 ORM 在首次保存时自动写入，序列化时为只读字段
    create_time = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        # 绑定手工建表 SQL 中的表名
        db_table = 'desensitize_field'
        # 表结构不由 Django 管理，避免 makemigrations 检测到差异
        managed = False
        # 新配置在前，便于列表页优先看到最近绑定的字段
        ordering = ['-id']


# 脱敏角色表：记录"哪些角色对某条规则拥有明文权限"（即豁免脱敏）
# 同样不继承 BaseModel：无审计字段、无逻辑删除，删除即物理删除
class DesensitizeRole(models.Model):
    """脱敏角色表（不继承 BaseModel）：角色与规则的关联。"""

    # 主键：雪花 ID
    id = SnowflakeIDField(primary_key=True)
    # 角色 ID：逻辑外键，指向 sys_role.id；无数据库外键约束
    role_id = models.BigIntegerField('角色ID')
    # 规则 ID：逻辑外键，指向 desensitize_rule.id；表示该角色可跳过这条脱敏规则
    rule_id = models.BigIntegerField('规则ID')
    # 创建时间：首次保存时自动写入，用于审计授权时间
    create_time = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        # 绑定手工建表 SQL 中的表名
        db_table = 'desensitize_role'
        # 不参与 Django 建表/迁移
        managed = False
        # 新授权在前
        ordering = ['-id']