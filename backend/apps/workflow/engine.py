"""BPMN2.0 审批引擎：解析 bpmn-js 导出的 XML，驱动流程实例流转并生成人工待办。

设计要点：
1. 解析 XML 得到节点图，按顺序流推进 token；
2. userTask 暂停并生成待办任务，支持串行 / 或签 / 会签；
3. 排他网关按表达式条件分支，并行网关按到达次数汇合；
4. 运行状态（串行队列、并行到达记录）存 wf_instance.engine_state，随操作持久化；
5. 节点审批人策略、抄送、超时、监听器由本模块自主实现。
"""
# 模块：apps/workflow/engine.py —— 自研 BPMN 2.0 流程引擎（不引入第三方工作流组件）
# 职责：解析 bpmn-js 导出的 BPMN XML 并构建节点/顺序流拓扑，用 token 队列推进流程实例；
#       在 userTask 生成人工待办并暂停当前分支，按审批模式（1 串行 / 2 或签 / 3 会签）汇总结果；
#       处理排他/并行/包容三类网关的选路与汇合，执行 ${...} 条件表达式与动态审批人表达式；
#       负责抄送落库、超时到期时间计算、监听器回调，并把实例收敛到完成/驳回/终止终态。
# 调用方：apps/workflow/views.py（发起、同意、驳回、转审、加签、退回、撤回、终止等接口通过
#         engine.WorkflowEngine 或本模块的任务动作函数驱动流程；参数校验/权限/响应封装留在视图层）。
# 支持节点：startEvent / endEvent / userTask / serviceTask / scriptTask / manualTask /
#           exclusiveGateway（排他）/ parallelGateway（并行）/ inclusiveGateway（包容）/ subProcess。
# 审批模式：approveMode 1=串行（逐人依次审批）、2=或签（任一人通过即节点通过）、3=会签（全员通过才通过）。
# 关联的 11 张 wf_ 表（均 managed=False，由 SQL 手工建表）：
#   wf_model 提供 bpmn_xml/node_config；wf_instance 持久化 form_data/engine_state/current_node/状态；
#   wf_task 落人工待办；wf_audit 记录各审批动作轨迹；wf_cc 落抄送；wf_listener 提供事件监听；
#   wf_group / wf_group_user 供“分组审批人”解析；wf_category / wf_form 为建模配置；
#   wf_expression 为表达式配置（运行态主要读写前六类表，配置类表由视图与设计器维护）。
# 状态机：wf_instance.status 0 运行中 / 1 已完成 / 2 已驳回 / 3 已终止；
#         wf_task.status 0 待办 / 1 已办 / 2 已转派 / 3 已加签 / 4 已驳回。
# 安全约束：解析前拒绝 DTD/ENTITY（防 XXE 与实体膨胀）；表达式走受限 eval（清空 __builtins__）。
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
    # 节点白名单明细：任务类、事件类、三类网关与子流程；其余标签（图形/注释等）不参与流转
    'startEvent', 'endEvent', 'userTask', 'serviceTask', 'scriptTask', 'manualTask',
    'exclusiveGateway', 'parallelGateway', 'inclusiveGateway', 'subProcess',
}
USER_TASK = 'userTask'  # 人工审批节点
END_EVENT = 'endEvent'  # 结束节点


# 引擎业务异常：继承 Exception 便于 views.py 精确捕获并转成统一业务错误，而非 500
class EngineError(Exception):
    """流程引擎业务异常：由视图捕获并转换为统一错误响应。"""


# 表达式上下文包装：把普通 dict 变成可用 form.xxx 访问的对象，供受限 eval 使用
class AttrDict(dict):
    """把字典包装成支持 form.xxx 属性访问，供表达式直接使用。"""

    # 仅当常规属性访问（dict 的键本身不是属性）未命中时触发，缺字段返回 None 而非抛异常
    def __getattr__(self, item):
        """属性读取回退到字典 get，缺失字段返回 None 而不是报错。"""
        # 字段缺失返回 None，表达式里写 f.xxx 不会因 KeyError 中断整个求值
        return self.get(item)


# XML 标签工具：ElementTree 的 tag 可能带 {namespace} 前缀，引擎内部统一按本地名比较
def _local(tag):
    """去掉 XML 命名空间，返回标签本地名。"""
    return tag.split('}', 1)[1] if '}' in tag else tag  # ElementTree 的 tag 形如 {ns}userTask


# XML 安全闸门：空串、DTD/ENTITY、超大文本三类输入在进入解析器前直接拦截，防 XXE 与实体膨胀
def _check_xml_safe(xml):
    """BPMN XML 安全校验：拒绝 DTD/实体，防止 XXE 与实体膨胀攻击。"""
    if not xml or not xml.strip():  # 空定义直接拒绝
        # 空定义无法得到开始节点，提前给出可读业务提示
        raise EngineError('流程定义为空，请先设计流程图')
    upper = xml.upper()  # 统一大写便于关键字匹配
    if '<!DOCTYPE' in upper or '<!ENTITY' in upper:  # 常见攻击载荷关键字
        # XXE 与 billion-laughs 攻击都依赖 DTD/ENTITY 声明，一旦命中直接拒绝
        raise EngineError('流程定义包含非法 DTD/ENTITY 声明')
    if len(xml) > 2 * 1024 * 1024:  # 单份流程定义限制 2MB，避免解析过慢
        # 2MB 上限：正常 bpmn-js 导出远小于该值，超限多为异常/恶意数据，也避免解析耗时过长
        raise EngineError('流程定义过大')


# 流程定义图：把 BPMN 解析成节点表 + 顺序流表；实例运行期间只读，不保留原始 DOM
class ProcessGraph:
    """BPMN 流程定义图：解析节点、顺序流与网关条件。"""

    # 入参 xml 为 bpmn-js 导出的完整定义文本；解析/校验失败统一抛 EngineError
    def __init__(self, xml):
        """解析 XML，构建节点与顺序流索引。"""
        _check_xml_safe(xml)  # 先做安全校验
        # 标签不闭合、编码错误等解析异常转成业务异常，避免原始 ET 异常外泄到接口层
        try:
            root = ET.fromstring(xml)  # 解析为元素树
        except ET.ParseError as exc:  # XML 语法错误
            # 带上原始错误信息，便于设计器侧排查 XML 语法问题
            raise EngineError('BPMN XML 解析失败：%s' % exc)
        process = None  # 目标 process 元素
        for elem in root.iter():  # 广度查找第一个 process
            if _local(elem.tag) == 'process':  # 只认标准 process
                process = elem  # 记录并跳出
                # 找到第一个 process 即停止搜索
                break
        if process is None:  # 没有 process 说明不是合法 BPMN
            # 只有图元没有 process 的定义不可执行（可能只上传了图形文件）
            raise EngineError('BPMN 中未找到 process 定义')

        self.nodes = {}  # node_id -> {id,name,type,incoming,outgoing,default}
        self.flows = {}  # flow_id -> {id,source,target,condition,name}
        for elem in process:  # 遍历 process 的一级子元素
            tag = _local(elem.tag)  # 本地标签名
            eid = elem.attrib.get('id')  # 元素 ID
            if not eid:  # 没有 ID 的元素无法参与流转
                # 无 id 的元素无法被 sequenceFlow 引用，跳过以免污染节点表
                continue
            if tag == 'sequenceFlow':  # 顺序流
                cond = ''  # 条件表达式文本
                for child in elem:  # 条件表达式是子元素
                    if _local(child.tag) == 'conditionExpression':  # 条件节点
                        cond = (child.text or '').strip()  # 取出表达式文本
                # 顺序流登记：保存源/目标/条件/名称，后续建图与排他网关选路都读这里
                self.flows[eid] = {
                    # 顺序流自身 ID，便于按 flow_id 回查
                    'id': eid,
                    'source': elem.attrib.get('sourceRef'),  # 源节点
                    'target': elem.attrib.get('targetRef'),  # 目标节点
                    'condition': cond,  # 条件表达式
                    'name': elem.attrib.get('name') or '',  # 连线名称
                }
            elif tag in NODE_TYPES:  # 普通节点
                # 节点登记：类型取自标签本地名；incoming/outgoing 等全部 flow 读完后再回填
                self.nodes[eid] = {
                    # 节点主键，与 BPMN 元素 id 一致
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
                # 源端记录出边，_run/_enter 推进时按 outgoing 取下一批流
                src['outgoing'].append(flow['id'])
            if dst:  # 目标节点存在时挂 incoming
                # 目标端记录入边，并行汇合计数与“退回上一步”逆向搜索都依赖它
                dst['incoming'].append(flow['id'])
        if not self.nodes:  # 没有任何节点
            # 只有连线没有节点属于无效定义，启动前就拒绝
            raise EngineError('BPMN 中未找到可执行节点')

    # 取开始节点：标准 BPMN 只有一个 startEvent，返回其 id 供 start() 推进
    def start_node(self):
        """返回开始节点 ID；缺失时抛出异常。"""
        for node in self.nodes.values():  # 查找开始事件
            # 逐节点扫描类型，兼容 XML 中节点声明顺序不固定的情况
            if node['type'] == 'startEvent':
                # 命中即返回，无需继续遍历
                return node['id']
        # 没有开始事件属于建模缺陷，启动前就暴露给设计者
        raise EngineError('流程缺少开始节点')

    # 统一取节点入口：所有流转方法经此校验，把 KeyError 转成业务异常
    def node(self, node_id):
        """按 ID 取节点，不存在时抛出异常。"""
        node = self.nodes.get(node_id)  # 字典查找
        # 未命中说明模型改版或数据不一致，按业务异常处理
        if not node:
            # 带上节点 ID，便于定位设计器中的具体元素
            raise EngineError('流程节点不存在：%s' % node_id)
        # 返回节点字典本身，调用方只读使用
        return node

    # 条件读取：顺序流不存在或未配置条件时返回空串，调用方据此识别“无条件默认流”
    def condition(self, flow_id):
        """取顺序流条件表达式。"""
        flow = self.flows.get(flow_id)  # 顺序流查找
        return (flow or {}).get('condition') or ''  # 不存在返回空串

    # 退回语义：沿 incoming 逆向广度优先搜索最近 userTask，visited 以 flow_id 去重防成环
    def previous_user_task(self, node_id):
        """逆向查找最近的人工任务节点，供“退回上一步”使用。"""
        queue = list(self.node(node_id)['incoming'])  # 从当前节点的入边开始
        visited = set()  # 防止逆向成环
        while queue:  # 广度优先
            flow_id = queue.pop(0)  # 取一条入边
            if flow_id in visited:  # 已访问跳过
                # 同一入边可能被多条路径引用，重复访问直接跳过
                continue
            # 标记已处理，保证逆向搜索复杂度为 O(边数)
            visited.add(flow_id)
            flow = self.flows.get(flow_id)  # 顺序流
            if not flow:  # 脏数据跳过
                # 顺序流定义缺失（脏数据）时忽略，继续找其他入边
                continue
            src = self.nodes.get(flow['source'])  # 源节点
            if not src:  # 节点缺失
                # 源节点缺失同理跳过
                continue
            if src['type'] == USER_TASK:  # 找到上游人工节点
                # 找到最近的人工节点即返回，符合“只退一层”的预期
                return src['id']
            queue.extend(src['incoming'])  # 继续向上游搜索
        return None  # 上游没有人工节点

    # 节点配置归一化：集中补默认值，后续审批人解析不必重复判空
    def cfg(self, node_id, node_config):
        """读取节点审批人配置，未配置时给出兜底默认值。"""
        raw = (node_config or {}).get(node_id) or {}  # 节点配置
        # 输出固定为引擎约定的 9 个键，缺失字段在此统一兜底
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


# 网关条件求值：BPMN 条件常写成 ${form.xxx}，先剥离 EL 外壳再按 Python 语法执行
def _eval_expr(expr, form_data):
    """计算流程表达式，支持 ${form.leaveDays > 3} 与 && / || 写法。"""
    text = (expr or '').strip()  # 去空白
    if text.startswith('${') and text.endswith('}'):  # 去掉 EL 表达式包装
        # 去掉 ${ 与 } 两个外壳字符，只保留内部表达式文本
        text = text[2:-1].strip()
    text = text.replace('&&', ' and ').replace('||', ' or ')  # 兼容 Java 风格逻辑运算符
    if not text:  # 空表达式视为不成立
        # 空条件按“不成立”处理，排他网关因此会退到默认流
        return False
    ctx = {'form': AttrDict(form_data or {})}  # 表单对象，支持 form.xxx
    ctx.update(form_data or {})  # 同时支持直接写字段名
    # 受限执行：清空 __builtins__ 阻断文件/网络等危险调用，仅暴露表单上下文
    try:
        return bool(eval(text, {'__builtins__': {}}, ctx))  # 受限执行，禁用内置函数
    except Exception:  # 表达式语法/字段错误按不成立处理，避免阻断流程
        # 字段缺失、语法错误、类型不匹配统一视为条件不成立，保证流程不中断
        return False


# 时间基准：数据库 datetime 精确到秒，统一去微秒避免相等比较与序列化出现小数
def _now():
    """返回本地当前时间（去掉微秒，与 MySQL datetime 对齐）。"""
    # 使用本地时间，与 wf_* 表中时间列的存储约定保持一致
    return datetime.now().replace(microsecond=0)


# 状态反序列化：engine_state 可能为空/历史格式/被手工改坏，任何异常都回退空结构继续运行
def _load_state(instance):
    """读取实例引擎状态，损坏时回退空结构。"""
    # 正常路径按 JSON 解析，不影响性能
    try:
        state = json.loads(instance.engine_state or '{}')  # 正常解析
    # 仅捕获类型/取值错误，不吞掉数据库等系统异常
    except (TypeError, ValueError):
        state = {}  # 脏数据回退
    state.setdefault('arrivals', {})  # 并行网关到达记录
    state.setdefault('serial', {})  # 串行审批剩余人员
    # 保证两个必备键存在，后续代码可直接下标访问
    return state


# 状态序列化：ensure_ascii=False 保留中文可读；只改内存字段，由调用方决定何时 save
def _save_state(instance, state):
    """把引擎状态写回实例字段（不触发额外查询）。"""
    instance.engine_state = json.dumps(state, ensure_ascii=False)  # 中文保持可读
    instance.update_time = _now()  # 同步更新时间


# 监听器旁路：只查启用且未删除的记录；单个监听器失败不阻断审批主链路
def fire_listeners(model, event, instance, node_name=''):
    """触发流程监听器：日志/通知直接记录，回调接口失败不影响主流程。"""
    listeners = WfListener.objects.filter(model_id=model.id, event_type=event,
                                         status=0, is_deleted=0)  # 启用中的监听器
    for listener in listeners:  # 逐个执行
        # 逐个隔离异常，避免一个坏回调拖垮整批监听器
        try:
            if listener.action_type == 'callback' and listener.callback_url:  # HTTP 回调
                payload = json.dumps({
                    # 回调负载：事件名、实例标识、模型标识与节点名，便于外部系统定位
                    'event': event, 'instanceId': instance.id, 'instanceKey': instance.instance_key,
                    'modelId': model.id, 'modelKey': model.model_key, 'node': node_name,
                    # 监听器配置的附加参数，允许外部系统自定义过滤/路由
                    'extra': json.loads(listener.callback_param or '{}'),
                }, ensure_ascii=False).encode('utf-8')  # 组装回调参数
                req = urllib.request.Request(listener.callback_url, data=payload,
                                             headers={'Content-Type': 'application/json'})  # POST 请求
                urllib.request.urlopen(req, timeout=3).read()  # 限时调用，避免拖慢审批
            else:  # notify / update_data / log 统一写服务日志
                # 通知/改数据/日志类动作统一写服务日志，由日志采集侧消费
                logger.info('[wf-listener] model=%s event=%s action=%s instance=%s node=%s',
                            model.model_key, event, listener.action_type, instance.id, node_name)
        except Exception as exc:  # 监听器属于旁路能力，失败只记录
            # 记录监听器 ID 与异常，便于运营补偿，不向上抛出
            logger.warning('[wf-listener] 执行失败 id=%s: %s', listener.id, exc)


# 引擎实例是“单次操作”的短生命周期对象：构造时读取实例快照，操作结束后由 sync() 落库
class WorkflowEngine:
    """流程实例引擎：负责启动、推进、完成任务与终态处理。"""

    # 入参：instance 已持久化的实例；model 发起时锁定的模型快照；node_config 可覆盖模型配置
    def __init__(self, instance, model, node_config=None):
        """绑定实例与模型，解析流程图。"""
        self.instance = instance  # 流程实例
        self.model = model  # 流程模型（已锁定版本）
        self.graph = ProcessGraph(model.bpmn_xml)  # 解析 BPMN
        # node_config 可能是 JSON 文本或已解析字典，两种形态都兼容
        try:
            cfg = node_config if node_config is not None else json.loads(model.node_config or '{}')  # 节点配置
        # 非法 JSON 回退空配置，审批人解析会走默认策略而不是直接报错
        except (TypeError, ValueError):
            cfg = {}  # 脏数据回退空配置
        self.node_config = cfg if isinstance(cfg, dict) else {}  # 保证是字典
        self.state = _load_state(instance)  # 运行状态
        # 表单数据来自实例快照，发起后不再变化，用于条件表达式与动态审批人计算
        try:
            self.form_data = json.loads(instance.form_data or '{}')  # 表单数据
        except (TypeError, ValueError):
            self.form_data = {}  # 脏数据回退
        self.steps = 0  # 已执行步数

    # ------------------------------------------------------------ 公共入口
    # 启动：写 started 标记 → 沿 startEvent 出边推进 → 触发 start 监听 → 同步实例状态
    def start(self):
        """启动流程：从开始事件推进到第一个暂停点。"""
        start_id = self.graph.start_node()  # 开始节点
        # 复用已加载的状态对象，后续修改随 _save_state 一起落库
        state = self.state
        state['started'] = True  # 标记已启动，防止重复启动
        _save_state(self.instance, state)  # 先落状态
        self._run(list(self.graph.node(start_id)['outgoing']))  # 推进开始节点出的顺序流
        fire_listeners(self.model, 'start', self.instance, '开始')  # 流程启动事件
        self.sync()  # 同步实例状态与当前节点

    # 续流：审批完成后从当前节点出边继续；调用方保证节点已完成，这里不再校验任务状态
    def continue_from(self, node_id):
        """从指定节点继续流转（审批通过后调用）。"""
        self._run(list(self.graph.node(node_id)['outgoing']))  # 沿节点出边推进
        self.sync()  # 同步实例状态

    # ------------------------------------------------------------ 流转核心
    # 推进循环：queue 为待处理的顺序流 ID；进入节点后可能继续向 queue 追加新边
    def _run(self, queue):
        """按顺序流队列推进 token，直到没有可推进的边。"""
        while queue:  # 队列非空
            self.steps += 1  # 累计步数
            if self.steps > MAX_STEPS:  # 防止死循环
                # 步数护栏：正常流程远小于 500 步，超限基本意味着网关成环或数据异常
                raise EngineError('流程流转步数超限，请检查网关连线是否成环')
            flow_id = queue.pop(0)  # 取一条顺序流
            flow = self.graph.flows.get(flow_id)  # 顺序流定义
            if not flow:  # 脏数据
                # 顺序流缺失属于脏数据，跳过该 token 继续处理后续边，避免整个流程失败
                continue
            target = self.graph.nodes.get(flow['target'])  # 目标节点
            if not target:  # 目标节点缺失
                # 目标节点缺失同理跳过
                continue
            self._enter(target, flow, queue)  # 进入目标节点
        _save_state(self.instance, self.state)  # 每轮推进后持久化状态

    # 分发入口：按节点类型分派；userTask 是唯一会暂停 token 的类型，其余节点自动向后推进
    def _enter(self, node, flow, queue):
        """进入节点：按类型决定暂停、分支、分流或结束。"""
        ntype = node['type']  # 节点类型
        if ntype == USER_TASK:  # 人工任务：生成待办并暂停该分支
            # 生成待办后当前分支停止，等审批动作再 continue_from
            self._create_tasks(node, flow)
            # 显式 return，避免继续执行后面的网关分支
            return
        if ntype == 'endEvent':  # 结束事件
            # 结束事件不直接改实例状态，统一交给 sync() 判定“所有分支都结束”
            self._on_end(node)
            # 终止当前分支
            return
        if ntype == 'exclusiveGateway':  # 排他网关：只走一条
            chosen = self._choose_flow(node)  # 选择条件成立的出边
            if chosen:  # 命中分支
                # 只追加一条命中边，实现排他语义
                queue.append(chosen)
            # 分支处理完毕，返回 _run 循环
            return
        if ntype == 'parallelGateway':  # 并行网关：分流或汇合
            if not self._join_ready(node, flow):  # 等待其他分支到达
                # 未集齐入边则暂停该 token，等待其他分支后续到达
                return
            queue.extend(list(node['outgoing']))  # 全部出边同时推进
            # 分流/汇合完成，继续推进全部出边
            return
        if ntype == 'inclusiveGateway':  # 包容网关按条件取多条出边
            for flow_id in node['outgoing']:  # 逐条判断
                cond = self.graph.condition(flow_id)  # 条件表达式
                if not cond or _eval_expr(cond, self.form_data):  # 无条件或条件成立
                    # 包容网关可命中多条出边，逐条入队
                    queue.append(flow_id)
            # 所有命中边已入队，继续循环
            return
        # 其他任务（serviceTask/scriptTask/manualTask/subProcess）自动通过
        queue.extend(list(node['outgoing']))

    # 排他选路优先级：按连线声明顺序找第一条成立的条件流；无条件连线视作 else；最后才用 default
    def _choose_flow(self, node):
        """排他网关选路：条件成立的第一条，否则走默认流。"""
        for flow_id in node['outgoing']:  # 按连线顺序判断
            cond = self.graph.condition(flow_id)  # 条件
            if cond and _eval_expr(cond, self.form_data):  # 条件成立
                # 第一条成立即命中，保证排他性
                return flow_id
            if not cond:  # 无条件连线视为默认命中
                # 无条件流等价于 else，直接命中
                return flow_id
        return node.get('default')  # 回退网关 default 属性

    # 并行汇合判定：单入边视为分叉直接放行；否则记录已到达的 flow，集齐后才放行出边
    def _join_ready(self, node, flow):
        """并行网关汇合判断：所有入边都到达后才放行。"""
        incoming = node['incoming']  # 入边数量
        if len(incoming) <= 1:  # 单入边视为分流
            # 单入边/零入边是分流节点，无需等待
            return True
        arrivals = self.state['arrivals'].setdefault(node['id'], [])  # 已到达的入边
        if flow['id'] not in arrivals:  # 记录本次到达
            # 记录本次到达的入边 ID，用于去重计数
            arrivals.append(flow['id'])
        if len(arrivals) < len(incoming):  # 还没全部到达
            # 还有分支未到，暂停当前 token
            return False
        self.state['arrivals'][node['id']] = []  # 汇合成功，清空记录供下一轮使用
        # 汇合完成并清空记录，允许下一轮流程重新进入该节点
        return True

    # 结束节点处理：只登记轨迹，不改实例状态，避免并行分支提前结束整单
    def _on_end(self, node):
        """结束事件：仅在无未完成待办时把实例置为完成。"""
        # 终态统一在 sync() 中处理，这里只记录轨迹节点
        names = self.state.setdefault('ended_nodes', [])  # 已结束节点列表
        if node['id'] not in names:  # 去重记录
            # 同一结束节点可能被多条路径命中，去重避免 state 膨胀
            names.append(node['id'])

    # ------------------------------------------------------------ 任务生成
    # 建任务幂等：同一实例同一 userTask 只要还有未完成任务就跳过，防止并行/回退重复建单
    def _create_tasks(self, node, flow):
        """为人工任务节点生成待办：解析审批人、审批方式、抄送与到期时间。"""
        pending = WfTask.objects.filter(instance_id=self.instance.id, task_key=node['id'],
                                        status=0, is_deleted=0)  # 节点已有待办则跳过
        if pending.exists():  # 防止循环/重复进入重复建任务
            # 已有待办说明该节点仍在处理中，本次进入不重复生成
            return
        cfg = self.graph.cfg(node['id'], self.node_config)  # 节点配置
        assignees = self._resolve_assignees(cfg)  # 解析审批人
        if not assignees:  # 无审批人时兜底发起人，保证流程可继续
            # 审批人解析为空时兜底发起人，避免流程卡死在无人可审的节点
            assignees = [self.instance.start_user_id]
        assignees = self._dedupe(assignees)  # 去重保持顺序
        self._make_cc(node, cfg.get('ccUserIds') or [])  # 进入节点即抄送
        mode = cfg['approveMode']  # 审批方式
        if mode not in (1, 2, 3):  # 非法值回退或签
            # 配置漂移/历史数据可能出现非法值，统一按或签（2）处理
            mode = 2
        if mode == 1 and len(assignees) > 1:  # 串行：只建第一个人的任务
            self.state['serial'][node['id']] = assignees[1:]  # 其余排队
            # 只保留第一位处理人，其余进入 serial 队列，审批通过后逐个唤醒
            assignees = assignees[:1]
        else:
            self.state['serial'].pop(node['id'], None)  # 非串行清空历史队列
        due_time = None  # 到期时间
        if cfg.get('dueHours'):  # 配置了超时小时数
            due_time = _now() + timedelta(hours=float(cfg['dueHours']))  # 计算截止时间
        now = _now()  # 统一时间
        for uid in assignees:  # 逐个生成待办
            # 每个审批人一条 wf_task：status=0 待办、approve_mode 记录该节点审批方式
            WfTask.objects.create(
                instance_id=self.instance.id, task_key=node['id'], task_name=node['name'],
                assignee=uid, status=0, approve_mode=mode, due_time=due_time,
                # 审计列：发起人作为创建人，统一使用同一次 now，保证待办时间一致
                start_time=now, create_by=self.instance.create_by or 'system',
                create_time=now, update_by=self.instance.create_by or 'system', update_time=now,
                is_deleted=0,
            )
        fire_listeners(self.model, 'enter', self.instance, node['name'])  # 节点进入事件
        self.state['waiting_node'] = node['id']  # 记录最近生成的节点

    # 审批人策略分派：starter 发起人 / user 指定用户 / role 角色 / dept 部门 / group 分组 / expression 表达式
    def _resolve_assignees(self, cfg):
        """按配置策略解析审批人用户 ID 列表。"""
        kind = cfg['assigneeType']  # 策略类型
        if kind == 'starter':  # 发起人本人
            # 发起人节点：直接取实例发起人，无需查库
            return [self.instance.start_user_id]
        if kind == 'user':  # 指定用户
            return [int(x) for x in cfg['userIds'] if str(x).isdigit()]
        if kind == 'role':  # 指定角色下的启用用户
            role_ids = [int(x) for x in cfg['roleIds'] if str(x).isdigit()]
            if not role_ids:  # 未选角色
                # 未选择角色时不返回任何人，交由 _create_tasks 兜底发起人
                return []
            from django.db import connection  # 局部导入，避免模块级依赖
            with connection.cursor() as cursor:  # 复用项目数据库连接
                placeholders = ','.join(['%s'] * len(role_ids))  # 参数占位
                # SQL 直查角色-用户关联：一次查询避免 ORM 反查 sys_role 的额外开销
                cursor.execute(
                    # 关联 sys_user 并过滤未删除、启用状态，保证只返回有效账号
                    'SELECT ur.user_id FROM sys_user_role ur JOIN sys_user u ON u.id = ur.user_id '
                    # 占位符按 role_ids 数量动态生成，参数仍通过 %s 绑定，避免拼接注入
                    'AND u.is_deleted = 0 AND u.status = 0 WHERE ur.role_id IN (%s)' % placeholders,
                    role_ids)
                return [row[0] for row in cursor.fetchall()]  # 返回用户 ID
        if kind == 'dept':  # 指定部门
            dept_ids = [int(x) for x in cfg['deptIds'] if str(x).isdigit()]
            if not dept_ids:  # 未选部门
                # 未选择部门同样返回空，走兜底逻辑
                return []
            # 部门策略按 sys_user.dept_id 过滤有效用户
            return list(SysUser.objects.filter(dept_id__in=dept_ids, status=0, is_deleted=0)
                        .values_list('id', flat=True))
        if kind == 'group':  # 指定用户分组
            if not cfg['groupId']:  # 未选分组
                # 未选择分组返回空
                return []
            ids = list(WfGroupUser.objects.filter(group_id=cfg['groupId']).values_list('user_id', flat=True))  # 分组用户
            # 分组关系表可能保留已停用用户，二次过滤保证审批人有效
            return list(SysUser.objects.filter(id__in=ids, status=0, is_deleted=0)
                        .values_list('id', flat=True))  # 过滤有效账号
        if kind == 'expression':  # 动态表达式：结果按用户 ID 列表解析
            value = self._eval_assignee_expr(cfg.get('expr'))
            if isinstance(value, (list, tuple)):  # 列表形式
                # 表达式返回数组：逐项转 int 并过滤非法值
                return [int(x) for x in value if str(x).isdigit()]
            if str(value).isdigit():  # 单个 ID
                # 表达式返回单个用户 ID
                return [int(value)]
            # 表达式无结果或类型不支持时返回空
            return []
        return []  # 未知策略

    # 动态审批人表达式：与网关条件共用受限 eval 思路，但返回用户 ID/列表而不是布尔值
    def _eval_assignee_expr(self, expr):
        """执行动态审批人表达式，失败返回空值。"""
        text = (expr or '').strip()  # 去空白
        if text.startswith('${') and text.endswith('}'):  # 去包装
            # 剥离 ${...} 外壳后再求值
            text = text[2:-1]
        try:
            # 清空内置函数，仅允许读取表单数据；form 对象与扁平字段同时暴露
            return eval(text, {'__builtins__': {}}, {'form': AttrDict(self.form_data), **self.form_data})
        except Exception:  # 表达式非法
            # 失败返回 None，由上层按空审批人处理
            return None

    # 入参可能来自多策略合并，去重同时保留配置顺序
    @staticmethod  # 静态方法：去重不依赖引擎运行状态
    def _dedupe(ids):
        """去重并保持顺序，避免同一人重复收到待办。"""
        result = []  # 结果列表
        for uid in ids:  # 逐个处理
            if uid and uid not in result:  # 未出现过才加入
                # 空值（None/0）与重复 ID 不再加入
                result.append(uid)
        return result  # 返回去重列表

    # 抄送：进入节点时即写 wf_cc，只读通知；按 (实例, 节点, 用户) 判重，避免回退/重入重复抄送
    def _make_cc(self, node, user_ids):
        """生成抄送记录，同一实例同节点同用户只写一次。"""
        now = _now()  # 抄送时间
        for uid in self._dedupe([int(x) for x in user_ids if str(x).isdigit()]):  # 逐个抄送
            exists = WfCc.objects.filter(instance_id=self.instance.id, user_id=uid,
                                         node_id=node['id']).exists()  # 防重复
            if exists:  # 已抄送过
                # 已存在抄送记录直接跳过
                continue
            # status=0 未读，接收人在“抄送我的”列表标记已读
            WfCc.objects.create(instance_id=self.instance.id, user_id=uid, node_id=node['id'],
                                status=0, create_time=now)  # 写入抄送记录

    # ------------------------------------------------------------ 状态同步
    # 汇总同步：以未完成待办推导当前节点；没有待办且实例仍运行则收敛为完成并触发 end 监听
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

    # 审批留痕：提交/同意/驳回/转审/加签/退回/撤回/终止等动作统一写 wf_audit，供轨迹页与已办查询
    def record(self, operator_id, action, comment='', task=None, node_id=None, node_name=None):
        """写入审批记录，供轨迹与已办查询。"""
        # 一条动作一条记录；task 为空时表示流程级动作（如提交、撤回）
        WfAudit.objects.create(
            instance_id=self.instance.id,
            # 记录操作人、动作、意见与所在节点，node_name 用于前端直接展示
            task_id=task.id if task else None, operator_id=operator_id, action=action,
            comment=comment, node_id=node_id, node_name=node_name, create_time=_now(),
        )


# -------------------------------------------------------------- 任务动作工具
# 批量关闭：按 status 置为已办/驳回/终止；限定 node_id 时只影响该节点，否则关闭实例全部待办
def close_tasks(instance_id, node_id=None, operator_id=None, status=1):
    """关闭实例下（可限定节点）的待办任务。"""
    qs = WfTask.objects.filter(instance_id=instance_id, status=0, is_deleted=0)  # 未完成待办
    if node_id:  # 限定节点
        # 只关闭指定 BPMN 节点（task_key）的任务
        qs = qs.filter(task_key=node_id)
    qs.update(status=status, end_time=_now(), update_by=str(operator_id or ''),
              update_time=_now())  # 批量置为已办/驳回


# 同意主流程：先落审批记录与任务完成态，再按 approve_mode 决定唤醒下一人/关闭其他人/等待会签/继续流转
def approve_task(instance, model, task, operator_id, comment=''):
    """同意任务：按串行/或签/会签规则推进流程。"""
    engine = WorkflowEngine(instance, model)  # 构造引擎
    engine.record(operator_id, 'approve', comment, task, task.task_key, task.task_name)  # 先记审批意见
    task.status = 1  # 当前任务已办
    task.end_time = _now()  # 完成时间
    task.update_by = str(operator_id)  # 更新人
    task.update_time = _now()  # 更新时间
    # 只更新任务状态相关列，避免覆盖其他字段
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
            # 串行下一位：沿用节点与原到期时间，approve_mode 仍为 1
            WfTask.objects.create(
                instance_id=instance.id, task_key=node_id,
                task_name=engine.graph.node(node_id)['name'], assignee=next_uid,
                # 待办属性与首人保持一致，仅 assignee 换成队列中的下一位
                status=0, approve_mode=1, due_time=task.due_time,
                start_time=now, create_by=instance.create_by or 'system', create_time=now,
                update_by=instance.create_by or 'system', update_time=now, is_deleted=0)  # 生成下一位待办
            engine.sync()  # 同步当前节点
            # 串行节点尚未走完，不能触发 continue_from
            return
        engine.state['serial'].pop(node_id, None)  # 队列清空
    elif mode == 2:  # 或签：其他人待办直接关闭
        # 或签：任一人通过即代表节点通过，其余待办批量置为已办
        close_tasks(instance.id, node_id, operator_id, status=1)
    else:  # 会签：还有其他人未处理则等待
        others = WfTask.objects.filter(instance_id=instance.id, task_key=node_id,
                                       status=0, is_deleted=0)  # 其余待办
        if others.exists():  # 仍需等待
            engine.sync()  # 仅同步当前节点
            # 还有人未签，仅同步当前节点，流程继续等待
            return
    # 节点已完成（或签/串行结束/会签集齐），沿出边继续流转
    engine.continue_from(node_id)  # 节点完成，继续流转
    fire_listeners(model, 'complete', instance, task.task_name)  # 节点完成事件


# 驳回：记录意见 → 关闭实例下全部待办（status=4）→ 实例置 2 已驳回 → 触发 reject 监听
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


# 转审：原处理人把任务交给他人，原任务记 2 已转派，新建同节点同审批方式待办
def transfer_task(instance, model, task, operator_id, target_id, comment=''):
    """转审：原任务置为已转派，为目标用户新建同节点待办。"""
    engine = WorkflowEngine(instance, model)  # 构造引擎
    engine.record(operator_id, 'transfer', comment, task, task.task_key, task.task_name)  # 审批记录
    task.status = 2  # 原任务已转派
    task.end_time = _now()  # 完成时间
    task.update_by = str(operator_id)  # 更新人
    task.update_time = _now()  # 更新时间
    # 原任务保留轨迹但不计入待办，故不再参与 sync 的待办统计
    task.save(update_fields=['status', 'end_time', 'update_by', 'update_time'])
    now = _now()  # 当前时间
    # 新任务继承节点、审批方式、优先级与到期时间，仅处理人替换为目标用户
    WfTask.objects.create(
        instance_id=instance.id, task_key=task.task_key, task_name=task.task_name,
        # 原到期时间与优先级一并继承，避免转审重置超时策略
        assignee=target_id, status=0, approve_mode=task.approve_mode, priority=task.priority,
        due_time=task.due_time, start_time=now, create_by=instance.create_by or 'system',
        create_time=now, update_by=instance.create_by or 'system', update_time=now,
        is_deleted=0)  # 新处理人待办
    engine.sync()  # 同步当前节点


# 加签：保留原任务并改为会签语义，新增一条 approve_mode=3 待办；节点需所有人完成才流转
def addsign_task(instance, model, task, operator_id, target_id, comment=''):
    """加签：新增一名会签人，节点需全部通过后才继续。"""
    engine = WorkflowEngine(instance, model)  # 构造引擎
    engine.record(operator_id, 'addsign', comment, task, task.task_key, task.task_name)  # 审批记录
    now = _now()  # 当前时间
    # 加签任务默认会签，即使原节点是或签/串行也改为“全部通过”语义
    WfTask.objects.create(
        instance_id=instance.id, task_key=task.task_key, task_name=task.task_name,
        # 继承原任务优先级与到期时间，新加签人同样受超时约束
        assignee=target_id, status=0, approve_mode=3, priority=task.priority,
        due_time=task.due_time, start_time=now, create_by=instance.create_by or 'system',
        create_time=now, update_by=instance.create_by or 'system', update_time=now, is_deleted=0)  # 加签待办
    # 关键：原任务审批方式同步改为 3，否则同意时会被当成或签而提前关闭节点
    WfTask.objects.filter(id=task.id).update(approve_mode=3)  # 原任务改为会签语义
    engine.sync()  # 同步当前节点


# 退回上一步：关闭当前节点待办并清串行队列，在上游最近 userTask 重建任务；实例从终态恢复为运行中
def back_task(instance, model, task, operator_id, comment=''):
    """退回上一步：关闭当前节点待办，在上一个人工节点重新生成任务。"""
    engine = WorkflowEngine(instance, model)  # 构造引擎
    previous = engine.graph.previous_user_task(task.task_key)  # 上游人工节点
    if not previous:  # 没有可退回节点
        # 上游没有人工节点（如直接连 startEvent）时无法回退，抛业务异常给前端
        raise EngineError('当前节点没有可退回的上一步')
    engine.record(operator_id, 'back', comment, task, task.task_key, task.task_name)  # 审批记录
    close_tasks(instance.id, task.task_key, operator_id, status=4)  # 关闭当前节点全部待办
    engine.state['serial'].pop(task.task_key, None)  # 清理串行队列
    engine.state['waiting_node'] = previous  # 记录回退节点
    engine._create_tasks(engine.graph.node(previous), {'id': ''})  # 在上游节点重建待办
    # 实例可能已因驳回/终止变为终态，退回后必须恢复为运行中
    instance.status = 0  # 恢复运行中
    instance.end_time = None  # 清空结束时间
    engine.sync()  # 同步当前节点


# 撤回：仅允许发起人在无人同意前操作；关闭全部待办并把实例置 3 已终止，同时保留 withdraw 轨迹
def withdraw_instance(instance, operator_id, comment=''):
    """撤回：发起人在无人审批前终止自己的流程。"""
    approved = WfAudit.objects.filter(instance_id=instance.id, action='approve').exists()  # 是否已有人审批
    if approved:  # 已有审批不可撤回
        # 已有任何同意记录即不可撤回，防止审批结果被发起人单方面抹掉
        raise EngineError('流程已被审批，无法撤回')
    close_tasks(instance.id, None, operator_id, status=4)  # 关闭全部待办
    # 撤回同样写审计记录，node_name 固定为“发起人”便于轨迹展示
    WfAudit.objects.create(instance_id=instance.id, operator_id=operator_id, action='withdraw',
                           comment=comment or '发起人撤回', node_id=None, node_name='发起人', create_time=_now())  # 撤回记录
    instance.status = 3  # 置为已终止
    instance.end_time = _now()  # 结束时间
    instance.update_time = _now()  # 更新时间
    instance.save(update_fields=['status', 'end_time', 'update_time'])  # 持久化


# 管理员终止：不做“是否已审批”限制；关闭待办、写 terminate 轨迹、实例置 3 并触发 end 监听
def terminate_instance(instance, model, operator_id, comment=''):
    """管理员强制终止流程。"""
    close_tasks(instance.id, None, operator_id, status=4)  # 关闭全部待办
    # 记录操作人（管理员）与终止原因
    WfAudit.objects.create(instance_id=instance.id, operator_id=operator_id, action='terminate',
                           comment=comment or '管理员终止', node_id=None, node_name='系统', create_time=_now())  # 终止记录
    instance.status = 3  # 已终止
    instance.end_time = _now()  # 结束时间
    instance.update_time = _now()  # 更新时间
    instance.save(update_fields=['status', 'end_time', 'update_time'])  # 持久化
    fire_listeners(model, 'end', instance, '终止')  # 结束事件
