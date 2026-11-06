"""工作流初始化：菜单（三级）、按钮权限、请假/报销演示流程与示例数据（幂等可重复执行）。"""
# 模块：apps/workflow/seed.py —— 工作流（OA 审批）模块的种子数据初始化脚本
# 用途：写入工作流三级菜单与按钮权限，并准备请假/报销两套演示流程所需的分类、表单、审批分组、
#       BPMN 流程模型、条件表达式与监听器，使系统初始化后即可直接体验审批全流程。
# 调用方：core/management/commands/init_db.py（以及 seed_new_modules.py）在初始化数据库时调用 seed_workflow()。
# 幂等性：菜单按「父级 + 名称 + 未删除」判重、授权用 INSERT IGNORE；
#         分类/表单/分组/模型按业务唯一键（code/form_key/group_code/model_key）查询后复用或更新；
#         表达式与监听器先查存在再创建，因此反复执行不会产生重复业务数据。
# 涉及数据表：sys_menu（三级菜单与按钮）、sys_role_menu（角色-菜单授权）、
#             wf_category、wf_form、wf_group、wf_group_user、wf_model、wf_expression、wf_listener。
# 说明：BPMN XML 与表单配置 JSON 均为字符串演示数据，字符串内容需与前端流程设计器/表单渲染器保持一致，请勿随手改动。
import json  # 表单与节点配置序列化
import time  # 写入时间字符串

# 引入工作流模块用到的全部模型：分类、表达式、表单、用户分组、分组成员、监听器、流程模型
# 一次导入可减少下方多次局部 import 的开销，且这些模型在本脚本中都会被读写
from apps.workflow.models import (
    WfCategory, WfExpression, WfForm, WfGroup, WfGroupUser, WfListener, WfModel)  # 工作流模型


# 菜单定义：(父 key, key, 名称, 路由, 组件, 权限, 类型, 图标, 排序)
# 每行含义：父级 key、本级 key、菜单名称、路由 path、前端组件、权限标识、类型、图标、排序
# 类型取值：M=目录（仅分组不渲染页面）、C=菜单页面（component 指向前端页面）、F=按钮权限
# 父级 key 为 None 表示顶级菜单；本数据为「顶级目录 → 二级目录 → 页面」的三级结构
MENUS = [
    # 一级目录：工作流程，路由 workflow、图标 Share、排序 3；空权限/空组件表示仅作容器
    (None, 'workflow', '工作流程', 'workflow', '', '', 'M', 'Share', 3),  # 一级目录
    # 二级目录：流程管理（管理员配置入口），排在其父级目录下第 1 位
    ('workflow', 'wf_manage', '流程管理', 'manage', '', '', 'M', 'SetUp', 1),  # 二级目录
    # 流程管理二级目录：配置类页面（分类、模型、表单、分组、监听器、表达式、实例、任务）
    # 流程分类页：维护「OA审批/财务审批」等分类字典，列表权限 wf:category:list
    ('wf_manage', 'wf_category', '流程分类', 'category', 'workflow/category/index', 'wf:category:list', 'C', 'CollectionTag', 1),
    # 流程模型页：用 bpmn-js 设计、发布流程定义，种子写入请假/报销两个模型
    ('wf_manage', 'wf_model', '流程模型', 'model', 'workflow/model/index', 'wf:model:list', 'C', 'Share', 2),
    # 流程表单页：维护表单字段 JSON（请假单、报销单的字段由 LEAVE_FIELDS/EXPENSE_FIELDS 生成）
    ('wf_manage', 'wf_form', '流程表单', 'form', 'workflow/form/index', 'wf:form:list', 'C', 'Document', 3),
    # 用户分组页：把若干用户组成固定审批组（种子里建 manager_group、finance_group）
    ('wf_manage', 'wf_group', '用户分组', 'group', 'workflow/group/index', 'wf:group:list', 'C', 'UserFilled', 4),
    # 流程监听器页：配置流程事件（start/end 等）触发的通知或回调动作
    ('wf_manage', 'wf_listener', '流程监听器', 'listener', 'workflow/listener/index', 'wf:listener:list', 'C', 'Bell', 5),
    # 流程表达式页：维护网关条件表达式（如 ${form.leaveDays > 3}）
    ('wf_manage', 'wf_expression', '流程表达式', 'expression', 'workflow/expression/index', 'wf:expression:list', 'C', 'MagicStick', 6),
    # 流程实例页：管理员视角查看全部实例，权限含强制终止
    ('wf_manage', 'wf_instance', '流程实例', 'instance', 'workflow/instance/index', 'wf:instance:list', 'C', 'List', 7),
    # 流程任务页：管理员视角查看全部待办，权限含转派
    ('wf_manage', 'wf_task_admin', '流程任务', 'task', 'workflow/task/index', 'wf:task:list', 'C', 'Tickets', 8),
    # 二级目录：审批中心（业务用户自助入口），排序 2
    ('workflow', 'wf_center', '审批中心', 'center', '', '', 'M', 'Promotion', 2),  # 二级目录
    # 审批中心二级目录：业务用户自助页面（发起、我的流程、待办、已办、抄送）
    # 发起流程页：展示可发起的已发布模型并填写表单，权限 wf:start:create
    ('wf_center', 'wf_start', '发起流程', 'start', 'workflow/start/index', 'wf:start:create', 'C', 'Promotion', 1),
    # 我的流程页：查看自己发起的实例，权限含撤回
    ('wf_center', 'wf_my', '我的流程', 'my', 'workflow/my/index', 'wf:instance:my', 'C', 'Files', 2),
    # 待办任务页：当前用户待审批任务，权限含同意/驳回/转审/加签/退回
    ('wf_center', 'wf_todo', '待办任务', 'todo', 'workflow/todo/index', 'wf:task:todo', 'C', 'AlarmClock', 3),
    # 已办任务页：当前用户处理过的任务历史
    ('wf_center', 'wf_done', '已办任务', 'done', 'workflow/done/index', 'wf:task:done', 'C', 'Finished', 4),
    # 抄送我的页：我收到抄送的单据，只能查看
    ('wf_center', 'wf_cc', '抄送我的', 'cc', 'workflow/cc/index', 'wf:cc:mine', 'C', 'ChatDotRound', 5),
    # 二级目录：OA示例（演示单据的查询入口），排序 3
    ('workflow', 'wf_oa', 'OA示例', 'oa', '', '', 'M', 'DocumentAdd', 3),  # 二级目录
    # OA 示例二级目录：请假单据查询页（复用实例列表数据做演示）
    # 请假查询页：按请假单维度展示实例数据，直接复用实例列表权限
    ('wf_oa', 'wf_leave', '请假查询', 'leave', 'workflow/leave/index', 'wf:instance:list', 'C', 'Clock', 1),
]

# 按钮权限：菜单 key -> [(按钮名称, 权限标识)]
# 初始化时按所属页面挂成 F 类型子菜单；权限标识由前端按钮级鉴权使用，命名规则为「模块:资源:动作」
BUTTONS = {
    # 流程分类：标准增删改查四个按钮
    'wf_category': [('查询', 'wf:category:list'), ('新增', 'wf:category:create'),
                    ('编辑', 'wf:category:update'), ('删除', 'wf:category:delete')],
    # 流程模型：增删改查之外增加「发布」按钮，发布后版本号 +1 并生效
    'wf_model': [('查询', 'wf:model:list'), ('新增', 'wf:model:create'), ('编辑', 'wf:model:update'),
                 ('删除', 'wf:model:delete'), ('发布', 'wf:model:publish')],
    # 流程表单：增删改查四个按钮
    'wf_form': [('查询', 'wf:form:list'), ('新增', 'wf:form:create'),
                ('编辑', 'wf:form:update'), ('删除', 'wf:form:delete')],
    # 用户分组：增删改查四个按钮
    'wf_group': [('查询', 'wf:group:list'), ('新增', 'wf:group:create'),
                 ('编辑', 'wf:group:update'), ('删除', 'wf:group:delete')],
    # 流程监听器：增删改查四个按钮
    'wf_listener': [('查询', 'wf:listener:list'), ('新增', 'wf:listener:create'),
                    ('编辑', 'wf:listener:update'), ('删除', 'wf:listener:delete')],
    # 流程表达式：增删改查四个按钮
    'wf_expression': [('查询', 'wf:expression:list'), ('新增', 'wf:expression:create'),
                      ('编辑', 'wf:expression:update'), ('删除', 'wf:expression:delete')],
    # 实例监控：仅有查询与强制终止，不提供新增/编辑业务单据
    'wf_instance': [('查询', 'wf:instance:list'), ('终止', 'wf:instance:terminate')],  # 实例监控：查询与强制终止
    # 管理员任务：查询全部任务并把任务转派给其他人
    'wf_task_admin': [('查询', 'wf:task:list'), ('转派', 'wf:task:transfer')],  # 管理员任务：查询与转派
    # 发起流程：业务用户从已发布模型中发起一个新实例
    'wf_start': [('发起', 'wf:start:create')],  # 发起流程按钮
    # 我的流程：查看自己发起的实例；流程仍在运行时允许撤回
    'wf_my': [('查询', 'wf:instance:my'), ('撤回', 'wf:instance:withdraw')],  # 我的流程：查询与撤回
    # 待办任务：审批人可执行的六种动作（同意、驳回、转审、加签、退回、查询）
    'wf_todo': [('查询', 'wf:task:todo'), ('同意', 'wf:task:approve'), ('驳回', 'wf:task:reject'),
                ('转审', 'wf:task:transfer'), ('加签', 'wf:task:addsign'), ('退回', 'wf:task:back')],
    # 已办任务：只提供查询
    'wf_done': [('查询', 'wf:task:done')],  # 已办任务查询
    # 抄送我的：只提供查询，抄送件不可审批
    'wf_cc': [('查询', 'wf:cc:mine')],  # 抄送我的查询
    # 请假查询：复用实例列表权限，仅做只读展示
    'wf_leave': [('查询', 'wf:instance:list')],  # 请假单据查询
}


# 幂等创建单条菜单：菜单模型由调用方注入，便于复用同一套逻辑创建菜单与按钮
# 幂等键为「父级 ID + 菜单名称 + 未删除」，重复执行不会产生重复菜单
def _ensure_menu(SysMenu, parent_id, name, path, component, perms, mtype, icon, order):
    # 作用：按「父级 + 名称 + 未删除」判重创建菜单，已存在则复用，不存在才插入
    """按父级+名称幂等创建菜单，返回菜单行。"""
    # 先查是否已存在同父级同名的有效菜单，命中直接复用（保留原 ID，授权也沿用）
    row = SysMenu.objects.filter(parent_id=parent_id, menu_name=name, is_deleted=0).first()  # 已存在则复用
    # 已存在则不再插入，直接返回，保证种子可重复执行
    if row:
        # 命中重复：直接复用已有菜单，跳过创建
        return row
    # 统一使用字符串格式的当前时间，与其它模块种子的时间字段保持一致
    now = time.strftime('%Y-%m-%d %H:%M:%S')  # 创建时间
    # 不存在才创建：父级决定菜单层级，menu_type 区分目录/页面/按钮
    return SysMenu.objects.create(
        # 基础属性：父级、名称、路由、前端组件与权限标识
        parent_id=parent_id, menu_name=name, path=path, component=component, perms=perms,
        # visible='0' 显示、status='0' 启用；order_num 控制同级排序
        menu_type=mtype, icon=icon, order_num=order, visible='0', status='0',
        # 审计字段统一记 admin：种子数据无真实登录用户；is_deleted=0 表示未删除
        create_by='admin', create_time=now, update_by='admin', update_time=now, is_deleted=0)


# 菜单初始化入口：先按 MENUS 顺序建目录/页面，再给每个页面补按钮，最后统一授权给全部有效角色
def init_menus():
    # 作用：按 MENUS/BUTTONS 定义建菜单树与按钮，并把全部 ID 授权给所有有效角色
    """写入工作流程三级菜单与按钮，并授权给超级管理员角色。"""
    # 延迟导入：仅本函数需要数据库连接（批量授权走原生 SQL），模块加载期不需要
    from django.db import connection  # 授权需要原生 SQL 的 INSERT IGNORE
    # 延迟导入系统模型，避免与系统模块的初始化顺序产生循环依赖
    from apps.system.models import SysMenu, SysRole  # 菜单与角色模型

    # key -> 菜单 ID 映射：子菜单靠父级 key 反查父级 ID，保证三级结构正确挂载
    menu_ids = {}  # key -> 菜单 ID
    # 收集本次涉及的全部菜单/按钮 ID，最后一次性授权
    created_ids = []  # 本次涉及的全部菜单 ID（含按钮）
    # 按定义顺序遍历：MENUS 中父级总排在子级之前，因此可边建边解析父级
    for parent_key, key, name, path, component, perms, mtype, icon, order in MENUS:
        # 顶级菜单父级固定为 0；子菜单从已建好的映射中取父级 ID
        parent_id = menu_ids.get(parent_key, 0) if parent_key else 0  # 解析父级 ID
        # 幂等创建菜单行（目录 M 或页面 C），已存在则复用
        row = _ensure_menu(SysMenu, parent_id, name, path, component, perms, mtype, icon, order)  # 建菜单
        # 记录本级 key 与 ID，供其子级使用
        menu_ids[key] = row.id  # 记录映射
        # 菜单本身也纳入授权集合
        created_ids.append(row.id)
        # 若该菜单在 BUTTONS 中有定义则继续创建按钮；无定义时 get 返回空列表
        for btn_name, btn_perms in BUTTONS.get(key, []):  # 建按钮
            # 按钮挂在该页面的 ID 下；类型 F 表示按钮权限，无路由/组件，排序 0
            btn = _ensure_menu(SysMenu, row.id, btn_name, '', '', btn_perms, 'F', '', 0)
            # 按钮同样需要授权，加入集合
            created_ids.append(btn.id)
    # 查询全部未删除角色的 ID：默认把工作流菜单授权给所有角色，方便各业务账号直接体验
    role_ids = list(SysRole.objects.filter(is_deleted=0).values_list('id', flat=True))  # 全部启用角色
    # 使用原生游标批量写关联表，减少 ORM 逐条插入的开销
    with connection.cursor() as cursor:  # 批量授权
        # 外层遍历角色：角色 × 菜单 的笛卡尔积逐行写入
        for role_id in role_ids:  # 每个角色都授权工作流菜单，便于业务账号使用审批中心
            # 内层遍历本次创建的菜单与按钮
            for menu_id in created_ids:  # 逐个菜单
                # INSERT IGNORE：已存在的 (role_id, menu_id) 行被忽略，保证重复执行幂等且不报错
                cursor.execute('INSERT IGNORE INTO sys_role_menu (role_id, menu_id) VALUES (%s, %s)',
                               # 参数顺序与占位符一一对应：先角色后菜单
                               [role_id, menu_id])
    # 返回 key→ID 映射，方便调用方/排查时定位菜单
    return menu_ids


# 请假流程 BPMN 定义：返回 bpmn-js 可解析的 XML 字符串，最终写入 wf_model.bpmn_xml 字段
# 业务节点：StartEvent_Leave（开始）→ Task_Manager（部门主管审批）
#           → Gateway_Days（排他网关：请假天数判断）
#           → Task_Director（总监审批，仅 >3 天时进入）→ EndEvent_Leave（结束）
# 连线：Flow_Leave_1 开始→主管；Flow_Leave_2 主管→网关；
#       Flow_Leave_3 网关→总监，条件表达式 ${form.leaveDays > 3}（请假天数大于 3 天）；
#       Flow_Leave_4 网关→结束，为网关 default 默认分支（3 天及以内直接结束）；
#       Flow_Leave_5 总监→结束
# 后半段 BPMNDiagram / BPMNPlane 只是画布的图形坐标（BPMNShape 的 Bounds、BPMNEdge 的 waypoint），
# 不影响流程语义；保留它们是为了让流程图打开时节点位置固定、可读
def _leave_xml():
    # 作用：返回请假流程的 BPMN XML 原文，供模型表 bpmn_xml 字段与前端设计器使用
    """请假流程 BPMN：开始 → 部门主管审批 → 天数判断 → 总监审批/结束。"""
    # 下面是 XML 原文：包含 definitions → process → 各事件/任务/网关/连线 → 图形定义，内容不可改动
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


# 报销流程 BPMN 定义：较请假流程更简单，只有「开始 → 财务审批 → 结束」三个节点
# 节点：StartEvent_Expense（开始）→ Task_Finance（财务审批）→ EndEvent_Expense（结束）
# 连线：Flow_Expense_1（开始→财务审批）、Flow_Expense_2（财务审批→结束），无网关与条件
# 后半段 BPMNDiagram / BPMNPlane 为图形坐标，供前端画布渲染，不参与流转判断
def _expense_xml():
    # 作用：返回报销流程的 BPMN XML 原文，结构简单，不含网关条件
    """报销流程 BPMN：开始 → 财务审批 → 结束。"""
    # 下面是 XML 原文：结构与请假流程相同，仅节点 ID（Expense 前缀）与图形坐标不同
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


# 请假表单字段定义：列表中的每个元素是一个表单控件，序列化后写入 wf_form.form_json
# 通用属性：key=提交数据 form_data 的字段名（必须与流程表达式引用一致）；
#           label=界面标签；type=控件类型；required=是否必填；options=下拉选项；placeholder=输入提示
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
    # 以上共 6 个字段：类型、开始/结束日期、天数、事由、附件；leaveDays 同时被 BPMN 网关条件和 wf_expression 复用
]

# 报销表单字段定义：结构与 LEAVE_FIELDS 一致，提交时按各字段的 required 做必填校验
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
    # 以上共 5 个字段：报销类型、金额、发生日期、说明、发票；金额为数字类型供汇总统计
]


# 确保「OA审批」分类存在：分类是流程模型的归类维度，请假/报销两个模型都挂到该分类下
# 以唯一编码 code='oa' 作为幂等键查询，已存在直接复用，不做任何更新
def _ensure_category():
    # 作用：按 code='oa' 判重，存在即复用，不存在才插入 OA 审批分类
    """确保 OA 审批分类存在。"""
    # 按唯一编码 + 未删除查询，命中说明之前初始化过
    row = WfCategory.objects.filter(code='oa', is_deleted=0).first()  # 按编码查询
    # 已存在直接返回，避免重复插入触发唯一键冲突
    if row:
        # 已有分类：直接返回，不覆盖已有配置
        return row
    # 统一字符串格式时间
    now = time.strftime('%Y-%m-%d %H:%M:%S')  # 创建时间
    # 创建分类：name=显示名，code=唯一编码，sort=1 排在前面，status=1 表示启用，
    # remark 说明用途；审计字段记 admin，is_deleted=0 未删除
    return WfCategory.objects.create(name='OA审批', code='oa', sort=1, status=1, remark='日常办公审批流程',
                                     # 审计字段：创建/更新人固定 admin，时间为当前时间
                                     create_by='admin', create_time=now, update_by='admin',
                                     # 逻辑删除标记：0 表示未删除
                                     update_time=now, is_deleted=0)


# 确保表单存在并保持字段配置最新：form_key 为幂等键，字段列表序列化为 form_json 存储
# 与分类不同，表单每次执行都会把最新 fields 覆盖写回，便于修改演示字段后重新初始化即可生效
def _ensure_form(form_name, form_key, fields):
    # 作用：按 form_key 查表单；已存在就覆盖 form_json，不存在才插入新表单
    """确保表单存在并保持字段配置最新。"""
    # form_key 是表单唯一标识，按它 + 未删除查询
    row = WfForm.objects.filter(form_key=form_key, is_deleted=0).first()  # 按唯一标识查询
    # 当前时间，用于 create_time / update_time
    now = time.strftime('%Y-%m-%d %H:%M:%S')  # 当前时间
    # 把 Python 列表序列化为 JSON 文本；ensure_ascii=False 保证中文标签原样保存
    form_json = json.dumps(fields, ensure_ascii=False)  # 字段配置 JSON
    if row:  # 已存在则更新字段，便于修复演示数据
        # 已存在则直接 UPDATE 字段 JSON 与更新时间，使演示配置始终与代码定义一致
        WfForm.objects.filter(id=row.id).update(form_json=form_json, update_time=now)
        # 同步内存对象属性，保证返回值的 form_json 是最新的
        row.form_json = form_json
        # 返回已存在的表单行，保持调用方拿到的 ID 不变
        return row
    # 不存在则新建表单：status=0 表示启用，remark 标记为演示表单，审计字段记 admin
    return WfForm.objects.create(form_name=form_name, form_key=form_key, form_json=form_json,
                                 status=0, remark='演示表单', create_by='admin', create_time=now,
                                 # 更新时间与逻辑删除标记：新建时与创建时间一致、未删除
                                 update_by='admin', update_time=now, is_deleted=0)


# 确保用户分组存在并同步成员：group_code 为幂等键，user_ids 为要加入该组的系统用户 ID 列表
# 成员只做「补齐」不做删除，避免把手工加入的成员误删
def _ensure_group(group_name, group_code, user_ids):
    # 作用：按 group_code 查分组；不存在就建组，再把 user_ids 中缺的成员补进关联表
    """确保用户分组存在并写入成员。"""
    # 按分组唯一编码查询未删除的分组
    row = WfGroup.objects.filter(group_code=group_code, is_deleted=0).first()  # 按编码查询
    # 统一时间字符串
    now = time.strftime('%Y-%m-%d %H:%M:%S')  # 当前时间
    if not row:  # 不存在则创建
        # 不存在才建分组：status=0 表示启用，remark 标记演示分组
        row = WfGroup.objects.create(group_name=group_name, group_code=group_code, status=0,
                                     remark='演示分组', create_by='admin', create_time=now,
                                     # 审计与删除标记：新建记录记 admin，未删除
                                     update_by='admin', update_time=now, is_deleted=0)
    # 读取该组现有成员 ID 集合，用于去重，避免重复插入同一成员
    existing = set(WfGroupUser.objects.filter(group_id=row.id).values_list('user_id', flat=True))  # 现有成员
    for uid in user_ids:  # 补齐成员
        # 仅当成员不在现有集合中才插入，保证重复执行结果一致
        if uid not in existing:
            # wf_group_user 只有 group_id/user_id/create_time 三个字段，没有逻辑删除标记
            WfGroupUser.objects.create(group_id=row.id, user_id=uid, create_time=now)
    # 返回分组行，供后续节点配置取 group_id
    return row


# 确保流程模型存在并同步定义：model_key 为幂等键，xml 为 BPMN 字符串，node_config 为节点审批配置字典
# 已存在时覆盖 bpmn_xml / node_config / 关联分类与表单，便于升级演示流程定义；version 保持不变
def _ensure_model(name, key, category_id, form_id, xml, node_config, remark):
    # 作用：按 model_key 查流程模型；已存在则同步 BPMN/节点配置/关联关系，不存在才新建已发布模型
    """确保流程模型存在；已存在时同步 XML 与节点配置。"""
    # 按模型唯一 Key 查询未删除记录（引擎按 model_key 识别流程）
    row = WfModel.objects.filter(model_key=key, is_deleted=0).first()  # 按 Key 查询
    # 统一时间字符串
    now = time.strftime('%Y-%m-%d %H:%M:%S')  # 当前时间
    # 节点配置字典序列化为 JSON；ensure_ascii=False 保留中文说明
    cfg_text = json.dumps(node_config, ensure_ascii=False)  # 节点配置 JSON
    if row:  # 已存在则同步演示配置
        # 已存在则只更新流程定义相关字段：BPMN、节点配置、所属分类与表单、更新时间
        WfModel.objects.filter(id=row.id).update(bpmn_xml=xml, node_config=cfg_text,
                                                 # 同步关联的分类与表单，保证模型引用关系与代码一致
                                                 category_id=category_id, form_id=form_id,
                                                 # 只更新更新时间，创建时间与版本号保持原值
                                                 update_time=now)
        # 返回原行，调用方可继续使用其 id
        return row
    # 不存在则新建：version=1 初始版本，status=1 已发布（发起页只展示已发布模型），
    # process_status=0 表示运行中，remark 记录演示用途
    return WfModel.objects.create(model_name=name, model_key=key, category_id=category_id,
                                  form_id=form_id, bpmn_xml=xml, node_config=cfg_text,
                                  # 初始版本 1、状态 1=已发布、流程状态 0=运行中
                                  version=1, status=1, process_status=0, remark=remark,
                                  # 审计字段：创建/更新人 admin，时间当前
                                  create_by='admin', create_time=now, update_by='admin',
                                  # 逻辑删除标记 0=未删除
                                  update_time=now, is_deleted=0)


# 种子总入口：按依赖顺序初始化工作流全部演示数据，任一子函数均保证可重复执行
# 执行顺序：菜单/按钮 → 分类 → 表单 → 审批分组 → 流程模型（含 BPMN 与节点配置）→ 表达式 → 监听器
def seed_workflow():
    # 作用：工作流模块唯一的对外初始化入口，被 init_db 命令调用；内部各步骤均可重复执行
    """初始化工作流菜单与演示数据（菜单、分类、表单、分组、流程模型、表达式、监听器）。"""
    # 1. 先建菜单与按钮权限并授权，保证登录后能看到工作流入口
    init_menus()  # 先建菜单与按钮权限
    # 2. 创建/复用 OA 审批分类，作为两个流程模型的归属
    category = _ensure_category()  # OA 分类
    # 3. 创建/更新请假表单：form_key='leave_form'，字段来自 LEAVE_FIELDS
    leave_form = _ensure_form('请假申请单', 'leave_form', LEAVE_FIELDS)  # 请假表单
    # 4. 创建/更新报销表单：form_key='expense_form'，字段来自 EXPENSE_FIELDS
    expense_form = _ensure_form('报销申请单', 'expense_form', EXPENSE_FIELDS)  # 报销表单
    # 5. 部门主管审批组：成员写用户 ID 2（演示账号 zhangsan），审批模式由节点配置引用
    manager_group = _ensure_group('部门主管组', 'manager_group', [2])  # 部门主管组（zhangsan）
    # 6. 财务审批组：成员写用户 ID 1（内置超级管理员 admin），用于报销流程财务节点
    finance_group = _ensure_group('财务审批组', 'finance_group', [1])  # 财务组（admin）
    # 请假流程节点配置：key 为 BPMN 中 userTask 的 id，value 描述该节点的审批人来源与办理策略
    # assigneeType：group=按用户分组选人；role=按系统角色选人
    # groupId / roleIds：分别指向分组 ID 与角色 ID；approveMode：1 串行 / 2 或签 / 3 会签
    # dueHours：任务办理时限（小时），供超时提醒/监听使用；ccUserIds：抄送用户 ID 列表
    leave_cfg = {
        # 部门主管审批节点 Task_Manager：由「部门主管组」选人，或签，24 小时内办结，不抄送
        'Task_Manager': {'assigneeType': 'group', 'groupId': manager_group.id,
                         # 或签；24 小时办结；不抄送任何人
                         'approveMode': 2, 'dueHours': 24, 'ccUserIds': []},
        # 总监审批节点 Task_Director：按角色 ID 1（admin 角色）选人，或签，48 小时内办结，抄送用户 2（zhangsan）
        'Task_Director': {'assigneeType': 'role', 'roleIds': [1],
                          # 或签；48 小时办结；抄送用户 2（zhangsan）
                          'approveMode': 2, 'dueHours': 48, 'ccUserIds': [2]},
    }  # 主管组审批，超过 3 天走 admin 角色审批并抄送 zhangsan
    # 报销流程节点配置：只有一个财务审批节点，结构同上
    expense_cfg = {
        # 财务审批节点 Task_Finance：由「财务审批组」选人，或签，24 小时内办结，抄送用户 2（zhangsan）
        'Task_Finance': {'assigneeType': 'group', 'groupId': finance_group.id,
                         # 或签；24 小时办结；抄送用户 2（zhangsan）
                         'approveMode': 2, 'dueHours': 24, 'ccUserIds': [2]},
    }  # 财务组审批并抄送 zhangsan
    # 创建/同步请假流程模型：model_key='leave'，绑定 OA 分类与请假表单，BPMN 由 _leave_xml() 提供
    leave_model = _ensure_model('请假流程', 'leave', category.id, leave_form.id,
                                _leave_xml(), leave_cfg, 'OA 请假审批演示流程')  # 请假模型
    # 创建/同步报销流程模型：model_key='expense'，绑定 OA 分类与报销表单，BPMN 由 _expense_xml() 提供
    _ensure_model('报销流程', 'expense', category.id, expense_form.id,
                  _expense_xml(), expense_cfg, 'OA 报销审批演示流程')  # 报销模型
    # 表达式示例：先按唯一编码判断是否存在，避免重复执行时插入重复表达式
    if not WfExpression.objects.filter(expr_code='leave_days_gt3', is_deleted=0).exists():  # 表达式示例
        # 当前时间用于审计字段
        now = time.strftime('%Y-%m-%d %H:%M:%S')  # 当前时间
        # 条件表达式：expr_type='condition' 表示用于网关条件判断；expr_content 与 BPMN 网关条件一致，
        # 引用表单字段 form.leaveDays，超过 3 天为真
        WfExpression.objects.create(expr_name='请假天数大于3天', expr_code='leave_days_gt3',
                                    # 表达式内容直接引用表单字段 leaveDays；类型为条件 condition
                                    expr_content='${form.leaveDays > 3}', expr_type='condition',
                                    # 备注说明使用场景；审计字段同样记 admin
                                    remark='超过 3 天需要总监审批', create_by='admin', create_time=now,
                                    # 更新人与未删除标记
                                    update_by='admin', update_time=now, is_deleted=0)
    # 监听器示例：挂在请假模型上，判断同模型同事件同动作是否已存在，保证幂等
    if not WfListener.objects.filter(model_id=leave_model.id, event_type='start',
                                     action_type='notify', is_deleted=0).exists():  # 监听器示例
        # 当前时间用于审计字段
        now = time.strftime('%Y-%m-%d %H:%M:%S')  # 当前时间
        # event_type='start' 表示流程启动时触发；action_type='notify' 表示发送通知；
        # callback_url 为空（演示用内置通知，不调外部接口）；callback_param 为通知内容 JSON；status=0 启用
        WfListener.objects.create(model_id=leave_model.id, event_type='start', action_type='notify',
                                  # 回调地址为空；回调参数是 JSON 字符串，通知内容为「流程已启动」
                                  callback_url='', callback_param='{"msg":"流程已启动"}', status=0,
                                  # 审计字段：记录创建人与时间
                                  create_by='admin', create_time=now, update_by='admin',
                                  # 更新人与未删除标记
                                  update_time=now, is_deleted=0)
    # 返回分类与请假模型的 ID，便于初始化命令打印或后续排查
    return {'category': category.id, 'leave_model': leave_model.id}  # 返回关键 ID 便于排查
