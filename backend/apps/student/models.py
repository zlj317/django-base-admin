"""学生信息表 模型（由代码生成器生成，可二次修改）。"""
from django.db import models


class BizStudent(models.Model):
    """学生信息表（biz_student）"""

    id = models.BigAutoField(primary_key=True, verbose_name='主键ID')
    name = models.CharField(verbose_name='学生姓名', max_length=50)
    age = models.IntegerField(verbose_name='年龄', null=True, blank=True)
    gender = models.SmallIntegerField(verbose_name='性别（字典sys_user_sex）', null=True, blank=True)
    phone = models.CharField(verbose_name='手机号', max_length=20, null=True, blank=True)
    email = models.CharField(verbose_name='邮箱', max_length=100, null=True, blank=True)
    enroll_date = models.DateField(verbose_name='入学日期', null=True, blank=True)
    score = models.DecimalField(verbose_name='总分', max_digits=18, decimal_places=2, null=True, blank=True)
    address = models.CharField(verbose_name='家庭住址', max_length=255, null=True, blank=True)
    remark = models.CharField(verbose_name='备注', max_length=500, null=True, blank=True)
    create_by = models.CharField(verbose_name='创建人', max_length=64, null=True, blank=True)
    create_time = models.DateTimeField(verbose_name='创建时间', null=True, blank=True)
    update_by = models.CharField(verbose_name='更新人', max_length=64, null=True, blank=True)
    update_time = models.DateTimeField(verbose_name='更新时间', null=True, blank=True)
    is_deleted = models.SmallIntegerField(verbose_name='逻辑删除', default=0)


    class Meta:
        db_table = 'biz_student'
        managed = False
        verbose_name = '学生信息表'
        ordering = ['-id']
