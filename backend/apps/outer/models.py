"""外部接口模块模型（表结构由 docs 建表 SQL 手工创建，managed=False）。"""
# 模块用途：把外部对接模块的三张业务表映射为 Django 模型，供视图层与序列化器使用。
# 对应表：outer_api_config（接口配置）、outer_api_request_log（调用日志）、outer_sync_task（同步任务）。
# 说明：三张表均由 docs 建表 SQL 手工创建，Meta 中 managed=False，不参与 Django migrate。
# 现状：outer 以「配置 + 调试」为主；同步任务只登记定义，通过 task_id 关联 task_info，
#       既不会真正拉取数据写入 target_table，也不会驱动报表或大屏。
from django.db import models  # Django ORM 字段与模型基类
from common.fields import SnowflakeIDField  # 雪花算法主键字段

from common.utils import BaseModel  # 公共字段基类：创建/更新人、逻辑删除


# 接口配置表：一行代表一个允许后台测试或调用的外部 HTTP 接口。
class OuterApiConfig(BaseModel):
    """外部API配置表：定义可被调用的外部接口及鉴权参数。"""
    METHOD_CHOICES = (('GET', 'GET'), ('POST', 'POST'), ('PUT', 'PUT'), ('DELETE', 'DELETE'))  # HTTP 方法可选值
    AUTH_TYPE_CHOICES = (('none', '无鉴权'), ('token', 'Token'), ('basic', 'Basic Auth'))  # 鉴权方式可选值

    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    api_name = models.CharField('接口名称', max_length=200)  # 显示名称
    api_url = models.CharField('接口URL', max_length=500)  # 完整 URL 或模板
    method = models.CharField('请求方法', max_length=10, choices=METHOD_CHOICES, default='GET')  # HTTP 方法
    headers_json = models.TextField('请求头(JSON)', blank=True, null=True)  # HTTP Header JSON 文本
    params_json = models.TextField('默认参数(JSON)', blank=True, null=True)  # Query/Body 默认参数 JSON
    auth_type = models.CharField('鉴权方式', max_length=16, choices=AUTH_TYPE_CHOICES, default='none')  # 方式
    auth_config = models.TextField('鉴权配置', blank=True, null=True)  # Token/Basic 的具体配置 JSON
    status = models.SmallIntegerField('状态', default=0)  # 0 正常 / 1 停用
    remark = models.CharField('备注', max_length=500, blank=True, null=True)  # 备注说明

    # Meta 只声明物理表映射与默认排序，不负责建表（表结构由 docs SQL 维护）。
    class Meta:
        """指定真实表名；表由 SQL 手工维护，故不参与迁移。"""
        db_table = 'outer_api_config'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['-id']  # 默认按主键倒序


# 调用日志表：每次 test/call 无论成功失败都会写一条，用于审计与排查外部接口问题。
# 不继承 BaseModel，是因为该表只有调用快照，不需要 create_by/update_by/is_deleted 等业务审计列。
class OuterApiRequestLog(models.Model):
    """外部API调用日志表（不继承 BaseModel）：记录每次外部接口调用详情。"""
    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    api_id = models.BigIntegerField('API配置ID')  # 关联 outer_api_config 主键
    api_name = models.CharField('接口名称', max_length=200, blank=True, null=True)  # 接口名称快照
    request_url = models.CharField('请求URL', max_length=500, blank=True, null=True)  # 实际请求 URL
    request_param = models.TextField('请求参数', blank=True, null=True)  # 实际发送的参数快照
    response_body = models.TextField('响应内容', blank=True, null=True)  # 接口返回的响应体
    http_code = models.IntegerField('HTTP状态码', blank=True, null=True)  # 200/400/500 等
    cost_time = models.BigIntegerField('耗时毫秒', blank=True, null=True)  # 接口调用耗时
    error_msg = models.TextField('错误信息', blank=True, null=True)  # 异常时的错误详情
    request_time = models.DateTimeField('请求时间', blank=True, null=True)  # 请求发起时刻
    create_time = models.DateTimeField('创建时间', blank=True, null=True)  # 入库时间

    # Meta 只声明物理表映射与默认排序，不负责建表；日志表数据量增长快，默认倒序便于看最新调用。
    class Meta:
        """指定真实表名；表由 SQL 手工维护，故不参与迁移。"""
        db_table = 'outer_api_request_log'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['-id']  # 默认按主键倒序，最新调用在前


# 同步任务表：描述「何时从哪个接口、按什么字段映射、写入哪张目标表」。
# 注意：目前只保存定义，task_id 指向 task_info 的调度记录，实际同步逻辑尚未实现（演示为主）。
class OuterSyncTask(BaseModel):
    """外部数据同步任务表：定时从外部接口拉取数据写入目标表。"""
    SYNC_TYPE_CHOICES = (('manual', '手动触发'), ('schedule', '定时任务'))  # 同步方式可选值

    id = SnowflakeIDField(primary_key=True)  # 主键，雪花算法生成
    sync_name = models.CharField('同步任务名称', max_length=200)  # 显示名称
    api_id = models.BigIntegerField('接口配置ID')  # 关联 outer_api_config 主键
    target_table = models.CharField('目标表名', max_length=100)  # 同步写入的数据表名
    sync_field_json = models.TextField('字段映射(JSON)', blank=True, null=True)  # 接口字段到表字段的映射 JSON
    sync_type = models.CharField('同步方式', max_length=16, choices=SYNC_TYPE_CHOICES, default='manual')  # 方式
    task_id = models.BigIntegerField('调度任务ID', blank=True, null=True)  # 关联 task_info 主键
    status = models.SmallIntegerField('状态', default=0)  # 0 正常 / 1 停用
    remark = models.CharField('备注', max_length=500, blank=True, null=True)  # 备注说明

    # Meta 只声明物理表映射与默认排序，不负责建表；表结构由 docs SQL 维护。
    class Meta:
        """指定真实表名；表由 SQL 手工维护，故不参与迁移。"""
        db_table = 'outer_sync_task'  # 对应数据库物理表名
        managed = False  # 不参与 migrate 的建表/改表
        ordering = ['-id']  # 默认按主键倒序