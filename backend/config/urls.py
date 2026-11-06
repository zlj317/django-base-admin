"""全局路由。"""
# ============================== 文件说明 ==============================
# 作用：项目根 URLConf，由 settings.ROOT_URLCONF='config.urls' 指定。
# 被谁加载：Django 处理请求时导入本模块；include() 再把各应用子路由挂载到命名空间。
# 关键约定：
#   1) 所有接口统一以 /api/ 开头，便于 Nginx 反向代理与前端 baseURL 统一配置；
#   2) 每个模块只 include 一次，具体路由规则由各 apps/*/urls.py 自行维护；
#   3) 新增业务模块时按分组追加到列表末尾，不要随意改动已有顺序；
#   4) apps.student 挂在裸前缀 'api/' 下，其子路由均以 'student/' 开头；若子路由未命中，
#      Django 会自动继续尝试后续 'api/xxx/' 规则，因此该条不会截断其它模块。
# 匹配规则：Django 自上而下逐条匹配，更具体的前缀应排在更宽泛的前缀之前。
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
    # ↓↓↓ 需求4：通用标配功能 ↓↓↓
    path('api/sys_no/', include('apps.sys_no.urls')),  # 编码规则
    path('api/imprint/', include('apps.imprint.urls')),  # 导入模板 + 打印模板
    path('api/backup/', include('apps.backup.urls')),  # 数据备份
    path('api/dp/', include('apps.dp.urls')),  # 数据权限
    path('api/dsm/', include('apps.dsm.urls')),  # 脱敏配置
    path('api/mon/', include('apps.mon.urls')),  # 监控告警
    path('api/sec/', include('apps.sec.urls')),  # 安全策略
    # ↓↓↓ 需求5：高级可选功能 ↓↓↓
    path('api/tenant/', include('apps.tenant.urls')),  # 多租户
    path('api/wo/', include('apps.wo.urls')),  # 工单
    path('api/cal/', include('apps.cal.urls')),  # 日历日程
    path('api/kb/', include('apps.kb.urls')),  # 知识库
    # ↓↓↓ 需求6：系统首页 ↓↓↓
    path('api/home/', include('apps.home.urls')),  # 首页聚合接口
    # ↓↓↓ 需求7：3D 可视化 ↓↓↓
    path('api/scene3d/', include('apps.scene3d.urls')),  # 3D 场景/模型/绑定/告警/巡检/分享接口
]
