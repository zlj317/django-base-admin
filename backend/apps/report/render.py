"""报表数据渲染：把 rp_template 配置解析成前端可直接绘制的结构。"""
# 模块：apps/report/render.py —— 报表预览与生成记录回放的渲染层
# 用途：读取 rp_template.template_json，交给 common.chart_data 归一化后拼成前端统一的数据包。
# 数据表：读取 rp_template、rp_category、rp_datasource、rp_generate_record（只读，不落库）。
# 调用方：apps/report/views.py 的 preview 动作，分别处理模板预览与历史记录回放。
# 说明：SQL 执行失败、配置为空等情况由 chart_data 兜底生成演示数据，本层不抛业务异常。
import time  # 生成更新时间

from apps.report.models import RpCategory, RpDatasource, RpTemplate  # 报表模型
from common.chart_data import build_chart_data, parse_config  # 公共图表数据构建

# 图表类型 → 中文名，用于预览页展示"当前是什么图"；未命中时留空由前端兜底
CHART_LABELS = {'bar': '柱状图', 'line': '折线图', 'pie': '饼图', 'table': '数据表格'}  # 图表类型中文名


# 解析模板的分类名与数据源名；两者都可能为空（分类/数据源被删除或未配置）
def _resolve_meta(category_id, ds_id):
    """解析分类名与数据源名，供预览页展示来源信息。"""
    # 先给默认空串，保证调用方拿到的始终是字符串，前端无需判 null
    category_name = ''
    # 数据源名同样先置空，模板未配置数据源时保持空串
    ds_name = ''
    # 只有配置了分类 ID 才查库，避免无意义的 SQL
    if category_id:
        # values_list(flat=True) 只取名称列，减少数据传输；first() 查不到时返回 None
        category_name = RpCategory.objects.filter(pk=category_id).values_list('category_name', flat=True).first() or ''
    # 数据源同理：ds_id 为空说明模板未指定数据源
    if ds_id:
        # 取不到时用空串兜底，预览页显示为空即可
        ds_name = RpDatasource.objects.filter(pk=ds_id).values_list('ds_name', flat=True).first() or ''
    # 返回二元组，供 _build 直接写入数据包
    return category_name, ds_name


# 统一组装函数：模板预览与记录回放都走这里，保证两条路径输出结构一致
def _build(template_json, name, seed, template_id, key, category_name, ds_name, version):
    """按模板配置构建报表数据包，四种视图（柱/线/饼/表）统一结构。"""
    # parse_config 容错解析 JSON；build_chart_data 归一化图表类型、系列、明细行与摘要
    core = build_chart_data(parse_config(template_json), name, seed, 'bar')
    # 返回前端约定的完整结构：模板元信息 + 图表数据 + 更新时间
    return {
        # 模板标识与展示名，前端用于标题、缓存键与下载命名
        'id': template_id, 'name': name, 'key': key,
        # 来源信息（分类名/数据源名）与版本号，便于排查数据出处
        'category_name': category_name, 'ds_name': ds_name,
        # 模板版本号，前端可用于提示"配置已更新"
        'version': version,
        # 图表中文名；未识别的类型给空串
        'chart_label': CHART_LABELS.get(core['chart'], ''),
        # 把 chart_data 生成的 chart/categories/series/columns/rows/summary/value 等展开到顶层
        **core,
        # 当前渲染时刻，供前端展示"数据刷新时间"；此处为预览时刻而非落库时间
        'updated_at': time.strftime('%Y-%m-%d %H:%M:%S'),
        # 预览场景没有生成记录，占位为 None，保持结构统一
        'record': None,
        # 数据包组装结束
    }


# 模板预览入口：由 views 的 preview 动作在传入模板对象时调用
def build_report(template):
    """根据报表模板生成预览数据。"""
    # 先补齐分类名/数据源名，再做结构组装
    category_name, ds_name = _resolve_meta(template.category_id, template.ds_id)
    # seed 用模板主键，保证同一模板多次预览得到相同的演示数据
    return _build(template.template_json, template.template_name, template.id, template.id,
                  # 参数依次为：配置、名称、seed、模板 ID、模板编码、分类名、数据源名、版本
                  template.template_key or '', category_name, ds_name, template.version)


# 生成记录回放：用于历史记录预览；模板已删除时仍要能展示，故退化为按快照生成演示数据
def build_record_report(record):
    """根据生成记录回放报表结果：模板被删除时用记录快照生成演示数据。"""
    # 先按记录里的 template_id 找模板，模板可能已被逻辑删除或物理删除
    template = RpTemplate.objects.filter(pk=record.template_id).first()
    # 分支一：模板仍在，用模板当前配置渲染，但名称优先取记录快照，保证与当时一致
    if template:
        # 分类/数据源同样按模板当前配置解析
        category_name, ds_name = _resolve_meta(template.category_id, template.ds_id)
        # 传入记录快照名称，模板被改名时回放仍显示生成时的名称
        payload = _build(template.template_json, record.template_name or template.template_name,
                         # 模板 ID 同时作为 seed，保证回放时演示数据稳定
                         template.id, template.id, template.template_key or '',
                         # 分类名、数据源名与版本沿用模板当前配置
                         category_name, ds_name, template.version)
    # 分支二：模板不存在，只能用记录快照 + 空配置，由 chart_data 生成演示数据
    else:
        # 空字符串配置会触发演示数据；seed 用 template_id 保证同一记录回放结果稳定
        payload = _build('', record.template_name or '已删除的报表模板', record.template_id or record.id,
                         # 模板已删，分类/数据源/版本均无意义，统一给空值
                         record.template_id, '', '', '', 0)
    # 无论模板是否存在，都把本次生成记录信息附加到返回包，供前端展示状态与参数
    payload['record'] = {
        # 记录主键与生成状态/触发方式，前端据此显示成功或失败标签
        'id': record.id, 'gen_status': record.gen_status, 'gen_type': record.gen_type,
        # 生成耗时（毫秒）与完成时间，用于审计与性能观察
        'cost_time': record.cost_time, 'gen_time': record.gen_time,
        # 失败原因与查询参数；空值转空串，避免前端渲染 null
        'error_msg': record.error_msg or '',
        # 生成时使用的查询参数（JSON 文本），便于复现同一份报表
        'param': record.param_json or '',
        # 生成记录信息组装结束
    }
    # 返回最终数据包
    return payload
