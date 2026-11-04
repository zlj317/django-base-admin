"""报表数据渲染：把 rp_template 配置解析成前端可直接绘制的结构。"""
import time  # 生成更新时间

from apps.report.models import RpCategory, RpDatasource, RpTemplate  # 报表模型
from common.chart_data import build_chart_data, parse_config  # 公共图表数据构建

CHART_LABELS = {'bar': '柱状图', 'line': '折线图', 'pie': '饼图', 'table': '数据表格'}  # 图表类型中文名


def _resolve_meta(category_id, ds_id):
    """解析分类名与数据源名，供预览页展示来源信息。"""
    category_name = ''
    ds_name = ''
    if category_id:
        category_name = RpCategory.objects.filter(pk=category_id).values_list('category_name', flat=True).first() or ''
    if ds_id:
        ds_name = RpDatasource.objects.filter(pk=ds_id).values_list('ds_name', flat=True).first() or ''
    return category_name, ds_name


def _build(template_json, name, seed, template_id, key, category_name, ds_name, version):
    """按模板配置构建报表数据包，四种视图（柱/线/饼/表）统一结构。"""
    core = build_chart_data(parse_config(template_json), name, seed, 'bar')
    return {
        'id': template_id, 'name': name, 'key': key,
        'category_name': category_name, 'ds_name': ds_name,
        'version': version,
        'chart_label': CHART_LABELS.get(core['chart'], ''),
        **core,
        'updated_at': time.strftime('%Y-%m-%d %H:%M:%S'),
        'record': None,
    }


def build_report(template):
    """根据报表模板生成预览数据。"""
    category_name, ds_name = _resolve_meta(template.category_id, template.ds_id)
    return _build(template.template_json, template.template_name, template.id, template.id,
                  template.template_key or '', category_name, ds_name, template.version)


def build_record_report(record):
    """根据生成记录回放报表结果：模板被删除时用记录快照生成演示数据。"""
    template = RpTemplate.objects.filter(pk=record.template_id).first()
    if template:
        category_name, ds_name = _resolve_meta(template.category_id, template.ds_id)
        payload = _build(template.template_json, record.template_name or template.template_name,
                         template.id, template.id, template.template_key or '',
                         category_name, ds_name, template.version)
    else:
        payload = _build('', record.template_name or '已删除的报表模板', record.template_id or record.id,
                         record.template_id, '', '', '', 0)
    payload['record'] = {
        'id': record.id, 'gen_status': record.gen_status, 'gen_type': record.gen_type,
        'cost_time': record.cost_time, 'gen_time': record.gen_time,
        'error_msg': record.error_msg or '',
        'param': record.param_json or '',
    }
    return payload
