"""{{ table.module_comment }} 模型（由代码生成器生成，可二次修改）。"""
from django.db import models

from common.fields import SnowflakeIDField


class {{ table.class_name }}(models.Model):
    """{{ table.module_comment }}（{{ table.table_name }}）"""

{% for col in columns %}{% if col.is_pk %}    id = SnowflakeIDField(verbose_name='{{ col.column_comment }}')
{% else %}    {{ col.column_name }} = {{ col.field_def }}
{% endif %}{% endfor %}

    class Meta:
        db_table = '{{ table.table_name }}'
        managed = False
        verbose_name = '{{ table.module_comment }}'
        ordering = ['-{{ pk }}']
