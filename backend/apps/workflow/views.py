"""工作流模块视图：流程配置 CRUD、流程实例、审批任务与抄送。"""
import json  # 表单配置与表单数据解析
import time  # 生成业务单据号与路径时间戳
import uuid  # 生成流程实例唯一标识

from django.db import IntegrityError, transaction  # 事务保证审批与引擎流转原子性
from rest_framework import viewsets  # DRF 视图集基类

from apps.system.models import SysDept, SysRole, SysUser  # 节点配置可选的人员/角色/部门
from apps.workflow import engine  # BPMN 审批引擎
from apps.workflow.models import (
    WfAudit, WfCategory, WfCc, WfExpression, WfForm, WfGroup, WfGroupUser,
    WfInstance, WfListener, WfModel, WfTask)
from apps.workflow.serializers import (
    WfAuditSerializer, WfCategorySerializer, WfCcSerializer, WfExpressionSerializer,
    WfFormSerializer, WfGroupSerializer, WfInstanceSerializer, WfListenerSerializer,
    WfModelSerializer, WfTaskSerializer)
from common.auth import LoginRequired  # 登录校验（节点配置下拉只需要登录）
from common.pagination import StandardPagination  # 统一分页输出
from common.permissions import PermissionCheck, get_user_perms  # 权限标识校验 + 超管识别
from common.response import fail, ok  # 统一响应包装
from common.views import CrudViewSet  # 通用 CRUD 基类


def parse_json(text, default):
    """把数据库中的 JSON 文本解析为对象，失败时返回默认值。"""
    try:
        return json.loads(text) if text else default  # 空值直接返回默认值
    except (TypeError, ValueError):
        return default  # 脏数据不影响接口返回


class WfCategoryViewSet(CrudViewSet):
    """流程分类：标准增删改查。"""
    model = WfCategory  # 绑定分类模型
    serializer_class = WfCategorySerializer  # 序列化器
    perm_prefix = 'wf:category'  # 权限前缀
    module_name = '流程分类'  # 操作日志模块名
    filter_map = {'name': 'icontains', 'code': 'icontains', 'status': 'exact'}  # 支持的筛选字段


class WfFormViewSet(CrudViewSet):
    """流程表单：表单配置的增删改查。"""
    model = WfForm  # 绑定表单模型
    serializer_class = WfFormSerializer  # 序列化器
    perm_prefix = 'wf:form'  # 权限前缀
    module_name = '流程表单'  # 操作日志模块名
    filter_map = {'form_name': 'icontains', 'form_key': 'icontains', 'status': 'exact'}  # 筛选字段

    @property  # 属性方法：DRF 访问时动态生成当前视图的权限映射
    def permission_classes(self):
        """补充表单详情动作的权限映射。"""
        self.perm_map = {
            'list': 'wf:form:list', 'create': 'wf:form:create',
            'update': 'wf:form:update', 'delete': 'wf:form:delete',
            'form_detail': 'wf:form:list',
        }
        return [PermissionCheck]

    def form_detail(self, request, pk=None):
        """返回表单配置详情，form_json 解析为数组供设计器直接使用。"""
        row = self.get_queryset().filter(id=pk).first()  # 未删除记录
        if not row:  # 不存在
            return fail('表单不存在', code=404)
        data = WfFormSerializer(row).data  # 基础字段
        data['form_json_obj'] = parse_json(row.form_json, [])  # 解析后的字段数组
        return ok(data)


class WfGroupViewSet(CrudViewSet):
    """用户分组：分组维护与成员设置。"""
    model = WfGroup  # 绑定分组模型
    serializer_class = WfGroupSerializer  # 序列化器
    perm_prefix = 'wf:group'  # 权限前缀
    module_name = '用户分组'  # 操作日志模块名
    filter_map = {'group_name': 'icontains', 'group_code': 'icontains', 'status': 'exact'}  # 筛选字段

    @property  # 属性方法：把成员相关自定义动作也纳入权限校验
    def permission_classes(self):
        """补充成员查询与设置动作的权限映射。"""
        self.perm_map = {
            'list': 'wf:group:list', 'create': 'wf:group:create',
            'update': 'wf:group:update', 'delete': 'wf:group:delete',
            'users': 'wf:group:list', 'set_users': 'wf:group:update',
        }
        return [PermissionCheck]

    def users(self, request, pk=None):
        """查询分组内用户列表。"""
        group = self.get_queryset().filter(id=pk).first()  # 分组
        if not group:  # 分组不存在
            return fail('分组不存在', code=404)
        user_ids = list(WfGroupUser.objects.filter(group_id=group.id).values_list('user_id', flat=True))  # 成员 ID
        users = SysUser.objects.filter(id__in=user_ids).values('id', 'username', 'nickname')  # 成员信息
        return ok({'group_id': group.id, 'user_ids': user_ids, 'users': list(users)})

    def set_users(self, request, pk=None):
        """覆盖式保存分组成员：先清空再写入提交的用户。"""
        group = self.get_queryset().filter(id=pk).first()  # 分组
        if not group:  # 分组不存在
            return fail('分组不存在', code=404)
        user_ids = [int(x) for x in (request.data.get('user_ids') or []) if str(x).isdigit()]  # 过滤合法 ID
        WfGroupUser.objects.filter(group_id=group.id).delete()  # 覆盖式更新
        now = time.strftime('%Y-%m-%d %H:%M:%S')  # 统一写入时间
        for uid in set(user_ids):  # 去重写入
            WfGroupUser.objects.create(group_id=group.id, user_id=uid, create_time=now)
        return ok({'user_ids': user_ids}, '成员保存成功')


class WfModelViewSet(CrudViewSet):
    """流程模型：设计、保存、发布、停用与复制。"""
    model = WfModel  # 绑定模型
    serializer_class = WfModelSerializer  # 序列化器
    perm_prefix = 'wf:model'  # 权限前缀
    module_name = '流程模型'  # 操作日志模块名
    filter_map = {'model_name': 'icontains', 'model_key': 'icontains',
                  'category_id': 'exact', 'status': 'exact'}  # 筛选字段

    @property  # 属性方法：把设计器相关自定义动作也纳入权限校验
    def permission_classes(self):
        """补充设计/发布/复制/停用/下拉动作的权限映射。"""
        self.perm_map = {
            'list': 'wf:model:list', 'create': 'wf:model:create',
            'update': 'wf:model:update', 'delete': 'wf:model:delete',
            'design': 'wf:model:list', 'save': 'wf:model:update',
            'publish': 'wf:model:publish', 'disable': 'wf:model:update',
            'copy': 'wf:model:create', 'options': 'wf:model:list',
        }
        return [PermissionCheck]

    def create(self, request):
        """新增模型：校验模型 Key 唯一，并给出友好提示。"""
        try:
            return super().create(request)  # 复用通用新增逻辑
        except IntegrityError:  # 唯一键冲突
            return fail('模型 Key 已存在，请更换')

    def design(self, request, pk=None):
        """返回模型设计数据：BPMN XML 与节点配置。"""
        row = self.get_queryset().filter(id=pk).first()  # 模型
        if not row:  # 不存在
            return fail('模型不存在', code=404)
        return ok({
            'id': row.id, 'model_name': row.model_name, 'model_key': row.model_key,
            'status': row.status, 'version': row.version,
            'bpmn_xml': row.bpmn_xml or '',  # 流程定义
            'node_config': parse_json(row.node_config, {}),  # 节点审批人配置
        })

    def save(self, request):
        """保存设计结果：更新 BPMN XML 与节点配置。"""
        pk = request.data.get('id')  # 模型 ID
        row = self.get_queryset().filter(id=pk).first()  # 模型
        if not row:  # 不存在
            return fail('模型不存在', code=404)
        xml = request.data.get('bpmn_xml') or ''  # 流程定义
        try:
            engine.ProcessGraph(xml)  # 保存前先解析，提前暴露错误 XML
        except engine.EngineError as exc:  # 解析失败
            return fail(str(exc))
        node_config = request.data.get('node_config') or {}  # 节点配置
        row.bpmn_xml = xml  # 写入 XML
        row.node_config = json.dumps(node_config, ensure_ascii=False)  # 写入配置
        row.update_by = request.user_info.username  # 更新人
        row.update_time = time.strftime('%Y-%m-%d %H:%M:%S')  # 更新时间
        row.save(update_fields=['bpmn_xml', 'node_config', 'update_by', 'update_time'])  # 只更新必要字段
        return ok({'id': row.id}, '设计保存成功')

    def publish(self, request, pk=None):
        """发布模型：校验流程可解析，版本号 +1 并置为已发布。"""
        row = self.get_queryset().filter(id=pk).first()  # 模型
        if not row:  # 不存在
            return fail('模型不存在', code=404)
        try:
            engine.ProcessGraph(row.bpmn_xml)  # 校验 BPMN
        except engine.EngineError as exc:
            return fail(str(exc))
        if not row.form_id:  # 未绑定表单
            return fail('请先为流程绑定表单再发布')
        row.version = (row.version or 0) + 1  # 版本递增，实现版本隔离
        row.status = 1  # 已发布
        row.update_by = request.user_info.username  # 更新人
        row.update_time = time.strftime('%Y-%m-%d %H:%M:%S')  # 更新时间
        row.save(update_fields=['version', 'status', 'update_by', 'update_time'])  # 持久化
        return ok({'id': row.id, 'version': row.version}, '发布成功')

    def disable(self, request, pk=None):
        """停用模型：已运行实例不受影响，新发起将不可选择。"""
        row = self.get_queryset().filter(id=pk).first()  # 模型
        if not row:  # 不存在
            return fail('模型不存在', code=404)
        row.status = 2  # 停用
        row.update_by = request.user_info.username  # 更新人
        row.update_time = time.strftime('%Y-%m-%d %H:%M:%S')  # 更新时间
        row.save(update_fields=['status', 'update_by', 'update_time'])  # 持久化
        return ok(None, '已停用')

    def copy(self, request, pk=None):
        """复制模型：生成草稿副本，便于快速改版。"""
        row = self.get_queryset().filter(id=pk).first()  # 原模型
        if not row:  # 不存在
            return fail('模型不存在', code=404)
        new_key = '%s_copy_%s' % (row.model_key, time.strftime('%H%M%S'))  # 新 Key 带时间戳避免冲突
        now = time.strftime('%Y-%m-%d %H:%M:%S')  # 当前时间
        new_row = WfModel.objects.create(
            model_name='%s 副本' % row.model_name, model_key=new_key,
            category_id=row.category_id, form_id=row.form_id, bpmn_xml=row.bpmn_xml,
            node_config=row.node_config, version=0, status=0, process_status=0,
            remark='由 %s 复制' % row.model_name, create_by=request.user_info.username,
            create_time=now, update_by=request.user_info.username, update_time=now, is_deleted=0)
        return ok({'id': new_row.id}, '复制成功')

    def options(self, request):
        """返回已发布且启用的模型，供发起流程页选择。"""
        rows = self.get_queryset().filter(status=1)  # 已发布模型
        data = [{'id': r.id, 'model_name': r.model_name, 'model_key': r.model_key,
                 'form_id': r.form_id, 'category_id': r.category_id} for r in rows]  # 精简字段
        return ok(data)


class WfListenerViewSet(CrudViewSet):
    """流程监听器配置。"""
    model = WfListener  # 绑定监听器
    serializer_class = WfListenerSerializer  # 序列化器
    perm_prefix = 'wf:listener'  # 权限前缀
    module_name = '流程监听器'  # 操作日志模块名
    filter_map = {'model_id': 'exact', 'event_type': 'exact',
                  'action_type': 'exact', 'status': 'exact'}  # 筛选字段


class WfExpressionViewSet(CrudViewSet):
    """流程表达式配置。"""
    model = WfExpression  # 绑定表达式
    serializer_class = WfExpressionSerializer  # 序列化器
    perm_prefix = 'wf:expression'  # 权限前缀
    module_name = '流程表达式'  # 操作日志模块名
    filter_map = {'expr_name': 'icontains', 'expr_code': 'icontains',
                  'expr_type': 'exact'}  # 筛选字段
    order_by = 'id'  # 编号升序


class WfInstanceViewSet(viewsets.ViewSet):
    """流程实例：发起、我的流程、全局监控、轨迹、终止与撤回。"""
    permission_classes = [PermissionCheck]  # 统一权限校验

    @property  # 属性方法：实例相关动作到权限标识的动态映射
    def perm_map(self):
        """接口动作到权限标识的映射。"""
        return {
            'list': 'wf:instance:list', 'my': 'wf:instance:my', 'start': 'wf:start:create',
            'detail_info': '', 'trace': '',  # 详情/轨迹对已登录业务用户开放（发起人、审批人需查看）
            'terminate': 'wf:instance:terminate', 'withdraw': 'wf:instance:withdraw',
        }

    def get_queryset(self):
        """未删除实例集合，按最新发起倒序。"""
        return WfInstance.objects.filter(is_deleted=0).order_by('-id')

    def _serialize(self, row):
        """实例序列化。"""
        return WfInstanceSerializer(row).data

    def list(self, request):
        """全局实例列表（管理员监控）。"""
        qs = self.get_queryset()  # 基础集合
        for key, lookup in (('model_id', 'exact'), ('status', 'exact'),
                            ('start_user_id', 'exact'), ('biz_key', 'icontains')):
            value = request.query_params.get(key)  # 取查询参数
            if value not in (None, ''):  # 非空才过滤
                qs = qs.filter(**{key + '__' + lookup: value})
        return StandardPagination(request).paginate(qs, WfInstanceSerializer)  # 分页输出

    def my(self, request):
        """我发起的流程实例列表。"""
        qs = self.get_queryset().filter(start_user_id=request.user_info.id)  # 只取本人发起
        status = request.query_params.get('status')  # 状态筛选
        if status not in (None, ''):  # 非空
            qs = qs.filter(status=status)
        return StandardPagination(request).paginate(qs, WfInstanceSerializer)

    def _load_model(self, row):
        """取实例对应的流程模型。"""
        return WfModel.objects.filter(id=row.model_id).first()

    def _detail_data(self, request, row):
        """组装实例详情：模型、表单、表单数据、审批记录与任务。"""
        model = self._load_model(row)  # 模型
        form = WfForm.objects.filter(id=model.form_id).first() if model and model.form_id else None  # 表单
        audits = WfAudit.objects.filter(instance_id=row.id).order_by('id')  # 审批轨迹
        tasks = WfTask.objects.filter(instance_id=row.id, is_deleted=0).order_by('id')  # 任务列表
        pending_mine = tasks.filter(assignee=request.user_info.id, status=0).exists()  # 当前用户是否有待办
        return {
            'instance': self._serialize(row),  # 实例字段
            'model': {'id': model.id, 'model_name': model.model_name, 'model_key': model.model_key,
                      'bpmn_xml': model.bpmn_xml or '', 'form_id': model.form_id,
                      'node_config': parse_json(model.node_config, {})} if model else None,
            'form': {'id': form.id, 'form_name': form.form_name,
                     'form_json': parse_json(form.form_json, [])} if form else None,
            'form_data': parse_json(row.form_data, {}),  # 表单数据对象
            'audits': WfAuditSerializer(audits, many=True).data,  # 轨迹
            'tasks': WfTaskSerializer(tasks, many=True).data,  # 任务
            'canApprove': pending_mine,  # 是否可操作
        }

    def detail_info(self, request, pk=None):
        """实例详情。"""
        row = self.get_queryset().filter(id=pk).first()  # 实例
        if not row:  # 不存在
            return fail('流程实例不存在', code=404)
        return ok(self._detail_data(request, row))

    def trace(self, request, pk=None):
        """流程轨迹：审批记录 + 任务 + 当前节点。"""
        row = self.get_queryset().filter(id=pk).first()  # 实例
        if not row:  # 不存在
            return fail('流程实例不存在', code=404)
        audits = WfAudit.objects.filter(instance_id=row.id).order_by('id')  # 轨迹
        return ok({
            'instance': self._serialize(row),
            'audits': WfAuditSerializer(audits, many=True).data,
            'tasks': WfTaskSerializer(WfTask.objects.filter(instance_id=row.id, is_deleted=0), many=True).data,
        })

    def start(self, request):
        """发起流程：校验表单必填项，创建实例并启动引擎。"""
        model_id = request.data.get('model_id')  # 模型 ID
        model = WfModel.objects.filter(id=model_id, is_deleted=0).first()  # 模型
        if not model:  # 不存在
            return fail('流程模型不存在')
        if model.status != 1:  # 未发布不可发起
            return fail('该流程尚未发布，无法发起')
        form_data = request.data.get('form_data') or {}  # 表单数据
        if isinstance(form_data, str):  # 兼容 JSON 字符串
            form_data = parse_json(form_data, {})
        form = WfForm.objects.filter(id=model.form_id).first() if model.form_id else None  # 绑定表单
        if form:  # 必填项服务端校验
            fields = parse_json(form.form_json, [])  # 字段数组
            missing = [f.get('label') or f.get('key') for f in fields
                       if f.get('required') and (
                           form_data.get(f.get('key')) is None
                           or str(form_data.get(f.get('key'))).strip() == '')]  # 缺失项
            if missing:  # 有必填未填
                return fail('请填写必填项：%s' % '、'.join(missing))
        now = time.strftime('%Y-%m-%d %H:%M:%S')  # 当前时间
        biz_key = request.data.get('biz_key') or '%s%s' % (
            (model.model_key or 'WF').upper(), time.strftime('%Y%m%d%H%M%S'))  # 业务单据号
        instance = WfInstance.objects.create(
            instance_key=uuid.uuid4().hex, model_id=model.id, model_version=model.version or 1,
            biz_key=biz_key, form_data=json.dumps(form_data, ensure_ascii=False),
            start_user_id=request.user_info.id, status=0, current_node=None,
            start_time=now, create_by=request.user_info.username, create_time=now,
            update_by=request.user_info.username, update_time=now, is_deleted=0)  # 创建实例
        engine_obj = engine.WorkflowEngine(instance, model)  # 构造引擎
        engine_obj.record(request.user_info.id, 'submit', '提交申请', None, None, '发起流程')  # 提交记录
        try:
            engine_obj.start()  # 启动并生成首个待办
        except engine.EngineError as exc:  # 流程定义问题
            WfAudit.objects.filter(instance_id=instance.id).delete()  # 清理提交记录
            WfTask.objects.filter(instance_id=instance.id).delete()  # 清理可能生成的待办
            instance.delete()  # 删除实例，避免留下孤儿数据
            return fail(str(exc))
        return ok({'id': instance.id, 'biz_key': biz_key}, '发起成功')

    def terminate(self, request, pk=None):
        """管理员强制终止运行中的实例。"""
        row = self.get_queryset().filter(id=pk).first()  # 实例
        if not row:  # 不存在
            return fail('流程实例不存在', code=404)
        if row.status != 0:  # 已结束不可终止
            return fail('流程已结束，无需终止')
        model = self._load_model(row)  # 模型
        engine.terminate_instance(row, model, request.user_info.id,
                                  request.data.get('comment') or '管理员终止')  # 终止处理
        return ok(None, '已终止')

    def withdraw(self, request, pk=None):
        """发起人撤回：仅本人且无人审批时可用。"""
        row = self.get_queryset().filter(id=pk).first()  # 实例
        if not row:  # 不存在
            return fail('流程实例不存在', code=404)
        if row.start_user_id != request.user_info.id:  # 非本人发起
            return fail('只能撤回自己发起的流程', code=403)
        if row.status != 0:  # 已结束
            return fail('流程已结束，无法撤回')
        try:
            engine.withdraw_instance(row, request.user_info.id,
                                     request.data.get('comment') or '发起人撤回')  # 撤回处理
        except engine.EngineError as exc:  # 已有审批
            return fail(str(exc))
        return ok(None, '撤回成功')


class WfTaskViewSet(viewsets.ViewSet):
    """流程任务：待办/已办/全局任务与审批动作。"""
    permission_classes = [PermissionCheck]  # 统一权限校验

    @property  # 属性方法：任务相关动作到权限标识的动态映射
    def perm_map(self):
        """接口动作到权限标识的映射。"""
        return {
            'todo': 'wf:task:todo', 'done': 'wf:task:done', 'list': 'wf:task:list',
            'approve': 'wf:task:approve', 'reject': 'wf:task:reject',
            'transfer': 'wf:task:transfer', 'addsign': 'wf:task:addsign',
            'back': 'wf:task:back',
        }

    def _filters(self, qs, request):
        """按实例、状态、处理人筛选任务列表。"""
        for key in ('status', 'assignee', 'instance_id'):
            value = request.query_params.get(key)  # 查询参数
            if value not in (None, ''):  # 非空
                qs = qs.filter(**{key: value})
        return qs

    def todo(self, request):
        """我的待办：仅当前处理人且状态待办。"""
        qs = WfTask.objects.filter(assignee=request.user_info.id, status=0, is_deleted=0).order_by('-id')  # 待办
        return StandardPagination(request).paginate(qs, WfTaskSerializer)

    def done(self, request):
        """我的已办：当前用户处理过的任务（含转派/驳回）。"""
        qs = WfTask.objects.filter(assignee=request.user_info.id,
                                   status__in=[1, 2, 3, 4], is_deleted=0).order_by('-id')  # 已处理
        return StandardPagination(request).paginate(qs, WfTaskSerializer)

    def list(self, request):
        """全局任务监控。"""
        qs = self._filters(WfTask.objects.filter(is_deleted=0).order_by('-id'), request)  # 全量任务
        return StandardPagination(request).paginate(qs, WfTaskSerializer)

    def _task(self, request, pk):
        """取任务并校验归属人，防止越权处理他人待办。"""
        with transaction.atomic():  # 行锁事务，避免并发重复审批
            task = WfTask.objects.select_for_update().filter(id=pk, is_deleted=0).first()  # 锁定任务
            if not task:  # 不存在
                return None, fail('任务不存在', code=404)
            if task.assignee != request.user_info.id:  # 非本人任务
                perms = get_user_perms(request.user_info)  # 当前用户权限集合
                if '*:*:*' not in perms:  # 超管可代为处理/转派，其余用户越权
                    return None, fail('只能处理分配给自己的任务', code=403)
            instance = WfInstance.objects.select_for_update().filter(id=task.instance_id).first()  # 锁定实例
            if not instance:  # 实例不存在
                return None, fail('流程实例不存在', code=404)
            if instance.status != 0:  # 实例已结束
                return None, fail('流程已结束，无法操作')
            model = WfModel.objects.filter(id=instance.model_id).first()  # 模型
            if not model:  # 模型已删除
                return None, fail('流程模型不存在')
            return (task, instance, model), None  # 三元组供动作复用

    def approve(self, request, pk=None):
        """同意任务。"""
        with transaction.atomic():  # 审批写库与引擎流转同事务
            loaded, error = self._task(request, pk)  # 取任务
            if error:
                return error
            task, instance, model = loaded  # 解包
            comment = request.data.get('comment') or ''  # 审批意见
            engine.approve_task(instance, model, task, request.user_info.id, comment)  # 引擎推进
            return ok({'instance_status': instance.status}, '审批通过')

    def reject(self, request, pk=None):
        """驳回任务。"""
        with transaction.atomic():  # 保持事务一致性
            loaded, error = self._task(request, pk)  # 取任务
            if error:
                return error
            task, instance, model = loaded  # 解包
            comment = request.data.get('comment') or ''  # 驳回意见
            if not comment:  # 驳回必须填写理由
                return fail('请填写驳回意见')
            engine.reject_task(instance, model, task, request.user_info.id, comment)  # 驳回处理
            return ok(None, '已驳回')

    def transfer(self, request, pk=None):
        """转审给其他用户。"""
        with transaction.atomic():  # 保持事务一致性
            loaded, error = self._task(request, pk)  # 取任务
            if error:
                return error
            task, instance, model = loaded  # 解包
            target = request.data.get('user_id')  # 目标用户
            if not target:  # 未选择
                return fail('请选择转审人')
            if int(target) == request.user_info.id:  # 不能转给自己
                return fail('不能转审给自己')
            if not SysUser.objects.filter(id=target, status=0, is_deleted=0).exists():  # 目标无效
                return fail('转审人不存在或已停用')
            engine.transfer_task(instance, model, task, request.user_info.id, target,
                                 request.data.get('comment') or '')  # 转审处理
            return ok(None, '转审成功')

    def addsign(self, request, pk=None):
        """加签其他用户，节点转为会签。"""
        with transaction.atomic():  # 保持事务一致性
            loaded, error = self._task(request, pk)  # 取任务
            if error:
                return error
            task, instance, model = loaded  # 解包
            target = request.data.get('user_id')  # 加签人
            if not target:  # 未选择
                return fail('请选择加签人')
            if int(target) == request.user_info.id:  # 不能加签自己
                return fail('不能加签给自己')
            if not SysUser.objects.filter(id=target, status=0, is_deleted=0).exists():  # 目标无效
                return fail('加签人不存在或已停用')
            engine.addsign_task(instance, model, task, request.user_info.id, target,
                                request.data.get('comment') or '')  # 加签处理
            return ok(None, '加签成功')

    def back(self, request, pk=None):
        """退回上一步。"""
        with transaction.atomic():  # 保持事务一致性
            loaded, error = self._task(request, pk)  # 取任务
            if error:
                return error
            task, instance, model = loaded  # 解包
            try:
                engine.back_task(instance, model, task, request.user_info.id,
                                 request.data.get('comment') or '')  # 回退处理
            except engine.EngineError as exc:  # 无可退回节点
                return fail(str(exc))
            return ok(None, '已退回上一步')


class WfCcViewSet(viewsets.ViewSet):
    """抄送：抄送我的列表与标记已读。"""
    permission_classes = [PermissionCheck]  # 统一权限校验

    @property  # 属性方法：抄送相关动作复用同一查询权限
    def perm_map(self):
        """接口动作到权限标识的映射。"""
        return {'mine': 'wf:cc:mine', 'read': 'wf:cc:mine'}

    def mine(self, request):
        """抄送我的列表。"""
        qs = WfCc.objects.filter(user_id=request.user_info.id).order_by('-id')  # 当前用户抄送
        return StandardPagination(request).paginate(qs, WfCcSerializer)

    def read(self, request, pk=None):
        """标记抄送为已读。"""
        row = WfCc.objects.filter(id=pk, user_id=request.user_info.id).first()  # 本人抄送
        if not row:  # 不存在
            return fail('抄送记录不存在', code=404)
        row.status = 1  # 已读
        row.save(update_fields=['status'])
        return ok(None, '已读')


class OptionViewSet(viewsets.ViewSet):
    """节点配置下拉数据：用户、角色、部门、分组与表达式。"""
    permission_classes = [LoginRequired]  # 仅要求登录，配置人员均可读取

    def users(self, request):
        """启用用户列表。"""
        rows = SysUser.objects.filter(status=0, is_deleted=0).order_by('id')  # 有效账号
        return ok([{'id': r.id, 'username': r.username, 'nickname': r.nickname,
                    'dept_id': r.dept_id} for r in rows])

    def roles(self, request):
        """启用角色列表。"""
        rows = SysRole.objects.filter(status=0, is_deleted=0).order_by('role_sort', 'id')  # 有效角色
        return ok([{'id': r.id, 'role_name': r.role_name, 'role_key': r.role_key} for r in rows])

    def depts(self, request):
        """部门列表。"""
        rows = SysDept.objects.filter(is_deleted=0).order_by('order_num', 'id')  # 有效部门
        return ok([{'id': r.id, 'dept_name': r.dept_name, 'parent_id': r.parent_id} for r in rows])

    def groups(self, request):
        """启用分组列表。"""
        rows = WfGroup.objects.filter(status=0, is_deleted=0).order_by('id')  # 有效分组
        return ok([{'id': r.id, 'group_name': r.group_name, 'group_code': r.group_code} for r in rows])
