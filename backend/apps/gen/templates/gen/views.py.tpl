"""{{ table.module_comment }} 管理接口（由代码生成器生成，可二次修改）。"""
import io
import time
from datetime import datetime

import openpyxl
from django.http import HttpResponse
from rest_framework import viewsets

from apps.{{ table.module_name }}.models import {{ table.class_name }}
from apps.{{ table.module_name }}.serializers import (
    {{ table.class_name }}CreateSerializer,
    {{ table.class_name }}ListSerializer,
    {{ table.class_name }}Serializer,
)
from common.pagination import StandardPagination
from common.permissions import PermissionCheck
from common.response import fail, ok

{% if table.export_enable %}
EXPORT_COLUMNS = [
{% for col in export_cols %}    ('{{ col.column_name }}', '{{ col.column_comment }}'),
{% endfor %}]
{% endif %}
{% if table.import_enable %}
IMPORT_COLUMNS = [
{% for col in import_cols %}    ('{{ col.column_name }}', '{{ col.column_comment }}'),
{% endfor %}]
{% endif %}

FILE_NAME = '{{ table.module_comment }}.xlsx'


class {{ table.class_name }}ViewSet(viewsets.ViewSet):
    """{{ table.module_comment }}管理"""

    module_name = '{{ table.module_comment }}'
    permission_classes = [PermissionCheck]

    @property
    def perm_map(self):
        prefix = '{{ table.module_name }}'
        return {
            'list': prefix + ':list',
            'create': prefix + ':create',
            'update': prefix + ':update',
            'delete': prefix + ':delete',
{% if table.import_enable %}            'import_template': prefix + ':import',
            'import_data': prefix + ':import',
{% endif %}{% if table.export_enable %}            'export_data': prefix + ':export',
{% endif %}        }

    def get_queryset(self):
        queryset = {{ table.class_name }}.objects.all()
{% if table.is_delete_logic %}        queryset = queryset.filter(is_deleted=0)
{% endif %}        return queryset.order_by('-{{ pk }}')

    def apply_filters(self, request, queryset):
{{ filters_code }}
        return queryset

    def list(self, request):
        queryset = self.apply_filters(request, self.get_queryset())
        return StandardPagination(request).paginate(queryset, {{ table.class_name }}ListSerializer)

    def create(self, request):
        serializer = {{ table.class_name }}CreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = getattr(request, 'user_info', None)
        now = time.strftime('%Y-%m-%d %H:%M:%S')
        instance = serializer.save(
            create_by=user.username if user else '', create_time=now,
            update_by=user.username if user else '', update_time=now)
        return ok({{ table.class_name }}Serializer(instance).data, '新增成功')

    def update(self, request, pk=None):
        instance = self.get_queryset().filter(pk=pk).first()
        if not instance:
            return fail('记录不存在', code=404)
        serializer = {{ table.class_name }}CreateSerializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        user = getattr(request, 'user_info', None)
        serializer.save(update_by=user.username if user else '',
                        update_time=time.strftime('%Y-%m-%d %H:%M:%S'))
        return ok({{ table.class_name }}Serializer(instance).data, '修改成功')

    def delete(self, request):
        ids = request.data.get('ids') or []
        if not ids:
            return fail('请选择要删除的数据')
        queryset = self.get_queryset().filter(id__in=ids)
{% if table.is_delete_logic %}        user = getattr(request, 'user_info', None)
        queryset.update(is_deleted=1, update_by=user.username if user else '')
{% else %}        queryset.delete()
{% endif %}        return ok(None, '删除成功')

{% if table.import_enable %}
    def import_template(self, request):
        """下载导入模板。"""
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = '{{ table.module_comment }}'
        ws.append([label for _, label in IMPORT_COLUMNS])
        buf = io.BytesIO()
        wb.save(buf)
        response = HttpResponse(
            buf.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename=import_template.xlsx'
        return response

    def import_data(self, request):
        """Excel 导入：校验失败返回行号与错误信息，不导入脏数据。"""
        file = request.FILES.get('file')
        if not file:
            return fail('请上传 Excel 文件')
        try:
            wb = openpyxl.load_workbook(file, read_only=True)
        except Exception:
            return fail('Excel 文件解析失败，请使用导入模板填写数据')
        ws = wb.active
        errors = []
        to_create = []
        for index, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            if all(v in (None, '') for v in row):
                continue
            data = {}
            for pos, (name, _) in enumerate(IMPORT_COLUMNS):
                if pos < len(row):
                    data[name] = row[pos]
            row_errors = []
{% for col in import_cols %}{% if col.is_required %}            if data.get('{{ col.column_name }}') in (None, ''):
                row_errors.append('{{ col.column_comment }} 不能为空')
{% endif %}{% endfor %}
            if row_errors:
                errors.extend('第 %d 行：%s' % (index, e) for e in row_errors)
                continue
            to_create.append({{ table.class_name }}(**data))
        if errors:
            return ok({'success_count': 0, 'errors': errors[:50]}, '校验失败，未导入任何数据')
        user = getattr(request, 'user_info', None)
        now = time.strftime('%Y-%m-%d %H:%M:%S')
        for obj in to_create:
            obj.create_by = user.username if user else ''
            obj.create_time = now
        {{ table.class_name }}.objects.bulk_create(to_create)
        return ok({'success_count': len(to_create), 'errors': []}, '导入成功')
{% endif %}

{% if table.export_enable %}
    def export_data(self, request):
        """按当前查询条件导出 Excel（限制最大行数）。"""
        queryset = self.apply_filters(request, self.get_queryset())
        queryset = queryset[:self.get_config_int('sys.export.max_rows', 50000)]
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = '{{ table.module_comment }}'
        ws.append([label for _, label in EXPORT_COLUMNS])
        for row in queryset:
            values = []
            for name, _ in EXPORT_COLUMNS:
                value = getattr(row, name, None)
                if isinstance(value, datetime):
                    value = value.strftime('%Y-%m-%d %H:%M:%S')
                values.append(value)
            ws.append(values)
        buf = io.BytesIO()
        wb.save(buf)
        response = HttpResponse(
            buf.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename=' + FILE_NAME
        return response

    @staticmethod
    def get_config_int(key, default):
        from apps.system.models import SysConfig
        value = SysConfig.objects.filter(config_key=key, is_deleted=0) \
            .values_list('config_value', flat=True).first()
        try:
            return int(value) if value else default
        except (TypeError, ValueError):
            return default
{% endif %}
