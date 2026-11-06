"""监控告警模块路由。"""
# 模块：apps/mon/urls.py —— 监控告警模块的路由表
# 用途：为规则（rule）与记录（record）两组视图集拼装“列表/新增/删除/更新 + 自定义动作”路由。
# 对应表：monitor_alarm_rule（规则）、monitor_alarm_record（告警记录）。
# 路由前缀：由 config/urls.py 挂载为 /api/mon/，本文件内再区分 rule / record 两组。
# 告警生命周期：rule/* 维护触发条件与启停状态；record/* 查询告警并通过 update 回写处理结果。
# 说明：项目统一不用 DRF router，直接显式声明 path，便于把多个动作复用到同一视图函数。
# URL 路由构造函数
from django.urls import path

# 本模块视图集，供下方路由绑定
from apps.mon import views


# 路由生成器：按前缀批量产出标准 CRUD 路由，extras 用于追加自定义动作
def crud(prefix, viewset, extras=None):
    # 兼容工具函数：有前缀时原样返回，否则去掉前导斜杠（当前模块未使用，保留原有定义）
    def _rp(s): return s if prefix else s.lstrip('/')
    # 前缀拼接：无前缀时不额外加 "/"，避免出现以 "/" 开头的非法路径
    def _join(s): return f'{prefix}/{s}' if prefix else s
    # 多个标准动作共用一个视图函数：list/create/delete 分别映射到 GET/POST/DELETE
    list_view = viewset.as_view({'get': 'list', 'post': 'create', 'delete': 'delete'})
    # 详情动作：批量更新按主键定位，方法限定 PUT
    item_view = viewset.as_view({'put': 'update'})
    # 标准路由清单：list、create、delete 共用 list_view；update 走详情视图
    patterns = [
        # 列表：GET 分页查询
        path(_join('list'), list_view),
        # 新增：POST 创建一条规则/记录
        path(_join('create'), list_view),
        # 删除：DELETE，实际为批量删除（ids 放在请求体）
        path(_join('delete'), list_view),
        # 更新：PUT，按主键批量/单条更新
        path(_join('update/<int:pk>'), item_view),
    ]
    # 追加自定义动作：键为路径后缀，值为 {HTTP 方法: action 名} 映射
    for suffix, methods in (extras or {}).items():
        # 同一个视图集按 action 名生成新的视图函数，挂到对应路径
        patterns.append(path(_join(suffix), viewset.as_view(methods)))
    # 返回路由列表，供 urlpatterns 直接拼接
    return patterns


# 模块级路由：规则路由（含 status 启停自定义动作）+ 记录路由
urlpatterns = crud('rule', views.MonitorAlarmRuleViewSet, {
    # 启停：PUT rule/status/<pk>，更新规则 status 字段
    'status/<int:pk>': {'put': 'status'},
}) + crud('record', views.MonitorAlarmRecordViewSet)
