"""编码规则模块模型。"""
# 模块：apps/sys_no/models.py —— 编码规则（单据编号生成器）的数据模型
# 用途：定义两张表：sys_no_rule 保存编号规则（前缀/日期格式/流水位数/步长/重置策略/状态）；
#       sys_no_log 保存每次取号的流水日志（可追溯谁在何时为何业务生成了什么编号）。
# 建表方式：两张表均由手工 SQL 创建，模型侧 managed=False，Django 不会自动建表或改表。
# 主键约定：统一使用 SnowflakeIDField（雪花算法 64 位整型），避免自增 ID 暴露数据量并支持分布式生成。
# 路由前缀：接口挂在 /sys_no/rule 与 /sys_no/log 下（见 urls.py），生成动作为 POST /sys_no/rule/generate/<pk>。
# 幂等性：模型本身无副作用；generate 动作每次调用都会递增 seq_current 并写一条日志，属于非幂等写操作。
from django.db import models
from common.fields import SnowflakeIDField  # 雪花算法主键字段

from common.utils import BaseModel


# 编码规则主表：一条记录代表一套编号生成规则，业务按 rule_key 区分不同单据类型
class SysNoRule(BaseModel):
    """编码规则表：定义业务编号的生成规则。"""

    # 主键：雪花 ID，保存时由字段生成，保证多实例部署下不冲突
    id = SnowflakeIDField(primary_key=True)
    # 规则编码：业务侧引用的唯一标识（如 order_no、contract_no），唯一索引防止重复规则
    rule_key = models.CharField('规则编码', max_length=100, unique=True)
    # 规则名称：管理端展示用的中文名，便于运营识别该规则对应的单据
    rule_name = models.CharField('规则名称', max_length=100)
    # 编号前缀：拼在编号最前面的固定字符（如 SO、CT），允许为空表示纯日期+流水
    prefix = models.CharField('前缀', max_length=50, blank=True, default='')
    # 日期格式：预留的日期段格式（如 YYYYMMDD），当前生成逻辑硬编码 %Y%m%d，尚未读取该值
    date_format = models.CharField('日期格式', max_length=20, blank=True, default='YYYYMMDD')
    # 流水号长度：流水部分左侧补 0 的总位数，默认 4 位（如 0001）
    seq_length = models.IntegerField('流水号长度', default=4)
    # 当前流水值：上一次已用到的流水号，每次生成按 step 递增后落库
    seq_current = models.IntegerField('当前流水', default=0)
    # 步长：每次生成的流水增量，默认 1，也可用于隔号预留或批量取号
    step = models.IntegerField('步长', default=1)
    # 分隔符：前缀/日期/流水之间的连接符，允许为空表示直接相连
    separator = models.CharField('分隔符', max_length=10, blank=True, default='')
    # 重置方式：流水归零周期（none/year/month/day 等），当前生成逻辑尚未实现按周期重置
    reset_type = models.CharField('重置方式', max_length=20, blank=True, default='none')
    # 重置时间：记录最近一次重置日期，供按周期判断是否归零，当前逻辑未使用
    reset_time = models.DateField('重置时间', blank=True, null=True)
    # 状态：1=启用、0=停用；停用规则业务侧不应再生成编号
    status = models.SmallIntegerField('状态', default=1)
    # 备注：规则用途补充说明，允许为空
    remark = models.CharField('备注', max_length=500, blank=True, null=True)

    # 元信息：绑定手工建表 SQL 的真实表名，并声明 Django 不管理表结构
    class Meta:
        # 表名必须与手工建表 SQL 完全一致，否则 ORM 查不到数据
        db_table = 'sys_no_rule'
        # managed=False：迁移系统不创建/修改该表，结构变更走人工 SQL
        managed = False
        # 默认按主键倒序，新增规则优先展示（视图层 order_by 保持一致）
        ordering = ['-id']


# 编码生成日志表：只追加不修改，用于审计与追溯每一次取号行为
class SysNoLog(models.Model):
    """编码生成日志表（不继承 BaseModel）。"""

    # 主键：雪花 ID，保证并发写入下列日志的唯一性
    id = SnowflakeIDField(primary_key=True)
    # 规则 ID：普通 bigint 保存规则主键，不建数据库外键约束，保持日志表轻量
    rule_id = models.BigIntegerField('规则ID')
    # 生成编号：最终拼接出的完整编号（前缀+分隔符+日期+分隔符+流水）
    no_value = models.CharField('生成编号', max_length=100)
    # 业务类型：编号用于哪类业务（如 order、contract），便于按业务检索日志
    biz_type = models.CharField('业务类型', max_length=50, blank=True, null=True)
    # 业务 ID：编号对应业务记录的主键，便于从日志反查单据
    biz_id = models.BigIntegerField('业务ID', blank=True, null=True)
    # 生成用户 ID：触发取号的操作人主键，未登录或系统任务时为空
    gen_user_id = models.BigIntegerField('生成用户ID', blank=True, null=True)
    # 生成时间：本次取号发生的业务时刻（与入库时间区分）
    gen_time = models.DateTimeField('生成时间', blank=True, null=True)
    # 入库时间：模型自动写入当前时刻，无需业务代码赋值，便于排查写入延迟
    create_time = models.DateTimeField('入库时间', auto_now_add=True)

    # 元信息：日志表同样由手工 SQL 建表，模型仅做映射
    class Meta:
        # 真实表名与手工建表 SQL 一致
        db_table = 'sys_no_log'
        # 不参与迁移管理，避免 Django 生成建表语句覆盖人工结构
        managed = False
        # 按主键倒序，最新生成的编号排在最前
        ordering = ['-id']