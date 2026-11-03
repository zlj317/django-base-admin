"""{{ table.module_comment }} 序列化器（由代码生成器生成，可二次修改）。"""
from rest_framework import serializers

from apps.{{ table.module_name }}.models import {{ table.class_name }}

COMMON_FIELDS = ['id', 'create_by', 'create_time', 'update_by', 'update_time']


class {{ table.class_name }}Serializer(serializers.ModelSerializer):
    """详情 / 响应序列化器"""

    class Meta:
        model = {{ table.class_name }}
        fields = ['{{ pk }}'] + [
{% for col in form_cols %}{% if not col.is_pk %}            '{{ col.column_name }}',
{% endif %}{% endfor %}        ] + COMMON_FIELDS


class {{ table.class_name }}CreateSerializer(serializers.ModelSerializer):
    """新增 / 编辑序列化器"""

    def to_internal_value(self, data):
        # 前端未选择的下拉/数值/日期传空串，统一转为 None
        data = dict(data)
        for key, value in data.items():
            if value == '':
                data[key] = None
        return super().to_internal_value(data)

    class Meta:
        model = {{ table.class_name }}
        fields = [
{% for col in form_cols %}{% if not col.is_pk %}            '{{ col.column_name }}',
{% endif %}{% endfor %}        ]
        extra_kwargs = {
{% for col in form_cols %}{% if not col.is_pk %}{% if col.is_required %}            '{{ col.column_name }}': {'required': True},
{% elif col.is_char %}            '{{ col.column_name }}': {'required': False, 'allow_blank': True, 'allow_null': True},
{% else %}            '{{ col.column_name }}': {'required': False, 'allow_null': True},
{% endif %}{% endif %}{% endfor %}        }


class {{ table.class_name }}ListSerializer(serializers.ModelSerializer):
    """列表序列化器"""

    class Meta:
        model = {{ table.class_name }}
        fields = ['{{ pk }}'] + [
{% for col in list_cols %}            '{{ col.column_name }}',
{% endfor %}{% if has_create_time %}            'create_time',
{% endif %}        ]
