"""学生信息表 管理接口（由代码生成器生成，可二次修改）。"""
import io  # 内存流，直接在内存中拼装 xlsx 与响应体
import time  # 生成当前时间字符串，写入审计字段
from datetime import datetime  # 判断导出值是否为时间类型

import openpyxl  # 读写 Excel 文件
from django.http import HttpResponse  # 构造文件下载响应
from rest_framework import viewsets  # DRF 视图集基类，按 action 分派处理方法

from apps.student.models import BizStudent  # 学生信息表模型
from apps.student.serializers import (  # 三个序列化器覆盖写入、列表、详情三种场景
    BizStudentCreateSerializer,  # 新增与编辑用的写入序列化器
    BizStudentListSerializer,  # 列表用的精简序列化器
    BizStudentSerializer,  # 详情与返回的完整序列化器
)
from common.pagination import StandardPagination  # 统一分页参数解析
from common.permissions import PermissionCheck  # 基于 perm_map 的接口权限校验
from common.response import fail, ok  # 统一响应包装


EXPORT_COLUMNS = [  # 导出 Excel 的列映射：(模型字段名, 表头中文名)
    ('name', '学生姓名'),  # 第 1 列：姓名
    ('age', '年龄'),  # 第 2 列：年龄
    ('gender', '性别（字典sys_user_sex）'),  # 第 3 列：性别字典值
    ('phone', '手机号'),  # 第 4 列：手机号
    ('email', '邮箱'),  # 第 5 列：邮箱
    ('enroll_date', '入学日期'),  # 第 6 列：入学日期
    ('score', '总分'),  # 第 7 列：总分
    ('address', '家庭住址'),  # 第 8 列：家庭住址
]


IMPORT_COLUMNS = [  # 导入模板的列映射，顺序决定 Excel 列读取位置
    ('name', '学生姓名'),  # 第 1 列：姓名（必填）
    ('age', '年龄'),  # 第 2 列：年龄
    ('gender', '性别（字典sys_user_sex）'),  # 第 3 列：性别字典值
    ('phone', '手机号'),  # 第 4 列：手机号
    ('email', '邮箱'),  # 第 5 列：邮箱
    ('enroll_date', '入学日期'),  # 第 6 列：入学日期
    ('score', '总分'),  # 第 7 列：总分
    ('address', '家庭住址'),  # 第 8 列：家庭住址
]


FILE_NAME = '学生信息表.xlsx'  # 导出文件名


class BizStudentViewSet(viewsets.ViewSet):
    """学生信息表管理"""

    module_name = '学生信息表'  # 模块名，用于日志与提示
    permission_classes = [PermissionCheck]  # 全部接口先做权限校验

    @property
    def perm_map(self):
        """接口动作到权限编码的映射，供 PermissionCheck 校验。"""
        prefix = 'student'  # 权限编码统一前缀
        return {
            'list': prefix + ':list',  # 列表查询权限
            'create': prefix + ':create',  # 新增权限
            'update': prefix + ':update',  # 编辑权限
            'delete': prefix + ':delete',  # 删除权限
            'import_template': prefix + ':import',  # 模板下载复用导入权限
            'import_data': prefix + ':import',  # 数据导入权限
            'export_data': prefix + ':export',  # 数据导出权限
        }

    def get_queryset(self):
        """返回未逻辑删除的记录集，主键升序便于稳定分页。"""
        queryset = BizStudent.objects.all()  # 全量记录集
        queryset = queryset.filter(is_deleted=0)  # 只保留未删除数据
        return queryset.order_by('id')  # 固定排序，避免分页结果漂移

    def apply_filters(self, request, queryset):
        """按查询参数逐列过滤，文本模糊匹配、其余等值匹配。"""
        queryset = queryset.filter(is_deleted=0)  # 再次兜底过滤已删除数据
        value = request.query_params.get('name')  # 学生姓名条件
        if value:  # 非空才过滤
            queryset = queryset.filter(name__icontains=value)  # 姓名模糊匹配
        value = request.query_params.get('age')  # 年龄条件
        if value not in (None, ''):  # 区分 0 与空值
            queryset = queryset.filter(age=value)  # 年龄等值匹配
        value = request.query_params.get('gender')  # 性别字典值条件
        if value not in (None, ''):  # 字典值 0 也需保留
            queryset = queryset.filter(gender=value)  # 性别等值匹配
        value = request.query_params.get('phone')  # 手机号条件
        if value:  # 非空才过滤
            queryset = queryset.filter(phone__icontains=value)  # 手机号模糊匹配
        value = request.query_params.get('email')  # 邮箱条件
        if value:  # 非空才过滤
            queryset = queryset.filter(email__icontains=value)  # 邮箱模糊匹配
        value = request.query_params.get('enroll_date')  # 入学日期条件
        if value not in (None, ''):  # 空串视为未填写
            queryset = queryset.filter(enroll_date=value)  # 日期等值匹配
        value = request.query_params.get('score')  # 总分条件
        if value not in (None, ''):  # 保留 0 分查询
            queryset = queryset.filter(score=value)  # 总分等值匹配
        value = request.query_params.get('address')  # 家庭住址条件
        if value:  # 非空才过滤
            queryset = queryset.filter(address__icontains=value)  # 住址模糊匹配
        return queryset  # 返回过滤后的记录集

    def list(self, request):
        """分页查询学生列表。"""
        queryset = self.apply_filters(request, self.get_queryset())  # 先按条件过滤
        return StandardPagination(request).paginate(queryset, BizStudentListSerializer)  # 统一分页并序列化输出

    def create(self, request):
        """新增学生记录，自动写入创建人与时间。"""
        serializer = BizStudentCreateSerializer(data=request.data)  # 校验前端提交数据
        serializer.is_valid(raise_exception=True)  # 校验失败由 DRF 直接抛 400
        user = getattr(request, 'user_info', None)  # 兼容未注入用户信息的场景
        now = time.strftime('%Y-%m-%d %H:%M:%S')  # 统一写入时间
        instance = serializer.save(  # 落库并在同一次 save 中补齐审计字段
            create_by=user.username if user else '', create_time=now,
            update_by=user.username if user else '', update_time=now)  # 保存时补齐审计字段
        return ok(BizStudentSerializer(instance).data, '新增成功')  # 返回完整详情

    def update(self, request, pk=None):
        """按主键更新学生记录，仅更新提交的字段。"""
        instance = self.get_queryset().filter(pk=pk).first()  # 未删除记录中按主键查找
        if not instance:  # 记录不存在或已删除
            return fail('记录不存在', code=404)  # 返回 404 业务错误
        serializer = BizStudentCreateSerializer(instance, data=request.data, partial=True)  # 局部更新允许只传部分字段
        serializer.is_valid(raise_exception=True)  # 校验失败由 DRF 直接抛 400
        user = getattr(request, 'user_info', None)  # 兜底获取当前用户，未注入时置空
        serializer.save(update_by=user.username if user else '',  # 仅刷新更新审计字段
                        update_time=time.strftime('%Y-%m-%d %H:%M:%S'))  # 刷新更新人与更新时间
        return ok(BizStudentSerializer(instance).data, '修改成功')  # 返回修改后的详情

    def delete(self, request):
        """按主键批量逻辑删除学生记录。"""
        ids = request.data.get('ids') or []  # 前端提交的主键数组
        if not ids:  # 未选择数据时提示
            return fail('请选择要删除的数据')  # 不做空集合更新，直接返回业务错误
        queryset = self.get_queryset().filter(id__in=ids)  # 仅命中未删除记录，避免重复删除
        user = getattr(request, 'user_info', None)  # 兜底获取当前用户
        queryset.update(is_deleted=1, update_by=user.username if user else '')  # 批量标记删除并记录操作人
        return ok(None, '删除成功')  # 返回成功提示


    def import_template(self, request):
        """下载导入模板。"""
        wb = openpyxl.Workbook()  # 新建工作簿
        ws = wb.active  # 取默认工作表
        ws.title = '学生信息表'  # 工作表名称与业务一致
        ws.append([label for _, label in IMPORT_COLUMNS])  # 首行写入中文表头
        buf = io.BytesIO()  # 内存缓冲，不落临时文件
        wb.save(buf)  # 把工作簿写入缓冲
        # 使用 xlsx 标准 MIME，浏览器才按 Excel 处理
        response = HttpResponse(  # 内存中的工作簿直接作为响应体输出
            buf.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename=import_template.xlsx'  # 声明下载文件名
        return response  # 返回文件流

    def import_data(self, request):
        """Excel 导入：校验失败返回行号与错误信息，不导入脏数据。"""
        file = request.FILES.get('file')  # 取上传文件
        if not file:  # 未上传时提示
            return fail('请上传 Excel 文件')  # 缺少文件直接拒绝，避免空指针
        try:  # 尝试按 xlsx 解析，非 Excel 或文件损坏会进入异常分支
            wb = openpyxl.load_workbook(file, read_only=True)  # 只读模式加载，降低内存占用
        except Exception:  # 非 Excel 或文件损坏
            return fail('Excel 文件解析失败，请使用导入模板填写数据')
        ws = wb.active  # 取第一个工作表
        errors = []  # 汇总全部行级错误
        to_create = []  # 暂存待批量写入的实例
        for index, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):  # 跳过表头，行号从 2 开始
            if all(v in (None, '') for v in row):  # 整行为空视为空行，直接跳过
                continue  # 空行不参与导入，也不计入错误
            data = {}  # 收集当前行按模型字段名映射的数据
            for pos, (name, _) in enumerate(IMPORT_COLUMNS):  # 按模板列顺序映射到模型字段
                if pos < len(row):  # 兼容用户删减列的情况
                    data[name] = row[pos]  # 按位置取值
            row_errors = []  # 当前行的错误列表
            if data.get('name') in (None, ''):  # 唯一必填项校验
                row_errors.append('学生姓名 不能为空')  # 姓名缺失是模板唯一必填错误

            if row_errors:  # 当前行有错则记录并跳过，不构造实例
                errors.extend('第 %d 行：%s' % (index, e) for e in row_errors)  # 拼上 Excel 行号便于定位
                continue  # 跳过本行，等全部行校验完再决定整批导入
            to_create.append(BizStudent(**data))  # 先构造实例，全部校验通过后再统一写入
        if errors:  # 存在任何错误则整批拒绝导入
            return ok({'success_count': 0, 'errors': errors[:50]}, '校验失败，未导入任何数据')  # 最多返回 50 条错误
        user = getattr(request, 'user_info', None)  # 兜底获取当前用户
        now = time.strftime('%Y-%m-%d %H:%M:%S')  # 统一写入时间
        for obj in to_create:  # 逐条补齐审计字段
            obj.create_by = user.username if user else ''  # 记录导入人
            obj.create_time = now  # 记录导入时间
        BizStudent.objects.bulk_create(to_create)  # 一次性批量写入，减少数据库往返
        return ok({'success_count': len(to_create), 'errors': []}, '导入成功')  # 返回成功条数



    def export_data(self, request):
        """按当前查询条件导出 Excel（限制最大行数）。"""
        queryset = self.apply_filters(request, self.get_queryset())  # 复用列表过滤逻辑
        queryset = queryset[:self.get_config_int('sys.export.max_rows', 50000)]  # 按配置截断，防止导出过大
        wb = openpyxl.Workbook()  # 新建工作簿
        ws = wb.active  # 取默认工作表
        ws.title = '学生信息表'  # 工作表名称
        ws.append([label for _, label in EXPORT_COLUMNS])  # 首行写入中文表头
        for row in queryset:  # 逐行写入数据
            values = []  # 当前行待写入的单元格值
            for name, _ in EXPORT_COLUMNS:  # 按导出列顺序取值
                value = getattr(row, name, None)  # 字段缺失时取空值
                if isinstance(value, datetime):  # 时间类型转成可读字符串
                    value = value.strftime('%Y-%m-%d %H:%M:%S')  # 统一格式化，避免 Excel 显示原始日期对象
                values.append(value)  # 加入当前行
            ws.append(values)  # 写入一行
        buf = io.BytesIO()  # 内存缓冲
        wb.save(buf)  # 把工作簿写入缓冲
        response = HttpResponse(  # 以二进制附件形式返回，浏览器直接下载
            buf.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')  # xlsx 标准 MIME
        response['Content-Disposition'] = 'attachment; filename=' + FILE_NAME  # 文件名含中文，交由浏览器处理
        return response  # 返回文件流

    @staticmethod  # 静态工具方法：读取配置不依赖视图实例
    def get_config_int(key, default):
        """读取系统配置中的整数项，缺失或非法时返回默认值。"""
        from apps.system.models import SysConfig  # 局部导入，避免模块级循环依赖
        # 按配置键查询未删除的配置项，再取第一条配置值
        value = SysConfig.objects.filter(config_key=key, is_deleted=0) \
            .values_list('config_value', flat=True).first()  # 取未删除配置的第一条值
        try:  # 配置值可能为空或非数字，转换失败时回退默认值
            return int(value) if value else default  # 空值直接用默认值
        except (TypeError, ValueError):  # 配置不是合法数字时不让导出失败
            return default  # 回退默认值
