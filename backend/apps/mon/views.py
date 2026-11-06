"""监控告警模块视图集。"""
# 模块：apps/mon/views.py —— 监控告警模块的 DRF 视图集
# 用途：对外提供告警规则的增删改查/启停，以及告警记录的查询与处理入口。
# 对应表：monitor_alarm_rule（规则）、monitor_alarm_record（告警记录）。
# 路由前缀：/api/mon/rule/*、/api/mon/record/*（由 apps/mon/urls.py 手工拼装，不走 router）。
# 告警生命周期：规则启用 → 采集判定命中 → 生成告警记录（handle_status=0 未处理）→
#               运维通过记录更新接口回写 handle_status=1、handler_id、handle_time 完成闭环。
# 权限：规则用 mon:rule:*，记录用 mon:record:*，由基类按 perm_prefix 动态生成。
# 统一分页器：解析 page/page_size 并包装响应
from common.pagination import StandardPagination
# 通用 CRUD 基类：提供 list/create/update/delete/status 与筛选
from common.views import CrudViewSet

# 本模块两个模型
from apps.mon.models import MonitorAlarmRecord, MonitorAlarmRule
# 对应序列化器
from apps.mon.serializers import MonitorAlarmRecordSerializer, MonitorAlarmRuleSerializer


# 规则视图集：四类标准动作 + 基类自带的 status 动作（路由 rule/status/<pk>）
class MonitorAlarmRuleViewSet(CrudViewSet):
    """监控告警规则 CRUD。"""
    # 目标模型：告警规则表；基类 get_queryset 会据此过滤 is_deleted=0
    model = MonitorAlarmRule
    # 序列化器：全字段输出/校验
    serializer_class = MonitorAlarmRuleSerializer
    # 权限前缀：拼出 mon:rule:list / create / update / delete
    perm_prefix = 'mon:rule'
    # 查询参数 → ORM lookup 白名单；未列出的参数不会被拼进 SQL 条件
    filter_map = {
        # 规则名称：模糊搜索，便于按关键字定位规则
        'rule_name': 'icontains',
        # 监控类型：精确匹配，如只看 service 类规则
        'monitor_type': 'exact',
        # 告警级别：精确匹配，按严重程度筛选
        'alarm_level': 'exact',
        # 状态：精确匹配，筛选启用/停用规则
        'status': 'exact',
    }
    # 列表默认按主键倒序，新增规则排在最前
    order_by = '-id'
    # 操作日志模块名（基类保留供子类/日志写入使用）
    module_name = '告警规则'

    # 重写 list：基类同样的“筛选 + 分页”流程，显式写出便于本模块单独调整
    def list(self, request):
        # 先按 filter_map 过滤，再交给分页器，保证 total 反映筛选后的条数
        queryset = self.apply_filters(self.get_queryset(), request)
        # paginate 内部完成 count、当前页切片与序列化，返回 {code,msg,data}
        return StandardPagination(request).paginate(queryset, self.get_serializer_class())


# 记录视图集：告警记录只读查询为主，处理动作通过通用 update 回写处理状态
class MonitorAlarmRecordViewSet(CrudViewSet):
    """告警记录 CRUD。"""
    # 目标模型：告警记录表
    model = MonitorAlarmRecord
    # 序列化器：全字段输出/校验
    serializer_class = MonitorAlarmRecordSerializer
    # 权限前缀：拼出 mon:record:list / create / update / delete
    perm_prefix = 'mon:record'
    # 查询参数 → ORM lookup 白名单
    filter_map = {
        # 规则 ID：精确匹配，查看某条规则产生的全部告警
        'rule_id': 'exact',
        # 告警级别：精确匹配，按严重程度过滤
        'alarm_level': 'exact',
        # 处理状态：精确匹配，0 未处理 / 1 已处理，用于待办列表
        'handle_status': 'exact',
    }
    # 默认按主键倒序，最新告警优先展示
    order_by = '-id'
    # 操作日志模块名
    module_name = '告警记录'

    # 覆盖基类查询集：记录表没有 is_deleted 列，不能沿用基类的逻辑删除过滤
    def get_queryset(self):
        # 直接取全表并按 order_by 排序；删除时基类也会因无 is_deleted 而走物理删除
        return self.model.objects.order_by(self.order_by)

    # 重写 list：记录表查询同样需要自定义 get_queryset，故显式复用相同流程
    def list(self, request):
        # 按 filter_map 过滤后再分页
        queryset = self.apply_filters(self.get_queryset(), request)
        # 返回统一分页结构，前端表格直接消费
        return StandardPagination(request).paginate(queryset, self.get_serializer_class())
