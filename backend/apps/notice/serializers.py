"""公告模块序列化器。"""
# 模块：apps/notice/serializers.py —— 公告模块的 DRF 序列化器
# 用途：把三张公告表模型转成可 JSON 化的字段集合，列表、详情、新增、编辑共用同一套输出。
# 对应表：notice_category、notice_info、notice_read
# 关键约定：全部使用 ModelSerializer + fields='__all__'，字段类型与校验直接由模型定义推导，不额外加工。
from rest_framework import serializers  # DRF 序列化/反序列化组件

from apps.notice.models import NoticeCategory, NoticeInfo, NoticeRead  # 公告相关模型


# 公告分类序列化器：分类字段简单，全量输出即可满足前端下拉选择与编辑表单。
class NoticeCategorySerializer(serializers.ModelSerializer):
    """公告分类序列化器：直接暴露全部字段。"""
    # Meta 只声明模型与字段范围，DRF 据此自动推导每个字段的类型、必填与只读规则。
    class Meta:
        """声明模型与全部字段。"""
        model = NoticeCategory  # 目标模型
        fields = '__all__'  # 全字段输出


# 公告信息序列化器：公告正文、状态、可见范围等字段整体读写，前端编辑页依赖完整字段。
class NoticeInfoSerializer(serializers.ModelSerializer):
    """公告信息序列化器：直接暴露全部字段。"""
    # Meta 只声明模型与字段范围，DRF 据此自动推导每个字段的类型、必填与只读规则。
    class Meta:
        """声明模型与全部字段。"""
        model = NoticeInfo  # 目标模型
        fields = '__all__'  # 全字段输出


# 公告阅读记录序列化器：后台查看阅读明细时使用，只读输出全部字段。
class NoticeReadSerializer(serializers.ModelSerializer):
    """公告阅读记录序列化器：直接暴露全部字段。"""
    # Meta 只声明模型与字段范围，DRF 据此自动推导每个字段的类型、必填与只读规则。
    class Meta:
        """声明模型与全部字段。"""
        model = NoticeRead  # 目标模型
        fields = '__all__'  # 全字段输出
