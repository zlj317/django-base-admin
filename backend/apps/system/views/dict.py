"""数据字典：字典类型 + 字典项。"""
from apps.system.models import SysDictData, SysDictType  # 字典项与字典类型模型
from apps.system.serializers import DictDataSerializer, DictTypeSerializer  # 两个序列化器
from common.auth import LoginRequired  # 登录校验（树/全量接口备用）
from common.response import ok  # 统一响应封装
from common.views import CrudViewSet  # 通用 CRUD 基类


class DictTypeViewSet(CrudViewSet):
    """字典类型管理视图：删除类型时级联删除其字典项。"""
    model = SysDictType  # 目标模型
    serializer_class = DictTypeSerializer  # 序列化器
    perm_prefix = 'system:dict'  # 权限标识前缀
    module_name = '字典管理'  # 操作日志模块名
    filter_map = {'dict_name': 'icontains', 'dict_type': 'icontains'}  # 列表筛选字段

    def delete(self, request):
        """删除字典类型时同步删除其字典项。"""
        from rest_framework.decorators import action  # noqa 函数内延迟导入，避免循环依赖
        ids = request.data.get('ids') or []  # 待删除类型ID
        if not ids:
            return ok(None, '请选择要删除的数据')  # 未选择数据
        self.get_queryset().filter(id__in=ids).update(is_deleted=1)  # 逻辑删除类型
        SysDictData.objects.filter(dict_type_id__in=ids).update(is_deleted=1)  # 级联删除字典项
        return ok(None, '删除成功')  # 返回成功


class DictDataViewSet(CrudViewSet):
    """字典项管理视图：支持按类型编码查询与全量启用字典输出。"""
    model = SysDictData  # 目标模型
    serializer_class = DictDataSerializer  # 序列化器
    perm_prefix = 'system:dict'  # 权限标识前缀
    module_name = '字典管理'  # 操作日志模块名
    filter_map = {'dict_type_id': 'exact', 'status': 'exact'}  # 列表筛选字段

    def get_queryset(self):
        """支持按 dict_type 编码（而非ID）过滤字典项。"""
        qs = super().get_queryset()  # 基类已过滤逻辑删除
        dict_type = self.request.query_params.get('dict_type')  # 类型编码参数
        if dict_type:
            type_id = SysDictType.objects.filter(dict_type=dict_type, is_deleted=0) \
                .values_list('id', flat=True).first()  # 编码换算为主键
            qs = qs.filter(dict_type_id=type_id) if type_id else qs.none()  # 无匹配则空集
        return qs  # 返回过滤后的查询集

    def all(self, request):
        """全部启用字典（前端缓存做翻译与下拉）。"""
        types = SysDictType.objects.filter(is_deleted=0, status=0)  # 启用的字典类型
        data = []
        for t in types:
            items = SysDictData.objects.filter(dict_type_id=t.id, is_deleted=0, status=0)  # 启用项
            data.append({'dict_type': t.dict_type,  # 类型编码作为键
                         'list': [{'dict_label': i.dict_label, 'dict_value': i.dict_value}
                                  for i in items]})  # 标签与键值列表
        return ok(data)  # 返回全部字典
