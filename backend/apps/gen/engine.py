# =============================================================================
# 代码生成引擎（backend/apps/gen/engine.py）
# 模块用途：把数据库中的业务表转换成一套可运行的前后端代码，是「代码生成器」
#           的核心；本模块只负责读表元数据、推断默认配置、渲染模板与拼装文件，
#           真正的 ZIP 打包和菜单注册由调用方 apps/gen/views.py 完成。
# 调用方：backend/apps/gen/views.py
#   - list_tables / import_tables  ：调用 list_db_tables、import_table 读表并落默认配置
#   - preview                      ：调用 render_files 在线预览，不落盘
#   - ddl                          ：调用 get_table_ddl 返回 SHOW CREATE TABLE
#   - download                     ：调用 render_files 后自行打包 ZIP，并按需注册菜单
# 生成流程：
#   1. list_db_tables 从 information_schema 读取业务表清单（排除 sys_/django_/auth_）；
#   2. import_table 读取表注释与列元数据，按列名/类型/注释推断表单控件、查询方式，
#      写入 sys_gen_table 与 sys_gen_table_column 两张配置表；
#   3. render_files 把配置整理成模板上下文，交给 templates/gen 下的模板渲染；
#   4. build_filters_code / vue_component / build_vue_page / build_api_js 负责
#      视图过滤代码、Vue 表单控件、Vue 页面与 axios 封装的动态拼接。
# 生成产物（render_files 固定返回 9 项，对应生成后的目录结构）：
#   1) backend/apps/<module>/__init__.py   包初始化（空文件）
#   2) backend/apps/<module>/apps.py       应用配置
#   3) backend/apps/<module>/models.py     模型（字段由 django_field_def 生成）
#   4) backend/apps/<module>/serializers.py 序列化器（读写/列表）
#   5) backend/apps/<module>/views.py      视图（列表过滤由 build_filters_code 生成）
#   6) backend/apps/<module>/urls.py       路由
#   7) README-部署说明.txt                 部署与接入说明
#   8) frontend/src/api/<module>.js        axios 请求封装（build_api_js）
#   9) frontend/src/views/<gen_path>.vue   列表页 SFC（build_vue_page）
# 注意：本文件大量使用多行字符串作为「生成代码的模板」，其中的缩进、占位符、
#       花括号都是生成产物的一部分，修改时只能在其外部增删注释，不能改动内容。
# =============================================================================
"""代码生成引擎：读取数据表、默认配置推断、模板渲染、ZIP 打包、菜单注册。"""
import io  # 内存流模块，便于在内存中拼装二进制内容
import os  # 路径拼接，定位模板目录
import re  # 正则匹配，识别列名语义与解析字段长度
import zipfile  # ZIP 打包，批量下载生成代码
from datetime import datetime  # 识别并格式化数据库查询返回的时间对象

from django.db import connection  # 原生游标，读取 information_schema 元数据
from django.template import Context, Engine  # 独立模板引擎，与项目模板配置隔离

from apps.gen.models import SysGenTable, SysGenTableColumn  # 生成配置主表与字段配置表模型

TPL_DIR = os.path.join(os.path.dirname(__file__), 'templates', 'gen')  # 模板目录：本包下的 templates/gen

FORM_TYPE_RULES = [  # 列名/注释语义到表单控件的匹配规则，自上而下命中即止
    ('image', re.compile(r'(_img|_image|_pic|_avatar)$|图片|头像')),  # 图片类列名或中文注释
    ('file', re.compile(r'(_file|_url|_attachment)$|附件|文件地址')),  # 附件或文件地址类列
    ('date', None),  # 由类型判断，占位以保证优先级顺序
    ('textarea', re.compile(r'text|json')),  # 长文本或 JSON 内容改用多行文本
]
# 公共审计列不参与表单、查询、导入与导出
COMMON_SKIP = {'create_by', 'create_time', 'update_by', 'update_time', 'is_deleted', 'remark'}

_engine = None  # 模板引擎单例缓存，避免重复创建开销


def tpl_engine():
    """返回模块级模板引擎单例，首次调用时按模板目录初始化。"""
    global _engine  # 声明修改模块级变量
    if _engine is None:  # 仅在尚未初始化时创建
        _engine = Engine(dirs=[TPL_DIR], autoescape=False)  # 关闭自动转义，保证生成代码原样输出
    return _engine  # 返回单例供后续渲染复用


def render_tpl(name, context):
    """渲染指定模板文件并返回生成的文本内容。"""
    return tpl_engine().get_template(name).render(Context(context, autoescape=False))  # 手工构造 Context 并关闭转义


def snake_to_pascal(name):
    """下划线命名转大驼峰，如 biz_student 转为 BizStudent。"""
    return ''.join(part.capitalize() for part in name.split('_'))  # 逐段首字母大写后拼接


# ---------------------------------------------------------------- 数据库读取

TABLE_NAME_RE = re.compile(r'^[A-Za-z0-9_]+$')  # 表名白名单校验，防止拼接 SQL 时被注入


def list_db_tables(keyword=None):
    """读取当前库中的业务表（排除 sys_ 前缀与 Django 内置表）。"""
    with connection.cursor() as cursor:  # 借用项目数据库连接执行只读查询
        cursor.execute(  # 一次性取回库内所有基表的名称、注释、行数与创建时间
            "SELECT table_name, table_comment, table_rows, create_time "
            "FROM information_schema.tables "
            "WHERE table_schema = DATABASE() AND table_type = 'BASE TABLE' "
            "ORDER BY table_name")
        tables = cursor.fetchall()  # 结果按表名升序，便于前端稳定展示
    # 已导入表名集合：前端据此把对应行标为「已导入」，避免重复导入
    imported = set(SysGenTable.objects.filter(is_deleted=0)
                   .values_list('table_name', flat=True))  # 已导入表名集合，用于标记禁用
    result = []  # 组装返回列表
    for name, comment, rows, create_time in tables:  # 逐表过滤并整理字段
        if name.startswith(('sys_', 'django_', 'auth_')):  # 系统表与框架内置表不参与生成
            continue
        if keyword and keyword.lower() not in name.lower():  # 有关键字时做不区分大小写的包含匹配
            continue
        # 组装单张表的展示信息，键名与前端表格列一一对应
        result.append({
            'table_name': name,  # 表名
            'table_comment': comment or '',  # 表注释，空值统一成空串
            'table_rows': rows or 0,  # 估算行数，可能为空值
            # 驱动返回时间对象时格式化，其他类型原样透出
            'create_time': create_time.strftime('%Y-%m-%d %H:%M:%S') if isinstance(create_time, datetime) else create_time,
            'imported': name in imported,  # 是否已导入过，前端据此禁用重复导入
        })
    return result  # 返回可导入表清单


def get_table_ddl(table_name):
    """返回指定表的建表语句，表名非法时抛出 ValueError。"""
    if not TABLE_NAME_RE.match(table_name or ''):  # 先做白名单校验，避免拼接触发注入
        # 表名只允许字母、数字与下划线，非法时直接抛业务异常
        raise ValueError('非法表名')
    with connection.cursor() as cursor:  # 复用项目数据库连接
        cursor.execute(f'SHOW CREATE TABLE `{table_name}`')  # 查建表语句，表名已过白名单
        return cursor.fetchone()[1]  # 第二列即 CREATE TABLE 文本


def get_db_columns(table_name):
    """读取指定表的列名、类型、注释、可空性、索引标记与自增信息。"""
    with connection.cursor() as cursor:  # 复用项目数据库连接
        cursor.execute(  # 按列原始顺序返回，保证生成配置与建表顺序一致
            "SELECT column_name, column_type, column_comment, is_nullable, column_key, extra "
            "FROM information_schema.columns "
            "WHERE table_schema = DATABASE() AND table_name = %s ORDER BY ordinal_position",
            [table_name])  # 参数化传表名
        return cursor.fetchall()  # 返回全部列的元数据


# ---------------------------------------------------------------- 导入与默认配置

def guess_form_type(column_name, base_type, comment):
    """按列名、注释与基础类型推断前端表单控件类型。"""
    for form_type, pattern in FORM_TYPE_RULES:  # 按优先级匹配语义规则
        if form_type == 'date':  # 日期规则不靠正则，交由下面的类型判断处理
            # date 规则没有正则，跳过本轮循环避免 pattern 为 None 时报错
            continue
        if pattern and (pattern.search(column_name) or pattern.search(comment or '')):  # 列名或注释命中即采用
            return form_type  # 命中第一条规则立即返回
    if base_type in ('datetime', 'timestamp', 'date'):  # 时间类型统一用日期选择器
        # 数据库时间类型交给日期控件，避免退化成自由文本输入
        return 'date'
    if base_type in ('text', 'mediumtext', 'longtext'):  # 大文本用多行输入
        # 大文本内容通常较长，使用多行文本框更利于编辑
        return 'textarea'
    if base_type in ('int', 'bigint', 'tinyint', 'smallint', 'decimal', 'numeric',
                     'float', 'double'):  # 数值类型用数字框
        # 数值类型使用数字输入框，前端可限制最小值与格式
        return 'number'
    return 'input'  # 其余默认单行输入框


def guess_query_type(base_type):
    """按基础类型推断默认查询方式：文本用模糊，其余用等值。"""
    if base_type in ('varchar', 'char', 'text'):  # 字符类字段适合模糊匹配
        # 字符字段用右模糊/包含匹配比等值匹配更实用
        return 'like'
    return 'eq'  # 数值、日期等默认等值匹配


def import_table(table_name, username=''):
    """导入一张数据表：写入生成配置主表与默认字段配置。"""
    if not TABLE_NAME_RE.match(table_name or ''):  # 先做表名白名单校验
        # 非法表名不进入后续 SQL 拼接与元数据查询
        raise ValueError(f'非法表名：{table_name}')
    if table_name.startswith('sys_'):  # 系统配置表不允许再次生成
        # 生成器自身依赖 sys_ 配置表，禁止把系统表再次纳入生成流程
        raise ValueError(f'系统表 {table_name} 不允许导入')
    if SysGenTable.objects.filter(table_name=table_name, is_deleted=0).exists():  # 防止重复导入
        # 同一张表只保留一条未删除的生成配置，保证下载结果唯一
        raise ValueError(f'表 {table_name} 已导入过')

    # 表注释
    with connection.cursor() as cursor:  # 读取表注释，用于默认模块中文名
        # 表注释可能为空，后面会用表名兜底
        cursor.execute(
            "SELECT table_comment FROM information_schema.tables "
            "WHERE table_schema = DATABASE() AND table_name = %s", [table_name])
        row = cursor.fetchone()  # 表不存在时返回空
    table_comment = (row[0] if row else '') or table_name  # 无注释时退回表名，保证页面标题非空

    segments = table_name.strip('_').split('_')  # 按业务前缀拆分表名，如 biz_student
    module_name = segments[-1] if len(segments) > 1 else table_name  # 取最后一段作模块名，单段表名直接用表名
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # 统一写入时间
    gen_table = SysGenTable.objects.create(  # 写入生成任务主表
        table_name=table_name,  # 源表名
        table_comment=table_comment,  # 表中文名
        class_name=snake_to_pascal(table_name),  # 生成模型类名
        module_name=module_name,  # 模块英文标识
        module_comment=table_comment,  # 模块中文名
        url_prefix=f'/api/{module_name}',  # 默认接口前缀
        gen_path=f'{module_name}/index',  # 默认前端页面路径
        parent_menu_id=None,  # 默认不挂菜单，下载时再指定
        is_delete_logic=True,  # 默认按逻辑删除生成查询过滤
        import_enable=True,  # 默认开启导入
        export_enable=True,  # 默认开启导出
        create_by=username, create_time=now, update_by=username, update_time=now,  # 审计字段
    )

    # 遍历源表全部列，逐列生成默认字段配置
    for i, (col_name, col_type, col_comment, nullable, col_key, extra) in \
            enumerate(get_db_columns(table_name)):
        base_type = col_type.lower().split('(')[0]  # 去掉长度精度，只留基础类型
        is_pk = 1 if col_key == 'PRI' else 0  # 主键列标记
        skip_common = col_name in COMMON_SKIP  # 是否属于公共审计列
        has_default = bool(get_column_default(table_name, col_name))  # 是否有默认值，影响必填推断
        SysGenTableColumn.objects.create(  # 写入单列配置
            gen_table_id=gen_table.id,  # 所属生成任务
            column_name=col_name,  # 列名
            column_comment=col_comment or col_name,  # 无注释时列名兜底作标签
            column_type=col_type,  # 原始列类型
            is_pk=is_pk,  # 是否主键
            dict_type='',  # 字典编码默认空，需人工选择
            # 主键不在表单出现，其余列按语义自动推断控件类型
            form_type='input' if is_pk else guess_form_type(col_name, base_type, col_comment),
            is_list=0 if (is_pk or skip_common) else 1,  # 主键与公共列不进列表
            is_query=0 if (is_pk or skip_common) else 1,  # 主键与公共列不作查询条件
            query_type=guess_query_type(base_type),  # 默认查询方式
            # 主键/公共列/有默认值/自增/可空 字段均不作为必填表单项
            is_required=0 if (is_pk or skip_common or has_default
                              or nullable == 'YES' or 'auto_increment' in (extra or '')) else 1,
            is_export=0 if (is_pk or skip_common) else 1,  # 主键与公共列不导出
            is_import=0 if (is_pk or skip_common) else 1,  # 主键与公共列不导入
            sort=i,  # 按建表列顺序排序
            create_by=username, create_time=now,  # 审计字段
        )
    return gen_table  # 返回主表实例，供调用方读取 id


def get_column_default(table_name, column_name):
    """读取单列的默认值，用于判断该列是否可不必填。"""
    with connection.cursor() as cursor:  # 复用项目数据库连接
        cursor.execute(
            "SELECT column_default FROM information_schema.columns "
            "WHERE table_schema = DATABASE() AND table_name = %s AND column_name = %s",
            [table_name, column_name])  # 参数化传入表名与列名
        return cursor.fetchone()[0]  # 无默认值时返回 None


# ---------------------------------------------------------------- 字段映射

def parse_type_limits(raw_type):
    """解析类型中的长度与精度，如 varchar(50)、decimal(18,2)。"""
    m = re.search(r'\((\d+)(?:,(\d+))?\)', raw_type or '')  # 兼容无括号的类型串
    if not m:  # 没有长度信息
        return None, None  # 返回空值，由调用方兜底
    return int(m.group(1)), (int(m.group(2)) if m.group(2) else None)  # 返回长度与可选的精度


def django_field_def(col):
    """列配置 → Django 模型字段定义字符串。"""
    raw = (col.column_type or '').lower()  # 统一小写，便于比较类型
    base = raw.split('(')[0].strip()  # 提取基础类型
    comment = (col.column_comment or col.column_name).replace("'", "\\'")  # 转义单引号，避免破坏生成的字符串
    null_part = 'null=True, blank=True' if not col.is_required else ''  # 非必填列允许为空

    if base in ('varchar', 'char'):  # 变长/定长字符
        length, _ = parse_type_limits(raw)  # 取长度
        args = f"verbose_name='{comment}', max_length={length or 255}"  # 缺省长度按 255
    elif base in ('text', 'mediumtext', 'longtext'):  # 大文本
        args = f"verbose_name='{comment}'"
    elif base in ('bigint',):  # 长整型
        args = f"verbose_name='{comment}'"
    elif base in ('int', 'integer'):  # 整型
        args = f"verbose_name='{comment}'"
    elif base in ('tinyint', 'smallint'):  # 小整型
        args = f"verbose_name='{comment}'"
    elif base in ('decimal', 'numeric'):  # 定点小数
        _, places = parse_type_limits(raw)  # 取小数位
        args = f"verbose_name='{comment}', max_digits=18, decimal_places={places or 2}"  # 总位数固定 18
    elif base in ('float', 'double'):  # 浮点
        args = f"verbose_name='{comment}'"
    elif base in ('datetime', 'timestamp'):  # 日期时间
        args = f"verbose_name='{comment}'"
    elif base == 'date':  # 纯日期
        args = f"verbose_name='{comment}'"
    elif base == 'time':  # 纯时间
        args = f"verbose_name='{comment}'"
    else:  # 未识别类型按字符串兜底
        args = f"verbose_name='{comment}', max_length=255"

    if (col.column_name or '') == 'is_deleted':  # 逻辑删除列需带默认值
        # 逻辑删除列在库中为 NOT NULL DEFAULT 0，生成 default 而非 null
        null_part = ''  # 该列不允许为空
        args += ', default=0'  # 补默认值 0
    if null_part:  # 非必填列追加可空参数
        args += ', ' + null_part
    field_map = {  # 数据库基础类型到 Django 字段类的映射表
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
    field_cls = field_map.get(base, 'models.CharField')  # 未匹配类型回退为字符字段
    return f"{field_cls}({args})"  # 拼成完整的字段声明


# ---------------------------------------------------------------- 代码渲染

def render_files(table, columns):
    """渲染全部生成文件，返回 [(相对路径, 内容), ...]。"""
    table_dict = {  # 模板上下文：主表信息转普通字典
        'table_name': table.table_name,  # 源表名
        'class_name': table.class_name,  # 模型类名
        'module_name': table.module_name,  # 模块英文标识
        'module_comment': table.module_comment,  # 模块中文名
        'url_prefix': table.url_prefix,  # 接口路由前缀
        'gen_path': table.gen_path,  # 前端页面路径
        'is_delete_logic': bool(table.is_delete_logic),  # 是否逻辑删除
        'import_enable': bool(table.import_enable),  # 是否生成导入功能
        'export_enable': bool(table.export_enable),  # 是否生成导出功能
    }
    cols = []  # 模板上下文：整理后的列信息
    for c in columns:  # 逐列归一化，便于模板直接取值
        base_type = (c.column_type or '').lower().split('(')[0].strip()  # 基础类型
        cols.append({
            'column_name': c.column_name,  # 列名
            'column_comment': c.column_comment or c.column_name,  # 列中文名，空值用列名兜底
            'column_type': c.column_type,  # 原始类型
            'is_pk': bool(c.is_pk),  # 是否主键
            'form_type': c.form_type or 'input',  # 表单控件，空值默认输入框
            'dict_type': c.dict_type or '',  # 字典编码
            'is_list': bool(c.is_list),  # 是否列表展示
            'is_query': bool(c.is_query),  # 是否查询条件
            'query_type': c.query_type or 'eq',  # 查询方式，默认等值
            'is_required': bool(c.is_required),  # 是否必填
            'is_export': bool(c.is_export),  # 是否导出
            'is_import': bool(c.is_import),  # 是否导入
            # 是否字符类，模板据此选择过滤器写法
            'is_char': base_type in ('varchar', 'char', 'text', 'mediumtext', 'longtext'),
            'sort': c.sort,  # 排序号
            'field_def': django_field_def(c),  # 预生成 Django 字段声明
        })

    pk_col = next((c for c in cols if c['is_pk']), {'column_name': 'id'})  # 主键列，缺失时按 id 兜底
    business_cols = [c for c in cols if not c['is_pk']]  # 业务列，排除主键
    # 表单列：排除公共审计列
    form_cols = [c for c in business_cols if c['form_type'] and c['column_name'] not in COMMON_SKIP]
    list_cols = [c for c in business_cols if c['is_list']]  # 列表展示列
    query_cols = [c for c in business_cols if c['is_query']]  # 查询条件列
    export_cols = [c for c in business_cols if c['is_export']]  # 导出列
    # 导入列：排除公共审计列
    import_cols = [c for c in business_cols if c['is_import'] and c['column_name'] not in COMMON_SKIP]

    context = {  # 汇总模板上下文
        'table': table_dict,  # 主表信息
        'columns': cols,  # 全部列信息
        'form_cols': form_cols,  # 表单列
        'list_cols': list_cols,  # 列表列
        'query_cols': query_cols,  # 查询列
        'export_cols': export_cols,  # 导出列
        'import_cols': import_cols,  # 导入列
        'pk': pk_col['column_name'],  # 主键字段名
        'route': (table_dict['url_prefix'] or '').replace('/api/', '').strip('/'),  # 前端接口前缀，去掉 /api 与服务端斜杠
        'has_create_time': any(c['column_name'] == 'create_time' for c in cols),  # 是否存在创建时间列，决定列表是否展示时间
        'buttons': [  # 默认按钮权限，供生成的前端与菜单使用
            ('查询', f"{table.module_name}:list"),
            ('新增', f"{table.module_name}:create"),
            ('编辑', f"{table.module_name}:update"),
            ('删除', f"{table.module_name}:delete"),
        ] + ([('导入', f'{table.module_name}:import')] if table.import_enable else [])
        + ([('导出', f'{table.module_name}:export')] if table.export_enable else []),
        'filters_code': build_filters_code(query_cols, table_dict['is_delete_logic']),  # 预生成列表过滤代码片段
    }

    files = [  # 待打包的文件清单：后端模块 + 说明 + 前端 api 与页面
        (f'backend/apps/{table.module_name}/__init__.py', ''),  # 包初始化文件，内容留空
        (f'backend/apps/{table.module_name}/apps.py', render_tpl('apps.py.tpl', context)),  # 应用配置
        (f'backend/apps/{table.module_name}/models.py', render_tpl('models.py.tpl', context)),  # 模型
        # 序列化器：按配置生成读写与列表序列化器
        (f'backend/apps/{table.module_name}/serializers.py', render_tpl('serializers.py.tpl', context)),
        (f'backend/apps/{table.module_name}/views.py', render_tpl('views.py.tpl', context)),  # 视图
        (f'backend/apps/{table.module_name}/urls.py', render_tpl('urls.py.tpl', context)),  # 路由
        ('README-部署说明.txt', render_tpl('readme.txt.tpl', context)),  # 部署说明
        ('frontend/src/api/' + table.module_name + '.js', build_api_js(table_dict, context)),  # 前端请求封装
        ('frontend/src/views/' + table.gen_path + '.vue', build_vue_page(table_dict, context)),  # 前端列表页
    ]
    return files  # 返回相对路径与内容列表


def build_filters_code(query_cols, logic_delete):
    """生成 views.py 中的过滤代码（含缩进 8 空格）。"""
    lines = []  # 收集生成的代码行
    if logic_delete:  # 逻辑删除模式先追加未删除过滤
        lines.append('        queryset = queryset.filter(is_deleted=0)')
    for c in query_cols:  # 按每个查询列生成一段过滤逻辑
        name, qtype = c['column_name'], c['query_type']  # 列名与查询方式
        if qtype == 'like':  # 模糊查询：取参数值后按 icontains 过滤
            lines.append(
                f"        value = request.query_params.get('{name}')\n"
                f"        if value:\n"
                f"            queryset = queryset.filter({name}__icontains=value)")
        elif qtype == 'between':  # 区间查询：起止两个参数分别做 gte/lte
            lines.append(
                f"        start = request.query_params.get('{name}_start')\n"
                f"        end = request.query_params.get('{name}_end')\n"
                f"        if start:\n"
                f"            queryset = queryset.filter({name}__gte=start)\n"
                f"        if end:\n"
                f"            queryset = queryset.filter({name}__lte=end)")
        elif qtype == 'gt':  # 大于查询
            lines.append(
                f"        value = request.query_params.get('{name}')\n"
                f"        if value:\n"
                f"            queryset = queryset.filter({name}__gt=value)")
        elif qtype == 'lt':  # 小于查询
            lines.append(
                f"        value = request.query_params.get('{name}')\n"
                f"        if value:\n"
                f"            queryset = queryset.filter({name}__lt=value)")
        else:  # eq 等值查询
            lines.append(
                f"        value = request.query_params.get('{name}')\n"
                f"        if value not in (None, ''):\n"
                f"            queryset = queryset.filter({name}=value)")
    if not lines:  # 没有生成任何过滤时补 pass，保证函数体合法
        lines.append('        pass  # 未配置查询条件')
    return '\n'.join(lines)  # 拼接为多行代码字符串


# ---------------------------------------------------------------- Vue / JS 生成

def vue_component(col):
    """根据 form_type 生成 el-form-item 内部控件代码。"""
    name, label = col['column_name'], col['column_comment']  # 绑定字段名与中文标签
    ph = f"placeholder=\"请输入{label}\""  # 统一的输入框占位提示
    if col['form_type'] == 'number':  # 数字控件不允许负数且占满整行
        return f'<el-input-number v-model="form.{name}" :min="0" style="width: 100%" />'
    # 日期控件统一按 YYYY-MM-DD HH:mm:ss 回传，避免时区/格式差异
    if col['form_type'] == 'date':
        return f'<el-date-picker v-model="form.{name}" type="datetime" {ph} value-format="YYYY-MM-DD HH:mm:ss" style="width: 100%" />'
    if col['form_type'] == 'select' and col['dict_type']:  # 有字典编码才生成下拉
        return (f'<el-select v-model="form.{name}" {ph} clearable style="width: 100%">\n'
                f'            <el-option v-for="d in dictList(\'{col["dict_type"]}\')" :key="d.dict_value" '
                f':label="d.dict_label" :value="d.dict_value" />\n'
                f'          </el-select>')
    if col['form_type'] == 'radio' and col['dict_type']:  # 有字典编码才生成单选框组
        return (f'<el-radio-group v-model="form.{name}">\n'
                f'            <el-radio v-for="d in dictList(\'{col["dict_type"]}\')" :key="d.dict_value" '
                f':value="d.dict_value">' + '{{ d.dict_label }}</el-radio>\n'
                f'          </el-radio-group>')
    if col['form_type'] == 'textarea':  # 多行文本，默认三行
        return f'<el-input v-model="form.{name}" type="textarea" :rows="3" {ph} />'
    if col['form_type'] == 'image':  # 图片暂以地址字符串输入，简化依赖
        return f'<el-input v-model="form.{name}" {ph} />'
    if col['form_type'] == 'file':  # 附件同样以地址字符串输入
        return f'<el-input v-model="form.{name}" {ph} />'
    return f'<el-input v-model="form.{name}" {ph} />'  # 其他类型统一单行输入


def build_vue_page(table, ctx):
    """生成 Vue 列表页 SFC。"""
    m = table['module_name']  # 模块名，用于权限编码与 api 导入
    cn = table['class_name']  # 类名，当前模板未使用但保留扩展位
    lines = []  # 逐行拼装 SFC 源码
    a = lines.append  # 简写，减少重复书写

    # ---- template：查询区 ----
    # 模板根标签，SFC 从这里开始
    a('<template>')  # 模板根标签
    # 页面容器，沿用后台统一的左右留白样式
    a('  <div class="app-container">')  # 页面容器
    # 页头区域，放页面标题
    a('    <div class="page-header">')  # 页头区域
    # 标题包裹层，控制标题与副标题间距
    a('      <div class="page-title-wrap">')  # 标题包裹层
    a('        <h2>%s</h2>' % table['module_comment'])  # 用模块中文名作页面标题
    # 副标题展示总记录数，total 来自列表接口
    a('        <div class="sub">数据维护 · 共 {{ total }} 条记录</div>')  # 副标题展示总记录数
    # 结束标题包裹层
    a('      </div>')
    # 结束页头
    a('    </div>')
    # 查询卡片注释，保留在生成产物中便于阅读
    a('    <!-- 查询区域 -->')  # 查询卡片注释
    # 查询卡片，去掉阴影以贴合后台简洁风格
    a('    <el-card shadow="never" class="search-card">')  # 查询卡片
    # 仅当存在查询条件时渲染查询表单，避免生成空表单
    if ctx['query_cols']:  # 仅当存在查询条件时渲染查询表单
        # 行内表单，阻止默认提交行为
        a('      <el-form :model="query" inline @submit.prevent>')  # 行内表单，阻止默认提交
        # 逐列生成查询项，顺序与字段配置一致
        for c in ctx['query_cols']:  # 逐列生成查询项
            if c['query_type'] == 'between':  # 区间查询渲染两个日期选择器
                # 查询项容器，标签取列中文名
                a(f'        <el-form-item label="{c["column_comment"]}">')
                # 区间查询的起始日期
                # 起始值绑定到 _start 字段，仅取日期
                a(f'          <el-date-picker v-model="query.{c["column_name"]}_start" type="date" value-format="YYYY-MM-DD" placeholder="开始日期" style="width: 160px" />')
                a(f'          <span> - </span>')  # 起止之间的分隔符
                # 区间查询的结束日期
                # 结束值绑定到 _end 字段
                a(f'          <el-date-picker v-model="query.{c["column_name"]}_end" type="date" value-format="YYYY-MM-DD" placeholder="结束日期" style="width: 160px" />')
                # 结束区间查询项
                a('        </el-form-item>')
            # 下拉字典查询项，无字典编码时退回文本输入
            elif c['form_type'] == 'select' and c['dict_type']:  # 下拉字典查询项
                # 查询项容器
                a(f'        <el-form-item label="{c["column_comment"]}">')
                # 可清空的下拉，选项来自字典
                # clearable 支持一键清空条件
                a(f'          <el-select v-model="query.{c["column_name"]}" placeholder="请选择" clearable style="width: 180px">')
                # 按字典编码渲染下拉选项
                # 以 dict_value 提交、dict_label 展示
                a(f'            <el-option v-for="d in dictList(\'{c["dict_type"]}\')" :key="d.dict_value" :label="d.dict_label" :value="d.dict_value" />')
                # 结束下拉
                a('          </el-select>')
                # 结束查询项
                a('        </el-form-item>')
            else:  # 其余按文本输入处理
                # 查询项容器
                a(f'        <el-form-item label="{c["column_comment"]}">')
                # 文本查询项，回车即可触发查询
                # 回车直接查询，省去点按钮
                a(f'          <el-input v-model="query.{c["column_name"]}" placeholder="请输入{c["column_comment"]}" clearable style="width: 180px" @keyup.enter="handleQuery" />')
                # 结束查询项
                a('        </el-form-item>')
        # 查询与重置按钮独占一个表单项
        a('        <el-form-item class="search-actions">')  # 查询与重置按钮
        # 查询按钮，重置页码后拉取
        a('          <el-button type="primary" :icon="Search" @click="handleQuery">查询</el-button>')
        # 重置按钮，清空全部查询条件
        a('          <el-button :icon="Refresh" @click="resetQuery">重置</el-button>')
        # 结束按钮项
        a('        </el-form-item>')
        # 结束行内表单
        a('      </el-form>')
    # 结束查询卡片
    a('    </el-card>')
    # 查询区与表格之间的空行
    a('')
    # ---- 表格 ----
    # 表格区域注释
    a('    <!-- 数据表格 -->')
    a('    <el-card shadow="never" class="table-card">')  # 表格卡片
    # 卡片头部插槽，右侧放操作按钮
    a('      <template #header>')  # 卡片头部插槽
    # 标题与按钮两端对齐的容器
    a('        <div class="card-header">')
    # 列表标题，展示模块中文名
    a('          <span class="card-title">%s列表</span>' % table['module_comment'])  # 列表标题
    a('          <div class="card-actions">')  # 操作按钮组
    # 新增按钮带权限指令，无权限时自动隐藏
    # 权限编码与菜单注册保持一致
    a('            <el-button v-perm="\'%s:create\'" type="primary" :icon="Plus" @click="openCreate">新增</el-button>' % m)
    # 开启导入才渲染导入按钮，避免生成无用入口
    if table['import_enable']:  # 开启导入才渲染导入按钮
        # 点击打开导入弹窗
        a('            <el-button v-perm="\'%s:import\'" type="success" plain :icon="Upload" @click="importVisible = true">导入</el-button>' % m)
    if table['export_enable']:  # 开启导出才渲染导出按钮
        # 按当前查询条件导出
        a('            <el-button v-perm="\'%s:export\'" type="warning" plain :icon="Download" @click="handleExport">导出</el-button>' % m)
    # 未勾选任何行时批量删除按钮置灰
    # 复用删除权限编码
    a('            <el-button v-perm="\'%s:delete\'" type="danger" plain :icon="Delete" :disabled="!selectedIds.length" @click="handleBatchDelete">批量删除</el-button>' % m)
    # 结束按钮组
    a('          </div>')
    # 结束卡片头部
    a('        </div>')
    # 结束头部插槽
    a('      </template>')
    # 斑马纹表格，勾选变化同步到 selectedIds
    # 加载态、空数据文案与多选回调
    a('      <el-table v-loading="loading" :data="rows" stripe empty-text="暂无数据" @selection-change="onSelectionChange">')
    a('        <el-table-column type="index" label="序号" width="70" align="center" />')  # 首列序号，升序展示
    # 多选列，供批量删除使用
    a('        <el-table-column type="selection" width="50" align="center" />')  # 多选列
    # 逐列渲染表格列，仅 is_list 为真的字段
    for c in ctx['list_cols']:  # 逐列渲染表格列
        if c['form_type'] == 'select' and c['dict_type']:  # 字典字段用标签展示中文
            # 自定义插槽列，便于按字典翻译
            a(f'        <el-table-column label="{c["column_comment"]}" prop="{c["column_name"]}" align="center">')
            # 取得当前行数据
            a(f'          <template #default="scope">')
            # 字典字段用标签展示中文含义
            # 通过 dictLabel 把字典值转中文
            a(f'            <el-tag :type="scope.row.{c["column_name"]} === \'0\' ? \'primary\' : \'info\'">' + '{{ dictLabel(\'' + c['dict_type'] + '\', scope.row.' + c['column_name'] + ') }}</el-tag>')
            # 结束行插槽
            a('          </template>')
            # 结束字典列
            a('        </el-table-column>')
        else:  # 普通列直接展示，超出省略并悬浮提示
            # 超长内容省略并悬浮显示全文
            a(f'        <el-table-column label="{c["column_comment"]}" prop="{c["column_name"]}" align="center" show-overflow-tooltip />')
    # 操作列固定在右侧，含行内编辑与行内删除
    # fixed 保证横向滚动时操作列可见
    a('        <el-table-column label="操作" width="150" align="center" fixed="right">')
    # 行内按钮通过 scope.row 取得当前记录
    a('          <template #default="scope">')
    # 行内编辑按钮
    # link 样式让按钮更紧凑
    a('            <el-button v-perm="\'%s:update\'" link type="primary" :icon="Edit" @click="handleEdit(scope.row)">编辑</el-button>' % m)
    # 行内删除按钮
    # 单条删除走二次确认
    a('            <el-button v-perm="\'%s:delete\'" link type="danger" :icon="Delete" @click="handleDelete(scope.row)">删除</el-button>' % m)
    # 结束操作列插槽
    a('          </template>')
    # 结束操作列
    a('        </el-table-column>')
    # 结束表格
    a('      </el-table>')
    # 分页容器，右对齐展示
    a('      <div class="pagination-wrap">')  # 分页容器
    # 分页组件，含总数与跳页
    a('        <el-pagination background layout="total, sizes, prev, pager, next, jumper"')
    # 页码与页长双向绑定到查询对象
    a('          :total="total" v-model:current-page="query.page" v-model:page-size="query.page_size"')
    a('          :page-sizes="[10, 20, 50, 100]" @change="getList" />')  # 页码或页长变化即重新查询
    # 结束分页容器
    a('      </div>')
    # 结束表格卡片
    a('    </el-card>')

    # ---- 新增/编辑弹窗 ----
    # 弹窗区域注释
    a('    <!-- 新增/编辑弹窗 -->')
    # 有主键即编辑态，标题随之切换
    # 主键有值即编辑，关闭时销毁表单状态
    a('    <el-dialog :title="form.%s ? \'编辑%s\' : \'新增%s\'" v-model="dialogVisible" width="640px" :close-on-click-modal="false" destroy-on-close>' % (ctx['pk'], table['module_comment'], table['module_comment']))
    # 弹窗表单：绑定校验规则与统一标签宽度
    # 统一标签宽度，保持多字段对齐
    a('      <el-form ref="formRef" :model="form" :rules="rules" label-width="110px" class="dialog-form">')
    # 逐列渲染表单项，顺序与配置一致
    for c in ctx['form_cols']:  # 逐列渲染表单项
        # 主键不进入表单，避免用户修改主键
        if c['column_name'] == ctx['pk']:  # 主键不进入表单
            # 跳过主键，继续下一列
            continue
        # prop 与校验规则字段名对应
        a(f'        <el-form-item label="{c["column_comment"]}" prop="{c["column_name"]}">')
        a('          ' + vue_component(c))  # 按控件类型生成内部组件
        # 结束表单项
        a('        </el-form-item>')
    # 结束弹窗表单
    a('      </el-form>')
    # 弹窗底部按钮插槽
    a('      <template #footer>')  # 弹窗底部按钮
    # 取消只关闭弹窗，不提交
    a('        <el-button @click="dialogVisible = false">取消</el-button>')
    # 确定按钮提交时展示 loading，避免重复提交
    # loading 由 saving 控制
    a('        <el-button type="primary" :loading="saving" @click="submitForm">确定</el-button>')
    # 结束底部插槽
    a('      </template>')
    # 结束新增/编辑弹窗
    a('    </el-dialog>')

    # ---- 导入弹窗 ----
    if table['import_enable']:  # 开启导入才生成导入弹窗
        # 导入区域注释
        a('    <!-- 导入弹窗 -->')
        # 标题带模块中文名
        a('    <el-dialog title="导入%s" v-model="importVisible" width="420px">' % table['module_comment'])
        # 拖拽上传，仅选择文件，由“开始导入”按钮手动触发
        # 关闭自动上传，一次仅一个 Excel
        a('      <el-upload drag :auto-upload="false" :limit="1" accept=".xlsx,.xls" :on-change="onFileChange" :file-list="fileList">')
        # 拖拽区图标
        a('        <el-icon size="40"><UploadFilled /></el-icon>')
        # 上传提示文案
        a('        <div>将 Excel 文件拖到此处，或点击选择</div>')
        # 结束上传组件
        a('      </el-upload>')
        # 模板下载入口，与上传区留出间距
        a('      <div class="mt12">')  # 模板下载入口
        # 模板由后端按字段配置生成
        a('        <el-button link type="primary" @click="downloadTemplate">下载导入模板</el-button>')
        # 结束模板下载区
        a('      </div>')
        # 仅在有错误明细时展示提示框
        # 导入失败明细以只读提示框展示
        a('      <el-alert v-if="importErrors.length" type="error" :closable="false" class="mt12">')
        a('        <div v-for="e in importErrors" :key="e"> ' + '{{ e }}</div>')  # 逐条列出校验错误
        # 结束错误提示
        a('      </el-alert>')
        # 导入弹窗底部按钮
        a('      <template #footer>')
        # 关闭导入弹窗
        a('        <el-button @click="importVisible = false">取消</el-button>')
        # importing 防止重复提交
        a('        <el-button type="primary" :loading="importing" @click="submitImport">开始导入</el-button>')
        # 结束底部插槽
        a('      </template>')
        # 结束导入弹窗
        a('    </el-dialog>')

    # 结束页面容器
    a('  </div>')
    # 结束模板段
    a('</template>')

    # ---- script ----
    # script 段前的空行，保证生成代码可读
    a('')
    # 组合式 API 写法，无需 export default
    a('<script setup>')  # 组合式 API 写法
    a("import { reactive, ref } from 'vue'")  # 响应式与引用
    a("import { ElMessage, ElMessageBox } from 'element-plus'")  # 消息提示与确认框
    # 按钮图标按需引入，避免全量打包
    # 与模板中使用的图标一一对应
    a("import { UploadFilled, Plus, Edit, Delete, Search, Refresh, Upload, Download } from '@element-plus/icons-vue'")
    # 引入本模块的 axios 接口封装
    # 模块名决定接口文件路径
    a("import { createApi, deleteApi, exportApi, importApi, listApi, templateApi, updateApi } from '@/api/%s'" % m)
    a("import { dictLabel, dictList, loadDicts } from '@/utils/dict'")  # 字典工具
    # 导入区与逻辑区之间的空行
    a('')
    a("loadDicts()")  # 提前加载字典，避免首屏渲染时缺数据
    # 逻辑区前的空行
    a('')
    a('const loading = ref(false)')  # 列表加载态
    a('const saving = ref(false)')  # 表单提交态
    a('const rows = ref([])')  # 列表数据
    a('const total = ref(0)')  # 记录总数
    a('const selectedIds = ref([])')  # 勾选行主键
    a('const dialogVisible = ref(false)')  # 表单弹窗显隐
    a('const formRef = ref()')  # 表单引用，用于校验
    if table['import_enable']:  # 导入相关的响应式变量
        a('const importVisible = ref(false)')  # 导入弹窗显隐
        a('const importing = ref(false)')  # 导入进行态
        a('const importFile = ref(null)')  # 待上传文件
        a('const importErrors = ref([])')  # 导入错误明细
        a('const fileList = ref([])')  # 上传组件文件列表
    # 状态区与查询对象之间的空行
    a('')
    a('const query = reactive({ page: 1, page_size: 10 })')  # 查询条件默认第一页十条
    # 按查询列初始化条件字段，避免响应式对象缺键
    for c in ctx['query_cols']:  # 按查询列初始化条件字段
        if c['query_type'] == 'between':  # 区间条件拆成起止两个字段
            # 起始字段，与 views 的 _start 参数对应
            a(f"query.{c['column_name']}_start = ''")
            # 结束字段，与 views 的 _end 参数对应
            a(f"query.{c['column_name']}_end = ''")
        else:
            a(f"query.{c['column_name']} = ''")  # 其余条件默认空串
    # 查询对象与表单初始值之间的空行
    a('')
    a('const emptyForm = { %s: null }' % ctx['pk'])  # 表单初始值，主键为空表示新增
    for c in ctx['form_cols']:  # 逐列补初始值
        # 主键跳过，不参与表单初始值
        if c['column_name'] == ctx['pk']:  # 主键跳过
            # 继续处理下一个字段
            continue
        # el-input-number 要求 Number/null，字符串初始值会触发类型校验错误
        init = 'null' if c['form_type'] == 'number' else "''"  # 数字框用 null，其余用空串
        # 逐字段写入初始值
        a(f"emptyForm.{c['column_name']} = {init}")
    a('const form = reactive({ ...emptyForm })')  # 用展开复制，保证重置时互不影响
    # 表单对象与校验规则之间的空行
    a('')
    a('const rules = {')  # 表单校验规则
    # 仅为必填列生成规则，非必填不校验
    for c in ctx['form_cols']:  # 仅为必填列生成规则
        # 主键不参与校验
        if c['column_name'] == ctx['pk']:
            # 跳过主键
            continue
        # 仅必填列需要 required 规则
        if c['is_required']:
            a('  %s: [{ required: true, message: \'请输入%s\', trigger: \'blur\' }],'
              % (c['column_name'], c['column_comment']))  # 失焦时提示必填
    # 结束校验规则对象
    a('}')
    # 校验规则与列表方法之间的空行
    a('')
    a('async function getList() {')  # 拉取列表数据
    # 请求开始即展示加载遮罩
    a('  loading.value = true')
    # 用 try/finally 保证异常时也能复位加载态
    a('  try {')
    a('    const data = await listApi(query)')  # 携带分页与查询条件请求
    # 当前页记录
    a('    rows.value = data.list')
    # 总记录数，供分页与副标题使用
    a('    total.value = data.total')
    a('  } finally {')
    a('    loading.value = false')  # 无论成功失败都关闭加载态
    a('  }')
    a('}')
    # 方法之间留空行
    a('')
    a('function handleQuery() {')  # 查询：重置到第一页后拉取
    # 条件变化后回到第一页，避免越界
    a('  query.page = 1')
    # 重新请求列表
    a('  getList()')
    a('}')
    # 方法之间留空行
    a('')
    a('function resetQuery() {')  # 重置查询条件
    # 遍历查询对象的全部键
    a('  Object.keys(query).forEach((key) => {')
    a("    if (!['page', 'page_size'].includes(key)) query[key] = ''")  # 保留分页字段，仅清空条件
    # 结束遍历
    a('  })')
    # 清空后重新查询
    a('  handleQuery()')
    a('}')
    # 方法之间留空行
    a('')
    a('function onSelectionChange(selection) {')  # 勾选变化时保存主键集合
    # 只取主键，批量删除接口按主键数组处理
    a('  selectedIds.value = selection.map((item) => item.%s)' % ctx['pk'])
    a('}')
    # 方法之间留空行
    a('')
    a('function openCreate() {')  # 打开新增弹窗并重置表单
    # 用初始值覆盖上次编辑残留
    a('  Object.assign(form, emptyForm)')
    # 打开弹窗，主键为空即新增态
    a('  dialogVisible.value = true')
    a('}')
    # 方法之间留空行
    a('')
    a('function handleEdit(row) {')  # 打开编辑弹窗，用行数据回填表单
    # 先重置再合并行数据，避免字段残留
    a('  Object.assign(form, emptyForm, row)')
    # 打开弹窗，主键有值即编辑态
    a('  dialogVisible.value = true')
    a('}')
    # 方法之间留空行
    a('')
    a('function submitForm() {')  # 校验通过后新增或修改
    # 等待表单校验结果
    a('  formRef.value.validate(async (valid) => {')
    # 校验不通过直接返回，错误提示由表单组件展示
    a('    if (!valid) return')
    # 进入提交态，禁用确定按钮
    a('    saving.value = true')
    a('    try {')
    a('      // 数值/日期字段空串转 null，避免后端校验失败')
    a('      const payload = { ...form }')  # 复制提交数据，避免直接改动表单
    for c in ctx['form_cols']:  # 按列类型做空串兜底
        # 主键不提交空值转换
        if c['column_name'] == ctx['pk']:
            # 跳过主键
            continue
        # 仅数值与日期需要特殊处理
        if c['form_type'] in ('number', 'date'):
            # 数值与日期字段的空串转 null，避免后端校验失败
            # 空串转 null 以匹配后端字段类型
            a("      if (payload.%s === '') payload.%s = null" % (c['column_name'], c['column_name']))
    a('      if (form.%s) {' % ctx['pk'])  # 有主键走修改
    # 主键作为路径参数，payload 作请求体
    a('        await updateApi(form.%s, payload)' % ctx['pk'])
    # 修改成功提示
    a("        ElMessage.success('修改成功')")
    # 无主键走新增
    a('      } else {')
    a('        await createApi(payload)')  # 无主键走新增
    # 新增成功提示
    a("        ElMessage.success('新增成功')")
    a('      }')
    # 提交成功后关闭弹窗
    a('      dialogVisible.value = false')
    a('      getList()')  # 提交成功后刷新列表
    a('    } finally {')
    a('      saving.value = false')  # 结束提交态
    a('    }')
    # 结束校验回调
    a('  })')
    # 结束 submitForm
    a('}')
    # 方法之间留空行
    a('')
    a('function handleDelete(row) {')  # 单条删除，先二次确认
    # 用户点击确定后才真正删除
    a("  ElMessageBox.confirm('确认删除该条记录？', '提示', { type: 'warning' }).then(async () => {")
    a('    await deleteApi([row.%s])' % ctx['pk'])  # 接口统一按主键数组删除
    # 删除成功提示
    a("    ElMessage.success('删除成功')")
    # 删除后刷新当前页
    a('    getList()')
    # 结束确认回调
    a('  })')
    # 结束单条删除
    a('}')
    # 方法之间留空行
    a('')
    a('function handleBatchDelete() {')  # 批量删除
    # 确认文案带勾选数量，避免误删
    # 用 replace 动态拼接勾选条数
    a("  ElMessageBox.confirm('确认删除选中的 %s 条记录？'.replace('%s', selectedIds.value.length), '提示', { type: 'warning' }).then(async () => {")
    # 直接提交勾选的主键数组
    a('    await deleteApi(selectedIds.value)')
    # 删除成功提示
    a("    ElMessage.success('删除成功')")
    # 删除后刷新列表
    a('    getList()')
    # 结束确认回调
    a('  })')
    # 结束批量删除
    a('}')
    if table['export_enable']:  # 开启导出才生成导出方法
        # 导出方法前的空行
        a('')
        a('async function handleExport() {')  # 按当前条件导出 Excel
        # 导出接口返回二进制流
        a('  const blob = await exportApi(query)')
        a('  const url = URL.createObjectURL(blob)')  # 二进制转临时地址
        a("  const link = document.createElement('a')")  # 借助隐藏链接触发下载
        # 指向临时地址
        a("  link.href = url")
        a("  link.download = '%s.xlsx'" % table['module_comment'])  # 以模块中文名作文件名
        # 模拟点击即触发浏览器下载
        a('  link.click()')
        a('  URL.revokeObjectURL(url)')  # 释放临时对象地址
        # 结束导出方法
        a('}')
    if table['import_enable']:  # 开启导入才生成模板下载与导入方法
        # 导入方法前的空行
        a('')
        a('function onFileChange(file) {')  # 选择文件时缓存原始文件对象
        # 保存原生 File，提交时再组 FormData
        a('  importFile.value = file.raw')
        # 结束文件选择回调
        a('}')
        # 方法之间留空行
        a('')
        a('async function downloadTemplate() {')  # 下载后端生成的导入模板
        # 模板接口同样返回二进制流
        a('  const blob = await templateApi()')
        # 转临时地址
        a('  const url = URL.createObjectURL(blob)')
        # 创建隐藏下载链接
        a("  const link = document.createElement('a')")
        # 指向模板文件
        a("  link.href = url")
        # 模板文件名带模块中文名
        a("  link.download = '%s导入模板.xlsx'" % table['module_comment'])
        # 触发下载
        a('  link.click()')
        # 释放临时对象地址
        a('  URL.revokeObjectURL(url)')
        # 结束模板下载
        a('}')
        # 方法之间留空行
        a('')
        a('async function submitImport() {')  # 提交 Excel 导入
        # 未选择文件时直接提示
        a('  if (!importFile.value) {')
        # 警告提示
        a("    ElMessage.warning('请选择要导入的文件')")
        # 中断提交
        a('    return')
        # 结束前置校验
        a('  }')
        # 进入导入中状态
        a('  importing.value = true')
        a('  importErrors.value = []')  # 清空上一次的错误明细
        # 用 try/finally 复位导入状态
        a('  try {')
        # 以 multipart 上传文件
        a('    const result = await importApi(importFile.value)')
        a("    ElMessage.success(`成功导入 ${result.success_count} 条`)")  # 展示成功条数
        a('    if (result.errors && result.errors.length) importErrors.value = result.errors')  # 有错误则留在弹窗展示
        a('    else importVisible.value = false')  # 全部成功才关闭弹窗
        # 导入后刷新列表
        a('    getList()')
        a('  } finally {')
        # 结束导入中状态
        a('    importing.value = false')
        a('  }')
        # 结束导入提交
        a('}')
    # 方法区与初始化调用之间的空行
    a('')
    a('getList()')  # 组件初始化即拉取首屏数据
    # 结束脚本段
    a('</script>')
    # 脚本与样式之间的空行
    a('')
    a('<style scoped>')  # 局部样式，避免污染全局
    # 页头标题：加粗、深色，与副标题形成层次
    # 标题选择器
    a('.page-title-wrap h2 {')
    # 去掉默认外边距
    a('  margin: 0;')
    # 标题字号
    a('  font-size: 20px;')
    # 半粗字重
    a('  font-weight: 600;')
    # 深灰文字色
    a('  color: #1f2937;')
    # 轻微字间距
    a('  letter-spacing: 0.5px;')
    # 结束标题规则
    a('}')
    # 副标题选择器
    a('.page-title-wrap .sub {')
    # 与标题留出间距
    a('  margin-top: 6px;')
    # 小字号
    a('  font-size: 12px;')
    # 浅灰辅助色
    a('  color: #8a94a6;')
    # 结束副标题规则
    a('}')
    # 卡片头部布局
    a('.card-header {')
    # 横向排列
    a('  display: flex;')
    # 垂直居中
    a('  align-items: center;')
    # 标题与按钮两端对齐
    a('  justify-content: space-between;')
    # 结束卡片头部规则
    a('}')
    # 卡片标题样式
    a('.card-title {')
    # 标题字号
    a('  font-size: 15px;')
    # 半粗字重
    a('  font-weight: 600;')
    # 深灰文字色
    a('  color: #1f2937;')
    # 结束卡片标题规则
    a('}')
    # 操作按钮组布局
    a('.card-actions {')
    # 横向排列
    a('  display: flex;')
    # 垂直居中
    a('  align-items: center;')
    # 按钮间距
    a('  gap: 10px;')
    # 结束按钮组规则
    a('}')
    # 抵消 Element 默认的按钮左边距
    a('.card-actions .el-button + .el-button {')
    # 改由 gap 控制间距
    a('  margin-left: 0;')
    # 结束按钮间距规则
    a('}')
    # 弹窗表单样式
    a('.dialog-form {')
    # 顶部留白
    a('  padding-top: 4px;')
    # 结束弹窗表单规则
    a('}')
    # 通用下间距工具类
    a('.mb12 { margin-bottom: 12px }')
    # 通用上间距工具类
    a('.mt12 { margin-top: 12px }')
    # 结束样式段
    a('</style>')
    return '\n'.join(lines)  # 拼装为完整 SFC 字符串


def build_api_js(table, ctx):
    """生成 axios 请求封装 js。"""
    # 基础增删改查接口；BASE 只写业务前缀，baseURL 由 request 封装统一补 /api
    # 生成产物：frontend/src/api/<module>.js，页面通过具名导入调用这些函数。
    # 只生成导出/导入接口当且仅当主表配置开启了对应能力，避免出现无用请求。
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
"""]  # 基础接口封装，作为第一部分
    if table['export_enable']:  # 开启导出才追加导出接口
        # 导出接口对应 views 的 exportData 动作，返回 Excel 文件流
        parts.append("""
export function exportApi(params) {
  return request({ url: BASE + '/exportData', method: 'get', params, responseType: 'blob' })
}
""")  # responseType 为 blob，前端按文件流处理
    if table['import_enable']:  # 开启导入才追加模板下载与导入接口
        # 模板下载返回 Excel 文件流；导入接口以 multipart 上传单个文件
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
""")  # 上传需显式声明 multipart 头
    return ''.join(parts)  # 拼成完整 js 文本
