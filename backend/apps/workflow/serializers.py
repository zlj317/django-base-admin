"""工作流模块序列化器：统一列表展示字段与详情返回结构。"""
# 模块：apps/workflow/serializers.py —— 工作流审批接口的 DRF 序列化器
# 用途：把 11 张 wf_ 表模型转成前端可用的 JSON，并补充分类名/表单名/处理人/状态中文等展示字段。
# 数据表：wf_category、wf_form、wf_group、wf_group_user、wf_model、wf_instance、wf_task、
#         wf_audit、wf_cc、wf_listener、wf_expression（均由建表 SQL 维护，managed=False）。
# 路由前缀：wf（/api/wf/），本文件的序列化器被 apps/workflow/views.py 的各 ViewSet 引用。
# 关键约定：SerializerMethodField 只读展示、不参与写入；名称缺失时统一回退 '-' 或空串，避免前端出现 None。
# 标准库 json：把 form_data 等 TextField 里的 JSON 文本解析成对象，供前端直接使用
import json  # 解析表单/节点配置 JSON

# DRF 序列化器基类：ModelSerializer 依据模型自动生成字段、类型转换与基础校验
from rest_framework import serializers  # DRF 序列化器基类

# 系统用户/部门模型：用于把用户 ID 翻译成名称，部门用于节点配置的选人下拉
from apps.system.models import SysDept, SysUser  # 用户与部门，用于展示名称
# 11 张工作流表模型：每个模型对应下方一个序列化器，字段与表结构保持一致
from apps.workflow.models import (
    # 建模与留痕相关模型：分类、表单、分组、审批记录、抄送、表达式
    WfAudit, WfCategory, WfCc, WfExpression, WfForm, WfGroup, WfGroupUser,
    # 运行态相关模型：实例、监听器、模型定义、任务
    WfInstance, WfListener, WfModel, WfTask)

# 以下三张映射表是序列化器输出中文名的唯一来源，新增状态码时需同步维护
# 状态字典：前端标签展示与筛选复用同一套文案
INSTANCE_STATUS = {0: '运行中', 1: '已完成', 2: '已驳回', 3: '已终止'}  # 流程实例状态
TASK_STATUS = {0: '待办', 1: '已办', 2: '已转派', 3: '已加签', 4: '已驳回'}  # 任务状态
MODEL_STATUS = {0: '草稿', 1: '已发布', 2: '停用'}  # 模型状态


# 用户名称解析：实例/任务/审批/抄送多处需要 ID→可读名称，抽成公共函数避免重复查询逻辑
def user_name(user_id):
    """按用户 ID 取昵称或账号，缺失时返回空串，避免列表出现 None。"""
    if not user_id:  # 未分配处理人
        return ''  # 返回空串便于前端展示
    user = SysUser.objects.filter(id=user_id).only('username', 'nickname').first()  # 只查必要字段
    if not user:  # 用户已被删除
        return '用户%s' % user_id  # 回退显示原始 ID
    return user.nickname or user.username  # 优先昵称，其次账号


# 分类序列化器：分类数据量小且无敏感字段，直接全字段读写，列表与新增编辑共用
class WfCategorySerializer(serializers.ModelSerializer):
    """流程分类：列表与新增编辑共用。"""

    # 元信息：绑定 WfCategory，全字段输出供分类管理与模型列表筛选复用
    class Meta:
        model = WfCategory  # 绑定分类模型
        fields = '__all__'  # 输出全部字段，前端按需取用


# 表单序列化器：form_json 以字符串原样存取，解析与渲染交给前端表单设计器
class WfFormSerializer(serializers.ModelSerializer):
    """流程表单：form_json 以原始字符串存取，前端自行解析。"""

    # 元信息：绑定 WfForm，全字段输出便于编辑时保留完整 JSON 配置
    class Meta:
        model = WfForm  # 绑定表单模型
        fields = '__all__'  # 输出全部字段


# 分组序列化器：除分组自身字段外，额外挂成员数与成员账号，列表页无需二次请求
class WfGroupSerializer(serializers.ModelSerializer):
    """用户分组：附带成员数量与成员账号，便于列表展示。"""
    user_count = serializers.SerializerMethodField()  # 分组内用户数
    user_names = serializers.SerializerMethodField()  # 分组内用户账号串

    # 元信息：绑定 WfGroup，全字段输出并自动带上两个 SerializerMethodField
    class Meta:
        model = WfGroup  # 绑定分组模型
        fields = '__all__'  # 输出全部字段

    # 成员数量：列表页展示分组规模，实时 count 保证增删成员后立即准确
    def get_user_count(self, obj):
        """统计分组下未删除关联的用户数。"""
        return WfGroupUser.objects.filter(group_id=obj.id).count()  # 关联表按分组过滤

    # 成员账号：前端用标签直接展示，避免再按 ID 逐个查询用户
    def get_user_names(self, obj):
        """返回分组内用户账号列表，前端用标签展示。"""
        ids = list(WfGroupUser.objects.filter(group_id=obj.id).values_list('user_id', flat=True))  # 取出用户 ID
        if not ids:  # 空分组直接返回空数组
            # 提前返回，省掉一次空集合的数据库查询
            return []
        return list(SysUser.objects.filter(id__in=ids).values_list('username', flat=True))  # 转成账号列表


# 模型序列化器：附带分类/表单名称、实例数与状态中文，设计页复用 bpmn_xml 与 node_config
class WfModelSerializer(serializers.ModelSerializer):
    """流程模型：列表附带分类名、表单名与运行实例数。"""
    category_name = serializers.SerializerMethodField()  # 分类名称
    form_name = serializers.SerializerMethodField()  # 绑定表单名称
    instance_count = serializers.SerializerMethodField()  # 已发起实例数
    status_name = serializers.SerializerMethodField()  # 状态中文名

    # 元信息：绑定 WfModel，全字段输出（含 bpmn_xml），模型设计页可直接复用该响应
    class Meta:
        model = WfModel  # 绑定模型
        fields = '__all__'  # 输出全部字段（含 bpmn_xml，设计页复用）

    # 分类名称：模型列表只展示可读名称，未分类或分类被删除时用 '-' 占位
    def get_category_name(self, obj):
        """按分类 ID 取名称。"""
        if not obj.category_id:  # 未分类
            return '-'  # 占位
        row = WfCategory.objects.filter(id=obj.category_id).first()  # 单条查询
        return row.name if row else '-'  # 分类被删除时回退

    # 表单名称：发起前需要展示绑定的业务表单，未绑定或表单被删除时用 '-' 占位
    def get_form_name(self, obj):
        """按表单 ID 取表单名称。"""
        if not obj.form_id:  # 未绑定表单
            return '-'  # 占位
        row = WfForm.objects.filter(id=obj.form_id).first()  # 单条查询
        return row.form_name if row else '-'  # 表单不存在时回退

    # 实例数：列表页据此判断模型是否已被使用，避免删除仍有在途流程的模型
    def get_instance_count(self, obj):
        """统计该模型已发起的未删除实例数。"""
        return WfInstance.objects.filter(model_id=obj.id, is_deleted=0).count()  # 实例计数

    # 状态中文：前端标签直接展示，未知状态码统一兜底为“未知”
    def get_status_name(self, obj):
        """把模型状态码转中文。"""
        return MODEL_STATUS.get(obj.status, '未知')  # 未知码兜底


# 实例序列化器：列表展示模型、发起人、状态与业务摘要，表单对象已解析成 JSON 供详情页使用
class WfInstanceSerializer(serializers.ModelSerializer):
    """流程实例：列表展示模型、发起人、状态与业务摘要。"""
    model_name = serializers.SerializerMethodField()  # 模型名称
    model_key = serializers.SerializerMethodField()  # 模型 Key
    start_user_name = serializers.SerializerMethodField()  # 发起人名称
    status_name = serializers.SerializerMethodField()  # 状态中文
    form_data_obj = serializers.SerializerMethodField()  # 解析后的表单对象

    # 元信息：绑定 WfInstance，全字段输出并自动带上 5 个只读展示字段
    class Meta:
        model = WfInstance  # 绑定实例模型
        fields = '__all__'  # 输出全部字段

    # 模型名称：列表标题展示；模型被删除时用 '-' 占位而不抛异常
    def get_model_name(self, obj):
        """取模型名称，历史实例按版本快照回查同一模型记录。"""
        row = WfModel.objects.filter(id=obj.model_id).first()  # 模型记录
        return row.model_name if row else '-'  # 模型被删除时占位

    # 模型 Key：业务示例页按 key 过滤实例，模型不存在时返回空串保证前端可安全比较
    def get_model_key(self, obj):
        """取模型唯一 Key，用于业务示例页筛选。"""
        row = WfModel.objects.filter(id=obj.model_id).first()  # 模型记录
        return row.model_key if row else ''  # 不存在返回空串

    # 发起人名称：列表/详情都要展示谁发起的，复用统一的用户名称解析
    def get_start_user_name(self, obj):
        """发起人展示名。"""
        return user_name(obj.start_user_id)  # 复用用户名称工具

    # 状态中文：实例列表用标签展示运行中/已完成/已驳回/已终止
    def get_status_name(self, obj):
        """实例状态中文。"""
        return INSTANCE_STATUS.get(obj.status, '未知')  # 未知码兜底

    # 表单对象：前端详情页直接按字段渲染，无需再自行 JSON.parse 字符串
    def get_form_data_obj(self, obj):
        """把 form_data 字符串解析为对象，解析失败返回空对象。"""
        # 历史数据可能为空或非法 JSON，异常时返回空对象，避免整页 500
        try:
            return json.loads(obj.form_data or '{}')  # 正常 JSON
        # 解析失败统一返回空对象，避免脏数据导致接口 500
        except (TypeError, ValueError):
            return {}  # 脏数据不影响列表渲染


# 任务序列化器：待办/已办/全局任务列表共用，跨表补齐实例、模型、发起人与状态信息
class WfTaskSerializer(serializers.ModelSerializer):
    """流程任务：待办/已办/全局任务列表共用，附带实例与人员信息。"""
    assignee_name = serializers.SerializerMethodField()  # 处理人名称
    instance_key = serializers.SerializerMethodField()  # 实例标识
    model_name = serializers.SerializerMethodField()  # 流程模型名称
    start_user_name = serializers.SerializerMethodField()  # 发起人
    status_name = serializers.SerializerMethodField()  # 状态中文
    approve_mode_name = serializers.SerializerMethodField()  # 审批方式中文
    instance_status = serializers.SerializerMethodField()  # 实例状态码

    # 元信息：绑定 WfTask，全字段输出并自动带上 7 个只读展示字段
    class Meta:
        model = WfTask  # 绑定任务模型
        fields = '__all__'  # 输出全部字段

    # 处理人名称：待办列表直接展示姓名，避免前端再查用户表
    def get_assignee_name(self, obj):
        """处理人名称。"""
        return user_name(obj.assignee)  # 复用用户名称工具

    # 实例缓存查询：多个展示字段都依赖实例，抽成私有方法避免重复写查询语句
    def _instance(self, obj):
        """取任务所属实例，供多个方法复用。"""
        return WfInstance.objects.filter(id=obj.instance_id).first()  # 单条查询

    # 实例标识：前端做任务跳转或去重时使用，实例被删除时返回空串
    def get_instance_key(self, obj):
        """实例唯一标识。"""
        row = self._instance(obj)  # 取实例
        return row.instance_key if row else ''  # 不存在返回空串

    # 模型名称：任务列表展示所属流程名称，实例或模型缺失时统一用 '-' 占位
    def get_model_name(self, obj):
        """任务所属流程模型名称。"""
        row = self._instance(obj)  # 取实例
        if not row:  # 实例已删除
            return '-'  # 占位
        model = WfModel.objects.filter(id=row.model_id).first()  # 查模型
        return model.model_name if model else '-'  # 模型不存在时占位

    # 发起人名称：待办列表按发起人区分单据，实例缺失时返回空串
    def get_start_user_name(self, obj):
        """任务所属实例的发起人。"""
        row = self._instance(obj)  # 取实例
        return user_name(row.start_user_id) if row else ''  # 无实例返回空串

    # 任务状态中文：待办/已办列表用标签展示任务生命周期
    def get_status_name(self, obj):
        """任务状态中文。"""
        return TASK_STATUS.get(obj.status, '未知')  # 未知码兜底

    # 审批方式中文：前端据此展示“或签/会签”提示，未知值用 '-' 占位
    def get_approve_mode_name(self, obj):
        """任务审批方式中文。"""
        return {1: '串行', 2: '或签', 3: '会签'}.get(obj.approve_mode, '-')  # 默认占位

    # 实例状态码：前端据此禁用已完成/已终止实例上的审批按钮，实例不存在返回 -1
    def get_instance_status(self, obj):
        """实例状态码，前端据此判断是否允许操作。"""
        row = self._instance(obj)  # 取实例
        return row.status if row else -1  # 实例不存在给 -1


# 审批记录序列化器：把 action 英文码翻成中文，供流程详情页的轨迹时间线渲染
class WfAuditSerializer(serializers.ModelSerializer):
    """审批记录：轨迹时间线展示。"""
    operator_name = serializers.SerializerMethodField()  # 操作人名称
    action_name = serializers.SerializerMethodField()  # 操作中文

    # 元信息：绑定 WfAudit，全字段输出并自动带上操作人/操作类型两个展示字段
    class Meta:
        model = WfAudit  # 绑定审批记录
        fields = '__all__'  # 输出全部字段

    # 操作人名称：轨迹中展示可读姓名，用户被删除时回退为“用户ID”
    def get_operator_name(self, obj):
        """操作人展示名。"""
        return user_name(obj.operator_id)  # 复用工具

    # 操作类型中文：时间线按中文展示，未知动作原样返回英文码便于排查
    def get_action_name(self, obj):
        """操作类型中文映射。"""
        # 操作码→中文映射；未知动作原样返回英文码，便于历史数据排查
        return {'submit': '提交', 'approve': '同意', 'reject': '驳回', 'transfer': '转审',
                'addsign': '加签', 'back': '退回', 'withdraw': '撤回', 'terminate': '终止'}.get(obj.action, obj.action)


# 抄送序列化器：抄送我的列表需要模型名、发起人、实例状态与已读状态
class WfCcSerializer(serializers.ModelSerializer):
    """抄送记录：抄送我的列表。"""
    model_name = serializers.SerializerMethodField()  # 模型名称
    start_user_name = serializers.SerializerMethodField()  # 发起人
    instance_status = serializers.SerializerMethodField()  # 实例状态
    status_name = serializers.SerializerMethodField()  # 已读状态中文

    # 元信息：绑定 WfCc，全字段输出并自动带上模型/发起人/状态/已读四个展示字段
    class Meta:
        model = WfCc  # 绑定抄送记录
        fields = '__all__'  # 输出全部字段

    # 实例查询：多个展示字段共享同一条实例记录，集中在此方法内查询
    def _instance(self, obj):
        """取抄送所属实例。"""
        return WfInstance.objects.filter(id=obj.instance_id).first()  # 单条查询

    # 模型名称：抄送列表展示流程名，实例或模型缺失时用 '-' 占位
    def get_model_name(self, obj):
        """模型名称。"""
        row = self._instance(obj)  # 实例
        if not row:  # 实例不存在
            return '-'  # 占位
        model = WfModel.objects.filter(id=row.model_id).first()  # 查模型
        return model.model_name if model else '-'  # 占位

    # 发起人名称：抄送列表展示单据来源人，实例缺失时返回空串
    def get_start_user_name(self, obj):
        """发起人名称。"""
        row = self._instance(obj)  # 实例
        return user_name(row.start_user_id) if row else ''  # 无实例返回空串

    # 实例状态码：前端据此展示流程是否已结束，实例不存在返回 -1
    def get_instance_status(self, obj):
        """实例状态码。"""
        row = self._instance(obj)  # 实例
        return row.status if row else -1  # 不存在给 -1

    # 已读状态：抄送列表用未读角标提醒用户查看，status 只有 0/1 二值
    def get_status_name(self, obj):
        """抄送已读状态。"""
        return '已读' if obj.status == 1 else '未读'  # 二值状态


# 监听器序列化器：配置页只额外补模型名称，回调参数保持 JSON 字符串原样
class WfListenerSerializer(serializers.ModelSerializer):
    """流程监听器配置。"""
    model_name = serializers.SerializerMethodField()  # 所属模型名称

    # 元信息：绑定 WfListener，全字段输出并自动带上所属模型名称
    class Meta:
        model = WfListener  # 绑定监听器
        fields = '__all__'  # 输出全部字段

    # 模型名称：监听器配置页展示所属流程，模型被删除时用 '-' 占位
    def get_model_name(self, obj):
        """模型名称。"""
        row = WfModel.objects.filter(id=obj.model_id).first()  # 查模型
        return row.model_name if row else '-'  # 占位


# 表达式序列化器：纯配置表，表达式内容由引擎解析，这里只做字段映射不做额外校验
class WfExpressionSerializer(serializers.ModelSerializer):
    """流程表达式配置。"""

    # 元信息：绑定 WfExpression，全字段输出供表达式管理页整体读写
    class Meta:
        model = WfExpression  # 绑定表达式
        fields = '__all__'  # 输出全部字段


# 部门精简序列化器：节点选人只需 id/名称/父级，避免把部门全部字段暴露给前端
class DeptSerializer(serializers.ModelSerializer):
    """部门精简结构，供节点配置选择部门。"""

    # 元信息：绑定 SysDept，仅输出树形选择所需的最小字段集合
    class Meta:
        model = SysDept  # 绑定部门模型
        fields = ['id', 'dept_name', 'parent_id']  # 只输出必要字段
