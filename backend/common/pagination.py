"""统一分页：返回 {total, page, page_size, list}。"""
# 模块用途：为所有列表接口提供一致的分页入参解析与响应结构，前端只需维护一套表格分页逻辑。
# 被谁调用：common/views.py 的 CrudViewSet.list，以及各 apps 中手写列表视图。
# 关键约定：page 从 1 开始；page_size 上限 1000；返回体统一经 common.response.ok 包装成 {code, msg, data}。
from django.conf import settings  # 读取默认页大小配置

from common.response import ok  # 复用统一响应体，保证各接口分页结构一致


# 轻量分页器：只依赖 request.query_params，不依赖 DRF 全局分页配置，可在任意视图复用。
class StandardPagination:
    # docstring 写明入参来源与输出结构，前端联调时以此为准。
    """基于 request 查询参数的分页器。"""
    # 说明：没有直接使用 DRF 的 PageNumberPagination，因为项目响应结构是自定义的 {code,msg,data}，
    # 在视图里手动切片比改全局分页配置更可控，也不影响其余非分页接口。

    # 构造时即完成参数解析并挂到实例属性，后续 offset/paginate 直接复用，避免重复解析。
    def __init__(self, request):
        # 入参是 DRF 的 Request（含 query_params），解析结果只在本实例生命周期内使用。
        """解析 page / page_size 并做边界收敛，非法值回退默认值。"""
        # 页码解析：query_params 是 DRF 的 QueryDict，缺失时取默认 1；int() 也可能因 "abc" 抛 ValueError。
        try:
            self.page = max(int(request.query_params.get('page', 1)), 1)  # 页码至少为 1，防止出现负偏移
        except (TypeError, ValueError):
            self.page = 1  # 非数字时回退第一页，避免接口直接报错
        # 页大小解析：默认值来自 settings.PAGE_DEFAULT_SIZE，便于不同部署环境统一调整。
        try:
            self.page_size = int(request.query_params.get('page_size', settings.PAGE_DEFAULT_SIZE))  # 支持自定义
        except (TypeError, ValueError):
            self.page_size = settings.PAGE_DEFAULT_SIZE  # 非法值使用配置的默认条数
        # 上限保护：防止 page_size=999999 之类的请求把整张表读进内存拖垮服务。
        self.page_size = min(max(self.page_size, 1), 1000)  # 限制在 1~1000，防止一次拉取全表

    # 以属性形式暴露偏移量，手写 SQL 的位置也能复用同一套计算逻辑。
    @property
    # 每次访问都按当前 page/page_size 重新计算；分页参数在构造后不再变化，因此结果稳定。
    def offset(self):
        # 由 page/page_size 推导，无需调用方关心 limit/offset 的具体数值。
        """计算 SQL 偏移量，供 ORM 切片查询使用。"""
        # 供需要手写 SQL 或二次查询的位置复用，避免各处重复推导 (page-1)*page_size。
        return (self.page - 1) * self.page_size  # 页大小固定，偏移量等于前面所有页的条数

    # 分页核心：先 count 再切片，保证 total 准确且只把当前页数据加载到内存。
    def paginate(self, queryset, serializer_class=None, many=True):
        # serializer_class 为空时退化为 list(rows)，便于无需序列化的内部调用（如日志导出）。
        """统计总数并截取当前页，可选序列化后按统一结构返回。"""
        # count() 在切片前执行，Django 会据此生成独立 SELECT COUNT(*)，统计值不受后面的 LIMIT 影响。
        total = queryset.count()  # 先取总数，前端需要据此计算总页数
        # 对 QuerySet 切片等价于 SQL 的 LIMIT/OFFSET，只把当前页数据取回内存。
        rows = queryset[self.offset:self.offset + self.page_size]  # 只查当前页数据，避免全量加载
        # 四个字段名是前后端约定的分页协议，新增字段需要同步前端表格组件。
        data = {
            'total': total,  # 总记录数
            'page': self.page,  # 当前页码
            'page_size': self.page_size,  # 每页条数
            'list': serializer_class(rows, many=many).data if serializer_class else list(rows),  # 有序列化器则输出字典
        }
        # 统一包装：调用方（视图）直接 return，无需再关心响应格式。
        return ok(data)  # 统一包装成 {code, msg, data}
