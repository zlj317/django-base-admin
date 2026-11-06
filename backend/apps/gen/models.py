"""代码生成器配置表模型。"""
# 模块：apps/gen/models.py —— 代码生成器的两张配置表模型
# 用途：保存"哪张业务表要出码"以及"每个字段如何生成表单/查询/导入导出"的配置。
# 数据表：sys_gen_table（生成任务主表）、sys_gen_table_column（字段级配置表）。
# 调用方：apps/gen/engine.py 读取配置渲染代码，apps/gen/views.py 与 serializers.py 读写配置。
# 说明：两张表均由 docs 建表 SQL 手工创建，故 managed=False，不参与 migrate。
from django.db import models  # 引入 ORM 字段定义模块
from common.fields import SnowflakeIDField  # 雪花算法主键字段

from common.utils import BaseModel  # 公共基类，提供审计字段与逻辑删除标记


# 生成任务主表：一条记录对应一张已导入的业务表，是整套出码配置的根
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

    # 元信息：锁定物理表名、关闭迁移托管、指定默认排序
    class Meta:
        """模型元信息：指定表名并交由手工建表脚本维护。"""

        db_table = 'sys_gen_table'  # 固定表名，保持与建表 SQL 一致
        managed = False  # 表已由 SQL 手工创建，不参与 Django 迁移
        ordering = ['-id']  # 默认按主键倒序，新导入的配置排在前面


# 字段配置表：主表的子表，逐列描述表单控件、查询方式与导入导出开关
class SysGenTableColumn(BaseModel):
    """生成字段配置表：逐列记录表单元件、查询方式等生成选项。"""

    # 表单控件：决定前端渲染什么组件，值由导入时按列类型自动推断、之后可人工调整
    FORM_CHOICES = (  # 表单控件可选项，供前端下拉展示
        ('input', '输入框'), ('number', '数字框'), ('date', '日期选择'),
        ('select', '下拉字典'), ('radio', '单选'), ('textarea', '多行文本'),
        ('image', '图片上传'), ('file', '文件上传'),
    )
    # 查询方式：决定列表页过滤条件用等值、LIKE 还是区间比较
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

    # 元信息：锁定物理表名、关闭迁移托管，并按排序号输出保证界面顺序稳定
    class Meta:
        """模型元信息：指定表名并按排序号升序输出。"""

        db_table = 'sys_gen_table_column'  # 固定表名，保持与建表 SQL 一致
        managed = False  # 表已由 SQL 手工创建，不参与 Django 迁移
        ordering = ['sort', 'id']  # 先按排序号、再按主键，保证展示顺序稳定