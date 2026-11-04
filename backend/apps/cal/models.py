"""日历日程模块模型（表由建表 SQL 手工创建，managed=False）。"""
from django.db import models  # Django ORM 字段与模型基类
from common.fields import SnowflakeIDField  # 雪花算法主键字段

from common.utils import BaseModel  # 公共字段基类：创建/更新人、逻辑删除


class CalSchedule(BaseModel):
    """日程表：存储日历事件主体。"""
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    title = models.CharField('日程标题', max_length=200)  # 日程标题
    content = models.TextField('日程内容', blank=True, null=True)  # 日程详细描述
    start_time = models.DateTimeField('开始时间', blank=True, null=True)  # 日程开始时刻
    end_time = models.DateTimeField('结束时间', blank=True, null=True)  # 日程结束时刻
    all_day = models.SmallIntegerField('是否全天', default=0)  # 0 否 / 1 是
    owner_id = models.BigIntegerField('所有者ID', blank=True, null=True)  # 日程归属用户
    reminder_minutes = models.IntegerField('提前提醒分钟', default=0)  # 提前 N 分钟提醒
    remind_status = models.SmallIntegerField('提醒状态', default=0)  # 0 未提醒 / 1 已提醒
    shared_json = models.CharField('共享用户列表', max_length=500, blank=True, null=True)  # 共享用户ID列表 JSON
    status = models.SmallIntegerField('状态', default=0)  # 0 正常 / 1 取消

    class Meta:
        db_table = 'cal_schedule'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['-start_time']  # 最新开始时间在前


class CalReminder(models.Model):
    """日程提醒表（不继承 BaseModel）：记录每条提醒的发送与状态。"""
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    schedule_id = models.BigIntegerField('日程ID')  # 关联 cal_schedule 主键
    remind_user_id = models.BigIntegerField('被提醒用户ID', blank=True, null=True)  # 接收提醒的用户
    remind_time = models.DateTimeField('提醒时间', blank=True, null=True)  # 提醒应发送的时刻
    remind_status = models.SmallIntegerField('提醒状态', default=0)  # 0 待发送 / 1 已发送 / 2 已忽略
    create_time = models.DateTimeField('创建时间', blank=True, null=True)  # 入库时间

    class Meta:
        db_table = 'cal_reminder'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['-id']  # 最新提醒在前