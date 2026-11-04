"""全局路由。"""
from django.urls import include, path  # include 挂载子路由，path 定义单条路由规则

urlpatterns = [  # 路由表：按 URL 前缀把各模块的子路由挂载到不同命名空间
    path('api/auth/', include('apps.system.urls_auth')),  # 认证接口：登录/登出/当前用户等
    path('api/system/', include('apps.system.urls')),  # 系统管理接口：用户/角色/菜单/日志等
    path('api/gen/', include('apps.gen.urls')),  # 代码生成器接口
    path('api/wf/', include('apps.workflow.urls')),  # 工作流（审批）接口
    # ↓↓↓ 由代码生成器生成的业务模块路由（新增业务表后在此追加） ↓↓↓
    path('api/', include('apps.student.urls')),  # 示例业务模块路由，默认挂在 /api/ 下
    path('api/file/', include('apps.file.urls')),  # 文件管理模块
    path('api/msg/', include('apps.msg.urls')),  # 消息通知模块
    path('api/notice/', include('apps.notice.urls')),  # 公告模块
    path('api/task/', include('apps.task_sched.urls')),  # 任务调度模块
    path('api/rp/', include('apps.report.urls')),  # 报表模块
    path('api/bi/', include('apps.bi.urls')),  # 大屏BI模块
    path('api/outer/', include('apps.outer.urls')),  # 外部接口模块
]
