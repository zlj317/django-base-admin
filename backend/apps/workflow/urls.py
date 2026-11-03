"""工作流模块路由：全部挂在 /api/wf/ 下，路径不带结尾斜杠。"""
from django.urls import path  # 路由声明函数

from apps.workflow import views  # 工作流视图


def crud(prefix, viewset, extras=None):
    """生成标准 CRUD 路由：/list /create /update/<pk> /delete，并追加自定义动作。"""
    list_view = viewset.as_view({'get': 'list', 'post': 'create', 'delete': 'delete'})  # 集合入口
    item_view = viewset.as_view({'put': 'update'})  # 单条更新
    patterns = [
        path(f'{prefix}/list', list_view),  # 分页列表
        path(f'{prefix}/create', list_view),  # 新增
        path(f'{prefix}/delete', list_view),  # 批量删除
        path(f'{prefix}/update/<int:pk>', item_view),  # 按主键更新
    ]
    for suffix, methods in (extras or {}).items():  # 追加自定义动作
        patterns.append(path(f'{prefix}/{suffix}', viewset.as_view(methods)))
    return patterns  # 返回路由列表


urlpatterns = crud('category', views.WfCategoryViewSet) \
    + crud('form', views.WfFormViewSet, {
        'detail/<int:pk>': {'get': 'form_detail'},  # 表单配置详情
    }) \
    + crud('group', views.WfGroupViewSet, {
        'users/<int:pk>': {'get': 'users'},  # 分组内用户
        'set_users/<int:pk>': {'put': 'set_users'},  # 覆盖保存组成员
    }) \
    + crud('model', views.WfModelViewSet, {
        'design/<int:pk>': {'get': 'design'},  # 加载设计器数据
        'save': {'post': 'save'},  # 保存 BPMN XML 与节点配置
        'publish/<int:pk>': {'post': 'publish'},  # 发布并递增版本
        'disable/<int:pk>': {'post': 'disable'},  # 停用
        'copy/<int:pk>': {'post': 'copy'},  # 复制模型
        'options': {'get': 'options'},  # 可发起模型下拉
    }) \
    + crud('listener', views.WfListenerViewSet) \
    + crud('expression', views.WfExpressionViewSet) \
    + [
        path('instance/list', views.WfInstanceViewSet.as_view({'get': 'list'})),  # 全局实例
        path('instance/my', views.WfInstanceViewSet.as_view({'get': 'my'})),  # 我的流程
        path('instance/start', views.WfInstanceViewSet.as_view({'post': 'start'})),  # 发起流程
        path('instance/detail/<int:pk>', views.WfInstanceViewSet.as_view({'get': 'detail_info'})),  # 实例详情
        path('instance/trace/<int:pk>', views.WfInstanceViewSet.as_view({'get': 'trace'})),  # 流程轨迹
        path('instance/terminate/<int:pk>', views.WfInstanceViewSet.as_view({'post': 'terminate'})),  # 强制终止
        path('instance/withdraw/<int:pk>', views.WfInstanceViewSet.as_view({'post': 'withdraw'})),  # 发起人撤回
        path('task/todo', views.WfTaskViewSet.as_view({'get': 'todo'})),  # 我的待办
        path('task/done', views.WfTaskViewSet.as_view({'get': 'done'})),  # 我的已办
        path('task/list', views.WfTaskViewSet.as_view({'get': 'list'})),  # 全局任务
        path('task/approve/<int:pk>', views.WfTaskViewSet.as_view({'post': 'approve'})),  # 同意
        path('task/reject/<int:pk>', views.WfTaskViewSet.as_view({'post': 'reject'})),  # 驳回
        path('task/transfer/<int:pk>', views.WfTaskViewSet.as_view({'post': 'transfer'})),  # 转审
        path('task/addsign/<int:pk>', views.WfTaskViewSet.as_view({'post': 'addsign'})),  # 加签
        path('task/back/<int:pk>', views.WfTaskViewSet.as_view({'post': 'back'})),  # 退回上一步
        path('cc/mine', views.WfCcViewSet.as_view({'get': 'mine'})),  # 抄送我的
        path('cc/read/<int:pk>', views.WfCcViewSet.as_view({'post': 'read'})),  # 标记已读
        path('option/users', views.OptionViewSet.as_view({'get': 'users'})),  # 用户下拉
        path('option/roles', views.OptionViewSet.as_view({'get': 'roles'})),  # 角色下拉
        path('option/depts', views.OptionViewSet.as_view({'get': 'depts'})),  # 部门下拉
        path('option/groups', views.OptionViewSet.as_view({'get': 'groups'})),  # 分组下拉
    ]
