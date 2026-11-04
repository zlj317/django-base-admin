"""消息模块模型（表结构由 docs 建表 SQL 手工创建，managed=False）。"""
from django.db import models  # Django ORM 字段与模型基类
from common.fields import SnowflakeIDField  # 雪花算法主键字段

from common.utils import BaseModel  # 公共字段基类：创建/更新人、逻辑删除


class MsgTemplate(BaseModel):
    """消息模板表：以 template_code 唯一标识一种消息模板。"""
    MSG_TYPE_CHOICES = (('notice', '通知'), ('alert', '告警'), ('todo', '待办'))  # 消息类型可选值

    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    template_code = models.CharField('模板编码', max_length=100, unique=True)  # 唯一编码，程序引用用
    template_name = models.CharField('模板名称', max_length=200)  # 显示名称
    msg_type = models.CharField('消息类型', max_length=16, choices=MSG_TYPE_CHOICES, default='notice')  # 类型
    template_content = models.TextField('模板内容', blank=True, null=True)  # 支持变量占位符的模板正文
    channel = models.CharField('推送渠道', max_length=64, blank=True, null=True)  # 逗号分隔：sms,email,wechat
    status = models.SmallIntegerField('状态', default=0)  # 0 正常 / 1 停用
    remark = models.CharField('备注', max_length=500, blank=True, null=True)  # 备注说明

    class Meta:
        """指定真实表名；表由 SQL 手工维护，故不参与迁移。"""
        db_table = 'msg_template'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['-id']  # 默认按主键倒序


class MsgRecord(BaseModel):
    """消息记录表：记录每条发送给用户的消息。"""
    MSG_TYPE_CHOICES = (('notice', '通知'), ('alert', '告警'), ('todo', '待办'))  # 消息类型可选值

    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    msg_type = models.CharField('消息类型', max_length=16, choices=MSG_TYPE_CHOICES, default='notice')  # 类型
    title = models.CharField('消息标题', max_length=200, blank=True, null=True)  # 标题行
    content = models.TextField('消息内容', blank=True, null=True)  # 消息正文
    receiver_id = models.BigIntegerField('接收人ID')  # 目标用户 ID
    link_url = models.CharField('跳转链接', max_length=500, blank=True, null=True)  # 点击后跳转的 URL
    biz_type = models.CharField('业务类型', max_length=64, blank=True, null=True)  # 关联业务类型
    biz_id = models.BigIntegerField('业务ID', blank=True, null=True)  # 关联业务主键
    is_read = models.SmallIntegerField('是否已读', default=0)  # 0 未读 / 1 已读
    read_time = models.DateTimeField('阅读时间', blank=True, null=True)  # 用户点击阅读的时间

    class Meta:
        """指定真实表名；表由 SQL 手工维护，故不参与迁移。"""
        db_table = 'msg_record'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['-id']  # 默认按主键倒序，最新消息在前


class MsgPushLog(models.Model):
    """消息推送日志表（不继承 BaseModel）：记录各渠道推送结果。"""
    PUSH_STATUS_CHOICES = ((0, '待推送'), (1, '成功'), (2, '失败'))  # 推送状态可选值

    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    record_id = models.BigIntegerField('消息记录ID')  # 关联 msg_record 主键
    receiver_id = models.BigIntegerField('接收人ID', blank=True, null=True)  # 接收人用户 ID
    channel = models.CharField('推送渠道', max_length=32, blank=True, null=True)  # sms/email/wechat 等
    push_status = models.SmallIntegerField('推送状态', choices=PUSH_STATUS_CHOICES, default=0)  # 0/1/2
    error_msg = models.TextField('错误信息', blank=True, null=True)  # 失败时的错误详情
    retry_count = models.IntegerField('重试次数', default=0)  # 已重试次数
    push_time = models.DateTimeField('推送时间', blank=True, null=True)  # 实际推送时刻
    create_time = models.DateTimeField('创建时间', blank=True, null=True)  # 入库时间

    class Meta:
        """指定真实表名；表由 SQL 手工维护，故不参与迁移。"""
        db_table = 'msg_push_log'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['-id']  # 默认按主键倒序


class MsgPushConfig(BaseModel):
    """消息推送配置表：以 channel 唯一标识一个渠道的推送参数。"""
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    channel = models.CharField('推送渠道', max_length=32, unique=True)  # sms/email/wechat/dingtalk 等
    channel_name = models.CharField('渠道名称', max_length=100)  # 显示名称
    enabled = models.SmallIntegerField('是否启用', default=0)  # 0 否 / 1 是
    config_json = models.TextField('渠道配置(JSON)', blank=True, null=True)  # 渠道专属配置 JSON 文本
    remark = models.CharField('备注', max_length=500, blank=True, null=True)  # 备注说明

    class Meta:
        """指定真实表名；表由 SQL 手工维护，故不参与迁移。"""
        db_table = 'msg_push_config'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表