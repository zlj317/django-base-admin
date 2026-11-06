"""编码规则模块路由。"""
# 模块：apps/sys_no/urls.py —— 编码规则与生成日志的 URL 路由
# 用途：不使用 DRF Router，而是显式 path 把 CrudViewSet 的动作映射到 URL，前端接口地址固定可预期。
# 路由前缀：rule/ 与 log/（最终 URL 前缀由上层项目路由挂载决定，通常为 /sys_no/）。
# 幂等性：路由本身无副作用；generate/<pk> 为 POST 写操作，每次调用都会递增流水并写日志。
# 约定：list 与 create/delete 共用同一 as_view 实例，由 HTTP 方法分派到基类对应动作。
from django.urls import path

from apps.sys_no import views


# 路由工厂：为某个前缀生成标准 CRUD 路径，并按需追加自定义动作
def crud(prefix, viewset, extras=None):
    # 拼接子路径：prefix 为空时直接返回子路径，避免出现多余的 "/"
    def _join(s): return f'{prefix}/{s}' if prefix else s
    # 集合视图方法映射：GET=list、POST=create、DELETE=delete
    list_view = viewset.as_view({'get': 'list', 'post': 'create', 'delete': 'delete'})
    # 详情视图方法映射：PUT=update；pk 由 <int:pk> 传入视图的 pk 参数
    item_view = viewset.as_view({'put': 'update'})
    # 标准 CRUD 路径集合：list/create/delete 走集合视图，update 走详情视图
    patterns = [
        # 列表查询（GET）与批量删除（DELETE）共用该路径
        path(_join('list'), list_view),
        # 新增（POST）走独立路径，前端调用语义更清晰
        path(_join('create'), list_view),
        # 批量删除（DELETE），ids 通过请求体传递
        path(_join('delete'), list_view),
        # 单条编辑（PUT），仅修改指定主键的记录
        path(_join('update/<int:pk>'), item_view),
    ]
    # 追加自定义动作：键为子路径、值为 {HTTP 方法: 动作名} 映射
    for suffix, methods in (extras or {}).items():
        # 每个自定义动作生成独立 path；动作名必须是视图集上真实存在的方法
        patterns.append(path(_join(suffix), viewset.as_view(methods)))
    # 返回该前缀下的全部路由，供调用方合并
    return patterns


# 规则路由：标准 CRUD + 生成编号（POST /rule/generate/<pk>）
urlpatterns = crud('rule', views.SysNoRuleViewSet, {
    # generate：按规则主键取号，detail 动作需要 pk
    'generate/<int:pk>': {'post': 'generate'},
}) + crud('log', views.SysNoLogViewSet, {
    # status：日志表无 status 列，该路由实际不可用（见主报告"疑似问题"）
    'status/<int:pk>': {'put': 'status'},
})
