"""数据权限模块视图集。"""
# 文件：backend/apps/dp/views.py
# 用途：为数据权限规则表与角色授权关联表提供列表/新增/修改/删除/启停接口。
# 对应表：sys_data_permission、sys_role_data_permission。
# 路由前缀：/api/dp/permission/*、/api/dp/role_perm/*（见 apps/dp/urls.py）。
# 数据范围生效方式：这里仅做配置数据的 CRUD，没有在业务列表查询中拼装数据范围条件；
#   因此数据权限目前是"配置/预留"，不会真正限制任何业务数据，需后续在业务视图接入后才生效。
# 通用 CRUD 基类：提供分页/筛选/逻辑删除/审计字段/按钮权限
from common.views import CrudViewSet

# 本模块两张表模型：规则主表与角色授权关联表
from apps.dp.models import SysDataPermission, SysRoleDataPermission
# 对应序列化器：用于 CRUD 的输出序列化与入参校验
from apps.dp.serializers import SysDataPermissionSerializer, SysRoleDataPermissionSerializer


# 数据权限规则视图集：维护可复用的数据范围规则（全部/本部门/本部门及以下/自定义等）
class SysDataPermissionViewSet(CrudViewSet):
    """数据权限表 CRUD。"""
    # 目标模型：基类 get_queryset 会按 is_deleted=0 过滤，删除动作也改写该标记而非物理删除
    model = SysDataPermission
    # 序列化器：列表输出、创建/修改校验都使用它，字段集合由模型的 __all__ 决定
    serializer_class = SysDataPermissionSerializer
    # 权限前缀：基类自动生成 dp:list、dp:create、dp:update、dp:delete 四个按钮权限标识
    # 注意：本类的 status 自定义动作未登记进 perm_map，按基类规则该动作只校验登录、不校验按钮权限
    perm_prefix = 'dp'
    # 查询参数到 ORM lookup 的白名单映射；字段名由后端固定，用户只能传值，不存在字段注入
    filter_map = {
        # 权限名称模糊搜索，便于按关键字筛选规则
        'permission_name': 'icontains',
        # 权限类型精确匹配，如 all/dept/self/role
        'permission_type': 'exact',
        # 启用状态精确匹配：1=启用、0=停用
        'status': 'exact',
    }
    # 列表默认排序：雪花 ID 倒序，新建规则在前；分页结果稳定
    order_by = '-id'
    # 操作日志模块名，便于后续接入日志时标识业务来源（基类当前并未直接使用该属性）
    module_name = '数据权限配置'


# 角色-数据权限关联视图集：维护某角色被授予了哪些数据权限规则
class SysRoleDataPermissionViewSet(CrudViewSet):
    """角色-数据权限关联表 CRUD（无 BaseModel）。"""
    # 目标模型：该表不继承 BaseModel，没有 is_deleted 字段，删除会由基类走物理删除分支
    model = SysRoleDataPermission
    # 关联关系序列化器：输出 id、role_id、permission_id、create_time
    serializer_class = SysRoleDataPermissionSerializer
    # 与规则表共用 dp 权限前缀：拥有 dp 按钮权限即可维护角色授权关系
    perm_prefix = 'dp'
    # 支持的筛选参数：按角色 ID、权限规则 ID 精确查询，便于配置页展示某个角色的授权明细
    filter_map = {
        # 角色 ID 精确匹配
        'role_id': 'exact',
        # 数据权限规则 ID 精确匹配
        'permission_id': 'exact',
    }
    # 默认按雪花 ID 倒序，最新授权记录在前
    order_by = '-id'
    # 操作日志模块名，供日志/审计扩展使用
    module_name = '角色数据权限关联'

    # 重写查询集：关联表没有 is_deleted 列，不能复用基类 filter(is_deleted=0)，否则会抛 FieldError
    # 这里只做排序，列表、详情、更新、删除都会调用本方法，保证行为一致
    def get_queryset(self):
        # 直接返回全表并按 order_by 排序；无逻辑删除过滤是因为模型本身没有该字段
        return self.model.objects.order_by(self.order_by)
