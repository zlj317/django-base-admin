"""报表模块序列化器。"""
# 模块：apps/report/serializers.py —— 报表四类资源的 DRF 序列化器
# 用途：把 rp_category / rp_datasource / rp_template / rp_generate_record 的模型实例与 JSON 互转。
# 数据表：rp_category、rp_datasource、rp_template、rp_generate_record。
# 调用方：apps/report/views.py 的四个 ViewSet 在 list/retrieve/create/update 时使用。
# 说明：报表配置本身是自由 JSON，故统一用 fields='__all__'，不做字段级业务校验。
from rest_framework import serializers  # DRF 序列化/反序列化组件

from apps.report.models import RpCategory, RpDatasource, RpGenerateRecord, RpTemplate  # 报表相关模型


# 报表分类序列化器：字段少且无敏感信息，直接全量暴露
class RpCategorySerializer(serializers.ModelSerializer):
    """报表分类序列化器：直接暴露全部字段。"""
    # Meta 声明目标模型与输出字段范围
    class Meta:
        """声明模型与全部字段。"""
        model = RpCategory  # 目标模型
        fields = '__all__'  # 全字段输出


# 报表数据源序列化器：ds_config 为 JSON 文本，交由前端解析，序列化层原样透传
class RpDatasourceSerializer(serializers.ModelSerializer):
    """报表数据源序列化器：直接暴露全部字段。"""
    # Meta 声明目标模型与输出字段范围
    class Meta:
        """声明模型与全部字段。"""
        model = RpDatasource  # 目标模型
        fields = '__all__'  # 全字段输出


# 报表模板序列化器：template_json / permission_json 均以字符串透传，由 render 层解析
class RpTemplateSerializer(serializers.ModelSerializer):
    """报表模板序列化器：直接暴露全部字段。"""
    # Meta 声明目标模型与输出字段范围
    class Meta:
        """声明模型与全部字段。"""
        model = RpTemplate  # 目标模型
        fields = '__all__'  # 全字段输出


# 生成记录序列化器：记录只由后端写入，前端主要读取状态与结果
class RpGenerateRecordSerializer(serializers.ModelSerializer):
    """报表生成记录序列化器：直接暴露全部字段。"""
    # Meta 声明目标模型与输出字段范围
    class Meta:
        """声明模型与全部字段。"""
        model = RpGenerateRecord  # 目标模型
        fields = '__all__'  # 全字段输出
