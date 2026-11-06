"""公告模块视图集。"""
# 模块：apps/notice/views.py —— 公告模块的三个 ViewSet
# 用途：分类/公告/阅读记录的标准 CRUD，外加公告可见性过滤、发布、下线、标记已读等自定义动作。
# 对应表：notice_category、notice_info、notice_read
# 路由前缀：/api/notice/，具体路径由 apps/notice/urls.py 生成。
# 关键约定：权限前缀统一为 notice；列表按 is_deleted=0 过滤；时间字段以字符串写入手工 DATETIME 列。
import json  # role_scope JSON 解析
import time  # 阅读时间字符串

from django.db import models  # Q 查询
from rest_framework.decorators import action  # 自定义路由装饰器

from common.pagination import StandardPagination  # 统一分页
from common.response import fail, ok  # 统一响应封装
from common.views import CrudViewSet  # 通用 CRUD 基类

from apps.notice.models import NoticeCategory, NoticeInfo, NoticeRead  # 公告相关模型
from apps.notice.serializers import (NoticeCategorySerializer, NoticeInfoSerializer,  # 对应序列化器
                                     NoticeReadSerializer)


# 公告分类视图集：标准 CRUD，按排序号升序返回，支持名称/编码/状态筛选。
class NoticeCategoryViewSet(CrudViewSet):
    """公告分类表 CRUD：管理公告分类。"""
    model = NoticeCategory  # 目标模型
    serializer_class = NoticeCategorySerializer  # 序列化器
    perm_prefix = 'notice'  # 权限前缀：notice:list/create/update/delete
    filter_map = {  # 支持的查询参数与 ORM lookup 映射
        'category_name': 'icontains',  # 分类名称模糊搜索
        'category_code': 'icontains',  # 分类编码模糊搜索
        'status': 'exact',  # 状态精确匹配
    }
    order_by = 'sort'  # 按排序号升序
    module_name = '公告分类'  # 操作日志模块名


# 公告信息视图集：标准 CRUD 之外，提供当前用户可见列表、发布、下线、已读四个自定义动作。
class NoticeInfoViewSet(CrudViewSet):
    """公告信息表 CRUD：管理公告正文。"""
    model = NoticeInfo  # 目标模型
    serializer_class = NoticeInfoSerializer  # 序列化器
    perm_prefix = 'notice'  # 权限前缀
    filter_map = {  # 支持的查询参数
        'title': 'icontains',  # 标题模糊搜索
        'category_id': 'exact',  # 分类精确匹配
        'status': 'exact',  # 状态精确匹配
        'is_top': 'exact',  # 是否置顶精确匹配
    }
    order_by = '-id'  # 按主键倒序
    module_name = '公告信息'  # 操作日志模块名

    # detail=False：动作挂在集合级路由 /info/my 上，不需要主键。
    @action(detail=False, methods=['get'])
    def my(self, request):
        """我的可见公告：status=1、时间有效、角色范围包含当前用户或为空。"""
        # 统一时间字符串，用于与手工 DATETIME 列做比较（MySQL 会按字符串隐式转时间）。
        now_str = time.strftime('%Y-%m-%d %H:%M:%S')
        # 基础过滤：已发布(status=1) 且未被逻辑删除。
        qs = NoticeInfo.objects.filter(
            status=1, is_deleted=0,
        ).filter(
            # 生效窗口：开始时间为空视为立即生效；结束时间为空视为永久有效。
            models.Q(start_time__isnull=True) | models.Q(start_time__lte=now_str),
            models.Q(end_time__isnull=True) | models.Q(end_time__gte=now_str),
        # 置顶优先，其次按主键倒序（最新发布靠前），与模型 Meta 的默认排序保持一致。
        ).order_by('-is_top', '-id')
        # 按 role_scope 过滤：空=全部可见；否则解析 JSON 数组，只要包含当前用户任一角色即可
        # 当前登录用户由认证中间件注入 request.user_info，未登录时为 None。
        user = getattr(request, 'user_info', None)
        # 收集当前用户的角色编码列表，供 role_scope 逐个比对。
        role_list = []
        if user and getattr(user, 'roles', None):
            role_list = list(user.roles)
        # 先收集可见公告 ID，再一次性收敛查询集（避免在 Python 循环里做分页）。
        visible_ids = []
        for n in qs:
            # role_scope 为空串/空白视为不限角色，所有人可见。
            scope = n.role_scope or ''
            if not scope.strip():
                visible_ids.append(n.id)
                continue
            # 兼容脏数据：JSON 解析失败时降级为空范围，避免整条公告不可见。
            try:
                scope_list = json.loads(scope)
            except Exception:
                scope_list = []
            # 解析结果为空数组（如 "[]"）同样视为全员可见。
            if not scope_list:
                visible_ids.append(n.id)
                continue
            # 只要用户拥有其中任一角色，就允许看到该公告。
            if any(r in scope_list for r in role_list):
                visible_ids.append(n.id)
        # 用可见 ID 收敛结果；一条都不可见时返回空集，而不是放行全量。
        qs = qs.filter(id__in=visible_ids) if visible_ids else qs.none()
        # 支持搜索
        # 标题关键字模糊搜索：前端表格搜索框直接以 title 作为查询参数。
        title_q = request.query_params.get('title')
        if title_q:
            qs = qs.filter(title__icontains=title_q)
        # 走统一分页器，返回与其它列表接口一致的分页结构。
        return StandardPagination(request).paginate(qs, NoticeInfoSerializer)

    # 发布动作：PUT /info/publish/<pk>，把草稿置为已发布并记录发布人/时间。
    @action(detail=True, methods=['put'])
    def publish(self, request, pk=None):
        """发布公告：置为已发布并记录发布人与发布时间。"""
        # 只允许操作未逻辑删除的公告，避免已删数据被重新发布。
        row = NoticeInfo.objects.filter(pk=pk, is_deleted=0).first()
        if not row:
            return fail('公告不存在', code=404)
        # 取当前登录用户；发布人 ID 允许为空（例如定时任务代发）。
        user = getattr(request, 'user_info', None)
        # 统一时间字符串，与手工 DATETIME 列格式对齐。
        now = time.strftime('%Y-%m-%d %H:%M:%S')
        row.status = 1  # 1 = 已发布
        row.publish_user_id = getattr(user, 'id', None)
        row.publish_time = now
        row.save()
        # 返回更新后的完整公告，便于前端就地刷新状态与发布时间。
        return ok(NoticeInfoSerializer(row).data, '发布成功')

    # 下线动作：PUT /info/offline/<pk>，把已发布公告置为已下线。
    @action(detail=True, methods=['put'])
    def offline(self, request, pk=None):
        """下线公告：置为已下线。"""
        # 只允许操作未逻辑删除的公告。
        row = NoticeInfo.objects.filter(pk=pk, is_deleted=0).first()
        if not row:
            return fail('公告不存在', code=404)
        row.status = 2  # 2 = 已下线
        row.save()
        # 返回更新后的公告详情，前端据此刷新列表状态。
        return ok(NoticeInfoSerializer(row).data, '已下线')

    # 已读动作：POST /info/read/<pk>，向 notice_read 写入一条阅读记录。
    @action(detail=True, methods=['post'])
    def read(self, request, pk=None):
        """标记公告为已读（插入 notice_read，幂等）。"""
        # 只允许对未删除的公告打已读标记。
        row = NoticeInfo.objects.filter(pk=pk, is_deleted=0).first()
        if not row:
            return fail('公告不存在', code=404)
        # 阅读记录必须归属到具体用户，未登录直接拒绝。
        user = getattr(request, 'user_info', None)
        if not user or not getattr(user, 'id', None):
            return fail('未登录', code=401)
        # 阅读时间与创建时间取同一时刻，保持语义一致。
        now = time.strftime('%Y-%m-%d %H:%M:%S')
        # get_or_create 保证同一用户对同一公告只有一条记录，重复点击不会报唯一键冲突。
        NoticeRead.objects.get_or_create(
            notice_id=pk, user_id=user.id,
            defaults={'read_time': now, 'create_time': now},
        )
        # 阅读记录无业务返回体，只回传统一成功结构。
        return ok(None, '已记录阅读')


# 公告阅读记录视图集：以只读查询为主，供后台查看每条公告的阅读明细。
class NoticeReadViewSet(CrudViewSet):
    """公告阅读记录表 CRUD：已阅读的公告记录。"""
    model = NoticeRead  # 目标模型
    serializer_class = NoticeReadSerializer  # 序列化器
    perm_prefix = 'notice'  # 权限前缀
    filter_map = {  # 支持的查询参数
        'notice_id': 'exact',  # 公告精确匹配
        'user_id': 'exact',  # 用户精确匹配
    }
    order_by = '-id'  # 按主键倒序
    module_name = '公告阅读记录'  # 操作日志模块名

    # 阅读记录表没有 is_deleted 字段，因此不附加逻辑删除条件，直接按主键倒序返回全部。
    def get_queryset(self):
        return self.model.objects.order_by(self.order_by)
