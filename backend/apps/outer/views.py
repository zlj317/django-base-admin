"""外部接口模块视图集。"""
import json  # 解析请求头/参数 JSON
import time  # 耗时计算

from rest_framework.decorators import action  # 自定义路由装饰器

from common.pagination import StandardPagination  # 统一分页
from common.response import fail, ok  # 统一响应封装
from common.views import CrudViewSet  # 通用 CRUD 基类

from apps.outer.models import OuterApiConfig, OuterApiRequestLog, OuterSyncTask  # 外部接口相关模型
from apps.outer.serializers import (OuterApiConfigSerializer, OuterApiRequestLogSerializer,  # 对应序列化器
                                   OuterSyncTaskSerializer)


class OuterApiConfigViewSet(CrudViewSet):
    """外部API配置表 CRUD：管理可调用的外部接口。"""
    model = OuterApiConfig  # 目标模型
    serializer_class = OuterApiConfigSerializer  # 序列化器
    perm_prefix = 'outer'  # 权限前缀：outer:list/create/update/delete
    filter_map = {  # 支持的查询参数与 ORM lookup 映射
        'api_name': 'icontains',  # 接口名称模糊搜索
        'method': 'exact',  # 请求方法精确匹配
        'auth_type': 'exact',  # 鉴权方式精确匹配
        'status': 'exact',  # 状态精确匹配
    }
    order_by = '-id'  # 按主键倒序
    module_name = '外部API配置'  # 操作日志模块名

    def _do_request(self, config_obj, extra_params=None):
        """内部 helper：执行一次 HTTP 请求并写日志，返回 (ok_response 或 fail_response, http_code)。"""
        import urllib.request
        import urllib.error
        start = time.time()
        method = (config_obj.method or 'GET').upper()
        url = config_obj.api_url or ''
        headers = {}
        if config_obj.headers_json:
            try:
                headers = json.loads(config_obj.headers_json)
            except Exception:
                headers = {}
        data = {}
        if config_obj.params_json:
            try:
                data = json.loads(config_obj.params_json)
            except Exception:
                data = {}
        if extra_params:
            data.update(extra_params)
        if method in ('GET', 'DELETE') and data:
            from urllib.parse import urlencode, urlsplit, urlunsplit
            parts = urlsplit(url)
            qs = urlencode(data)
            sep = '&' if parts.query else '?'
            url = urlunsplit((parts.scheme, parts.netloc, parts.path,
                              parts.query + sep + qs, parts.fragment))
            body = None
        else:
            body = json.dumps(data).encode('utf-8') if data else None
        http_code = None
        resp_body = ''
        error_msg = ''
        try:
            req = urllib.request.Request(url, data=body, headers=headers, method=method)
            with urllib.request.urlopen(req, timeout=10) as resp:
                http_code = resp.status
                resp_body = resp.read().decode('utf-8', errors='replace')
        except urllib.error.HTTPError as e:
            http_code = e.code
            try:
                resp_body = e.read().decode('utf-8', errors='replace')
            except Exception:
                resp_body = ''
            error_msg = str(e.reason) if hasattr(e, 'reason') else str(e)
        except Exception as e:
            error_msg = str(e)
        cost_ms = int((time.time() - start) * 1000)
        now = time.strftime('%Y-%m-%d %H:%M:%S')
        OuterApiRequestLog.objects.create(
            api_id=config_obj.id, api_name=config_obj.api_name,
            request_url=url, request_param=json.dumps(data, ensure_ascii=False),
            response_body=resp_body, http_code=http_code,
            cost_time=cost_ms, error_msg=error_msg,
            request_time=now, create_time=now,
        )
        if http_code and 200 <= http_code < 300:
            return ok({'http_code': http_code, 'cost_ms': cost_ms,
                       'body': resp_body[:1000]}, '调用成功'), http_code
        return fail(f'调用失败: {error_msg or "HTTP " + str(http_code)}',
                    http_code or 0), http_code

    @action(detail=True, methods=['post'])
    def test(self, request, pk=None):
        """连通性测试：实际发起一次调用。"""
        row = OuterApiConfig.objects.filter(pk=pk, is_deleted=0).first()
        if not row:
            return fail('API 配置不存在', code=404)
        resp, _ = self._do_request(row)
        return resp

    @action(detail=True, methods=['post'])
    def call(self, request, pk=None):
        """正式调用：可由前端覆盖部分参数。"""
        row = OuterApiConfig.objects.filter(pk=pk, is_deleted=0).first()
        if not row:
            return fail('API 配置不存在', code=404)
        extra = (request.data or {}).get('params') or {}
        resp, _ = self._do_request(row, extra)
        return resp


class OuterApiRequestLogViewSet(CrudViewSet):
    """外部API调用日志表 CRUD：已发生的接口调用记录。"""
    model = OuterApiRequestLog  # 目标模型
    serializer_class = OuterApiRequestLogSerializer  # 序列化器
    perm_prefix = 'outer'  # 权限前缀
    filter_map = {  # 支持的查询参数
        'api_id': 'exact',  # API精确匹配
        'api_name': 'icontains',  # 接口名称模糊搜索
        'http_code': 'exact',  # HTTP 状态码精确匹配
    }
    order_by = '-id'  # 按主键倒序
    module_name = '外部API调用日志'  # 操作日志模块名

    def get_queryset(self):
        return self.model.objects.order_by(self.order_by)

    def list(self, request):
        """列表查询：OuterApiRequestLog 不继承 BaseModel。"""
        queryset = OuterApiRequestLog.objects.all().order_by('-id')
        for param, lookup in self.filter_map.items():
            value = request.query_params.get(param)
            if value not in (None, ''):
                queryset = queryset.filter(**{f'{param}__{lookup}': value})
        return StandardPagination(request).paginate(queryset, OuterApiRequestLogSerializer)


class OuterSyncTaskViewSet(CrudViewSet):
    """外部数据同步任务表 CRUD：管理同步任务定义。"""
    model = OuterSyncTask  # 目标模型
    serializer_class = OuterSyncTaskSerializer  # 序列化器
    perm_prefix = 'outer'  # 权限前缀
    filter_map = {  # 支持的查询参数
        'sync_name': 'icontains',  # 任务名称模糊搜索
        'api_id': 'exact',  # API精确匹配
        'target_table': 'icontains',  # 目标表模糊搜索
        'sync_type': 'exact',  # 同步方式精确匹配
        'status': 'exact',  # 状态精确匹配
    }
    order_by = '-id'  # 按主键倒序
    module_name = '外部数据同步'  # 操作日志模块名

    @action(detail=True, methods=['post'])
    def run_once(self, request, pk=None):
        """手动触发一次同步任务（占位）。"""
        row = OuterSyncTask.objects.filter(pk=pk, is_deleted=0).first()
        if not row:
            return fail('同步任务不存在', code=404)
        return ok(None, '同步任务已触发（演示：未实际拉取）')
