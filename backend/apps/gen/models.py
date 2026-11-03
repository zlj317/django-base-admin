"""代码生成器配置表模型。"""
from django.db import models

from common.utils import BaseModel


class SysGenTable(BaseModel):
    """生成任务主表。"""

    id = models.BigAutoField(primary_key=True)
    table_name = models.CharField('数据库表名', max_length=100, unique=True)
    table_comment = models.CharField('表注释', max_length=200, blank=True, null=True)
    class_name = models.CharField('实体类名', max_length=100, blank=True, null=True)
    module_name = models.CharField('模块英文标识', max_length=50, blank=True, null=True)
    module_comment = models.CharField('模块中文名称', max_length=100, blank=True, null=True)
    url_prefix = models.CharField('接口路由前缀', max_length=100, blank=True, null=True)
    gen_path = models.CharField('前端页面存放路径', max_length=255, blank=True, null=True)
    parent_menu_id = models.BigIntegerField('父级菜单ID', blank=True, null=True)
    is_delete_logic = models.BooleanField('是否逻辑删除', default=True)
    import_enable = models.BooleanField('是否开启导入', default=True)
    export_enable = models.BooleanField('是否开启导出', default=True)

    class Meta:
        db_table = 'sys_gen_table'
        managed = False
        ordering = ['-id']


class SysGenTableColumn(BaseModel):
    """生成字段配置表。"""

    FORM_CHOICES = (
        ('input', '输入框'), ('number', '数字框'), ('date', '日期选择'),
        ('select', '下拉字典'), ('radio', '单选'), ('textarea', '多行文本'),
        ('image', '图片上传'), ('file', '文件上传'),
    )
    QUERY_CHOICES = (
        ('eq', '等于'), ('like', '模糊'), ('gt', '大于'),
        ('lt', '小于'), ('between', '区间'),
    )

    id = models.BigAutoField(primary_key=True)
    gen_table_id = models.BigIntegerField('生成任务ID')
    column_name = models.CharField('字段名', max_length=100)
    column_comment = models.CharField('字段注释', max_length=200, blank=True, null=True)
    column_type = models.CharField('字段类型', max_length=50, blank=True, null=True)
    is_pk = models.BooleanField('是否主键', default=False)
    dict_type = models.CharField('字典编码', max_length=100, blank=True, null=True)
    form_type = models.CharField('表单控件', max_length=50, blank=True, null=True)
    is_list = models.BooleanField('列表展示', default=True)
    is_query = models.BooleanField('查询条件', default=False)
    query_type = models.CharField('查询方式', max_length=20, blank=True, null=True)
    is_required = models.BooleanField('是否必填', default=False)
    is_export = models.BooleanField('是否导出', default=True)
    is_import = models.BooleanField('是否导入', default=True)
    sort = models.IntegerField('排序号', default=0)

    class Meta:
        db_table = 'sys_gen_table_column'
        managed = False
        ordering = ['sort', 'id']
