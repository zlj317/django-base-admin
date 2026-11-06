"""导入模板 + 打印模板模块模型。"""
# 模块：apps/imprint/models.py —— 导入模板 / 模板列定义 / 打印模板三张表的 ORM 映射。
# 用途：为“导入模板管理”“导入模板列”“打印模板管理”页面提供数据访问层。
# 对应表：imp_template（导入模板主表）、imp_template_column（列级校验规则）、print_template（打印模板）。
# 路由前缀：/api/imprint/（见 config/urls.py），下挂 template、column、print 三组 CRUD。
# 幂等性：本文件只做表结构映射，不写数据；菜单初始化由 seed.py 负责且可重复执行。
from django.db import models
# 雪花算法主键字段：全局唯一且趋势递增，替代自增主键
from common.fields import SnowflakeIDField  # 雪花算法主键字段

# 通用基类：提供 create_by/create_time/update_by/update_time/is_deleted 等审计字段
from common.utils import BaseModel


# 导入模板主表：一条记录描述“一个 Excel 导入方案”，列级规则拆到 ImpTemplateColumn。
class ImpTemplate(BaseModel):
    """导入模板表。"""

    # 主键改用雪花 ID：对外不暴露自增规模，也是全库统一的 ID 方案
    id = SnowflakeIDField(primary_key=True)
    # 模板显示名，列表主要检索字段
    template_name = models.CharField('模板名称', max_length=100)
    # 业务唯一键：编码重复会导致导入逻辑取错模板，故加 unique
    template_key = models.CharField('模板编码', max_length=100, unique=True)
    # 导入落库的目标物理表；空值表示只做校验不落库
    table_name = models.CharField('目标表名', max_length=100, blank=True, null=True)
    # 允许上传的模板文件后缀，默认 xlsx
    file_type = models.CharField('文件类型', max_length=20, blank=True, default='xlsx')
    # 关联 wf_file 的文件主键，供用户下载标准模板
    template_file_id = models.BigIntegerField('模板文件ID', blank=True, null=True)
    # 1=启用 0=停用；停用后前端应隐藏导入入口
    status = models.SmallIntegerField('状态', default=1)
    # 运维说明，不影响业务逻辑
    remark = models.CharField('备注', max_length=500, blank=True, null=True)

    class Meta:
        # 显式表名，与手写建表 SQL 对齐
        db_table = 'imp_template'
        # 表由 SQL 手工创建，Django 不参与建表/迁移
        managed = False
        # 默认主键倒序：最新模板排在最前
        ordering = ['-id']


# 列定义表：每行对应模板中的一列（Excel 列头 → 目标字段），承载必填/类型/长度/正则/枚举等校验规则。
# 不继承 BaseModel：该表没有审计字段，只有 is_deleted，所以模型层单独声明删除标记。
class ImpTemplateColumn(models.Model):
    """导入模板列定义表（不继承 BaseModel）。"""

    # 雪花主键，与主表使用同一套 ID 生成策略
    id = SnowflakeIDField(primary_key=True)
    # 外键语义指向 ImpTemplate.id；未用 ForeignKey 以兼容手工 SQL
    template_id = models.BigIntegerField('模板ID')
    # 落库时的目标字段名（英文/下划线命名）
    column_name = models.CharField('字段名', max_length=100)
    # Excel 首行的中文列头，解析时按此匹配
    column_header = models.CharField('列头名', max_length=100)
    # 1=必填、0=可空；解析阶段据此报缺失
    is_required = models.SmallIntegerField('是否必填', default=0)
    # 校验/转换类型：string/int/decimal/date 等
    data_type = models.CharField('数据类型', max_length=30, blank=True, default='string')
    # 字符串最大长度；空值表示不限制
    max_length = models.IntegerField('最大长度', blank=True, null=True)
    # 自定义正则；空值表示不做格式校验
    regex = models.CharField('正则校验', max_length=255, blank=True, null=True)
    # 逗号分隔的合法取值，用于下拉/枚举校验
    enum_values = models.CharField('枚举值', max_length=500, blank=True, null=True)
    # 列在模板中的展示/解析顺序，值越小越靠前
    sort = models.IntegerField('排序', default=0)
    # 0=未删除、1=已删除；查询时必须带上该条件
    is_deleted = models.SmallIntegerField('逻辑删除', default=0)

    class Meta:
        # 与手写 SQL 建表名一致
        db_table = 'imp_template_column'
        # 手写建表，禁用 Django 迁移管理
        managed = False
        # 默认按列顺序再按 ID 排序，保证模板列展示稳定
        ordering = ['sort', 'id']


# 打印模板表：保存可直接渲染的 HTML 片段（含占位符），按业务类型/纸张大小供打印使用。
class PrintTemplate(BaseModel):
    """打印模板表。"""

    # 雪花主键，与导入模板保持一致的 ID 方案
    id = SnowflakeIDField(primary_key=True)
    # 打印模板显示名，前端列表主要字段
    template_name = models.CharField('模板名称', max_length=100)
    # 业务唯一键，渲染时用它定位模板
    template_key = models.CharField('模板编码', max_length=100, unique=True)
    # 归属业务（如 order/invoice），用于按业务筛模板
    biz_type = models.CharField('业务类型', max_length=50, blank=True, null=True)
    # 模板正文，通常含 {{占位符}} 由前端/后端替换
    html_content = models.TextField('HTML模板内容', blank=True, null=True)
    # 打印纸张规格，默认 A4
    paper_size = models.CharField('纸张大小', max_length=30, blank=True, default='A4')
    # 1=同 biz_type 下的默认模板，0=普通模板
    is_default = models.SmallIntegerField('是否默认', default=0)
    # 1=启用 0=停用；停用模板不应被选用
    status = models.SmallIntegerField('状态', default=1)
    # 备注说明，便于业务方辨认
    remark = models.CharField('备注', max_length=500, blank=True, null=True)

    class Meta:
        # 表名与手写 SQL 一致
        db_table = 'print_template'
        # 表由手工创建，迁移时跳过
        managed = False
        # 主键倒序，最新创建的模板优先展示
        ordering = ['-id']