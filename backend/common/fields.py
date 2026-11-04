"""自定义模型字段：雪花算法主键。"""
from django.db import models  # 复用 Django 内置字段类型

from common.snowflake import next_id  # 雪花 ID 生成器


class SnowflakeIDField(models.BigIntegerField):
    """BIGINT 主键，插入时由后端雪花算法生成，不使用数据库自增。"""

    description = '雪花算法主键'

    def __init__(self, *args, **kwargs):
        """统一补齐主键、默认值与只读属性，子模型只需声明字段名。"""
        kwargs.setdefault('primary_key', True)  # 固定作为主键
        kwargs.setdefault('default', next_id)  # 新建实例时自动生成雪花 ID
        kwargs.setdefault('editable', False)  # 管理端/序列化器不接收手工指定主键
        super().__init__(*args, **kwargs)
