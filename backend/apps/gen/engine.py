"""代码生成引擎：读取数据表、默认配置推断、模板渲染、ZIP 打包、菜单注册。"""
import io
import os
import re
import zipfile
from datetime import datetime

from django.db import connection
from django.template import Context, Engine

from apps.gen.models import SysGenTable, SysGenTableColumn

TPL_DIR = os.path.join(os.path.dirname(__file__), 'templates', 'gen')

FORM_TYPE_RULES = [
    ('image', re.compile(r'(_img|_image|_pic|_avatar)$|图片|头像')),
    ('file', re.compile(r'(_file|_url|_attachment)$|附件|文件地址')),
    ('date', None),  # 由类型判断
    ('textarea', re.compile(r'text|json')),
]
COMMON_SKIP = {'create_by', 'create_time', 'update_by', 'update_time', 'is_deleted', 'remark'}

_engine = None


def tpl_engine():
    global _engine
    if _engine is None:
        _engine = Engine(dirs=[TPL_DIR], autoescape=False)
    return _engine


def render_tpl(name, context):
    return tpl_engine().get_template(name).render(Context(context, autoescape=False))


def snake_to_pascal(name):
    return ''.join(part.capitalize() for part in name.split('_'))


# ---------------------------------------------------------------- 数据库读取

TABLE_NAME_RE = re.compile(r'^[A-Za-z0-9_]+$')


def list_db_tables(keyword=None):
    """读取当前库中的业务表（排除 sys_ 前缀与 Django 内置表）。"""
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT table_name, table_comment, table_rows, create_time "
            "FROM information_schema.tables "
            "WHERE table_schema = DATABASE() AND table_type = 'BASE TABLE' "
            "ORDER BY table_name")
        tables = cursor.fetchall()
    imported = set(SysGenTable.objects.filter(is_deleted=0)
                   .values_list('table_name', flat=True))
    result = []
    for name, comment, rows, create_time in tables:
        if name.startswith(('sys_', 'django_', 'auth_')):
            continue
        if keyword and keyword.lower() not in name.lower():
            continue
        result.append({
            'table_name': name,
            'table_comment': comment or '',
            'table_rows': rows or 0,
            'create_time': create_time.strftime('%Y-%m-%d %H:%M:%S') if isinstance(create_time, datetime) else create_time,
            'imported': name in imported,
        })
    return result


def get_table_ddl(table_name):
    if not TABLE_NAME_RE.match(table_name or ''):
        raise ValueError('非法表名')
    with connection.cursor() as cursor:
        cursor.execute(f'SHOW CREATE TABLE `{table_name}`')
        return cursor.fetchone()[1]


def get_db_columns(table_name):
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT column_name, column_type, column_comment, is_nullable, column_key, extra "
            "FROM information_schema.columns "
            "WHERE table_schema = DATABASE() AND table_name = %s ORDER BY ordinal_position",
            [table_name])
        return cursor.fetchall()


# ---------------------------------------------------------------- 导入与默认配置

def guess_form_type(column_name, base_type, comment):
    for form_type, pattern in FORM_TYPE_RULES:
        if form_type == 'date':
            continue
        if pattern and (pattern.search(column_name) or pattern.search(comment or '')):
            return form_type
    if base_type in ('datetime', 'timestamp', 'date'):
        return 'date'
    if base_type in ('text', 'mediumtext', 'longtext'):
        return 'textarea'
    if base_type in ('int', 'bigint', 'tinyint', 'smallint', 'decimal', 'numeric',
                     'float', 'double'):
        return 'number'
    return 'input'


def guess_query_type(base_type):
    if base_type in ('varchar', 'char', 'text'):
        return 'like'
    return 'eq'


def import_table(table_name, username=''):
    """导入一张数据表：写入生成配置主表与默认字段配置。"""
    if not TABLE_NAME_RE.match(table_name or ''):
        raise ValueError(f'非法表名：{table_name}')
    if table_name.startswith('sys_'):
        raise ValueError(f'系统表 {table_name} 不允许导入')
    if SysGenTable.objects.filter(table_name=table_name, is_deleted=0).exists():
        raise ValueError(f'表 {table_name} 已导入过')

    # 表注释
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT table_comment FROM information_schema.tables "
            "WHERE table_schema = DATABASE() AND table_name = %s", [table_name])
        row = cursor.fetchone()
    table_comment = (row[0] if row else '') or table_name

    segments = table_name.strip('_').split('_')
    module_name = segments[-1] if len(segments) > 1 else table_name
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    gen_table = SysGenTable.objects.create(
        table_name=table_name,
        table_comment=table_comment,
        class_name=snake_to_pascal(table_name),
        module_name=module_name,
        module_comment=table_comment,
        url_prefix=f'/api/{module_name}',
        gen_path=f'{module_name}/index',
        parent_menu_id=None,
        is_delete_logic=True,
        import_enable=True,
        export_enable=True,
        create_by=username, create_time=now, update_by=username, update_time=now,
    )

    for i, (col_name, col_type, col_comment, nullable, col_key, extra) in \
            enumerate(get_db_columns(table_name)):
        base_type = col_type.lower().split('(')[0]
        is_pk = 1 if col_key == 'PRI' else 0
        skip_common = col_name in COMMON_SKIP
        has_default = bool(get_column_default(table_name, col_name))
        SysGenTableColumn.objects.create(
            gen_table_id=gen_table.id,
            column_name=col_name,
            column_comment=col_comment or col_name,
            column_type=col_type,
            is_pk=is_pk,
            dict_type='',
            form_type='input' if is_pk else guess_form_type(col_name, base_type, col_comment),
            is_list=0 if (is_pk or skip_common) else 1,
            is_query=0 if (is_pk or skip_common) else 1,
            query_type=guess_query_type(base_type),
            # 主键/公共列/有默认值/自增/可空 字段均不作为必填表单项
            is_required=0 if (is_pk or skip_common or has_default
                              or nullable == 'YES' or 'auto_increment' in (extra or '')) else 1,
            is_export=0 if (is_pk or skip_common) else 1,
            is_import=0 if (is_pk or skip_common) else 1,
            sort=i,
            create_by=username, create_time=now,
        )
    return gen_table


def get_column_default(table_name, column_name):
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT column_default FROM information_schema.columns "
            "WHERE table_schema = DATABASE() AND table_name = %s AND column_name = %s",
            [table_name, column_name])
        return cursor.fetchone()[0]


# ---------------------------------------------------------------- 字段映射

def parse_type_limits(raw_type):
    m = re.search(r'\((\d+)(?:,(\d+))?\)', raw_type or '')
    if not m:
        return None, None
    return int(m.group(1)), (int(m.group(2)) if m.group(2) else None)


def django_field_def(col):
    """列配置 → Django 模型字段定义字符串。"""
    raw = (col.column_type or '').lower()
    base = raw.split('(')[0].strip()
    comment = (col.column_comment or col.column_name).replace("'", "\\'")
    null_part = 'null=True, blank=True' if not col.is_required else ''

    if base in ('varchar', 'char'):
        length, _ = parse_type_limits(raw)
        args = f"verbose_name='{comment}', max_length={length or 255}"
    elif base in ('text', 'mediumtext', 'longtext'):
        args = f"verbose_name='{comment}'"
    elif base in ('bigint',):
        args = f"verbose_name='{comment}'"
    elif base in ('int', 'integer'):
        args = f"verbose_name='{comment}'"
    elif base in ('tinyint', 'smallint'):
        args = f"verbose_name='{comment}'"
    elif base in ('decimal', 'numeric'):
        _, places = parse_type_limits(raw)
        args = f"verbose_name='{comment}', max_digits=18, decimal_places={places or 2}"
    elif base in ('float', 'double'):
        args = f"verbose_name='{comment}'"
    elif base in ('datetime', 'timestamp'):
        args = f"verbose_name='{comment}'"
    elif base == 'date':
        args = f"verbose_name='{comment}'"
    elif base == 'time':
        args = f"verbose_name='{comment}'"
    else:
        args = f"verbose_name='{comment}', max_length=255"

    if (col.column_name or '') == 'is_deleted':
        # 逻辑删除列在库中为 NOT NULL DEFAULT 0，生成 default 而非 null
        null_part = ''
        args += ', default=0'
    if null_part:
        args += ', ' + null_part
    field_map = {
        'bigint': 'models.BigIntegerField', 'int': 'models.IntegerField',
        'integer': 'models.IntegerField', 'tinyint': 'models.SmallIntegerField',
        'smallint': 'models.SmallIntegerField', 'decimal': 'models.DecimalField',
        'numeric': 'models.DecimalField', 'float': 'models.FloatField',
        'double': 'models.FloatField', 'datetime': 'models.DateTimeField',
        'timestamp': 'models.DateTimeField', 'date': 'models.DateField',
        'time': 'models.TimeField', 'text': 'models.TextField',
        'mediumtext': 'models.TextField', 'longtext': 'models.TextField',
        'varchar': 'models.CharField', 'char': 'models.CharField',
    }
    field_cls = field_map.get(base, 'models.CharField')
    return f"{field_cls}({args})"


# ---------------------------------------------------------------- 代码渲染

def render_files(table, columns):
    """渲染全部生成文件，返回 [(相对路径, 内容), ...]。"""
    table_dict = {
        'table_name': table.table_name,
        'class_name': table.class_name,
        'module_name': table.module_name,
        'module_comment': table.module_comment,
        'url_prefix': table.url_prefix,
        'gen_path': table.gen_path,
        'is_delete_logic': bool(table.is_delete_logic),
        'import_enable': bool(table.import_enable),
        'export_enable': bool(table.export_enable),
    }
    cols = []
    for c in columns:
        base_type = (c.column_type or '').lower().split('(')[0].strip()
        cols.append({
            'column_name': c.column_name,
            'column_comment': c.column_comment or c.column_name,
            'column_type': c.column_type,
            'is_pk': bool(c.is_pk),
            'form_type': c.form_type or 'input',
            'dict_type': c.dict_type or '',
            'is_list': bool(c.is_list),
            'is_query': bool(c.is_query),
            'query_type': c.query_type or 'eq',
            'is_required': bool(c.is_required),
            'is_export': bool(c.is_export),
            'is_import': bool(c.is_import),
            'is_char': base_type in ('varchar', 'char', 'text', 'mediumtext', 'longtext'),
            'sort': c.sort,
            'field_def': django_field_def(c),
        })

    pk_col = next((c for c in cols if c['is_pk']), {'column_name': 'id'})
    business_cols = [c for c in cols if not c['is_pk']]
    form_cols = [c for c in business_cols if c['form_type'] and c['column_name'] not in COMMON_SKIP]
    list_cols = [c for c in business_cols if c['is_list']]
    query_cols = [c for c in business_cols if c['is_query']]
    export_cols = [c for c in business_cols if c['is_export']]
    import_cols = [c for c in business_cols if c['is_import'] and c['column_name'] not in COMMON_SKIP]

    context = {
        'table': table_dict,
        'columns': cols,
        'form_cols': form_cols,
        'list_cols': list_cols,
        'query_cols': query_cols,
        'export_cols': export_cols,
        'import_cols': import_cols,
        'pk': pk_col['column_name'],
        'route': (table_dict['url_prefix'] or '').replace('/api/', '').strip('/'),
        'has_create_time': any(c['column_name'] == 'create_time' for c in cols),
        'buttons': [
            ('查询', f"{table.module_name}:list"),
            ('新增', f"{table.module_name}:create"),
            ('编辑', f"{table.module_name}:update"),
            ('删除', f"{table.module_name}:delete"),
        ] + ([('导入', f'{table.module_name}:import')] if table.import_enable else [])
        + ([('导出', f'{table.module_name}:export')] if table.export_enable else []),
        'filters_code': build_filters_code(query_cols, table_dict['is_delete_logic']),
    }

    files = [
        (f'backend/apps/{table.module_name}/__init__.py', ''),
        (f'backend/apps/{table.module_name}/apps.py', render_tpl('apps.py.tpl', context)),
        (f'backend/apps/{table.module_name}/models.py', render_tpl('models.py.tpl', context)),
        (f'backend/apps/{table.module_name}/serializers.py', render_tpl('serializers.py.tpl', context)),
        (f'backend/apps/{table.module_name}/views.py', render_tpl('views.py.tpl', context)),
        (f'backend/apps/{table.module_name}/urls.py', render_tpl('urls.py.tpl', context)),
        ('README-部署说明.txt', render_tpl('readme.txt.tpl', context)),
        ('frontend/src/api/' + table.module_name + '.js', build_api_js(table_dict, context)),
        ('frontend/src/views/' + table.gen_path + '.vue', build_vue_page(table_dict, context)),
    ]
    return files


def build_filters_code(query_cols, logic_delete):
    """生成 views.py 中的过滤代码（含缩进 8 空格）。"""
    lines = []
    if logic_delete:
        lines.append('        queryset = queryset.filter(is_deleted=0)')
    for c in query_cols:
        name, qtype = c['column_name'], c['query_type']
        if qtype == 'like':
            lines.append(
                f"        value = request.query_params.get('{name}')\n"
                f"        if value:\n"
                f"            queryset = queryset.filter({name}__icontains=value)")
        elif qtype == 'between':
            lines.append(
                f"        start = request.query_params.get('{name}_start')\n"
                f"        end = request.query_params.get('{name}_end')\n"
                f"        if start:\n"
                f"            queryset = queryset.filter({name}__gte=start)\n"
                f"        if end:\n"
                f"            queryset = queryset.filter({name}__lte=end)")
        elif qtype == 'gt':
            lines.append(
                f"        value = request.query_params.get('{name}')\n"
                f"        if value:\n"
                f"            queryset = queryset.filter({name}__gt=value)")
        elif qtype == 'lt':
            lines.append(
                f"        value = request.query_params.get('{name}')\n"
                f"        if value:\n"
                f"            queryset = queryset.filter({name}__lt=value)")
        else:  # eq
            lines.append(
                f"        value = request.query_params.get('{name}')\n"
                f"        if value not in (None, ''):\n"
                f"            queryset = queryset.filter({name}=value)")
    if not lines:
        lines.append('        pass  # 未配置查询条件')
    return '\n'.join(lines)


# ---------------------------------------------------------------- Vue / JS 生成

def vue_component(col):
    """根据 form_type 生成 el-form-item 内部控件代码。"""
    name, label = col['column_name'], col['column_comment']
    ph = f"placeholder=\"请输入{label}\""
    if col['form_type'] == 'number':
        return f'<el-input-number v-model="form.{name}" :min="0" style="width: 100%" />'
    if col['form_type'] == 'date':
        return f'<el-date-picker v-model="form.{name}" type="datetime" {ph} value-format="YYYY-MM-DD HH:mm:ss" style="width: 100%" />'
    if col['form_type'] == 'select' and col['dict_type']:
        return (f'<el-select v-model="form.{name}" {ph} clearable style="width: 100%">\n'
                f'            <el-option v-for="d in dictList(\'{col["dict_type"]}\')" :key="d.dict_value" '
                f':label="d.dict_label" :value="d.dict_value" />\n'
                f'          </el-select>')
    if col['form_type'] == 'radio' and col['dict_type']:
        return (f'<el-radio-group v-model="form.{name}">\n'
                f'            <el-radio v-for="d in dictList(\'{col["dict_type"]}\')" :key="d.dict_value" '
                f':value="d.dict_value">' + '{{ d.dict_label }}</el-radio>\n'
                f'          </el-radio-group>')
    if col['form_type'] == 'textarea':
        return f'<el-input v-model="form.{name}" type="textarea" :rows="3" {ph} />'
    if col['form_type'] == 'image':
        return f'<el-input v-model="form.{name}" {ph} />'
    if col['form_type'] == 'file':
        return f'<el-input v-model="form.{name}" {ph} />'
    return f'<el-input v-model="form.{name}" {ph} />'


def build_vue_page(table, ctx):
    """生成 Vue 列表页 SFC。"""
    m = table['module_name']
    cn = table['class_name']
    lines = []
    a = lines.append

    # ---- template：查询区 ----
    a('<template>')
    a('  <div class="app-container">')
    a('    <div class="page-header">')
    a('      <div class="page-title-wrap">')
    a('        <h2>%s</h2>' % table['module_comment'])
    a('        <div class="sub">数据维护 · 共 {{ total }} 条记录</div>')
    a('      </div>')
    a('    </div>')
    a('    <!-- 查询区域 -->')
    a('    <el-card shadow="never" class="search-card">')
    if ctx['query_cols']:
        a('      <el-form :model="query" inline @submit.prevent>')
        for c in ctx['query_cols']:
            if c['query_type'] == 'between':
                a(f'        <el-form-item label="{c["column_comment"]}">')
                a(f'          <el-date-picker v-model="query.{c["column_name"]}_start" type="date" value-format="YYYY-MM-DD" placeholder="开始日期" style="width: 160px" />')
                a(f'          <span> - </span>')
                a(f'          <el-date-picker v-model="query.{c["column_name"]}_end" type="date" value-format="YYYY-MM-DD" placeholder="结束日期" style="width: 160px" />')
                a('        </el-form-item>')
            elif c['form_type'] == 'select' and c['dict_type']:
                a(f'        <el-form-item label="{c["column_comment"]}">')
                a(f'          <el-select v-model="query.{c["column_name"]}" placeholder="请选择" clearable style="width: 180px">')
                a(f'            <el-option v-for="d in dictList(\'{c["dict_type"]}\')" :key="d.dict_value" :label="d.dict_label" :value="d.dict_value" />')
                a('          </el-select>')
                a('        </el-form-item>')
            else:
                a(f'        <el-form-item label="{c["column_comment"]}">')
                a(f'          <el-input v-model="query.{c["column_name"]}" placeholder="请输入{c["column_comment"]}" clearable style="width: 180px" @keyup.enter="handleQuery" />')
                a('        </el-form-item>')
        a('        <el-form-item class="search-actions">')
        a('          <el-button type="primary" :icon="Search" @click="handleQuery">查询</el-button>')
        a('          <el-button :icon="Refresh" @click="resetQuery">重置</el-button>')
        a('        </el-form-item>')
        a('      </el-form>')
    a('    </el-card>')
    a('')
    # ---- 表格 ----
    a('    <!-- 数据表格 -->')
    a('    <el-card shadow="never" class="table-card">')
    a('      <template #header>')
    a('        <div class="card-header">')
    a('          <span class="card-title">%s列表</span>' % table['module_comment'])
    a('          <div class="card-actions">')
    a('            <el-button v-perm="\'%s:create\'" type="primary" :icon="Plus" @click="openCreate">新增</el-button>' % m)
    if table['import_enable']:
        a('            <el-button v-perm="\'%s:import\'" type="success" plain :icon="Upload" @click="importVisible = true">导入</el-button>' % m)
    if table['export_enable']:
        a('            <el-button v-perm="\'%s:export\'" type="warning" plain :icon="Download" @click="handleExport">导出</el-button>' % m)
    a('            <el-button v-perm="\'%s:delete\'" type="danger" plain :icon="Delete" :disabled="!selectedIds.length" @click="handleBatchDelete">批量删除</el-button>' % m)
    a('          </div>')
    a('        </div>')
    a('      </template>')
    a('      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据" @selection-change="onSelectionChange">')
    a('        <el-table-column type="selection" width="50" align="center" />')
    for c in ctx['list_cols']:
        if c['form_type'] == 'select' and c['dict_type']:
            a(f'        <el-table-column label="{c["column_comment"]}" prop="{c["column_name"]}" align="center">')
            a(f'          <template #default="scope">')
            a(f'            <el-tag :type="scope.row.{c["column_name"]} === \'0\' ? \'primary\' : \'info\'">' + '{{ dictLabel(\'' + c['dict_type'] + '\', scope.row.' + c['column_name'] + ') }}</el-tag>')
            a('          </template>')
            a('        </el-table-column>')
        else:
            a(f'        <el-table-column label="{c["column_comment"]}" prop="{c["column_name"]}" align="center" show-overflow-tooltip />')
    a('        <el-table-column label="操作" width="150" align="center" fixed="right">')
    a('          <template #default="scope">')
    a('            <el-button v-perm="\'%s:update\'" link type="primary" :icon="Edit" @click="handleEdit(scope.row)">编辑</el-button>' % m)
    a('            <el-button v-perm="\'%s:delete\'" link type="danger" :icon="Delete" @click="handleDelete(scope.row)">删除</el-button>' % m)
    a('          </template>')
    a('        </el-table-column>')
    a('      </el-table>')
    a('      <div class="pagination-wrap">')
    a('        <el-pagination background layout="total, sizes, prev, pager, next, jumper"')
    a('          :total="total" v-model:current-page="query.page" v-model:page-size="query.page_size"')
    a('          :page-sizes="[10, 20, 50, 100]" @change="getList" />')
    a('      </div>')
    a('    </el-card>')

    # ---- 新增/编辑弹窗 ----
    a('    <!-- 新增/编辑弹窗 -->')
    a('    <el-dialog :title="form.%s ? \'编辑%s\' : \'新增%s\'" v-model="dialogVisible" width="640px" :close-on-click-modal="false" destroy-on-close>' % (ctx['pk'], table['module_comment'], table['module_comment']))
    a('      <el-form ref="formRef" :model="form" :rules="rules" label-width="110px" class="dialog-form">')
    for c in ctx['form_cols']:
        if c['column_name'] == ctx['pk']:
            continue
        a(f'        <el-form-item label="{c["column_comment"]}" prop="{c["column_name"]}">')
        a('          ' + vue_component(c))
        a('        </el-form-item>')
    a('      </el-form>')
    a('      <template #footer>')
    a('        <el-button @click="dialogVisible = false">取消</el-button>')
    a('        <el-button type="primary" :loading="saving" @click="submitForm">确定</el-button>')
    a('      </template>')
    a('    </el-dialog>')

    # ---- 导入弹窗 ----
    if table['import_enable']:
        a('    <!-- 导入弹窗 -->')
        a('    <el-dialog title="导入%s" v-model="importVisible" width="420px">' % table['module_comment'])
        a('      <el-upload drag :auto-upload="false" :limit="1" accept=".xlsx,.xls" :on-change="onFileChange" :file-list="fileList">')
        a('        <el-icon size="40"><UploadFilled /></el-icon>')
        a('        <div>将 Excel 文件拖到此处，或点击选择</div>')
        a('      </el-upload>')
        a('      <div class="mt12">')
        a('        <el-button link type="primary" @click="downloadTemplate">下载导入模板</el-button>')
        a('      </div>')
        a('      <el-alert v-if="importErrors.length" type="error" :closable="false" class="mt12">')
        a('        <div v-for="e in importErrors" :key="e"> ' + '{{ e }}</div>')
        a('      </el-alert>')
        a('      <template #footer>')
        a('        <el-button @click="importVisible = false">取消</el-button>')
        a('        <el-button type="primary" :loading="importing" @click="submitImport">开始导入</el-button>')
        a('      </template>')
        a('    </el-dialog>')

    a('  </div>')
    a('</template>')

    # ---- script ----
    a('')
    a('<script setup>')
    a("import { reactive, ref } from 'vue'")
    a("import { ElMessage, ElMessageBox } from 'element-plus'")
    a("import { UploadFilled, Plus, Edit, Delete, Search, Refresh, Upload, Download } from '@element-plus/icons-vue'")
    a("import { createApi, deleteApi, exportApi, importApi, listApi, templateApi, updateApi } from '@/api/%s'" % m)
    a("import { dictLabel, dictList, loadDicts } from '@/utils/dict'")
    a('')
    a("loadDicts()")
    a('')
    a('const loading = ref(false)')
    a('const saving = ref(false)')
    a('const rows = ref([])')
    a('const total = ref(0)')
    a('const selectedIds = ref([])')
    a('const dialogVisible = ref(false)')
    a('const formRef = ref()')
    if table['import_enable']:
        a('const importVisible = ref(false)')
        a('const importing = ref(false)')
        a('const importFile = ref(null)')
        a('const importErrors = ref([])')
        a('const fileList = ref([])')
    a('')
    a('const query = reactive({ page: 1, page_size: 10 })')
    for c in ctx['query_cols']:
        if c['query_type'] == 'between':
            a(f"query.{c['column_name']}_start = ''")
            a(f"query.{c['column_name']}_end = ''")
        else:
            a(f"query.{c['column_name']} = ''")
    a('')
    a('const emptyForm = { %s: null }' % ctx['pk'])
    for c in ctx['form_cols']:
        if c['column_name'] == ctx['pk']:
            continue
        # el-input-number 要求 Number/null，字符串初始值会触发类型校验错误
        init = 'null' if c['form_type'] == 'number' else "''"
        a(f"emptyForm.{c['column_name']} = {init}")
    a('const form = reactive({ ...emptyForm })')
    a('')
    a('const rules = {')
    for c in ctx['form_cols']:
        if c['column_name'] == ctx['pk']:
            continue
        if c['is_required']:
            a('  %s: [{ required: true, message: \'请输入%s\', trigger: \'blur\' }],'
              % (c['column_name'], c['column_comment']))
    a('}')
    a('')
    a('async function getList() {')
    a('  loading.value = true')
    a('  try {')
    a('    const data = await listApi(query)')
    a('    rows.value = data.list')
    a('    total.value = data.total')
    a('  } finally {')
    a('    loading.value = false')
    a('  }')
    a('}')
    a('')
    a('function handleQuery() {')
    a('  query.page = 1')
    a('  getList()')
    a('}')
    a('')
    a('function resetQuery() {')
    a('  Object.keys(query).forEach((key) => {')
    a("    if (!['page', 'page_size'].includes(key)) query[key] = ''")
    a('  })')
    a('  handleQuery()')
    a('}')
    a('')
    a('function onSelectionChange(selection) {')
    a('  selectedIds.value = selection.map((item) => item.%s)' % ctx['pk'])
    a('}')
    a('')
    a('function openCreate() {')
    a('  Object.assign(form, emptyForm)')
    a('  dialogVisible.value = true')
    a('}')
    a('')
    a('function handleEdit(row) {')
    a('  Object.assign(form, emptyForm, row)')
    a('  dialogVisible.value = true')
    a('}')
    a('')
    a('function submitForm() {')
    a('  formRef.value.validate(async (valid) => {')
    a('    if (!valid) return')
    a('    saving.value = true')
    a('    try {')
    a('      // 数值/日期字段空串转 null，避免后端校验失败')
    a('      const payload = { ...form }')
    for c in ctx['form_cols']:
        if c['column_name'] == ctx['pk']:
            continue
        if c['form_type'] in ('number', 'date'):
            a("      if (payload.%s === '') payload.%s = null" % (c['column_name'], c['column_name']))
    a('      if (form.%s) {' % ctx['pk'])
    a('        await updateApi(form.%s, payload)' % ctx['pk'])
    a("        ElMessage.success('修改成功')")
    a('      } else {')
    a('        await createApi(payload)')
    a("        ElMessage.success('新增成功')")
    a('      }')
    a('      dialogVisible.value = false')
    a('      getList()')
    a('    } finally {')
    a('      saving.value = false')
    a('    }')
    a('  })')
    a('}')
    a('')
    a('function handleDelete(row) {')
    a("  ElMessageBox.confirm('确认删除该条记录？', '提示', { type: 'warning' }).then(async () => {")
    a('    await deleteApi([row.%s])' % ctx['pk'])
    a("    ElMessage.success('删除成功')")
    a('    getList()')
    a('  })')
    a('}')
    a('')
    a('function handleBatchDelete() {')
    a("  ElMessageBox.confirm('确认删除选中的 %s 条记录？'.replace('%s', selectedIds.value.length), '提示', { type: 'warning' }).then(async () => {")
    a('    await deleteApi(selectedIds.value)')
    a("    ElMessage.success('删除成功')")
    a('    getList()')
    a('  })')
    a('}')
    if table['export_enable']:
        a('')
        a('async function handleExport() {')
        a('  const blob = await exportApi(query)')
        a('  const url = URL.createObjectURL(blob)')
        a("  const link = document.createElement('a')")
        a("  link.href = url")
        a("  link.download = '%s.xlsx'" % table['module_comment'])
        a('  link.click()')
        a('  URL.revokeObjectURL(url)')
        a('}')
    if table['import_enable']:
        a('')
        a('function onFileChange(file) {')
        a('  importFile.value = file.raw')
        a('}')
        a('')
        a('async function downloadTemplate() {')
        a('  const blob = await templateApi()')
        a('  const url = URL.createObjectURL(blob)')
        a("  const link = document.createElement('a')")
        a("  link.href = url")
        a("  link.download = '%s导入模板.xlsx'" % table['module_comment'])
        a('  link.click()')
        a('  URL.revokeObjectURL(url)')
        a('}')
        a('')
        a('async function submitImport() {')
        a('  if (!importFile.value) {')
        a("    ElMessage.warning('请选择要导入的文件')")
        a('    return')
        a('  }')
        a('  importing.value = true')
        a('  importErrors.value = []')
        a('  try {')
        a('    const result = await importApi(importFile.value)')
        a("    ElMessage.success(`成功导入 ${result.success_count} 条`)")
        a('    if (result.errors && result.errors.length) importErrors.value = result.errors')
        a('    else importVisible.value = false')
        a('    getList()')
        a('  } finally {')
        a('    importing.value = false')
        a('  }')
        a('}')
    a('')
    a('getList()')
    a('</script>')
    a('')
    a('<style scoped>')
    a('.page-title-wrap h2 {')
    a('  margin: 0;')
    a('  font-size: 20px;')
    a('  font-weight: 600;')
    a('  color: #1f2937;')
    a('  letter-spacing: 0.5px;')
    a('}')
    a('.page-title-wrap .sub {')
    a('  margin-top: 6px;')
    a('  font-size: 12px;')
    a('  color: #8a94a6;')
    a('}')
    a('.card-header {')
    a('  display: flex;')
    a('  align-items: center;')
    a('  justify-content: space-between;')
    a('}')
    a('.card-title {')
    a('  font-size: 15px;')
    a('  font-weight: 600;')
    a('  color: #1f2937;')
    a('}')
    a('.card-actions {')
    a('  display: flex;')
    a('  align-items: center;')
    a('  gap: 10px;')
    a('}')
    a('.card-actions .el-button + .el-button {')
    a('  margin-left: 0;')
    a('}')
    a('.dialog-form {')
    a('  padding-top: 4px;')
    a('}')
    a('.mb12 { margin-bottom: 12px }')
    a('.mt12 { margin-top: 12px }')
    a('</style>')
    return '\n'.join(lines)


def build_api_js(table, ctx):
    """生成 axios 请求封装 js。"""
    parts = [f"""import request from '@/utils/request'

// {table['module_comment']} 模块接口（由代码生成器生成）
// request 封装已带 baseURL '/api'，这里只写业务前缀
const BASE = '/{ctx['route']}'

export function listApi(params) {{
  return request({{ url: BASE + '/list', method: 'get', params }}).then((res) => res.data)
}}

export function createApi(data) {{
  return request({{ url: BASE + '/create', method: 'post', data }})
}}

export function updateApi(id, data) {{
  return request({{ url: `${{BASE}}/update/${{id}}`, method: 'put', data }})
}}

export function deleteApi(ids) {{
  return request({{ url: BASE + '/delete', method: 'delete', data: {{ ids }} }})
}}
"""]
    if table['export_enable']:
        parts.append("""
export function exportApi(params) {
  return request({ url: BASE + '/exportData', method: 'get', params, responseType: 'blob' })
}
""")
    if table['import_enable']:
        parts.append("""
export function templateApi() {
  return request({ url: BASE + '/importTemplate', method: 'get', responseType: 'blob' })
}

export function importApi(file) {
  const formData = new FormData()
  formData.append('file', file)
  return request({ url: BASE + '/importData', method: 'post', data: formData,
    headers: { 'Content-Type': 'multipart/form-data' } }).then((res) => res.data)
}
""")
    return ''.join(parts)
