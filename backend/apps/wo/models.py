"""工单模块模型（表由建表 SQL 手工创建，managed=False）。"""
# 文件：apps/wo/models.py —— 工单模块的 ORM 数据模型定义
# 用途：把工单类型、工单主体、工单流转日志三张手建表映射成 Django 模型，
#       为工单类型维护、工单 CRUD、指派/解决/关闭动作以及"我的工单"筛选提供统一的数据读写入口。
# 对应表：work_order_type（工单类型）、work_order（工单主体）、work_order_log（工单操作日志）。
# 路由前缀：/api/wo/type/、/api/wo/order/、/api/wo/log/，由 apps/wo/urls.py 生成后挂到 config/urls.py。
# 状态流转：work_order.status 0 待处理 →（assign 指派处理人）→（solve 标记）2 已解决 →（close 关闭）3 已关闭，
#           关闭时同步写入 close_time；每次动作由视图层向 work_order_log 追加一条操作记录。
# 关联方式：order_type_id / creator_id / assignee_id 存用户与类型的主键值，attachment_ids 存附件 file_id 串，
#           均不建数据库外键，便于跨模块引用且不干扰手工建表结构。
# 迁移策略：三个模型均 managed=False，表结构由建表 SQL 维护，Django 只负责读写、不生成建表/改表语句。
from django.db import models  # Django ORM 字段与模型基类
from common.fields import SnowflakeIDField  # 雪花算法主键字段

from common.utils import BaseModel  # 公共字段基类：创建/更新人、逻辑删除


# 工单类型模型：维护"设备报修""网络故障"等分类，工单创建时按 order_type_id 引用
class WorkOrderType(BaseModel):
    """工单类型表：定义工单分类。"""
    # 主键：雪花算法在插入时生成 64 位整数，避免依赖数据库自增、也便于分库分表
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    # 类型名称：前端下拉框与列表展示用，100 字符足以覆盖业务分类命名
    type_name = models.CharField('类型名称', max_length=100)  # 工单类型名称
    # 排序值：数值越小越靠前，管理员可通过编辑调整下拉框顺序
    sort = models.IntegerField('排序', default=0)  # 排序值，数值小排前
    # 启停状态：1 表示启用可被新工单选用，0 表示停用但历史工单仍保留该分类
    status = models.SmallIntegerField('状态', default=1)  # 1 启用 / 0 停用
    # 备注：可选补充说明；限制 500 字符，避免长文本误写入类型表
    remark = models.CharField('备注', max_length=500, blank=True, null=True)  # 备注说明

    # 元信息：指定物理表名、托管方式与默认排序规则
    class Meta:
        # 显式声明表名，避免 Django 按 app_label + 类名拼出不存在的默认表名
        db_table = 'work_order_type'  # 对应数据库物理表名
        # 关键配置：表已由外部 SQL 建好，migrate 时既不建表也不改表，避免产生多余 DDL
        managed = False  # 不参与 migrate 的建表/改表
        # 默认排序：先按人工排序值，再按主键兜底，保证同 sort 值下顺序稳定
        ordering = ['sort', 'id']  # 先按 sort 再按 id 升序


# 工单主体模型：一条记录就是一张工单，承载标题、内容、附件、状态、处理人等核心信息
class WorkOrder(BaseModel):
    """工单表：存储工单主体信息。"""
    # 主键：雪花 ID，同时作为前端详情/编辑/流转接口的 pk 参数
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    # 工单编号：业务侧展示与检索用的可读编号（如 WD202611060001），允许为空以兼容历史数据
    order_no = models.CharField('工单编号', max_length=64, blank=True, null=True)  # 自动生成的编号
    # 类型外键值：指向 work_order_type.id；用 BigInteger 存 ID 而不建 FK，避免级联删除影响历史工单
    order_type_id = models.BigIntegerField('工单类型ID', blank=True, null=True)  # 关联 work_order_type
    # 标题：工单摘要，必填且限制 200 字符，列表页展示主要依赖该字段
    title = models.CharField('工单标题', max_length=200)  # 工单标题
    # 内容：问题详细描述，允许较长文本，故使用 TextField 而非 CharField
    content = models.TextField('工单内容', blank=True, null=True)  # 工单详细描述
    # 附件 ID 串：保存 wf_file 的 file_id，多个以逗号分隔；500 字符限制单工单附件数量规模
    attachment_ids = models.CharField('附件ID列表', max_length=500, blank=True, null=True)  # 附件 file_id 列表，逗号分隔
    # 优先级：1 低 / 2 中 / 3 高，默认 2 让新建工单落在常规水平，前端可按此排序或标色
    priority = models.SmallIntegerField('优先级', default=2)  # 1 低 / 2 中 / 3 高
    # 状态：工单生命周期核心字段，由 assign/solve/close 动作修改，新建时默认 0 待处理
    status = models.SmallIntegerField('状态', default=0)  # 0 待处理 / 1 处理中 / 2 已解决 / 3 已关闭
    # 创建人：记录提单用户 ID，用于"我的工单"按 creator_id 过滤，避免只能依赖审计字段 create_by
    creator_id = models.BigIntegerField('创建人ID', blank=True, null=True)  # 创建工单的用户
    # 处理人：由 assign 动作写入的用户 ID，工单列表可按 assignee_id 筛选"我负责的工单"
    assignee_id = models.BigIntegerField('处理人ID', blank=True, null=True)  # 当前处理人
    # 期望完成时间：用于 SLA/超时提醒展示，可为空表示未约定交付时间
    expect_time = models.DateTimeField('期望完成时间', blank=True, null=True)  # 期望交付时间
    # 关闭时间：仅 close 动作写入，用于统计工单从创建到关闭的耗时
    close_time = models.DateTimeField('关闭时间', blank=True, null=True)  # 工单实际关闭时间

    # 元信息：表名、非托管、默认排序
    class Meta:
        # 物理表名与建表 SQL 保持一致，Django 只映射不创建
        db_table = 'work_order'  # 对应数据库物理表名
        # 非托管模型：结构变更需改建表 SQL 并人工执行，避免 migrate 误删业务列
        managed = False  # 不参与 migrate 的建表/改表
        # 按主键倒序：雪花 ID 趋势递增，等价于"最新创建的工单排在最前"
        ordering = ['-id']  # 按主键倒序


# 工单日志模型：记录每次流转动作（assign/solve/close 等），用于详情页时间线与审计追溯
class WorkOrderLog(models.Model):
    """工单日志表（不继承 BaseModel）：记录工单流转与操作痕迹。"""
    # 主键：雪花 ID，日志量增长快，使用趋势递增 ID 使按 id 倒序即按写入顺序倒序
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    # 工单 ID：指向 work_order.id，视图通过 order_id 精确筛选某张工单的全部日志
    order_id = models.BigIntegerField('工单ID')  # 关联 work_order 主键
    # 操作人：执行该动作的用户 ID，可为空以兼容系统自动动作或匿名操作
    operator_id = models.BigIntegerField('操作人ID', blank=True, null=True)  # 执行该操作的用户
    # 动作类型：约定的英文枚举 assign/solve/close，便于前端按动作渲染不同图标与文案
    action = models.CharField('操作动作', max_length=50, blank=True, null=True)  # assign/solve/close 等
    # 备注：动作附带的说明（如指派对象、解决说明），用户可通过请求体 comment 自定义
    comment = models.CharField('操作备注', max_length=1000, blank=True, null=True)  # 备注信息
    # 创建时间：日志写入时刻；本模型不继承 BaseModel，因此只有这一个时间字段
    create_time = models.DateTimeField('创建时间', blank=True, null=True)  # 入库时间

    # 元信息：表名、非托管、默认排序
    class Meta:
        # 物理表名与建表 SQL 对齐，日志表由外部脚本维护
        db_table = 'work_order_log'  # 对应数据库物理表名
        # 非托管：migrate 不会为日志表生成任何建表/改表操作
        managed = False  # 不参与 migrate 的建表/改表
        # 倒序排列：最新动作排在最前，前端时间线直接按接口顺序渲染即可
        ordering = ['-id']  # 最新日志在前