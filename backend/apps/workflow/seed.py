"""工作流初始化：菜单（三级）、按钮权限、请假/报销演示流程与示例数据（幂等可重复执行）。"""
import json  # 表单与节点配置序列化
import time  # 写入时间字符串

from apps.workflow.models import (
    WfCategory, WfExpression, WfForm, WfGroup, WfGroupUser, WfListener, WfModel)  # 工作流模型


# 菜单定义：(父 key, key, 名称, 路由, 组件, 权限, 类型, 图标, 排序)
MENUS = [
    (None, 'workflow', '工作流程', 'workflow', '', '', 'M', 'Share', 3),  # 一级目录
    ('workflow', 'wf_manage', '流程管理', 'manage', '', '', 'M', 'SetUp', 1),  # 二级目录
    # 流程管理二级目录：配置类页面（分类、模型、表单、分组、监听器、表达式、实例、任务）
    ('wf_manage', 'wf_category', '流程分类', 'category', 'workflow/category/index', 'wf:category:list', 'C', 'CollectionTag', 1),
    ('wf_manage', 'wf_model', '流程模型', 'model', 'workflow/model/index', 'wf:model:list', 'C', 'Share', 2),
    ('wf_manage', 'wf_form', '流程表单', 'form', 'workflow/form/index', 'wf:form:list', 'C', 'Document', 3),
    ('wf_manage', 'wf_group', '用户分组', 'group', 'workflow/group/index', 'wf:group:list', 'C', 'UserFilled', 4),
    ('wf_manage', 'wf_listener', '流程监听器', 'listener', 'workflow/listener/index', 'wf:listener:list', 'C', 'Bell', 5),
    ('wf_manage', 'wf_expression', '流程表达式', 'expression', 'workflow/expression/index', 'wf:expression:list', 'C', 'MagicStick', 6),
    ('wf_manage', 'wf_instance', '流程实例', 'instance', 'workflow/instance/index', 'wf:instance:list', 'C', 'List', 7),
    ('wf_manage', 'wf_task_admin', '流程任务', 'task', 'workflow/task/index', 'wf:task:list', 'C', 'Tickets', 8),
    ('workflow', 'wf_center', '审批中心', 'center', '', '', 'M', 'Promotion', 2),  # 二级目录
    # 审批中心二级目录：业务用户自助页面（发起、我的流程、待办、已办、抄送）
    ('wf_center', 'wf_start', '发起流程', 'start', 'workflow/start/index', 'wf:start:create', 'C', 'Promotion', 1),
    ('wf_center', 'wf_my', '我的流程', 'my', 'workflow/my/index', 'wf:instance:my', 'C', 'Files', 2),
    ('wf_center', 'wf_todo', '待办任务', 'todo', 'workflow/todo/index', 'wf:task:todo', 'C', 'AlarmClock', 3),
    ('wf_center', 'wf_done', '已办任务', 'done', 'workflow/done/index', 'wf:task:done', 'C', 'Finished', 4),
    ('wf_center', 'wf_cc', '抄送我的', 'cc', 'workflow/cc/index', 'wf:cc:mine', 'C', 'ChatDotRound', 5),
    ('workflow', 'wf_oa', 'OA示例', 'oa', '', '', 'M', 'DocumentAdd', 3),  # 二级目录
    # OA 示例二级目录：请假单据查询页（复用实例列表数据做演示）
    ('wf_oa', 'wf_leave', '请假查询', 'leave', 'workflow/leave/index', 'wf:instance:list', 'C', 'Clock', 1),
]

# 按钮权限：菜单 key -> [(按钮名称, 权限标识)]
BUTTONS = {
    'wf_category': [('查询', 'wf:category:list'), ('新增', 'wf:category:create'),
                    ('编辑', 'wf:category:update'), ('删除', 'wf:category:delete')],
    'wf_model': [('查询', 'wf:model:list'), ('新增', 'wf:model:create'), ('编辑', 'wf:model:update'),
                 ('删除', 'wf:model:delete'), ('发布', 'wf:model:publish')],
    'wf_form': [('查询', 'wf:form:list'), ('新增', 'wf:form:create'),
                ('编辑', 'wf:form:update'), ('删除', 'wf:form:delete')],
    'wf_group': [('查询', 'wf:group:list'), ('新增', 'wf:group:create'),
                 ('编辑', 'wf:group:update'), ('删除', 'wf:group:delete')],
    'wf_listener': [('查询', 'wf:listener:list'), ('新增', 'wf:listener:create'),
                    ('编辑', 'wf:listener:update'), ('删除', 'wf:listener:delete')],
    'wf_expression': [('查询', 'wf:expression:list'), ('新增', 'wf:expression:create'),
                      ('编辑', 'wf:expression:update'), ('删除', 'wf:expression:delete')],
    'wf_instance': [('查询', 'wf:instance:list'), ('终止', 'wf:instance:terminate')],  # 实例监控：查询与强制终止
    'wf_task_admin': [('查询', 'wf:task:list'), ('转派', 'wf:task:transfer')],  # 管理员任务：查询与转派
    'wf_start': [('发起', 'wf:start:create')],  # 发起流程按钮
    'wf_my': [('查询', 'wf:instance:my'), ('撤回', 'wf:instance:withdraw')],  # 我的流程：查询与撤回
    'wf_todo': [('查询', 'wf:task:todo'), ('同意', 'wf:task:approve'), ('驳回', 'wf:task:reject'),
                ('转审', 'wf:task:transfer'), ('加签', 'wf:task:addsign'), ('退回', 'wf:task:back')],
    'wf_done': [('查询', 'wf:task:done')],  # 已办任务查询
    'wf_cc': [('查询', 'wf:cc:mine')],  # 抄送我的查询
    'wf_leave': [('查询', 'wf:instance:list')],  # 请假单据查询
}


def _ensure_menu(SysMenu, parent_id, name, path, component, perms, mtype, icon, order):
    """按父级+名称幂等创建菜单，返回菜单行。"""
    row = SysMenu.objects.filter(parent_id=parent_id, menu_name=name, is_deleted=0).first()  # 已存在则复用
    if row:
        return row
    now = time.strftime('%Y-%m-%d %H:%M:%S')  # 创建时间
    return SysMenu.objects.create(
        parent_id=parent_id, menu_name=name, path=path, component=component, perms=perms,
        menu_type=mtype, icon=icon, order_num=order, visible='0', status='0',
        create_by='admin', create_time=now, update_by='admin', update_time=now, is_deleted=0)


def init_menus():
    """写入工作流程三级菜单与按钮，并授权给超级管理员角色。"""
    from django.db import connection  # 授权需要原生 SQL 的 INSERT IGNORE
    from apps.system.models import SysMenu, SysRole  # 菜单与角色模型

    menu_ids = {}  # key -> 菜单 ID
    created_ids = []  # 本次涉及的全部菜单 ID（含按钮）
    for parent_key, key, name, path, component, perms, mtype, icon, order in MENUS:
        parent_id = menu_ids.get(parent_key, 0) if parent_key else 0  # 解析父级 ID
        row = _ensure_menu(SysMenu, parent_id, name, path, component, perms, mtype, icon, order)  # 建菜单
        menu_ids[key] = row.id  # 记录映射
        created_ids.append(row.id)
        for btn_name, btn_perms in BUTTONS.get(key, []):  # 建按钮
            btn = _ensure_menu(SysMenu, row.id, btn_name, '', '', btn_perms, 'F', '', 0)
            created_ids.append(btn.id)
    role_ids = list(SysRole.objects.filter(is_deleted=0).values_list('id', flat=True))  # 全部启用角色
    with connection.cursor() as cursor:  # 批量授权
        for role_id in role_ids:  # 每个角色都授权工作流菜单，便于业务账号使用审批中心
            for menu_id in created_ids:  # 逐个菜单
                cursor.execute('INSERT IGNORE INTO sys_role_menu (role_id, menu_id) VALUES (%s, %s)',
                               [role_id, menu_id])
    return menu_ids


def _leave_xml():
    """请假流程 BPMN：开始 → 部门主管审批 → 天数判断 → 总监审批/结束。"""
    return '''<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI" xmlns:dc="http://www.omg.org/spec/DD/20100524/DC" xmlns:di="http://www.omg.org/spec/DD/20100524/DI" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" id="Definitions_Leave" targetNamespace="http://bpmn.io/schema/bpmn">
  <bpmn:process id="leave_process" name="请假流程" isExecutable="true">
    <bpmn:startEvent id="StartEvent_Leave" name="开始">
      <bpmn:outgoing>Flow_Leave_1</bpmn:outgoing>
    </bpmn:startEvent>
    <bpmn:userTask id="Task_Manager" name="部门主管审批">
      <bpmn:incoming>Flow_Leave_1</bpmn:incoming>
      <bpmn:outgoing>Flow_Leave_2</bpmn:outgoing>
    </bpmn:userTask>
    <bpmn:exclusiveGateway id="Gateway_Days" name="请假天数判断" default="Flow_Leave_4">
      <bpmn:incoming>Flow_Leave_2</bpmn:incoming>
      <bpmn:outgoing>Flow_Leave_3</bpmn:outgoing>
      <bpmn:outgoing>Flow_Leave_4</bpmn:outgoing>
    </bpmn:exclusiveGateway>
    <bpmn:userTask id="Task_Director" name="总监审批">
      <bpmn:incoming>Flow_Leave_3</bpmn:incoming>
      <bpmn:outgoing>Flow_Leave_5</bpmn:outgoing>
    </bpmn:userTask>
    <bpmn:endEvent id="EndEvent_Leave" name="结束">
      <bpmn:incoming>Flow_Leave_4</bpmn:incoming>
      <bpmn:incoming>Flow_Leave_5</bpmn:incoming>
    </bpmn:endEvent>
    <bpmn:sequenceFlow id="Flow_Leave_1" sourceRef="StartEvent_Leave" targetRef="Task_Manager" />
    <bpmn:sequenceFlow id="Flow_Leave_2" sourceRef="Task_Manager" targetRef="Gateway_Days" />
    <bpmn:sequenceFlow id="Flow_Leave_3" name="大于3天" sourceRef="Gateway_Days" targetRef="Task_Director">
      <bpmn:conditionExpression xsi:type="bpmn:tFormalExpression">${form.leaveDays &gt; 3}</bpmn:conditionExpression>
    </bpmn:sequenceFlow>
    <bpmn:sequenceFlow id="Flow_Leave_4" name="3天及以内" sourceRef="Gateway_Days" targetRef="EndEvent_Leave" />
    <bpmn:sequenceFlow id="Flow_Leave_5" sourceRef="Task_Director" targetRef="EndEvent_Leave" />
  </bpmn:process>
  <bpmndi:BPMNDiagram id="BPMNDiagram_Leave">
    <bpmndi:BPMNPlane id="BPMNPlane_Leave" bpmnElement="leave_process">
      <bpmndi:BPMNShape id="StartEvent_Leave_di" bpmnElement="StartEvent_Leave">
        <dc:Bounds x="160" y="222" width="36" height="36" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="Task_Manager_di" bpmnElement="Task_Manager">
        <dc:Bounds x="250" y="200" width="100" height="80" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="Gateway_Days_di" bpmnElement="Gateway_Days" isMarkerVisible="true">
        <dc:Bounds x="410" y="215" width="50" height="50" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="Task_Director_di" bpmnElement="Task_Director">
        <dc:Bounds x="520" y="320" width="100" height="80" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="EndEvent_Leave_di" bpmnElement="EndEvent_Leave">
        <dc:Bounds x="720" y="222" width="36" height="36" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNEdge id="Flow_Leave_1_di" bpmnElement="Flow_Leave_1">
        <di:waypoint x="196" y="240" />
        <di:waypoint x="250" y="240" />
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="Flow_Leave_2_di" bpmnElement="Flow_Leave_2">
        <di:waypoint x="350" y="240" />
        <di:waypoint x="410" y="240" />
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="Flow_Leave_3_di" bpmnElement="Flow_Leave_3">
        <di:waypoint x="435" y="265" />
        <di:waypoint x="435" y="360" />
        <di:waypoint x="520" y="360" />
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="Flow_Leave_4_di" bpmnElement="Flow_Leave_4">
        <di:waypoint x="460" y="240" />
        <di:waypoint x="720" y="240" />
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="Flow_Leave_5_di" bpmnElement="Flow_Leave_5">
        <di:waypoint x="620" y="360" />
        <di:waypoint x="738" y="360" />
        <di:waypoint x="738" y="258" />
      </bpmndi:BPMNEdge>
    </bpmndi:BPMNPlane>
  </bpmndi:BPMNDiagram>
</bpmn:definitions>'''


def _expense_xml():
    """报销流程 BPMN：开始 → 财务审批 → 结束。"""
    return '''<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI" xmlns:dc="http://www.omg.org/spec/DD/20100524/DC" xmlns:di="http://www.omg.org/spec/DD/20100524/DI" id="Definitions_Expense" targetNamespace="http://bpmn.io/schema/bpmn">
  <bpmn:process id="expense_process" name="报销流程" isExecutable="true">
    <bpmn:startEvent id="StartEvent_Expense" name="开始">
      <bpmn:outgoing>Flow_Expense_1</bpmn:outgoing>
    </bpmn:startEvent>
    <bpmn:userTask id="Task_Finance" name="财务审批">
      <bpmn:incoming>Flow_Expense_1</bpmn:incoming>
      <bpmn:outgoing>Flow_Expense_2</bpmn:outgoing>
    </bpmn:userTask>
    <bpmn:endEvent id="EndEvent_Expense" name="结束">
      <bpmn:incoming>Flow_Expense_2</bpmn:incoming>
    </bpmn:endEvent>
    <bpmn:sequenceFlow id="Flow_Expense_1" sourceRef="StartEvent_Expense" targetRef="Task_Finance" />
    <bpmn:sequenceFlow id="Flow_Expense_2" sourceRef="Task_Finance" targetRef="EndEvent_Expense" />
  </bpmn:process>
  <bpmndi:BPMNDiagram id="BPMNDiagram_Expense">
    <bpmndi:BPMNPlane id="BPMNPlane_Expense" bpmnElement="expense_process">
      <bpmndi:BPMNShape id="StartEvent_Expense_di" bpmnElement="StartEvent_Expense">
        <dc:Bounds x="170" y="222" width="36" height="36" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="Task_Finance_di" bpmnElement="Task_Finance">
        <dc:Bounds x="270" y="200" width="100" height="80" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="EndEvent_Expense_di" bpmnElement="EndEvent_Expense">
        <dc:Bounds x="440" y="222" width="36" height="36" />
      </bpmndi:BPMNShape>
      <bpmndi:BPMNEdge id="Flow_Expense_1_di" bpmnElement="Flow_Expense_1">
        <di:waypoint x="206" y="240" />
        <di:waypoint x="270" y="240" />
      </bpmndi:BPMNEdge>
      <bpmndi:BPMNEdge id="Flow_Expense_2_di" bpmnElement="Flow_Expense_2">
        <di:waypoint x="370" y="240" />
        <di:waypoint x="440" y="240" />
      </bpmndi:BPMNEdge>
    </bpmndi:BPMNPlane>
  </bpmndi:BPMNDiagram>
</bpmn:definitions>'''


LEAVE_FIELDS = [  # 请假演示表单字段：key 需与流程表达式、form_data 取值保持一致
    # 请假类型：下拉单选，限定四种假别
    {'key': 'leaveType', 'label': '请假类型', 'type': 'select', 'required': True,
     'options': ['事假', '病假', '年假', '调休'], 'placeholder': '请选择请假类型'},
    # 开始日期：日期选择，用于单据展示
    {'key': 'startDate', 'label': '开始日期', 'type': 'date', 'required': True, 'placeholder': '请选择开始日期'},
    # 结束日期：日期选择，用于单据展示
    {'key': 'endDate', 'label': '结束日期', 'type': 'date', 'required': True, 'placeholder': '请选择结束日期'},
    # 请假天数：数字输入，排他网关条件 ${form.leaveDays > 3} 依赖该字段
    {'key': 'leaveDays', 'label': '请假天数', 'type': 'number', 'required': True, 'placeholder': '请输入请假天数'},
    # 请假事由：多行文本，审批人判断依据
    {'key': 'reason', 'label': '请假事由', 'type': 'textarea', 'required': True, 'placeholder': '请输入请假事由'},
    # 附件地址：文件字段，非必填
    {'key': 'attachment', 'label': '附件地址', 'type': 'file', 'required': False, 'placeholder': '请输入附件地址'},
]

EXPENSE_FIELDS = [  # 报销演示表单字段：结构与请假表单一致，提交时按 key 校验必填
    # 报销类型：下拉单选，限定费用科目
    {'key': 'expenseType', 'label': '报销类型', 'type': 'select', 'required': True,
     'options': ['差旅费', '办公用品', '招待费', '其他'], 'placeholder': '请选择报销类型'},
    # 报销金额：数字输入，供财务核对
    {'key': 'amount', 'label': '报销金额（元）', 'type': 'number', 'required': True, 'placeholder': '请输入报销金额'},
    # 发生日期：日期选择，用于财务归档
    {'key': 'expenseDate', 'label': '发生日期', 'type': 'date', 'required': True, 'placeholder': '请选择发生日期'},
    # 报销说明：多行文本，说明费用用途
    {'key': 'reason', 'label': '报销说明', 'type': 'textarea', 'required': True, 'placeholder': '请输入报销说明'},
    # 发票地址：文件字段，非必填
    {'key': 'attachment', 'label': '发票地址', 'type': 'file', 'required': False, 'placeholder': '请输入发票地址'},
]


def _ensure_category():
    """确保 OA 审批分类存在。"""
    row = WfCategory.objects.filter(code='oa', is_deleted=0).first()  # 按编码查询
    if row:
        return row
    now = time.strftime('%Y-%m-%d %H:%M:%S')  # 创建时间
    return WfCategory.objects.create(name='OA审批', code='oa', sort=1, status=1, remark='日常办公审批流程',
                                     create_by='admin', create_time=now, update_by='admin',
                                     update_time=now, is_deleted=0)


def _ensure_form(form_name, form_key, fields):
    """确保表单存在并保持字段配置最新。"""
    row = WfForm.objects.filter(form_key=form_key, is_deleted=0).first()  # 按唯一标识查询
    now = time.strftime('%Y-%m-%d %H:%M:%S')  # 当前时间
    form_json = json.dumps(fields, ensure_ascii=False)  # 字段配置 JSON
    if row:  # 已存在则更新字段，便于修复演示数据
        WfForm.objects.filter(id=row.id).update(form_json=form_json, update_time=now)
        row.form_json = form_json
        return row
    return WfForm.objects.create(form_name=form_name, form_key=form_key, form_json=form_json,
                                 status=0, remark='演示表单', create_by='admin', create_time=now,
                                 update_by='admin', update_time=now, is_deleted=0)


def _ensure_group(group_name, group_code, user_ids):
    """确保用户分组存在并写入成员。"""
    row = WfGroup.objects.filter(group_code=group_code, is_deleted=0).first()  # 按编码查询
    now = time.strftime('%Y-%m-%d %H:%M:%S')  # 当前时间
    if not row:  # 不存在则创建
        row = WfGroup.objects.create(group_name=group_name, group_code=group_code, status=0,
                                     remark='演示分组', create_by='admin', create_time=now,
                                     update_by='admin', update_time=now, is_deleted=0)
    existing = set(WfGroupUser.objects.filter(group_id=row.id).values_list('user_id', flat=True))  # 现有成员
    for uid in user_ids:  # 补齐成员
        if uid not in existing:
            WfGroupUser.objects.create(group_id=row.id, user_id=uid, create_time=now)
    return row


def _ensure_model(name, key, category_id, form_id, xml, node_config, remark):
    """确保流程模型存在；已存在时同步 XML 与节点配置。"""
    row = WfModel.objects.filter(model_key=key, is_deleted=0).first()  # 按 Key 查询
    now = time.strftime('%Y-%m-%d %H:%M:%S')  # 当前时间
    cfg_text = json.dumps(node_config, ensure_ascii=False)  # 节点配置 JSON
    if row:  # 已存在则同步演示配置
        WfModel.objects.filter(id=row.id).update(bpmn_xml=xml, node_config=cfg_text,
                                                 category_id=category_id, form_id=form_id,
                                                 update_time=now)
        return row
    return WfModel.objects.create(model_name=name, model_key=key, category_id=category_id,
                                  form_id=form_id, bpmn_xml=xml, node_config=cfg_text,
                                  version=1, status=1, process_status=0, remark=remark,
                                  create_by='admin', create_time=now, update_by='admin',
                                  update_time=now, is_deleted=0)


def seed_workflow():
    """初始化工作流菜单与演示数据（菜单、分类、表单、分组、流程模型、表达式、监听器）。"""
    init_menus()  # 先建菜单与按钮权限
    category = _ensure_category()  # OA 分类
    leave_form = _ensure_form('请假申请单', 'leave_form', LEAVE_FIELDS)  # 请假表单
    expense_form = _ensure_form('报销申请单', 'expense_form', EXPENSE_FIELDS)  # 报销表单
    manager_group = _ensure_group('部门主管组', 'manager_group', [2])  # 部门主管组（zhangsan）
    finance_group = _ensure_group('财务审批组', 'finance_group', [1])  # 财务组（admin）
    leave_cfg = {
        'Task_Manager': {'assigneeType': 'group', 'groupId': manager_group.id,
                         'approveMode': 2, 'dueHours': 24, 'ccUserIds': []},
        'Task_Director': {'assigneeType': 'role', 'roleIds': [1],
                          'approveMode': 2, 'dueHours': 48, 'ccUserIds': [2]},
    }  # 主管组审批，超过 3 天走 admin 角色审批并抄送 zhangsan
    expense_cfg = {
        'Task_Finance': {'assigneeType': 'group', 'groupId': finance_group.id,
                         'approveMode': 2, 'dueHours': 24, 'ccUserIds': [2]},
    }  # 财务组审批并抄送 zhangsan
    leave_model = _ensure_model('请假流程', 'leave', category.id, leave_form.id,
                                _leave_xml(), leave_cfg, 'OA 请假审批演示流程')  # 请假模型
    _ensure_model('报销流程', 'expense', category.id, expense_form.id,
                  _expense_xml(), expense_cfg, 'OA 报销审批演示流程')  # 报销模型
    if not WfExpression.objects.filter(expr_code='leave_days_gt3', is_deleted=0).exists():  # 表达式示例
        now = time.strftime('%Y-%m-%d %H:%M:%S')  # 当前时间
        WfExpression.objects.create(expr_name='请假天数大于3天', expr_code='leave_days_gt3',
                                    expr_content='${form.leaveDays > 3}', expr_type='condition',
                                    remark='超过 3 天需要总监审批', create_by='admin', create_time=now,
                                    update_by='admin', update_time=now, is_deleted=0)
    if not WfListener.objects.filter(model_id=leave_model.id, event_type='start',
                                     action_type='notify', is_deleted=0).exists():  # 监听器示例
        now = time.strftime('%Y-%m-%d %H:%M:%S')  # 当前时间
        WfListener.objects.create(model_id=leave_model.id, event_type='start', action_type='notify',
                                  callback_url='', callback_param='{"msg":"流程已启动"}', status=0,
                                  create_by='admin', create_time=now, update_by='admin',
                                  update_time=now, is_deleted=0)
    return {'category': category.id, 'leave_model': leave_model.id}  # 返回关键 ID 便于排查
