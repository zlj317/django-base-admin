"""安全策略模块视图集。"""
# 文件：apps/sec/views.py —— 安全策略模块的接口层（ViewSet 声明）
# 用途：基于公共基类 CrudViewSet，为 IP 黑白名单、登录尝试记录、接口限流规则提供
#       列表/新增/编辑/删除/启停等后台管理接口。
# 对应表：sys_ip_control、sys_login_attempt、sys_rate_limit（均为手工建表、managed=False）。
# 路由前缀：/api/sec/ip、/api/sec/login_attempt、/api/sec/rate_limit（见 apps/sec/urls.py）。
# 生效范围（重要）：本模块对外提供的是“策略配置的维护能力”，并不包含执行拦截的代码；
#                   IP 名单与限流规则是否真被登录链路或请求中间件读取执行，以实际代码为准
#                   （当前仓库未见接入点，因此这些策略暂以配置与演示为主）。
# 权限约定：基类的 permission_classes 会按 perm_prefix 生成 4 个标准 action 的权限标识
#           （list/create/update/delete）；注意种子数据（apps/sec/seed.py）中“登录尝试”“接口限流”
#           两个页面登记的 perms 都是 sec:ip:list，而对应视图集的 perm_prefix 分别是
#           sec:login_attempt / sec:rate_limit，两者并不一致（疑似配置问题，此处按原样记录，不做修改）。
from common.pagination import StandardPagination
# 上一行引入统一分页器：输出 {code,msg,data} 结构，登录记录列表会直接使用它。
from common.views import CrudViewSet

# 上一行引入通用 CRUD 基类：统一分页、筛选、增删改、状态切换与权限校验。
from apps.sec.models import SysIpControl, SysLoginAttempt, SysRateLimit
from apps.sec.serializers import (
    SysIpControlSerializer,
    SysLoginAttemptSerializer,
    SysRateLimitSerializer,
)


# IP 黑白名单视图集：直接复用基类的标准 CRUD，无需额外业务逻辑
class SysIpControlViewSet(CrudViewSet):
    """IP 黑白名单 CRUD。"""
    # 目标模型：基类据此构建查询集、生成唯一性预检
    model = SysIpControl
    # 序列化器：负责输出与入参校验
    serializer_class = SysIpControlSerializer
    # 权限前缀：拼出 sec:ip:list/create/update/delete 四个权限标识（与种子菜单一致）
    perm_prefix = 'sec:ip'
    # 查询参数 → ORM lookup 映射：声明后前端即可按这些条件筛选
    filter_map = {
        # IP 地址模糊匹配，便于按网段前缀检索
        'ip': 'icontains',
        # 控制类型精确匹配（black/white）
        'control_type': 'exact',
        # 启用状态精确匹配（1/0）
        'status': 'exact',
    }
    # 默认按主键倒序：最新加入的名单规则排在最前
    order_by = '-id'
    # 操作日志模块名：基类/日志记录使用的中文标识
    module_name = 'IP黑白名单'


# 登录尝试记录视图集：该模型不继承 BaseModel，没有 is_deleted 列，故需重写查询集与列表
class SysLoginAttemptViewSet(CrudViewSet):
    """登录尝试记录 CRUD。"""
    # 目标模型：sys_login_attempt
    model = SysLoginAttempt
    # 序列化器：输出全部字段
    serializer_class = SysLoginAttemptSerializer
    # 权限前缀：本视图据此生成 sec:login_attempt:list/create/update/delete
    # 注意：种子菜单里“登录尝试”页面登记的 perms 是 sec:ip:list，与这里生成的标识不一致（记录不修改）
    perm_prefix = 'sec:login_attempt'
    # 支持的筛选条件：仅按用户名模糊搜索，避免暴露过多检索维度
    filter_map = {
        # 用户名模糊匹配
        'username': 'icontains',
    }
    # 按主键倒序：最新的登录尝试在前
    order_by = '-id'
    # 操作日志模块名
    module_name = '登录记录'

    # 重写查询集：日志表没有 is_deleted 字段，若沿用基类的 is_deleted=0 过滤会直接报错
    def get_queryset(self):
        # 直接返回全表并按 order_by 排序；登录流水不做逻辑删除，删除即物理删除
        return self.model.objects.order_by(self.order_by)

    # 重写列表：筛选逻辑与基类一致，但因为上面改了 get_queryset，这里显式复用同一套流程
    def list(self, request):
        # 先按 filter_map 过滤（如 username 模糊搜索），再由分页器统一分页与序列化
        queryset = self.apply_filters(self.get_queryset(), request)
        # 分页器内部会实例化序列化器类并输出统一结构；传类本身而非实例
        return StandardPagination(request).paginate(queryset, self.get_serializer_class())


# 接口限流规则视图集：标准 CRUD，规则生效与否由外部执行方决定
class SysRateLimitViewSet(CrudViewSet):
    """限流规则 CRUD。"""
    # 目标模型：sys_rate_limit
    model = SysRateLimit
    # 序列化器：负责字段校验与输出
    serializer_class = SysRateLimitSerializer
    # 权限前缀：本视图据此生成 sec:rate_limit:list/create/update/delete
    # 注意：种子菜单中“接口限流”页面登记的 perms 是 sec:ip:list，两者不一致（记录不修改）
    perm_prefix = 'sec:rate_limit'
    # 支持按规则名、限制 URL 模糊搜索，以及启用状态精确筛选
    filter_map = {
        # 规则名称模糊匹配
        'rule_name': 'icontains',
        # 接口路径模糊匹配，便于按模块前缀检索
        'limit_url': 'icontains',
        # 启用/停用精确筛选
        'status': 'exact',
    }
    # 按主键倒序：最新规则在前
    order_by = '-id'
    # 操作日志模块名
    module_name = '限流规则'
