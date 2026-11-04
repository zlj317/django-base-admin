"""知识库模块视图集。"""
import datetime  # 统计今日新增文档

from django.db.models import Sum  # 汇总阅读次数

from common.response import ok  # 统一响应结构
from common.views import CrudViewSet  # 通用 CRUD 基类

from apps.kb.models import KBCategory, KBDocument, KBFavorite  # 知识库相关模型
from apps.kb.serializers import KBCategorySerializer, KBDocumentSerializer, KBFavoriteSerializer  # 对应序列化器


class KBCategoryViewSet(CrudViewSet):
    """知识库分类 CRUD。"""
    model = KBCategory
    serializer_class = KBCategorySerializer
    perm_prefix = 'kb'
    filter_map = {
        'category_name': 'icontains',
        'status': 'exact',
        'parent_id': 'exact',
    }
    order_by = 'sort'
    module_name = '文档分类'


class KBDocumentViewSet(CrudViewSet):
    """知识库文档 CRUD。"""
    model = KBDocument
    serializer_class = KBDocumentSerializer
    perm_prefix = 'kb'
    filter_map = {
        'doc_title': 'icontains',
        'category_id': 'exact',
        'status': 'exact',
        'author_id': 'exact',
    }
    order_by = '-id'
    module_name = '文档管理'

    def stats(self, request):
        """文档列表顶部统计：总数、今日新增、已发布、累计阅读。"""
        queryset = KBDocument.objects.filter(is_deleted=0)  # 只统计未删除文档
        today = datetime.date.today().strftime('%Y-%m-%d')
        total_reads = queryset.aggregate(total=Sum('read_count'))['total'] or 0  # 累计阅读量
        data = {
            'total_documents': queryset.count(),
            'today_new': queryset.filter(create_time__date=today).count(),
            'published': queryset.filter(status=1).count(),
            'total_reads': total_reads,
        }
        return ok(data)


class KBFavoriteViewSet(CrudViewSet):
    """知识收藏 CRUD（不继承 BaseModel，覆写 get_queryset）。"""
    model = KBFavorite
    serializer_class = KBFavoriteSerializer
    perm_prefix = 'kb'
    filter_map = {
        'doc_id': 'exact',
        'user_id': 'exact',
    }
    order_by = '-id'
    module_name = '知识收藏'

    def get_queryset(self):
        """KBFavorite 无 is_deleted 字段，直接返回全部。"""
        return KBFavorite.objects.order_by(self.order_by)
