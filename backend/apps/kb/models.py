"""知识库模块模型（表由建表 SQL 手工创建，managed=False）。"""
from django.db import models  # Django ORM 字段与模型基类
from common.fields import SnowflakeIDField  # 雪花算法主键字段

from common.utils import BaseModel  # 公共字段基类：创建/更新人、逻辑删除


class KBCategory(BaseModel):
    """知识库分类表：支持树形结构。"""
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    category_name = models.CharField('分类名称', max_length=100)  # 分类显示名称
    parent_id = models.BigIntegerField('父分类ID', default=0)  # 0 为顶级分类
    sort = models.IntegerField('排序', default=0)  # 排序值，数值小排前
    status = models.SmallIntegerField('状态', default=1)  # 1 启用 / 0 停用
    remark = models.CharField('备注', max_length=500, blank=True, null=True)  # 备注说明

    class Meta:
        db_table = 'kb_category'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['sort', 'id']  # 先按 sort 再按 id 升序


class KBDocument(BaseModel):
    """知识库文档表：存储文档主体信息与内容。"""
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    category_id = models.BigIntegerField('所属分类ID', blank=True, null=True)  # 关联 kb_category
    doc_title = models.CharField('文档标题', max_length=200)  # 文档标题
    doc_content = models.TextField('文档内容', blank=True, null=True)  # 文档正文（富文本）
    file_id = models.BigIntegerField('附件文件ID', blank=True, null=True)  # 关联文件表
    tags = models.CharField('标签', max_length=255, blank=True, null=True)  # 标签列表，逗号分隔
    author_id = models.BigIntegerField('作者ID', blank=True, null=True)  # 文档作者
    permission_type = models.CharField('权限类型', max_length=20, default='public')  # public/private/role
    role_json = models.CharField('可见角色列表', max_length=500, blank=True, null=True)  # 允许访问的角色ID列表 JSON
    read_count = models.IntegerField('阅读次数', default=0)  # 被阅读累计次数
    version = models.IntegerField('版本号', default=1)  # 当前版本号
    status = models.SmallIntegerField('状态', default=1)  # 1 已发布 / 0 草稿

    class Meta:
        db_table = 'kb_document'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['-id']  # 最新文档在前


class KBFavorite(models.Model):
    """知识收藏表（不继承 BaseModel）：记录用户收藏的文档。"""
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    doc_id = models.BigIntegerField('文档ID')  # 关联 kb_document 主键
    user_id = models.BigIntegerField('收藏用户ID')  # 执行收藏的用户
    create_time = models.DateTimeField('创建时间', blank=True, null=True)  # 收藏时刻

    class Meta:
        db_table = 'kb_favorite'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['-id']  # 最新收藏在前