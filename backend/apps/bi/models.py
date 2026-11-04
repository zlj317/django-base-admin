"""大屏BI模块模型（表结构由 docs 建表 SQL 手工创建，managed=False）。"""
from django.db import models  # Django ORM 字段与模型基类
from common.fields import SnowflakeIDField  # 雪花算法主键字段

from common.utils import BaseModel  # 公共字段基类：创建/更新人、逻辑删除


class BiScreen(BaseModel):
    """大屏信息表：存储大屏的可视化配置与发布状态。"""
    STATUS_CHOICES = ((0, '草稿'), (1, '已发布'), (2, '已下线'))  # 大屏状态可选值

    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    screen_name = models.CharField('大屏名称', max_length=200)  # 显示名称
    screen_config = models.TextField('大屏配置', blank=True, null=True)  # LONGTEXT：组件布局+样式 JSON
    status = models.SmallIntegerField('状态', choices=STATUS_CHOICES, default=0)  # 0/1/2
    share_url = models.CharField('分享链接', max_length=500, blank=True, null=True)  # 对外分享 URL
    share_password = models.CharField('分享密码', max_length=64, blank=True, null=True)  # 访问密码
    refresh_sec = models.IntegerField('自动刷新秒数', default=60)  # 数据自动刷新间隔
    snapshot_file_id = models.BigIntegerField('快照文件ID', blank=True, null=True)  # 大屏封面快照文件
    remark = models.CharField('备注', max_length=500, blank=True, null=True)  # 备注说明

    class Meta:
        """指定真实表名；表由 SQL 手工维护，故不参与迁移。"""
        db_table = 'bi_screen'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['-id']  # 默认按主键倒序


class BiDataset(BaseModel):
    """大屏数据集表：大屏组件引用的数据查询定义。"""
    DS_TYPE_CHOICES = (('mysql', 'MySQL数据库'), ('api', '外部API'))  # 数据源类型可选值

    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    dataset_name = models.CharField('数据集名称', max_length=200)  # 显示名称
    ds_type = models.CharField('数据源类型', max_length=16, choices=DS_TYPE_CHOICES, default='mysql')  # 类型
    ds_config = models.TextField('数据集配置', blank=True, null=True)  # SQL 或 API 参数 JSON
    screen_id = models.BigIntegerField('所属大屏ID', blank=True, null=True)  # 关联 bi_screen 主键
    status = models.SmallIntegerField('状态', default=0)  # 0 正常 / 1 停用
    remark = models.CharField('备注', max_length=500, blank=True, null=True)  # 备注说明

    class Meta:
        """指定真实表名；表由 SQL 手工维护，故不参与迁移。"""
        db_table = 'bi_dataset'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['-id']  # 默认按主键倒序


class BiVisitLog(models.Model):
    """大屏访问日志表（不继承 BaseModel）：记录大屏被访问的痕迹。"""
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    screen_id = models.BigIntegerField('大屏ID')  # 关联 bi_screen 主键
    visitor_user_id = models.BigIntegerField('访问用户ID', blank=True, null=True)  # 登录用户 ID，匿名则空
    visit_ip = models.CharField('访问IP', max_length=50, blank=True, null=True)  # 客户端 IP
    visit_time = models.DateTimeField('访问时间', blank=True, null=True)  # 访问发生时刻
    create_time = models.DateTimeField('创建时间', blank=True, null=True)  # 入库时间

    class Meta:
        """指定真实表名；表由 SQL 手工维护，故不参与迁移。"""
        db_table = 'bi_visit_log'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['-id']  # 默认按主键倒序，最新访问在前