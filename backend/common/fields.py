"""自定义模型字段：雪花算法主键。"""
# 模块用途：提供项目统一的 BIGINT 主键字段，屏蔽“主键必须由数据库自增”的默认假设。
# 被谁调用：apps 下各 models.py 声明主键时复用，使业务代码在 insert 前就能拿到主键值。
# 关键约定：主键由后端雪花算法生成（见 common/snowflake.py），字段不可编辑、永不自增；
#           依赖数据库列类型为 BIGINT，且字段参数需与手工建表 SQL 保持一致。
from django.db import models  # 复用 Django 内置字段类型

from common.snowflake import next_id  # 雪花 ID 生成器


# 继承 BigIntegerField：数据库侧为 BIGINT、Python 侧为 int，容量足以存放雪花 ID 且不走自增。
class SnowflakeIDField(models.BigIntegerField):
    # docstring 说明字段语义（谁生成、何时生成）；Django 的字段类型描述仍以 description 为准。
    """BIGINT 主键，插入时由后端雪花算法生成，不使用数据库自增。"""

    # description 会出现在 Django 的字段类型描述与管理端提示中，仅用于说明，不参与建表。
    description = '雪花算法主键'  # Django 内部用于描述字段类型的说明文本

    # 构造时统一注入默认参数，子模型只需写 id = SnowflakeIDField()，不必重复配置。
    def __init__(self, *args, **kwargs):
        # 保留 *args/**kwargs 透传，兼容子类继续传 verbose_name、db_index 等原生字段参数。
        """统一补齐主键、默认值与只读属性，子模型只需声明字段名。"""
        # 用 setdefault 而非直接赋值：允许极少数子类在确有需要时显式覆盖这几个默认行为。
        kwargs.setdefault('primary_key', True)  # 固定作为主键
        # default 传的是函数对象，每条新实例化时才调用一次，因此同一次请求内多条记录也不会重复。
        kwargs.setdefault('default', next_id)  # 新建实例时自动生成雪花 ID
        # 关闭可编辑性：前端提交的 id 一律被忽略，避免伪造主键覆盖已有记录。
        kwargs.setdefault('editable', False)  # 管理端/序列化器不接收手工指定主键
        # 补齐参数后交回父类，由父类完成参数校验并记录到 deconstruct()，迁移文件依赖这些参数。
        super().__init__(*args, **kwargs)
