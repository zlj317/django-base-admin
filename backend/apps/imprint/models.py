"""导入模板 + 打印模板模块模型。"""
from django.db import models
from common.fields import SnowflakeIDField  # 雪花算法主键字段

from common.utils import BaseModel


class ImpTemplate(BaseModel):
    """导入模板表。"""

    id = SnowflakeIDField(primary_key=True)
    template_name = models.CharField('模板名称', max_length=100)
    template_key = models.CharField('模板编码', max_length=100, unique=True)
    table_name = models.CharField('目标表名', max_length=100, blank=True, null=True)
    file_type = models.CharField('文件类型', max_length=20, blank=True, default='xlsx')
    template_file_id = models.BigIntegerField('模板文件ID', blank=True, null=True)
    status = models.SmallIntegerField('状态', default=1)
    remark = models.CharField('备注', max_length=500, blank=True, null=True)

    class Meta:
        db_table = 'imp_template'
        managed = False
        ordering = ['-id']


class ImpTemplateColumn(models.Model):
    """导入模板列定义表（不继承 BaseModel）。"""

    id = SnowflakeIDField(primary_key=True)
    template_id = models.BigIntegerField('模板ID')
    column_name = models.CharField('字段名', max_length=100)
    column_header = models.CharField('列头名', max_length=100)
    is_required = models.SmallIntegerField('是否必填', default=0)
    data_type = models.CharField('数据类型', max_length=30, blank=True, default='string')
    max_length = models.IntegerField('最大长度', blank=True, null=True)
    regex = models.CharField('正则校验', max_length=255, blank=True, null=True)
    enum_values = models.CharField('枚举值', max_length=500, blank=True, null=True)
    sort = models.IntegerField('排序', default=0)
    is_deleted = models.SmallIntegerField('逻辑删除', default=0)

    class Meta:
        db_table = 'imp_template_column'
        managed = False
        ordering = ['sort', 'id']


class PrintTemplate(BaseModel):
    """打印模板表。"""

    id = SnowflakeIDField(primary_key=True)
    template_name = models.CharField('模板名称', max_length=100)
    template_key = models.CharField('模板编码', max_length=100, unique=True)
    biz_type = models.CharField('业务类型', max_length=50, blank=True, null=True)
    html_content = models.TextField('HTML模板内容', blank=True, null=True)
    paper_size = models.CharField('纸张大小', max_length=30, blank=True, default='A4')
    is_default = models.SmallIntegerField('是否默认', default=0)
    status = models.SmallIntegerField('状态', default=1)
    remark = models.CharField('备注', max_length=500, blank=True, null=True)

    class Meta:
        db_table = 'print_template'
        managed = False
        ordering = ['-id']