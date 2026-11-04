"""工作流（审批）模块模型：11 张 wf_ 表（表结构由 docs 建表 SQL 手工创建，managed=False）。"""
from django.db import models  # Django ORM 字段与模型基类
from common.fields import SnowflakeIDField  # 雪花算法主键字段

from common.utils import BaseModel  # 公共字段基类：创建/更新人、逻辑删除


class WfCategory(BaseModel):
    """流程分类表：对流程模型做分组归类（OA审批、财务审批等）。"""
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    name = models.CharField('分类名称', max_length=100)  # 分类显示名称
    code = models.CharField('分类编码', max_length=64, unique=True)  # 唯一编码，供接口与数据关联
    sort = models.IntegerField('排序号', default=0)  # 越小越靠前
    status = models.SmallIntegerField('状态', default=1)  # 0 停用 / 1 启用（与需求文档保持一致）
    remark = models.CharField('备注', max_length=255, blank=True, null=True)  # 备注说明

    class Meta:
        """指定真实表名；表由 SQL 手工维护，故不参与迁移。"""
        db_table = 'wf_category'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['sort', 'id']  # 默认按排序号、主键升序


class WfForm(BaseModel):
    """流程表单表：自定义业务表单配置，form_json 存放字段与校验规则。"""
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    form_name = models.CharField('表单名称', max_length=100)  # 表单名称
    form_key = models.CharField('表单标识', max_length=64, unique=True)  # 唯一标识
    form_json = models.TextField('表单配置JSON', blank=True, null=True)  # 字段、组件、校验规则
    status = models.SmallIntegerField('状态', default=0)  # 0 启用 / 1 停用
    remark = models.CharField('备注', max_length=255, blank=True, null=True)  # 备注说明

    class Meta:
        """指定真实表名；表由 SQL 手工维护，故不参与迁移。"""
        db_table = 'wf_form'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['id']  # 编号升序


class WfGroup(BaseModel):
    """用户分组表：固定审批小组，流程节点选人时可直接选择分组。"""
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    group_name = models.CharField('分组名称', max_length=100)  # 分组名称
    group_code = models.CharField('分组编码', max_length=64, unique=True)  # 唯一编码
    status = models.SmallIntegerField('状态', default=0)  # 0 启用 / 1 停用
    remark = models.CharField('备注', max_length=255, blank=True, null=True)  # 备注说明

    class Meta:
        """指定真实表名；表由 SQL 手工维护，故不参与迁移。"""
        db_table = 'wf_group'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['id']  # 编号升序


class WfGroupUser(models.Model):
    """用户分组关联表：一个分组包含多个系统用户（不继承公共字段）。"""
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    group_id = models.BigIntegerField('分组ID')  # 关联 wf_group.id
    user_id = models.BigIntegerField('用户ID')  # 关联 sys_user.id
    create_time = models.DateTimeField('创建时间', blank=True, null=True)  # 加入时间

    class Meta:
        """指定真实表名；表由 SQL 手工维护，故不参与迁移。"""
        db_table = 'wf_group_user'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['id']  # 编号升序


class WfModel(BaseModel):
    """流程模型表：保存 BPMN XML 与节点配置，发布后按版本运行。"""
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    model_name = models.CharField('模型名称', max_length=100)  # 流程名称（请假流程等）
    model_key = models.CharField('模型Key', max_length=64, unique=True)  # 引擎识别用唯一 Key
    category_id = models.BigIntegerField('分类ID', blank=True, null=True)  # 关联 wf_category.id
    form_id = models.BigIntegerField('表单ID', blank=True, null=True)  # 关联 wf_form.id
    bpmn_xml = models.TextField('BPMN XML', blank=True, null=True)  # bpmn-js 导出的流程定义
    node_config = models.TextField('节点配置JSON', blank=True, null=True)  # 各节点审批人/会签/抄送配置
    version = models.IntegerField('版本号', default=0)  # 每次发布 +1
    status = models.SmallIntegerField('状态', default=0)  # 0 草稿 / 1 已发布 / 2 停用
    process_status = models.SmallIntegerField('流程状态', default=0)  # 0 运行中 / 1 完成 / 2 驳回 / 3 终止
    remark = models.CharField('备注', max_length=255, blank=True, null=True)  # 备注说明

    class Meta:
        """指定真实表名；表由 SQL 手工维护，故不参与迁移。"""
        db_table = 'wf_model'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['id']  # 编号升序


class WfInstance(BaseModel):
    """流程实例表：一次流程发起对应一条记录，锁定模型版本。"""
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    instance_key = models.CharField('实例标识', max_length=64, unique=True)  # 引擎 token/uuid
    model_id = models.BigIntegerField('模型ID')  # 关联 wf_model.id
    model_version = models.IntegerField('模型版本快照', default=1)  # 发起时的模型版本
    biz_key = models.CharField('业务单据号', max_length=64, blank=True, null=True)  # 请假单号等
    form_data = models.TextField('表单数据JSON', blank=True, null=True)  # 发起时提交的业务数据
    start_user_id = models.BigIntegerField('发起人ID')  # 发起用户
    status = models.SmallIntegerField('状态', default=0)  # 0 运行中 / 1 已完成 / 2 已驳回 / 3 已终止
    current_node = models.CharField('当前节点', max_length=200, blank=True, null=True)  # 当前节点ID
    start_time = models.DateTimeField('发起时间', blank=True, null=True)  # 发起时间
    end_time = models.DateTimeField('结束时间', blank=True, null=True)  # 结束时间
    engine_state = models.TextField('引擎状态JSON', blank=True, null=True)  # 网关到达记录、串行队列

    class Meta:
        """指定真实表名；表由 SQL 手工维护，故不参与迁移。"""
        db_table = 'wf_instance'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['-id']  # 最新发起的实例排在前面


class WfTask(BaseModel):
    """流程任务表：userTask 生成的人工待办任务。"""
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    instance_id = models.BigIntegerField('实例ID')  # 关联 wf_instance.id
    task_key = models.CharField('任务节点ID', max_length=64)  # BPMN userTask id
    task_name = models.CharField('任务名称', max_length=100, blank=True, null=True)  # 节点显示名称
    assignee = models.BigIntegerField('处理人ID', blank=True, null=True)  # 当前处理人
    candidate_group_id = models.BigIntegerField('候选分组ID', blank=True, null=True)  # 关联 wf_group.id
    status = models.SmallIntegerField('状态', default=0)  # 0 待办 / 1 已办 / 2 已转派 / 3 已加签 / 4 已驳回
    approve_mode = models.SmallIntegerField('审批方式', default=2)  # 1 串行 / 2 或签 / 3 会签
    priority = models.IntegerField('优先级', default=0)  # 数值越大越优先
    due_time = models.DateTimeField('到期时间', blank=True, null=True)  # 超时监听依据
    start_time = models.DateTimeField('生成时间', blank=True, null=True)  # 任务生成时间
    end_time = models.DateTimeField('完成时间', blank=True, null=True)  # 任务完成时间

    class Meta:
        """指定真实表名；表由 SQL 手工维护，故不参与迁移。"""
        db_table = 'wf_task'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['id']  # 编号升序


class WfAudit(models.Model):
    """审批记录表：全流程操作留痕（提交/同意/驳回/转审/加签/退回）。"""
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    instance_id = models.BigIntegerField('实例ID')  # 关联 wf_instance.id
    task_id = models.BigIntegerField('任务ID', blank=True, null=True)  # 关联 wf_task.id
    operator_id = models.BigIntegerField('操作人ID', blank=True, null=True)  # 操作人用户
    action = models.CharField('操作类型', max_length=20, blank=True, null=True)  # submit/approve/reject...
    comment = models.CharField('审批意见', max_length=500, blank=True, null=True)  # 审批意见
    node_id = models.CharField('节点ID', max_length=64, blank=True, null=True)  # 操作所在节点
    node_name = models.CharField('节点名称', max_length=100, blank=True, null=True)  # 节点显示名称
    create_time = models.DateTimeField('操作时间', blank=True, null=True)  # 操作发生时间

    class Meta:
        """指定真实表名；表由 SQL 手工维护，故不参与迁移。"""
        db_table = 'wf_audit'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['id']  # 按操作先后顺序输出轨迹


class WfCc(models.Model):
    """抄送记录表：流程抄送给业务用户，仅可查看不可审批。"""
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    instance_id = models.BigIntegerField('实例ID')  # 关联 wf_instance.id
    user_id = models.BigIntegerField('抄送用户ID')  # 接收抄送的用户
    node_id = models.CharField('来源节点', max_length=64, blank=True, null=True)  # 抄送来源节点
    status = models.SmallIntegerField('状态', default=0)  # 0 未读 / 1 已读
    create_time = models.DateTimeField('创建时间', blank=True, null=True)  # 抄送时间

    class Meta:
        """指定真实表名；表由 SQL 手工维护，故不参与迁移。"""
        db_table = 'wf_cc'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['-id']  # 最新抄送在前


class WfListener(BaseModel):
    """流程监听器表：节点/流程事件触发回调、通知、改数据或写日志。"""
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    model_id = models.BigIntegerField('模型ID')  # 关联 wf_model.id
    event_type = models.CharField('事件类型', max_length=30)  # start/enter/complete/end/reject
    action_type = models.CharField('动作类型', max_length=30)  # callback/notify/update_data/log
    callback_url = models.CharField('回调地址', max_length=255, blank=True, null=True)  # 回调接口
    callback_param = models.TextField('回调参数JSON', blank=True, null=True)  # 附加参数
    status = models.SmallIntegerField('状态', default=0)  # 0 启用 / 1 停用

    class Meta:
        """指定真实表名；表由 SQL 手工维护，故不参与迁移。"""
        db_table = 'wf_listener'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['id']  # 编号升序


class WfExpression(BaseModel):
    """流程表达式表：网关条件与动态审批人计算表达式。"""
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    expr_name = models.CharField('表达式名称', max_length=100)  # 表达式名称
    expr_code = models.CharField('表达式编码', max_length=64, unique=True)  # 唯一编码
    expr_content = models.CharField('表达式内容', max_length=500, blank=True, null=True)  # ${form.leaveDays > 3}
    expr_type = models.CharField('表达式类型', max_length=30, default='condition')  # condition/assignee
    remark = models.CharField('备注', max_length=255, blank=True, null=True)  # 备注说明

    class Meta:
        """指定真实表名；表由 SQL 手工维护，故不参与迁移。"""
        db_table = 'wf_expression'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['id']  # 编号升序