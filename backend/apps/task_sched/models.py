"""任务调度模块模型（表结构由 docs 建表 SQL 手工创建，managed=False）。"""
# 模块用途：定义定时任务主表 task_info 与执行日志表 task_log 的 ORM 映射，供调度与查询使用。
# 对应路由：apps/task_sched/views.py 中 TaskInfoViewSet / TaskLogViewSet 对两张表做 CRUD。
# 权限：模型层不做权限控制，接口鉴权由视图的 perm_prefix='task' 生成 task:* 权限标识后校验。
# 表来源：建表语句位于 docs 的 SQL 文档，由数据库初始化脚本执行，因此 Meta.managed=False 不参与迁移。
# 被谁调用：task_sched/serializers.py、views.py、seed.py，以及调度执行逻辑。
from django.db import models  # Django ORM 字段与模型基类
from common.fields import SnowflakeIDField  # 雪花算法主键字段

from common.utils import BaseModel  # 公共字段基类：创建/更新人、逻辑删除


# 任务主表：一条记录代表一个可被调度器识别的任务，task_key 是程序侧引用该任务的唯一编码。
class TaskInfo(BaseModel):
    """定时任务信息表：以 task_key 唯一标识一项可调度的任务。"""
    TASK_TYPE_CHOICES = (('cron', 'Cron表达式'), ('interval', '固定间隔'))  # 调度类型可选值

    # 身份与配置字段：task_key 全局唯一；cron_expr 与 interval_sec 分属两种调度方式，按 task_type 取用。
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    task_name = models.CharField('任务名称', max_length=200)  # 显示名称
    task_key = models.CharField('任务编码', max_length=100, unique=True)  # 唯一编码，程序引用用
    task_type = models.CharField('调度类型', max_length=16, choices=TASK_TYPE_CHOICES, default='cron')  # 类型
    cron_expr = models.CharField('Cron表达式', max_length=100, blank=True, null=True)  # 如 0 0 * * * ?
    interval_sec = models.IntegerField('间隔秒数', default=60)  # interval 类型下生效
    params = models.TextField('任务参数(JSON)', blank=True, null=True)  # 传递给任务执行函数的 JSON 参数
    # 运行控制字段：status 控制启停，retry_on_fail/retry_count 控制失败重试策略。
    status = models.SmallIntegerField('状态', default=0)  # 0 正常(运行) / 1 暂停
    retry_on_fail = models.SmallIntegerField('失败重试', default=0)  # 0 否 / 1 是
    retry_count = models.IntegerField('最大重试次数', default=0)  # 单次失败最多重试几次
    remark = models.CharField('备注', max_length=500, blank=True, null=True)  # 备注说明

    class Meta:
        """指定真实表名；表由 SQL 手工维护，故不参与迁移。"""
        db_table = 'task_info'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['-id']  # 默认按主键倒序


# 日志表：每次调度（含手动触发）写一行，记录状态、返回内容、错误与耗时；无逻辑删除字段。
class TaskLog(models.Model):
    """任务执行日志表（不继承 BaseModel）：记录每次调度运行结果。"""
    RUN_STATUS_CHOICES = ((0, '运行中'), (1, '成功'), (2, '失败'))  # 运行状态可选值

    # 关联与状态字段：task_id 为逻辑外键（未建物理外键，删除任务后日志仍保留）；task_name 冗余快照。
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    task_id = models.BigIntegerField('任务ID')  # 关联 task_info 主键
    task_name = models.CharField('任务名称', max_length=200, blank=True, null=True)  # 任务名称快照
    run_status = models.SmallIntegerField('运行状态', choices=RUN_STATUS_CHOICES, default=0)  # 0/1/2
    # 结果字段：成功写 return_info，失败写 error_msg，二者都保留便于排查。
    return_info = models.TextField('返回结果', blank=True, null=True)  # 任务执行的返回内容
    error_msg = models.TextField('错误信息', blank=True, null=True)  # 失败时的错误详情
    # 时间字段：run_time 是开始执行时刻，create_time 是日志入库时刻，格式与手工建表 SQL 的 DATETIME 对齐。
    cost_time = models.BigIntegerField('耗时毫秒', blank=True, null=True)  # 运行耗时
    run_time = models.DateTimeField('开始运行时间', blank=True, null=True)  # 开始执行时刻
    create_time = models.DateTimeField('创建时间', blank=True, null=True)  # 入库时间

    class Meta:
        """指定真实表名；表由 SQL 手工维护，故不参与迁移。"""
        db_table = 'task_log'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['-id']  # 默认按主键倒序，最新运行在前