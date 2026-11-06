"""操作日志 / 登录日志。"""
# 模块用途：后台操作日志与登录日志的查询、筛选与一键清空，属于安全审计能力。
# 对应路由前缀：/api/system/operlog/ 与 /api/system/loginlog/（均含 list/delete/clear）。
# 权限要求：基类按 perm_prefix 生成 system:operlog:*、system:loginlog:* 权限点。
# 关键约定：日志只做逻辑删除（is_deleted=1），保留数据可追溯；clear 为批量清空动作。
from apps.system.models import SysLoginLog, SysOperLog  # 两类日志模型
from apps.system.serializers import LoginLogSerializer, OperLogSerializer  # 对应序列化器
from common.response import ok  # 统一响应封装
from common.views import CrudViewSet  # 通用 CRUD 基类


class OperLogViewSet(CrudViewSet):
    """操作日志视图：支持筛选与一键清空（逻辑删除）。"""
    # 四个类属性交给通用基类，列表/删除等标准动作无需在本文件重复实现。
    model = SysOperLog  # 目标模型
    serializer_class = OperLogSerializer  # 序列化器
    perm_prefix = 'system:operlog'  # 权限标识前缀
    module_name = '操作日志'  # 操作日志模块名
    # 操作人/模块名走模糊搜索，操作类型走精确匹配，兼顾易用与准确。
    filter_map = {'oper_user': 'icontains', 'module_name': 'icontains', 'oper_type': 'exact'}  # 筛选

    # 自定义动作 clear：路由声明为 POST /api/system/operlog/clear。
    def clear(self, request):
        """清空全部操作日志（批量逻辑删除）。"""
        # 用 QuerySet.update 一条 SQL 批量打标记，避免逐条 save 产生 N 次写库。
        self.get_queryset().update(is_deleted=1)  # 批量打删除标记
        # 不回传数据，前端收到成功即可刷新列表。
        return ok(None, '日志已清空')  # 返回成功


class LoginLogViewSet(CrudViewSet):
    """登录日志视图：支持筛选与一键清空（逻辑删除）。"""
    # 登录日志与操作日志结构不同，因此单独声明一套模型与序列化器。
    model = SysLoginLog  # 目标模型
    serializer_class = LoginLogSerializer  # 序列化器
    perm_prefix = 'system:loginlog'  # 权限标识前缀
    module_name = '登录日志'  # 操作日志模块名
    # 用户名模糊搜索 + 登录结果(status)精确匹配（0 成功 / 1 失败）。
    filter_map = {'username': 'icontains', 'status': 'exact'}  # 列表筛选字段

    # 自定义动作 clear：路由声明为 POST /api/system/loginlog/clear。
    def clear(self, request):
        """清空全部登录日志（批量逻辑删除）。"""
        # 逻辑删除而非物理删除，保留审计线索；日志量大时也只需一条 UPDATE。
        self.get_queryset().update(is_deleted=1)  # 批量打删除标记
        # 不返回数据量，避免暴露日志规模。
        return ok(None, '日志已清空')  # 返回成功
