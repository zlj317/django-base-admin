"""大屏BI模块视图集。"""
import uuid  # 分享链接

from rest_framework.decorators import action  # 自定义路由装饰器

from common.pagination import StandardPagination  # 统一分页
from common.response import fail, ok  # 统一响应封装
from common.views import CrudViewSet  # 通用 CRUD 基类

from apps.bi.models import BiDataset, BiScreen, BiVisitLog  # BI 相关模型
from apps.bi.render import build_screen, record_visit  # 大屏渲染数据
from apps.bi.serializers import BiDatasetSerializer, BiScreenSerializer, BiVisitLogSerializer  # 对应序列化器


class BiScreenViewSet(CrudViewSet):
    """大屏信息表 CRUD：管理可视化大屏。"""
    model = BiScreen  # 目标模型
    serializer_class = BiScreenSerializer  # 序列化器
    perm_prefix = 'bi'  # 权限前缀：bi:list/create/update/delete
    filter_map = {  # 支持的查询参数与 ORM lookup 映射
        'screen_name': 'icontains',  # 大屏名称模糊搜索
        'status': 'exact',  # 状态精确匹配
    }
    order_by = '-id'  # 按主键倒序
    module_name = '大屏管理'  # 操作日志模块名

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        """发布大屏：status=1 并生成 share_url。"""
        row = BiScreen.objects.filter(pk=pk, is_deleted=0).first()
        if not row:
            return fail('大屏不存在', code=404)
        user = getattr(request, 'user_info', None)
        row.status = 1
        row.share_url = f'/bi/share/{uuid.uuid4().hex}'
        row.save(update_fields=['status', 'share_url'])
        return ok(BiScreenSerializer(row).data, '发布成功')

    @action(detail=True, methods=['get'])
    def preview(self, request, pk=None):
        """大屏预览：返回画布配置与各组件数据，并记录一次访问。"""
        row = BiScreen.objects.filter(pk=pk, is_deleted=0).first()
        if not row:
            return fail('大屏不存在', code=404)
        record_visit(row, request)
        return ok(build_screen(row), '获取成功')

    @action(detail=False, methods=['get'])
    def share(self, request, token=None):
        """分享访问：按 share_url 中的 token 取已发布大屏。"""
        row = BiScreen.objects.filter(share_url__endswith=f'/{token}', status=1, is_deleted=0).first()
        if not row:
            return fail('分享链接无效或大屏未发布', code=404)
        record_visit(row, request)
        return ok(build_screen(row), '获取成功')


class BiDatasetViewSet(CrudViewSet):
    """大屏数据集表 CRUD：管理数据查询定义。"""
    model = BiDataset  # 目标模型
    serializer_class = BiDatasetSerializer  # 序列化器
    perm_prefix = 'bi'  # 权限前缀
    filter_map = {  # 支持的查询参数
        'dataset_name': 'icontains',  # 数据集名称模糊搜索
        'ds_type': 'exact',  # 数据源类型精确匹配
        'screen_id': 'exact',  # 所属大屏精确匹配
        'status': 'exact',  # 状态精确匹配
    }
    order_by = '-id'  # 按主键倒序
    module_name = '大屏数据集'  # 操作日志模块名

    def list(self, request):
        """列表查询：直接复用基类 apply_filters + 分页。"""
        queryset = self.apply_filters(self.get_queryset(), request)
        return StandardPagination(request).paginate(queryset, BiDatasetSerializer)


class BiVisitLogViewSet(CrudViewSet):
    """大屏访问日志表 CRUD：已产生的访问记录。"""
    model = BiVisitLog  # 目标模型
    serializer_class = BiVisitLogSerializer  # 序列化器
    perm_prefix = 'bi'  # 权限前缀
    filter_map = {  # 支持的查询参数
        'screen_id': 'exact',  # 大屏精确匹配
        'visitor_user_id': 'exact',  # 用户精确匹配
    }
    order_by = '-id'  # 按主键倒序
    module_name = '大屏访问日志'  # 操作日志模块名

    def get_queryset(self):
        return self.model.objects.order_by(self.order_by)

    def list(self, request):
        """列表查询：BiVisitLog 不继承 BaseModel，直接过滤。"""
        queryset = BiVisitLog.objects.all().order_by('-id')
        for param, lookup in self.filter_map.items():
            value = request.query_params.get(param)
            if value not in (None, ''):
                queryset = queryset.filter(**{f'{param}__{lookup}': value})
        return StandardPagination(request).paginate(queryset, BiVisitLogSerializer)
