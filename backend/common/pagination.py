"""统一分页：返回 {total, page, page_size, list}。"""
from django.conf import settings  # 读取默认页大小配置

from common.response import ok  # 复用统一响应体，保证各接口分页结构一致


class StandardPagination:
    """基于 request 查询参数的分页器。"""

    def __init__(self, request):
        """解析 page / page_size 并做边界收敛，非法值回退默认值。"""
        try:
            self.page = max(int(request.query_params.get('page', 1)), 1)  # 页码至少为 1，防止出现负偏移
        except (TypeError, ValueError):
            self.page = 1  # 非数字时回退第一页，避免接口直接报错
        try:
            self.page_size = int(request.query_params.get('page_size', settings.PAGE_DEFAULT_SIZE))  # 支持自定义
        except (TypeError, ValueError):
            self.page_size = settings.PAGE_DEFAULT_SIZE  # 非法值使用配置的默认条数
        self.page_size = min(max(self.page_size, 1), 1000)  # 限制在 1~1000，防止一次拉取全表

    @property
    def offset(self):
        """计算 SQL 偏移量，供 ORM 切片查询使用。"""
        return (self.page - 1) * self.page_size  # 页大小固定，偏移量等于前面所有页的条数

    def paginate(self, queryset, serializer_class=None, many=True):
        """统计总数并截取当前页，可选序列化后按统一结构返回。"""
        total = queryset.count()  # 先取总数，前端需要据此计算总页数
        rows = queryset[self.offset:self.offset + self.page_size]  # 只查当前页数据，避免全量加载
        data = {
            'total': total,  # 总记录数
            'page': self.page,  # 当前页码
            'page_size': self.page_size,  # 每页条数
            'list': serializer_class(rows, many=many).data if serializer_class else list(rows),  # 有序列化器则输出字典
        }
        return ok(data)  # 统一包装成 {code, msg, data}
