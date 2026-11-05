"""3D 可视化模块路由。"""
from django.urls import path  # 路由声明

from apps.scene3d import views  # 引入本模块视图集


def crud(prefix, viewset, extras=None):  # 路由工厂：按统一约定生成 CRUD 与自定义动作
    """与其它模块保持一致的 CRUD 路由生成器。"""
    def _join(s):  # 内部辅助：拼资源前缀，保留空前缀（场景主表）
        """拼接路由前缀。"""
        return f'{prefix}/{s}' if prefix else s  # 空前缀时不加斜杠
    list_view = viewset.as_view({'get': 'list', 'post': 'create', 'delete': 'delete'})  # 列表/新增/批量删除
    item_view = viewset.as_view({'put': 'update'})  # 编辑
    patterns = [  # 固定的四条基础路由
        path(_join('list'), list_view),  # 分页列表
        path(_join('create'), list_view),  # 新增
        path(_join('delete'), list_view),  # 批量删除
        path(_join('update/<int:pk>'), item_view),  # 编辑指定记录
    ]
    for suffix, methods in (extras or {}).items():  # 追加自定义动作
        patterns.append(path(_join(suffix), viewset.as_view(methods)))  # 按动作映射 HTTP 方法
    return patterns  # 返回该资源全部路由，供上层拼接


urlpatterns = (  # 汇总各资源路由，前缀决定最终 URL
    crud('category', views.Scene3dCategoryViewSet, {  # 场景分类
        'update/<int:pk>/status': {'put': 'status'},  # 启用/停用
    })
    + crud('template', views.Scene3dTemplateViewSet, {  # 场景模板
        'update/<int:pk>/status': {'put': 'status'},
    })
    + crud('', views.Scene3dSceneViewSet, {  # 场景主表（无前缀：/scene3d/list 等）
        '<int:pk>/detail': {'get': 'detail_info'},  # 场景详情（动作名避开 DRF 保留属性 detail）
        '<int:pk>/save': {'post': 'save'},  # 保存草稿
        '<int:pk>/publish': {'post': 'publish'},  # 发布
        '<int:pk>/offline': {'post': 'offline'},  # 下线
        '<int:pk>/copy': {'post': 'copy'},  # 复制
        '<int:pk>/versions': {'get': 'versions'},  # 版本列表
        '<int:pk>/rollback': {'post': 'rollback'},  # 版本回滚
        '<int:pk>/share': {'post': 'share'},  # 生成分享链接
        '<int:pk>/visit-log': {'get': 'visit_log'},  # 访问日志
        '<int:pk>/export': {'get': 'export_config'},  # 导出配置
    })
    + crud('model', views.Scene3dModelResourceViewSet, {  # 模型资源
        'upload': {'post': 'upload'},  # 上传模型
        '<int:pk>/preview': {'get': 'preview'},  # 预览信息
    })
    + crud('object', views.Scene3dObjectViewSet)  # 场景对象
    + crud('binding', views.Scene3dBindingViewSet, {  # 数据绑定
        '<int:pk>/preview': {'get': 'preview'},  # 模拟读数预览
    })
    + crud('alarm/rule', views.Scene3dAlarmRuleViewSet)  # 告警规则
    + crud('alarm', views.Scene3dAlarmRecordViewSet, {  # 告警记录
        'records': {'get': 'list'},  # 记录列表（语义化别名）
        '<int:pk>/confirm': {'post': 'confirm'},  # 确认告警
        'stats': {'get': 'stats'},  # 告警统计
    })
    + crud('route', views.Scene3dPatrolRouteViewSet, {  # 巡检路线
        '<int:pk>/play': {'post': 'play'},  # 开始巡检
    })
    + crud('route/record', views.Scene3dPatrolRecordViewSet)  # 巡检记录（只读）
    + crud('permission', views.Scene3dPermissionViewSet)  # 场景访问授权
    + crud('visit-log', views.Scene3dAccessLogViewSet)  # 访问日志
) + [
    path('screen/data', views.Scene3dScreenView.as_view({'get': 'data'}), name='scene3d-screen-data'),  # 大屏聚合数据
    path('share/<str:token>', views.Scene3dShareView.as_view(), name='scene3d-share'),  # 免登录分享数据
]
