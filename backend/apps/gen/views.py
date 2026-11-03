"""代码生成器视图。"""
import io
import zipfile
from datetime import datetime

from django.db import connection, transaction
from django.http import HttpResponse
from rest_framework import viewsets

from apps.gen import engine
from apps.gen.models import SysGenTable, SysGenTableColumn
from apps.gen.serializers import GenColumnSerializer, GenTableSerializer
from apps.system.models import SysMenu
from common.pagination import StandardPagination
from common.permissions import PermissionCheck
from common.response import fail, ok


class GenTableViewSet(viewsets.ViewSet):
    """代码生成：表读取 / 配置 / 预览 / 下载。"""

    module_name = '代码生成'

    @property
    def perm_map(self):
        return {
            'list': 'gen:table:list',
            'db_tables': 'gen:table:import',
            'import_tables': 'gen:table:import',
            'retrieve': 'gen:table:list',
            'save': 'gen:table:update',
            'delete': 'gen:table:delete',
            'preview': 'gen:table:preview',
            'download': 'gen:table:download',
            'ddl': 'gen:table:preview',
        }

    permission_classes = [PermissionCheck]

    # ---- 数据库表读取与导入 ----
    def db_tables(self, request):
        keyword = request.query_params.get('table_name')
        tables = engine.list_db_tables(keyword)
        page = StandardPagination(request)
        start = page.offset
        data = {
            'total': len(tables),
            'page': page.page,
            'page_size': page.page_size,
            'list': tables[start:start + page.page_size],
        }
        return ok(data)

    def import_tables(self, request):
        table_names = request.data.get('tables') or []
        if not table_names:
            return fail('请选择要导入的表')
        errors, success = [], []
        username = request.user_info.username
        for name in table_names:
            try:
                engine.import_table(name, username)
                success.append(name)
            except Exception as exc:
                errors.append(f'{name}: {exc}')
        msg = f'成功导入 {len(success)} 张表'
        if errors:
            msg += '；失败：' + '；'.join(errors)
        return ok({'success': success, 'errors': errors}, msg)

    # ---- 生成配置管理 ----
    def list(self, request):
        queryset = SysGenTable.objects.filter(is_deleted=0).order_by('-id')
        table_name = request.query_params.get('table_name')
        module_comment = request.query_params.get('module_comment')
        if table_name:
            queryset = queryset.filter(table_name__icontains=table_name)
        if module_comment:
            queryset = queryset.filter(module_comment__icontains=module_comment)
        page = StandardPagination(request)
        total = queryset.count()
        rows = queryset[page.offset:page.offset + page.page_size]
        data = []
        for t in rows:
            item = GenTableSerializer(t).data
            item['column_count'] = SysGenTableColumn.objects.filter(
                gen_table_id=t.id, is_deleted=0).count()
            data.append(item)
        return ok({'total': total, 'page': page.page, 'page_size': page.page_size, 'list': data})

    def retrieve(self, request, pk=None):
        """生成配置详情（不可命名为 detail：DRF as_view 会设置 cls.detail=None 遮蔽）。"""
        table = SysGenTable.objects.filter(pk=pk, is_deleted=0).first()
        if not table:
            return fail('配置不存在', code=404)
        columns = SysGenTableColumn.objects.filter(gen_table_id=pk, is_deleted=0)
        return ok({
            'table': GenTableSerializer(table).data,
            'columns': GenColumnSerializer(columns, many=True).data,
        })

    def save(self, request, pk=None):
        """保存生成配置：主表信息 + 整组字段配置（整体替换）。"""
        table = SysGenTable.objects.filter(pk=pk, is_deleted=0).first()
        if not table:
            return fail('配置不存在', code=404)

        with transaction.atomic():
            table_serializer = GenTableSerializer(table, data=request.data.get('table') or {},
                                                  partial=True)
            table_serializer.is_valid(raise_exception=True)
            username = request.user_info.username
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            table_serializer.save(update_by=username, update_time=now)

            columns = request.data.get('columns')
            if columns is not None:
                SysGenTableColumn.objects.filter(gen_table_id=pk).delete()
                for i, col in enumerate(columns):
                    col = dict(col)
                    col['gen_table_id'] = pk
                    col['sort'] = col.get('sort', i)
                    col['create_by'] = username
                    col['create_time'] = now
                    col_serializer = GenColumnSerializer(data=col)
                    col_serializer.is_valid(raise_exception=True)
                    col_serializer.save()
        return ok(None, '保存成功')

    def delete(self, request):
        ids = request.data.get('ids') or []
        if not ids:
            return fail('请选择要删除的数据')
        SysGenTable.objects.filter(id__in=ids).update(is_deleted=1)
        SysGenTableColumn.objects.filter(gen_table_id__in=ids).update(is_deleted=1)
        return ok(None, '删除成功')

    # ---- 预览 / DDL / 下载 ----
    def _load(self, pk):
        table = SysGenTable.objects.filter(pk=pk, is_deleted=0).first()
        if not table:
            return None, None
        columns = list(SysGenTableColumn.objects.filter(gen_table_id=pk, is_deleted=0))
        return table, columns

    def preview(self, request, pk=None):
        table, columns = self._load(pk)
        if not table:
            return fail('配置不存在', code=404)
        files = engine.render_files(table, columns)
        return ok({'files': [{'name': path.split('/')[-1], 'path': path, 'content': content}
                             for path, content in files]})

    def ddl(self, request, pk=None):
        table, _ = self._load(pk)
        if not table:
            return fail('配置不存在', code=404)
        try:
            return ok({'ddl': engine.get_table_ddl(table.table_name)})
        except ValueError as exc:
            return fail(str(exc))

    def download(self, request, pk=None):
        """打包 ZIP 下载；若配置了父级菜单则自动注册菜单与按钮权限。"""
        table, columns = self._load(pk)
        if not table:
            return fail('配置不存在', code=404)
        if table.parent_menu_id:
            self.create_menus(table, columns, request.user_info.username)

        files = engine.render_files(table, columns)
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
            for path, content in files:
                zf.writestr(path, content or '\n')
        response = HttpResponse(buf.getvalue(),
                                content_type='application/octet-stream')
        response['Content-Disposition'] = f'attachment; filename={table.module_name}_code.zip'
        return response

    def create_menus(self, table, columns, username):
        """在 sys_menu 中注册业务菜单与按钮权限。"""
        prefix = table.module_name
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        def insert(parent_id, menu_name, menu_type, path='', component='', perms='', icon=''):
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO sys_menu (parent_id, menu_name, path, component, perms, "
                    "menu_type, icon, order_num, visible, status, create_by, create_time, is_deleted) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, 0, '0', '0', %s, %s, 0)",
                    [parent_id, menu_name, path, component, perms, menu_type, icon, username, now])
                cursor.execute("SELECT LAST_INSERT_ID()")
                return cursor.fetchone()[0]

        if SysMenu.objects.filter(perms=f'{prefix}:list', is_deleted=0).exists():
            return  # 已注册过
        parent_id = table.parent_menu_id or 0
        menu_id = insert(parent_id, table.module_comment, 'C',
                         path=table.module_name,
                         component=table.gen_path or f'{prefix}/index',
                         icon='Document')
        buttons = [('查询', f'{prefix}:list'), ('新增', f'{prefix}:create'),
                   ('编辑', f'{prefix}:update'), ('删除', f'{prefix}:delete')]
        if table.import_enable:
            buttons.append(('导入', f'{prefix}:import'))
        if table.export_enable:
            buttons.append(('导出', f'{prefix}:export'))
        for name, perms in buttons:
            insert(menu_id, name, 'F', perms=perms)
