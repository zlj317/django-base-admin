"""公告模块视图集。"""
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

    @action(detail=False, methods=['get'])
    def my(self, request):
        """我的可见公告：status=1、时间有效、角色范围包含当前用户或为空。"""
        now_str = time.strftime('%Y-%m-%d %H:%M:%S')
        qs = NoticeInfo.objects.filter(
            status=1, is_deleted=0,
        ).filter(
            models.Q(start_time__isnull=True) | models.Q(start_time__lte=now_str),
            models.Q(end_time__isnull=True) | models.Q(end_time__gte=now_str),
        ).order_by('-is_top', '-id')
        # 按 role_scope 过滤：空=全部可见；否则解析 JSON 数组，只要包含当前用户任一角色即可
        user = getattr(request, 'user_info', None)
        role_list = []
        if user and getattr(user, 'roles', None):
            role_list = list(user.roles)
        visible_ids = []
        for n in qs:
            scope = n.role_scope or ''
            if not scope.strip():
                visible_ids.append(n.id)
                continue
            try:
                scope_list = json.loads(scope)
            except Exception:
                scope_list = []
            if not scope_list:
                visible_ids.append(n.id)
                continue
            if any(r in scope_list for r in role_list):
                visible_ids.append(n.id)
        qs = qs.filter(id__in=visible_ids) if visible_ids else qs.none()
        # 支持搜索
        title_q = request.query_params.get('title')
        if title_q:
            qs = qs.filter(title__icontains=title_q)
        return StandardPagination(request).paginate(qs, NoticeInfoSerializer)

    @action(detail=True, methods=['put'])
    def publish(self, request, pk=None):
        """发布公告：置为已发布并记录发布人与发布时间。"""
        row = NoticeInfo.objects.filter(pk=pk, is_deleted=0).first()
        if not row:
            return fail('公告不存在', code=404)
        user = getattr(request, 'user_info', None)
        now = time.strftime('%Y-%m-%d %H:%M:%S')
        row.status = 1  # 1 = 已发布
        row.publish_user_id = getattr(user, 'id', None)
        row.publish_time = now
        row.save()
        return ok(NoticeInfoSerializer(row).data, '发布成功')

    @action(detail=True, methods=['put'])
    def offline(self, request, pk=None):
        """下线公告：置为已下线。"""
        row = NoticeInfo.objects.filter(pk=pk, is_deleted=0).first()
        if not row:
            return fail('公告不存在', code=404)
        row.status = 2  # 2 = 已下线
        row.save()
        return ok(NoticeInfoSerializer(row).data, '已下线')

    @action(detail=True, methods=['post'])
    def read(self, request, pk=None):
        """标记公告为已读（插入 notice_read，幂等）。"""
        row = NoticeInfo.objects.filter(pk=pk, is_deleted=0).first()
        if not row:
            return fail('公告不存在', code=404)
        user = getattr(request, 'user_info', None)
        if not user or not getattr(user, 'id', None):
            return fail('未登录', code=401)
        now = time.strftime('%Y-%m-%d %H:%M:%S')
        NoticeRead.objects.get_or_create(
            notice_id=pk, user_id=user.id,
            defaults={'read_time': now, 'create_time': now},
        )
        return ok(None, '已记录阅读')


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

    def get_queryset(self):
        return self.model.objects.order_by(self.order_by)
