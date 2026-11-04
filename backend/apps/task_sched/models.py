"""任务调度模块模型（表结构由 docs 建表 SQL 手工创建，managed=False）。"""
from django.db import models  # Django ORM 字段与模型基类

from common.utils import BaseModel  # 公共字段基类：创建/更新人、逻辑删除


class TaskInfo(BaseModel):
    """定时任务信息表：以 task_key 唯一标识一项可调度的任务。"""
    TASK_TYPE_CHOICES = (('cron', 'Cron表达式'), ('interval', '固定间隔'))  # 调度类型可选值

    id = models.BigAutoField(primary_key=True)  # 主键，自增
    task_name = models.CharField('任务名称', max_length=200)  # 显示名称
    task_key = models.CharField('任务编码', max_length=100, unique=True)  # 唯一编码，程序引用用
    task_type = models.CharField('调度类型', max_length=16, choices=TASK_TYPE_CHOICES, default='cron')  # 类型
    cron_expr = models.CharField('Cron表达式', max_length=100, blank=True, null=True)  # 如 0 0 * * * ?
    interval_sec = models.IntegerField('间隔秒数', default=60)  # interval 类型下生效
    params = models.TextField('任务参数(JSON)', blank=True, null=True)  # 传递给任务执行函数的 JSON 参数
    status = models.SmallIntegerField('状态', default=0)  # 0 正常(运行) / 1 暂停
    retry_on_fail = models.SmallIntegerField('失败重试', default=0)  # 0 否 / 1 是
    retry_count = models.IntegerField('最大重试次数', default=0)  # 单次失败最多重试几次
    remark = models.CharField('备注', max_length=500, blank=True, null=True)  # 备注说明

    class Meta:
        """指定真实表名；表由 SQL 手工维护，故不参与迁移。"""
        db_table = 'task_info'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['-id']  # 默认按主键倒序


class TaskLog(models.Model):
    """任务执行日志表（不继承 BaseModel）：记录每次调度运行结果。"""
    RUN_STATUS_CHOICES = ((0, '运行中'), (1, '成功'), (2, '失败'))  # 运行状态可选值

    id = models.BigAutoField(primary_key=True)  # 主键，自增
    task_id = models.BigIntegerField('任务ID')  # 关联 task_info 主键
    task_name = models.CharField('任务名称', max_length=200, blank=True, null=True)  # 任务名称快照
    run_status = models.SmallIntegerField('运行状态', choices=RUN_STATUS_CHOICES, default=0)  # 0/1/2
    return_info = models.TextField('返回结果', blank=True, null=True)  # 任务执行的返回内容
    error_msg = models.TextField('错误信息', blank=True, null=True)  # 失败时的错误详情
    cost_time = models.BigIntegerField('耗时毫秒', blank=True, null=True)  # 运行耗时
    run_time = models.DateTimeField('开始运行时间', blank=True, null=True)  # 开始执行时刻
    create_time = models.DateTimeField('创建时间', blank=True, null=True)  # 入库时间

    class Meta:
        """指定真实表名；表由 SQL 手工维护，故不参与迁移。"""
        db_table = 'task_log'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['-id']  # 默认按主键倒序，最新运行在前
