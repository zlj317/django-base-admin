"""报表模块视图集。"""
import time  # 生成时间

from rest_framework.decorators import action  # 自定义路由装饰器

from common.pagination import StandardPagination  # 统一分页
from common.response import fail, ok  # 统一响应封装
from common.views import CrudViewSet  # 通用 CRUD 基类

from apps.report.models import RpCategory, RpDatasource, RpGenerateRecord, RpTemplate  # 报表相关模型
from apps.report.render import build_record_report, build_report  # 报表数据渲染
from apps.report.serializers import (RpCategorySerializer, RpDatasourceSerializer,  # 对应序列化器
                                     RpGenerateRecordSerializer, RpTemplateSerializer)


class RpCategoryViewSet(CrudViewSet):
    """报表分类表 CRUD：管理报表分类。"""
    model = RpCategory  # 目标模型
    serializer_class = RpCategorySerializer  # 序列化器
    perm_prefix = 'rp'  # 权限前缀：rp:list/create/update/delete
    filter_map = {  # 支持的查询参数与 ORM lookup 映射
        'category_name': 'icontains',  # 分类名称模糊搜索
        'status': 'exact',  # 状态精确匹配
    }
    order_by = 'sort'  # 按排序号升序
    module_name = '报表分类'  # 操作日志模块名


class RpDatasourceViewSet(CrudViewSet):
    """报表数据源表 CRUD：管理数据源连接。"""
    model = RpDatasource  # 目标模型
    serializer_class = RpDatasourceSerializer  # 序列化器
    perm_prefix = 'rp'  # 权限前缀
    filter_map = {  # 支持的查询参数
        'ds_name': 'icontains',  # 数据源名称模糊搜索
        'ds_type': 'exact',  # 数据源类型精确匹配
        'status': 'exact',  # 状态精确匹配
    }
    order_by = '-id'  # 按主键倒序
    module_name = '报表数据源'  # 操作日志模块名


class RpTemplateViewSet(CrudViewSet):
    """报表模板表 CRUD：管理报表模板。"""
    model = RpTemplate  # 目标模型
    serializer_class = RpTemplateSerializer  # 序列化器
    perm_prefix = 'rp'  # 权限前缀
    filter_map = {  # 支持的查询参数
        'template_name': 'icontains',  # 模板名称模糊搜索
        'template_key': 'icontains',  # 模板编码模糊搜索
        'category_id': 'exact',  # 分类精确匹配
        'ds_id': 'exact',  # 数据源精确匹配
        'status': 'exact',  # 状态精确匹配
    }
    order_by = '-id'  # 按主键倒序
    module_name = '报表模板'  # 操作日志模块名

    @action(detail=True, methods=['get'])
    def preview(self, request, pk=None):
        """报表预览：解析模板配置并返回可绘制的图表数据。"""
        tpl = RpTemplate.objects.filter(pk=pk, is_deleted=0).first()
        if not tpl:
            return fail('模板不存在', code=404)
        return ok(build_report(tpl), '获取成功')

    @action(detail=True, methods=['post'])
    def generate(self, request, pk=None):
        """手动生成报表：落生成记录并直接返回本次渲染结果。"""
        tpl = RpTemplate.objects.filter(pk=pk, is_deleted=0).first()
        if not tpl:
            return fail('模板不存在', code=404)
        user = getattr(request, 'user_info', None)
        now = time.strftime('%Y-%m-%d %H:%M:%S')
        data = request.data or {}
        param = data.get('param_json') or data.get('param') or ''
        started = time.time()
        report = build_report(tpl)  # 先渲染数据，耗时计入生成记录
        cost = int((time.time() - started) * 1000)
        record = RpGenerateRecord.objects.create(
            template_id=tpl.id, template_name=tpl.template_name,
            param_json=str(param), gen_status=1, gen_type='manual',
            gen_user_id=getattr(user, 'id', None),
            cost_time=max(cost, 1), gen_time=now,
            create_by=user.username if user else '', create_time=now,
            update_by=user.username if user else '', update_time=now, is_deleted=0,
        )
        report['record'] = RpGenerateRecordSerializer(record).data
        return ok(report, '报表生成成功')


class RpGenerateRecordViewSet(CrudViewSet):
    """报表生成记录表 CRUD：已生成的报表记录。"""
    model = RpGenerateRecord  # 目标模型
    serializer_class = RpGenerateRecordSerializer  # 序列化器
    perm_prefix = 'rp'  # 权限前缀
    filter_map = {  # 支持的查询参数
        'template_id': 'exact',  # 模板精确匹配
        'template_name': 'icontains',  # 模板名称模糊搜索
        'gen_status': 'exact',  # 生成状态精确匹配
        'gen_type': 'exact',  # 触发方式精确匹配
    }
    order_by = '-id'  # 按主键倒序
    module_name = '报表生成记录'  # 操作日志模块名

    @action(detail=True, methods=['get'])
    def preview(self, request, pk=None):
        """按生成记录回放报表效果。"""
        record = self.get_queryset().filter(pk=pk).first()
        if not record:
            return fail('生成记录不存在', code=404)
        return ok(build_record_report(record), '获取成功')
