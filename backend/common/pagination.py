"""统一分页：返回 {total, page, page_size, list}。"""
from django.conf import settings

from common.response import ok


class StandardPagination:
    """基于 request 查询参数的分页器。"""

    def __init__(self, request):
        try:
            self.page = max(int(request.query_params.get('page', 1)), 1)
        except (TypeError, ValueError):
            self.page = 1
        try:
            self.page_size = int(request.query_params.get('page_size', settings.PAGE_DEFAULT_SIZE))
        except (TypeError, ValueError):
            self.page_size = settings.PAGE_DEFAULT_SIZE
        self.page_size = min(max(self.page_size, 1), 1000)

    @property
    def offset(self):
        return (self.page - 1) * self.page_size

    def paginate(self, queryset, serializer_class=None, many=True):
        total = queryset.count()
        rows = queryset[self.offset:self.offset + self.page_size]
        data = {
            'total': total,
            'page': self.page,
            'page_size': self.page_size,
            'list': serializer_class(rows, many=many).data if serializer_class else list(rows),
        }
        return ok(data)
