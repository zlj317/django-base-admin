"""外部接口模块视图集。"""
# 模块用途：外部对接模块的 HTTP 接口层，提供接口配置 CRUD、连通性测试/正式调用、请求日志查询、同步任务 CRUD。
# 对应表：outer_api_config / outer_api_request_log / outer_sync_task，均由 docs 建表 SQL 手工创建（managed=False）。
# 路由前缀：/api/outer/，细分为 /api/outer/api/、/api/outer/log/、/api/outer/sync/。
# 权限：继承 CrudViewSet，perm_prefix='outer' 生成 outer:list/create/update/delete，由 PermissionCheck 校验。
# 现状：_do_request 会真实发起外部 HTTP 并写日志；run_once 仅为演示入口，不真正拉取数据，
#       同步任务通过 task_id 关联 task_info，尚未驱动报表或大屏。
import json  # 解析请求头/参数 JSON
import time  # 耗时计算

from rest_framework.decorators import action  # 自定义路由装饰器

from common.pagination import StandardPagination  # 统一分页
from common.response import fail, ok  # 统一响应封装
from common.views import CrudViewSet  # 通用 CRUD 基类

from apps.outer.models import OuterApiConfig, OuterApiRequestLog, OuterSyncTask  # 外部接口相关模型
from apps.outer.serializers import (OuterApiConfigSerializer, OuterApiRequestLogSerializer,  # 对应序列化器
                                   # 同步任务序列化器，用于任务定义的 CRUD 输出。
                                   OuterSyncTaskSerializer)


# 接口配置资源：标准 CRUD 由基类提供，额外动作 test/call/status 在 urls.py 中显式注册。
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

    # 出网核心：test 与 call 都走这里，集中处理参数拼装、超时、异常兜底与调用日志落库。
    def _do_request(self, config_obj, extra_params=None):
        """内部 helper：执行一次 HTTP 请求并写日志，返回 (ok_response 或 fail_response, http_code)。"""
        # 使用标准库 urllib 而非第三方 requests，项目无需新增依赖即可发起 HTTP 请求。
        import urllib.request
        # 单独导入 error 模块，用于区分 4xx/5xx（HTTPError）与其他网络异常。
        import urllib.error
        # 计时起点，最终换算为日志表的 cost_time（毫秒），用于评估外部接口性能。
        start = time.time()
        # 取出配置中的 HTTP 方法并统一转大写，兼容库里手工填写的小写值；为空时按 GET 兜底。
        method = (config_obj.method or 'GET').upper()
        # 接口地址来自配置；为空时请求阶段会抛异常，但仍会写一条失败日志便于排查。
        url = config_obj.api_url or ''
        # 请求头默认空字典，urllib 会自行补充 Host 等基础头。
        headers = {}
        # 请求头以 JSON 文本存储；解析失败时降级为空头，避免坏配置直接阻断调用流程。
        if config_obj.headers_json:
            # 尝试把 JSON 文本解析为请求头字典。
            try:
                headers = json.loads(config_obj.headers_json)
            # 解析失败不抛错，降级为无自定义请求头。
            except Exception:
                # 非法 JSON 不抛异常，按“无自定义请求头”处理，保证日志里能看到一次完整调用。
                headers = {}
        # 默认参数同样以 JSON 文本存储，后面会与前端传入的 extra_params 合并。
        data = {}
        # 参数 JSON 解析失败时保持空字典；配置错误由使用方自行修正，不影响本次调用记录。
        if config_obj.params_json:
            # 尝试解析配置中的默认参数。
            try:
                data = json.loads(config_obj.params_json)
            # 非法 JSON 按空参数处理，避免坏配置阻断调用。
            except Exception:
                # 保持空字典，后续仍可合并前端临时参数。
                data = {}
        # 正式调用可携带临时参数：同名键覆盖默认值，未传则完全沿用配置。
        if extra_params:
            # 用前端临时参数覆盖配置默认值（浅合并，键冲突时以入参为准）。
            data.update(extra_params)
        # GET/DELETE 没有请求体，参数必须拼到 URL 的查询串上；无参数时保持原地址不变。
        if method in ('GET', 'DELETE') and data:
            # 延迟导入：仅 URL 拼装分支需要，避免模块顶层引入无关符号。
            from urllib.parse import urlencode, urlsplit, urlunsplit
            # 解析原 URL，保留 scheme/netloc/path/fragment 等已有部分。
            parts = urlsplit(url)
            # 对参数做 URL 编码，避免中文、空格、& 等字符破坏查询串结构。
            qs = urlencode(data)
            # 原地址已有查询串时用 & 追加，否则用 ? 开始新的查询串。
            sep = '&' if parts.query else '?'
            # 重新拼装 URL：只替换查询串，scheme/netloc/path/fragment 保持原样。
            # urlunsplit 的第 4 个参数是完整 query，第 5 个保留原 fragment。
            url = urlunsplit((parts.scheme, parts.netloc, parts.path,
                              # 在原查询串后追加编码后的参数。
                              parts.query + sep + qs, parts.fragment))
            # GET/DELETE 不能带请求体，参数已经全部进入 URL。
            body = None
        # 非 GET/DELETE 走下面的请求体分支。
        else:
            # POST/PUT 等把参数序列化为 JSON 字节流；无参数时不发送 body。
            body = json.dumps(data).encode('utf-8') if data else None
        # 预先初始化结果字段，保证任何异常分支都能拼出一条完整日志。
        http_code = None
        # 响应体先置空，后续按实际返回覆盖。
        resp_body = ''
        # 错误信息同样先置空，成功时保持空串。
        error_msg = ''
        # 统一出网入口：req 的构造与发送放在同一个 try 内，所有网络异常都在下方兜底。
        try:
            # 按配置的方法、头、体构造 Request；headers 为空时 urllib 会补默认头。
            req = urllib.request.Request(url, data=body, headers=headers, method=method)
            # timeout=10 秒：外部接口不可用时快速失败，避免拖住当前 Django 请求线程。
            with urllib.request.urlopen(req, timeout=10) as resp:
                # 记录真实 HTTP 状态码，成功时用于判断是否 2xx。
                http_code = resp.status
                # 按 UTF-8 解码；errors='replace' 容忍非 UTF-8 响应，防止解码异常中断日志写入。
                resp_body = resp.read().decode('utf-8', errors='replace')
        # 4xx/5xx 会抛 HTTPError：仍要保留状态码和响应体，便于前端展示接口的真实返回。
        except urllib.error.HTTPError as e:
            # HTTPError.code 即真实 HTTP 状态码。
            http_code = e.code
            # 错误响应体也尽量读取，很多外部接口会在 4xx 里返回具体错误原因。
            try:
                resp_body = e.read().decode('utf-8', errors='replace')
            except Exception:
                # 响应体不可读（连接已断等）时置空，不阻断后续日志。
                resp_body = ''
            # reason 是状态短语（如 Bad Request）；没有该属性时退回完整异常文本。
            error_msg = str(e.reason) if hasattr(e, 'reason') else str(e)
        # 连接超时、DNS 失败、URL 非法等非 HTTP 异常统一兜底，避免接口直接 500。
        except Exception as e:
            # 保存异常文本（超时、DNS、URL 非法等），写入日志的 error_msg。
            error_msg = str(e)
        # 耗时换算为毫秒整数，对应日志表的 cost_time 字段。
        cost_ms = int((time.time() - start) * 1000)
        # 与手工建表 SQL 的 DATETIME 格式保持一致，直接存本地时间字符串。
        now = time.strftime('%Y-%m-%d %H:%M:%S')
        # 无论成功失败都写日志：这是排查外部接口问题的主要依据，也用于统计调用量。
        OuterApiRequestLog.objects.create(
            # 记录配置主键与名称快照；配置后续被改名也能看出当时调用的是哪个接口。
            api_id=config_obj.id, api_name=config_obj.api_name,
            # 实际请求地址与参数快照；ensure_ascii=False 保留中文，便于直接阅读。
            request_url=url, request_param=json.dumps(data, ensure_ascii=False),
            # 实际状态码与响应体（可能为空）。
            response_body=resp_body, http_code=http_code,
            # 耗时与错误详情，成功时 error_msg 为空串。
            cost_time=cost_ms, error_msg=error_msg,
            # 请求时刻与入库时刻，字段均为 DATETIME 类型。
            request_time=now, create_time=now,
        )
        # 只有存在状态码且在 2xx 区间才算调用成功；无状态码说明请求根本没发出去。
        if http_code and 200 <= http_code < 300:
            # 成功时返回状态码、耗时与响应体前 1000 字（截断避免超大响应撑爆前端）。
            return ok({'http_code': http_code, 'cost_ms': cost_ms,
                       'body': resp_body[:1000]}, '调用成功'), http_code
        # 失败时优先给出具体错误；没有错误文本则回退为 HTTP 状态码；无状态码时业务码为 0。
        return fail(f'调用失败: {error_msg or "HTTP " + str(http_code)}',
                    http_code or 0), http_code

    # 连通性测试：路由 POST /api/outer/api/test/<pk>/，按配置原样调用一次并写日志。
    @action(detail=True, methods=['post'])
    def test(self, request, pk=None):
        """连通性测试：实际发起一次调用。"""
        # 只允许操作未逻辑删除的配置，已删除配置不再对外发起请求。
        row = OuterApiConfig.objects.filter(pk=pk, is_deleted=0).first()
        if not row:
            # 主键不存在或被删除时返回业务 404，避免对空对象取值。
            return fail('API 配置不存在', code=404)
        # 测试不传额外参数，完全使用配置里的 URL、方法、请求头与默认参数。
        resp, _ = self._do_request(row)
        return resp

    # 正式调用：路由 POST /api/outer/api/call/<pk>/，允许前端临时覆盖部分参数。
    @action(detail=True, methods=['post'])
    def call(self, request, pk=None):
        """正式调用：可由前端覆盖部分参数。"""
        # 同样只在未删除的配置中查找。
        row = OuterApiConfig.objects.filter(pk=pk, is_deleted=0).first()
        if not row:
            return fail('API 配置不存在', code=404)
        # 取请求体中的 params 字段；未传或传 null 时退化为空字典。
        extra = (request.data or {}).get('params') or {}
        # 合并默认参数后统一出网；返回值中的 HTTP 码此处不消费，日志里已持久化。
        resp, _ = self._do_request(row, extra)
        return resp


# 调用日志资源：日志由 test/call 自动写入，前端主要做查询与清理，不提供新增/编辑动作。
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

    # 覆盖基类：日志表没有 is_deleted 列，不能再套用 is_deleted=0 过滤。
    def get_queryset(self):
        return self.model.objects.order_by(self.order_by)

    # 覆盖基类 list：改用不带逻辑删除过滤的查询集，并复用 filter_map 做筛选。
    def list(self, request):
        """列表查询：OuterApiRequestLog 不继承 BaseModel。"""
        # 全量日志按主键倒序，最新调用排在最前。
        queryset = OuterApiRequestLog.objects.all().order_by('-id')
        # 逐项读取白名单查询参数；空值视为未筛选，避免把结果过滤成空。
        for param, lookup in self.filter_map.items():
            value = request.query_params.get(param)
            if value not in (None, ''):
                # lookup 由类属性声明，不存在用户可控字段名注入风险。
                queryset = queryset.filter(**{f'{param}__{lookup}': value})
        # 统一分页输出，前端表格无需区分日志表与其他业务表。
        return StandardPagination(request).paginate(queryset, OuterApiRequestLogSerializer)


# 同步任务资源：当前仅管理任务定义与启停状态，不包含真实的数据同步执行逻辑。
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

    # 手动执行入口：虽定义为 action，但 urls.py 未注册路由，当前只能由代码直接调用。
    @action(detail=True, methods=['post'])
    def run_once(self, request, pk=None):
        """手动触发一次同步任务（占位）。"""
        # 只在未逻辑删除的任务中查找，已删除任务不再允许触发。
        row = OuterSyncTask.objects.filter(pk=pk, is_deleted=0).first()
        if not row:
            # 任务不存在时返回业务 404，避免空对象继续执行。
            return fail('同步任务不存在', code=404)
        # 演示实现：仅返回提示，不读取 api_id/sync_field_json，也不写入 target_table；
        # 任务与调度器的关系仅靠 task_id 关联 task_info，尚未真正驱动报表或大屏。
        return ok(None, '同步任务已触发（演示：未实际拉取）')
