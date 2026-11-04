"""通用 CRUD 视图基类：统一分页/筛选/增删改 + 权限校验。"""
import time  # 生成创建/更新时间字符串，与手工 SQL 的 datetime 字段对齐

from rest_framework import viewsets  # 提供 ViewSet 基类与 action 语义

from common.pagination import StandardPagination  # 统一分页输出
from common.permissions import PermissionCheck  # 登录 + 权限标识校验
from common.response import fail, ok  # 统一成功/失败响应


class CrudViewSet(viewsets.ViewSet):
    """通用 CRUD。

    子类配置：
      model:            模型类
      serializer_class: 序列化器
      perm_prefix:      权限前缀，如 'system:user'
      filter_map:       {查询参数: lookup}，如 {'username': 'icontains', 'status': 'exact'}
      order_by:         排序字段，默认 'id'（编号升序）
      module_name:      操作日志模块名
    """

    model = None  # 子类必须指定模型类
    serializer_class = None  # 子类必须指定序列化器
    perm_prefix = ''  # 权限前缀，如 system:user，用于拼出各 action 的权限标识
    filter_map = {}  # 查询参数到 ORM lookup 的映射，声明后即可支持筛选
    order_by = 'id'  # 默认按编号升序，保证分页结果稳定
    module_name = ''  # 操作日志模块名，子类可覆盖为中文名

    @property
    def permission_classes(self):
        """按 perm_prefix 动态生成 perm_map，并固定使用 PermissionCheck。"""
        prefix = self.perm_prefix  # 取子类配置的权限前缀
        self.perm_map = {
            'list': f'{prefix}:list',  # 列表查询权限
            'create': f'{prefix}:create',  # 新增权限
            'update': f'{prefix}:update',  # 编辑权限
            'delete': f'{prefix}:delete',  # 删除权限
        }
        return [PermissionCheck]  # 只挂自定义权限类，登录校验已在其内部完成

    def get_queryset(self):
        """返回过滤逻辑删除后的基础查询集，供各类操作复用。"""
        return self.model.objects.filter(is_deleted=0).order_by(self.order_by)  # 逻辑删除条件在此统一收敛

    def get_serializer_class(self):
        """序列化器统一取类属性，子类只需声明一次。"""
        return self.serializer_class  # 基类不做动态选择

    def apply_filters(self, queryset, request):
        """按 filter_map 把非空查询参数拼成 ORM 过滤条件。"""
        for param, lookup in self.filter_map.items():
            value = request.query_params.get(param)  # 取前端传入的筛选值
            if value not in (None, ''):
                queryset = queryset.filter(**{f'{param}__{lookup}': value})  # 动态拼接 ORM lookup
        return queryset  # 返回链式过滤后的查询集

    def list(self, request):
        """列表接口：筛选 + 分页 + 序列化。"""
        queryset = self.apply_filters(self.get_queryset(), request)  # 先过滤再分页，保证 total 准确
        return StandardPagination(request).paginate(queryset, self.get_serializer_class())  # 输出统一分页结构

    def create(self, request):
        """新增接口：校验入参后补审计字段并回写完整对象。"""
        serializer = self.get_serializer_class()(data=request.data)  # 绑定请求体做字段校验
        serializer.is_valid(raise_exception=True)  # 校验失败交给全局异常处理器转 400
        now = time.strftime('%Y-%m-%d %H:%M:%S')  # 统一时间格式，与手写 SQL 的写入方式保持一致
        user = getattr(request, 'user_info', None)  # 当前登录用户，用于审计字段
        audit = {}  # 仅对继承 BaseModel 的模型补审计字段，日志类模型无这些列
        if hasattr(self.model, 'create_by'):
            audit = dict(
                create_by=user.username if user else '',  # 未登录时留空（正常流程不会出现）
                create_time=now,  # 创建时间
                update_by=user.username if user else '',  # 初始更新人与创建人一致
                update_time=now,  # 初始更新时间
            )
        instance = serializer.save(**audit)
        self.after_create(request, instance)  # 子类可在此做关联数据写入
        return ok(self.get_serializer_class()(instance).data, '新增成功')  # 返回落库后的完整数据

    def update(self, request, pk=None):
        """编辑接口：部分更新，并记录更新人与更新时间。"""
        instance = self.get_queryset().filter(pk=pk).first()  # 只在未删除的数据中查找
        if not instance:
            return self._not_found()  # 不存在时返回业务码 404
        serializer = self.serializer_class(instance, data=request.data, partial=True)  # partial 允许只传变更字段
        serializer.is_valid(raise_exception=True)  # 校验失败统一转 400
        user = getattr(request, 'user_info', None)  # 操作人，用于审计字段
        audit = {}  # 日志类模型没有审计列，跳过即可
        if hasattr(self.model, 'update_by'):
            audit = dict(
                update_by=user.username if user else '',  # 更新人账号
                update_time=time.strftime('%Y-%m-%d %H:%M:%S'),  # 更新时刻
            )
        serializer.save(**audit)
        self.after_update(request, instance)  # 子类钩子，如同步更新关联表
        return ok(self.serializer_class(instance).data, '修改成功')  # 返回最新对象

    def delete(self, request):
        """批量删除接口：按 ids 做逻辑删除。"""
        ids = request.data.get('ids') or []  # 兼容未传或传 null 的情况
        if not ids:
            return ok(None, '请选择要删除的数据')  # 未选数据时给出提示而不是报错
        user = getattr(request, 'user_info', None)  # 操作人，用于记录删除者
        queryset = self.get_queryset().filter(id__in=ids)  # 先定位本次要删除的记录
        if hasattr(self.model, 'is_deleted'):
            queryset.update(
                is_deleted=1, update_by=user.username if user else '')  # 业务表统一逻辑删除，数据保留可追溯
        else:
            queryset.delete()  # 日志类模型无逻辑删除列，直接物理删除
        return ok(None, '删除成功')  # 无需回传数据

    # ---- 钩子 ----
    def status(self, request, pk=None):
        """启用/停用：按请求体的 status 或 enabled 字段更新指定记录。"""
        instance = self.get_queryset().filter(pk=pk).first()  # 只在未删除数据中查找
        if not instance:
            return self._not_found()  # 不存在时返回业务码 404
        data = request.data or {}
        fields = [f for f in ('status', 'enabled') if f in data]  # 兼容两种状态字段名
        if not fields:
            return fail('未提供状态字段', code=400)  # 参数缺失给出明确提示
        for field in fields:
            setattr(instance, field, data[field])  # 逐个赋值，兼容 status/enabled
        user = getattr(request, 'user_info', None)
        if hasattr(instance, 'update_by'):
            instance.update_by = user.username if user else ''
        if hasattr(instance, 'update_time'):
            instance.update_time = time.strftime('%Y-%m-%d %H:%M:%S')
        instance.save()  # 只保存本次改动
        return ok(self.serializer_class(instance).data, '状态更新成功')

    def after_create(self, request, instance):
        """新增后的扩展点，默认不做任何事。"""
        pass  # 子类按需覆盖

    def after_update(self, request, instance):
        """编辑后的扩展点，默认不做任何事。"""
        pass  # 子类按需覆盖

    @staticmethod
    def _not_found():
        """构造 404 业务响应，供按主键查询失败时复用。"""
        from common.response import fail  # 局部导入，避免与模块顶部导入产生冗余
        return fail('记录不存在', code=404)  # 业务码 404，HTTP 状态仍为 200
