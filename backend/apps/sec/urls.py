"""安全策略模块路由。"""
# 文件：apps/sec/urls.py —— 安全策略模块的 URL 配置
# 用途：为三个视图集批量注册后台管理接口（list/create/delete/update/status），
#       供前端“安全策略”相关页面调用。
# 对应表：sys_ip_control、sys_login_attempt、sys_rate_limit。
# 路由前缀：本文件被 config/urls.py 以 path('api/sec/', include('apps.sec.urls')) 挂载，
#           因此最终地址为 /api/sec/ip/*、/api/sec/login_attempt/*、/api/sec/rate_limit/*。
# 生效范围：这些路由只暴露“策略配置的维护接口”，不提供拦截/校验接口；
#           IP 名单与限流规则是否真正参与登录或请求处理，以代码中的实际调用为准
#           （当前以配置与演示为主，未见登录链路引用这些表）。
# 实现约定：不使用 DRF Router，而是用下面的 crud() 辅助函数显式拼出路径，
#           与项目内其它模块保持“手写 path + as_view”风格。
from django.urls import path

# 上一行引入 path()：用于把 URL 规则与视图函数（as_view 返回的可调用对象）绑定。
from apps.sec import views


# 批量注册标准 CRUD 路径的辅助函数
# 参数：prefix 为 URL 前缀（如 'ip'）；viewset 为视图集类；extras 为额外动作配置 {路径后缀: {方法: action}}
def crud(prefix, viewset, extras=None):
    # 前缀为空时去掉路径段前导斜杠，避免拼出 '//list'；当前调用 prefix 均非空，此分支为兼容写法
    def _rp(s): return s if prefix else s.lstrip('/')
    # 拼接前缀与路径段：prefix 非空时用 'prefix/段' 形式；为空时直接用段名
    def _join(s): return f'{prefix}/{s}' if prefix else s
    # 列表与新增共用同一组视图：GET→list（分页查询）、POST→create（新增）、DELETE→delete（批量删除）
    list_view = viewset.as_view({'get': 'list', 'post': 'create', 'delete': 'delete'})
    # 详情编辑：PUT→update，按主键部分更新；基类只在未删除记录中查找，不能借接口“复活”数据
    item_view = viewset.as_view({'put': 'update'})
    # 固定生成 4 条标准路径，保证三个资源的路由行为完全一致
    patterns = [
        # 列表查询：/api/sec/<prefix>/list（支持 query_params 筛选与分页）
        path(_join('list'), list_view),
        # 新增：/api/sec/<prefix>/create（与 list 共用视图，按请求方法区分 action）
        path(_join('create'), list_view),
        # 批量删除：/api/sec/<prefix>/delete（ids 放在请求体，避免 URL 过长）
        path(_join('delete'), list_view),
        # 编辑：/api/sec/<prefix>/update/<pk>（pk 为雪花主键，用 int 转换器接收）
        path(_join('update/<int:pk>'), item_view),
    ]
    # 追加子类声明的额外动作（如 status 启停），extras 为空时只保留上面的标准 4 条
    for suffix, methods in (extras or {}).items():
        # 每个动作单独注册：methods 形如 {'put': 'status'}，即 PUT 映射到基类的 status 方法
        patterns.append(path(_join(suffix), viewset.as_view(methods)))
    # 返回本条资源的路由列表，供下面用 + 号拼接成最终 urlpatterns
    return patterns


# 三条资源的最终路由表：IP 名单额外支持启停，登录记录只有标准 CRUD，限流规则额外支持启停
urlpatterns = crud('ip', views.SysIpControlViewSet, {
    # 启停：PUT /api/sec/ip/status/<pk>，请求体传 status/enabled，由基类 status 动作处理
    'status/<int:pk>': {'put': 'status'},
}) + crud('login_attempt', views.SysLoginAttemptViewSet) + crud('rate_limit', views.SysRateLimitViewSet, {
    # 启停：PUT /api/sec/rate_limit/status/<pk>，复用基类 status 动作更新规则启用状态
    'status/<int:pk>': {'put': 'status'},
})
