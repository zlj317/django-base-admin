"""工单模块视图集。"""
# 文件：apps/wo/views.py —— 工单模块的接口实现
# 用途：提供工单类型、工单主体、工单日志三类资源的增删改查，并在工单上挂载
#       assign（指派处理人）、solve（标记已解决）、close（关闭）三个流转动作。
# 对应表：work_order_type、work_order、work_order_log（手建表，managed=False）。
# 路由前缀：/api/wo/type/、/api/wo/order/、/api/wo/log/（见 apps/wo/urls.py）。
# 状态流转：新建工单 status=0 待处理；assign 写入 assignee_id 并记日志；solve 置 2 已解决；
#           close 置 3 已关闭并写 close_time；每次流转调用 _write_log 追加一条 work_order_log。
# 权限约定：基类按 perm_prefix 自动生成 wo:list/create/update/delete 四个权限标识，
#           自定义动作（assign/solve/close）未写入 perm_map，因此当前实现里不做细粒度校验。
# 响应约定：全部通过 common.response 的 ok/fail 返回 {code, msg, data} 结构，HTTP 状态保持 200。
import time  # 生成日志时间

from rest_framework.decorators import action  # 自定义路由装饰器

from common.pagination import StandardPagination  # 统一分页
from common.response import fail, ok  # 统一响应封装
from common.views import CrudViewSet  # 通用 CRUD 基类

from apps.wo.models import WorkOrder, WorkOrderLog, WorkOrderType  # 工单相关模型
from apps.wo.serializers import WorkOrderLogSerializer, WorkOrderSerializer, WorkOrderTypeSerializer  # 对应序列化器


# 工单类型视图集：维护工单分类，接口行为全部由 CRUD 基类提供
class WOTypeViewSet(CrudViewSet):
    # 只声明配置不重写方法：增删改查、筛选、分页全部复用 CrudViewSet 的实现
    """工单类型 CRUD。"""
    # 目标模型：基类据此构建查询集并执行增删改
    model = WorkOrderType
    # 序列化器：列表输出与新增/编辑校验共用同一个全字段序列化器
    serializer_class = WorkOrderTypeSerializer
    # 权限前缀：基类据此生成 wo:list、wo:create、wo:update、wo:delete 四个权限标识
    perm_prefix = 'wo'
    # 查询参数映射：参数名 -> ORM lookup，基类 list 时按白名单动态拼接过滤条件
    filter_map = {
        # 类型名称模糊搜索：支持按关键字查找分类
        'type_name': 'icontains',
        # 状态精确匹配：前端按启用/停用筛选
        'status': 'exact',
    }
    # 筛选白名单到此结束：仅这两个参数参与过滤，其余查询参数会被忽略
    # 默认排序：与模型 Meta 的 sort 升序保持一致，保证下拉框顺序符合人工配置
    order_by = 'sort'
    # 操作日志模块名：便于把工单类型的增删改归入"工单类型"模块统计
    module_name = '工单类型'


# 工单视图集：工单主体 CRUD 之外，额外提供指派、解决、关闭三个流转动作
class WorkOrderViewSet(CrudViewSet):
    # 在基类 CRUD 之上扩展三个流转动作；动作方法通过 @action 声明，再在 urls.py 显式挂载
    """工单 CRUD + assign/solve/close 动作。"""
    # 目标模型：工单主体表 work_order
    model = WorkOrder
    # 序列化器：工单全字段，动作接口回写最新对象也复用它
    serializer_class = WorkOrderSerializer
    # 权限前缀：标准四个动作使用 wo:list/create/update/delete
    perm_prefix = 'wo'
    # 查询参数映射：覆盖标题/编号/状态/优先级/创建人/处理人六类常用筛选维度
    filter_map = {
        # 标题模糊搜索：前端搜索框常用字段
        'title': 'icontains',
        # 工单编号模糊搜索：支持按业务编号片段检索
        'order_no': 'icontains',
        # 状态精确匹配：按待处理/处理中/已解决/已关闭筛选
        'status': 'exact',
        # 优先级精确匹配：1 低 / 2 中 / 3 高
        'priority': 'exact',
        # 创建人精确匹配："我的工单"按我提交的过滤
        'creator_id': 'exact',
        # 处理人精确匹配：查看指派给我的工单
        'assignee_id': 'exact',
        # 筛选白名单结束；creator_id/assignee_id 分别支撑"我提交的"和"指派给我的"两种视图
    }
    # 默认排序：雪花 ID 趋势递增，倒序即最新工单在前
    order_by = '-id'
    # 操作日志模块名：工单管理
    module_name = '工单管理'

    # 内部方法：统一写入 work_order_log，避免 assign/solve/close 三处重复拼装日志对象
    def _write_log(self, order_id, operator_id, action, comment=''):
        # 日志字段统一在此拼装：工单 ID、操作人、动作、备注、写入时间
        """内部方法：向 work_order_log 插入一条日志。"""
        # 直接 create 落库；create_time 用字符串传入，由 Django DateTimeField 解析为日期时间
        WorkOrderLog.objects.create(
            # 关联的工单主键，日志详情页按该字段聚合时间线
            order_id=order_id,
            # 操作人 ID：从 request.user_info 取值，未登录时为 None
            operator_id=operator_id,
            # 动作标识：assign / solve / close，前端据此渲染不同节点样式
            action=action,
            # 动作备注：默认空串，动作接口可传 comment 覆盖
            comment=comment,
            # 记录日志产生时刻，便于时间线按时间排序
            create_time=time.strftime('%Y-%m-%d %H:%M:%S'),
        # create 立即落库；日志与工单同库同连接，详情页刷新即可看到新记录
        )

    # 指派动作：PUT /api/wo/order/assign/<pk>，仅更新处理人并写一条 assign 日志
    @action(detail=True, methods=['put'])
    def assign(self, request, pk=None):
        # 只改变处理人，不修改工单状态，尽量缩小单次流转的影响面
        """指派处理人：assignee_id + 写 assign 日志。"""
        # 只查未逻辑删除的工单，避免对已删除数据执行流转
        row = WorkOrder.objects.filter(pk=pk, is_deleted=0).first()
        # 工单不存在（或已删除）时直接返回 404 业务码，不再写日志
        if not row:
            # 先做存在性判断，避免对空对象赋值后再 save 抛异常
            return fail('工单不存在', code=404)
        # 从请求上下文取当前登录用户（由认证中间件注入），用于审计与日志操作人
        user = getattr(request, 'user_info', None)
        # 请求体中的处理人 ID；前端传入字符串数字时 Django 在保存阶段会做类型转换
        assignee_id = request.data.get('assignee_id')
        # 未指定处理人视为参数错误，用 400 业务码提示，避免把工单派给空值
        if assignee_id is None:
            # 空值会写进 assignee_id，导致工单"已指派却无处理人"，因此直接拒绝
            return fail('请指定处理人', code=400)
        # 统一时间字符串，供 update_time 使用
        now = time.strftime('%Y-%m-%d %H:%M:%S')
        # 更新处理人字段：工单进入"已指派"状态
        row.assignee_id = assignee_id
        # 审计字段：记录最后修改人（未登录时留空串，避免写入 None 报错）
        row.update_by = user.username if user else ''
        # 审计字段：记录最后修改时间
        row.update_time = now
        # 保存本次变更（仅这三个字段变化，走模型 save 保证信号与默认值生效）
        row.save()
        # 写流转日志：操作人取用户 ID，备注记录被指派人，便于追溯"派给了谁"
        self._write_log(pk, getattr(user, 'id', None), 'assign',
                        # 备注写入被指派人 ID，便于在时间线中看出"派给了谁"
                        f'指派给用户ID {assignee_id}')
        # 返回最新工单数据，前端可直接刷新详情/列表行
        return ok(WorkOrderSerializer(row).data, '指派成功')

    # 解决动作：PUT /api/wo/order/solve/<pk>，把状态置为 2 并写日志
    @action(detail=True, methods=['put'])
    def solve(self, request, pk=None):
        # 仅置状态位，不写 close_time；关闭动作与解决动作在此明确分离
        """标记已解决：status=2 + 写 solve 日志。"""
        # 同样只处理未删除工单，防止通过流转接口修改已删除记录
        row = WorkOrder.objects.filter(pk=pk, is_deleted=0).first()
        # 工单不存在时返回 404，不产生日志
        if not row:
            # 提前返回，保证失败场景不会留下半条流转记录
            return fail('工单不存在', code=404)
        # 当前操作人，用于审计与日志
        user = getattr(request, 'user_info', None)
        # 统一时间字符串
        now = time.strftime('%Y-%m-%d %H:%M:%S')
        # 状态置 2：已解决（此时尚未关闭，close_time 仍为空）
        row.status = 2
        # 审计字段：最后修改人
        row.update_by = user.username if user else ''
        # 审计字段：最后修改时间
        row.update_time = now
        # 保存状态变更
        row.save()
        # 写日志：备注优先取请求体 comment，缺省用"已解决"，记录解决说明
        self._write_log(pk, getattr(user, 'id', None), 'solve',
                        # 解决说明由前端填写；未填时用默认文案，保证日志备注不为空
                        request.data.get('comment', '已解决'))
        # 返回最新工单数据
        return ok(WorkOrderSerializer(row).data, '解决成功')

    # 关闭动作：PUT /api/wo/order/close/<pk>，置状态 3、记录关闭时间并写日志
    @action(detail=True, methods=['put'])
    def close(self, request, pk=None):
        # 关闭是终态动作，同时落状态与关闭时间，便于统计处理时长
        """关闭工单：status=3 + close_time + 写 close 日志。"""
        # 只允许关闭未删除的工单
        row = WorkOrder.objects.filter(pk=pk, is_deleted=0).first()
        # 不存在则返回 404
        if not row:
            # 空对象无法写入关闭时间，直接提前返回
            return fail('工单不存在', code=404)
        # 当前操作人
        user = getattr(request, 'user_info', None)
        # 统一时间字符串，close_time 与 update_time 共用同一时刻，保证统计口径一致
        now = time.strftime('%Y-%m-%d %H:%M:%S')
        # 状态置 3：已关闭，工单不再参与"待处理/处理中"统计
        row.status = 3
        # 记录实际关闭时间，用于计算处理耗时
        row.close_time = now
        # 审计字段：最后修改人
        row.update_by = user.username if user else ''
        # 审计字段：最后修改时间
        row.update_time = now
        # 保存本次关闭结果
        row.save()
        # 写日志：备注优先取请求体 comment，缺省"已关闭"
        self._write_log(pk, getattr(user, 'id', None), 'close',
                        # 关闭原因由前端填写；未填时用默认文案，方便事后追溯
                        request.data.get('comment', '已关闭'))
        # 返回最新工单数据
        return ok(WorkOrderSerializer(row).data, '关闭成功')


# 工单日志视图集：日志的查询与维护（日志表无 is_deleted，需覆写 get_queryset）
class WOLogViewSet(CrudViewSet):
    # 日志表无 is_deleted 列，因此必须覆写查询集，其它 CRUD 行为仍由基类提供
    """工单日志 CRUD（不继承 BaseModel，覆写 get_queryset）。"""
    # 目标模型：work_order_log
    model = WorkOrderLog
    # 序列化器：日志全字段
    serializer_class = WorkOrderLogSerializer
    # 权限前缀：日志接口复用工单模块的 wo:list 等权限
    perm_prefix = 'wo'
    # 查询参数映射：只开放按工单 ID 精确查询，前端详情页据此拉取单张工单的时间线
    filter_map = {
        # 工单 ID 精确匹配
        'order_id': 'exact',
        # 只开放工单 ID 一个筛选维度：日志通常按单张工单查看，避免全表扫描式查询
    }
    # 默认排序：最新日志在前
    order_by = '-id'
    # 操作日志模块名：工单日志
    module_name = '工单日志'

    # 覆写基类查询集：基类默认过滤 is_deleted=0，而日志表没有该列，直接查询会报字段不存在
    def get_queryset(self):
        # 覆写原因：基类 get_queryset 会拼 is_deleted=0，本表无此列会直接报字段不存在
        """WorkOrderLog 无 is_deleted 字段，直接返回全部。"""
        # 显式按 order_by 排序，保持与其它模块一致的"最新在前"输出
        return WorkOrderLog.objects.order_by(self.order_by)
