# 模块：apps/workflow/views.py —— 工作流（审批）模块的视图层（DRF ViewSet）
# 用途：流程配置（分类/表单/分组/模型/监听器/表达式）CRUD、流程实例（发起/我的/详情/轨迹/终止/撤回）、
#       流程任务（待办/已办/审批/驳回/转审/加签/退回）、抄送与节点配置下拉数据。
# 路由前缀：wf（即 /api/wf/，路由见 apps/workflow/urls.py，所有路径不带结尾斜杠）。
# 权限：配置类视图集通过 perm_prefix + PermissionCheck 校验；运行态视图集在 perm_map 中显式映射动作到权限标识。
# 与 engine.py 的关系：本文件只做参数校验、事务与响应封装；节点流转、会签、网关等推进逻辑全部委托给 engine.py。
"""工作流模块视图：流程配置 CRUD、流程实例、审批任务与抄送。"""
import json  # 表单配置与表单数据解析
import time  # 生成业务单据号与路径时间戳
import uuid  # 生成流程实例唯一标识

from django.db import IntegrityError, transaction  # 事务保证审批与引擎流转原子性
from rest_framework import viewsets  # DRF 视图集基类

from apps.system.models import SysDept, SysRole, SysUser  # 节点配置可选的人员/角色/部门
from apps.workflow import engine  # BPMN 审批引擎
# 模型导入：覆盖配置态（分类/表单/分组/模型/监听器/表达式）与运行态（实例/任务/审批/抄送）全部表
from apps.workflow.models import (
    # 按业务板块换行导入，便于新增模型时快速核对是否遗漏
    WfAudit, WfCategory, WfCc, WfExpression, WfForm, WfGroup, WfGroupUser,
    # 运行态与扩展配置：实例/任务驱动流转，监听器/表达式供引擎扩展使用
    WfInstance, WfListener, WfModel, WfTask)
# 序列化器导入：与模型一一对应，负责字典化输出与字段校验
from apps.workflow.serializers import (
    # 配置与留痕类序列化器
    WfAuditSerializer, WfCategorySerializer, WfCcSerializer, WfExpressionSerializer,
    # 表单/分组/实例/监听器序列化器
    WfFormSerializer, WfGroupSerializer, WfInstanceSerializer, WfListenerSerializer,
    # 模型与任务序列化器：列表与详情接口统一复用
    WfModelSerializer, WfTaskSerializer)
from common.auth import LoginRequired  # 登录校验（节点配置下拉只需要登录）
from common.pagination import StandardPagination  # 统一分页输出
from common.permissions import PermissionCheck, get_user_perms  # 权限标识校验 + 超管识别
from common.response import fail, ok  # 统一响应包装
from common.views import CrudViewSet  # 通用 CRUD 基类


# 工具函数：把数据库 TextField 里的 JSON 文本解析为 Python 对象，失败时返回默认值
def parse_json(text, default):
    # 接口多处读取 JSON 字段，统一走此函数，避免单个脏数据导致 500
    """把数据库中的 JSON 文本解析为对象，失败时返回默认值。"""
    # 正常路径：文本非空才解析，空值直接给默认值
    try:
        return json.loads(text) if text else default  # 空值直接返回默认值
    # 容错：类型错误或 JSON 语法错误一律视为脏数据
    except (TypeError, ValueError):
        return default  # 脏数据不影响接口返回


# 流程分类视图集：分类是流程模型的一级归类，供模型列表筛选与前端下拉
class WfCategoryViewSet(CrudViewSet):
    # 仅用标准 CRUD，无需自定义动作
    """流程分类：标准增删改查。"""
    model = WfCategory  # 绑定分类模型
    serializer_class = WfCategorySerializer  # 序列化器
    perm_prefix = 'wf:category'  # 权限前缀
    module_name = '流程分类'  # 操作日志模块名
    filter_map = {'name': 'icontains', 'code': 'icontains', 'status': 'exact'}  # 支持的筛选字段


# 流程表单视图集：维护自定义表单配置（字段、组件、校验规则）
class WfFormViewSet(CrudViewSet):
    # 表单只描述结构，业务数据在发起时写入流程实例的 form_data
    """流程表单：表单配置的增删改查。"""
    model = WfForm  # 绑定表单模型
    serializer_class = WfFormSerializer  # 序列化器
    perm_prefix = 'wf:form'  # 权限前缀
    module_name = '流程表单'  # 操作日志模块名
    filter_map = {'form_name': 'icontains', 'form_key': 'icontains', 'status': 'exact'}  # 筛选字段

    @property  # 属性方法：DRF 访问时动态生成当前视图的权限映射
    # 动态权限映射：CRUD 基类的默认映射不包含自定义动作，这里补全后交给 DRF 校验
    def permission_classes(self):
        # 覆盖 permission_classes 属性，DRF 每次请求都会重新计算映射
        """补充表单详情动作的权限映射。"""
        # 动作名 -> 权限标识：表单详情是只读，复用 list 权限
        self.perm_map = {
            # 标准 CRUD 四项权限，与菜单/按钮权限一一对应
            'list': 'wf:form:list', 'create': 'wf:form:create',
            # 更新与删除各用独立权限点，避免误授权
            'update': 'wf:form:update', 'delete': 'wf:form:delete',
            # 详情动作单独列出，否则 PermissionCheck 取不到映射
            'form_detail': 'wf:form:list',
        # 映射字典结束
        }
        # 返回权限类列表，由 DRF 在视图入口统一执行
        return [PermissionCheck]

    # 自定义动作：表单详情，供设计器加载已有配置
    def form_detail(self, request, pk=None):
        # 额外返回解析后的 form_json_obj，前端设计器需要数组而非字符串
        """返回表单配置详情，form_json 解析为数组供设计器直接使用。"""
        row = self.get_queryset().filter(id=pk).first()  # 未删除记录
        if not row:  # 不存在
            # 404：表单不存在或已被逻辑删除
            return fail('表单不存在', code=404)
        data = WfFormSerializer(row).data  # 基础字段
        data['form_json_obj'] = parse_json(row.form_json, [])  # 解析后的字段数组
        # 统一包装返回，前端直接取 data 渲染设计器画布
        return ok(data)


# 用户分组视图集：维护固定审批小组及成员，节点选人时可整组指定
class WfGroupViewSet(CrudViewSet):
    # 成员关系单独存 wf_group_user，因此补充成员查询与覆盖保存动作
    """用户分组：分组维护与成员设置。"""
    model = WfGroup  # 绑定分组模型
    serializer_class = WfGroupSerializer  # 序列化器
    perm_prefix = 'wf:group'  # 权限前缀
    module_name = '用户分组'  # 操作日志模块名
    filter_map = {'group_name': 'icontains', 'group_code': 'icontains', 'status': 'exact'}  # 筛选字段

    @property  # 属性方法：把成员相关自定义动作也纳入权限校验
    # 动态权限映射：把成员查询/保存两个自定义动作纳入校验
    def permission_classes(self):
        # 查看成员归 list，修改成员归 update，避免新增权限点
        """补充成员查询与设置动作的权限映射。"""
        # 动作名 -> 权限标识映射
        self.perm_map = {
            # 标准 CRUD 四动作沿用分组自身权限点
            'list': 'wf:group:list', 'create': 'wf:group:create',
            # 更新/删除沿用分组权限
            'update': 'wf:group:update', 'delete': 'wf:group:delete',
            # users 只读复用 list；set_users 写复用 update
            'users': 'wf:group:list', 'set_users': 'wf:group:update',
        # 映射字典结束
        }
        # 返回权限类
        return [PermissionCheck]

    # 查询分组成员：返回 ID 集合与用户信息，前端据此回显多选
    def users(self, request, pk=None):
        # 先查关联表拿到成员 ID，再查用户表补全账号/昵称
        """查询分组内用户列表。"""
        group = self.get_queryset().filter(id=pk).first()  # 分组
        if not group:  # 分组不存在
            # 404：分组不存在，避免返回空列表造成误解
            return fail('分组不存在', code=404)
        user_ids = list(WfGroupUser.objects.filter(group_id=group.id).values_list('user_id', flat=True))  # 成员 ID
        users = SysUser.objects.filter(id__in=user_ids).values('id', 'username', 'nickname')  # 成员信息
        # group_id 供前端定位，user_ids 用于回显，users 用于渲染姓名
        return ok({'group_id': group.id, 'user_ids': user_ids, 'users': list(users)})

    # 覆盖式保存成员：前端提交全量勾选结果，后端先清空再写入
    def set_users(self, request, pk=None):
        # 为什么覆盖式：勾选 UI 提交的就是最终集合，增量同步容易产生脏数据
        """覆盖式保存分组成员：先清空再写入提交的用户。"""
        group = self.get_queryset().filter(id=pk).first()  # 分组
        if not group:  # 分组不存在
            # 404：分组不存在则不写入，避免产生孤儿关联
            return fail('分组不存在', code=404)
        user_ids = [int(x) for x in (request.data.get('user_ids') or []) if str(x).isdigit()]  # 过滤合法 ID
        WfGroupUser.objects.filter(group_id=group.id).delete()  # 覆盖式更新
        now = time.strftime('%Y-%m-%d %H:%M:%S')  # 统一写入时间
        for uid in set(user_ids):  # 去重写入
            # 逐条写入关联表；create_time 记录加入时间供后续排序
            WfGroupUser.objects.create(group_id=group.id, user_id=uid, create_time=now)
        # 回显最终成员 ID，结构与 users 接口保持一致
        return ok({'user_ids': user_ids}, '成员保存成功')


# 流程模型视图集：流程定义 CRUD，外加设计器保存、发布、停用、复制
class WfModelViewSet(CrudViewSet):
    # 模型保存 BPMN XML 与节点配置，发布时版本 +1 供实例锁定快照
    """流程模型：设计、保存、发布、停用与复制。"""
    model = WfModel  # 绑定模型
    serializer_class = WfModelSerializer  # 序列化器
    perm_prefix = 'wf:model'  # 权限前缀
    module_name = '流程模型'  # 操作日志模块名
    # 筛选映射：名称/Key 模糊搜索，分类/状态精确匹配
    filter_map = {'model_name': 'icontains', 'model_key': 'icontains',
                  # status 精确匹配用于区分草稿(0)/已发布(1)/停用(2)
                  'category_id': 'exact', 'status': 'exact'}  # 筛选字段

    @property  # 属性方法：把设计器相关自定义动作也纳入权限校验
    # 动态权限映射：设计器相关自定义动作也纳入权限校验
    def permission_classes(self):
        # 保存/发布/停用/复制/下拉都会读写模型，必须挂权限点
        """补充设计/发布/复制/停用/下拉动作的权限映射。"""
        # 动作名 -> 权限标识
        self.perm_map = {
            # 标准 CRUD 四动作
            'list': 'wf:model:list', 'create': 'wf:model:create',
            # 更新/删除沿用模型自身权限点
            'update': 'wf:model:update', 'delete': 'wf:model:delete',
            # 设计器读取复用 list；保存属于修改，复用 update
            'design': 'wf:model:list', 'save': 'wf:model:update',
            # 发布有独立权限点；停用复用 update
            'publish': 'wf:model:publish', 'disable': 'wf:model:update',
            # 复制本质是新增，复用 create；下拉只读复用 list
            'copy': 'wf:model:create', 'options': 'wf:model:list',
        # 映射字典结束
        }
        # 返回权限类
        return [PermissionCheck]

    # 新增模型：包一层捕获唯一键冲突，返回业务可读提示
    def create(self, request):
        # model_key 建了唯一索引，用数据库约束兜底比“先查后写”更可靠
        """新增模型：校验模型 Key 唯一，并给出友好提示。"""
        # 复用基类新增逻辑：字段校验、审计字段与操作日志都由基类完成
        try:
            return super().create(request)  # 复用通用新增逻辑
        except IntegrityError:  # 唯一键冲突
            # 唯一键冲突说明 model_key 已存在，转换为业务提示而非 500
            return fail('模型 Key 已存在，请更换')

    # 设计器数据：一次返回模型信息、BPMN XML 与节点配置
    def design(self, request, pk=None):
        # 前端 bpmn-js 打开画布时依赖这三块数据还原
        """返回模型设计数据：BPMN XML 与节点配置。"""
        row = self.get_queryset().filter(id=pk).first()  # 模型
        if not row:  # 不存在
            # 404：模型不存在
            return fail('模型不存在', code=404)
        # 统一响应：data 内为设计器所需完整快照
        return ok({
            # 标识与状态：id 供后续保存，status/version 供界面提示
            'id': row.id, 'model_name': row.model_name, 'model_key': row.model_key,
            # 版本号只读展示，只有发布动作会递增
            'status': row.status, 'version': row.version,
            'bpmn_xml': row.bpmn_xml or '',  # 流程定义
            'node_config': parse_json(row.node_config, {}),  # 节点审批人配置
        # 结束字典并包装成功响应
        })

    # 保存设计结果：先校验 XML 可解析，再落库 XML 与节点配置
    def save(self, request):
        # 先校验后写库，避免保存坏流程导致后续发布/发起失败
        """保存设计结果：更新 BPMN XML 与节点配置。"""
        pk = request.data.get('id')  # 模型 ID
        row = self.get_queryset().filter(id=pk).first()  # 模型
        if not row:  # 不存在
            # 404：模型不存在
            return fail('模型不存在', code=404)
        xml = request.data.get('bpmn_xml') or ''  # 流程定义
        # 实例化流程图即做语法/结构校验，不会触发实际流转
        try:
            engine.ProcessGraph(xml)  # 保存前先解析，提前暴露错误 XML
        except engine.EngineError as exc:  # 解析失败
            # 解析失败：原样返回引擎错误，提示用户修正画布
            return fail(str(exc))
        node_config = request.data.get('node_config') or {}  # 节点配置
        row.bpmn_xml = xml  # 写入 XML
        row.node_config = json.dumps(node_config, ensure_ascii=False)  # 写入配置
        row.update_by = request.user_info.username  # 更新人
        row.update_time = time.strftime('%Y-%m-%d %H:%M:%S')  # 更新时间
        row.save(update_fields=['bpmn_xml', 'node_config', 'update_by', 'update_time'])  # 只更新必要字段
        # 只回 id，前端据此标记已保存
        return ok({'id': row.id}, '设计保存成功')

    # 发布模型：校验流程可运行且已绑定表单，然后版本 +1 置为已发布
    def publish(self, request, pk=None):
        # 版本递增让在途实例继续使用旧版本快照，实现版本隔离
        """发布模型：校验流程可解析，版本号 +1 并置为已发布。"""
        row = self.get_queryset().filter(id=pk).first()  # 模型
        if not row:  # 不存在
            # 404：模型不存在
            return fail('模型不存在', code=404)
        # 发布前再次校验 BPMN，防止保存后 XML 被直接改库绕过校验
        try:
            engine.ProcessGraph(row.bpmn_xml)  # 校验 BPMN
        # 捕获引擎的结构错误
        except engine.EngineError as exc:
            # 返回具体错误信息，便于设计器定位问题节点
            return fail(str(exc))
        if not row.form_id:  # 未绑定表单
            # 未绑定表单的业务流程无法渲染发起页，必须阻断发布
            return fail('请先为流程绑定表单再发布')
        row.version = (row.version or 0) + 1  # 版本递增，实现版本隔离
        row.status = 1  # 已发布
        row.update_by = request.user_info.username  # 更新人
        row.update_time = time.strftime('%Y-%m-%d %H:%M:%S')  # 更新时间
        row.save(update_fields=['version', 'status', 'update_by', 'update_time'])  # 持久化
        # 返回新版本号，前端据此提示“发布成功 vN”
        return ok({'id': row.id, 'version': row.version}, '发布成功')

    # 停用模型：只改状态，不删除定义也不影响已运行实例
    def disable(self, request, pk=None):
        # 停用后 options 下拉不再返回该模型，新发起入口自然收敛
        """停用模型：已运行实例不受影响，新发起将不可选择。"""
        row = self.get_queryset().filter(id=pk).first()  # 模型
        if not row:  # 不存在
            # 404：模型不存在
            return fail('模型不存在', code=404)
        row.status = 2  # 停用
        row.update_by = request.user_info.username  # 更新人
        row.update_time = time.strftime('%Y-%m-%d %H:%M:%S')  # 更新时间
        row.save(update_fields=['status', 'update_by', 'update_time'])  # 持久化
        # 无返回体，仅提示状态变更成功
        return ok(None, '已停用')

    # 复制模型：以原模型为模板生成草稿副本，便于改版试运行
    def copy(self, request, pk=None):
        # 副本 version/status 归零，避免未审核的副本被直接发起
        """复制模型：生成草稿副本，便于快速改版。"""
        row = self.get_queryset().filter(id=pk).first()  # 原模型
        if not row:  # 不存在
            # 404：原模型不存在
            return fail('模型不存在', code=404)
        new_key = '%s_copy_%s' % (row.model_key, time.strftime('%H%M%S'))  # 新 Key 带时间戳避免冲突
        now = time.strftime('%Y-%m-%d %H:%M:%S')  # 当前时间
        # 落库副本：沿用分类/表单/流程定义/节点配置，重置发布状态
        new_row = WfModel.objects.create(
            # 名称加“副本”后缀；Key 带时间戳避免唯一约束冲突
            model_name='%s 副本' % row.model_name, model_key=new_key,
            # 继承分类与表单：副本默认沿用同一套业务表单
            category_id=row.category_id, form_id=row.form_id, bpmn_xml=row.bpmn_xml,
            # 继承流程定义与节点配置：画布与审批人配置一起复制
            node_config=row.node_config, version=0, status=0, process_status=0,
            # 版本/状态/流程状态全部归零，副本从草稿开始
            remark='由 %s 复制' % row.model_name, create_by=request.user_info.username,
            # 审计字段按当前操作人写入，is_deleted=0 表示有效记录
            create_time=now, update_by=request.user_info.username, update_time=now, is_deleted=0)
        # 返回新主键，前端可直接跳转到副本设计页
        return ok({'id': new_row.id}, '复制成功')

    # 下拉数据：供发起流程页选择可发起的模型
    def options(self, request):
        # 只返回已发布模型，草稿/停用不对外暴露
        """返回已发布且启用的模型，供发起流程页选择。"""
        rows = self.get_queryset().filter(status=1)  # 已发布模型
        # 精简字段：下拉只需要标识与关联 ID，不返回体积较大的 XML
        data = [{'id': r.id, 'model_name': r.model_name, 'model_key': r.model_key,
                 # form_id 决定发起页渲染哪套表单，category_id 供分组展示
                 'form_id': r.form_id, 'category_id': r.category_id} for r in rows]  # 精简字段
        # 返回数组而非分页，下拉场景数据量小
        return ok(data)


# 流程监听器视图集：维护节点/流程事件的回调、通知等扩展配置
class WfListenerViewSet(CrudViewSet):
    # 监听器由 engine.py 在对应事件点触发，本视图集只负责配置读写
    """流程监听器配置。"""
    model = WfListener  # 绑定监听器
    serializer_class = WfListenerSerializer  # 序列化器
    perm_prefix = 'wf:listener'  # 权限前缀
    module_name = '流程监听器'  # 操作日志模块名
    # 筛选：按模型、事件类型、动作类型、启停状态精确定位监听器
    filter_map = {'model_id': 'exact', 'event_type': 'exact',
                  # action_type 区分 callback/notify/update_data/log；status 0 启用 / 1 停用
                  'action_type': 'exact', 'status': 'exact'}  # 筛选字段


# 流程表达式视图集：维护网关条件与动态审批人表达式
class WfExpressionViewSet(CrudViewSet):
    # 表达式由引擎解释执行，改动只影响此后新产生的流转
    """流程表达式配置。"""
    model = WfExpression  # 绑定表达式
    serializer_class = WfExpressionSerializer  # 序列化器
    perm_prefix = 'wf:expression'  # 权限前缀
    module_name = '流程表达式'  # 操作日志模块名
    # 筛选：名称/编码模糊搜索，类型精确匹配
    filter_map = {'expr_name': 'icontains', 'expr_code': 'icontains',
                  # expr_type 区分 condition 条件表达式与 assignee 审批人表达式
                  'expr_type': 'exact'}  # 筛选字段
    order_by = 'id'  # 编号升序


# 流程实例视图集：运行态查询 + 发起/终止/撤回等生命周期动作
class WfInstanceViewSet(viewsets.ViewSet):
    # 不用 CrudViewSet：实例由流程引擎创建，禁止外部直接增删改
    """流程实例：发起、我的流程、全局监控、轨迹、终止与撤回。"""
    permission_classes = [PermissionCheck]  # 统一权限校验

    @property  # 属性方法：实例相关动作到权限标识的动态映射
    # 动作 -> 权限标识映射；用 property 让 DRF 每次请求动态读取
    def perm_map(self):
        # 实例是跨部门数据，列表/终止/撤回必须受权限控制
        """接口动作到权限标识的映射。"""
        # 返回映射字典
        return {
            # 全局列表走独立权限；我的流程只返回本人发起的数据
            'list': 'wf:instance:list', 'my': 'wf:instance:my', 'start': 'wf:start:create',
            'detail_info': '', 'trace': '',  # 详情/轨迹对已登录业务用户开放（发起人、审批人需查看）
            # 终止属高风险操作单独授权；撤回仅发起人可用，视图内再校验归属
            'terminate': 'wf:instance:terminate', 'withdraw': 'wf:instance:withdraw',
        # 映射字典结束
        }

    # 统一查询集：逻辑删除过滤 + 最新在前，所有实例动作复用
    def get_queryset(self):
        # 倒序符合“最新流程在最上面”的使用习惯
        """未删除实例集合，按最新发起倒序。"""
        # 排除逻辑删除实例；-id 让新实例优先展示
        return WfInstance.objects.filter(is_deleted=0).order_by('-id')

    # 内部工具：把实例对象序列化为字典，供详情/轨迹复用
    def _serialize(self, row):
        # 只做一层封装，后续追加字段时改一处即可
        """实例序列化。"""
        # 复用 WfInstanceSerializer，保证各接口字段一致
        return WfInstanceSerializer(row).data

    # 全局实例列表：管理员监控所有运行中与历史流程
    def list(self, request):
        # 支持模型、状态、发起人、业务单据号组合筛选
        """全局实例列表（管理员监控）。"""
        qs = self.get_queryset()  # 基础集合
        # 支持的四类筛选参数与对应的 ORM lookup
        for key, lookup in (('model_id', 'exact'), ('status', 'exact'),
                            # exact 用于 ID/状态；icontains 用于单据号模糊搜索
                            ('start_user_id', 'exact'), ('biz_key', 'icontains')):
            value = request.query_params.get(key)  # 取查询参数
            if value not in (None, ''):  # 非空才过滤
                # 非空才叠加过滤条件，避免空字符串把结果清空
                qs = qs.filter(**{key + '__' + lookup: value})
        return StandardPagination(request).paginate(qs, WfInstanceSerializer)  # 分页输出

    # 我的流程：只返回当前登录人发起的实例
    def my(self, request):
        # 对应前端“我发起的申请”页面
        """我发起的流程实例列表。"""
        qs = self.get_queryset().filter(start_user_id=request.user_info.id)  # 只取本人发起
        status = request.query_params.get('status')  # 状态筛选
        if status not in (None, ''):  # 非空
            # 状态筛选：0 运行中 / 1 已完成 / 2 已驳回 / 3 已终止
            qs = qs.filter(status=status)
        # 统一分页输出，前端按 total/rows 渲染表格
        return StandardPagination(request).paginate(qs, WfInstanceSerializer)

    # 内部工具：按实例的 model_id 取流程模型
    def _load_model(self, row):
        # 实例只存模型 ID，需要时再查，避免实例表冗余大字段
        """取实例对应的流程模型。"""
        # first() 容错：模型被物理删除时返回 None
        return WfModel.objects.filter(id=row.model_id).first()

    # 组装实例详情：一次返回前端详情页所需的全部数据
    def _detail_data(self, request, row):
        # 避免前端为模型/表单/轨迹/任务发起多次请求
        """组装实例详情：模型、表单、表单数据、审批记录与任务。"""
        model = self._load_model(row)  # 模型
        form = WfForm.objects.filter(id=model.form_id).first() if model and model.form_id else None  # 表单
        audits = WfAudit.objects.filter(instance_id=row.id).order_by('id')  # 审批轨迹
        tasks = WfTask.objects.filter(instance_id=row.id, is_deleted=0).order_by('id')  # 任务列表
        pending_mine = tasks.filter(assignee=request.user_info.id, status=0).exists()  # 当前用户是否有待办
        # 统一返回结构，字段名与前端详情页约定一致
        return {
            'instance': self._serialize(row),  # 实例字段
            # 模型快照：含 XML 与节点配置，供前端画流程图/展示审批人
            'model': {'id': model.id, 'model_name': model.model_name, 'model_key': model.model_key,
                      # 即使模型已停用也返回定义，历史实例仍可查看流程图
                      'bpmn_xml': model.bpmn_xml or '', 'form_id': model.form_id,
                      # node_config 解析失败时降级为空对象，不影响详情页
                      'node_config': parse_json(model.node_config, {})} if model else None,
            # 表单结构：前端按 form_json 渲染只读表单
            'form': {'id': form.id, 'form_name': form.form_name,
                     # form 可能为空（流程未绑定表单），此时返回 None
                     'form_json': parse_json(form.form_json, [])} if form else None,
            'form_data': parse_json(row.form_data, {}),  # 表单数据对象
            'audits': WfAuditSerializer(audits, many=True).data,  # 轨迹
            'tasks': WfTaskSerializer(tasks, many=True).data,  # 任务
            'canApprove': pending_mine,  # 是否可操作
        # 结束返回字典
        }

    # 实例详情接口：按主键返回完整详情
    def detail_info(self, request, pk=None):
        # 对发起人/审批人开放，权限映射为空表示只校验登录态
        """实例详情。"""
        row = self.get_queryset().filter(id=pk).first()  # 实例
        if not row:  # 不存在
            # 404：实例不存在或已逻辑删除
            return fail('流程实例不存在', code=404)
        # 复用 _detail_data，避免详情与轨迹接口字段不一致
        return ok(self._detail_data(request, row))

    # 流程轨迹：按时间线展示审批记录与任务，供流程图高亮当前节点
    def trace(self, request, pk=None):
        # 轨迹是审批系统的核心可追溯能力
        """流程轨迹：审批记录 + 任务 + 当前节点。"""
        row = self.get_queryset().filter(id=pk).first()  # 实例
        if not row:  # 不存在
            # 404：实例不存在
            return fail('流程实例不存在', code=404)
        audits = WfAudit.objects.filter(instance_id=row.id).order_by('id')  # 轨迹
        # 轨迹响应：实例摘要 + 审批记录 + 任务列表
        return ok({
            # 实例摘要给前端展示单号、状态、当前节点
            'instance': self._serialize(row),
            # 审批记录按 id 升序即为操作时间线
            'audits': WfAuditSerializer(audits, many=True).data,
            # 任务列表含已完成与待办，用于流程图节点着色
            'tasks': WfTaskSerializer(WfTask.objects.filter(instance_id=row.id, is_deleted=0), many=True).data,
        # 结束返回字典
        })

    # 发起流程：服务端校验 + 创建实例 + 启动引擎生成首个待办
    def start(self, request):
        # 全流程在请求内同步完成，创建失败必须把已写数据清理干净
        """发起流程：校验表单必填项，创建实例并启动引擎。"""
        model_id = request.data.get('model_id')  # 模型 ID
        model = WfModel.objects.filter(id=model_id, is_deleted=0).first()  # 模型
        if not model:  # 不存在
            # 模型不存在时无法渲染表单，直接拒绝
            return fail('流程模型不存在')
        if model.status != 1:  # 未发布不可发起
            # 草稿/停用模型不允许发起，防止绕过发布审核
            return fail('该流程尚未发布，无法发起')
        form_data = request.data.get('form_data') or {}  # 表单数据
        if isinstance(form_data, str):  # 兼容 JSON 字符串
            # 兼容老前端或第三方以 JSON 字符串提交表单数据
            form_data = parse_json(form_data, {})
        form = WfForm.objects.filter(id=model.form_id).first() if model.form_id else None  # 绑定表单
        if form:  # 必填项服务端校验
            fields = parse_json(form.form_json, [])  # 字段数组
            # 服务端必填校验：前端校验可绕过，接口必须再校验一次
            missing = [f.get('label') or f.get('key') for f in fields
                       # 遍历字段定义，required 为真才检查
                       if f.get('required') and (
                           # 未传或去空格后为空都视为缺失
                           form_data.get(f.get('key')) is None
                           or str(form_data.get(f.get('key'))).strip() == '')]  # 缺失项
            if missing:  # 有必填未填
                # 把缺失字段的中文 label 拼给用户，便于直接定位
                return fail('请填写必填项：%s' % '、'.join(missing))
        now = time.strftime('%Y-%m-%d %H:%M:%S')  # 当前时间
        # 业务单据号：外部可传；未传则用模型 Key + 时间戳生成
        biz_key = request.data.get('biz_key') or '%s%s' % (
            (model.model_key or 'WF').upper(), time.strftime('%Y%m%d%H%M%S'))  # 业务单据号
        # 创建实例记录：快照模型版本并保存表单数据
        instance = WfInstance.objects.create(
            # instance_key 用 uuid 保证对外唯一；model_version 锁定发起时的版本
            instance_key=uuid.uuid4().hex, model_id=model.id, model_version=model.version or 1,
            # form_data 落库为 JSON 文本，查询与回显统一按字符串处理
            biz_key=biz_key, form_data=json.dumps(form_data, ensure_ascii=False),
            # 新实例为运行中(0)，当前节点由引擎启动后写入
            start_user_id=request.user_info.id, status=0, current_node=None,
            # 发起时间与审计字段一次写入
            start_time=now, create_by=request.user_info.username, create_time=now,
            # 审计人取当前登录用户；is_deleted=0 表示有效
            update_by=request.user_info.username, update_time=now, is_deleted=0)  # 创建实例
        engine_obj = engine.WorkflowEngine(instance, model)  # 构造引擎
        engine_obj.record(request.user_info.id, 'submit', '提交申请', None, None, '发起流程')  # 提交记录
        # 引擎启动可能因流程定义缺陷抛错，需要清理已写入的数据
        try:
            engine_obj.start()  # 启动并生成首个待办
        except engine.EngineError as exc:  # 流程定义问题
            WfAudit.objects.filter(instance_id=instance.id).delete()  # 清理提交记录
            WfTask.objects.filter(instance_id=instance.id).delete()  # 清理可能生成的待办
            instance.delete()  # 删除实例，避免留下孤儿数据
            # 返回引擎错误；实例已回滚，用户修正流程后可重试
            return fail(str(exc))
        # 返回实例 id 与单据号，前端据此跳转详情/待办页
        return ok({'id': instance.id, 'biz_key': biz_key}, '发起成功')

    # 强制终止：管理员对运行中实例做终态处理
    def terminate(self, request, pk=None):
        # 终止会关闭全部待办并写审批记录，属高风险动作
        """管理员强制终止运行中的实例。"""
        row = self.get_queryset().filter(id=pk).first()  # 实例
        if not row:  # 不存在
            # 404：实例不存在
            return fail('流程实例不存在', code=404)
        if row.status != 0:  # 已结束不可终止
            # 只有运行中(0)才能终止，终态实例重复终止无意义
            return fail('流程已结束，无需终止')
        model = self._load_model(row)  # 模型
        # 委托引擎：关闭待办、写轨迹、把实例置为终止
        engine.terminate_instance(row, model, request.user_info.id,
                                  request.data.get('comment') or '管理员终止')  # 终止处理
        # 终止成功，无返回数据
        return ok(None, '已终止')

    # 发起人撤回：仅本人在无人审批前可撤回
    def withdraw(self, request, pk=None):
        # 撤回失败需给出明确原因（非本人/已结束/已有审批）
        """发起人撤回：仅本人且无人审批时可用。"""
        row = self.get_queryset().filter(id=pk).first()  # 实例
        if not row:  # 不存在
            # 404：实例不存在
            return fail('流程实例不存在', code=404)
        if row.start_user_id != request.user_info.id:  # 非本人发起
            # 越权校验：只能撤回自己发起的流程
            return fail('只能撤回自己发起的流程', code=403)
        if row.status != 0:  # 已结束
            # 终态实例不可撤回
            return fail('流程已结束，无法撤回')
        # 引擎会检查是否已有审批，有则抛错阻断撤回
        try:
            # 委托引擎：撤销待办并把实例置为终止终态
            engine.withdraw_instance(row, request.user_info.id,
                                     request.data.get('comment') or '发起人撤回')  # 撤回处理
        except engine.EngineError as exc:  # 已有审批
            # 已有审批或状态变化时返回引擎错误原因
            return fail(str(exc))
        # 撤回成功
        return ok(None, '撤回成功')


# 流程任务视图集：待办/已办/全局任务查询与六类审批动作
class WfTaskViewSet(viewsets.ViewSet):
    # 任务由 engine.py 生成，本视图集只处理人工操作入口
    """流程任务：待办/已办/全局任务与审批动作。"""
    permission_classes = [PermissionCheck]  # 统一权限校验

    @property  # 属性方法：任务相关动作到权限标识的动态映射
    # 动作 -> 权限标识映射
    def perm_map(self):
        # 列表类与审批类动作各自独立授权，便于按岗位配置按钮权限
        """接口动作到权限标识的映射。"""
        # 返回映射字典
        return {
            # 三类列表：我的待办、我的已办、全局监控
            'todo': 'wf:task:todo', 'done': 'wf:task:done', 'list': 'wf:task:list',
            # 同意/驳回是审批核心动作，独立权限点
            'approve': 'wf:task:approve', 'reject': 'wf:task:reject',
            # 转审/加签会改变处理人，独立权限点
            'transfer': 'wf:task:transfer', 'addsign': 'wf:task:addsign',
            # 退回上一步涉及流程回滚，独立权限点
            'back': 'wf:task:back',
        # 映射字典结束
        }

    # 内部工具：按状态/处理人/实例筛选任务，列表接口复用
    def _filters(self, qs, request):
        # 查询参数缺失或为空时不过滤，保持全量
        """按实例、状态、处理人筛选任务列表。"""
        # 三类精确匹配字段
        for key in ('status', 'assignee', 'instance_id'):
            value = request.query_params.get(key)  # 查询参数
            if value not in (None, ''):  # 非空
                # 非空才叠加过滤条件
                qs = qs.filter(**{key: value})
        # 返回过滤后的查询集，交由分页器处理
        return qs

    # 我的待办：仅当前处理人且状态为待办的任务
    def todo(self, request):
        # status=0 且未逻辑删除，最新生成的排前面
        """我的待办：仅当前处理人且状态待办。"""
        qs = WfTask.objects.filter(assignee=request.user_info.id, status=0, is_deleted=0).order_by('-id')  # 待办
        # 统一分页，前端表格直接渲染
        return StandardPagination(request).paginate(qs, WfTaskSerializer)

    # 我的已办：当前用户处理过的任务
    def done(self, request):
        # 含已办(1)/转派(2)/加签(3)/驳回(4) 四种终态
        """我的已办：当前用户处理过的任务（含转派/驳回）。"""
        # 按处理人维度过滤
        qs = WfTask.objects.filter(assignee=request.user_info.id,
                                   status__in=[1, 2, 3, 4], is_deleted=0).order_by('-id')  # 已处理
        # 分页输出，结构与待办接口一致
        return StandardPagination(request).paginate(qs, WfTaskSerializer)

    # 全局任务监控：管理员查看所有任务
    def list(self, request):
        # 支持状态/处理人/实例筛选，便于排查卡单
        """全局任务监控。"""
        qs = self._filters(WfTask.objects.filter(is_deleted=0).order_by('-id'), request)  # 全量任务
        # 分页返回全量任务
        return StandardPagination(request).paginate(qs, WfTaskSerializer)

    # 内部工具：加行锁取任务并校验归属人与实例状态
    def _task(self, request, pk):
        # 六类审批动作共用此入口，保证前置校验一致
        """取任务并校验归属人，防止越权处理他人待办。"""
        with transaction.atomic():  # 行锁事务，避免并发重复审批
            task = WfTask.objects.select_for_update().filter(id=pk, is_deleted=0).first()  # 锁定任务
            if not task:  # 不存在
                # 任务不存在：多为并发重复提交或已被处理
                return None, fail('任务不存在', code=404)
            if task.assignee != request.user_info.id:  # 非本人任务
                perms = get_user_perms(request.user_info)  # 当前用户权限集合
                if '*:*:*' not in perms:  # 超管可代为处理/转派，其余用户越权
                    # 非超管处理他人任务属越权，直接 403
                    return None, fail('只能处理分配给自己的任务', code=403)
            instance = WfInstance.objects.select_for_update().filter(id=task.instance_id).first()  # 锁定实例
            if not instance:  # 实例不存在
                # 实例被删除时任务也失去意义，返回 404
                return None, fail('流程实例不存在', code=404)
            if instance.status != 0:  # 实例已结束
                # 终态实例不再接受任何审批动作
                return None, fail('流程已结束，无法操作')
            model = WfModel.objects.filter(id=instance.model_id).first()  # 模型
            if not model:  # 模型已删除
                # 模型缺失说明配置被物理删除，无法继续流转
                return None, fail('流程模型不存在')
            return (task, instance, model), None  # 三元组供动作复用

    # 同意：审批通过并推进到下一节点
    def approve(self, request, pk=None):
        # 写审批记录、关闭当前任务、生成后续待办/抄送全部由引擎完成
        """同意任务。"""
        with transaction.atomic():  # 审批写库与引擎流转同事务
            loaded, error = self._task(request, pk)  # 取任务
            # 前置校验失败直接返回
            if error:
                # 返回 fail 响应：任务不存在/越权/实例已结束等
                return error
            task, instance, model = loaded  # 解包
            comment = request.data.get('comment') or ''  # 审批意见
            engine.approve_task(instance, model, task, request.user_info.id, comment)  # 引擎推进
            # 返回实例最新状态，前端据此提示“已通过/流程结束”
            return ok({'instance_status': instance.status}, '审批通过')

    # 驳回：把流程置为驳回终态并通知发起人
    def reject(self, request, pk=None):
        # 驳回必须写意见，便于追溯原因
        """驳回任务。"""
        with transaction.atomic():  # 保持事务一致性
            loaded, error = self._task(request, pk)  # 取任务
            # 前置校验失败直接返回
            if error:
                # 返回 fail 响应
                return error
            task, instance, model = loaded  # 解包
            comment = request.data.get('comment') or ''  # 驳回意见
            if not comment:  # 驳回必须填写理由
                # 驳回意见为必填，空意见无法向发起人解释
                return fail('请填写驳回意见')
            engine.reject_task(instance, model, task, request.user_info.id, comment)  # 驳回处理
            # 驳回成功
            return ok(None, '已驳回')

    # 转审：把当前待办转给其他用户处理
    def transfer(self, request, pk=None):
        # 转出后原任务置为已转派，新任务归属目标用户
        """转审给其他用户。"""
        with transaction.atomic():  # 保持事务一致性
            loaded, error = self._task(request, pk)  # 取任务
            # 前置校验失败直接返回
            if error:
                # 返回 fail 响应
                return error
            task, instance, model = loaded  # 解包
            target = request.data.get('user_id')  # 目标用户
            if not target:  # 未选择
                # 必须指定转审人
                return fail('请选择转审人')
            if int(target) == request.user_info.id:  # 不能转给自己
                # 转给自己没有意义，直接拒绝
                return fail('不能转审给自己')
            if not SysUser.objects.filter(id=target, status=0, is_deleted=0).exists():  # 目标无效
                # 目标账号必须存在且启用，避免转到离职/停用账号
                return fail('转审人不存在或已停用')
            # 委托引擎写轨迹并重建任务归属
            engine.transfer_task(instance, model, task, request.user_info.id, target,
                                 request.data.get('comment') or '')  # 转审处理
            # 转审成功
            return ok(None, '转审成功')

    # 加签：在当前节点追加处理人，转为会签
    def addsign(self, request, pk=None):
        # 加签不改变当前处理人，完成后需所有会签人同意
        """加签其他用户，节点转为会签。"""
        with transaction.atomic():  # 保持事务一致性
            loaded, error = self._task(request, pk)  # 取任务
            # 前置校验失败直接返回
            if error:
                # 返回 fail 响应
                return error
            task, instance, model = loaded  # 解包
            target = request.data.get('user_id')  # 加签人
            if not target:  # 未选择
                # 必须指定加签人
                return fail('请选择加签人')
            if int(target) == request.user_info.id:  # 不能加签自己
                # 加签给自己等于重复待办，拒绝
                return fail('不能加签给自己')
            if not SysUser.objects.filter(id=target, status=0, is_deleted=0).exists():  # 目标无效
                # 加签对象需为有效账号
                return fail('加签人不存在或已停用')
            # 委托引擎生成会签任务并记录轨迹
            engine.addsign_task(instance, model, task, request.user_info.id, target,
                                request.data.get('comment') or '')  # 加签处理
            # 加签成功
            return ok(None, '加签成功')

    # 退回上一步：把流程回退到上一审批节点
    def back(self, request, pk=None):
        # 与驳回不同：退回只回退一级，流程仍在原实例上继续
        """退回上一步。"""
        with transaction.atomic():  # 保持事务一致性
            loaded, error = self._task(request, pk)  # 取任务
            # 前置校验失败直接返回
            if error:
                # 返回 fail 响应
                return error
            task, instance, model = loaded  # 解包
            # 回退依赖上一节点快照，无上一节点时引擎抛错
            try:
                # 委托引擎：关闭当前任务并在上一节点重建待办
                engine.back_task(instance, model, task, request.user_info.id,
                                 request.data.get('comment') or '')  # 回退处理
            except engine.EngineError as exc:  # 无可退回节点
                # 无可退回节点等业务错误原样返回
                return fail(str(exc))
            # 退回成功
            return ok(None, '已退回上一步')


# 抄送视图集：只读通知，接收人查看并标记已读
class WfCcViewSet(viewsets.ViewSet):
    # 抄送由引擎在节点完成时写入 wf_cc，本视图集不创建抄送
    """抄送：抄送我的列表与标记已读。"""
    permission_classes = [PermissionCheck]  # 统一权限校验

    @property  # 属性方法：抄送相关动作复用同一查询权限
    # 动作 -> 权限映射：两个动作都复用抄送查询权限
    def perm_map(self):
        # 已读属于查看行为的延伸，不再单独设权限点
        """接口动作到权限标识的映射。"""
        # mine/read 同一权限，避免用户能看却不能标记已读
        return {'mine': 'wf:cc:mine', 'read': 'wf:cc:mine'}

    # 抄送我的：当前用户收到的抄送记录
    def mine(self, request):
        # 最新抄送在前，便于优先处理新通知
        """抄送我的列表。"""
        qs = WfCc.objects.filter(user_id=request.user_info.id).order_by('-id')  # 当前用户抄送
        # 分页输出，字段含实例、来源节点、已读状态
        return StandardPagination(request).paginate(qs, WfCcSerializer)

    # 标记已读：仅允许本人操作自己的抄送记录
    def read(self, request, pk=None):
        # 更新 status=1，前端未读角标随之减少
        """标记抄送为已读。"""
        row = WfCc.objects.filter(id=pk, user_id=request.user_info.id).first()  # 本人抄送
        if not row:  # 不存在
            # 记录不存在或不属于本人时统一 404，避免探测他人数据
            return fail('抄送记录不存在', code=404)
        row.status = 1  # 已读
        # 只更新 status 字段，减少写放大
        row.save(update_fields=['status'])
        # 已读成功
        return ok(None, '已读')


# 节点配置下拉视图集：给流程设计器提供选人/选角色/选部门数据
class OptionViewSet(viewsets.ViewSet):
    # 只读接口，登录即可访问，不额外要求工作流权限
    """节点配置下拉数据：用户、角色、部门、分组与表达式。"""
    permission_classes = [LoginRequired]  # 仅要求登录，配置人员均可读取

    # 用户下拉：返回启用账号的 id/账号/昵称/部门
    def users(self, request):
        # 停用与已删除账号不应出现在审批人候选列表
        """启用用户列表。"""
        rows = SysUser.objects.filter(status=0, is_deleted=0).order_by('id')  # 有效账号
        # 精简字段，避免把密码等敏感列带出
        return ok([{'id': r.id, 'username': r.username, 'nickname': r.nickname,
                    # dept_id 供前端按部门分组或联动筛选
                    'dept_id': r.dept_id} for r in rows])

    # 角色下拉：返回启用角色，节点可按角色指定审批人
    def roles(self, request):
        # 运行时由引擎把角色解析为具体用户
        """启用角色列表。"""
        rows = SysRole.objects.filter(status=0, is_deleted=0).order_by('role_sort', 'id')  # 有效角色
        # role_key 供节点配置保存稳定的业务标识
        return ok([{'id': r.id, 'role_name': r.role_name, 'role_key': r.role_key} for r in rows])

    # 部门下拉：返回未删除部门，供按部门选人或组织树展示
    def depts(self, request):
        # parent_id 让前端可以还原部门层级
        """部门列表。"""
        rows = SysDept.objects.filter(is_deleted=0).order_by('order_num', 'id')  # 有效部门
        # 返回扁平数组，层级关系由 parent_id 表达
        return ok([{'id': r.id, 'dept_name': r.dept_name, 'parent_id': r.parent_id} for r in rows])

    # 分组下拉：返回启用的固定审批小组
    def groups(self, request):
        # 节点选择分组后，引擎会把组内成员展开为审批人
        """启用分组列表。"""
        rows = WfGroup.objects.filter(status=0, is_deleted=0).order_by('id')  # 有效分组
        # group_code 供节点配置引用，避免依赖可变的组名
        return ok([{'id': r.id, 'group_name': r.group_name, 'group_code': r.group_code} for r in rows])
