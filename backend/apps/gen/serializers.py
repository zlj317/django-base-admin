"""代码生成器序列化器。"""
from rest_framework import serializers

from apps.gen.models import SysGenTable, SysGenTableColumn


class GenTableSerializer(serializers.ModelSerializer):
    class Meta:
        model = SysGenTable
        fields = ['id', 'table_name', 'table_comment', 'class_name', 'module_name',
                  'module_comment', 'url_prefix', 'gen_path', 'parent_menu_id',
                  'is_delete_logic', 'import_enable', 'export_enable', 'create_time']

    def validate_module_name(self, value):
        import re
        if value and not re.match(r'^[a-z][a-z0-9_]*$', value):
            raise serializers.ValidationError('模块英文标识只能包含小写字母、数字、下划线，且以字母开头')
        return value

    def validate(self, attrs):
        import re
        prefix = attrs.get('url_prefix') or (self.instance.url_prefix if self.instance else '')
        if prefix and not re.match(r'^/api/[\w/]+$', prefix):
            raise serializers.ValidationError('接口路由前缀需以 /api/ 开头，如 /api/student/')
        return attrs


class GenColumnSerializer(serializers.ModelSerializer):
    class Meta:
        model = SysGenTableColumn
        fields = ['id', 'gen_table_id', 'column_name', 'column_comment', 'column_type',
                  'is_pk', 'dict_type', 'form_type', 'is_list', 'is_query', 'query_type',
                  'is_required', 'is_export', 'is_import', 'sort']
