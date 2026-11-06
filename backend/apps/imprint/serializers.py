"""导入模板 + 打印模板模块序列化器。"""
# 模块：apps/imprint/serializers.py —— 三张表的 DRF 序列化器。
# 用途：把模型实例转成前端可用的 JSON，并在新增/编辑时做字段类型与必填校验。
# 对应表：imp_template / imp_template_column / print_template。
# 路由前缀：/api/imprint/，由 views.py 的三个 ViewSet 通过 serializer_class 引用本文件。
# 幂等性：序列化器无状态、只读类属性，反复调用不会产生副作用（写库由 CrudViewSet 负责）。
from rest_framework import serializers

# 需要序列化的三个模型：导入模板、模板列定义、打印模板
from apps.imprint.models import ImpTemplate, ImpTemplateColumn, PrintTemplate


# 导入模板主表序列化器：直接映射全部字段（含 BaseModel 的审计字段与 is_deleted）。
class ImpTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        # 绑定模型，自动推导各字段的序列化与校验行为
        model = ImpTemplate
        # 全字段输出：前端编辑表单需要完整字段，且审计字段由后端覆盖写入
        fields = '__all__'


# 导入模板列序列化器：用于列定义的新增/编辑/列表，字段级校验交给模型定义推导。
class ImpTemplateColumnSerializer(serializers.ModelSerializer):
    class Meta:
        # 绑定列定义模型（无审计字段）
        model = ImpTemplateColumn
        # 全字段输出，前端列配置表格直接回显
        fields = '__all__'


# 打印模板序列化器：html_content 为长文本，仍走默认 CharField/TextField 映射即可。
class PrintTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        # 绑定打印模板模型
        model = PrintTemplate
        # 全字段输出，包含 HTML 正文与纸张/默认标记等配置
        fields = '__all__'
