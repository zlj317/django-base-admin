"""导入模板 + 打印模板模块视图集。"""
from common.views import CrudViewSet

from apps.imprint.models import ImpTemplate, ImpTemplateColumn, PrintTemplate
from apps.imprint.serializers import (ImpTemplateColumnSerializer, ImpTemplateSerializer,
                                      PrintTemplateSerializer)


class ImpTemplateViewSet(CrudViewSet):
    """导入模板表 CRUD。"""
    model = ImpTemplate
    serializer_class = ImpTemplateSerializer
    perm_prefix = 'imprint'
    filter_map = {
        'template_name': 'icontains',
        'template_key': 'icontains',
        'status': 'exact',
    }
    order_by = '-id'
    module_name = '导入模板管理'


class ImpTemplateColumnViewSet(CrudViewSet):
    """导入模板列定义表 CRUD（无 BaseModel）。"""
    model = ImpTemplateColumn
    serializer_class = ImpTemplateColumnSerializer
    perm_prefix = 'imprint'
    filter_map = {
        'template_id': 'exact',
        'column_name': 'icontains',
    }
    order_by = '-id'
    module_name = '导入模板列管理'

    def get_queryset(self):
        return self.model.objects.filter(is_deleted=0).order_by(self.order_by)


class PrintTemplateViewSet(CrudViewSet):
    """打印模板表 CRUD。"""
    model = PrintTemplate
    serializer_class = PrintTemplateSerializer
    perm_prefix = 'imprint'
    filter_map = {
        'template_name': 'icontains',
        'template_key': 'icontains',
        'biz_type': 'exact',
        'status': 'exact',
    }
    order_by = '-id'
    module_name = '打印模板管理'
