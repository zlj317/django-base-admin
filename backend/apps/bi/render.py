"""大屏渲染：把 bi_screen.screen_config 解析成可展示的组件与数据。"""
# 文件：apps/bi/render.py —— 大屏渲染层
# 用途：读取大屏 screen_config，把组件配置与关联数据集转成前端可直接绘制的数据包。
# 数据表：读 bi_screen（由入参传入）、bi_dataset（组件引用的数据集）；写 bi_visit_log（访问日志）。
# 路由前缀：/api/bi/screen/preview/<pk> 与 /api/bi/screen/share/<token> 都会调用 build_screen / record_visit。
# 说明：配置缺失或数据集为空时由 common.chart_data 生成演示数据，本层不抛业务异常。
import datetime  # 访问日志时间
import time  # 生成更新时间

from apps.bi.models import BiDataset, BiVisitLog  # 大屏模型
from common.chart_data import build_chart_data, normalize_chart, parse_config  # 公共图表数据构建

# 大屏允许的组件类型白名单；不在其中的类型统一降级为柱状图，避免前端渲染未知组件
WIDGET_TYPES = ('kpi', 'bar', 'line', 'pie', 'gauge', 'rank', 'table', 'text')  # 大屏支持的组件类型
# 配置里没有 widgets 时的兜底布局，保证预览/分享页不会出现空白画布
DEFAULT_WIDGETS = [  # 配置为空时的兜底布局
    # 指标卡：展示核心数值
    {'type': 'kpi', 'title': '核心指标'},
    # 柱状图：展示销售趋势
    {'type': 'bar', 'title': '销售趋势'},
    # 饼图：展示渠道占比
    {'type': 'pie', 'title': '渠道占比'},
    # 排行榜：展示区域排行
    {'type': 'rank', 'title': '区域排行'},
]


# 计算单个组件的画布坐标：优先用配置值，否则按 4 列网格自动排布
def _geometry(widget, index, width):
    """组件定位：配置了坐标就用配置值，否则按 4 列网格自动排版。"""
    # 需要同时具备 x/y/w/h 四个坐标字段，才认为用户自定义了布局
    keys = ('x', 'y', 'w', 'h')
    # all(...)：任一字段缺失就落到下面的自动排版分支
    if all(widget.get(key) is not None for key in keys):
        # 配置值可能是字符串，统一转 int 后再返回给前端
        return {key: int(widget.get(key)) for key in keys}
    # 自动排版的几何参数：左右边距 24、卡片间距 20、每行 4 列、单行高 260
    margin, gap, columns, row_height = 24, 20, 4, 260  # 画布边距、间距、列数与行高
    # 先扣除两侧边距与列间距，再均分得到单元格宽度
    cell_width = round((width - 2 * margin - (columns - 1) * gap) / columns)
    # 取模得列号、整除得行号，实现从左到右、从上到下的顺序排布
    column, row = index % columns, index // columns
    # 返回计算后的坐标与尺寸，供前端绝对定位
    return {
        # 横向位置：左边距 + 列序号 ×（单元宽 + 间距）
        'x': margin + column * (cell_width + gap),
        'y': 100 + row * (row_height + gap),  # 顶部留出大屏标题区域
        # 组件宽高固定为单元格宽与行高
        'w': cell_width,
        'h': row_height,
    }


# 组装单个组件的数据：内联数据 > 数据集 > 演示数据，保证任何组件都有内容可画
def _widget_data(widget, index, seed, datasets):
    """单个组件的数据：优先组件内联数据，其次关联数据集，最后演示数据。"""
    # 归一化组件类型，未知类型交给 normalize_chart 的默认值 bar
    wtype = normalize_chart(widget.get('type'), 'bar')
    # 二次校验：不在白名单内的类型统一按柱状图处理
    if wtype not in WIDGET_TYPES:
        # 不支持的类型统一回退为柱状图
        wtype = 'bar'
    # 标题缺失时给空串，后续会按“组件N”补位
    title = str(widget.get('title') or '')
    # 内联数据必须是 dict 才可用，否则视为未配置
    inline = widget.get('data') if isinstance(widget.get('data'), dict) else {}
    # 按 dataset_id 在预加载的数据集字典中取对象；未配置则为 None，避免逐组件查库
    dataset = datasets.get(widget.get('dataset_id')) if widget.get('dataset_id') else None
    # 分支一：组件自带内联数据，直接用它构建图表
    if inline:
        # seed 加 index，让同一大屏内各组件生成的演示数据互不相同
        data = build_chart_data(inline, title, seed + index, wtype)
    # 分支二：没有内联数据但关联了数据集，解析数据集配置生成图表
    elif dataset:
        # parse_config 容错解析 JSON；数据集 ID 作为 seed，保证同一数据集结果稳定
        data = build_chart_data(parse_config(dataset.ds_config), dataset.dataset_name or title, dataset.id, wtype)
    # 分支三：既无内联数据也无数据集，用空配置生成演示数据，保证组件不空白
    else:
        # 标题为空时用“组件N”，方便在画布上定位
        data = build_chart_data({}, title or f'组件{index + 1}', seed + index, wtype)
    # 文本组件只需展示文字，不参与图表系列计算，单独组装最小结构
    if wtype == 'text':  # 文本组件不做图表计算
        # 文案优先级：配置 text > 组件标题 > 默认占位文案
        data = {'chart': 'text', 'text': str(inline.get('text') or title or '大屏文本内容'),
                # 维度/系列/明细/摘要全部置空，保持与其他图表一致的结构
                'categories': [], 'series': [], 'columns': [], 'rows': [], 'summary': [], 'source': 'config'}
    # 单位优先级：组件配置 > 图表自带的单位 > 空串
    unit = str(widget.get('unit') or data.get('unit') or '')
    # 把最终单位写回数据包，前端统一从 data.unit 读取
    data['unit'] = unit
    # 标记数据来源数据集名称；无数据集时为空串，前端可据此标记“演示数据”
    data['dataset_name'] = dataset.dataset_name if dataset else ''
    # 返回该组件的完整数据包
    return data


# 渲染入口：把整块大屏配置转换成前端可直接绘制的结构
def build_screen(screen):
    """构建大屏展示数据包：画布尺寸、背景、组件列表及各组件数据。"""
    # 容错解析 screen_config：可能为空、可能是非法 JSON，统一得到 dict
    cfg = parse_config(screen.screen_config)
    # 画布宽度：未配置时用 1920 这一常见大屏分辨率
    width = int(cfg.get('width') or 1920)
    # 画布高度：未配置时用 1080
    height = int(cfg.get('height') or 1080)
    # widgets 必须是数组才采用，否则视为未配置
    widgets = cfg.get('widgets') if isinstance(cfg.get('widgets'), list) else []
    # 没有有效组件时启用兜底布局，避免分享页空白
    if not widgets:
        # 没有有效组件时使用兜底布局
        widgets = DEFAULT_WIDGETS
    # 收集所有组件引用的数据集 ID，供下面一次性批量查询
    dataset_ids = [widget.get('dataset_id') for widget in widgets
                   if isinstance(widget, dict) and widget.get('dataset_id')]  # 组件引用的数据集，允许跨大屏复用
    # 单次 SQL 预加载数据集，构建 id → 对象 字典，避免 N+1 查询；只取未逻辑删除的记录
    datasets = {row.id: row for row in BiDataset.objects.filter(id__in=dataset_ids, is_deleted=0)}
    # 渲染后的组件数组
    payload_widgets = []
    # 逐个组件渲染；index 同时用于自动布局与演示数据种子
    for index, widget in enumerate(widgets):
        # 容错：配置数组里混入非 dict 项时直接跳过
        if not isinstance(widget, dict):
            # 非法配置项直接跳过，避免后续取值报错
            continue
        # 归一化组件类型，保证前端拿到已知类型
        wtype = normalize_chart(widget.get('type'), 'bar')
        # 再次校验白名单，不支持的类型降级为柱状图
        wtype = wtype if wtype in WIDGET_TYPES else 'bar'
        # 组装单个组件的输出结构
        payload_widgets.append({
            # 组件 ID：配置里没有时用 w{序号} 兜底，供前端做 key 与联动
            'id': str(widget.get('id') or f'w{index + 1}'),
            # 组件类型与标题；标题缺失时用“组件N”
            'type': wtype,
            # 标题统一成字符串，避免前端渲染数字时报错
            'title': str(widget.get('title') or f'组件{index + 1}'),
            # 副标题可为空串
            'subtitle': str(widget.get('subtitle') or ''),
            # 展开 _geometry 返回的 x/y/w/h 四个定位字段
            **_geometry(widget, index, width),
            # 原始单位配置，组件数据里还会再带一份解析后的单位
            'unit': str(widget.get('unit') or ''),
            # 组件数据：seed 用大屏 ID，保证同一大屏每次预览生成的数据一致
            'data': _widget_data(widget, index, screen.id or 0, datasets),
        })
    # 返回完整大屏数据包：元信息 + 画布参数 + 组件数组 + 更新时间
    return {
        # 大屏标识与名称，前端用于标题展示
        'screen_id': screen.id, 'screen_name': screen.screen_name,
        # 状态与自动刷新间隔（0 视为不自动刷新）
        'status': screen.status, 'refresh_sec': screen.refresh_sec or 0,
        # 分享链接与密码，当前直接返回给前端展示
        'share_url': screen.share_url or '', 'share_password': screen.share_password or '',
        # 画布宽高与背景色，前端按此建立画布
        'width': width, 'height': height, 'background': str(cfg.get('background') or ''),
        # 渲染后的组件数组与渲染时刻
        'widgets': payload_widgets, 'updated_at': time.strftime('%Y-%m-%d %H:%M:%S'),
    }


# 访问埋点：预览与分享访问都会调用，写入 bi_visit_log
def record_visit(screen, request=None):
    """写入大屏访问日志：记录访问用户与来源 IP。"""
    # 登录用户由中间件注入 request.user_info；匿名访问时为 None
    user = getattr(request, 'user_info', None) if request else None
    # 反向代理场景优先读 X-Forwarded-For，获取真实客户端 IP
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR') if request else None
    # 代理链形如 "ip1, ip2"，只取第一个；否则退回 REMOTE_ADDR；都取不到用空串
    ip = forwarded.split(',')[0].strip() if forwarded else (request.META.get('REMOTE_ADDR', '') if request else '')
    # 统一用本地时间记录访问时刻
    now = datetime.datetime.now()
    # 落库访问日志；该表不继承 BaseModel，故手工填 create_time
    BiVisitLog.objects.create(
        # 被访问的大屏 ID 与访问用户 ID（匿名时为空）
        screen_id=screen.id, visitor_user_id=getattr(user, 'id', None),
        # IP 截断到字段长度 50，避免超长写入失败；访问时间与入库时间相同
        visit_ip=(ip or '')[:50], visit_time=now, create_time=now,
    )
