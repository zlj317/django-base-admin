"""工作流（审批）模块模型：11 张 wf_ 表（表结构由 docs 建表 SQL 手工创建，managed=False）。"""
# 模块：apps/workflow/models.py —— 工作流（审批）模块的 11 张 wf_ 表 ORM 映射
# 用途：覆盖流程建模（分类/表单/分组/模型）、运行态（实例/任务）、留痕（审批/抄送）与扩展配置（监听器/表达式）。
# 数据表：wf_category、wf_form、wf_group、wf_group_user、wf_model、wf_instance、wf_task、
#         wf_audit、wf_cc、wf_listener、wf_expression，共 11 张。
# 路由前缀：wf（即 /api/wf/，见 apps/workflow/urls.py，视图在 apps/workflow/views.py）。
# 关键约定：全部表由 docs 建表 SQL 手工创建，managed=False 不参与 migrate；审计/逻辑删除字段由 BaseModel 统一提供。
# 依赖导入：ORM 字段类型来自 django.db.models；雪花主键与公共基类来自 common 包
from django.db import models  # Django ORM 字段与模型基类
# 雪花算法主键：11 张表统一使用 64 位趋势递增 ID，避免自增主键暴露数据量并便于分库
from common.fields import SnowflakeIDField  # 雪花算法主键字段

# 公共基类：create_by/create_time/update_by/update_time/is_deleted 五个审计列由 BaseModel 自带
from common.utils import BaseModel  # 公共字段基类：创建/更新人、逻辑删除


# 流程分类：流程模型的一级归类，模型列表按分类筛选，sort 决定展示顺序
class WfCategory(BaseModel):
    """流程分类表：对流程模型做分组归类（OA审批、财务审批等）。"""

    # 主键与业务字段：code 唯一用于接口传参，status 控制分类是否可选
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    name = models.CharField('分类名称', max_length=100)  # 分类显示名称
    code = models.CharField('分类编码', max_length=64, unique=True)  # 唯一编码，供接口与数据关联
    sort = models.IntegerField('排序号', default=0)  # 越小越靠前
    status = models.SmallIntegerField('状态', default=1)  # 0 停用 / 1 启用（与需求文档保持一致）
    remark = models.CharField('备注', max_length=255, blank=True, null=True)  # 备注说明

    # 元信息：固定物理表 wf_category，禁止 migrate 改表，分类按 sort/id 升序输出
    class Meta:
        """指定真实表名；表由 SQL 手工维护，故不参与迁移。"""
        db_table = 'wf_category'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['sort', 'id']  # 默认按排序号、主键升序


# 流程表单：form_json 存字段、组件与校验规则，发起页和详情页由前端按它渲染
class WfForm(BaseModel):
    """流程表单表：自定义业务表单配置，form_json 存放字段与校验规则。"""

    # 主键与标识：form_key 全表唯一，供流程模型按业务场景引用同一套表单
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    form_name = models.CharField('表单名称', max_length=100)  # 表单名称
    form_key = models.CharField('表单标识', max_length=64, unique=True)  # 唯一标识
    form_json = models.TextField('表单配置JSON', blank=True, null=True)  # 字段、组件、校验规则
    status = models.SmallIntegerField('状态', default=0)  # 0 启用 / 1 停用
    remark = models.CharField('备注', max_length=255, blank=True, null=True)  # 备注说明

    # 元信息：固定物理表 wf_form，不参与迁移，按编号升序返回表单
    class Meta:
        """指定真实表名；表由 SQL 手工维护，故不参与迁移。"""
        db_table = 'wf_form'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['id']  # 编号升序


# 用户分组：固定审批小组，流程节点选人时可直接选择整个分组
class WfGroup(BaseModel):
    """用户分组表：固定审批小组，流程节点选人时可直接选择分组。"""

    # 主键与标识：group_code 全表唯一，便于节点配置保存分组编码而非易变的主键
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    group_name = models.CharField('分组名称', max_length=100)  # 分组名称
    group_code = models.CharField('分组编码', max_length=64, unique=True)  # 唯一编码
    status = models.SmallIntegerField('状态', default=0)  # 0 启用 / 1 停用
    remark = models.CharField('备注', max_length=255, blank=True, null=True)  # 备注说明

    # 元信息：固定物理表 wf_group，不参与迁移，按编号升序返回分组
    class Meta:
        """指定真实表名；表由 SQL 手工维护，故不参与迁移。"""
        db_table = 'wf_group'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['id']  # 编号升序


# 分组用户关联：一个分组可挂多个用户，选人时按组批量指定审批人
class WfGroupUser(models.Model):
    """用户分组关联表：一个分组包含多个系统用户（不继承公共字段）。"""

    # 只保留关系字段：无审计列，移除组成员即物理删除关联记录
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    group_id = models.BigIntegerField('分组ID')  # 关联 wf_group.id
    user_id = models.BigIntegerField('用户ID')  # 关联 sys_user.id
    create_time = models.DateTimeField('创建时间', blank=True, null=True)  # 加入时间

    # 元信息：固定物理表 wf_group_user，不参与迁移，按插入顺序返回成员关系
    class Meta:
        """指定真实表名；表由 SQL 手工维护，故不参与迁移。"""
        db_table = 'wf_group_user'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['id']  # 编号升序


# 流程模型：bpmn_xml 描述流转，node_config 描述审批人/会签/抄送，version 用于实例快照
class WfModel(BaseModel):
    """流程模型表：保存 BPMN XML 与节点配置，发布后按版本运行。"""

    # 主键与命名：model_key 供引擎识别流程定义，避免依赖可修改的展示名称
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    model_name = models.CharField('模型名称', max_length=100)  # 流程名称（请假流程等）
    model_key = models.CharField('模型Key', max_length=64, unique=True)  # 引擎识别用唯一 Key
    # 归属配置：分类用于列表筛选，表单用于发起页渲染，二者均可为空（未归类/无表单）
    category_id = models.BigIntegerField('分类ID', blank=True, null=True)  # 关联 wf_category.id
    form_id = models.BigIntegerField('表单ID', blank=True, null=True)  # 关联 wf_form.id
    # 流程定义：bpmn_xml 来自 bpmn-js 设计器，node_config 补充引擎外的审批人/会签/抄送参数
    bpmn_xml = models.TextField('BPMN XML', blank=True, null=True)  # bpmn-js 导出的流程定义
    node_config = models.TextField('节点配置JSON', blank=True, null=True)  # 各节点审批人/会签/抄送配置
    # 发布与状态：version 每次发布 +1 供实例锁定快照，status 控制草稿/发布/停用
    version = models.IntegerField('版本号', default=0)  # 每次发布 +1
    status = models.SmallIntegerField('状态', default=0)  # 0 草稿 / 1 已发布 / 2 停用
    process_status = models.SmallIntegerField('流程状态', default=0)  # 0 运行中 / 1 完成 / 2 驳回 / 3 终止
    remark = models.CharField('备注', max_length=255, blank=True, null=True)  # 备注说明

    # 元信息：固定物理表 wf_model，不参与迁移，按编号升序返回模型列表
    class Meta:
        """指定真实表名；表由 SQL 手工维护，故不参与迁移。"""
        db_table = 'wf_model'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['id']  # 编号升序


# 流程实例：一次发起对应一条记录，锁定模型版本并保存表单数据与引擎运行态
class WfInstance(BaseModel):
    """流程实例表：一次流程发起对应一条记录，锁定模型版本。"""

    # 主键与标识：instance_key 全表唯一，对外暴露实例时无需暴露雪花主键
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    instance_key = models.CharField('实例标识', max_length=64, unique=True)  # 引擎 token/uuid
    # 模型快照：model_id 指向定义，model_version 固定发起时的版本避免后续改版影响在途流程
    model_id = models.BigIntegerField('模型ID')  # 关联 wf_model.id
    model_version = models.IntegerField('模型版本快照', default=1)  # 发起时的模型版本
    # 业务关联：biz_key 对应请假单号等外部单据，form_data 保存发起时提交的完整表单 JSON
    biz_key = models.CharField('业务单据号', max_length=64, blank=True, null=True)  # 请假单号等
    form_data = models.TextField('表单数据JSON', blank=True, null=True)  # 发起时提交的业务数据
    start_user_id = models.BigIntegerField('发起人ID')  # 发起用户
    # 生命周期：status/current_node 由引擎推进，start_time/end_time 记录起止时刻
    status = models.SmallIntegerField('状态', default=0)  # 0 运行中 / 1 已完成 / 2 已驳回 / 3 已终止
    current_node = models.CharField('当前节点', max_length=200, blank=True, null=True)  # 当前节点ID
    start_time = models.DateTimeField('发起时间', blank=True, null=True)  # 发起时间
    end_time = models.DateTimeField('结束时间', blank=True, null=True)  # 结束时间
    # 引擎上下文：engine_state 记录网关到达情况与串行队列，会签/并行网关恢复时依赖它
    engine_state = models.TextField('引擎状态JSON', blank=True, null=True)  # 网关到达记录、串行队列

    # 元信息：固定物理表 wf_instance，不参与迁移，按主键倒序让最新发起排在最前
    class Meta:
        """指定真实表名；表由 SQL 手工维护，故不参与迁移。"""
        db_table = 'wf_instance'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['-id']  # 最新发起的实例排在前面


# 流程任务：userTask 生成的人工待办，一条任务对应一个节点上的一名处理人
class WfTask(BaseModel):
    """流程任务表：userTask 生成的人工待办任务。"""

    # 主键与归属：instance_id 定位实例，task_key 对应 BPMN 的 userTask id
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    instance_id = models.BigIntegerField('实例ID')  # 关联 wf_instance.id
    task_key = models.CharField('任务节点ID', max_length=64)  # BPMN userTask id
    task_name = models.CharField('任务名称', max_length=100, blank=True, null=True)  # 节点显示名称
    # 处理人：assignee 指向具体用户，candidate_group_id 支持按分组候选认领
    assignee = models.BigIntegerField('处理人ID', blank=True, null=True)  # 当前处理人
    candidate_group_id = models.BigIntegerField('候选分组ID', blank=True, null=True)  # 关联 wf_group.id
    # 任务状态：status 记录待办/已办/转派/加签/驳回，approve_mode 决定串行/或签/会签
    status = models.SmallIntegerField('状态', default=0)  # 0 待办 / 1 已办 / 2 已转派 / 3 已加签 / 4 已驳回
    approve_mode = models.SmallIntegerField('审批方式', default=2)  # 1 串行 / 2 或签 / 3 会签
    # 调度信息：priority 影响待办排序，due_time 供超时监听扫描
    priority = models.IntegerField('优先级', default=0)  # 数值越大越优先
    due_time = models.DateTimeField('到期时间', blank=True, null=True)  # 超时监听依据
    start_time = models.DateTimeField('生成时间', blank=True, null=True)  # 任务生成时间
    end_time = models.DateTimeField('完成时间', blank=True, null=True)  # 任务完成时间

    # 元信息：固定物理表 wf_task，不参与迁移，按编号升序保证待办顺序稳定
    class Meta:
        """指定真实表名；表由 SQL 手工维护，故不参与迁移。"""
        db_table = 'wf_task'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['id']  # 编号升序


# 审批记录：提交/同意/驳回等操作全量留痕，按 id 升序即可还原流程轨迹
class WfAudit(models.Model):
    """审批记录表：全流程操作留痕（提交/同意/驳回/转审/加签/退回）。"""

    # 主键与归属：instance_id 定位流程，task_id 指向具体任务（提交等动作可为空）
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    instance_id = models.BigIntegerField('实例ID')  # 关联 wf_instance.id
    task_id = models.BigIntegerField('任务ID', blank=True, null=True)  # 关联 wf_task.id
    operator_id = models.BigIntegerField('操作人ID', blank=True, null=True)  # 操作人用户
    action = models.CharField('操作类型', max_length=20, blank=True, null=True)  # submit/approve/reject...
    comment = models.CharField('审批意见', max_length=500, blank=True, null=True)  # 审批意见
    node_id = models.CharField('节点ID', max_length=64, blank=True, null=True)  # 操作所在节点
    node_name = models.CharField('节点名称', max_length=100, blank=True, null=True)  # 节点显示名称
    create_time = models.DateTimeField('操作时间', blank=True, null=True)  # 操作发生时间

    # 元信息：固定物理表 wf_audit，不参与迁移，按主键升序呈现操作时间线
    class Meta:
        """指定真实表名；表由 SQL 手工维护，故不参与迁移。"""
        db_table = 'wf_audit'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['id']  # 按操作先后顺序输出轨迹


# 抄送记录：只读通知，接收人可在“抄送我的”列表查看并标记已读
class WfCc(models.Model):
    """抄送记录表：流程抄送给业务用户，仅可查看不可审批。"""

    # 主键与归属：instance_id 定位流程，user_id 为接收抄送的用户
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    instance_id = models.BigIntegerField('实例ID')  # 关联 wf_instance.id
    user_id = models.BigIntegerField('抄送用户ID')  # 接收抄送的用户
    node_id = models.CharField('来源节点', max_length=64, blank=True, null=True)  # 抄送来源节点
    status = models.SmallIntegerField('状态', default=0)  # 0 未读 / 1 已读
    create_time = models.DateTimeField('创建时间', blank=True, null=True)  # 抄送时间

    # 元信息：固定物理表 wf_cc，不参与迁移，按主键倒序让最新抄送在前
    class Meta:
        """指定真实表名；表由 SQL 手工维护，故不参与迁移。"""
        db_table = 'wf_cc'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['-id']  # 最新抄送在前


# 流程监听器：按事件类型触发回调/通知/改数据/写日志，model_id 限定生效流程
class WfListener(BaseModel):
    """流程监听器表：节点/流程事件触发回调、通知、改数据或写日志。"""

    # 主键与归属：model_id 指定监听哪个流程模型，避免监听器全局误触发
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    model_id = models.BigIntegerField('模型ID')  # 关联 wf_model.id
    event_type = models.CharField('事件类型', max_length=30)  # start/enter/complete/end/reject
    action_type = models.CharField('动作类型', max_length=30)  # callback/notify/update_data/log
    callback_url = models.CharField('回调地址', max_length=255, blank=True, null=True)  # 回调接口
    callback_param = models.TextField('回调参数JSON', blank=True, null=True)  # 附加参数
    status = models.SmallIntegerField('状态', default=0)  # 0 启用 / 1 停用

    # 元信息：固定物理表 wf_listener，不参与迁移，按编号升序返回配置
    class Meta:
        """指定真实表名；表由 SQL 手工维护，故不参与迁移。"""
        db_table = 'wf_listener'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['id']  # 编号升序


# 流程表达式：网关条件与动态审批人计算，expr_type 区分 condition/assignee
class WfExpression(BaseModel):
    """流程表达式表：网关条件与动态审批人计算表达式。"""

    # 主键与标识：expr_code 全表唯一，节点配置按编码引用表达式，改内容不影响引用方
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    expr_name = models.CharField('表达式名称', max_length=100)  # 表达式名称
    expr_code = models.CharField('表达式编码', max_length=64, unique=True)  # 唯一编码
    expr_content = models.CharField('表达式内容', max_length=500, blank=True, null=True)  # ${form.leaveDays > 3}
    expr_type = models.CharField('表达式类型', max_length=30, default='condition')  # condition/assignee
    remark = models.CharField('备注', max_length=255, blank=True, null=True)  # 备注说明

    # 元信息：固定物理表 wf_expression，不参与迁移，按编号升序返回表达式
    class Meta:
        """指定真实表名；表由 SQL 手工维护，故不参与迁移。"""
        db_table = 'wf_expression'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['id']  # 编号升序