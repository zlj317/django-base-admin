# 文件：apps/kb/views.py —— 知识库模块的视图集
# 用途：提供分类、文档、收藏的增删改查接口，并额外提供文档列表页顶部统计。
# 对应表：kb_category、kb_document、kb_favorite。
# 路由前缀：api/kb/category/、api/kb/document/、api/kb/favorite/（路径由 apps/kb/urls.py 生成）。
# 关键约定：CRUD 能力来自 common.views.CrudViewSet，基类统一做权限、分页、筛选与逻辑删除；
#           权限前缀为 kb；KBFavorite 不继承 BaseModel（无 is_deleted 列），必须覆写 get_queryset。
"""知识库模块视图集。"""
# 生成"今日"日期字符串，用于统计今日新增文档
import datetime  # 统计今日新增文档

# 聚合函数：把 read_count 求和得到累计阅读量
from django.db.models import Sum  # 汇总阅读次数

# 统一成功响应 {code, msg, data}
from common.response import ok  # 统一响应结构
from common.views import CrudViewSet  # 通用 CRUD 基类

# 分类/文档/收藏模型
from apps.kb.models import KBCategory, KBDocument, KBFavorite  # 知识库相关模型
from apps.kb.serializers import KBCategorySerializer, KBDocumentSerializer, KBFavoriteSerializer  # 对应序列化器


# 分类视图集：树形数据由前端按 parent_id 组装，这里只提供平铺的 CRUD
class KBCategoryViewSet(CrudViewSet):
    """知识库分类 CRUD。"""
    # 目标模型：分类表
    model = KBCategory
    # 序列化器：直出分类全部字段
    serializer_class = KBCategorySerializer
    # 权限前缀：拼成 kb:list / kb:create / kb:update / kb:delete
    perm_prefix = 'kb'
    # 查询参数白名单：分类名模糊、状态精确、父级精确
    filter_map = {
        # 分类名模糊搜索
        'category_name': 'icontains',
        # 按启用/停用状态过滤
        'status': 'exact',
        # 按父级过滤，前端可逐层懒加载子分类
        'parent_id': 'exact',
    }
    # 默认排序：sort 升序，与模型 Meta.ordering 的第一个字段保持一致
    order_by = 'sort'
    # 操作日志模块名
    module_name = '文档分类'


# 文档视图集：知识库的核心接口，额外提供列表页统计动作
class KBDocumentViewSet(CrudViewSet):
    """知识库文档 CRUD。"""
    # 目标模型：文档表
    model = KBDocument
    # 序列化器：直出文档全部字段（含正文与权限配置）
    serializer_class = KBDocumentSerializer
    # 权限前缀：与其他知识库资源共用 kb
    perm_prefix = 'kb'
    # 查询参数白名单：标题模糊，分类/状态/作者精确
    filter_map = {
        # 标题模糊搜索，作为关键字检索入口
        'doc_title': 'icontains',
        # 按所属分类过滤
        'category_id': 'exact',
        # 按已发布/草稿过滤
        'status': 'exact',
        # 按作者过滤，查看某人贡献的文档
        'author_id': 'exact',
    }
    # 默认排序：主键倒序，最新文档在前
    order_by = '-id'
    # 操作日志模块名
    module_name = '文档管理'

    # 统计动作：不通过 @action 装饰器，而是在 urls.py 的 extras 中显式映射 GET
    def stats(self, request):
        """文档列表顶部统计：总数、今日新增、已发布、累计阅读。"""
        # 先收敛到"未删除文档"，后续四个指标都基于同一查询集，口径一致
        queryset = KBDocument.objects.filter(is_deleted=0)  # 只统计未删除文档
        # create_time 是 DATETIME 列，__date 取日期部分再与字符串比较，可命中当天新增
        today = datetime.date.today().strftime('%Y-%m-%d')
        # aggregate 一次 SQL 完成求和；无记录时返回 None，用 or 0 兜底为数字
        total_reads = queryset.aggregate(total=Sum('read_count'))['total'] or 0  # 累计阅读量
        # 组装前端卡片需要的四个指标，字段名与前端约定保持一致
        data = {
            # 文档总数
            'total_documents': queryset.count(),
            # 今日新增：按 create_time 的日期部分比较
            'today_new': queryset.filter(create_time__date=today).count(),
            # 已发布数量：status=1
            'published': queryset.filter(status=1).count(),
            # 累计阅读次数：read_count 求和
            'total_reads': total_reads,
        }
        # 统一响应结构返回，前端直接取 data 渲染统计卡片
        return ok(data)


# 收藏视图集：结构同前两个，但模型没有逻辑删除列，需要覆写查询集
class KBFavoriteViewSet(CrudViewSet):
    """知识收藏 CRUD（不继承 BaseModel，覆写 get_queryset）。"""
    # 目标模型：收藏表（纯关系表，无审计字段与 is_deleted）
    model = KBFavorite
    # 序列化器：直出收藏记录全部字段
    serializer_class = KBFavoriteSerializer
    # 权限前缀：与其他知识库资源共用 kb
    perm_prefix = 'kb'
    # 查询参数白名单：按文档、按用户精确过滤
    filter_map = {
        # 查看某篇文档被谁收藏
        'doc_id': 'exact',
        # 查看某用户的收藏列表
        'user_id': 'exact',
    }
    # 默认排序：主键倒序，最新收藏在前
    order_by = '-id'
    # 操作日志模块名
    module_name = '知识收藏'

    # 覆写查询集：KBFavorite 没有 is_deleted 列，不能沿用基类默认的 is_deleted=0 过滤
    def get_queryset(self):
        """KBFavorite 无 is_deleted 字段，直接返回全部。"""
        # 直接按排序字段取全表；删除时基类会因缺少 is_deleted 转为物理删除
        return KBFavorite.objects.order_by(self.order_by)
