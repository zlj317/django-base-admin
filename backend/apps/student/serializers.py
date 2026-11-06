"""学生信息表 序列化器（由代码生成器生成，可二次修改）。"""
# 模块用途：学生信息表的三套序列化器，覆盖“写入、列表、详情/响应”三种接口场景。
# 对应表：biz_student，字段与 apps/student/models.py 的 BizStudent 一一对应。
# 被谁引用：apps/student/views.py 的 list/create/update 动作以及导入导出后的返回体。
# 生成约定：每个业务模块固定生成三类序列化器——详情(全字段+审计)、写入(仅业务字段+extra_kwargs)、列表(精简)；
#           公共字段抽取为 COMMON_FIELDS 常量，增删审计字段只改这一处，其余序列化器自动同步。
from rest_framework import serializers  # 引入 DRF 序列化框架

from apps.student.models import BizStudent  # 引入学生信息表模型

# 公共字段清单：主键 + 四个审计字段；详情响应整体引用，写入接口刻意排除，避免前端篡改创建人与时间。
COMMON_FIELDS = ['id', 'create_by', 'create_time', 'update_by', 'update_time']  # 公共字段：主键与创建/更新审计字段


# ModelSerializer 会按模型字段自动生成校验规则（max_length、是否允许 NULL、decimal 精度等），无需重复声明。
class BizStudentSerializer(serializers.ModelSerializer):  # 详情/响应序列化器
    """详情 / 响应序列化器"""

    class Meta:  # 序列化配置
        """序列化配置：绑定模型并声明输出字段。"""

        model = BizStudent  # 绑定学生信息表模型
        fields = ['id'] + [  # 输出字段：主键 + 业务字段 + 审计字段
            'name',  # 学生姓名
            'age',  # 年龄
            'gender',  # 性别字典值
            'phone',  # 手机号
            'email',  # 邮箱
            'enroll_date',  # 入学日期
            'score',  # 总分
            'address',  # 家庭住址
        ] + COMMON_FIELDS  # 追加公共审计字段


# 写入序列化器只包含业务字段：审计字段与逻辑删除标记由后端维护，不再交给前端提交。
class BizStudentCreateSerializer(serializers.ModelSerializer):  # 新增/编辑序列化器
    """新增 / 编辑序列化器"""

    # 覆写 to_internal_value 是生成器的表单兼容约定：只做“空串转 None”的清洗，校验规则仍完整交给父类。
    def to_internal_value(self, data):  # 入库前的数据清洗入口
        """把提交的空串统一转为 None，再交给父类完成校验与类型转换。"""

        # 前端未选择的下拉/数值/日期传空串，统一转为 None
        data = dict(data)  # 复制为可变字典，避免修改原始请求数据
        for key, value in data.items():  # 遍历所有提交字段
            if value == '':  # 空串统一转换为 None，避免数值/日期字段校验失败
                data[key] = None  # 置为空值
        return super().to_internal_value(data)  # 交由父类完成字段校验与转换

    class Meta:  # 序列化配置
        """序列化配置：绑定模型并声明可写入字段与校验规则。"""

        model = BizStudent  # 绑定学生信息表模型
        fields = [  # 可写入字段列表
            'name',  # 学生姓名
            'age',  # 年龄
            'gender',  # 性别
            'phone',  # 手机号
            'email',  # 邮箱
            'enroll_date',  # 入学日期
            'score',  # 总分
            'address',  # 家庭住址
        ]
        # extra_kwargs 逐个声明必填性与空值容忍度，对应前端表单的 required / allowClear 规则；
        # 空串已在 to_internal_value 中转为 None，故这里只对文本字段额外允许 allow_blank。
        extra_kwargs = {  # 各字段的校验补充规则
            'name': {'required': True},  # 姓名必填
            'age': {'required': False, 'allow_null': True},  # 年龄非必填、可空
            'gender': {'required': False, 'allow_null': True},  # 性别非必填、可空
            'phone': {'required': False, 'allow_blank': True, 'allow_null': True},  # 手机号非必填、可为空串或空值
            'email': {'required': False, 'allow_blank': True, 'allow_null': True},  # 邮箱非必填、可为空串或空值
            'enroll_date': {'required': False, 'allow_null': True},  # 入学日期非必填、可空
            'score': {'required': False, 'allow_null': True},  # 总分非必填、可空
            'address': {'required': False, 'allow_blank': True, 'allow_null': True},  # 住址非必填、可为空串或空值
        }


# 列表序列化器只输出列表展示所需字段并附带 create_time，避免把 update_by 等审计细节暴露到列表接口。
class BizStudentListSerializer(serializers.ModelSerializer):  # 列表页序列化器
    """列表序列化器"""

    class Meta:  # 序列化配置
        """序列化配置：绑定模型并声明列表输出字段。"""

        model = BizStudent  # 绑定学生信息表模型
        fields = ['id'] + [  # 列表输出字段：主键 + 业务字段 + 创建时间
            'name',  # 学生姓名
            'age',  # 年龄
            'gender',  # 性别
            'phone',  # 手机号
            'email',  # 邮箱
            'enroll_date',  # 入学日期
            'score',  # 总分
            'address',  # 家庭住址
            'create_time',  # 创建时间，供列表展示
        ]
