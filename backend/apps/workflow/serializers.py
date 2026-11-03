"""工作流模块序列化器：统一列表展示字段与详情返回结构。"""
import json  # 解析表单/节点配置 JSON

from rest_framework import serializers  # DRF 序列化器基类

from apps.system.models import SysDept, SysUser  # 用户与部门，用于展示名称
from apps.workflow.models import (
    WfAudit, WfCategory, WfCc, WfExpression, WfForm, WfGroup, WfGroupUser,
    WfInstance, WfListener, WfModel, WfTask)

# 状态字典：前端标签展示与筛选复用同一套文案
INSTANCE_STATUS = {0: '运行中', 1: '已完成', 2: '已驳回', 3: '已终止'}  # 流程实例状态
TASK_STATUS = {0: '待办', 1: '已办', 2: '已转派', 3: '已加签', 4: '已驳回'}  # 任务状态
MODEL_STATUS = {0: '草稿', 1: '已发布', 2: '停用'}  # 模型状态


def user_name(user_id):
    """按用户 ID 取昵称或账号，缺失时返回空串，避免列表出现 None。"""
    if not user_id:  # 未分配处理人
        return ''  # 返回空串便于前端展示
    user = SysUser.objects.filter(id=user_id).only('username', 'nickname').first()  # 只查必要字段
    if not user:  # 用户已被删除
        return '用户%s' % user_id  # 回退显示原始 ID
    return user.nickname or user.username  # 优先昵称，其次账号


class WfCategorySerializer(serializers.ModelSerializer):
    """流程分类：列表与新增编辑共用。"""

    class Meta:
        model = WfCategory  # 绑定分类模型
        fields = '__all__'  # 输出全部字段，前端按需取用


class WfFormSerializer(serializers.ModelSerializer):
    """流程表单：form_json 以原始字符串存取，前端自行解析。"""

    class Meta:
        model = WfForm  # 绑定表单模型
        fields = '__all__'  # 输出全部字段


class WfGroupSerializer(serializers.ModelSerializer):
    """用户分组：附带成员数量与成员账号，便于列表展示。"""
    user_count = serializers.SerializerMethodField()  # 分组内用户数
    user_names = serializers.SerializerMethodField()  # 分组内用户账号串

    class Meta:
        model = WfGroup  # 绑定分组模型
        fields = '__all__'  # 输出全部字段

    def get_user_count(self, obj):
        """统计分组下未删除关联的用户数。"""
        return WfGroupUser.objects.filter(group_id=obj.id).count()  # 关联表按分组过滤

    def get_user_names(self, obj):
        """返回分组内用户账号列表，前端用标签展示。"""
        ids = list(WfGroupUser.objects.filter(group_id=obj.id).values_list('user_id', flat=True))  # 取出用户 ID
        if not ids:  # 空分组直接返回空数组
            return []
        return list(SysUser.objects.filter(id__in=ids).values_list('username', flat=True))  # 转成账号列表


class WfModelSerializer(serializers.ModelSerializer):
    """流程模型：列表附带分类名、表单名与运行实例数。"""
    category_name = serializers.SerializerMethodField()  # 分类名称
    form_name = serializers.SerializerMethodField()  # 绑定表单名称
    instance_count = serializers.SerializerMethodField()  # 已发起实例数
    status_name = serializers.SerializerMethodField()  # 状态中文名

    class Meta:
        model = WfModel  # 绑定模型
        fields = '__all__'  # 输出全部字段（含 bpmn_xml，设计页复用）

    def get_category_name(self, obj):
        """按分类 ID 取名称。"""
        if not obj.category_id:  # 未分类
            return '-'  # 占位
        row = WfCategory.objects.filter(id=obj.category_id).first()  # 单条查询
        return row.name if row else '-'  # 分类被删除时回退

    def get_form_name(self, obj):
        """按表单 ID 取表单名称。"""
        if not obj.form_id:  # 未绑定表单
            return '-'  # 占位
        row = WfForm.objects.filter(id=obj.form_id).first()  # 单条查询
        return row.form_name if row else '-'  # 表单不存在时回退

    def get_instance_count(self, obj):
        """统计该模型已发起的未删除实例数。"""
        return WfInstance.objects.filter(model_id=obj.id, is_deleted=0).count()  # 实例计数

    def get_status_name(self, obj):
        """把模型状态码转中文。"""
        return MODEL_STATUS.get(obj.status, '未知')  # 未知码兜底


class WfInstanceSerializer(serializers.ModelSerializer):
    """流程实例：列表展示模型、发起人、状态与业务摘要。"""
    model_name = serializers.SerializerMethodField()  # 模型名称
    model_key = serializers.SerializerMethodField()  # 模型 Key
    start_user_name = serializers.SerializerMethodField()  # 发起人名称
    status_name = serializers.SerializerMethodField()  # 状态中文
    form_data_obj = serializers.SerializerMethodField()  # 解析后的表单对象

    class Meta:
        model = WfInstance  # 绑定实例模型
        fields = '__all__'  # 输出全部字段

    def get_model_name(self, obj):
        """取模型名称，历史实例按版本快照回查同一模型记录。"""
        row = WfModel.objects.filter(id=obj.model_id).first()  # 模型记录
        return row.model_name if row else '-'  # 模型被删除时占位

    def get_model_key(self, obj):
        """取模型唯一 Key，用于业务示例页筛选。"""
        row = WfModel.objects.filter(id=obj.model_id).first()  # 模型记录
        return row.model_key if row else ''  # 不存在返回空串

    def get_start_user_name(self, obj):
        """发起人展示名。"""
        return user_name(obj.start_user_id)  # 复用用户名称工具

    def get_status_name(self, obj):
        """实例状态中文。"""
        return INSTANCE_STATUS.get(obj.status, '未知')  # 未知码兜底

    def get_form_data_obj(self, obj):
        """把 form_data 字符串解析为对象，解析失败返回空对象。"""
        try:
            return json.loads(obj.form_data or '{}')  # 正常 JSON
        except (TypeError, ValueError):
            return {}  # 脏数据不影响列表渲染


class WfTaskSerializer(serializers.ModelSerializer):
    """流程任务：待办/已办/全局任务列表共用，附带实例与人员信息。"""
    assignee_name = serializers.SerializerMethodField()  # 处理人名称
    instance_key = serializers.SerializerMethodField()  # 实例标识
    model_name = serializers.SerializerMethodField()  # 流程模型名称
    start_user_name = serializers.SerializerMethodField()  # 发起人
    status_name = serializers.SerializerMethodField()  # 状态中文
    approve_mode_name = serializers.SerializerMethodField()  # 审批方式中文
    instance_status = serializers.SerializerMethodField()  # 实例状态码

    class Meta:
        model = WfTask  # 绑定任务模型
        fields = '__all__'  # 输出全部字段

    def get_assignee_name(self, obj):
        """处理人名称。"""
        return user_name(obj.assignee)  # 复用用户名称工具

    def _instance(self, obj):
        """取任务所属实例，供多个方法复用。"""
        return WfInstance.objects.filter(id=obj.instance_id).first()  # 单条查询

    def get_instance_key(self, obj):
        """实例唯一标识。"""
        row = self._instance(obj)  # 取实例
        return row.instance_key if row else ''  # 不存在返回空串

    def get_model_name(self, obj):
        """任务所属流程模型名称。"""
        row = self._instance(obj)  # 取实例
        if not row:  # 实例已删除
            return '-'  # 占位
        model = WfModel.objects.filter(id=row.model_id).first()  # 查模型
        return model.model_name if model else '-'  # 模型不存在时占位

    def get_start_user_name(self, obj):
        """任务所属实例的发起人。"""
        row = self._instance(obj)  # 取实例
        return user_name(row.start_user_id) if row else ''  # 无实例返回空串

    def get_status_name(self, obj):
        """任务状态中文。"""
        return TASK_STATUS.get(obj.status, '未知')  # 未知码兜底

    def get_approve_mode_name(self, obj):
        """任务审批方式中文。"""
        return {1: '串行', 2: '或签', 3: '会签'}.get(obj.approve_mode, '-')  # 默认占位

    def get_instance_status(self, obj):
        """实例状态码，前端据此判断是否允许操作。"""
        row = self._instance(obj)  # 取实例
        return row.status if row else -1  # 实例不存在给 -1


class WfAuditSerializer(serializers.ModelSerializer):
    """审批记录：轨迹时间线展示。"""
    operator_name = serializers.SerializerMethodField()  # 操作人名称
    action_name = serializers.SerializerMethodField()  # 操作中文

    class Meta:
        model = WfAudit  # 绑定审批记录
        fields = '__all__'  # 输出全部字段

    def get_operator_name(self, obj):
        """操作人展示名。"""
        return user_name(obj.operator_id)  # 复用工具

    def get_action_name(self, obj):
        """操作类型中文映射。"""
        return {'submit': '提交', 'approve': '同意', 'reject': '驳回', 'transfer': '转审',
                'addsign': '加签', 'back': '退回', 'withdraw': '撤回', 'terminate': '终止'}.get(obj.action, obj.action)


class WfCcSerializer(serializers.ModelSerializer):
    """抄送记录：抄送我的列表。"""
    model_name = serializers.SerializerMethodField()  # 模型名称
    start_user_name = serializers.SerializerMethodField()  # 发起人
    instance_status = serializers.SerializerMethodField()  # 实例状态
    status_name = serializers.SerializerMethodField()  # 已读状态中文

    class Meta:
        model = WfCc  # 绑定抄送记录
        fields = '__all__'  # 输出全部字段

    def _instance(self, obj):
        """取抄送所属实例。"""
        return WfInstance.objects.filter(id=obj.instance_id).first()  # 单条查询

    def get_model_name(self, obj):
        """模型名称。"""
        row = self._instance(obj)  # 实例
        if not row:  # 实例不存在
            return '-'  # 占位
        model = WfModel.objects.filter(id=row.model_id).first()  # 查模型
        return model.model_name if model else '-'  # 占位

    def get_start_user_name(self, obj):
        """发起人名称。"""
        row = self._instance(obj)  # 实例
        return user_name(row.start_user_id) if row else ''  # 无实例返回空串

    def get_instance_status(self, obj):
        """实例状态码。"""
        row = self._instance(obj)  # 实例
        return row.status if row else -1  # 不存在给 -1

    def get_status_name(self, obj):
        """抄送已读状态。"""
        return '已读' if obj.status == 1 else '未读'  # 二值状态


class WfListenerSerializer(serializers.ModelSerializer):
    """流程监听器配置。"""
    model_name = serializers.SerializerMethodField()  # 所属模型名称

    class Meta:
        model = WfListener  # 绑定监听器
        fields = '__all__'  # 输出全部字段

    def get_model_name(self, obj):
        """模型名称。"""
        row = WfModel.objects.filter(id=obj.model_id).first()  # 查模型
        return row.model_name if row else '-'  # 占位


class WfExpressionSerializer(serializers.ModelSerializer):
    """流程表达式配置。"""

    class Meta:
        model = WfExpression  # 绑定表达式
        fields = '__all__'  # 输出全部字段


class DeptSerializer(serializers.ModelSerializer):
    """部门精简结构，供节点配置选择部门。"""

    class Meta:
        model = SysDept  # 绑定部门模型
        fields = ['id', 'dept_name', 'parent_id']  # 只输出必要字段
