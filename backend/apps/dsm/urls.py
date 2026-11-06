"""脱敏配置模块路由。"""
# 模块：apps/dsm/urls.py —— 脱敏配置模块的 URL 注册
# 用途：为规则表、字段配置表、角色关联表生成前端约定的 list/create/delete/update 四条基础路由，
#   并额外为规则表挂载一个启停动作。
# 对应表：desensitize_rule、desensitize_field、desensitize_role。
# 路由前缀：config/urls.py 用 path('api/dsm/', include('apps.dsm.urls')) 挂载，
#   因此最终地址是 /api/dsm/rule/list、/api/dsm/field/list、/api/dsm/role/list 等。
# 脱敏策略：路由只暴露配置的增删改查，没有任何接口在返回数据时执行脱敏，属"配置/预留"。
# 路由函数：把 URL 模式绑定到视图分发器
from django.urls import path

from apps.dsm import views


# 通用路由生成器：按本项目约定批量生成 CRUD 路由
# prefix：资源前缀（rule/field/role）；viewset：目标视图集；extras：追加的自定义动作映射
def crud(prefix, viewset, extras=None):
    # 去掉前导斜杠的辅助函数；不过本函数内部并未调用它（疑似早期遗留，仅记录不改）
    def _rp(s): return s if prefix else s.lstrip('/')
    # 拼接资源前缀与动作片段；prefix 为空时原样返回，避免出现多余的 "/"
    def _join(s): return f'{prefix}/{s}' if prefix else s
    # 列表视图同时分发三种方法：GET=list 列表、POST=create 新增、DELETE=delete 批量逻辑删除
    list_view = viewset.as_view({'get': 'list', 'post': 'create', 'delete': 'delete'})
    # 详情视图只分发 PUT=update；本项目不提供 GET 单条详情，前端用列表行数据回填表单
    item_view = viewset.as_view({'put': 'update'})
    # 每个资源固定生成四条基础路由，与前端 apiBase + '/list'|'/create'|'/delete'|'/update/{id}' 约定一致
    patterns = [
        # 列表查询：GET /<prefix>/list（支持 filter_map 中的查询参数）
        path(_join('list'), list_view),
        # 新增：POST /<prefix>/create（与 list 复用同一个视图，按方法分发）
        path(_join('create'), list_view),
        # 批量删除：DELETE /<prefix>/delete，ids 通过请求体传递
        path(_join('delete'), list_view),
        # 修改：PUT /<prefix>/update/<int:pk>；雪花 ID 是纯数字，int 转换器可正常匹配
        path(_join('update/<int:pk>'), item_view),
    ]
    # 追加自定义动作：extras 形如 {'status/<int:pk>': {'put': 'status'}}
    for suffix, methods in (extras or {}).items():
        # 每个动作单独生成一条 path，方法映射交给 DRF 的 as_view 分发
        patterns.append(path(_join(suffix), viewset.as_view(methods)))
    # 返回列表，便于下面直接用 + 拼接成 urlpatterns
    return patterns


# 模块级路由：
# 1) rule：基础 CRUD + PUT /rule/status/<pk>（调用 CrudViewSet.status 更新 status 字段）；
# 2) field / role：只有基础 CRUD，前端目前没有对应页面入口，属"后端已提供、前端未接入"
urlpatterns = crud('rule', views.DesensitizeRuleViewSet, {
    'status/<int:pk>': {'put': 'status'},
}) + crud('field', views.DesensitizeFieldViewSet) + crud('role', views.DesensitizeRoleViewSet)
