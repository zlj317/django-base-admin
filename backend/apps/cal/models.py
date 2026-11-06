# 文件：apps/cal/models.py —— 日历日程模块的 ORM 模型定义
# 用途：把手工创建的日程表、提醒表映射成 Django 模型，供视图集与序列化器读写。
# 对应表：cal_schedule（日程主体）、cal_reminder（日程提醒）。
# 路由前缀：api/cal/schedule/、api/cal/reminder/（由 apps/cal/urls.py 生成）。
# 关键约定：两张表均由手工建表 SQL 创建，故 Meta 中 managed=False，migrate 不会建表/改表；
#           CalSchedule 继承 BaseModel（带审计列与 is_deleted），CalReminder 是纯记录表、不继承。
"""日历日程模块模型（表由建表 SQL 手工创建，managed=False）。"""
# Django ORM 字段与模型基类，用来声明各列的类型
from django.db import models  # Django ORM 字段与模型基类
# 雪花算法主键字段：数据库列为 BIGINT，ID 由后端生成，不走数据库自增
from common.fields import SnowflakeIDField  # 雪花算法主键字段

# 公共字段基类：创建/更新人、逻辑删除标记
from common.utils import BaseModel  # 公共字段基类：创建/更新人、逻辑删除


# 日程主表：一条记录就是日历上的一个事件，归属某用户并可共享给其他用户
class CalSchedule(BaseModel):
    """日程表：存储日历事件主体。"""
    # 主键：实例化时由雪花算法生成，不走数据库自增，保证插入前就能拿到 ID
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    # 标题必填，日历格子与列表页展示的主文本
    title = models.CharField('日程标题', max_length=200)  # 日程标题
    # 正文允许为空：用户可以只建一个"占位"日程而不写详情
    content = models.TextField('日程内容', blank=True, null=True)  # 日程详细描述
    # 开始时间可空，兼容只记录标题、稍后再补时间的场景
    start_time = models.DateTimeField('开始时间', blank=True, null=True)  # 日程开始时刻
    # 结束时间可空；前端据此计算日程时长与日历上的条块高度
    end_time = models.DateTimeField('结束时间', blank=True, null=True)  # 日程结束时刻
    # 全天标记用 tinyint 而非布尔，保持与手工建表 SQL 的列类型一致
    all_day = models.SmallIntegerField('是否全天', default=0)  # 0 否 / 1 是
    # 归属用户：用于"我的日程"过滤，允许为空以兼容历史脏数据
    owner_id = models.BigIntegerField('所有者ID', blank=True, null=True)  # 日程归属用户
    # 提前提醒分钟数：0 表示不提醒，由提醒任务据此推算提醒时间
    reminder_minutes = models.IntegerField('提前提醒分钟', default=0)  # 提前 N 分钟提醒
    # 提醒状态由提醒任务回写，避免同一条日程被重复推送
    remind_status = models.SmallIntegerField('提醒状态', default=0)  # 0 未提醒 / 1 已提醒
    # 共享用户列表存 JSON 字符串（手工表无 JSON 列），由前端解析成用户数组
    shared_json = models.CharField('共享用户列表', max_length=500, blank=True, null=True)  # 共享用户ID列表 JSON
    # 状态用于"取消但保留记录"，与物理删除区分，便于统计与追溯
    status = models.SmallIntegerField('状态', default=0)  # 0 正常 / 1 取消

    # 内部 Meta：声明物理表名、关闭 migrate 管理、指定默认排序
    class Meta:
        db_table = 'cal_schedule'  # 对应数据库物理表名
        # 关闭 migrate 管理：表结构以手工建表 SQL 为准，Django 不建表也不改表
        managed = False  # 不参与 migrate 的建表/改表
        # 默认排序：最新开始时间在前，列表与日历首屏顺序一致
        ordering = ['-start_time']  # 最新开始时间在前


# 提醒表：每次提醒一条记录，独立于日程以便按用户分别追踪发送状态
class CalReminder(models.Model):
    """日程提醒表（不继承 BaseModel）：记录每条提醒的发送与状态。"""
    # 主键同样由雪花算法生成，跨库迁移时不会与自增 ID 冲突
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    # 关联日程主键；不使用 ForeignKey，避免跨表约束与手工建表结构不一致
    schedule_id = models.BigIntegerField('日程ID')  # 关联 cal_schedule 主键
    # 被提醒人：同一条日程可能通知多个共享用户，因此单独成表
    remind_user_id = models.BigIntegerField('被提醒用户ID', blank=True, null=True)  # 接收提醒的用户
    # 应发送时刻，由日程开始时间减去提前分钟数算得
    remind_time = models.DateTimeField('提醒时间', blank=True, null=True)  # 提醒应发送的时刻
    # 状态机：待发送 → 已发送，或人工/任务置为已忽略
    remind_status = models.SmallIntegerField('提醒状态', default=0)  # 0 待发送 / 1 已发送 / 2 已忽略
    # 该表不继承 BaseModel，只保留创建时间这一列，无审计人与逻辑删除
    create_time = models.DateTimeField('创建时间', blank=True, null=True)  # 入库时间

    # 内部 Meta：手工表映射与默认排序
    class Meta:
        db_table = 'cal_reminder'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        # 雪花 ID 单调递增，按 id 倒序等价于按创建顺序倒序，最新的提醒排最前
        ordering = ['-id']  # 最新提醒在前