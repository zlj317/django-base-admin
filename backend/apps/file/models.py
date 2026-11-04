"""文件模块模型（表结构由 docs 建表 SQL 手工创建，managed=False）。"""
from django.db import models  # Django ORM 字段与模型基类
from common.fields import SnowflakeIDField  # 雪花算法主键字段

from common.utils import BaseModel  # 公共字段基类：创建/更新人、逻辑删除


class WfFile(BaseModel):
    """文件表：记录上传文件的元信息与存储路径。"""
    STORAGE_TYPE_CHOICES = (('local', '本地存储'), ('minio', 'MinIO对象存储'))  # 存储方式可选值

    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    file_name = models.CharField('存储文件名', max_length=255)  # 服务器端存储名（可能含随机后缀）
    original_name = models.CharField('原始文件名', max_length=255, blank=True, null=True)  # 上传时的原文件名
    file_ext = models.CharField('文件扩展名', max_length=32, blank=True, null=True)  # 如 pdf、xlsx
    mime_type = models.CharField('MIME类型', max_length=128, blank=True, null=True)  # 如 application/pdf
    file_size = models.BigIntegerField('文件大小(字节)', default=0)  # 字节数
    file_md5 = models.CharField('文件MD5', max_length=32, blank=True, null=True)  # 用于秒传校验
    storage_type = models.CharField('存储类型', max_length=16, choices=STORAGE_TYPE_CHOICES, default='local')  # local/minio
    storage_path = models.CharField('存储路径', max_length=500, blank=True, null=True)  # 文件实际存储路径
    bucket = models.CharField('存储桶', max_length=128, blank=True, null=True)  # MinIO 存储桶名
    biz_type = models.CharField('业务类型', max_length=64, blank=True, null=True)  # 关联业务类型
    biz_id = models.BigIntegerField('业务ID', blank=True, null=True)  # 关联业务主键
    is_private = models.SmallIntegerField('是否私有', default=0)  # 0 否 / 1 是
    is_locked = models.SmallIntegerField('是否锁定', default=0)  # 0 否 / 1 是（锁定后禁止删除）
    is_watermark = models.SmallIntegerField('是否水印', default=0)  # 0 否 / 1 是（预览时加水印）
    expire_time = models.DateTimeField('过期时间', blank=True, null=True)  # 文件过期自动清理时间
    upload_user_id = models.BigIntegerField('上传用户ID', blank=True, null=True)  # 上传者用户ID

    class Meta:
        """指定真实表名；表由 SQL 手工维护，故不参与迁移。"""
        db_table = 'wf_file'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['-id']  # 默认按主键倒序，最新上传在前


class WfFileConfig(BaseModel):
    """文件配置表：以 config_key 唯一标识一项文件相关配置。"""
    CONFIG_TYPE_CHOICES = (('upload', '上传配置'), ('preview', '预览配置'), ('storage', '存储配置'))  # 配置类型可选值

    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    config_key = models.CharField('配置键', max_length=100, unique=True)  # 参数唯一键
    config_value = models.TextField('配置值', blank=True, null=True)  # 参数值（支持 JSON 文本）
    config_name = models.CharField('配置名称', max_length=100, blank=True, null=True)  # 显示名称
    config_type = models.CharField('配置类型', max_length=16, choices=CONFIG_TYPE_CHOICES, default='upload')  # 类型
    remark = models.CharField('备注', max_length=500, blank=True, null=True)  # 备注说明

    class Meta:
        """指定真实表名；表由 SQL 手工维护，故不参与迁移。"""
        db_table = 'wf_file_config'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表


class WfFileRecycle(models.Model):
    """文件回收站表（不继承 BaseModel）：记录被删除的文件，支持恢复。"""
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    file_id = models.BigIntegerField('原文件ID')  # 关联 wf_file 主键
    file_name = models.CharField('文件名', max_length=255, blank=True, null=True)  # 删除时的文件名快照
    delete_user_id = models.BigIntegerField('删除用户ID', blank=True, null=True)  # 操作人用户ID
    delete_time = models.DateTimeField('删除时间', blank=True, null=True)  # 删除时刻
    create_time = models.DateTimeField('创建时间', blank=True, null=True)  # 入库时间

    class Meta:
        """指定真实表名；表由 SQL 手工维护，故不参与迁移。"""
        db_table = 'wf_file_recycle'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['-id']  # 默认按主键倒序，最新删除在前