"""任务调度模块视图集。"""
# 模块用途：定时任务的 HTTP 接口层，提供任务信息 CRUD、手动触发一次、任务日志查询。
# 对应路由：apps/task_sched/urls.py 中 crud('info') / crud('log')，由 config/urls.py 挂到 /api/task/ 前缀。
# 权限：继承 CrudViewSet，perm_prefix='task' 生成 task:list/create/update/delete，由 PermissionCheck 校验。
# 注意：run_once 为演示实现，仅向 task_log 写入一条占位记录，不会真正调用调度器/Celery/crontab。
# 被谁调用：前端“任务信息”与“任务日志”页面。
import time  # 日志时间

from rest_framework.decorators import action  # 自定义路由装饰器

from common.pagination import StandardPagination  # 统一分页
from common.response import fail, ok  # 统一响应封装
from common.views import CrudViewSet  # 通用 CRUD 基类

from apps.task_sched.models import TaskInfo, TaskLog  # 任务相关模型
from apps.task_sched.serializers import TaskInfoSerializer, TaskLogSerializer  # 对应序列化器


# 任务视图：标准 CRUD 由 CrudViewSet 提供，额外增加“手动执行一次”的自定义动作。
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

    # 自定义动作：路由 /task/info/run_once/<pk> 仅接受 POST（见 urls.py 的 extras 配置）。
    @action(detail=True, methods=['post'])
    def run_once(self, request, pk=None):
        """手动触发一次任务：写一条 task_log 占位记录。"""
        # 只查找未逻辑删除的任务，已删除任务不允许再触发。
        task = TaskInfo.objects.filter(pk=pk, is_deleted=0).first()
        if not task:
            # 业务码 404，HTTP 状态仍为 200；与其它模块的错误返回约定一致。
            return fail('任务不存在', code=404)
        # 统一使用本地时间字符串，匹配 task_log.run_time/create_time 的 DATETIME 列。
        now = time.strftime('%Y-%m-%d %H:%M:%S')
        # 演示实现：这里只模拟一次成功执行并写日志占位，不调用任何真实任务函数或调度器。
        TaskLog.objects.create(
            task_id=task.id, task_name=task.task_name,
            # 运行状态固定写 1（成功）只是演示占位；真实执行时应按实际结果写 1/2 并补 error_msg。
            run_status=1, return_info='手动触发（演示：未实际调度）',
            cost_time=0, run_time=now, create_time=now,
        )
        # 文案显式标注“未实际调度”，避免使用者误以为任务已真正执行。
        return ok(None, '任务已触发（演示：未实际调度）')


# 日志视图：接口侧主要用于查询与删除；调度执行时由服务端逻辑直接写入 task_log。
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

    # 覆写查询集：日志表没有 is_deleted 列，只能直接按主键倒序返回全部记录。
    def get_queryset(self):
        # TaskLog 不继承 BaseModel，没有 is_deleted 列，不能复用基类的“过滤逻辑删除”查询集。
        return self.model.objects.order_by(self.order_by)

    # 覆写列表：日志不能走基类的 apply_filters(get_queryset()) 流程，这里自行拼装筛选条件。
    def list(self, request):
        """列表查询：TaskLog 不继承 BaseModel，直接过滤。"""
        # 显式覆盖基类 list：日志表无 is_deleted 字段，不能走基类 get_queryset() 的统一过滤。
        queryset = TaskLog.objects.all().order_by('-id')
        # 复用类属性 filter_map 的白名单声明，逐参数拼接 ORM lookup（字段名不受用户控制，无注入风险）。
        for param, lookup in self.filter_map.items():
            # 查询参数均为字符串，exact 条件由 ORM 按模型字段类型自行转换。
            value = request.query_params.get(param)
            if value not in (None, ''):
                # 空值视为“不筛选”，否则可能把结果集错误地过滤为空。
                queryset = queryset.filter(**{f'{param}__{lookup}': value})
        # 交给统一分页器完成 count/切片/序列化，返回结构与其他模块一致。
        return StandardPagination(request).paginate(queryset, TaskLogSerializer)
