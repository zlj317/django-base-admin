"""编码规则模块视图集。"""
# 模块：apps/sys_no/views.py —— 编码规则的增删改查与"生成编号"接口
# 用途：SysNoRuleViewSet 管理规则（CRUD + generate 取号并写日志）；
#       SysNoLogViewSet 提供生成日志的查询与删除（日志表无 is_deleted，删除为物理删除）。
# 路由前缀：/sys_no/rule/*（list / create / delete / update/<pk> / generate/<pk>）；
#           /sys_no/log/*（list / create / delete / update/<pk> / status/<pk>）。
# 权限：perm_prefix='sys_no'，基类据此生成 sys_no:list / create / update / delete 四个权限标识；
#       generate 是自定义动作，基类未纳入 perm_map，因此不会被权限点拦截（见主报告"疑似问题"）。
# 幂等性：generate 每次调用都会递增 seq_current 并新增一条 SysNoLog，重复点击会产生多个编号，非幂等。
from rest_framework.decorators import action

from common.response import fail, ok
from common.views import CrudViewSet

from apps.sys_no.models import SysNoLog, SysNoRule
from apps.sys_no.serializers import SysNoLogSerializer, SysNoRuleSerializer


# 规则视图集：继承通用 CRUD，额外提供 generate 生成编号动作
class SysNoRuleViewSet(CrudViewSet):
    """编码规则表 CRUD。"""
    # 目标模型：基类的 list/create/update/delete 均基于该模型
    model = SysNoRule
    # 序列化器：基类用于输出与入参校验
    serializer_class = SysNoRuleSerializer
    # 权限前缀：生成 sys_no:list / sys_no:create / sys_no:update / sys_no:delete
    perm_prefix = 'sys_no'
    # 查询参数 → ORM lookup 白名单：只允许按规则编码/名称模糊搜索、按状态精确筛选
    filter_map = {
        # 规则编码模糊匹配，便于按业务编码片段检索
        'rule_key': 'icontains',
        # 规则名称模糊匹配，支持中文关键字
        'rule_name': 'icontains',
        # 状态精确匹配（1 启用 / 0 停用）
        'status': 'exact',
    }
    # 默认排序：主键倒序，最新创建的规则排在最前
    order_by = '-id'
    # 操作日志模块名（供子类写操作日志时使用）
    module_name = '编码规则管理'

    # 生成编号动作：detail=True 表示 URL 需携带 pk；methods=['post'] 表示这是写操作
    @action(detail=True, methods=['post'])
    def generate(self, request, pk=None):
        """模拟生成一个编号：拼接前缀+日期+流水号并记录日志。"""
        # 只在未删除规则中查找（显式 is_deleted=0，与基类 get_queryset 语义一致）
        row = SysNoRule.objects.filter(pk=pk, is_deleted=0).first()
        # 规则不存在或已删除时返回业务码 404，避免生成无归属的编号
        if not row:
            return fail('规则不存在', code=404)
        # 局部导入 datetime：仅本动作需要当前时间，放函数内可减少模块顶部依赖
        import datetime
        # 取服务器本地当前时间，作为日期段与日志生成时间
        now = datetime.datetime.now()
        # 流水递增：当前流水加上步长后写回对象（先读后写非原子，并发下可能取到重复流水）
        row.seq_current = (row.seq_current or 0) + row.step
        # 仅提交流水与更新时间两列；但 update_time 未赋新值，实际不会被刷新（见主报告"疑似问题"）
        row.save(update_fields=['seq_current', 'update_time'])
        # 日期段：硬编码 %Y%m%d，未使用模型里的 date_format；reset_type/reset_time 也未生效
        date_part = now.strftime('%Y%m%d')
        # 流水段：左侧补 0 到 seq_length 位（配置为空或 0 时兜底为 4 位）
        seq = str(row.seq_current).zfill(row.seq_length or 4)
        # 分隔符：允许为空串，此时前缀/日期/流水直接相连
        sep = row.separator or ''
        # 最终编号：前缀 + 分隔符 + 日期 + 分隔符 + 流水，与前端约定的展示格式一致
        no_value = f"{row.prefix}{sep}{date_part}{sep}{seq}"
        # 当前登录用户由认证中间件注入；未登录为 None，仅用于日志，不阻断生成
        user = getattr(request, 'user_info', None)
        # 写生成日志：记录规则、编号、业务类型/业务 ID、操作人与生成时间，供审计追溯
        SysNoLog.objects.create(
            # 关联规则主键，便于按规则统计取号量
            rule_id=row.id,
            # 本次生成的编号字符串
            no_value=no_value,
            # 业务类型：由前端可选传入，未传为 None
            biz_type=request.data.get('biz_type'),
            # 业务 ID：由前端可选传入，用于反查具体单据
            biz_id=request.data.get('biz_id'),
            # 操作人主键：无登录信息时写 None
            gen_user_id=user.id if user else None,
            # 生成时间与日期段使用同一时刻，保证日期段与日志时间一致
            gen_time=now,
        )
        # 只返回编号，前端拿到后可直接填入业务单据的编号字段
        return ok({'no_value': no_value}, '生成成功')


# 日志视图集：日志表无 BaseModel 字段，需自行提供查询集
class SysNoLogViewSet(CrudViewSet):
    """编码生成日志表 CRUD（无 BaseModel，覆写 get_queryset）。"""
    # 目标模型：生成日志表
    model = SysNoLog
    # 序列化器：日志字段全部输出，便于审计查看
    serializer_class = SysNoLogSerializer
    # 权限前缀：与规则共用 sys_no 权限点（list/create/update/delete）
    perm_prefix = 'sys_no'
    # 查询参数 → ORM lookup：按规则主键精确筛选、按业务类型模糊筛选
    filter_map = {
        # 规则 ID 精确匹配，便于查看某条规则的取号历史
        'rule_id': 'exact',
        # 业务类型模糊匹配（icontains 为包含匹配）
        'biz_type': 'icontains',
    }
    # 排序：主键倒序，最新日志在前
    order_by = '-id'
    # 操作日志模块名
    module_name = '编码生成日志'

    # 覆写查询集：日志表没有 is_deleted 列，不能沿用基类的逻辑删除过滤
    def get_queryset(self):
        # 直接返回全量日志并排序；基类 delete 因模型无 is_deleted 会走物理删除分支
        return self.model.objects.order_by(self.order_by)
