"""报表模块视图集。"""
# 报表模块对外提供：分类/数据源/模板/生成记录四套 CRUD，
# 以及模板预览（只算不落库）、手动生成（落生成记录）两个自定义动作。
import time  # 生成时间与耗时统计

from rest_framework.decorators import action  # 自定义路由装饰器：把方法挂成 extra action

from common.pagination import StandardPagination  # 统一分页（本文件未直接使用，保留统一风格）
from common.response import fail, ok  # 统一响应封装：fail 返回错误、ok 返回成功
from common.views import CrudViewSet  # 通用 CRUD 基类：已封装列表/新增/编辑/删除

from apps.report.models import RpCategory, RpDatasource, RpGenerateRecord, RpTemplate  # 报表相关模型
from apps.report.render import build_record_report, build_report  # 报表数据渲染：模板渲染 / 记录回放
from apps.report.serializers import (RpCategorySerializer, RpDatasourceSerializer,  # 对应序列化器
                                     RpGenerateRecordSerializer, RpTemplateSerializer)


class RpCategoryViewSet(CrudViewSet):  # 报表分类视图集
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


class RpDatasourceViewSet(CrudViewSet):  # 报表数据源视图集
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


class RpTemplateViewSet(CrudViewSet):  # 报表模板视图集
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

    @action(detail=True, methods=['get'])  # 路由：GET /rp/template/preview/<pk>/，按主键预览
    def preview(self, request, pk=None):  # 预览动作：只读，不产生副作用
        """报表预览：解析模板配置并返回可绘制的图表数据。"""
        tpl = RpTemplate.objects.filter(pk=pk, is_deleted=0).first()  # 只查未删除的模板
        if not tpl:  # 模板不存在
            return fail('模板不存在', code=404)  # 主键不存在时返回 404 业务错误
        return ok(build_report(tpl), '获取成功')  # 纯计算，不落生成记录

    @action(detail=True, methods=['post'])  # 路由：POST /rp/template/generate/<pk>/，按主键生成
    def generate(self, request, pk=None):  # 生成动作：会新增一条生成记录
        """手动生成报表：落生成记录并直接返回本次渲染结果。"""
        tpl = RpTemplate.objects.filter(pk=pk, is_deleted=0).first()  # 同上：模板必须存在且未删除
        if not tpl:  # 模板不存在
            return fail('模板不存在', code=404)  # 模板缺失则拒绝生成
        user = getattr(request, 'user_info', None)  # 认证中间件注入的当前用户（可能为空）
        now = time.strftime('%Y-%m-%d %H:%M:%S')  # 生成时间，统一字符串格式
        data = request.data or {}  # 请求体，兼容空请求
        param = data.get('param_json') or data.get('param') or ''  # 生成参数，两种字段名都兼容
        started = time.time()  # 渲染计时起点（秒）
        report = build_report(tpl)  # 先渲染数据，耗时计入生成记录
        cost = int((time.time() - started) * 1000)  # 耗时换算成毫秒
        record = RpGenerateRecord.objects.create(  # 写入一条生成记录
            template_id=tpl.id, template_name=tpl.template_name,  # 快照模板 ID 与名称，避免模板改名后记录失真
            param_json=str(param), gen_status=1, gen_type='manual',  # 参数文本、成功状态、触发方式=手工
            gen_user_id=getattr(user, 'id', None),  # 当前用户 ID，未登录时为空
            cost_time=max(cost, 1), gen_time=now,  # 耗时至少记 1ms，便于前端展示
            create_by=user.username if user else '', create_time=now,  # 审计：创建人/创建时间
            update_by=user.username if user else '', update_time=now, is_deleted=0,  # 审计：更新人/更新时间/未删除
        )
        report['record'] = RpGenerateRecordSerializer(record).data  # 把本次记录一并返回给前端
        return ok(report, '报表生成成功')  # 统一成功响应


class RpGenerateRecordViewSet(CrudViewSet):  # 报表生成记录视图集
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

    @action(detail=True, methods=['get'])  # 路由：GET /rp/record/preview/<pk>/，按记录回放
    def preview(self, request, pk=None):  # 回放动作：按记录快照重新渲染，不写库
        """按生成记录回放报表效果。"""
        record = self.get_queryset().filter(pk=pk).first()  # 复用基类的查询集（已处理权限与软删除）
        if not record:  # 记录不存在
            return fail('生成记录不存在', code=404)  # 记录缺失返回 404
        return ok(build_record_report(record), '获取成功')  # 用记录中快照的参数重新渲染
