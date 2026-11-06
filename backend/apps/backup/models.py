"""数据备份模块模型。"""
# 文件：apps/backup/models.py —— 数据备份模块的 ORM 模型定义
# 用途：声明“备份记录表”与“备份策略表”的字段结构，供视图集与序列化器读写。
# 对应表：backup_record（每次备份的执行结果）、backup_strategy（自动备份的调度与保留规则）。
# 路由前缀：/api/backup/record/（记录 CRUD 与手动备份/下载）、/api/backup/strategy/（策略 CRUD 与启停）。
# 幂等性：本文件只声明模型结构，不产生数据；managed=False 表示建表由 SQL 脚本负责，重复导入无副作用。
# django.db.models：ORM 模块，提供各类字段与模型基类 Model
from django.db import models
# 雪花算法主键字段：生成 64 位趋势递增 ID，避免自增主键暴露数据规模并支持分布式生成
from common.fields import SnowflakeIDField  # 雪花算法主键字段

# 通用模型基类：提供 create_by/create_time/update_by/update_time/is_deleted 审计与逻辑删除字段
from common.utils import BaseModel


# 备份记录模型：每执行一次备份（手动或自动）产生一条记录，对应数据库表 backup_record
class BackupRecord(BaseModel):
    """备份记录表。"""

    # 主键：雪花 ID，在插入前由字段生成，非数据库自增，便于多节点部署时避免主键冲突
    id = SnowflakeIDField(primary_key=True)
    # 备份名称：展示用名称；手动备份时由“手动备份_时间戳”拼接，自动备份可由策略名生成
    backup_name = models.CharField('备份名称', max_length=100)
    # 备份类型：manual=手动触发，可扩展 auto/scheduled 等自动触发类型，默认 manual
    backup_type = models.CharField('备份类型', max_length=20, blank=True, default='manual')
    # 数据库名：记录本次备份的来源库，多库环境下用于区分数据来源
    db_name = models.CharField('数据库名', max_length=100, blank=True, null=True)
    # 备份文件 ID：预留关联 wf_file 的文件主键；演示环境未生成真实文件，因此允许为空
    file_id = models.BigIntegerField('备份文件ID', blank=True, null=True)
    # 文件大小：字节数，用于下载列表展示与容量统计；未生成真实文件时为空
    file_size = models.BigIntegerField('文件大小(字节)', blank=True, null=True)
    # 是否加密：0=不加密，1=加密，按执行时的策略快照写入，便于回溯当时的加密状态
    encrypt_flag = models.SmallIntegerField('是否加密', default=0)
    # 备份状态：0=初始/进行中，1=成功（手动备份为模拟实现，直接标记为 1），可扩展 2=失败
    backup_status = models.SmallIntegerField('备份状态', default=0)
    # 备份时间：实际执行时刻，用于前端展示、排序以及按保留天数做清理判断
    backup_time = models.DateTimeField('备份时间', blank=True, null=True)
    # 备注：记录触发来源、失败原因或“演示备份”等补充说明
    remark = models.CharField('备注', max_length=500, blank=True, null=True)

    # 模型元信息：物理表名、托管方式与默认排序
    class Meta:
        # 显式指定物理表名，避免 Django 默认的 app_label + 类名命名与初始化 SQL 不一致
        db_table = 'backup_record'
        # managed=False：Django 不负责建表与迁移，表结构由项目 SQL 脚本统一维护
        managed = False
        # 默认按主键倒序（雪花 ID 趋势递增），保证最新备份记录排在最前
        ordering = ['-id']


# 备份策略模型：定义自动备份的调度规则与文件保留周期，对应数据库表 backup_strategy
class BackupStrategy(BaseModel):
    """备份策略表。"""

    # 主键：雪花 ID，与备份记录表保持一致的主键生成方式，便于统一分页与排序
    id = SnowflakeIDField(primary_key=True)
    # 策略名称：如“每日全量备份”，用于策略列表展示与备份名称前缀
    strategy_name = models.CharField('策略名称', max_length=100)
    # Cron 表达式：定义自动备份的触发时间，例如 0 2 * * * 表示每天凌晨两点
    cron_expr = models.CharField('Cron表达式', max_length=100, blank=True, null=True)
    # 保留天数：备份文件保留期限，默认 7 天，过期后可由清理任务删除
    keep_days = models.IntegerField('保留天数', default=7)
    # 是否加密：0=不加密，1=加密，执行备份时作为参数传给实际备份逻辑
    encrypt_flag = models.SmallIntegerField('是否加密', default=0)
    # 状态：1=启用（会被调度执行），0=停用；默认新建策略即为启用
    status = models.SmallIntegerField('状态', default=1)
    # 备注：策略用途说明或创建原因
    remark = models.CharField('备注', max_length=500, blank=True, null=True)

    # 模型元信息：物理表名、托管方式与默认排序
    class Meta:
        # 物理表名，与初始化 SQL 中定义的表名一致
        db_table = 'backup_strategy'
        # managed=False：迁移系统不管理该表，避免与手工维护的表结构冲突
        managed = False
        # 默认按主键倒序，最新创建的策略排在最前
        ordering = ['-id']