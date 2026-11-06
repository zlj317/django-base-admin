"""大屏BI模块视图集。"""
# 文件：apps/bi/views.py —— 大屏 BI 模块的视图层
# 用途：提供大屏 CRUD、发布、预览、分享访问，以及数据集与访问日志的列表/增删改接口。
# 数据表：bi_screen（大屏）、bi_dataset（数据集）、bi_visit_log（访问日志）。
# 路由前缀：/api/bi/screen、/api/bi/dataset、/api/bi/visit，分享入口 /api/bi/screen/share/<token>。
# 说明：基础增删改查由 common.views.CrudViewSet 提供，本文件只补业务动作与日志表的分页查询。
import uuid  # 分享链接

from rest_framework.decorators import action  # 自定义路由装饰器

from common.pagination import StandardPagination  # 统一分页
from common.response import fail, ok  # 统一响应封装
from common.views import CrudViewSet  # 通用 CRUD 基类

from apps.bi.models import BiDataset, BiScreen, BiVisitLog  # BI 相关模型
from apps.bi.render import build_screen, record_visit  # 大屏渲染数据
from apps.bi.serializers import BiDatasetSerializer, BiScreenSerializer, BiVisitLogSerializer  # 对应序列化器


# 大屏视图集：基类提供 list/create/update/delete，这里扩展 publish / preview / share
class BiScreenViewSet(CrudViewSet):
    """大屏信息表 CRUD：管理可视化大屏。"""
    # 目标模型：基类的 get_queryset/create/update/delete 都基于它
    model = BiScreen  # 目标模型
    # 输入输出序列化器
    serializer_class = BiScreenSerializer  # 序列化器
    # 权限前缀：拼出 bi:list / bi:create / bi:update / bi:delete
    perm_prefix = 'bi'  # 权限前缀：bi:list/create/update/delete
    # 支持的查询参数 → ORM lookup；未声明的查询参数会被忽略
    filter_map = {  # 支持的查询参数与 ORM lookup 映射
        # 按名称模糊搜索（大小写不敏感）
        'screen_name': 'icontains',  # 大屏名称模糊搜索
        # 按状态精确匹配（0 草稿 / 1 已发布 / 2 已下线）
        'status': 'exact',  # 状态精确匹配
    }
    # 列表默认排序：主键倒序，最新的大屏在最前
    order_by = '-id'  # 按主键倒序
    # 操作日志中的模块名
    module_name = '大屏管理'  # 操作日志模块名

    # 发布动作：POST /api/bi/screen/publish/<pk>，把大屏置为已发布并生成分享地址
    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        """发布大屏：status=1 并生成 share_url。"""
        # 只允许发布未逻辑删除的大屏；pk 来自路由的 <int:pk>
        row = BiScreen.objects.filter(pk=pk, is_deleted=0).first()
        # 记录不存在（可能已被删除）时返回业务码 404
        if not row:
            return fail('大屏不存在', code=404)
        # 取当前操作人（当前仅取值，未写入审计字段）
        user = getattr(request, 'user_info', None)
        # 状态置为 1（已发布），此后可被分享链接访问
        row.status = 1
        # 生成随机分享地址：uuid4().hex 去掉横线，便于在 URL 中传递
        row.share_url = f'/bi/share/{uuid.uuid4().hex}'
        # 只更新这两列，避免把 screen_config 等其他字段整体回写
        row.save(update_fields=['status', 'share_url'])
        # 返回发布后的完整大屏对象，前端可直接刷新分享链接
        return ok(BiScreenSerializer(row).data, '发布成功')

    # 预览动作：GET /api/bi/screen/preview/<pk>，返回画布数据并记录一次访问
    @action(detail=True, methods=['get'])
    def preview(self, request, pk=None):
        """大屏预览：返回画布配置与各组件数据，并记录一次访问。"""
        # 只预览未逻辑删除的大屏
        row = BiScreen.objects.filter(pk=pk, is_deleted=0).first()
        # 大屏不存在时直接返回 404，此时不写访问日志
        if not row:
            return fail('大屏不存在', code=404)
        # 渲染前先埋点：预览也计入访问统计
        record_visit(row, request)
        # build_screen 负责解析 screen_config 并组装各组件的定位与数据
        return ok(build_screen(row), '获取成功')

    # 分享动作：GET /api/bi/screen/share/<token>，供未登录用户访问已发布大屏
    @action(detail=False, methods=['get'])
    def share(self, request, token=None):
        """分享访问：按 share_url 中的 token 取已发布大屏。"""
        # 用 endswith 匹配 token，避免 share_url 保存完整域名时无法匹配；同时限制必须是已发布状态
        row = BiScreen.objects.filter(share_url__endswith=f'/{token}', status=1, is_deleted=0).first()
        # 链接无效/大屏未发布/已删除都统一提示，不向前端暴露具体原因
        if not row:
            return fail('分享链接无效或大屏未发布', code=404)
        # 分享访问同样写入访问日志，与预览口径一致
        record_visit(row, request)
        # 返回与预览一致的数据包，前端共用同一套渲染逻辑
        return ok(build_screen(row), '获取成功')


# 数据集视图集：基类提供标准 CRUD，本类仅覆盖 list
class BiDatasetViewSet(CrudViewSet):
    """大屏数据集表 CRUD：管理数据查询定义。"""
    # 目标模型
    model = BiDataset  # 目标模型
    # 输入输出序列化器
    serializer_class = BiDatasetSerializer  # 序列化器
    # 权限前缀：拼出 bi:list / bi:create / bi:update / bi:delete
    perm_prefix = 'bi'  # 权限前缀
    # 支持的查询参数 → ORM lookup
    filter_map = {  # 支持的查询参数
        # 按数据集名称模糊搜索
        'dataset_name': 'icontains',  # 数据集名称模糊搜索
        # 按数据源类型精确匹配（mysql / api）
        'ds_type': 'exact',  # 数据源类型精确匹配
        # 按所属大屏精确匹配
        'screen_id': 'exact',  # 所属大屏精确匹配
        # 按状态精确匹配（0 正常 / 1 停用）
        'status': 'exact',  # 状态精确匹配
    }
    # 列表默认排序：主键倒序
    order_by = '-id'  # 按主键倒序
    # 操作日志中的模块名
    module_name = '大屏数据集'  # 操作日志模块名

    # 覆盖基类 list：显式走 apply_filters + 标准分页，保持筛选与分页结构与前端约定一致
    def list(self, request):
        """列表查询：直接复用基类 apply_filters + 分页。"""
        # 先过滤：get_queryset 已排除逻辑删除记录，apply_filters 再叠加查询参数
        queryset = self.apply_filters(self.get_queryset(), request)
        # 统一输出 {total, page, page_size, list}
        return StandardPagination(request).paginate(queryset, BiDatasetSerializer)


# 访问日志视图集：日志表不继承 BaseModel，需绕开基类的 is_deleted 过滤
class BiVisitLogViewSet(CrudViewSet):
    """大屏访问日志表 CRUD：已产生的访问记录。"""
    # 目标模型
    model = BiVisitLog  # 目标模型
    # 输入输出序列化器
    serializer_class = BiVisitLogSerializer  # 序列化器
    # 权限前缀：拼出 bi:list / bi:create / bi:update / bi:delete
    perm_prefix = 'bi'  # 权限前缀
    # 支持的查询参数 → ORM lookup
    filter_map = {  # 支持的查询参数
        # 按大屏 ID 精确匹配
        'screen_id': 'exact',  # 大屏精确匹配
        # 按访问用户 ID 精确匹配
        'visitor_user_id': 'exact',  # 用户精确匹配
    }
    # 列表默认排序：主键倒序，最新访问在前
    order_by = '-id'  # 按主键倒序
    # 操作日志中的模块名
    module_name = '大屏访问日志'  # 操作日志模块名

    # 覆盖基类 get_queryset：日志表没有 is_deleted 列，不能套用逻辑删除过滤
    def get_queryset(self):
        return self.model.objects.order_by(self.order_by)

    # 覆盖基类 list：手工实现过滤，避免基类假设模型存在 is_deleted 字段
    def list(self, request):
        """列表查询：BiVisitLog 不继承 BaseModel，直接过滤。"""
        # 全量查询并按主键倒序（日志表无逻辑删除列）
        queryset = BiVisitLog.objects.all().order_by('-id')
        # 逐个参数拼接过滤条件，空值视为未筛选
        for param, lookup in self.filter_map.items():
            # 取前端传入的筛选值
            value = request.query_params.get(param)
            # None / 空串都不参与过滤，避免误把结果集过滤成空
            if value not in (None, ''):
                # 动态拼接 ORM 查询；param 来自白名单 filter_map，不存在注入风险
                queryset = queryset.filter(**{f'{param}__{lookup}': value})
        # 分页 + 序列化，返回统一结构
        return StandardPagination(request).paginate(queryset, BiVisitLogSerializer)
