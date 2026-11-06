"""脱敏配置模块视图集。"""
# 模块：apps/dsm/views.py —— 脱敏规则/字段/角色的 CRUD 接口
# 用途：维护脱敏规则的元数据、规则与业务字段的绑定、角色与规则的明文授权。
# 对应表：desensitize_rule、desensitize_field、desensitize_role。
# 路由前缀：/api/dsm/rule/*、/api/dsm/field/*、/api/dsm/role/*（apps/dsm/urls.py 生成，config/urls.py 挂载）。
# 脱敏策略：这里只有配置的读写，没有任何业务序列化器/中间件引用这些配置去改写响应，
#   因此脱敏是"配置/预留"，不会真正对接口输出生效（以代码为准）。
# 权限标识：三个视图集各自用 dsm:rule / dsm:field / dsm:role 前缀，
#   由 CrudViewSet.permission_classes 动态生成 list/create/update/delete 四个权限点。
# 注意：rule 的 status 自定义动作未写入 perm_map，按 PermissionCheck 规则只校验登录、不校验按钮权限。
# 统一分页器，输出 {total,page,page_size,list}
from common.pagination import StandardPagination
# 通用 CRUD 基类：提供筛选/分页/审计字段/逻辑删除与按钮权限
from common.views import CrudViewSet

from apps.dsm.models import DesensitizeField, DesensitizeRole, DesensitizeRule
from apps.dsm.serializers import (
    DesensitizeFieldSerializer,
    DesensitizeRoleSerializer,
    DesensitizeRuleSerializer,
)


# 脱敏规则视图集：规则主表的标准 CRUD（含启停动作，路由在 urls.py 中单独挂载）
class DesensitizeRuleViewSet(CrudViewSet):
    """脱敏规则 CRUD。"""
    # 目标模型：继承 BaseModel（含 is_deleted），基类查询会自动过滤逻辑删除记录
    model = DesensitizeRule
    # 序列化器：列表输出与新增/修改校验共用，字段由 fields='__all__' 决定
    serializer_class = DesensitizeRuleSerializer
    # 权限前缀：生成 dsm:rule:list / dsm:rule:create / dsm:rule:update / dsm:rule:delete
    # 种子脚本只创建了这四个按钮权限，前端菜单也绑定到 dsm:rule:list
    perm_prefix = 'dsm:rule'
    # 查询参数 → ORM lookup 白名单；参数名固定为后端字段，用户只能传值，不存在字段注入
    filter_map = {
        # 规则名称模糊搜索，便于按关键字查找
        'rule_name': 'icontains',
        # 规则类型精确匹配（phone/idcard/bank/email/custom）
        'rule_type': 'exact',
        # 状态精确匹配：1=启用、0=停用
        'status': 'exact',
    }
    # 按雪花 ID 倒序：ID 递增，等价于最新创建的规则排在前面，分页结果稳定
    order_by = '-id'
    # 操作日志模块名，供日志/审计扩展标识业务来源（基类当前未直接使用）
    module_name = '脱敏规则'


# 脱敏字段视图集：维护"规则 → 业务类型 + 字段名"的绑定
class DesensitizeFieldViewSet(CrudViewSet):
    """脱敏字段 CRUD。"""
    # 目标模型：未继承 BaseModel，没有 is_deleted/审计字段，删除会走物理删除分支
    model = DesensitizeField
    # 序列化器：输出 id、rule_id、biz_type、field_name、status、create_time
    serializer_class = DesensitizeFieldSerializer
    # 权限前缀：生成 dsm:field:list 等四个权限点；注意种子脚本未创建这组按钮权限，
    # 因此除非手工在菜单里授权，普通角色调用这些接口会返回 403（疑似遗漏，仅记录未改）
    perm_prefix = 'dsm:field'
    # 支持的筛选参数：按规则 ID 精确查、按业务类型模糊查
    filter_map = {
        # 规则 ID 精确匹配，用于查看某条规则绑定了哪些字段
        'rule_id': 'exact',
        # 业务类型模糊匹配，如按 system 找出系统模块下所有字段配置
        'biz_type': 'icontains',
    }
    # 默认按雪花 ID 倒序
    order_by = '-id'
    # 操作日志模块名
    module_name = '脱敏字段'

    # 重写查询集：该表没有 is_deleted 列，不能复用基类的 is_deleted=0 过滤（否则 SQL 报错）
    def get_queryset(self):
        # 直接按排序字段返回全表查询集；本表无逻辑删除语义
        return self.model.objects.order_by(self.order_by)

    # 重写列表：逻辑与基类 list 相同（筛选 + 分页），之所以重写是为了配合上面的查询集覆盖
    def list(self, request):
        # 先按 filter_map 拼接筛选条件，保证分页 total 反映筛选后的条数
        queryset = self.apply_filters(self.get_queryset(), request)
        # 交给统一分页器完成 count、切片与序列化，返回 {code,msg,data} 结构
        return StandardPagination(request).paginate(queryset, self.get_serializer_class())


# 脱敏角色视图集：维护"角色 → 规则"的明文/豁免授权关系
class DesensitizeRoleViewSet(CrudViewSet):
    """脱敏角色 CRUD。"""
    # 目标模型：同样未继承 BaseModel，无逻辑删除列
    model = DesensitizeRole
    # 序列化器：输出 id、role_id、rule_id、create_time
    serializer_class = DesensitizeRoleSerializer
    # 权限前缀：生成 dsm:role:* 四个权限点；与 field 一样未在种子脚本中创建按钮权限
    perm_prefix = 'dsm:role'
    # 筛选参数：按角色 ID、规则 ID 精确查询，便于展示某角色被豁免了哪些规则
    filter_map = {
        # 角色 ID 精确匹配
        'role_id': 'exact',
        # 规则 ID 精确匹配
        'rule_id': 'exact',
    }
    # 默认按雪花 ID 倒序
    order_by = '-id'
    # 操作日志模块名
    module_name = '脱敏角色'

    # 重写查询集：表无 is_deleted 列，直接全表查询，避免基类过滤条件导致报错
    def get_queryset(self):
        # 仅按 ID 倒序，不做逻辑删除过滤
        return self.model.objects.order_by(self.order_by)

    # 重写列表：与字段视图集一致，筛选后交给统一分页器
    def list(self, request):
        # 应用白名单筛选条件
        queryset = self.apply_filters(self.get_queryset(), request)
        # 分页 + 序列化 + 统一响应包装
        return StandardPagination(request).paginate(queryset, self.get_serializer_class())
