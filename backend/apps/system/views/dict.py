"""数据字典：字典类型 + 字典项。"""
from apps.system.models import SysDictData, SysDictType
from apps.system.serializers import DictDataSerializer, DictTypeSerializer
from common.auth import LoginRequired
from common.response import ok
from common.views import CrudViewSet


class DictTypeViewSet(CrudViewSet):
    model = SysDictType
    serializer_class = DictTypeSerializer
    perm_prefix = 'system:dict'
    module_name = '字典管理'
    filter_map = {'dict_name': 'icontains', 'dict_type': 'icontains'}

    def delete(self, request):
        """删除字典类型时同步删除其字典项。"""
        from rest_framework.decorators import action  # noqa
        ids = request.data.get('ids') or []
        if not ids:
            return ok(None, '请选择要删除的数据')
        self.get_queryset().filter(id__in=ids).update(is_deleted=1)
        SysDictData.objects.filter(dict_type_id__in=ids).update(is_deleted=1)
        return ok(None, '删除成功')


class DictDataViewSet(CrudViewSet):
    model = SysDictData
    serializer_class = DictDataSerializer
    perm_prefix = 'system:dict'
    module_name = '字典管理'
    filter_map = {'dict_type_id': 'exact', 'status': 'exact'}

    def get_queryset(self):
        qs = super().get_queryset()
        dict_type = self.request.query_params.get('dict_type')
        if dict_type:
            type_id = SysDictType.objects.filter(dict_type=dict_type, is_deleted=0) \
                .values_list('id', flat=True).first()
            qs = qs.filter(dict_type_id=type_id) if type_id else qs.none()
        return qs

    def all(self, request):
        """全部启用字典（前端缓存做翻译与下拉）。"""
        types = SysDictType.objects.filter(is_deleted=0, status=0)
        data = []
        for t in types:
            items = SysDictData.objects.filter(dict_type_id=t.id, is_deleted=0, status=0)
            data.append({'dict_type': t.dict_type,
                         'list': [{'dict_label': i.dict_label, 'dict_value': i.dict_value}
                                  for i in items]})
        return ok(data)
