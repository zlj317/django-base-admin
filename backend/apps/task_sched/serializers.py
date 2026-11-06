"""任务调度模块序列化器。"""
# 模块用途：把 task_info/task_log 模型转换成前端可用的 JSON，并在新增/编辑时做字段级校验。
# 对应路由：apps/task_sched/views.py 的 TaskInfoViewSet / TaskLogViewSet 使用，路由见 task_sched/urls.py。
# 权限：序列化层不鉴权，接口权限由视图的 perm_prefix='task' 与 PermissionCheck 完成。
# 被谁调用：CrudViewSet 的 create/update/list 以及 StandardPagination.paginate 的序列化环节。
from rest_framework import serializers  # DRF 序列化/反序列化组件

from apps.task_sched.models import TaskInfo, TaskLog  # 任务相关模型


# 任务信息序列化器：由 ModelSerializer 依据模型字段自动生成唯一性、必填与 choices 校验。
class TaskInfoSerializer(serializers.ModelSerializer):
    """任务信息序列化器：直接暴露全部字段。"""
    # Meta 内声明模型与字段白名单，ModelSerializer 据此生成校验规则与输出字段。
    class Meta:
        """声明模型与全部字段。"""
        # 字段标签与 choices 直接复用模型定义，避免序列化器与模型两处维护导致不一致。
        model = TaskInfo  # 目标模型
        fields = '__all__'  # 全字段输出


# 任务日志序列化器：日志表无审计字段，直接全字段输出，供前端日志列表/详情展示。
class TaskLogSerializer(serializers.ModelSerializer):
    """任务执行日志序列化器：直接暴露全部字段。"""
    # Meta 同样只声明模型与字段范围，日志字段的 choices 校验复用模型中的 RUN_STATUS_CHOICES。
    class Meta:
        """声明模型与全部字段。"""
        # 同样全字段输出；日志一般由调度逻辑写入，接口侧主要用于读取与删除。
        model = TaskLog  # 目标模型
        fields = '__all__'  # 全字段输出
