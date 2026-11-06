"""代码生成器视图。"""
# 模块用途：代码生成器的 HTTP 入口，串起“读取库表 → 导入 → 保存字段配置 → 预览/下载代码”的完整链路。
# 对应路由：apps/gen/urls.py 挂载 /gen/db/tables、/gen/db/import、/gen/table/<pk>/preview|ddl|download 等。
# 权限：permission_classes=[PermissionCheck] 配合 perm_map，按 action 校验 gen:table:* 权限标识。
# 调用关系：库表元数据读取、默认配置推断、模板渲染与 DDL 查询全部委托 apps/gen/engine.py。
# 被谁调用：前端“代码生成”页面；本视图又由 config/urls.py 中的 include 挂到 /api/gen/ 前缀下。
import io  # 用于在内存中构造 ZIP 二进制流，避免落盘
import zipfile  # 用于把渲染结果打包成 ZIP
from datetime import datetime  # 生成审计时间字符串

from django.db import connection, transaction  # connection 执行原生 SQL，transaction 保证保存配置的原子性
from django.http import HttpResponse  # 构造文件下载响应
from rest_framework import viewsets  # DRF 视图集基类，按 action 分派处理方法

from apps.gen import engine  # 代码生成引擎，负责读表、推断配置与渲染
from apps.gen.models import SysGenTable, SysGenTableColumn  # 生成任务主表与字段配置表模型
from apps.gen.serializers import GenColumnSerializer, GenTableSerializer  # 配置读写序列化器
from apps.system.models import SysMenu  # 系统菜单模型，用于自动注册菜单与按钮权限
from common.pagination import StandardPagination  # 统一分页参数解析工具
from common.permissions import PermissionCheck  # 基于 perm_map 的接口权限校验
from common.response import fail, ok  # 统一响应包装


class GenTableViewSet(viewsets.ViewSet):
    """代码生成：表读取 / 配置 / 预览 / 下载。"""

    module_name = '代码生成'  # 模块名，用于日志与错误提示

    # perm_map 以 property 形式暴露：PermissionCheck 在每次请求时按当前 action 读取，避免类属性写死。
    @property
    def perm_map(self):
        """接口动作到权限编码的映射，供 PermissionCheck 校验。"""
        # 键是路由 as_view 中声明的 action 名，值是 sys_menu.perms 中配置的权限标识；未配置的动作会被放行。
        return {
            'list': 'gen:table:list',  # 配置列表查询权限
            'db_tables': 'gen:table:import',  # 读取可导入表清单，归入导入权限
            'import_tables': 'gen:table:import',  # 导入数据表权限
            'retrieve': 'gen:table:list',  # 配置详情复用列表权限
            'save': 'gen:table:update',  # 保存配置权限
            'delete': 'gen:table:delete',  # 删除配置权限
            'preview': 'gen:table:preview',  # 代码预览权限
            'download': 'gen:table:download',  # 代码下载权限
            'ddl': 'gen:table:preview',  # 建表语句复用一个预览权限
        }

    # 所有 action 统一挂 PermissionCheck：先校验登录（401），再按 perm_map 比对按钮权限（403）。
    permission_classes = [PermissionCheck]  # 全部接口先做权限校验

    # ---- 数据库表读取与导入 ----
    def db_tables(self, request):
        """按关键字筛选数据库中的业务表，并附带是否已导入标记。"""
        keyword = request.query_params.get('table_name')  # 取表名关键字，可为空
        tables = engine.list_db_tables(keyword)  # 引擎返回已过滤系统表后的表清单
        # 分页在内存中完成：信息来源是 information_schema，业务表数量有限，无需数据库层分页。
        page = StandardPagination(request)  # 解析页码与每页条数
        start = page.offset  # 计算当前页起始下标
        data = {
            'total': len(tables),  # 总条数，前端分页组件使用
            'page': page.page,  # 当前页码
            'page_size': page.page_size,  # 每页条数
            'list': tables[start:start + page.page_size],  # 内存切片取当前页数据
        }
        return ok(data)  # 统一成功响应

    def import_tables(self, request):
        """批量导入选中表：逐张处理并汇总成功与失败信息。"""
        table_names = request.data.get('tables') or []  # 前端勾选的表名列表
        if not table_names:  # 未选择任何表时直接提示
            return fail('请选择要导入的表')
        errors, success = [], []  # 分别收集失败原因与成功表名
        username = request.user_info.username  # 当前操作人，写入审计字段
        for name in table_names:  # 逐表导入，单表失败不影响其他表
            try:
                engine.import_table(name, username)  # 写入主表与默认字段配置
                success.append(name)  # 记录成功表名
            except Exception as exc:  # 捕获业务与数据库异常，转为可读错误
                errors.append(f'{name}: {exc}')  # 拼装“表名: 原因”便于定位
        msg = f'成功导入 {len(success)} 张表'  # 默认成功提示
        if errors:  # 存在失败时追加失败明细
            msg += '；失败：' + '；'.join(errors)  # 拼接全部失败原因
        return ok({'success': success, 'errors': errors}, msg)  # 返回明细与汇总提示

    # ---- 生成配置管理 ----
    def list(self, request):
        """分页查询生成配置，并附带每个配置的字段数量。"""
        queryset = SysGenTable.objects.filter(is_deleted=0).order_by('id')  # 只取未删除配置并按主键升序
        table_name = request.query_params.get('table_name')  # 表名模糊查询参数
        module_comment = request.query_params.get('module_comment')  # 模块中文名模糊查询参数
        if table_name:  # 有表名条件时追加过滤
            queryset = queryset.filter(table_name__icontains=table_name)  # 表名不区分大小写模糊匹配
        if module_comment:  # 有模块名条件时追加过滤
            queryset = queryset.filter(module_comment__icontains=module_comment)  # 模块名模糊匹配
        page = StandardPagination(request)  # 解析分页参数
        total = queryset.count()  # 先统计总数供分页组件使用
        rows = queryset[page.offset:page.offset + page.page_size]  # 切片取当前页记录
        # 主表信息由序列化器输出，字段数量需要额外统计，前端列表据此展示“已配置字段数”。
        data = []  # 组装返回列表
        for t in rows:  # 逐条补字段数量
            item = GenTableSerializer(t).data  # 序列化主表信息
            item['column_count'] = SysGenTableColumn.objects.filter(
                gen_table_id=t.id, is_deleted=0).count()  # 统计该配置下未删除的字段数
            data.append(item)  # 加入返回列表
        return ok({'total': total, 'page': page.page, 'page_size': page.page_size, 'list': data})  # 返回分页结构

    def retrieve(self, request, pk=None):
        """生成配置详情（不可命名为 detail：DRF as_view 会设置 cls.detail=None 遮蔽）。"""
        table = SysGenTable.objects.filter(pk=pk, is_deleted=0).first()  # 按主键取未删除配置
        if not table:  # 配置不存在或已删除
            return fail('配置不存在', code=404)  # 返回 404 业务错误
        columns = SysGenTableColumn.objects.filter(gen_table_id=pk, is_deleted=0)  # 取该配置下全部未删除字段
        return ok({
            'table': GenTableSerializer(table).data,  # 主表信息
            'columns': GenColumnSerializer(columns, many=True).data,  # 字段配置列表
        })  # 一次性返回主表与字段

    def save(self, request, pk=None):
        """保存生成配置：主表信息 + 整组字段配置（整体替换）。"""
        table = SysGenTable.objects.filter(pk=pk, is_deleted=0).first()  # 先确认配置存在
        if not table:  # 不存在则直接返回
            return fail('配置不存在', code=404)  # 统一 404 提示

        with transaction.atomic():  # 主表与字段配置要么全成功要么全回滚
            # 只更新前端提交的字段，未提交字段保持原值
            table_serializer = GenTableSerializer(table, data=request.data.get('table') or {},
                                                  partial=True)
            table_serializer.is_valid(raise_exception=True)  # 校验失败直接抛出 400
            username = request.user_info.username  # 当前操作人，写入审计字段
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # 统一的时间字符串
            table_serializer.save(update_by=username, update_time=now)  # 保存主表并刷新审计字段

            # 字段配置采用“整组替换”：先物理清空旧列再按提交顺序重建，避免残留已删除的列。
            columns = request.data.get('columns')  # 前端提交的整组字段配置
            if columns is not None:  # 未提交 columns 时保持原字段配置不动
                SysGenTableColumn.objects.filter(gen_table_id=pk).delete()  # 整体替换：先物理清空旧字段
                for i, col in enumerate(columns):  # 按提交顺序重建字段
                    col = dict(col)  # 复制为普通字典，避免改动请求数据
                    col['gen_table_id'] = pk  # 绑定所属生成任务
                    col['sort'] = col.get('sort', i)  # 未给排序号时按提交顺序兜底
                    col['create_by'] = username  # 记录创建人
                    col['create_time'] = now  # 记录创建时间
                    col_serializer = GenColumnSerializer(data=col)  # 逐列走序列化校验
                    col_serializer.is_valid(raise_exception=True)  # 任何一列不合法则整体回滚
                    col_serializer.save()  # 写入字段配置
        return ok(None, '保存成功')  # 返回成功提示

    def delete(self, request):
        """按主键批量逻辑删除生成配置及其字段配置。"""
        ids = request.data.get('ids') or []  # 前端提交的主键列表
        if not ids:  # 未选择数据时提示
            return fail('请选择要删除的数据')
        SysGenTable.objects.filter(id__in=ids).update(is_deleted=1)  # 主表标记删除而不物理删除
        SysGenTableColumn.objects.filter(gen_table_id__in=ids).update(is_deleted=1)  # 级联标记对应字段配置
        return ok(None, '删除成功')  # 返回成功提示

    # ---- 预览 / DDL / 下载 ----
    def _load(self, pk):
        """按主键加载配置主表与字段列表，任一缺失返回空值。"""
        table = SysGenTable.objects.filter(pk=pk, is_deleted=0).first()  # 取未删除的配置主表
        if not table:  # 配置不存在时保持返回契约一致
            return None, None  # 主表与字段均为空
        columns = list(SysGenTableColumn.objects.filter(gen_table_id=pk, is_deleted=0))  # 取字段配置并转为列表
        return table, columns  # 返回主表与字段集合

    def preview(self, request, pk=None):
        """在线预览生成的全部文件内容，不定盘。"""
        table, columns = self._load(pk)  # 加载配置
        if not table:  # 配置不存在
            return fail('配置不存在', code=404)  # 统一 404 提示
        # 引擎返回 (相对路径, 文本内容) 列表；此处在内存中直接回传，不写磁盘。
        files = engine.render_files(table, columns)  # 引擎渲染全部文件
        return ok({'files': [{'name': path.split('/')[-1], 'path': path, 'content': content}
                             for path, content in files]})  # 转成前端可直接展示的文件树数据

    def ddl(self, request, pk=None):
        """返回源表的建表语句，便于核对生成依据。"""
        table, _ = self._load(pk)  # 这里只用主表，字段配置可忽略
        if not table:  # 配置不存在
            return fail('配置不存在', code=404)  # 统一 404 提示
        try:
            return ok({'ddl': engine.get_table_ddl(table.table_name)})  # 读取 SHOW CREATE TABLE 结果
        except ValueError as exc:  # 表名非法等业务异常
            return fail(str(exc))  # 转为业务错误提示

    def download(self, request, pk=None):
        """打包 ZIP 下载；若配置了父级菜单则自动注册菜单与按钮权限。"""
        table, columns = self._load(pk)  # 加载配置
        if not table:  # 配置不存在
            return fail('配置不存在', code=404)  # 统一 404 提示
        if table.parent_menu_id:  # 指定父级菜单时才做菜单注册
            self.create_menus(table, columns, request.user_info.username)  # 注册菜单与按钮权限

        # 先按现有配置渲染全部文件，再统一打包，保证预览与下载内容一致。
        files = engine.render_files(table, columns)  # 渲染全部文件
        buf = io.BytesIO()  # 内存缓冲，避免产生临时文件
        with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:  # 以 deflate 压缩写入
            for path, content in files:  # 逐个写入生成文件
                zf.writestr(path, content or '\n')  # 空内容补换行，避免生成空文件异常
        response = HttpResponse(buf.getvalue(),
                                content_type='application/octet-stream')  # 以二进制流返回
        response['Content-Disposition'] = f'attachment; filename={table.module_name}_code.zip'  # 声明下载文件名
        return response  # 直接返回文件流

    def create_menus(self, table, columns, username):
        """在 sys_menu 中注册业务菜单与按钮权限。"""
        prefix = table.module_name  # 权限编码统一以模块名作前缀
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # 统一写入时间

        def insert(parent_id, menu_name, menu_type, path='', component='', perms='', icon=''):
            """插入一条菜单记录并返回雪花主键，供按钮挂载到菜单下。"""
            from common.snowflake import next_id  # 主键统一由后端雪花算法生成
            menu_id = next_id()  # 先取主键，再随 INSERT 一起写入
            with connection.cursor() as cursor:  # 菜单表由 SQL 维护，这里用原生 SQL 写入
                # 参数化插入，避免菜单名等文本污染 SQL
                cursor.execute(
                    "INSERT INTO sys_menu (id, parent_id, menu_name, path, component, perms, "
                    "menu_type, icon, order_num, visible, status, create_by, create_time, is_deleted) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 0, '0', '0', %s, %s, 0)",
                    [menu_id, parent_id, menu_name, path, component, perms, menu_type, icon, username, now])
                return menu_id  # 返回本次生成的雪花 ID

        # 以“列表权限”作为幂等判据：该模块只要注册过任一菜单/按钮，就不再重复插入。
        if SysMenu.objects.filter(perms=f'{prefix}:list', is_deleted=0).exists():  # 已有列表权限说明注册过
            return  # 已注册过则直接跳过，保证可重复下载
        parent_id = table.parent_menu_id or 0  # 未指定父级时挂到根节点
        menu_id = insert(parent_id, table.module_comment, 'C',
                         path=table.module_name,
                         component=table.gen_path or f'{prefix}/index',
                         icon='Document')  # 注册目录级菜单（C 为菜单类型）
        # 默认注册四个基础按钮；导入/导出按钮按配置开关追加，保持与生成的页面按钮一致。
        buttons = [('查询', f'{prefix}:list'), ('新增', f'{prefix}:create'),
                   ('编辑', f'{prefix}:update'), ('删除', f'{prefix}:delete')]  # 默认的四个按钮权限
        if table.import_enable:  # 开启导入时补充导入按钮
            buttons.append(('导入', f'{prefix}:import'))  # 导入权限编码
        if table.export_enable:  # 开启导出时补充导出按钮
            buttons.append(('导出', f'{prefix}:export'))  # 导出权限编码
        for name, perms in buttons:  # 逐个注册按钮权限（F 为按钮类型）
            insert(menu_id, name, 'F', perms=perms)  # 按钮挂到刚创建的菜单下
