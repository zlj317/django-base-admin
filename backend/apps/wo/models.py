"""工单模块模型（表由建表 SQL 手工创建，managed=False）。"""
from django.db import models  # Django ORM 字段与模型基类
from common.fields import SnowflakeIDField  # 雪花算法主键字段

from common.utils import BaseModel  # 公共字段基类：创建/更新人、逻辑删除


class WorkOrderType(BaseModel):
    """工单类型表：定义工单分类。"""
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    type_name = models.CharField('类型名称', max_length=100)  # 工单类型名称
    sort = models.IntegerField('排序', default=0)  # 排序值，数值小排前
    status = models.SmallIntegerField('状态', default=1)  # 1 启用 / 0 停用
    remark = models.CharField('备注', max_length=500, blank=True, null=True)  # 备注说明

    class Meta:
        db_table = 'work_order_type'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['sort', 'id']  # 先按 sort 再按 id 升序


class WorkOrder(BaseModel):
    """工单表：存储工单主体信息。"""
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    order_no = models.CharField('工单编号', max_length=64, blank=True, null=True)  # 自动生成的编号
    order_type_id = models.BigIntegerField('工单类型ID', blank=True, null=True)  # 关联 work_order_type
    title = models.CharField('工单标题', max_length=200)  # 工单标题
    content = models.TextField('工单内容', blank=True, null=True)  # 工单详细描述
    attachment_ids = models.CharField('附件ID列表', max_length=500, blank=True, null=True)  # 附件 file_id 列表，逗号分隔
    priority = models.SmallIntegerField('优先级', default=2)  # 1 低 / 2 中 / 3 高
    status = models.SmallIntegerField('状态', default=0)  # 0 待处理 / 1 处理中 / 2 已解决 / 3 已关闭
    creator_id = models.BigIntegerField('创建人ID', blank=True, null=True)  # 创建工单的用户
    assignee_id = models.BigIntegerField('处理人ID', blank=True, null=True)  # 当前处理人
    expect_time = models.DateTimeField('期望完成时间', blank=True, null=True)  # 期望交付时间
    close_time = models.DateTimeField('关闭时间', blank=True, null=True)  # 工单实际关闭时间

    class Meta:
        db_table = 'work_order'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['-id']  # 按主键倒序


class WorkOrderLog(models.Model):
    """工单日志表（不继承 BaseModel）：记录工单流转与操作痕迹。"""
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    order_id = models.BigIntegerField('工单ID')  # 关联 work_order 主键
    operator_id = models.BigIntegerField('操作人ID', blank=True, null=True)  # 执行该操作的用户
    action = models.CharField('操作动作', max_length=50, blank=True, null=True)  # assign/solve/close 等
    comment = models.CharField('操作备注', max_length=1000, blank=True, null=True)  # 备注信息
    create_time = models.DateTimeField('创建时间', blank=True, null=True)  # 入库时间

    class Meta:
        db_table = 'work_order_log'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['-id']  # 最新日志在前