"""安全策略模块模型（表结构由 docs 建表 SQL 手工创建，managed=False）。"""
# 文件：apps/sec/models.py —— 安全策略模块的模型层
# 用途：把三张安全策略相关的表映射为 ORM 模型，供后台页面做增删改查与列表展示。
# 对应表：sys_ip_control（IP 黑白名单）、sys_login_attempt（登录尝试流水）、sys_rate_limit（接口限流规则）。
# 路由前缀：/api/sec/ip、/api/sec/login_attempt、/api/sec/rate_limit，均在 apps/sec/urls.py 中注册。
# 生效范围（重要）：本模块目前以“配置维护 + 演示”为主——模型只提供数据结构，自身不含任何拦截逻辑；
#                   IP 名单与限流规则是否真正接入登录链路或请求中间件，以仓库中的实际调用代码为准
#                   （当前除本模块外未见读取这两张表执行判定的地方，因此不能仅凭本文件认定策略已生效）。
# 建表约定：三张表的 DDL 由 docs 下的建表 SQL 手工创建，所以 Meta 统一声明 managed = False，
#           Django 不负责建表/改表；若要调整字段，必须同步修改建表 SQL，否则运行时会报列不存在。
from django.db import models
# 上一行是 Django ORM 入口：Model 基类与各类字段（CharField/IntegerField/DateTimeField）。
from common.fields import SnowflakeIDField  # 雪花算法主键字段

# 公共基类：统一提供 create_by/create_time/update_by/update_time/is_deleted 五个审计/逻辑删除字段。
from common.utils import BaseModel


# IP 黑白名单模型：一行代表“某个 IP 或网段按某种控制类型被放行/拦截”的配置
class SysIpControl(BaseModel):
    """IP 黑白名单表。"""

    # 主键：雪花算法生成，避免自增 ID 暴露数据规模，也便于分库分表
    id = SnowflakeIDField(primary_key=True)
    # IP 地址：以字符串保存，支持单个 IPv4/IPv6 或网段写法（如 192.168.0.0/24），此处不做格式强校验
    ip = models.CharField('IP地址', max_length=50)
    # 控制类型：'black' 黑名单（拒绝）/'white' 白名单（放行），默认黑名单；具体取值语义由使用方约定
    control_type = models.CharField('控制类型', max_length=10, default='black')
    # 原因：记录加入名单的业务理由，方便审计与追责；允许为空（批量导入时可能不填）
    reason = models.CharField('原因', max_length=255, blank=True, null=True)
    # 状态：1 启用、0 停用；停用只是保留配置不参与判定（判定逻辑不在本模块内）
    status = models.SmallIntegerField('状态', default=1)
    # 过期时间：为空表示长期有效；适配“临时封禁”场景，是否按此时间自动失效取决于调用方
    expire_time = models.DateTimeField('过期时间', blank=True, null=True)

    class Meta:
        # 显式指定表名，必须与手工建表 SQL 中的表名完全一致
        db_table = 'sys_ip_control'
        # 关闭 Django 的表结构管理：不建表、不生成迁移，字段变更靠改 SQL
        managed = False
        # 默认按主键倒序，后台列表中新配置的记录排在最前
        ordering = ['-id']


# 登录尝试记录模型：记录每次登录成功/失败的流水，用于安全审计与失败次数统计
class SysLoginAttempt(models.Model):
    """登录尝试记录表（不继承 BaseModel）。"""

    # 主键：同样使用雪花 ID，与其它业务表风格保持一致
    id = SnowflakeIDField(primary_key=True)
    # 用户名：本次尝试使用的账号；允许为空，兼容空表单或匿名请求
    username = models.CharField('用户名', max_length=64, blank=True, null=True)
    # 来源 IP：由写入方记录客户端地址；允许为空（取不到真实地址时）
    ip = models.CharField('IP地址', max_length=50, blank=True, null=True)
    # 尝试时间：业务发生时间，允许调用方传入，便于补录历史数据（因此不用 auto_now）
    attempt_time = models.DateTimeField('尝试时间', blank=True, null=True)
    # 是否成功：1 成功、0 失败；失败次数统计即按此字段聚合，默认按失败处理
    success_flag = models.SmallIntegerField('是否成功', default=0)
    # 创建时间：插入时由 Django 自动填充，作为流水落库时间戳
    create_time = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        # 表名与手工建表 SQL 保持一致
        db_table = 'sys_login_attempt'
        # 该表由 SQL 手工创建，Django 不参与迁移
        managed = False
        # 倒序展示：最新的登录尝试排在最前
        ordering = ['-id']


# 接口限流模型：一行代表一条限流规则（在 period_sec 秒内某 URL 最多允许 max_count 次请求）
class SysRateLimit(BaseModel):
    """限流规则表。"""

    # 主键：雪花 ID，与其它业务表一致
    id = SnowflakeIDField(primary_key=True)
    # 规则名称：后台展示与运维识别的可读名称，不能为空
    rule_name = models.CharField('规则名称', max_length=100)
    # 限制 URL：规则作用的接口路径；允许为空，可表示默认/全局规则（具体语义由执行方约定）
    limit_url = models.CharField('限制URL', max_length=255, blank=True, null=True)
    # 时间周期（秒）：统计窗口长度，默认 60 秒
    period_sec = models.IntegerField('时间周期(秒)', default=60)
    # 最大请求数：窗口内允许的请求上限，默认 100 次
    max_count = models.IntegerField('最大请求数', default=100)
    # 状态：1 启用、0 停用；停用后规则保留但不参与限流判定
    status = models.SmallIntegerField('状态', default=1)

    class Meta:
        # 表名与手工建表 SQL 一致
        db_table = 'sys_rate_limit'
        # Django 不管理表结构，迁移不会触碰该表
        managed = False
        # 默认按主键倒序，后台列表最新规则在前
        ordering = ['-id']