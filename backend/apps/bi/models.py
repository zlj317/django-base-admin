"""大屏BI模块模型（表结构由 docs 建表 SQL 手工创建，managed=False）。"""
# 文件：apps/bi/models.py —— 大屏 BI 模块的数据模型层
# 用途：定义大屏、数据集、访问日志三张表的字段，供序列化器、视图层与渲染层读取。
# 数据表：bi_screen（大屏信息）、bi_dataset（数据集）、bi_visit_log（访问日志）。
# 路由前缀：/api/bi/screen、/api/bi/dataset、/api/bi/visit、/api/bi/screen/share/<token>。
# 说明：真实表由 docs 下的建表 SQL 手工创建，因此三个 Meta 都设置 managed = False，不参与 migrate。
from django.db import models  # Django ORM 字段与模型基类
from common.fields import SnowflakeIDField  # 雪花算法主键字段

from common.utils import BaseModel  # 公共字段基类：创建/更新人、逻辑删除


# 大屏主表：一条记录代表一个可视化大屏（画布配置 + 发布信息）
class BiScreen(BaseModel):
    """大屏信息表：存储大屏的可视化配置与发布状态。"""
    # 状态枚举：0 草稿、1 已发布、2 已下线；choices 让 Django 在写入时校验取值
    STATUS_CHOICES = ((0, '草稿'), (1, '已发布'), (2, '已下线'))  # 大屏状态可选值

    # 主键：雪花 ID，避免自增主键在高并发/分库场景下冲突
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    # 大屏中文名称，列表页与画布标题展示使用
    screen_name = models.CharField('大屏名称', max_length=200)  # 显示名称
    # 画布完整配置（尺寸、背景、组件数组）以 JSON 文本存储，读取时由 render.parse_config 解析
    screen_config = models.TextField('大屏配置', blank=True, null=True)  # LONGTEXT：组件布局+样式 JSON
    # 发布状态；默认 0 草稿，publish 动作会改为 1 并生成分享链接
    status = models.SmallIntegerField('状态', choices=STATUS_CHOICES, default=0)  # 0/1/2
    # 对外分享地址，发布时生成，形如 /bi/share/<uuid>
    share_url = models.CharField('分享链接', max_length=500, blank=True, null=True)  # 对外分享 URL
    # 分享访问密码，当前仅做存储，分享接口未做密码校验
    share_password = models.CharField('分享密码', max_length=64, blank=True, null=True)  # 访问密码
    # 自动刷新间隔（秒），0 表示前端不自动刷新
    refresh_sec = models.IntegerField('自动刷新秒数', default=60)  # 数据自动刷新间隔
    # 封面快照文件 ID，指向文件模块中的快照记录
    snapshot_file_id = models.BigIntegerField('快照文件ID', blank=True, null=True)  # 大屏封面快照文件
    # 备注，供运营/管理员补充说明
    remark = models.CharField('备注', max_length=500, blank=True, null=True)  # 备注说明

    # 元信息：绑定手工建表，禁止 Django 生成迁移
    class Meta:
        """指定真实表名；表由 SQL 手工维护，故不参与迁移。"""
        # 与建表 SQL 中一致的表名
        db_table = 'bi_screen'  # 对应数据库物理表名
        # 不参与 migrate，避免 Django 尝试建表/改表时报错
        managed = False  # 不参与 migrate 的建表/改表
        # 默认查询排序：主键倒序，最新创建的大屏在前
        ordering = ['-id']  # 默认按主键倒序


# 数据集表：大屏组件引用的数据查询定义（SQL 或外部 API）
class BiDataset(BaseModel):
    """大屏数据集表：大屏组件引用的数据查询定义。"""
    # 数据源类型枚举：mysql 走库内 SQL，api 走外部接口
    DS_TYPE_CHOICES = (('mysql', 'MySQL数据库'), ('api', '外部API'))  # 数据源类型可选值

    # 主键：雪花 ID
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    # 数据集名称，渲染时作为组件标题的兜底
    dataset_name = models.CharField('数据集名称', max_length=200)  # 显示名称
    # 数据源类型；当前渲染层只解析配置，不区分类型执行
    ds_type = models.CharField('数据源类型', max_length=16, choices=DS_TYPE_CHOICES, default='mysql')  # 类型
    # 数据集配置：mysql 类型存 SQL，api 类型存请求参数 JSON
    ds_config = models.TextField('数据集配置', blank=True, null=True)  # SQL 或 API 参数 JSON
    # 所属大屏 ID，仅作为归属标记，查询时不做强制约束
    screen_id = models.BigIntegerField('所属大屏ID', blank=True, null=True)  # 关联 bi_screen 主键
    # 状态：0 正常、1 停用；渲染层当前未按状态过滤
    status = models.SmallIntegerField('状态', default=0)  # 0 正常 / 1 停用
    # 备注，供配置说明
    remark = models.CharField('备注', max_length=500, blank=True, null=True)  # 备注说明

    # 元信息：绑定手工建表，禁止 Django 生成迁移
    class Meta:
        """指定真实表名；表由 SQL 手工维护，故不参与迁移。"""
        # 与建表 SQL 中一致的表名
        db_table = 'bi_dataset'  # 对应数据库物理表名
        # 不参与 migrate
        managed = False  # 不参与 migrate 的建表/改表
        # 默认按主键倒序
        ordering = ['-id']  # 默认按主键倒序


# 访问日志表：不继承 BaseModel（日志只追加，无需审计人、逻辑删除列）
class BiVisitLog(models.Model):
    """大屏访问日志表（不继承 BaseModel）：记录大屏被访问的痕迹。"""
    # 主键：雪花 ID，日志量较大时也能保持唯一与有序
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    # 被访问的大屏 ID，对应 bi_screen.id
    screen_id = models.BigIntegerField('大屏ID')  # 关联 bi_screen 主键
    # 访问用户 ID；匿名/未登录访问时为空
    visitor_user_id = models.BigIntegerField('访问用户ID', blank=True, null=True)  # 登录用户 ID，匿名则空
    # 访问来源 IP，优先取反向代理透传的真实 IP
    visit_ip = models.CharField('访问IP', max_length=50, blank=True, null=True)  # 客户端 IP
    # 访问发生时刻
    visit_time = models.DateTimeField('访问时间', blank=True, null=True)  # 访问发生时刻
    # 记录入库时刻；日志表无 BaseModel，故单独声明
    create_time = models.DateTimeField('创建时间', blank=True, null=True)  # 入库时间

    # 元信息：绑定手工建表，禁止 Django 生成迁移
    class Meta:
        """指定真实表名；表由 SQL 手工维护，故不参与迁移。"""
        # 与建表 SQL 中一致的表名
        db_table = 'bi_visit_log'  # 对应数据库物理表名
        # 不参与 migrate
        managed = False  # 不参与 migrate 的建表/改表
        # 默认按主键倒序，最新访问记录在前
        ordering = ['-id']  # 默认按主键倒序，最新访问在前