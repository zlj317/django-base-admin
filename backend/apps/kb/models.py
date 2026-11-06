# 文件：apps/kb/models.py —— 知识库模块的 ORM 模型定义
# 用途：把手工创建的分类表、文档表、收藏表映射成 Django 模型，供视图集与序列化器读写。
# 对应表：kb_category（分类）、kb_document（文档）、kb_favorite（收藏）。
# 路由前缀：api/kb/category/、api/kb/document/、api/kb/favorite/（由 apps/kb/urls.py 生成）。
# 关键约定：三张表均由手工建表 SQL 创建，故 Meta 中 managed=False，migrate 不会建表/改表；
#           KBCategory/KBDocument 继承 BaseModel（带审计列与 is_deleted），KBFavorite 是纯关系表、不继承。
"""知识库模块模型（表由建表 SQL 手工创建，managed=False）。"""
# Django ORM 字段与模型基类，用来声明各列的类型
from django.db import models  # Django ORM 字段与模型基类
# 雪花算法主键字段：数据库列为 BIGINT，ID 由后端生成，不走数据库自增
from common.fields import SnowflakeIDField  # 雪花算法主键字段

# 公共字段基类：创建/更新人、逻辑删除标记
from common.utils import BaseModel  # 公共字段基类：创建/更新人、逻辑删除


# 分类表：通过 parent_id 自关联形成树，用于知识库左侧分类导航
class KBCategory(BaseModel):
    """知识库分类表：支持树形结构。"""
    # 主键：实例化时由雪花算法生成，不走数据库自增
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    # 分类名称，树节点展示文本
    category_name = models.CharField('分类名称', max_length=100)  # 分类显示名称
    # 父分类 ID：0 表示顶级，与 common.utils.build_tree 的 root_parent 约定一致
    parent_id = models.BigIntegerField('父分类ID', default=0)  # 0 为顶级分类
    # 排序值：数值越小越靠前，同层级内生效
    sort = models.IntegerField('排序', default=0)  # 排序值，数值小排前
    # 状态用 tinyint：1 启用、0 停用，停用后前端可选择不展示该分类
    status = models.SmallIntegerField('状态', default=1)  # 1 启用 / 0 停用
    # 备注列允许为空，用于补充说明分类用途
    remark = models.CharField('备注', max_length=500, blank=True, null=True)  # 备注说明

    # 内部 Meta：声明物理表名、关闭 migrate 管理、指定默认排序
    class Meta:
        db_table = 'kb_category'  # 对应数据库物理表名
        # 关闭 migrate 管理：表结构以手工建表 SQL 为准，Django 不建表也不改表
        managed = False  # 不参与 migrate 的建表/改表
        # 先按 sort 升序，再按 id 升序，保证同序号时顺序稳定
        ordering = ['sort', 'id']  # 先按 sort 再按 id 升序


# 文档表：知识库的核心内容实体，支持富文本正文与附件
class KBDocument(BaseModel):
    """知识库文档表：存储文档主体信息与内容。"""
    # 主键：雪花算法生成，前端以字符串形式接收避免精度丢失
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    # 所属分类：允许为空，表示未归类文档
    category_id = models.BigIntegerField('所属分类ID', blank=True, null=True)  # 关联 kb_category
    # 标题必填，列表与搜索结果中展示
    doc_title = models.CharField('文档标题', max_length=200)  # 文档标题
    # 正文为富文本 HTML，允许为空以支持先建标题后补内容
    doc_content = models.TextField('文档内容', blank=True, null=True)  # 文档正文（富文本）
    # 附件只存文件表的主键 file_id，不保存物理路径，便于复用文件模块的下载/预览能力
    file_id = models.BigIntegerField('附件文件ID', blank=True, null=True)  # 关联文件表
    # 标签用逗号分隔的字符串存储，兼容手工表的 varchar 列
    tags = models.CharField('标签', max_length=255, blank=True, null=True)  # 标签列表，逗号分隔
    # 作者 ID：用于按作者筛选与权限判断
    author_id = models.BigIntegerField('作者ID', blank=True, null=True)  # 文档作者
    # 权限类型决定可见范围：public/private/role，默认公开
    permission_type = models.CharField('权限类型', max_length=20, default='public')  # public/private/role
    # 当权限类型为 role 时生效，存允许访问的角色 ID 列表 JSON 字符串
    role_json = models.CharField('可见角色列表', max_length=500, blank=True, null=True)  # 允许访问的角色ID列表 JSON
    # 阅读次数在查看详情时累加，用于统计热度
    read_count = models.IntegerField('阅读次数', default=0)  # 被阅读累计次数
    # 版本号从 1 开始，编辑内容时可自增以区分历史版本
    version = models.IntegerField('版本号', default=1)  # 当前版本号
    # 状态：1 已发布、0 草稿，列表默认展示已发布
    status = models.SmallIntegerField('状态', default=1)  # 1 已发布 / 0 草稿

    # 内部 Meta：手工表映射与默认排序
    class Meta:
        db_table = 'kb_document'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        # 雪花 ID 单调递增，按 id 倒序等价于按创建顺序倒序，最新文档排最前
        ordering = ['-id']  # 最新文档在前


# 收藏表：用户与文档的多对多关系，一条记录代表一次收藏
class KBFavorite(models.Model):
    """知识收藏表（不继承 BaseModel）：记录用户收藏的文档。"""
    # 主键：雪花算法生成，便于前端精确传递
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    # 被收藏的文档主键；不用外键，保持与手工表结构一致
    doc_id = models.BigIntegerField('文档ID')  # 关联 kb_document 主键
    # 收藏人主键，用于"我的收藏"列表过滤
    user_id = models.BigIntegerField('收藏用户ID')  # 执行收藏的用户
    # 该表不继承 BaseModel，只保留创建时间，没有审计人与逻辑删除
    create_time = models.DateTimeField('创建时间', blank=True, null=True)  # 收藏时刻

    # 内部 Meta：手工表映射与默认排序
    class Meta:
        db_table = 'kb_favorite'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['-id']  # 最新收藏在前