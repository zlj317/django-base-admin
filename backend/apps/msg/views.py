"""消息模块视图集。"""
import time  # 生成阅读时间字符串

from rest_framework.decorators import action  # 自定义路由装饰器

from common.pagination import StandardPagination  # 统一分页
from common.response import fail, ok  # 统一响应封装
from common.views import CrudViewSet  # 通用 CRUD 基类

from apps.msg.models import MsgRecord, MsgPushConfig, MsgPushLog, MsgTemplate  # 消息相关模型
from apps.msg.serializers import (MsgPushConfigSerializer, MsgPushLogSerializer,  # 对应序列化器
                                  MsgRecordSerializer, MsgTemplateSerializer)


class MsgTemplateViewSet(CrudViewSet):
    """消息模板表 CRUD：管理消息模板。"""
    model = MsgTemplate  # 目标模型
    serializer_class = MsgTemplateSerializer  # 序列化器
    perm_prefix = 'msg'  # 权限前缀：msg:list/create/update/delete
    filter_map = {  # 支持的查询参数与 ORM lookup 映射
        'template_name': 'icontains',  # 模板名称模糊搜索
        'template_code': 'icontains',  # 模板编码模糊搜索
        'msg_type': 'exact',  # 消息类型精确匹配
        'status': 'exact',  # 状态精确匹配
    }
    order_by = '-id'  # 按主键倒序
    module_name = '消息模板'  # 操作日志模块名


class MsgRecordViewSet(CrudViewSet):
    """消息记录表 CRUD：管理消息记录。"""
    model = MsgRecord  # 目标模型
    serializer_class = MsgRecordSerializer  # 序列化器
    perm_prefix = 'msg'  # 权限前缀
    filter_map = {  # 支持的查询参数
        'title': 'icontains',  # 标题模糊搜索
        'msg_type': 'exact',  # 消息类型精确匹配
        'receiver_id': 'exact',  # 接收人精确匹配
        'is_read': 'exact',  # 是否已读精确匹配
    }
    order_by = '-id'  # 按主键倒序
    module_name = '消息记录'  # 操作日志模块名

    @action(detail=False, methods=['get'])
    def my(self, request):
        """我的消息：按当前登录用户 filter receiver_id 并分页。"""
        user = getattr(request, 'user_info', None)
        if not user or not getattr(user, 'id', None):
            return fail('未登录', code=401)
        queryset = self.apply_filters(
            MsgRecord.objects.filter(receiver_id=user.id, is_deleted=0).order_by('-id'),
            request)
        return StandardPagination(request).paginate(queryset, MsgRecordSerializer)

    @action(detail=True, methods=['post'])
    def read(self, request, pk=None):
        """标记单条消息为已读。"""
        affected = MsgRecord.objects.filter(pk=pk, is_deleted=0).update(
            is_read=1, read_time=time.strftime('%Y-%m-%d %H:%M:%S'))
        if not affected:
            return fail('消息不存在', code=404)
        return ok(None, '已标记为已读')

    @action(detail=False, methods=['post'])
    def read_all(self, request):
        """全部标记为已读。"""
        user = getattr(request, 'user_info', None)
        if not user or not getattr(user, 'id', None):
            return fail('未登录', code=401)
        affected = MsgRecord.objects.filter(
            receiver_id=user.id, is_read=0, is_deleted=0).update(
            is_read=1, read_time=time.strftime('%Y-%m-%d %H:%M:%S'))
        return ok({'count': affected}, '已全部标记为已读')


class MsgPushLogViewSet(CrudViewSet):
    """消息推送日志表 CRUD：已推送的消息日志。"""
    model = MsgPushLog  # 目标模型
    serializer_class = MsgPushLogSerializer  # 序列化器
    perm_prefix = 'msg'  # 权限前缀
    filter_map = {  # 支持的查询参数
        'channel': 'exact',  # 推送渠道精确匹配
        'push_status': 'exact',  # 推送状态精确匹配
        'receiver_id': 'exact',  # 接收人精确匹配
    }
    order_by = '-id'  # 按主键倒序
    module_name = '推送日志'  # 操作日志模块名

    def get_queryset(self):
        return self.model.objects.order_by(self.order_by)

    def list(self, request):
        """列表查询：MsgPushLog 不继承 BaseModel，直接用 filter_map 过滤。"""
        queryset = MsgPushLog.objects.all().order_by('-id')
        for param, lookup in self.filter_map.items():
            value = request.query_params.get(param)
            if value not in (None, ''):
                queryset = queryset.filter(**{f'{param}__{lookup}': value})
        return StandardPagination(request).paginate(queryset, MsgPushLogSerializer)


class MsgPushConfigViewSet(CrudViewSet):
    """消息推送配置表 CRUD：管理各渠道推送配置。"""
    model = MsgPushConfig  # 目标模型
    serializer_class = MsgPushConfigSerializer  # 序列化器
    perm_prefix = 'msg'  # 权限前缀
    filter_map = {  # 支持的查询参数
        'channel': 'exact',  # 渠道精确匹配
        'enabled': 'exact',  # 是否启用精确匹配
    }
    order_by = '-id'  # 按主键倒序
    module_name = '推送配置'  # 操作日志模块名
