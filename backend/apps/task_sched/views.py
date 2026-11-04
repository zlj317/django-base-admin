"""任务调度模块视图集。"""
import time  # 日志时间

from rest_framework.decorators import action  # 自定义路由装饰器

from common.pagination import StandardPagination  # 统一分页
from common.response import fail, ok  # 统一响应封装
from common.views import CrudViewSet  # 通用 CRUD 基类

from apps.task_sched.models import TaskInfo, TaskLog  # 任务相关模型
from apps.task_sched.serializers import TaskInfoSerializer, TaskLogSerializer  # 对应序列化器


class TaskInfoViewSet(CrudViewSet):
    """任务信息表 CRUD：管理定时任务。"""
    model = TaskInfo  # 目标模型
    serializer_class = TaskInfoSerializer  # 序列化器
    perm_prefix = 'task'  # 权限前缀：task:list/create/update/delete
    filter_map = {  # 支持的查询参数与 ORM lookup 映射
        'task_name': 'icontains',  # 任务名称模糊搜索
        'task_key': 'icontains',  # 任务编码模糊搜索
        'task_type': 'exact',  # 调度类型精确匹配
        'status': 'exact',  # 状态精确匹配
    }
    order_by = '-id'  # 按主键倒序
    module_name = '定时任务'  # 操作日志模块名

    @action(detail=True, methods=['post'])
    def run_once(self, request, pk=None):
        """手动触发一次任务：写一条 task_log 占位记录。"""
        task = TaskInfo.objects.filter(pk=pk, is_deleted=0).first()
        if not task:
            return fail('任务不存在', code=404)
        now = time.strftime('%Y-%m-%d %H:%M:%S')
        TaskLog.objects.create(
            task_id=task.id, task_name=task.task_name,
            run_status=1, return_info='手动触发（演示：未实际调度）',
            cost_time=0, run_time=now, create_time=now,
        )
        return ok(None, '任务已触发（演示：未实际调度）')


class TaskLogViewSet(CrudViewSet):
    """任务执行日志表 CRUD：已执行的任务日志。"""
    model = TaskLog  # 目标模型
    serializer_class = TaskLogSerializer  # 序列化器
    perm_prefix = 'task'  # 权限前缀
    filter_map = {  # 支持的查询参数
        'task_id': 'exact',  # 任务精确匹配
        'run_status': 'exact',  # 运行状态精确匹配
        'task_name': 'icontains',  # 任务名称模糊搜索
    }
    order_by = '-id'  # 按主键倒序
    module_name = '任务日志'  # 操作日志模块名

    def get_queryset(self):
        return self.model.objects.order_by(self.order_by)

    def list(self, request):
        """列表查询：TaskLog 不继承 BaseModel，直接过滤。"""
        queryset = TaskLog.objects.all().order_by('-id')
        for param, lookup in self.filter_map.items():
            value = request.query_params.get(param)
            if value not in (None, ''):
                queryset = queryset.filter(**{f'{param}__{lookup}': value})
        return StandardPagination(request).paginate(queryset, TaskLogSerializer)
