from django.apps import AppConfig


class {{ table.class_name }}Config(AppConfig):
    name = 'apps.{{ table.module_name }}'
    verbose_name = '{{ table.module_comment }}'
