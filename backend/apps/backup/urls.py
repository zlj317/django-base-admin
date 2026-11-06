"""数据备份模块路由。"""
# 文件：apps/backup/urls.py —— 数据备份模块的 URL 路由表
# 用途：按项目统一的 CRUD 约定生成备份记录与备份策略接口，并挂载手动备份、下载、启停等自定义动作。
# 对应表：backup_record（记录）、backup_strategy（策略）。
# 路由前缀：本文件内为 record / strategy，追加到 config/urls.py 的 /api/backup/ 之后。
# 幂等性：路由定义是纯声明，重复加载不会产生重复数据；接口幂等性由视图层与数据库唯一约束保证。
# Django 路由函数：path() 用于把一个 URL 模式绑定到视图
from django.urls import path

# 导入本模块的视图集，路由表直接引用其中的 ViewSet 类
from apps.backup import views


# 通用 CRUD 路由生成器：按项目约定拼出 list/create/delete/update 四条基础路径，再追加自定义动作
def crud(prefix, viewset, extras=None):
    # 内部工具函数：前缀非空时补斜杠，避免出现 "record//list" 或缺少分隔符的路径
    def _join(s): return f'{prefix}/{s}' if prefix else s
    # 列表视图：同一路径按 HTTP 方法分派，GET=列表查询、POST=新增、DELETE=批量删除
    list_view = viewset.as_view({'get': 'list', 'post': 'create', 'delete': 'delete'})
    # 单条编辑视图：只暴露 PUT（update），本模块不提供单条详情 GET 接口
    item_view = viewset.as_view({'put': 'update'})
    # 基础四条路由：与前端通用 CRUD 组件的请求地址一一对应
    patterns = [
        # 列表查询：GET /{prefix}/list
        path(_join('list'), list_view),
        # 新增：POST /{prefix}/create
        path(_join('create'), list_view),
        # 批量删除：DELETE /{prefix}/delete（ids 放在请求体中，避免 URL 过长）
        path(_join('delete'), list_view),
        # 编辑：PUT /{prefix}/update/<pk>，pk 限定为整数以匹配雪花 ID 的十进制写法
        path(_join('update/<int:pk>'), item_view),
    ]
    # 追加模块自定义动作：extras 为 {路径后缀: {HTTP 方法: 动作名}} 的映射
    for suffix, methods in (extras or {}).items():
        # 每个自定义动作独立注册，方法字典由 DRF 的 as_view 解析到 ViewSet 中对应的方法
        patterns.append(path(_join(suffix), viewset.as_view(methods)))
    # 返回路由列表，供 urlpatterns 直接拼接
    return patterns


# 备份记录路由：前缀 record，额外提供“手动备份”与“下载备份”两个动作
urlpatterns = crud('record', views.BackupRecordViewSet, {
    # 手动备份：POST /api/backup/record/manual，对应视图集的 manual_backup 动作
    'manual': {'post': 'manual_backup'},
    # 下载备份：GET /api/backup/record/download/<pk>（演示环境返回备份元信息 JSON）
    'download/<int:pk>': {'get': 'download'},  # 下载备份（演示环境返回元信息）
}) + crud('strategy', views.BackupStrategyViewSet, {
    # 策略启停：PUT /api/backup/strategy/status/<pk>，复用 CrudViewSet 基类的 status 动作
    'status/<int:pk>': {'put': 'status'},
})
