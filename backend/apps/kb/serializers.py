# 文件：apps/kb/serializers.py —— 知识库模块的序列化器
# 用途：在模型与 JSON 之间做转换，供视图集输出数据、校验前端入参。
# 对应表：kb_category、kb_document、kb_favorite。
# 路由前缀：api/kb/category/、api/kb/document/、api/kb/favorite/。
# 关键约定：三个序列化器都用 ModelSerializer 直出全部字段，不做裁剪，前端字段名与模型一致。
"""知识库模块序列化器。"""
# DRF 序列化/反序列化组件，ModelSerializer 定义在此命名空间
from rest_framework import serializers  # DRF 序列化/反序列化组件

# 分类/文档/收藏模型，供下方 Meta.model 引用
from apps.kb.models import KBCategory, KBDocument, KBFavorite  # 知识库相关模型


# 分类序列化器：新增/编辑按模型字段自动校验，列表直接输出整行
class KBCategorySerializer(serializers.ModelSerializer):
    """知识库分类序列化器：直接暴露全部字段。"""
    # 内部 Meta：绑定模型并声明输出字段集合
    class Meta:
        # 绑定分类模型：字段与校验规则由模型自动推导
        model = KBCategory
        # 输出全部字段，含雪花 id、parent_id 与审计字段
        fields = '__all__'


# 文档序列化器：附件只暴露 file_id，前端再拿它去文件模块换下载地址
class KBDocumentSerializer(serializers.ModelSerializer):
    """知识库文档序列化器：直接暴露全部字段。"""
    # 内部 Meta：绑定文档模型并输出全部字段
    class Meta:
        # 绑定文档模型
        model = KBDocument
        # 输出全部字段，包含正文、标签、权限配置与统计字段
        fields = '__all__'


# 收藏序列化器：记录"谁收藏了哪篇文档"，字段少且无需裁剪
class KBFavoriteSerializer(serializers.ModelSerializer):
    """知识收藏序列化器：直接暴露全部字段。"""
    # 内部 Meta：绑定收藏模型并输出全部字段
    class Meta:
        # 绑定收藏模型
        model = KBFavorite
        # 输出全部字段，前端可据此渲染"我的收藏"列表
        fields = '__all__'
