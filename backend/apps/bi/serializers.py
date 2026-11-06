"""大屏BI模块序列化器。"""
# 文件：apps/bi/serializers.py —— 大屏 BI 模块的序列化器
# 用途：把 ORM 实例转成 JSON 输出，并对新增/编辑请求体做字段校验，供 views 的 CRUD 复用。
# 数据表：bi_screen（大屏）、bi_dataset（数据集）、bi_visit_log（访问日志）。
# 路由前缀：/api/bi/screen、/api/bi/dataset、/api/bi/visit。
# 说明：三个序列化器都用 ModelSerializer + fields='__all__'，字段范围随模型自动增减，无需手工维护。
from rest_framework import serializers  # DRF 序列化/反序列化组件

from apps.bi.models import BiDataset, BiScreen, BiVisitLog  # BI 相关模型


# 大屏序列化器：列表、详情、新增、编辑、发布回包都使用它
class BiScreenSerializer(serializers.ModelSerializer):
    """大屏信息序列化器：直接暴露全部字段。"""
    # Meta 声明绑定的模型与输出字段范围
    class Meta:
        """声明模型与全部字段。"""
        model = BiScreen  # 目标模型
        fields = '__all__'  # 全字段输出


# 数据集序列化器：数据集 CRUD 的读写序列化
class BiDatasetSerializer(serializers.ModelSerializer):
    """大屏数据集序列化器：直接暴露全部字段。"""
    # Meta 声明绑定的模型与输出字段范围
    class Meta:
        """声明模型与全部字段。"""
        model = BiDataset  # 目标模型
        fields = '__all__'  # 全字段输出


# 访问日志序列化器：访问记录列表/删除接口使用
class BiVisitLogSerializer(serializers.ModelSerializer):
    """大屏访问日志序列化器：直接暴露全部字段。"""
    # Meta 声明绑定的模型与输出字段范围
    class Meta:
        """声明模型与全部字段。"""
        model = BiVisitLog  # 目标模型
        fields = '__all__'  # 全字段输出
