"""多租户模块视图集。"""
# 文件：apps/tenant/views.py —— 多租户模块的视图集（租户/成员/套餐）
# 用途：基于通用 CrudViewSet 提供租户、租户成员关系、租户套餐的列表/新增/编辑/删除/启停接口。
# 对应表：sys_tenant、sys_tenant_user、sys_tenant_package。
# 路由前缀：/api/tenant/tenant|tenant_user|package/，具体子路径见 apps/tenant/urls.py。
# 租户隔离：仅在"租户-用户"映射中保存 tenant_id；业务数据查询未接入统一租户过滤，
#           因此当前模块更接近"租户配置/演示"能力，不能据此认为已实现全站数据隔离。
# 权限：perm_prefix 决定 tenant:tenant|tenant_user|package 的 list/create/update/delete 权限标识。
# 统一分页：解析 page/page_size 并输出 {total, rows}
from common.pagination import StandardPagination
# 通用 CRUD 基类：列表筛选、审计字段、逻辑删除、status 动作
from common.views import CrudViewSet

# 三张租户表模型
from apps.tenant.models import SysTenant, SysTenantPackage, SysTenantUser
# 对应序列化器
from apps.tenant.serializers import SysTenantPackageSerializer, SysTenantSerializer, SysTenantUserSerializer


# 租户主体视图集：继承基类后自动具备 list/create/update/delete/status 五个动作
class SysTenantViewSet(CrudViewSet):
    """租户 CRUD。"""
    # 目标模型；基类据此构建查询集并补审计字段
    model = SysTenant
    # 序列化器：新增/编辑校验与列表输出共用
    serializer_class = SysTenantSerializer
    # 权限前缀：拼出 tenant:tenant:list/create/update/delete，与种子菜单的 perms 对应
    perm_prefix = 'tenant:tenant'
    # 查询参数白名单：参数名固定为模型字段，用户无法注入任意字段名
    filter_map = {
        # 租户名称模糊搜索
        'tenant_name': 'icontains',
        # 租户编码模糊搜索
        'tenant_code': 'icontains',
        # 启停状态精确匹配
        'status': 'exact',
    }
    # 默认按主键倒序，新建租户排在最前
    order_by = '-id'
    # 操作日志模块名；当前基类只声明未使用，保留给日志类扩展
    module_name = '租户管理'
    # 未覆盖 get_queryset：沿用基类的 is_deleted=0 过滤，删除走逻辑删除并可追溯
    # 未定义动作扩展：status 由 urls.py 映射到基类的 status 方法，仅更新 status 字段


# 租户成员关系视图集：维护"租户-用户"归属以及是否租户管理员
class SysTenantUserViewSet(CrudViewSet):
    """租户用户关联 CRUD。"""
    # 目标模型：sys_tenant_user（无 is_deleted 审计列）
    model = SysTenantUser
    # 序列化器：全字段读写，便于前端直接提交 tenant_id/user_id/is_tenant_admin
    serializer_class = SysTenantUserSerializer
    # 权限前缀：tenant:tenant_user:list/create/update/delete
    perm_prefix = 'tenant:tenant_user'
    # 查询参数：按租户或用户精确定位成员关系，支撑"某租户的成员列表"
    filter_map = {
        # 按租户 ID 精确过滤
        'tenant_id': 'exact',
        # 按用户 ID 精确过滤
        'user_id': 'exact',
    }
    # 默认按主键倒序，最新加入的成员在前
    order_by = '-id'
    # 操作日志模块名（基类保留字段）
    module_name = '租户用户'

    # 必须覆盖：该表没有 is_deleted 列，若沿用基类的 filter(is_deleted=0) 会触发 FieldError
    def get_queryset(self):
        # 直接按主键倒序返回全表；成员关系不做逻辑删除，删除动作由基类走物理删除
        return self.model.objects.order_by(self.order_by)

    # 复写列表：在无逻辑删除的表上复用"筛选 + 分页"流程，实际逻辑与基类 list 等价
    def list(self, request):
        # 先按 filter_map 过滤，再交给统一分页器做 count/切片/序列化
        queryset = self.apply_filters(self.get_queryset(), request)
        # 分页器内部实例化 serializer_class，输出统一 {code, msg, data:{total, rows}} 结构
        return StandardPagination(request).paginate(queryset, self.get_serializer_class())


# 租户套餐视图集：维护可售套餐档位（用户数/存储/价格/上下架）
class SysTenantPackageViewSet(CrudViewSet):
    """租户套餐 CRUD。"""
    # 目标模型：sys_tenant_package（手工声明 is_deleted 审计字段）
    model = SysTenantPackage
    # 序列化器：新增/编辑校验与列表输出共用
    serializer_class = SysTenantPackageSerializer
    # 权限前缀：tenant:package:list/create/update/delete
    # 注意：种子脚本当前只建了 tenant:tenant:* 按钮，未建 tenant:package:*，普通角色可能无套餐操作权限
    perm_prefix = 'tenant:package'
    # 查询参数：套餐名称模糊搜索、上下架状态精确过滤
    filter_map = {
        # 套餐名称模糊搜索
        'package_name': 'icontains',
        # 状态精确匹配
        'status': 'exact',
    }
    # 默认按主键倒序，新套餐优先展示
    order_by = '-id'
    # 操作日志模块名（基类保留字段）
    module_name = '租户套餐'

    # 显式过滤逻辑删除：与基类默认行为一致，单独写明便于阅读套餐数据的可见范围
    def get_queryset(self):
        # 只返回未删除套餐，避免已下架/已删除档位出现在列表与编辑接口
        return self.model.objects.filter(is_deleted=0).order_by(self.order_by)
