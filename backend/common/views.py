"""通用 CRUD 视图基类：统一分页/筛选/增删改 + 权限校验。"""
import time

from rest_framework import viewsets

from common.pagination import StandardPagination
from common.permissions import PermissionCheck
from common.response import ok


class CrudViewSet(viewsets.ViewSet):
    """通用 CRUD。

    子类配置：
      model:            模型类
      serializer_class: 序列化器
      perm_prefix:      权限前缀，如 'system:user'
      filter_map:       {查询参数: lookup}，如 {'username': 'icontains', 'status': 'exact'}
      order_by:         排序字段，默认 '-id'
      module_name:      操作日志模块名
    """

    model = None
    serializer_class = None
    perm_prefix = ''
    filter_map = {}
    order_by = '-id'
    module_name = ''

    @property
    def permission_classes(self):
        prefix = self.perm_prefix
        self.perm_map = {
            'list': f'{prefix}:list',
            'create': f'{prefix}:create',
            'update': f'{prefix}:update',
            'delete': f'{prefix}:delete',
        }
        return [PermissionCheck]

    def get_queryset(self):
        return self.model.objects.filter(is_deleted=0).order_by(self.order_by)

    def get_serializer_class(self):
        return self.serializer_class

    def apply_filters(self, queryset, request):
        for param, lookup in self.filter_map.items():
            value = request.query_params.get(param)
            if value not in (None, ''):
                queryset = queryset.filter(**{f'{param}__{lookup}': value})
        return queryset

    def list(self, request):
        queryset = self.apply_filters(self.get_queryset(), request)
        return StandardPagination(request).paginate(queryset, self.get_serializer_class())

    def create(self, request):
        serializer = self.get_serializer_class()(data=request.data)
        serializer.is_valid(raise_exception=True)
        now = time.strftime('%Y-%m-%d %H:%M:%S')
        user = getattr(request, 'user_info', None)
        instance = serializer.save(
            create_by=user.username if user else '',
            create_time=now,
            update_by=user.username if user else '',
            update_time=now,
        )
        self.after_create(request, instance)
        return ok(self.get_serializer_class()(instance).data, '新增成功')

    def update(self, request, pk=None):
        instance = self.get_queryset().filter(pk=pk).first()
        if not instance:
            return self._not_found()
        serializer = self.serializer_class(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        user = getattr(request, 'user_info', None)
        serializer.save(
            update_by=user.username if user else '',
            update_time=time.strftime('%Y-%m-%d %H:%M:%S'),
        )
        self.after_update(request, instance)
        return ok(self.serializer_class(instance).data, '修改成功')

    def delete(self, request):
        ids = request.data.get('ids') or []
        if not ids:
            return ok(None, '请选择要删除的数据')
        user = getattr(request, 'user_info', None)
        self.get_queryset().filter(id__in=ids).update(
            is_deleted=1, update_by=user.username if user else '')
        return ok(None, '删除成功')

    # ---- 钩子 ----
    def after_create(self, request, instance):
        pass

    def after_update(self, request, instance):
        pass

    @staticmethod
    def _not_found():
        from common.response import fail
        return fail('记录不存在', code=404)
