# 文件：apps/cal/urls.py —— 日历日程模块的后端路由
# 用途：为日程、提醒两个视图集批量生成 列表/新增/删除/修改 四类固定路径。
# 对应表：cal_schedule、cal_reminder。
# 路由前缀：config/urls.py 以 api/cal/ 挂载本模块，故最终地址形如 /api/cal/schedule/list。
# 关键约定：路由由本文件的 crud() 函数统一生成（不使用 DRF router），写法与 bi/urls.py 保持一致；
#           删除的 ids 放在请求体而非 URL，因此 delete 与 list 共用同一个视图入口。
"""日历日程模块路由。"""
# Django 的 path 函数，用于声明单条 URL 规则
from django.urls import path

# 引入本模块视图集，供下面 as_view 绑定动作
from apps.cal import views


# 通用路由生成器：给定路径前缀与视图集，产出一组 CRUD 路径；extras 用于追加自定义动作
def crud(prefix, viewset, extras=None):
    """与 bi/urls.py 保持一致的 CRUD 路由生成器。"""
    # 拼接前缀：prefix 为空时直接返回子路径，避免出现多余的斜杠
    def _join(s): return f'{prefix}/{s}' if prefix else s
    # 列表/新增/删除共用同一入口，由 HTTP 方法分派到 list/create/delete
    list_view = viewset.as_view({'get': 'list', 'post': 'create', 'delete': 'delete'})
    # 修改入口：按主键定位记录，仅暴露 PUT（基类 update 内部按 partial 兼容只传变更字段）
    item_view = viewset.as_view({'put': 'update'})
    # 按固定顺序拼接四条基础路径，保证前端请求地址稳定
    patterns = [
        # 列表：GET /list，支持 filter_map 中的筛选参数与统一分页
        path(_join('list'), list_view),
        # 新增：POST /create，与 list 共用视图，由请求方法区分
        path(_join('create'), list_view),
        # 批量删除：DELETE /delete，ids 从请求体读取，避免 URL 过长
        path(_join('delete'), list_view),
        # 修改：PUT /update/<pk>，pk 由 Django 转换后传入视图
        path(_join('update/<int:pk>'), item_view),
    ]
    # 追加自定义动作：键为路径后缀，值为 {HTTP 方法: 视图方法名} 的映射
    for suffix, methods in (extras or {}).items():
        patterns.append(path(_join(suffix), viewset.as_view(methods)))
    # 返回路径列表，供 urlpatterns 用 + 拼接多个视图集的路由
    return patterns


# 汇总本模块路由：日程与提醒各生成一套结构相同的 CRUD 路径
urlpatterns = crud('schedule', views.ScheduleViewSet) + crud('reminder', views.ReminderViewSet)
