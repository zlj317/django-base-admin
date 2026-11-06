"""多租户模块模型（表结构由 docs 建表 SQL 手工创建，managed=False）。"""
# 文件：apps/tenant/models.py —— 多租户模块的 ORM 模型映射
# 用途：定义租户主体、租户成员关系、可售套餐三张表，供 tenant 视图集与种子脚本复用。
# 对应表：sys_tenant（租户主体）、sys_tenant_user（租户-用户关系）、sys_tenant_package（租户套餐）。
# 路由前缀：/api/tenant/tenant/、/api/tenant/tenant_user/、/api/tenant/package/（见 apps/tenant/urls.py）。
# 租户隔离：本模块只提供"租户-用户"映射数据；业务查询未做统一 tenant_id 过滤，当前属于配置/演示能力。
# 建表方式：三张表均由 docs 下的建表 SQL 手工创建，模型 managed=False，Django 不参与建表与迁移。
# Django ORM 的 Model 基类与字段类型
from django.db import models
# 雪花算法主键字段；原行尾注释保留不动
from common.fields import SnowflakeIDField  # 雪花算法主键字段

# 统一审计字段基类：create_by/create_time/update_by/update_time/is_deleted
from common.utils import BaseModel


# 租户主体：保存租户名称、编码、启停状态、到期时间与资源配额，是租户管理的核心表
class SysTenant(BaseModel):
    """租户表。"""

    # 主键：雪花 ID，由后端在 insert 前生成，避免依赖数据库自增
    id = SnowflakeIDField(primary_key=True)
    # 租户展示名称：列表接口按它做 icontains 模糊搜索
    tenant_name = models.CharField('租户名称', max_length=100)
    # 租户唯一编码：业务侧识别租户的短标识，数据库层加 unique 约束防重复
    tenant_code = models.CharField('租户编码', max_length=100, unique=True)
    # 启停状态：1 启用、0 停用；默认启用，由 status 动作单独切换
    status = models.SmallIntegerField('状态', default=1)
    # 到期时间：为空表示不限期；当前仅作展示/配置字段，业务查询不会据此拦截访问
    expire_time = models.DateTimeField('过期时间', blank=True, null=True)
    # 配额：租户允许容纳的最大用户数，供套餐展示与后续校验预留
    max_user_count = models.IntegerField('最大用户数', default=100)
    # 配额：租户允许使用的最大存储空间（MB），当前仅存储不强制限制
    max_storage_mb = models.BigIntegerField('最大存储空间(MB)', default=2048)
    # 租户级扩展配置：JSON 文本（主题、功能开关等），为空表示沿用系统默认
    config_json = models.TextField('配置JSON', blank=True, null=True)
    # 备注：补充说明租户归属或用途，可为空
    remark = models.CharField('备注', max_length=500, blank=True, null=True)

    class Meta:
        # 显式绑定手工建表 SQL 中的表名，避免 Django 使用默认的 app_label_modelname
        db_table = 'sys_tenant'
        # 表结构由外部 SQL 维护，Django 不生成迁移、不建表、不删表
        managed = False
        # 默认按主键倒序，新建租户排在前端列表最前面
        ordering = ['-id']


# 租户成员关系：把系统用户挂到某个租户下并标记是否为租户管理员
# 不继承 BaseModel：该表没有 create_by/update_by/is_deleted 等审计列，删除为物理删除
class SysTenantUser(models.Model):
    """租户用户关联表（不继承 BaseModel）。"""

    # 主键：雪花 ID，创建成员关系时由字段默认值生成
    id = SnowflakeIDField(primary_key=True)
    # 所属租户 ID，对应 sys_tenant.id；用普通整型而非外键，避免跨表强约束与联级删除
    tenant_id = models.BigIntegerField('租户ID')
    # 系统用户 ID，对应 sys_user.id；同一用户可属于多个租户（当前未加唯一约束）
    user_id = models.BigIntegerField('用户ID')
    # 是否租户管理员：1 是、0 否；用于标识租户内最高权限成员，当前仅存储标记
    is_tenant_admin = models.SmallIntegerField('是否租户管理员', default=0)
    # 加入租户的时间：可为空，兼容历史数据或未填写的场景
    join_time = models.DateTimeField('加入时间', blank=True, null=True)
    # 记录创建时间：auto_now_add 只在首次 insert 时写入，后续更新不变
    create_time = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        # 绑定手工建表 SQL 的表名
        db_table = 'sys_tenant_user'
        # 表结构由外部 SQL 维护，Django 不生成迁移
        managed = False
        # 默认按主键倒序，最新加入的成员排前面
        ordering = ['-id']


# 租户套餐：可售档位，描述用户数/存储空间/价格，供租户开通时参考
# 不继承 BaseModel：审计字段在此手工声明，且缺少 create_by/update_by 列
class SysTenantPackage(models.Model):
    """租户套餐表（不继承 BaseModel，手动定义审计字段）。"""

    # 主键：雪花 ID，新增套餐时由字段默认值生成
    id = SnowflakeIDField(primary_key=True)
    # 套餐名称：列表接口按它做 icontains 模糊搜索
    package_name = models.CharField('套餐名称', max_length=100)
    # 套餐包含的最大用户数，与租户表同名配额字段口径一致
    max_user_count = models.IntegerField('最大用户数', default=100)
    # 套餐包含的最大存储空间（MB），用于展示与下单参考
    max_storage_mb = models.BigIntegerField('最大存储空间(MB)', default=2048)
    # 套餐价格：Decimal 保证金额精确，默认 0（免费档）
    price = models.DecimalField('价格', max_digits=10, decimal_places=2, default=0)
    # 上/下架状态：1 启用、0 停用，由 status 动作单独切换
    status = models.SmallIntegerField('状态', default=1)
    # 套餐说明：面向运营/客户的补充描述，可为空
    remark = models.CharField('备注', max_length=500, blank=True, null=True)
    # 创建时间：auto_now_add 仅首次保存写入
    create_time = models.DateTimeField('创建时间', auto_now_add=True)
    # 更新时间：当前同样使用 auto_now_add，编辑套餐时不会自动刷新（疑似应为 auto_now）
    update_time = models.DateTimeField('更新时间', auto_now_add=True)
    # 逻辑删除标记：0 未删除、1 已删除；视图集列表显式过滤该字段
    is_deleted = models.SmallIntegerField('逻辑删除', default=0)

    class Meta:
        # 绑定手工建表 SQL 的表名
        db_table = 'sys_tenant_package'
        # 表结构由外部 SQL 维护，Django 不生成迁移
        managed = False
        # 默认按主键倒序，新套餐优先展示
        ordering = ['-id']