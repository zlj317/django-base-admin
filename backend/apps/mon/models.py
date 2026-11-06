"""监控告警模块模型（表结构由 docs 建表 SQL 手工创建，managed=False）。"""
# 模块：apps/mon/models.py —— 监控告警模块的模型定义
# 用途：声明“告警规则”与“告警记录”两张表的 ORM 映射，供 mon 模块视图集与序列化器使用。
# 对应表：monitor_alarm_rule（规则表）、monitor_alarm_record（告警记录表）。
# 建表方式：两张表都由 docs 下的建表 SQL 手工创建，managed=False 表示 Django 不参与建表/改表。
# 路由前缀：/api/mon/；规则接口 rule/*，记录接口 record/*（见 apps/mon/urls.py）。
# 告警生命周期：规则定义触发条件 → 命中后写入告警记录 → 运维确认/处理（handle_status、
#               handler_id、handle_time）→ 处理完毕即闭环；规则本身可启用/停用（status）。
# Django ORM 基类与字段类型
from django.db import models
# 雪花算法主键字段：插入前即可确定主键值
from common.fields import SnowflakeIDField  # 雪花算法主键字段

# 业务模型基类，提供 is_deleted 与创建/更新审计字段
from common.utils import BaseModel


# 规则模型：继承 BaseModel，因此具备 is_deleted 逻辑删除列与 create_by/create_time 等审计列。
class MonitorAlarmRule(BaseModel):
    """监控告警规则表：定义告警触发条件。"""

    # 主键：雪花 ID，由后端生成，不依赖数据库自增
    id = SnowflakeIDField(primary_key=True)
    # 规则名称：列表展示与告警文案中的可读标识
    rule_name = models.CharField('规则名称', max_length=100)
    # 监控类型：决定采集哪类指标（如 service 服务、cpu、memory 等）
    monitor_type = models.CharField('监控类型', max_length=30, default='service')
    # 比较操作符：与 threshold 组合成判定表达式，如 cpu > 80
    compare_op = models.CharField('比较操作符', max_length=10, default='>')
    # 阈值：用字符串存储以兼容数值、百分比、时长等不同量纲；blank/null 表示可留空
    threshold = models.CharField('阈值', max_length=50, blank=True, null=True)
    # 告警级别：整数分级，数值越大越严重（前端据此着色）
    alarm_level = models.SmallIntegerField('告警级别', default=1)
    # 通知渠道：告警触发后走哪种通知方式，默认站内信 site
    channel = models.CharField('通知渠道', max_length=30, default='site')
    # 状态：1=启用、0=停用；停用后该规则不参与判定
    status = models.SmallIntegerField('状态', default=1)
    # 备注：补充说明规则适用范围与维护信息
    remark = models.CharField('备注', max_length=500, blank=True, null=True)

    # 元信息：绑定手工建表 SQL 创建的表名，并声明 Django 不管理该表
    class Meta:
        # 对应数据库中的规则表
        db_table = 'monitor_alarm_rule'
        # managed=False：建表/改表由 docs 的 SQL 负责，ORM 只做读写映射
        managed = False
        # 默认按主键倒序，新建规则排在最前，列表页无需再传排序参数
        ordering = ['-id']


# 记录模型：只继承 models.Model（不是 BaseModel），没有 is_deleted 逻辑删除列，
# 因此记录删除即物理删除，视图层也需重写 get_queryset 去掉逻辑删除过滤。
class MonitorAlarmRecord(models.Model):
    """告警记录表（不继承 BaseModel）：已产生的告警事件。"""

    # 主键：雪花 ID，告警产生即确定唯一编号
    id = SnowflakeIDField(primary_key=True)
    # 规则 ID：记录由哪条规则命中产生；用 BigInteger 而非 ForeignKey，与手工建表 SQL 的无外键设计一致
    rule_id = models.BigIntegerField('规则ID', blank=True, null=True)
    # 告警级别：冗余存触发时的级别，即使规则后续被改也不影响历史记录语义
    alarm_level = models.SmallIntegerField('告警级别', default=1)
    # 告警内容：本次告警的正文描述（指标值、主机、原因等）
    alarm_content = models.CharField('告警内容', max_length=1000, blank=True, null=True)
    # 告警时间：实际触发时刻，由产生告警的一端写入；允许为空以兼容手工补录
    alarm_time = models.DateTimeField('告警时间', blank=True, null=True)
    # 处理状态：0=未处理、1=已处理（确认/处理动作回写此列，构成告警闭环）
    handle_status = models.SmallIntegerField('处理状态', default=0)
    # 处理人 ID：谁确认/处理了这条告警
    handler_id = models.BigIntegerField('处理人ID', blank=True, null=True)
    # 处理时间：处理完成时刻，用于统计响应时长
    handle_time = models.DateTimeField('处理时间', blank=True, null=True)
    # 创建时间：落库时间由 Django 自动填充；auto_now_add 只在首次插入时赋值
    create_time = models.DateTimeField('创建时间', auto_now_add=True)

    # 元信息：绑定手工建表 SQL 创建的表名，并声明 Django 不管理该表
    class Meta:
        # 对应数据库中的告警记录表
        db_table = 'monitor_alarm_record'
        # managed=False：表结构由 SQL 维护，ORM 仅做映射
        managed = False
        # 默认按主键倒序，最新告警在最前面，符合运维查看习惯
        ordering = ['-id']