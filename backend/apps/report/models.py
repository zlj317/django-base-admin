"""报表模块模型（表结构由 docs 建表 SQL 手工创建，managed=False）。"""
from django.db import models  # Django ORM 字段与模型基类
from common.fields import SnowflakeIDField  # 雪花算法主键字段

from common.utils import BaseModel  # 公共字段基类：创建/更新人、逻辑删除


class RpCategory(BaseModel):
    """报表分类表：组织报表模板的类别，支持排序与启用/停用。"""
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    category_name = models.CharField('分类名称', max_length=100)  # 分类显示名
    sort = models.IntegerField('排序', default=0)  # 同级显示顺序，越小越靠前
    status = models.SmallIntegerField('状态', default=0)  # 0 正常 / 1 停用
    remark = models.CharField('备注', max_length=500, blank=True, null=True)  # 备注说明

    class Meta:
        """指定真实表名；表由 SQL 手工维护，故不参与迁移。"""
        db_table = 'rp_category'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['sort', 'id']  # 默认排序：排序号、主键升序


class RpDatasource(BaseModel):
    """报表数据源表：定义报表可引用的数据源连接。"""
    DS_TYPE_CHOICES = (('mysql', 'MySQL数据库'), ('api', '外部API'))  # 数据源类型可选值

    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    ds_name = models.CharField('数据源名称', max_length=100)  # 显示名称
    ds_type = models.CharField('数据源类型', max_length=16, choices=DS_TYPE_CHOICES, default='mysql')  # 类型
    ds_config = models.TextField('数据源配置', blank=True, null=True)  # JSON 文本，含连接参数
    status = models.SmallIntegerField('状态', default=0)  # 0 正常 / 1 停用
    remark = models.CharField('备注', max_length=500, blank=True, null=True)  # 备注说明

    class Meta:
        """指定真实表名；表由 SQL 手工维护，故不参与迁移。"""
        db_table = 'rp_datasource'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['-id']  # 默认按主键倒序


class RpTemplate(BaseModel):
    """报表模板表：存储报表的查询与呈现定义。"""
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    template_name = models.CharField('模板名称', max_length=200)  # 显示名称
    template_key = models.CharField('模板编码', max_length=100, blank=True, null=True)  # 程序引用编码
    category_id = models.BigIntegerField('分类ID', blank=True, null=True)  # 关联 rp_category 主键
    ds_id = models.BigIntegerField('数据源ID', blank=True, null=True)  # 关联 rp_datasource 主键
    template_json = models.TextField('模板配置', blank=True, null=True)  # LONGTEXT：查询语句+图表配置 JSON
    version = models.IntegerField('版本号', default=1)  # 模板版本，用于灰度或回滚
    status = models.SmallIntegerField('状态', default=0)  # 0 正常 / 1 停用
    permission_json = models.TextField('权限配置(JSON)', blank=True, null=True)  # 可见角色/用户配置
    remark = models.CharField('备注', max_length=500, blank=True, null=True)  # 备注说明

    class Meta:
        """指定真实表名；表由 SQL 手工维护，故不参与迁移。"""
        db_table = 'rp_template'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['-id']  # 默认按主键倒序


class RpGenerateRecord(BaseModel):
    """报表生成记录表：记录每次报表生成的请求与结果。"""
    GEN_STATUS_CHOICES = ((0, '生成中'), (1, '成功'), (2, '失败'))  # 生成状态可选值
    GEN_TYPE_CHOICES = (('manual', '手动触发'), ('schedule', '定时任务'))  # 触发方式可选值

    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    template_id = models.BigIntegerField('模板ID')  # 关联 rp_template 主键
    template_name = models.CharField('模板名称', max_length=200, blank=True, null=True)  # 模板名称快照
    param_json = models.TextField('生成参数', blank=True, null=True)  # JSON 文本，前端传入的查询条件
    gen_status = models.SmallIntegerField('生成状态', choices=GEN_STATUS_CHOICES, default=0)  # 0/1/2
    file_id = models.BigIntegerField('生成文件ID', blank=True, null=True)  # 关联 wf_file 主键
    error_msg = models.TextField('错误信息', blank=True, null=True)  # 失败时的错误详情
    gen_type = models.CharField('触发方式', max_length=16, choices=GEN_TYPE_CHOICES, default='manual')  # 方式
    cost_time = models.BigIntegerField('耗时毫秒', blank=True, null=True)  # 生成耗时
    gen_user_id = models.BigIntegerField('生成用户ID', blank=True, null=True)  # 操作者用户 ID
    gen_time = models.DateTimeField('生成时间', blank=True, null=True)  # 生成完成时刻

    class Meta:
        """指定真实表名；表由 SQL 手工维护，故不参与迁移。"""
        db_table = 'rp_generate_record'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['-id']  # 默认按主键倒序，最新生成在前