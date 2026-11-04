"""图表数据辅助：配置解析、只读 SQL 执行与演示数据生成。

报表预览与大屏渲染共用本模块，取数优先级：
1. 配置中直接给出的 categories/series/rows/value；
2. 配置中的只读 SQL（仅单条 SELECT，执行失败时忽略）；
3. 按图表类型生成的确定性演示数据（同一模板每次结果一致）。
"""
import json  # 解析 TEXT 字段里的 JSON 配置
import random  # 演示数据需要稳定可复现

from django.db import connection  # 只读 SQL 复用项目默认数据库连接

CHART_ALIASES = {  # 常见配置别名 → 前端组件支持的图表类型
    'column': 'bar', 'area': 'line', 'donut': 'pie', 'ring': 'pie',
    'grid': 'table', 'map': 'rank', 'list': 'rank', 'ranking': 'rank',
    'stats': 'kpi', 'cards': 'kpi', 'number': 'kpi', 'dashboard': 'gauge',
}
CHART_TYPES = ('bar', 'line', 'pie', 'table', 'kpi', 'gauge', 'rank')  # 组件可渲染的类型
BLOCK_WORDS = ('insert ', 'update ', 'delete ', 'drop ', 'alter ', 'create ', 'truncate ', 'grant ')  # 只读 SQL 禁止出现的写操作


def parse_config(text):
    """把 TEXT 字段中的 JSON 转成 dict；非法内容一律视为空配置。"""
    if not text:
        return {}
    try:
        data = json.loads(text)
    except (TypeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def normalize_chart(value, default='bar'):
    """图表类型归一化：别名映射后校验，非法值回退默认类型。"""
    key = CHART_ALIASES.get(str(value or '').strip().lower(), str(value or '').strip().lower())
    return key if key in CHART_TYPES else default


def to_number(value):
    """转数值：非数字按 0 处理，整数去掉小数部分便于展示。"""
    try:
        num = float(value)
    except (TypeError, ValueError):
        return 0
    return int(num) if num == int(num) else round(num, 2)


def jsonable(value):
    """把 datetime/decimal 等不可 JSON 序列化的值转成文本。"""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def run_readonly_sql(sql, limit=100):
    """执行只读 SQL：仅允许单条 SELECT，失败或无结果返回 None。"""
    if not isinstance(sql, str):
        return None
    text = sql.strip().rstrip(';').strip()  # 去掉首尾空白与结尾分号
    lowered = text.lower()
    if not lowered.startswith('select') or ';' in text:  # 只读且只允许单条语句
        return None
    if any(word in f' {lowered} ' for word in BLOCK_WORDS):  # 含写关键字直接拒绝
        return None
    try:
        with connection.cursor() as cursor:
            cursor.execute(text)
            columns = [str(col[0]) for col in cursor.description or []]
            values = cursor.fetchmany(limit)
    except Exception:  # 数据源表不存在或 SQL 不合法时静默退回演示数据
        return None
    if not columns or not values:
        return None
    rows = [{col: jsonable(val) for col, val in zip(columns, row)} for row in values]
    return {'columns': [{'prop': col, 'label': col} for col in columns], 'rows': rows}


def normalize_columns(raw):
    """列定义归一化：支持字符串与 {prop,label} 两种写法。"""
    columns = []
    for item in raw if isinstance(raw, list) else []:
        if isinstance(item, dict) and item.get('prop'):
            columns.append({'prop': str(item['prop']), 'label': str(item.get('label') or item['prop'])})
        elif isinstance(item, str):
            columns.append({'prop': item, 'label': item})
    return columns


def normalize_series(raw):
    """系列定义归一化：过滤非数值数据，保证前端可直接绘制。"""
    series = []
    for item in raw if isinstance(raw, list) else []:
        if not isinstance(item, dict) or not isinstance(item.get('data'), list):
            continue
        name = str(item.get('name') or f'系列{len(series) + 1}')
        series.append({'name': name, 'data': [to_number(v) for v in item['data']]})
    return series


def rows_to_chart(rows, columns):
    """二维表 → categories + series：首列作维度，其余列作数值指标。"""
    if not rows or len(columns) < 2 or not isinstance(rows[0], dict):
        return None
    dimension = columns[0]['prop']
    categories = [str(row.get(dimension, '')) for row in rows]
    series = [
        {'name': col['label'], 'data': [to_number(row.get(col['prop'])) for row in rows]}
        for col in columns[1:]
    ]
    return {'categories': categories, 'series': series}


def demo_categories(title='', pie=False):
    """按标题关键词选择演示维度，尽量贴近报表语义。"""
    if '区域' in title:
        return ['华东', '华南', '华北', '西南', '东北']
    if any(key in title for key in ('库存', '商品', '品类', '周转')):
        return ['3C数码', '家用电器', '服饰鞋帽', '食品饮料', '美妆个护']
    if '客户' in title:
        return ['Q1', 'Q2', 'Q3', 'Q4']
    if pie:
        return ['直营渠道', '经销渠道', '电商渠道', '门店渠道', '其他渠道']
    return [f'{i}月' for i in range(1, 13)]


def demo_chart(chart, seed, title=''):
    """按图表类型生成确定性演示数据，保证同一模板每次预览一致。"""
    rnd = random.Random(f'{seed}-{chart}')  # 以模板/组件 ID 作种子
    if chart == 'gauge':
        return {'categories': [], 'series': [{'name': '完成率', 'data': [rnd.randint(45, 95)]}]}
    categories = demo_categories(title, pie=chart == 'pie')
    base = rnd.randint(60, 160)
    step = rnd.uniform(0.02, 0.09)
    first = [max(6, round(base * (1 + step * i) + rnd.uniform(-base * 0.16, base * 0.16)))
             for i in range(len(categories))]  # 整体缓慢上升，接近真实业务趋势
    second = [max(4, round(value * rnd.uniform(0.32, 0.62))) for value in first]
    if chart == 'pie':
        return {'categories': categories, 'series': [{'name': _value_name(title), 'data': first}]}
    names = ('销售额', '订单量')  # 默认双指标
    if '客户' in title:
        names = ('新增客户', '活跃客户')
    elif any(key in title for key in ('库存', '周转')):
        names = ('库存量', '周转天数')
    elif '率' in title:
        names = ('本期完成率', '上期完成率')
    return {'categories': categories,
            'series': [{'name': names[0], 'data': first}, {'name': names[1], 'data': second}]}


def _value_name(title):
    """根据标题猜一个适合饼图的值名称。"""
    if any(key in title for key in ('销售', '营收', '金额')):
        return '销售额'
    if '订单' in title:
        return '订单量'
    return '数量'


def demo_table(seed, title='', rows_count=6):
    """生成确定性的演示明细表，按库存/销售语义给出不同列。"""
    rnd = random.Random(f'{seed}-table')
    if any(key in title for key in ('库存', '商品')):
        columns = [{'prop': 'goods', 'label': '商品名称'}, {'prop': 'qty', 'label': '库存数量'},
                   {'prop': 'safe', 'label': '安全库存'}, {'prop': 'state', 'label': '状态'}]
        rows = []
        for index in range(rows_count):
            safe = rnd.randint(10, 60)
            qty = rnd.randint(0, safe + 40)
            rows.append({'goods': f'商品-{chr(65 + index)}', 'qty': qty, 'safe': safe,
                         'state': '预警' if qty < safe else '正常'})
        return {'columns': columns, 'rows': rows}
    columns = [{'prop': 'month', 'label': '月份'}, {'prop': 'orders', 'label': '订单数'},
               {'prop': 'amount', 'label': '销售额'}, {'prop': 'rate', 'label': '同比'}]
    rows = [{'month': f'{index}月', 'orders': rnd.randint(200, 900), 'amount': rnd.randint(8000, 60000),
             'rate': f'{rnd.randint(-8, 36)}%'} for index in range(1, rows_count + 1)]
    return {'columns': columns, 'rows': rows}


def demo_value(seed, title='', unit=''):
    """按单位/标题生成一个量级合理的演示指标值。"""
    rnd = random.Random(f'{seed}-value')
    if unit == '元' or any(key in title for key in ('销售', '营收', '金额')):
        return rnd.randint(100000, 999999)
    if unit == '单' or '订单' in title:
        return rnd.randint(1000, 9999)
    return rnd.randint(10, 999)


def build_summary(categories, series, unit=''):
    """根据首个系列生成合计/峰值/均值等摘要指标，供预览页展示。"""
    if not series:
        return []
    values = [to_number(value) for value in series[0].get('data') or []]
    if not values:
        return []
    total = sum(values)
    peak = max(values)
    peak_index = values.index(peak)
    peak_dimension = categories[peak_index] if peak_index < len(categories) else ''
    return [
        {'label': f'{series[0].get("name") or "合计"}合计', 'value': f'{total:,.0f}', 'unit': unit},
        {'label': '峰值', 'value': f'{peak:,.0f}', 'unit': unit},
        {'label': '峰值维度', 'value': peak_dimension or '-', 'unit': ''},
        {'label': '平均值', 'value': f'{total / len(values):,.0f}', 'unit': unit},
    ]


def build_chart_data(cfg, title='', seed=0, default='bar'):
    """把任意配置（含空配置）整理成统一的图表数据包。"""
    chart = normalize_chart(cfg.get('chart') or cfg.get('chart_type'), default)
    unit = str(cfg.get('unit') or '')
    value = cfg.get('value')
    categories = [str(item) for item in (cfg.get('categories') or []) if item is not None]
    series = normalize_series(cfg.get('series'))
    columns = normalize_columns(cfg.get('columns'))
    raw_rows = cfg.get('rows') if isinstance(cfg.get('rows'), list) else cfg.get('data')
    rows = raw_rows if isinstance(raw_rows, list) else []
    source = 'config'
    if rows and not columns and isinstance(rows[0], dict):
        columns = [{'prop': key, 'label': key} for key in rows[0].keys()]  # 行数据无列定义时按 key 推导
    if (not categories or not series) and rows and columns:
        converted = rows_to_chart(rows, columns)
        if converted:
            categories, series = converted['categories'], converted['series']
    if (not categories or not series) and cfg.get('sql'):
        result = run_readonly_sql(cfg['sql'])
        converted = rows_to_chart(result['rows'], result['columns']) if result else None
        if converted and len(converted['categories']) >= 2:  # 单行结果不足以绘图，视为无效
            categories, series = converted['categories'], converted['series']
            rows, columns, source = result['rows'], result['columns'], 'sql'
    if not categories or not series:
        if chart == 'table':
            table = demo_table(seed, title)
            columns, rows = table['columns'], table['rows']
            source = 'demo'
        elif chart == 'kpi':
            if value is None:
                value = demo_value(seed, title, unit)
                source = 'demo'
            series = [{'name': title or '当前值', 'data': [to_number(value)]}]
        elif chart == 'gauge':
            if value is None:
                series = demo_chart('gauge', seed, title)['series']
                source = 'demo'
            else:
                series = [{'name': '完成率', 'data': [to_number(value)]}]
        else:
            demo = demo_chart(chart, seed, title)
            categories, series = demo['categories'], demo['series']
            source = 'demo'
    if chart == 'pie' and len(series) > 1:  # 饼图只保留一个系列，避免比例失真
        series = [{'name': series[0]['name'], 'data': series[0]['data']}]
    if chart != 'table' and not rows:
        columns = [{'prop': 'category', 'label': '维度'}] + [
            {'prop': f's{index}', 'label': item['name']} for index, item in enumerate(series)]
        rows = [{'category': category, **{f's{index}': item['data'][index] if index < len(item['data']) else 0
                                           for index, item in enumerate(series)}}
                for index, category in enumerate(categories)]  # 图表数据同步生成明细表
    if chart == 'table' and (not categories or not series):
        converted = rows_to_chart(rows, columns)
        if converted:
            categories, series = converted['categories'], converted['series']
    final_value = value if value is not None else (series[0]['data'][0] if series and series[0].get('data') else 0)
    return {
        'chart': chart, 'unit': unit, 'value': to_number(final_value),
        'max': to_number(cfg.get('max')) or 100,
        'categories': categories, 'series': series,
        'columns': columns, 'rows': rows,
        'summary': build_summary(categories, series, unit),
        'source': source, 'sql': str(cfg.get('sql') or ''),
    }
