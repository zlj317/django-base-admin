"""公告模块模型（表结构由 docs 建表 SQL 手工创建，managed=False）。"""
from django.db import models  # Django ORM 字段与模型基类

from common.utils import BaseModel  # 公共字段基类：创建/更新人、逻辑删除


class NoticeCategory(BaseModel):
    """公告分类表：组织公告的类别，支持排序与启用/停用。"""
    id = models.BigAutoField(primary_key=True)  # 主键，自增
    category_name = models.CharField('分类名称', max_length=100)  # 分类显示名
    category_code = models.CharField('分类编码', max_length=64, blank=True, null=True)  # 程序引用编码
    sort = models.IntegerField('排序', default=0)  # 同级显示顺序，越小越靠前
    status = models.SmallIntegerField('状态', default=0)  # 0 正常 / 1 停用
    remark = models.CharField('备注', max_length=500, blank=True, null=True)  # 备注说明

    class Meta:
        """指定真实表名；表由 SQL 手工维护，故不参与迁移。"""
        db_table = 'notice_category'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['sort', 'id']  # 默认排序：排序号、主键升序


class NoticeInfo(BaseModel):
    """公告信息表：存储公告正文、发布范围及状态。"""
    STATUS_CHOICES = ((0, '草稿'), (1, '已发布'), (2, '已下线'))  # 公告状态可选值

    id = models.BigAutoField(primary_key=True)  # 主键，自增
    category_id = models.BigIntegerField('分类ID', blank=True, null=True)  # 关联 notice_category 主键
    title = models.CharField('公告标题', max_length=200)  # 公告标题
    content = models.TextField('公告正文', blank=True, null=True)  # 富文本正文
    attachment_ids = models.CharField('附件ID列表', max_length=1000, blank=True, null=True)  # 逗号分隔的文件 ID
    is_top = models.SmallIntegerField('是否置顶', default=0)  # 0 否 / 1 是
    status = models.SmallIntegerField('状态', choices=STATUS_CHOICES, default=0)  # 0/1/2
    role_scope = models.TextField('可见角色范围', blank=True, null=True)  # JSON 数组，可角色编码列表，空=全部
    start_time = models.DateTimeField('生效开始时间', blank=True, null=True)  # 定时发布
    end_time = models.DateTimeField('生效结束时间', blank=True, null=True)  # 定时下线
    publish_user_id = models.BigIntegerField('发布人ID', blank=True, null=True)  # 发布者用户 ID
    publish_time = models.DateTimeField('发布时间', blank=True, null=True)  # 实际发布时刻

    class Meta:
        """指定真实表名；表由 SQL 手工维护，故不参与迁移。"""
        db_table = 'notice_info'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['-is_top', '-id']  # 置顶优先，再按主键倒序


class NoticeRead(models.Model):
    """公告阅读记录表（不继承 BaseModel）：记录用户阅读公告的痕迹。"""
    id = models.BigAutoField(primary_key=True)  # 主键，自增
    notice_id = models.BigIntegerField('公告ID')  # 关联 notice_info 主键
    user_id = models.BigIntegerField('阅读用户ID')  # 阅读者用户 ID
    read_time = models.DateTimeField('阅读时间', blank=True, null=True)  # 实际阅读时刻
    create_time = models.DateTimeField('创建时间', blank=True, null=True)  # 入库时间

    class Meta:
        """指定真实表名；表由 SQL 手工维护，故不参与迁移。"""
        db_table = 'notice_read'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['-id']  # 默认按主键倒序
