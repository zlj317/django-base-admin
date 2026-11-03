"""BPMN2.0 审批引擎：解析 bpmn-js 导出的 XML，驱动流程实例流转并生成人工待办。

设计要点：
1. 解析 XML 得到节点图，按顺序流推进 token；
2. userTask 暂停并生成待办任务，支持串行 / 或签 / 会签；
3. 排他网关按表达式条件分支，并行网关按到达次数汇合；
4. 运行状态（串行队列、并行到达记录）存 wf_instance.engine_state，随操作持久化；
5. 节点审批人策略、抄送、超时、监听器由本模块自主实现。
"""
import json  # 引擎状态与表单数据序列化
import logging  # 监听器回调失败时记录日志，不阻断主流程
import urllib.request  # 监听器 HTTP 回调（标准库，避免额外依赖）
import xml.etree.ElementTree as ET  # BPMN XML 解析
from datetime import datetime, timedelta  # 计算任务到期时间

from apps.system.models import SysUser  # 审批人策略需要按用户/部门查人
from apps.workflow.models import WfAudit, WfCc, WfGroupUser, WfListener, WfTask  # 引擎落库模型

logger = logging.getLogger(__name__)  # 监听器与引擎异常日志

BPMN_NS = '{http://www.omg.org/spec/BPMN/20100524/MODEL}'  # BPMN 2.0 标准命名空间
MAX_STEPS = 500  # 单次流转最大步数，防止流程配置成死循环拖垮服务

NODE_TYPES = {  # 参与流转的节点标签（去掉命名空间后的本地名）
    'startEvent', 'endEvent', 'userTask', 'serviceTask', 'scriptTask', 'manualTask',
    'exclusiveGateway', 'parallelGateway', 'inclusiveGateway', 'subProcess',
}
USER_TASK = 'userTask'  # 人工审批节点
END_EVENT = 'endEvent'  # 结束节点


class EngineError(Exception):
    """流程引擎业务异常：由视图捕获并转换为统一错误响应。"""


class AttrDict(dict):
    """把字典包装成支持 form.xxx 属性访问，供表达式直接使用。"""

    def __getattr__(self, item):
        """属性读取回退到字典 get，缺失字段返回 None 而不是报错。"""
        return self.get(item)


def _local(tag):
    """去掉 XML 命名空间，返回标签本地名。"""
    return tag.split('}', 1)[1] if '}' in tag else tag  # ElementTree 的 tag 形如 {ns}userTask


def _check_xml_safe(xml):
    """BPMN XML 安全校验：拒绝 DTD/实体，防止 XXE 与实体膨胀攻击。"""
    if not xml or not xml.strip():  # 空定义直接拒绝
        raise EngineError('流程定义为空，请先设计流程图')
    upper = xml.upper()  # 统一大写便于关键字匹配
    if '<!DOCTYPE' in upper or '<!ENTITY' in upper:  # 常见攻击载荷关键字
        raise EngineError('流程定义包含非法 DTD/ENTITY 声明')
    if len(xml) > 2 * 1024 * 1024:  # 单份流程定义限制 2MB，避免解析过慢
        raise EngineError('流程定义过大')


class ProcessGraph:
    """BPMN 流程定义图：解析节点、顺序流与网关条件。"""

    def __init__(self, xml):
        """解析 XML，构建节点与顺序流索引。"""
        _check_xml_safe(xml)  # 先做安全校验
        try:
            root = ET.fromstring(xml)  # 解析为元素树
        except ET.ParseError as exc:  # XML 语法错误
            raise EngineError('BPMN XML 解析失败：%s' % exc)
        process = None  # 目标 process 元素
        for elem in root.iter():  # 广度查找第一个 process
            if _local(elem.tag) == 'process':  # 只认标准 process
                process = elem  # 记录并跳出
                break
        if process is None:  # 没有 process 说明不是合法 BPMN
            raise EngineError('BPMN 中未找到 process 定义')

        self.nodes = {}  # node_id -> {id,name,type,incoming,outgoing,default}
        self.flows = {}  # flow_id -> {id,source,target,condition,name}
        for elem in process:  # 遍历 process 的一级子元素
            tag = _local(elem.tag)  # 本地标签名
            eid = elem.attrib.get('id')  # 元素 ID
            if not eid:  # 没有 ID 的元素无法参与流转
                continue
            if tag == 'sequenceFlow':  # 顺序流
                cond = ''  # 条件表达式文本
                for child in elem:  # 条件表达式是子元素
                    if _local(child.tag) == 'conditionExpression':  # 条件节点
                        cond = (child.text or '').strip()  # 取出表达式文本
                self.flows[eid] = {
                    'id': eid,
                    'source': elem.attrib.get('sourceRef'),  # 源节点
                    'target': elem.attrib.get('targetRef'),  # 目标节点
                    'condition': cond,  # 条件表达式
                    'name': elem.attrib.get('name') or '',  # 连线名称
                }
            elif tag in NODE_TYPES:  # 普通节点
                self.nodes[eid] = {
                    'id': eid,
                    'name': elem.attrib.get('name') or tag,  # 节点显示名
                    'type': tag,  # 节点类型
                    'default': elem.attrib.get('default'),  # 网关默认流
                    'incoming': [],  # 进入顺序流
                    'outgoing': [],  # 离开顺序流
                }
        # 把顺序流挂到源/目标节点的进出一侧
        for flow in self.flows.values():
            src = self.nodes.get(flow['source'])  # 源节点
            dst = self.nodes.get(flow['target'])  # 目标节点
            if src:  # 源节点存在时挂 outgoing
                src['outgoing'].append(flow['id'])
            if dst:  # 目标节点存在时挂 incoming
                dst['incoming'].append(flow['id'])
        if not self.nodes:  # 没有任何节点
            raise EngineError('BPMN 中未找到可执行节点')

    def start_node(self):
        """返回开始节点 ID；缺失时抛出异常。"""
        for node in self.nodes.values():  # 查找开始事件
            if node['type'] == 'startEvent':
                return node['id']
        raise EngineError('流程缺少开始节点')

    def node(self, node_id):
        """按 ID 取节点，不存在时抛出异常。"""
        node = self.nodes.get(node_id)  # 字典查找
        if not node:
            raise EngineError('流程节点不存在：%s' % node_id)
        return node

    def condition(self, flow_id):
        """取顺序流条件表达式。"""
        flow = self.flows.get(flow_id)  # 顺序流查找
        return (flow or {}).get('condition') or ''  # 不存在返回空串

    def previous_user_task(self, node_id):
        """逆向查找最近的人工任务节点，供“退回上一步”使用。"""
        queue = list(self.node(node_id)['incoming'])  # 从当前节点的入边开始
        visited = set()  # 防止逆向成环
        while queue:  # 广度优先
            flow_id = queue.pop(0)  # 取一条入边
            if flow_id in visited:  # 已访问跳过
                continue
            visited.add(flow_id)
            flow = self.flows.get(flow_id)  # 顺序流
            if not flow:  # 脏数据跳过
                continue
            src = self.nodes.get(flow['source'])  # 源节点
            if not src:  # 节点缺失
                continue
            if src['type'] == USER_TASK:  # 找到上游人工节点
                return src['id']
            queue.extend(src['incoming'])  # 继续向上游搜索
        return None  # 上游没有人工节点

    def cfg(self, node_id, node_config):
        """读取节点审批人配置，未配置时给出兜底默认值。"""
        raw = (node_config or {}).get(node_id) or {}  # 节点配置
        return {
            'assigneeType': raw.get('assigneeType') or 'starter',  # 默认发起人
            'userIds': raw.get('userIds') or [],  # 指定用户
            'roleIds': raw.get('roleIds') or [],  # 指定角色
            'deptIds': raw.get('deptIds') or [],  # 指定部门
            'groupId': raw.get('groupId'),  # 指定分组
            'expr': raw.get('expr') or '',  # 动态审批人表达式
            'approveMode': int(raw.get('approveMode') or 2),  # 默认或签
            'dueHours': raw.get('dueHours'),  # 超时小时数
            'ccUserIds': raw.get('ccUserIds') or [],  # 抄送用户
        }


def _eval_expr(expr, form_data):
    """计算流程表达式，支持 ${form.leaveDays > 3} 与 && / || 写法。"""
    text = (expr or '').strip()  # 去空白
    if text.startswith('${') and text.endswith('}'):  # 去掉 EL 表达式包装
        text = text[2:-1].strip()
    text = text.replace('&&', ' and ').replace('||', ' or ')  # 兼容 Java 风格逻辑运算符
    if not text:  # 空表达式视为不成立
        return False
    ctx = {'form': AttrDict(form_data or {})}  # 表单对象，支持 form.xxx
    ctx.update(form_data or {})  # 同时支持直接写字段名
    try:
        return bool(eval(text, {'__builtins__': {}}, ctx))  # 受限执行，禁用内置函数
    except Exception:  # 表达式语法/字段错误按不成立处理，避免阻断流程
        return False


def _now():
    """返回本地当前时间（去掉微秒，与 MySQL datetime 对齐）。"""
    return datetime.now().replace(microsecond=0)


def _load_state(instance):
    """读取实例引擎状态，损坏时回退空结构。"""
    try:
        state = json.loads(instance.engine_state or '{}')  # 正常解析
    except (TypeError, ValueError):
        state = {}  # 脏数据回退
    state.setdefault('arrivals', {})  # 并行网关到达记录
    state.setdefault('serial', {})  # 串行审批剩余人员
    return state


def _save_state(instance, state):
    """把引擎状态写回实例字段（不触发额外查询）。"""
    instance.engine_state = json.dumps(state, ensure_ascii=False)  # 中文保持可读
    instance.update_time = _now()  # 同步更新时间


def fire_listeners(model, event, instance, node_name=''):
    """触发流程监听器：日志/通知直接记录，回调接口失败不影响主流程。"""
    listeners = WfListener.objects.filter(model_id=model.id, event_type=event,
                                         status=0, is_deleted=0)  # 启用中的监听器
    for listener in listeners:  # 逐个执行
        try:
            if listener.action_type == 'callback' and listener.callback_url:  # HTTP 回调
                payload = json.dumps({
                    'event': event, 'instanceId': instance.id, 'instanceKey': instance.instance_key,
                    'modelId': model.id, 'modelKey': model.model_key, 'node': node_name,
                    'extra': json.loads(listener.callback_param or '{}'),
                }, ensure_ascii=False).encode('utf-8')  # 组装回调参数
                req = urllib.request.Request(listener.callback_url, data=payload,
                                             headers={'Content-Type': 'application/json'})  # POST 请求
                urllib.request.urlopen(req, timeout=3).read()  # 限时调用，避免拖慢审批
            else:  # notify / update_data / log 统一写服务日志
                logger.info('[wf-listener] model=%s event=%s action=%s instance=%s node=%s',
                            model.model_key, event, listener.action_type, instance.id, node_name)
        except Exception as exc:  # 监听器属于旁路能力，失败只记录
            logger.warning('[wf-listener] 执行失败 id=%s: %s', listener.id, exc)


class WorkflowEngine:
    """流程实例引擎：负责启动、推进、完成任务与终态处理。"""

    def __init__(self, instance, model, node_config=None):
        """绑定实例与模型，解析流程图。"""
        self.instance = instance  # 流程实例
        self.model = model  # 流程模型（已锁定版本）
        self.graph = ProcessGraph(model.bpmn_xml)  # 解析 BPMN
        try:
            cfg = node_config if node_config is not None else json.loads(model.node_config or '{}')  # 节点配置
        except (TypeError, ValueError):
            cfg = {}  # 脏数据回退空配置
        self.node_config = cfg if isinstance(cfg, dict) else {}  # 保证是字典
        self.state = _load_state(instance)  # 运行状态
        try:
            self.form_data = json.loads(instance.form_data or '{}')  # 表单数据
        except (TypeError, ValueError):
            self.form_data = {}  # 脏数据回退
        self.steps = 0  # 已执行步数

    # ------------------------------------------------------------ 公共入口
    def start(self):
        """启动流程：从开始事件推进到第一个暂停点。"""
        start_id = self.graph.start_node()  # 开始节点
        state = self.state
        state['started'] = True  # 标记已启动，防止重复启动
        _save_state(self.instance, state)  # 先落状态
        self._run(list(self.graph.node(start_id)['outgoing']))  # 推进开始节点出的顺序流
        fire_listeners(self.model, 'start', self.instance, '开始')  # 流程启动事件
        self.sync()  # 同步实例状态与当前节点

    def continue_from(self, node_id):
        """从指定节点继续流转（审批通过后调用）。"""
        self._run(list(self.graph.node(node_id)['outgoing']))  # 沿节点出边推进
        self.sync()  # 同步实例状态

    # ------------------------------------------------------------ 流转核心
    def _run(self, queue):
        """按顺序流队列推进 token，直到没有可推进的边。"""
        while queue:  # 队列非空
            self.steps += 1  # 累计步数
            if self.steps > MAX_STEPS:  # 防止死循环
                raise EngineError('流程流转步数超限，请检查网关连线是否成环')
            flow_id = queue.pop(0)  # 取一条顺序流
            flow = self.graph.flows.get(flow_id)  # 顺序流定义
            if not flow:  # 脏数据
                continue
            target = self.graph.nodes.get(flow['target'])  # 目标节点
            if not target:  # 目标节点缺失
                continue
            self._enter(target, flow, queue)  # 进入目标节点
        _save_state(self.instance, self.state)  # 每轮推进后持久化状态

    def _enter(self, node, flow, queue):
        """进入节点：按类型决定暂停、分支、分流或结束。"""
        ntype = node['type']  # 节点类型
        if ntype == USER_TASK:  # 人工任务：生成待办并暂停该分支
            self._create_tasks(node, flow)
            return
        if ntype == 'endEvent':  # 结束事件
            self._on_end(node)
            return
        if ntype == 'exclusiveGateway':  # 排他网关：只走一条
            chosen = self._choose_flow(node)  # 选择条件成立的出边
            if chosen:  # 命中分支
                queue.append(chosen)
            return
        if ntype == 'parallelGateway':  # 并行网关：分流或汇合
            if not self._join_ready(node, flow):  # 等待其他分支到达
                return
            queue.extend(list(node['outgoing']))  # 全部出边同时推进
            return
        if ntype == 'inclusiveGateway':  # 包容网关按条件取多条出边
            for flow_id in node['outgoing']:  # 逐条判断
                cond = self.graph.condition(flow_id)  # 条件表达式
                if not cond or _eval_expr(cond, self.form_data):  # 无条件或条件成立
                    queue.append(flow_id)
            return
        # 其他任务（serviceTask/scriptTask/manualTask/subProcess）自动通过
        queue.extend(list(node['outgoing']))

    def _choose_flow(self, node):
        """排他网关选路：条件成立的第一条，否则走默认流。"""
        for flow_id in node['outgoing']:  # 按连线顺序判断
            cond = self.graph.condition(flow_id)  # 条件
            if cond and _eval_expr(cond, self.form_data):  # 条件成立
                return flow_id
            if not cond:  # 无条件连线视为默认命中
                return flow_id
        return node.get('default')  # 回退网关 default 属性

    def _join_ready(self, node, flow):
        """并行网关汇合判断：所有入边都到达后才放行。"""
        incoming = node['incoming']  # 入边数量
        if len(incoming) <= 1:  # 单入边视为分流
            return True
        arrivals = self.state['arrivals'].setdefault(node['id'], [])  # 已到达的入边
        if flow['id'] not in arrivals:  # 记录本次到达
            arrivals.append(flow['id'])
        if len(arrivals) < len(incoming):  # 还没全部到达
            return False
        self.state['arrivals'][node['id']] = []  # 汇合成功，清空记录供下一轮使用
        return True

    def _on_end(self, node):
        """结束事件：仅在无未完成待办时把实例置为完成。"""
        # 终态统一在 sync() 中处理，这里只记录轨迹节点
        names = self.state.setdefault('ended_nodes', [])  # 已结束节点列表
        if node['id'] not in names:  # 去重记录
            names.append(node['id'])

    # ------------------------------------------------------------ 任务生成
    def _create_tasks(self, node, flow):
        """为人工任务节点生成待办：解析审批人、审批方式、抄送与到期时间。"""
        pending = WfTask.objects.filter(instance_id=self.instance.id, task_key=node['id'],
                                        status=0, is_deleted=0)  # 节点已有待办则跳过
        if pending.exists():  # 防止循环/重复进入重复建任务
            return
        cfg = self.graph.cfg(node['id'], self.node_config)  # 节点配置
        assignees = self._resolve_assignees(cfg)  # 解析审批人
        if not assignees:  # 无审批人时兜底发起人，保证流程可继续
            assignees = [self.instance.start_user_id]
        assignees = self._dedupe(assignees)  # 去重保持顺序
        self._make_cc(node, cfg.get('ccUserIds') or [])  # 进入节点即抄送
        mode = cfg['approveMode']  # 审批方式
        if mode not in (1, 2, 3):  # 非法值回退或签
            mode = 2
        if mode == 1 and len(assignees) > 1:  # 串行：只建第一个人的任务
            self.state['serial'][node['id']] = assignees[1:]  # 其余排队
            assignees = assignees[:1]
        else:
            self.state['serial'].pop(node['id'], None)  # 非串行清空历史队列
        due_time = None  # 到期时间
        if cfg.get('dueHours'):  # 配置了超时小时数
            due_time = _now() + timedelta(hours=float(cfg['dueHours']))  # 计算截止时间
        now = _now()  # 统一时间
        for uid in assignees:  # 逐个生成待办
            WfTask.objects.create(
                instance_id=self.instance.id, task_key=node['id'], task_name=node['name'],
                assignee=uid, status=0, approve_mode=mode, due_time=due_time,
                start_time=now, create_by=self.instance.create_by or 'system',
                create_time=now, update_by=self.instance.create_by or 'system', update_time=now,
                is_deleted=0,
            )
        fire_listeners(self.model, 'enter', self.instance, node['name'])  # 节点进入事件
        self.state['waiting_node'] = node['id']  # 记录最近生成的节点

    def _resolve_assignees(self, cfg):
        """按配置策略解析审批人用户 ID 列表。"""
        kind = cfg['assigneeType']  # 策略类型
        if kind == 'starter':  # 发起人本人
            return [self.instance.start_user_id]
        if kind == 'user':  # 指定用户
            return [int(x) for x in cfg['userIds'] if str(x).isdigit()]
        if kind == 'role':  # 指定角色下的启用用户
            role_ids = [int(x) for x in cfg['roleIds'] if str(x).isdigit()]
            if not role_ids:  # 未选角色
                return []
            from django.db import connection  # 局部导入，避免模块级依赖
            with connection.cursor() as cursor:  # 复用项目数据库连接
                placeholders = ','.join(['%s'] * len(role_ids))  # 参数占位
                cursor.execute(
                    'SELECT ur.user_id FROM sys_user_role ur JOIN sys_user u ON u.id = ur.user_id '
                    'AND u.is_deleted = 0 AND u.status = 0 WHERE ur.role_id IN (%s)' % placeholders,
                    role_ids)
                return [row[0] for row in cursor.fetchall()]  # 返回用户 ID
        if kind == 'dept':  # 指定部门
            dept_ids = [int(x) for x in cfg['deptIds'] if str(x).isdigit()]
            if not dept_ids:  # 未选部门
                return []
            return list(SysUser.objects.filter(dept_id__in=dept_ids, status=0, is_deleted=0)
                        .values_list('id', flat=True))
        if kind == 'group':  # 指定用户分组
            if not cfg['groupId']:  # 未选分组
                return []
            ids = list(WfGroupUser.objects.filter(group_id=cfg['groupId']).values_list('user_id', flat=True))  # 分组用户
            return list(SysUser.objects.filter(id__in=ids, status=0, is_deleted=0)
                        .values_list('id', flat=True))  # 过滤有效账号
        if kind == 'expression':  # 动态表达式：结果按用户 ID 列表解析
            value = self._eval_assignee_expr(cfg.get('expr'))
            if isinstance(value, (list, tuple)):  # 列表形式
                return [int(x) for x in value if str(x).isdigit()]
            if str(value).isdigit():  # 单个 ID
                return [int(value)]
            return []
        return []  # 未知策略

    def _eval_assignee_expr(self, expr):
        """执行动态审批人表达式，失败返回空值。"""
        text = (expr or '').strip()  # 去空白
        if text.startswith('${') and text.endswith('}'):  # 去包装
            text = text[2:-1]
        try:
            return eval(text, {'__builtins__': {}}, {'form': AttrDict(self.form_data), **self.form_data})
        except Exception:  # 表达式非法
            return None

    @staticmethod
    def _dedupe(ids):
        """去重并保持顺序，避免同一人重复收到待办。"""
        result = []  # 结果列表
        for uid in ids:  # 逐个处理
            if uid and uid not in result:  # 未出现过才加入
                result.append(uid)
        return result  # 返回去重列表

    def _make_cc(self, node, user_ids):
        """生成抄送记录，同一实例同节点同用户只写一次。"""
        now = _now()  # 抄送时间
        for uid in self._dedupe([int(x) for x in user_ids if str(x).isdigit()]):  # 逐个抄送
            exists = WfCc.objects.filter(instance_id=self.instance.id, user_id=uid,
                                         node_id=node['id']).exists()  # 防重复
            if exists:  # 已抄送过
                continue
            WfCc.objects.create(instance_id=self.instance.id, user_id=uid, node_id=node['id'],
                                status=0, create_time=now)  # 写入抄送记录

    # ------------------------------------------------------------ 状态同步
    def sync(self):
        """同步实例状态：当前节点、是否完成、结束时间。"""
        pending = WfTask.objects.filter(instance_id=self.instance.id, status=0, is_deleted=0)  # 未完成待办
        node_ids = list(pending.values_list('task_key', flat=True))  # 当前节点 ID
        self.instance.current_node = ','.join(sorted(set(node_ids))) or self.instance.current_node  # 更新当前节点
        if not pending.exists() and self.instance.status == 0:  # 无待办且仍在运行
            self.instance.status = 1  # 置为已完成
            self.instance.end_time = _now()  # 记录结束时间
            fire_listeners(self.model, 'end', self.instance, '结束')  # 流程结束事件
        _save_state(self.instance, self.state)  # 持久化引擎状态
        self.instance.update_time = _now()  # 更新时间
        self.instance.save(update_fields=['current_node', 'status', 'end_time', 'engine_state', 'update_time'])  # 只写必要字段

    def record(self, operator_id, action, comment='', task=None, node_id=None, node_name=None):
        """写入审批记录，供轨迹与已办查询。"""
        WfAudit.objects.create(
            instance_id=self.instance.id,
            task_id=task.id if task else None, operator_id=operator_id, action=action,
            comment=comment, node_id=node_id, node_name=node_name, create_time=_now(),
        )


# -------------------------------------------------------------- 任务动作工具
def close_tasks(instance_id, node_id=None, operator_id=None, status=1):
    """关闭实例下（可限定节点）的待办任务。"""
    qs = WfTask.objects.filter(instance_id=instance_id, status=0, is_deleted=0)  # 未完成待办
    if node_id:  # 限定节点
        qs = qs.filter(task_key=node_id)
    qs.update(status=status, end_time=_now(), update_by=str(operator_id or ''),
              update_time=_now())  # 批量置为已办/驳回


def approve_task(instance, model, task, operator_id, comment=''):
    """同意任务：按串行/或签/会签规则推进流程。"""
    engine = WorkflowEngine(instance, model)  # 构造引擎
    engine.record(operator_id, 'approve', comment, task, task.task_key, task.task_name)  # 先记审批意见
    task.status = 1  # 当前任务已办
    task.end_time = _now()  # 完成时间
    task.update_by = str(operator_id)  # 更新人
    task.update_time = _now()  # 更新时间
    task.save(update_fields=['status', 'end_time', 'update_by', 'update_time'])
    mode = task.approve_mode  # 审批方式
    node_id = task.task_key  # 节点 ID
    if mode == 1:  # 串行：唤醒下一位
        remaining = engine.state['serial'].get(node_id) or []  # 排队人员
        if remaining:  # 还有人
            next_uid = remaining.pop(0)  # 取下一个
            engine.state['serial'][node_id] = remaining  # 回写队列
            cfg = engine.graph.cfg(node_id, engine.node_config)  # 取节点配置
            now = _now()  # 当前时间
            WfTask.objects.create(
                instance_id=instance.id, task_key=node_id,
                task_name=engine.graph.node(node_id)['name'], assignee=next_uid,
                status=0, approve_mode=1, due_time=task.due_time,
                start_time=now, create_by=instance.create_by or 'system', create_time=now,
                update_by=instance.create_by or 'system', update_time=now, is_deleted=0)  # 生成下一位待办
            engine.sync()  # 同步当前节点
            return
        engine.state['serial'].pop(node_id, None)  # 队列清空
    elif mode == 2:  # 或签：其他人待办直接关闭
        close_tasks(instance.id, node_id, operator_id, status=1)
    else:  # 会签：还有其他人未处理则等待
        others = WfTask.objects.filter(instance_id=instance.id, task_key=node_id,
                                       status=0, is_deleted=0)  # 其余待办
        if others.exists():  # 仍需等待
            engine.sync()  # 仅同步当前节点
            return
    engine.continue_from(node_id)  # 节点完成，继续流转
    fire_listeners(model, 'complete', instance, task.task_name)  # 节点完成事件


def reject_task(instance, model, task, operator_id, comment=''):
    """驳回任务：流程终止为已驳回，关闭全部待办。"""
    engine = WorkflowEngine(instance, model)  # 构造引擎
    engine.record(operator_id, 'reject', comment, task, task.task_key, task.task_name)  # 审批记录
    close_tasks(instance.id, None, operator_id, status=4)  # 关闭全部待办
    instance.status = 2  # 实例置为已驳回
    instance.end_time = _now()  # 结束时间
    instance.update_time = _now()  # 更新时间
    instance.save(update_fields=['status', 'end_time', 'update_time'])  # 持久化
    fire_listeners(model, 'reject', instance, task.task_name)  # 驳回事件


def transfer_task(instance, model, task, operator_id, target_id, comment=''):
    """转审：原任务置为已转派，为目标用户新建同节点待办。"""
    engine = WorkflowEngine(instance, model)  # 构造引擎
    engine.record(operator_id, 'transfer', comment, task, task.task_key, task.task_name)  # 审批记录
    task.status = 2  # 原任务已转派
    task.end_time = _now()  # 完成时间
    task.update_by = str(operator_id)  # 更新人
    task.update_time = _now()  # 更新时间
    task.save(update_fields=['status', 'end_time', 'update_by', 'update_time'])
    now = _now()  # 当前时间
    WfTask.objects.create(
        instance_id=instance.id, task_key=task.task_key, task_name=task.task_name,
        assignee=target_id, status=0, approve_mode=task.approve_mode, priority=task.priority,
        due_time=task.due_time, start_time=now, create_by=instance.create_by or 'system',
        create_time=now, update_by=instance.create_by or 'system', update_time=now,
        is_deleted=0)  # 新处理人待办
    engine.sync()  # 同步当前节点


def addsign_task(instance, model, task, operator_id, target_id, comment=''):
    """加签：新增一名会签人，节点需全部通过后才继续。"""
    engine = WorkflowEngine(instance, model)  # 构造引擎
    engine.record(operator_id, 'addsign', comment, task, task.task_key, task.task_name)  # 审批记录
    now = _now()  # 当前时间
    WfTask.objects.create(
        instance_id=instance.id, task_key=task.task_key, task_name=task.task_name,
        assignee=target_id, status=0, approve_mode=3, priority=task.priority,
        due_time=task.due_time, start_time=now, create_by=instance.create_by or 'system',
        create_time=now, update_by=instance.create_by or 'system', update_time=now, is_deleted=0)  # 加签待办
    WfTask.objects.filter(id=task.id).update(approve_mode=3)  # 原任务改为会签语义
    engine.sync()  # 同步当前节点


def back_task(instance, model, task, operator_id, comment=''):
    """退回上一步：关闭当前节点待办，在上一个人工节点重新生成任务。"""
    engine = WorkflowEngine(instance, model)  # 构造引擎
    previous = engine.graph.previous_user_task(task.task_key)  # 上游人工节点
    if not previous:  # 没有可退回节点
        raise EngineError('当前节点没有可退回的上一步')
    engine.record(operator_id, 'back', comment, task, task.task_key, task.task_name)  # 审批记录
    close_tasks(instance.id, task.task_key, operator_id, status=4)  # 关闭当前节点全部待办
    engine.state['serial'].pop(task.task_key, None)  # 清理串行队列
    engine.state['waiting_node'] = previous  # 记录回退节点
    engine._create_tasks(engine.graph.node(previous), {'id': ''})  # 在上游节点重建待办
    instance.status = 0  # 恢复运行中
    instance.end_time = None  # 清空结束时间
    engine.sync()  # 同步当前节点


def withdraw_instance(instance, operator_id, comment=''):
    """撤回：发起人在无人审批前终止自己的流程。"""
    approved = WfAudit.objects.filter(instance_id=instance.id, action='approve').exists()  # 是否已有人审批
    if approved:  # 已有审批不可撤回
        raise EngineError('流程已被审批，无法撤回')
    close_tasks(instance.id, None, operator_id, status=4)  # 关闭全部待办
    WfAudit.objects.create(instance_id=instance.id, operator_id=operator_id, action='withdraw',
                           comment=comment or '发起人撤回', node_id=None, node_name='发起人', create_time=_now())  # 撤回记录
    instance.status = 3  # 置为已终止
    instance.end_time = _now()  # 结束时间
    instance.update_time = _now()  # 更新时间
    instance.save(update_fields=['status', 'end_time', 'update_time'])  # 持久化


def terminate_instance(instance, model, operator_id, comment=''):
    """管理员强制终止流程。"""
    close_tasks(instance.id, None, operator_id, status=4)  # 关闭全部待办
    WfAudit.objects.create(instance_id=instance.id, operator_id=operator_id, action='terminate',
                           comment=comment or '管理员终止', node_id=None, node_name='系统', create_time=_now())  # 终止记录
    instance.status = 3  # 已终止
    instance.end_time = _now()  # 结束时间
    instance.update_time = _now()  # 更新时间
    instance.save(update_fields=['status', 'end_time', 'update_time'])  # 持久化
    fire_listeners(model, 'end', instance, '终止')  # 结束事件
