"""学生信息表 管理接口（由代码生成器生成，可二次修改）。"""
import io
import time
from datetime import datetime

import openpyxl
from django.http import HttpResponse
from rest_framework import viewsets

from apps.student.models import BizStudent
from apps.student.serializers import (
    BizStudentCreateSerializer,
    BizStudentListSerializer,
    BizStudentSerializer,
)
from common.pagination import StandardPagination
from common.permissions import PermissionCheck
from common.response import fail, ok


EXPORT_COLUMNS = [
    ('name', '学生姓名'),
    ('age', '年龄'),
    ('gender', '性别（字典sys_user_sex）'),
    ('phone', '手机号'),
    ('email', '邮箱'),
    ('enroll_date', '入学日期'),
    ('score', '总分'),
    ('address', '家庭住址'),
]


IMPORT_COLUMNS = [
    ('name', '学生姓名'),
    ('age', '年龄'),
    ('gender', '性别（字典sys_user_sex）'),
    ('phone', '手机号'),
    ('email', '邮箱'),
    ('enroll_date', '入学日期'),
    ('score', '总分'),
    ('address', '家庭住址'),
]


FILE_NAME = '学生信息表.xlsx'


class BizStudentViewSet(viewsets.ViewSet):
    """学生信息表管理"""

    module_name = '学生信息表'
    permission_classes = [PermissionCheck]

    @property
    def perm_map(self):
        prefix = 'student'
        return {
            'list': prefix + ':list',
            'create': prefix + ':create',
            'update': prefix + ':update',
            'delete': prefix + ':delete',
            'import_template': prefix + ':import',
            'import_data': prefix + ':import',
            'export_data': prefix + ':export',
        }

    def get_queryset(self):
        queryset = BizStudent.objects.all()
        queryset = queryset.filter(is_deleted=0)
        return queryset.order_by('-id')

    def apply_filters(self, request, queryset):
        queryset = queryset.filter(is_deleted=0)
        value = request.query_params.get('name')
        if value:
            queryset = queryset.filter(name__icontains=value)
        value = request.query_params.get('age')
        if value not in (None, ''):
            queryset = queryset.filter(age=value)
        value = request.query_params.get('gender')
        if value not in (None, ''):
            queryset = queryset.filter(gender=value)
        value = request.query_params.get('phone')
        if value:
            queryset = queryset.filter(phone__icontains=value)
        value = request.query_params.get('email')
        if value:
            queryset = queryset.filter(email__icontains=value)
        value = request.query_params.get('enroll_date')
        if value not in (None, ''):
            queryset = queryset.filter(enroll_date=value)
        value = request.query_params.get('score')
        if value not in (None, ''):
            queryset = queryset.filter(score=value)
        value = request.query_params.get('address')
        if value:
            queryset = queryset.filter(address__icontains=value)
        return queryset

    def list(self, request):
        queryset = self.apply_filters(request, self.get_queryset())
        return StandardPagination(request).paginate(queryset, BizStudentListSerializer)

    def create(self, request):
        serializer = BizStudentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = getattr(request, 'user_info', None)
        now = time.strftime('%Y-%m-%d %H:%M:%S')
        instance = serializer.save(
            create_by=user.username if user else '', create_time=now,
            update_by=user.username if user else '', update_time=now)
        return ok(BizStudentSerializer(instance).data, '新增成功')

    def update(self, request, pk=None):
        instance = self.get_queryset().filter(pk=pk).first()
        if not instance:
            return fail('记录不存在', code=404)
        serializer = BizStudentCreateSerializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        user = getattr(request, 'user_info', None)
        serializer.save(update_by=user.username if user else '',
                        update_time=time.strftime('%Y-%m-%d %H:%M:%S'))
        return ok(BizStudentSerializer(instance).data, '修改成功')

    def delete(self, request):
        ids = request.data.get('ids') or []
        if not ids:
            return fail('请选择要删除的数据')
        queryset = self.get_queryset().filter(id__in=ids)
        user = getattr(request, 'user_info', None)
        queryset.update(is_deleted=1, update_by=user.username if user else '')
        return ok(None, '删除成功')


    def import_template(self, request):
        """下载导入模板。"""
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = '学生信息表'
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
            if data.get('name') in (None, ''):
                row_errors.append('学生姓名 不能为空')

            if row_errors:
                errors.extend('第 %d 行：%s' % (index, e) for e in row_errors)
                continue
            to_create.append(BizStudent(**data))
        if errors:
            return ok({'success_count': 0, 'errors': errors[:50]}, '校验失败，未导入任何数据')
        user = getattr(request, 'user_info', None)
        now = time.strftime('%Y-%m-%d %H:%M:%S')
        for obj in to_create:
            obj.create_by = user.username if user else ''
            obj.create_time = now
        BizStudent.objects.bulk_create(to_create)
        return ok({'success_count': len(to_create), 'errors': []}, '导入成功')



    def export_data(self, request):
        """按当前查询条件导出 Excel（限制最大行数）。"""
        queryset = self.apply_filters(request, self.get_queryset())
        queryset = queryset[:self.get_config_int('sys.export.max_rows', 50000)]
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = '学生信息表'
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

