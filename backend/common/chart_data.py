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
    'column': 'bar', 'area': 'line', 'donut': 'pie', 'ring': 'pie',  # 柱状/面积/环形归一化为 bar/line/pie
    'grid': 'table', 'map': 'rank', 'list': 'rank', 'ranking': 'rank',  # 表格与排行类别名
    'stats': 'kpi', 'cards': 'kpi', 'number': 'kpi', 'dashboard': 'gauge',  # 指标卡与仪表盘别名
}
CHART_TYPES = ('bar', 'line', 'pie', 'table', 'kpi', 'gauge', 'rank')  # 组件可渲染的 7 种类型
BLOCK_WORDS = ('insert ', 'update ', 'delete ', 'drop ', 'alter ', 'create ', 'truncate ', 'grant ')  # 只读 SQL 禁止出现的写操作


def parse_config(text):
    """把 TEXT 字段中的 JSON 转成 dict；非法内容一律视为空配置。"""
    if not text:  # 空值/空串直接返回空配置
        return {}
    try:
        data = json.loads(text)  # 解析 JSON 文本
    except (TypeError, ValueError):  # 类型错误或 JSON 语法错误均视为非法
        return {}
    return data if isinstance(data, dict) else {}  # 只接受对象，数组/标量一律丢弃


def normalize_chart(value, default='bar'):
    """图表类型归一化：别名映射后校验，非法值回退默认类型。"""
    key = CHART_ALIASES.get(str(value or '').strip().lower(), str(value or '').strip().lower())  # 先小写去空格，再查别名表
    return key if key in CHART_TYPES else default  # 命中白名单才采用，否则回退默认


def to_number(value):
    """转数值：非数字按 0 处理，整数去掉小数部分便于展示。"""
    try:
        num = float(value)  # 统一先转浮点，兼容字符串数字
    except (TypeError, ValueError):  # 无法转换时按 0 兜底
        return 0
    return int(num) if num == int(num) else round(num, 2)  # 整数去掉 .0，小数保留两位


def jsonable(value):
    """把 datetime/decimal 等不可 JSON 序列化的值转成文本。"""
    if value is None or isinstance(value, (str, int, float, bool)):  # 基础类型原样返回
        return value
    return str(value)  # 其余类型（日期、Decimal 等）统一转字符串


def run_readonly_sql(sql, limit=100):
    """执行只读 SQL：仅允许单条 SELECT，失败或无结果返回 None。"""
    if not isinstance(sql, str):  # 非字符串配置直接拒绝
        return None
    text = sql.strip().rstrip(';').strip()  # 去掉首尾空白与结尾分号
    lowered = text.lower()  # 转小写便于关键字判断
    if not lowered.startswith('select') or ';' in text:  # 只读且只允许单条语句
        return None
    if any(word in f' {lowered} ' for word in BLOCK_WORDS):  # 含写关键字直接拒绝
        return None
    try:
        with connection.cursor() as cursor:  # 复用默认数据库连接，用完自动关闭
            cursor.execute(text)  # 执行已验证的 SELECT
            columns = [str(col[0]) for col in cursor.description or []]  # 从游标元数据取列名
            values = cursor.fetchmany(limit)  # 最多取 limit 行，避免大结果集拖慢预览
    except Exception:  # 数据源表不存在或 SQL 不合法时静默退回演示数据
        return None
    if not columns or not values:  # 无列或无数据都视为无效结果
        return None
    rows = [{col: jsonable(val) for col, val in zip(columns, row)} for row in values]  # 按列名组装成字典行
    return {'columns': [{'prop': col, 'label': col} for col in columns], 'rows': rows}  # 输出前端表格结构


def normalize_columns(raw):
    """列定义归一化：支持字符串与 {prop,label} 两种写法。"""
    columns = []  # 归一化后的列定义
    for item in raw if isinstance(raw, list) else []:  # 仅遍历列表配置，其它类型忽略
        if isinstance(item, dict) and item.get('prop'):  # 字典写法：必须有 prop
            columns.append({'prop': str(item['prop']), 'label': str(item.get('label') or item['prop'])})  # label 缺失时用 prop
        elif isinstance(item, str):  # 纯字符串写法：prop 与 label 相同
            columns.append({'prop': item, 'label': item})
    return columns  # 返回统一结构


def normalize_series(raw):
    """系列定义归一化：过滤非数值数据，保证前端可直接绘制。"""
    series = []  # 归一化后的系列列表
    for item in raw if isinstance(raw, list) else []:  # 仅遍历列表配置
        if not isinstance(item, dict) or not isinstance(item.get('data'), list):  # 结构不合法则跳过
            continue
        name = str(item.get('name') or f'系列{len(series) + 1}')  # 未命名时按序号补名
        series.append({'name': name, 'data': [to_number(v) for v in item['data']]})  # 数值统一转换
    return series


def rows_to_chart(rows, columns):
    """二维表 → categories + series：首列作维度，其余列作数值指标。"""
    if not rows or len(columns) < 2 or not isinstance(rows[0], dict):  # 至少两列且为字典行才可转换
        return None
    dimension = columns[0]['prop']  # 首列作为维度字段
    categories = [str(row.get(dimension, '')) for row in rows]  # 维度值转字符串供 X 轴使用
    series = [
        {'name': col['label'], 'data': [to_number(row.get(col['prop'])) for row in rows]}  # 每个指标列生成一个系列
        for col in columns[1:]
    ]
    return {'categories': categories, 'series': series}  # 返回图表可直接消费的结构


def demo_categories(title='', pie=False):
    """按标题关键词选择演示维度，尽量贴近报表语义。"""
    if '区域' in title:  # 区域类报表用大区维度
        return ['华东', '华南', '华北', '西南', '东北']
    if any(key in title for key in ('库存', '商品', '品类', '周转')):  # 库存类报表用商品品类维度
        return ['3C数码', '家用电器', '服饰鞋帽', '食品饮料', '美妆个护']
    if '客户' in title:  # 客户类报表按季度维度
        return ['Q1', 'Q2', 'Q3', 'Q4']
    if pie:  # 普通饼图默认按渠道分布
        return ['直营渠道', '经销渠道', '电商渠道', '门店渠道', '其他渠道']
    return [f'{i}月' for i in range(1, 13)]  # 兜底：1~12 月


def demo_chart(chart, seed, title=''):
    """按图表类型生成确定性演示数据，保证同一模板每次预览一致。"""
    rnd = random.Random(f'{seed}-{chart}')  # 以模板/组件 ID 作种子
    if chart == 'gauge':  # 仪表盘只返回一个完成率数值
        return {'categories': [], 'series': [{'name': '完成率', 'data': [rnd.randint(45, 95)]}]}
    categories = demo_categories(title, pie=chart == 'pie')  # 维度按标题语义选择
    base = rnd.randint(60, 160)  # 基准值，决定整体量级
    step = rnd.uniform(0.02, 0.09)  # 每月增长率，制造轻微上升趋势
    first = [max(6, round(base * (1 + step * i) + rnd.uniform(-base * 0.16, base * 0.16)))  # 主指标：趋势 + 随机波动
             for i in range(len(categories))]  # 整体缓慢上升，接近真实业务趋势
    second = [max(4, round(value * rnd.uniform(0.32, 0.62))) for value in first]  # 辅指标约为主指标的 1/3~2/3
    if chart == 'pie':  # 饼图只需要一个系列
        return {'categories': categories, 'series': [{'name': _value_name(title), 'data': first}]}
    names = ('销售额', '订单量')  # 默认双指标
    if '客户' in title:  # 客户主题换指标名
        names = ('新增客户', '活跃客户')
    elif any(key in title for key in ('库存', '周转')):  # 库存主题换指标名
        names = ('库存量', '周转天数')
    elif '率' in title:  # 比率主题换指标名
        names = ('本期完成率', '上期完成率')
    return {'categories': categories,
            'series': [{'name': names[0], 'data': first}, {'name': names[1], 'data': second}]}  # 双系列输出


def _value_name(title):
    """根据标题猜一个适合饼图的值名称。"""
    if any(key in title for key in ('销售', '营收', '金额')):  # 金额类主题
        return '销售额'
    if '订单' in title:  # 订单类主题
        return '订单量'
    return '数量'  # 兜底名称


def demo_table(seed, title='', rows_count=6):
    """生成确定性的演示明细表，按库存/销售语义给出不同列。"""
    rnd = random.Random(f'{seed}-table')  # 固定种子，保证每次同样的表
    if any(key in title for key in ('库存', '商品')):  # 库存类明细表结构
        columns = [{'prop': 'goods', 'label': '商品名称'}, {'prop': 'qty', 'label': '库存数量'},
                   {'prop': 'safe', 'label': '安全库存'}, {'prop': 'state', 'label': '状态'}]  # 四列：商品/库存/安全值/状态
        rows = []  # 演示明细行集合
        for index in range(rows_count):  # 逐行生成演示数据
            safe = rnd.randint(10, 60)  # 安全库存阈值
            qty = rnd.randint(0, safe + 40)  # 当前库存，可能低于安全值
            rows.append({'goods': f'商品-{chr(65 + index)}', 'qty': qty, 'safe': safe,
                         'state': '预警' if qty < safe else '正常'})  # 低于安全库存标记预警
        return {'columns': columns, 'rows': rows}
    columns = [{'prop': 'month', 'label': '月份'}, {'prop': 'orders', 'label': '订单数'},
               {'prop': 'amount', 'label': '销售额'}, {'prop': 'rate', 'label': '同比'}]  # 销售类明细表四列
    rows = [{'month': f'{index}月', 'orders': rnd.randint(200, 900), 'amount': rnd.randint(8000, 60000),
             'rate': f'{rnd.randint(-8, 36)}%'} for index in range(1, rows_count + 1)]  # 逐月生成订单/金额/同比
    return {'columns': columns, 'rows': rows}


def demo_value(seed, title='', unit=''):
    """按单位/标题生成一个量级合理的演示指标值。"""
    rnd = random.Random(f'{seed}-value')  # 固定种子保证幂等
    if unit == '元' or any(key in title for key in ('销售', '营收', '金额')):  # 金额类指标用十万级
        return rnd.randint(100000, 999999)
    if unit == '单' or '订单' in title:  # 订单类指标用千级
        return rnd.randint(1000, 9999)
    return rnd.randint(10, 999)  # 其余用百级


def build_summary(categories, series, unit=''):
    """根据首个系列生成合计/峰值/均值等摘要指标，供预览页展示。"""
    if not series:  # 没有系列就没有可汇总的数据
        return []  # 返回空摘要
    values = [to_number(value) for value in series[0].get('data') or []]  # 只汇总第一个系列
    if not values:  # 数据为空同样返回空摘要
        return []  # 返回空摘要
    total = sum(values)  # 合计
    peak = max(values)  # 峰值
    peak_index = values.index(peak)  # 峰值所在下标，用于回查维度名
    peak_dimension = categories[peak_index] if peak_index < len(categories) else ''  # 维度不足时留空
    return [
        {'label': f'{series[0].get("name") or "合计"}合计', 'value': f'{total:,.0f}', 'unit': unit},  # 合计指标
        {'label': '峰值', 'value': f'{peak:,.0f}', 'unit': unit},  # 峰值指标
        {'label': '峰值维度', 'value': peak_dimension or '-', 'unit': ''},  # 峰值对应维度
        {'label': '平均值', 'value': f'{total / len(values):,.0f}', 'unit': unit},  # 平均值指标
    ]


def build_chart_data(cfg, title='', seed=0, default='bar'):
    """把任意配置（含空配置）整理成统一的图表数据包。"""
    chart = normalize_chart(cfg.get('chart') or cfg.get('chart_type'), default)  # 图表类型归一化
    unit = str(cfg.get('unit') or '')  # 单位文本
    value = cfg.get('value')  # 指标卡/仪表盘的显式数值
    categories = [str(item) for item in (cfg.get('categories') or []) if item is not None]  # 维度列表，过滤空值
    series = normalize_series(cfg.get('series'))  # 系列归一化
    columns = normalize_columns(cfg.get('columns'))  # 列定义归一化
    raw_rows = cfg.get('rows') if isinstance(cfg.get('rows'), list) else cfg.get('data')  # rows 优先，兼容 data 字段
    rows = raw_rows if isinstance(raw_rows, list) else []  # 非列表一律视为无明细
    source = 'config'  # 取数来源标记：默认来自配置
    if rows and not columns and isinstance(rows[0], dict):  # 有行无列时按首行 key 推导列
        columns = [{'prop': key, 'label': key} for key in rows[0].keys()]  # 行数据无列定义时按 key 推导
    if (not categories or not series) and rows and columns:  # 缺维度或系列时尝试用明细表转换
        converted = rows_to_chart(rows, columns)  # 二维表转图表结构
        if converted:  # 转换成功才覆盖
            categories, series = converted['categories'], converted['series']
    if (not categories or not series) and cfg.get('sql'):  # 仍缺数据且配置了 SQL 时尝试查库
        result = run_readonly_sql(cfg['sql'])  # 只读执行，失败返回 None
        converted = rows_to_chart(result['rows'], result['columns']) if result else None  # 查询结果转图表
        if converted and len(converted['categories']) >= 2:  # 单行结果不足以绘图，视为无效
            categories, series = converted['categories'], converted['series']
            rows, columns, source = result['rows'], result['columns'], 'sql'  # 标记来源为 SQL
    if not categories or not series:  # 三种来源都没有可用数据时走演示数据
        if chart == 'table':  # 表格类生成演示明细
            table = demo_table(seed, title)  # 生成列与行
            columns, rows = table['columns'], table['rows']  # 解包到统一变量
            source = 'demo'  # 标记来源为演示
        elif chart == 'kpi':  # 指标卡没有显式值则生成演示值
            if value is None:  # 仅缺值时生成，已有值不覆盖
                value = demo_value(seed, title, unit)  # 生成量级合理的演示值
                source = 'demo'  # 标记来源为演示
            series = [{'name': title or '当前值', 'data': [to_number(value)]}]  # 指标卡用单值系列承载
        elif chart == 'gauge':  # 仪表盘同样按单值处理
            if value is None:  # 缺值时用演示仪表盘数据
                series = demo_chart('gauge', seed, title)['series']  # 45~95 的完成率
                source = 'demo'  # 标记来源为演示
            else:  # 有值则直接作为完成率
                series = [{'name': '完成率', 'data': [to_number(value)]}]
        else:  # 其余图表类型生成演示维度与系列
            demo = demo_chart(chart, seed, title)  # 按类型生成确定性数据
            categories, series = demo['categories'], demo['series']  # 解包维度与系列
            source = 'demo'  # 标记来源为演示
    if chart == 'pie' and len(series) > 1:  # 饼图只保留一个系列，避免比例失真
        series = [{'name': series[0]['name'], 'data': series[0]['data']}]  # 截取首个系列
    if chart != 'table' and not rows:  # 图表类同步生成明细表，供“数据视图”切换
        columns = [{'prop': 'category', 'label': '维度'}] + [  # 首列为维度列
            {'prop': f's{index}', 'label': item['name']} for index, item in enumerate(series)]  # 其余列对应各系列
        rows = [{'category': category, **{f's{index}': item['data'][index] if index < len(item['data']) else 0
                                           for index, item in enumerate(series)}}
                for index, category in enumerate(categories)]  # 图表数据同步生成明细表
    if chart == 'table' and (not categories or not series):  # 表格类反向补齐图表结构
        converted = rows_to_chart(rows, columns)  # 由明细表推导图表数据
        if converted:  # 推导成功才覆盖
            categories, series = converted['categories'], converted['series']
    final_value = value if value is not None else (series[0]['data'][0] if series and series[0].get('data') else 0)  # 最终展示值
    return {
        'chart': chart, 'unit': unit, 'value': to_number(final_value),  # 类型/单位/主数值
        'max': to_number(cfg.get('max')) or 100,  # 仪表盘最大值，缺省 100
        'categories': categories, 'series': series,  # 维度与系列
        'columns': columns, 'rows': rows,  # 明细表结构
        'summary': build_summary(categories, series, unit),  # 摘要指标
        'source': source, 'sql': str(cfg.get('sql') or ''),  # 取数来源与原始 SQL（供排查）
    }
