"""学生信息表 模型（由代码生成器生成，可二次修改）。"""
# 模块用途：学生信息表（biz_student）的 ORM 模型，定义字段、主键与数据库表映射。
# 对应表：biz_student；managed=False 表示建表/改表由外部 SQL 脚本负责，ORM 只读写、不生成迁移。
# 被谁引用：apps/student/serializers.py（字段映射）、apps/student/views.py（查询、写入、导入导出）。
# 生成约定：模型类名 Biz+表名驼峰；主键统一 SnowflakeIDField；字段顺序为业务字段在前、审计字段在后；
#           审计字段 create_by/create_time/update_by/update_time/is_deleted 由生成器自动补齐。
# 说明：本模型直接继承 models.Model（未复用 common.utils.BaseModel），是生成器的独立写法，故审计字段逐个显式声明。
from django.db import models  # 引入 Django ORM 模型模块
from common.fields import SnowflakeIDField  # 雪花算法主键字段


# 一个业务表对应一个模型类，类名由表名驼峰化得到，便于按表名反查模型。
class BizStudent(models.Model):  # 学生信息表模型，对应数据库表 biz_student
    """学生信息表（biz_student）"""

    # 字段声明顺序与建表 SQL 的列顺序一致，便于人工核对表结构。
    # 主键使用 SnowflakeIDField：实例化时由 common.fields 自动生成 64 位 ID，不依赖数据库自增。
    id = SnowflakeIDField(primary_key=True, verbose_name='主键ID')  # 自增主键
    name = models.CharField(verbose_name='学生姓名', max_length=50)  # 学生姓名，必填，最长 50 字符
    # 可空约定：除 name 外所有业务字段均 null=True/blank=True，前端留空或 Excel 缺列时不会校验失败。
    # 类型约定：整数/小整数/定点小数/日期分别对应建表 SQL 的 INT/SMALLINT/DECIMAL/DATE 列。
    # 字典约定：gender 只存字典值（整数），中文含义由字典 sys_user_sex 在前端翻译展示。
    age = models.IntegerField(verbose_name='年龄', null=True, blank=True)  # 年龄，允许为空
    gender = models.SmallIntegerField(verbose_name='性别（字典sys_user_sex）', null=True, blank=True)  # 性别，存字典值，允许为空
    phone = models.CharField(verbose_name='手机号', max_length=20, null=True, blank=True)  # 手机号，允许为空
    email = models.CharField(verbose_name='邮箱', max_length=100, null=True, blank=True)  # 邮箱，允许为空
    enroll_date = models.DateField(verbose_name='入学日期', null=True, blank=True)  # 入学日期，允许为空
    score = models.DecimalField(verbose_name='总分', max_digits=18, decimal_places=2, null=True, blank=True)  # 总分，保留两位小数
    address = models.CharField(verbose_name='家庭住址', max_length=255, null=True, blank=True)  # 家庭住址，允许为空
    remark = models.CharField(verbose_name='备注', max_length=500, null=True, blank=True)  # 备注，允许为空
    # 以下为审计字段与逻辑删除标记：统一由视图写入，不对外开放写入，避免前端伪造操作人。
    # is_deleted 取 0 未删除、1 已删除；列表、详情、更新、删除等查询都必须带 is_deleted=0 条件。
    create_by = models.CharField(verbose_name='创建人', max_length=64, null=True, blank=True)  # 创建人用户名
    create_time = models.DateTimeField(verbose_name='创建时间', null=True, blank=True)  # 创建时间
    update_by = models.CharField(verbose_name='更新人', max_length=64, null=True, blank=True)  # 更新人用户名
    update_time = models.DateTimeField(verbose_name='更新时间', null=True, blank=True)  # 更新时间
    is_deleted = models.SmallIntegerField(verbose_name='逻辑删除', default=0)  # 逻辑删除标记，0 未删除、1 已删除


    # Meta 约定：显式 db_table 指定物理表名；managed=False 阻止 migrate 建表/改表；
    # ordering 按 -id，保证后台列表默认最新记录在前，且分页顺序稳定。
    class Meta:  # 模型元信息
        """模型元信息：固定表名并交由手工建表脚本维护。"""

        db_table = 'biz_student'  # 指定数据库表名
        managed = False  # 由外部脚本建表，不纳入 Django 迁移管理
        verbose_name = '学生信息表'  # 后台展示名称
        ordering = ['-id']  # 查询默认按主键倒序