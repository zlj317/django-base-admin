"""代码生成器配置表模型。"""
from django.db import models  # 引入 ORM 字段定义模块
from common.fields import SnowflakeIDField  # 雪花算法主键字段

from common.utils import BaseModel  # 公共基类，提供审计字段与逻辑删除标记


class SysGenTable(BaseModel):
    """生成任务主表：记录一张业务表导入后形成的代码生成配置。"""

    id = SnowflakeIDField(primary_key=True)  # 自增主键，显式声明以保证与库结构一致
    table_name = models.CharField('数据库表名', max_length=100, unique=True)  # 源表名，唯一防止重复导入
    table_comment = models.CharField('表注释', max_length=200, blank=True, null=True)  # 表中文名，用于菜单与标题展示
    class_name = models.CharField('实体类名', max_length=100, blank=True, null=True)  # 生成模型类名，如 BizStudent
    module_name = models.CharField('模块英文标识', max_length=50, blank=True, null=True)  # 生成模块名，决定目录与权限前缀
    module_comment = models.CharField('模块中文名称', max_length=100, blank=True, null=True)  # 模块中文名，用于页面标题
    url_prefix = models.CharField('接口路由前缀', max_length=100, blank=True, null=True)  # 生成接口的路由前缀，如 /api/xxx
    gen_path = models.CharField('前端页面存放路径', max_length=255, blank=True, null=True)  # 生成 Vue 页面相对路径
    parent_menu_id = models.BigIntegerField('父级菜单ID', blank=True, null=True)  # 下载时据此挂载并注册业务菜单
    is_delete_logic = models.BooleanField('是否逻辑删除', default=True)  # 控制生成的查询是否带 is_deleted 过滤
    import_enable = models.BooleanField('是否开启导入', default=True)  # 决定是否生成 Excel 导入相关内容
    export_enable = models.BooleanField('是否开启导出', default=True)  # 决定是否生成 Excel 导出相关内容

    class Meta:
        """模型元信息：指定表名并交由手工建表脚本维护。"""

        db_table = 'sys_gen_table'  # 固定表名，保持与建表 SQL 一致
        managed = False  # 表已由 SQL 手工创建，不参与 Django 迁移
        ordering = ['-id']  # 默认按主键倒序，新导入的配置排在前面


class SysGenTableColumn(BaseModel):
    """生成字段配置表：逐列记录表单元件、查询方式等生成选项。"""

    FORM_CHOICES = (  # 表单控件可选项，供前端下拉展示
        ('input', '输入框'), ('number', '数字框'), ('date', '日期选择'),
        ('select', '下拉字典'), ('radio', '单选'), ('textarea', '多行文本'),
        ('image', '图片上传'), ('file', '文件上传'),
    )
    QUERY_CHOICES = (  # 查询方式可选项，决定列表过滤条件的生成逻辑
        ('eq', '等于'), ('like', '模糊'), ('gt', '大于'),
        ('lt', '小于'), ('between', '区间'),
    )

    id = SnowflakeIDField(primary_key=True)  # 自增主键，逐列唯一标识
    gen_table_id = models.BigIntegerField('生成任务ID')  # 所属生成任务，逻辑外键关联 SysGenTable
    column_name = models.CharField('字段名', max_length=100)  # 源表列名，生成代码时直接使用
    column_comment = models.CharField('字段注释', max_length=200, blank=True, null=True)  # 列中文名，作为表单标签
    column_type = models.CharField('字段类型', max_length=50, blank=True, null=True)  # 原始列类型，如 varchar(50)
    is_pk = models.BooleanField('是否主键', default=False)  # 标记主键列，主键列不参与表单与查询配置
    dict_type = models.CharField('字典编码', max_length=100, blank=True, null=True)  # 下拉/单选使用的字典编码
    form_type = models.CharField('表单控件', max_length=50, blank=True, null=True)  # 表单控件类型，对应 FORM_CHOICES
    is_list = models.BooleanField('列表展示', default=True)  # 是否在列表页输出该列
    is_query = models.BooleanField('查询条件', default=False)  # 是否作为查询条件参与过滤
    query_type = models.CharField('查询方式', max_length=20, blank=True, null=True)  # 查询方式，对应 QUERY_CHOICES
    is_required = models.BooleanField('是否必填', default=False)  # 是否作为必填表单项生成前端校验
    is_export = models.BooleanField('是否导出', default=True)  # 是否写入导出 Excel 的列
    is_import = models.BooleanField('是否导入', default=True)  # 是否作为导入模板的可填列
    sort = models.IntegerField('排序号', default=0)  # 列顺序，决定表单与列表的展示先后

    class Meta:
        """模型元信息：指定表名并按排序号升序输出。"""

        db_table = 'sys_gen_table_column'  # 固定表名，保持与建表 SQL 一致
        managed = False  # 表已由 SQL 手工创建，不参与 Django 迁移
        ordering = ['sort', 'id']  # 先按排序号、再按主键，保证展示顺序稳定