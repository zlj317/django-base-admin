"""大屏渲染：把 bi_screen.screen_config 解析成可展示的组件与数据。"""
import datetime  # 访问日志时间
import time  # 生成更新时间

from apps.bi.models import BiDataset, BiVisitLog  # 大屏模型
from common.chart_data import build_chart_data, normalize_chart, parse_config  # 公共图表数据构建

WIDGET_TYPES = ('kpi', 'bar', 'line', 'pie', 'gauge', 'rank', 'table', 'text')  # 大屏支持的组件类型
DEFAULT_WIDGETS = [  # 配置为空时的兜底布局
    {'type': 'kpi', 'title': '核心指标'},
    {'type': 'bar', 'title': '销售趋势'},
    {'type': 'pie', 'title': '渠道占比'},
    {'type': 'rank', 'title': '区域排行'},
]


def _geometry(widget, index, width):
    """组件定位：配置了坐标就用配置值，否则按 4 列网格自动排版。"""
    keys = ('x', 'y', 'w', 'h')
    if all(widget.get(key) is not None for key in keys):
        return {key: int(widget.get(key)) for key in keys}
    margin, gap, columns, row_height = 24, 20, 4, 260  # 画布边距、间距、列数与行高
    cell_width = round((width - 2 * margin - (columns - 1) * gap) / columns)
    column, row = index % columns, index // columns
    return {
        'x': margin + column * (cell_width + gap),
        'y': 100 + row * (row_height + gap),  # 顶部留出大屏标题区域
        'w': cell_width,
        'h': row_height,
    }


def _widget_data(widget, index, seed, datasets):
    """单个组件的数据：优先组件内联数据，其次关联数据集，最后演示数据。"""
    wtype = normalize_chart(widget.get('type'), 'bar')
    if wtype not in WIDGET_TYPES:
        wtype = 'bar'
    title = str(widget.get('title') or '')
    inline = widget.get('data') if isinstance(widget.get('data'), dict) else {}
    dataset = datasets.get(widget.get('dataset_id')) if widget.get('dataset_id') else None
    if inline:
        data = build_chart_data(inline, title, seed + index, wtype)
    elif dataset:
        data = build_chart_data(parse_config(dataset.ds_config), dataset.dataset_name or title, dataset.id, wtype)
    else:
        data = build_chart_data({}, title or f'组件{index + 1}', seed + index, wtype)
    if wtype == 'text':  # 文本组件不做图表计算
        data = {'chart': 'text', 'text': str(inline.get('text') or title or '大屏文本内容'),
                'categories': [], 'series': [], 'columns': [], 'rows': [], 'summary': [], 'source': 'config'}
    unit = str(widget.get('unit') or data.get('unit') or '')
    data['unit'] = unit
    data['dataset_name'] = dataset.dataset_name if dataset else ''
    return data


def build_screen(screen):
    """构建大屏展示数据包：画布尺寸、背景、组件列表及各组件数据。"""
    cfg = parse_config(screen.screen_config)
    width = int(cfg.get('width') or 1920)
    height = int(cfg.get('height') or 1080)
    widgets = cfg.get('widgets') if isinstance(cfg.get('widgets'), list) else []
    if not widgets:
        widgets = DEFAULT_WIDGETS
    dataset_ids = [widget.get('dataset_id') for widget in widgets
                   if isinstance(widget, dict) and widget.get('dataset_id')]  # 组件引用的数据集，允许跨大屏复用
    datasets = {row.id: row for row in BiDataset.objects.filter(id__in=dataset_ids, is_deleted=0)}
    payload_widgets = []
    for index, widget in enumerate(widgets):
        if not isinstance(widget, dict):
            continue
        wtype = normalize_chart(widget.get('type'), 'bar')
        wtype = wtype if wtype in WIDGET_TYPES else 'bar'
        payload_widgets.append({
            'id': str(widget.get('id') or f'w{index + 1}'),
            'type': wtype,
            'title': str(widget.get('title') or f'组件{index + 1}'),
            'subtitle': str(widget.get('subtitle') or ''),
            **_geometry(widget, index, width),
            'unit': str(widget.get('unit') or ''),
            'data': _widget_data(widget, index, screen.id or 0, datasets),
        })
    return {
        'screen_id': screen.id, 'screen_name': screen.screen_name,
        'status': screen.status, 'refresh_sec': screen.refresh_sec or 0,
        'share_url': screen.share_url or '', 'share_password': screen.share_password or '',
        'width': width, 'height': height, 'background': str(cfg.get('background') or ''),
        'widgets': payload_widgets, 'updated_at': time.strftime('%Y-%m-%d %H:%M:%S'),
    }


def record_visit(screen, request=None):
    """写入大屏访问日志：记录访问用户与来源 IP。"""
    user = getattr(request, 'user_info', None) if request else None
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR') if request else None
    ip = forwarded.split(',')[0].strip() if forwarded else (request.META.get('REMOTE_ADDR', '') if request else '')
    now = datetime.datetime.now()
    BiVisitLog.objects.create(
        screen_id=screen.id, visitor_user_id=getattr(user, 'id', None),
        visit_ip=(ip or '')[:50], visit_time=now, create_time=now,
    )
