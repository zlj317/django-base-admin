"""数据权限模块模型。"""
# 文件：backend/apps/dp/models.py
# 用途：定义数据权限规则表与"角色-数据权限"关联表的 ORM 映射，供配置页面维护。
# 对应表：sys_data_permission（权限规则）、sys_role_data_permission（角色授权关联）。
# 路由前缀：/api/dp/（permission 配置规则、role_perm 配置角色绑定），见 apps/dp/urls.py。
# 数据范围生效方式：按现有代码，本模块只提供规则存储与 CRUD，没有发现任何业务列表查询
#   调用这些表做 WHERE 条件拼接；因此当前属于"配置/预留"，不会自动过滤业务数据。
#   规则里的 permission_type（all/dept/self/role 等）与 sql_condition 均未被执行，
#   接入方需要自行解析规则并在查询集中追加过滤条件。
# 建表方式：两张表都由手工 SQL 创建，故 Meta.managed=False，Django 迁移不负责建表。
# Django ORM 模型基类与字段类型：用于声明表字段及 Meta 配置
from django.db import models
# 雪花算法主键字段：全局唯一、趋势递增的 bigint 主键
from common.fields import SnowflakeIDField  # 雪花算法主键字段

# 业务公共基类：提供审计字段（create_by/create_time/update_by/update_time）与逻辑删除标记
from common.utils import BaseModel


# 数据权限规则主表：一行代表一种可被角色复用的数据可见范围
class SysDataPermission(BaseModel):
    """数据权限表。"""

    # 主键：使用雪花 ID，避免自增主键在分库/批量导入时冲突，也便于前端按时间趋势排序
    id = SnowflakeIDField(primary_key=True)
    # 规则名称：配置页展示与选择时使用，例如"全部数据权限""本部门及以下"
    permission_name = models.CharField('权限名称', max_length=100)
    # 范围类型：决定过滤策略，默认 all；种子数据中出现 all/dept/self/role 四种取值
    # 注意：模型层不校验枚举，业务接入方需自行兼容未知类型（建议未知类型按最小权限处理）
    permission_type = models.CharField('权限类型', max_length=30, blank=True, default='all')
    # 范围参数：随类型变化，如 dept 可存 "self,children"、role 可存 "1,2" 等角色 ID 列表
    # 这里统一存字符串，避免为每种类型新增列；具体解析格式由接入方约定，当前无解析代码
    scope_value = models.CharField('范围值', max_length=500, blank=True, null=True)
    # 自定义 SQL 片段：预留给需要复杂条件的场景（如 "dept_id IN (...)"）
    # 当前没有任何代码执行该字段；接入时必须做白名单/参数化校验，禁止直接拼接用户输入，防止 SQL 注入
    sql_condition = models.CharField('SQL条件', max_length=1000, blank=True, null=True)
    # 排序号：配置页按此升序展示，便于把常用规则排在前面
    sort = models.IntegerField('排序', default=0)
    # 状态：1=启用、0=停用；当前 CRUD 只存值，查询业务数据时并未校验该状态
    status = models.SmallIntegerField('状态', default=1)
    # 备注：给配置人员补充说明，可为空，不影响权限计算
    remark = models.CharField('备注', max_length=500, blank=True, null=True)

    # 表级配置：固定表名并与手工建表 SQL 对齐
    class Meta:
        # 实际数据库表名；不写则由 Django 按 app_label + 类名推导，会与现有表不一致
        db_table = 'sys_data_permission'
        # 关闭迁移管理：表由初始化 SQL 创建，避免 makemigrations/migrate 试图改动该表
        managed = False
        # 默认排序：先按业务排序号升序，再按雪花 ID 倒序，保证同序号时新配置在前且分页稳定
        ordering = ['sort', '-id']


# 角色-数据权限关联表：多对多中间表，一行表示"某角色被授予某条数据权限规则"
class SysRoleDataPermission(models.Model):
    """角色-数据权限关联表（不继承 BaseModel）。"""

    # 主键：雪花 ID；关联表数据量大时仍保持趋势递增，便于索引与分页
    id = SnowflakeIDField(primary_key=True)
    # 角色 ID：对应 sys_role.id；只存整数，不建数据库外键，便于手工建表且避免级联删除耦合
    role_id = models.BigIntegerField('角色ID')
    # 数据权限规则 ID：对应 sys_data_permission.id；同样只存整数，由业务层维护引用完整性
    permission_id = models.BigIntegerField('数据权限ID')
    # 授权时间：auto_now_add 在首次 save 时自动写入，之后不再变化
    # 该表不继承 BaseModel，因此没有 is_deleted 等审计字段；删除关联时 CrudViewSet 会走物理删除
    create_time = models.DateTimeField('创建时间', auto_now_add=True)

    # 表级配置：与手工建表 SQL 对齐
    class Meta:
        # 实际数据库表名
        db_table = 'sys_role_data_permission'
        # 表由初始化 SQL 创建，迁移不管理
        managed = False
        # 默认按雪花 ID 倒序，最新授权记录排在最前
        ordering = ['-id']