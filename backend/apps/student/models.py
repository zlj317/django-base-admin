"""学生信息表 模型（由代码生成器生成，可二次修改）。"""
from django.db import models  # 引入 Django ORM 模型模块


class BizStudent(models.Model):  # 学生信息表模型，对应数据库表 biz_student
    """学生信息表（biz_student）"""

    id = models.BigAutoField(primary_key=True, verbose_name='主键ID')  # 自增主键
    name = models.CharField(verbose_name='学生姓名', max_length=50)  # 学生姓名，必填，最长 50 字符
    age = models.IntegerField(verbose_name='年龄', null=True, blank=True)  # 年龄，允许为空
    gender = models.SmallIntegerField(verbose_name='性别（字典sys_user_sex）', null=True, blank=True)  # 性别，存字典值，允许为空
    phone = models.CharField(verbose_name='手机号', max_length=20, null=True, blank=True)  # 手机号，允许为空
    email = models.CharField(verbose_name='邮箱', max_length=100, null=True, blank=True)  # 邮箱，允许为空
    enroll_date = models.DateField(verbose_name='入学日期', null=True, blank=True)  # 入学日期，允许为空
    score = models.DecimalField(verbose_name='总分', max_digits=18, decimal_places=2, null=True, blank=True)  # 总分，保留两位小数
    address = models.CharField(verbose_name='家庭住址', max_length=255, null=True, blank=True)  # 家庭住址，允许为空
    remark = models.CharField(verbose_name='备注', max_length=500, null=True, blank=True)  # 备注，允许为空
    create_by = models.CharField(verbose_name='创建人', max_length=64, null=True, blank=True)  # 创建人用户名
    create_time = models.DateTimeField(verbose_name='创建时间', null=True, blank=True)  # 创建时间
    update_by = models.CharField(verbose_name='更新人', max_length=64, null=True, blank=True)  # 更新人用户名
    update_time = models.DateTimeField(verbose_name='更新时间', null=True, blank=True)  # 更新时间
    is_deleted = models.SmallIntegerField(verbose_name='逻辑删除', default=0)  # 逻辑删除标记，0 未删除、1 已删除


    class Meta:  # 模型元信息
        """模型元信息：固定表名并交由手工建表脚本维护。"""

        db_table = 'biz_student'  # 指定数据库表名
        managed = False  # 由外部脚本建表，不纳入 Django 迁移管理
        verbose_name = '学生信息表'  # 后台展示名称
        ordering = ['-id']  # 查询默认按主键倒序
