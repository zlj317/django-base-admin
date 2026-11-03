"""操作日志 / 登录日志。"""
from apps.system.models import SysLoginLog, SysOperLog  # 两类日志模型
from apps.system.serializers import LoginLogSerializer, OperLogSerializer  # 对应序列化器
from common.response import ok  # 统一响应封装
from common.views import CrudViewSet  # 通用 CRUD 基类


class OperLogViewSet(CrudViewSet):
    """操作日志视图：支持筛选与一键清空（逻辑删除）。"""
    model = SysOperLog  # 目标模型
    serializer_class = OperLogSerializer  # 序列化器
    perm_prefix = 'system:operlog'  # 权限标识前缀
    module_name = '操作日志'  # 操作日志模块名
    filter_map = {'oper_user': 'icontains', 'module_name': 'icontains', 'oper_type': 'exact'}  # 筛选

    def clear(self, request):
        """清空全部操作日志（批量逻辑删除）。"""
        self.get_queryset().update(is_deleted=1)  # 批量打删除标记
        return ok(None, '日志已清空')  # 返回成功


class LoginLogViewSet(CrudViewSet):
    """登录日志视图：支持筛选与一键清空（逻辑删除）。"""
    model = SysLoginLog  # 目标模型
    serializer_class = LoginLogSerializer  # 序列化器
    perm_prefix = 'system:loginlog'  # 权限标识前缀
    module_name = '登录日志'  # 操作日志模块名
    filter_map = {'username': 'icontains', 'status': 'exact'}  # 列表筛选字段

    def clear(self, request):
        """清空全部登录日志（批量逻辑删除）。"""
        self.get_queryset().update(is_deleted=1)  # 批量打删除标记
        return ok(None, '日志已清空')  # 返回成功
