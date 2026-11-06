"""代码生成器序列化器。"""
# 模块：apps/gen/serializers.py —— 生成配置的 DRF 序列化器
# 用途：主表/字段表的 JSON 校验与输出，保证前端提交的模块名、路由前缀符合出码规范。
# 数据表：sys_gen_table、sys_gen_table_column（managed=False，由建表 SQL 维护）。
# 调用方：apps/gen/views.py 的列表、详情、保存与导入接口统一使用本文件的两个序列化器。
from rest_framework import serializers  # 引入 DRF 序列化组件，用于校验与输出

from apps.gen.models import SysGenTable, SysGenTableColumn  # 引入需要读写的两张配置表模型


# 主表序列化器：出码配置的读写入口，额外承担模块名与路由前缀的格式校验
class GenTableSerializer(serializers.ModelSerializer):
    """生成任务主表的读写序列化器，附带模块名与路由前缀的格式校验。"""

    # Meta 只声明模型与字段白名单，字段校验逻辑放在下面的 validate_* 方法
    class Meta:
        """序列化配置：绑定主表模型并声明可读写字段。"""

        model = SysGenTable  # 绑定生成任务主表模型
        fields = ['id', 'table_name', 'table_comment', 'class_name', 'module_name',
                  'module_comment', 'url_prefix', 'gen_path', 'parent_menu_id',
                  'is_delete_logic', 'import_enable', 'export_enable', 'create_time']  # 允许读写的字段白名单

    # 字段级校验：module_name 会被 engine 用作目录名/权限前缀，因此必须符合标识符规范
    def validate_module_name(self, value):
        """校验模块英文标识：仅允许小写字母、数字、下划线且以字母开头。"""
        import re  # 局部导入，避免为单点校验增加模块级依赖
        if value and not re.match(r'^[a-z][a-z0-9_]*$', value):  # 非空时按命名规则校验
            raise serializers.ValidationError('模块英文标识只能包含小写字母、数字、下划线，且以字母开头')  # 校验失败抛出字段错误
        return value  # 通过校验后原样返回

    # 对象级校验：多个字段放一起校验，方便处理局部更新（PATCH/仅提交部分字段）场景
    def validate(self, attrs):
        """对象级校验：接口路由前缀必须为 /api/ 开头的路径。"""
        import re  # 局部导入正则模块，仅本节使用
        # 未提交前缀时回退到已有值，避免局部更新时被误判
        prefix = attrs.get('url_prefix') or (self.instance.url_prefix if self.instance else '')
        if prefix and not re.match(r'^/api/[\w/]+$', prefix):  # 有值时校验 /api/ 前缀格式
            raise serializers.ValidationError('接口路由前缀需以 /api/ 开头，如 /api/student/')  # 前缀不合规时报错
        return attrs  # 返回清洗后的属性字典


# 字段序列化器：只做字段白名单映射，不额外校验；列名与控件类型由前端与 engine 约定
class GenColumnSerializer(serializers.ModelSerializer):
    """生成字段配置表的读写序列化器。"""

    # 绑定字段表并声明可读写字段，主键 gen_table_id 用于回填所属生成任务
    class Meta:
        """序列化配置：绑定字段配置模型并声明可读写字段。"""

        model = SysGenTableColumn  # 绑定字段配置表模型
        fields = ['id', 'gen_table_id', 'column_name', 'column_comment', 'column_type',
                  'is_pk', 'dict_type', 'form_type', 'is_list', 'is_query', 'query_type',
                  'is_required', 'is_export', 'is_import', 'sort']  # 允许读写的字段白名单
