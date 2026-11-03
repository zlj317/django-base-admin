"""学生信息表 序列化器（由代码生成器生成，可二次修改）。"""
from rest_framework import serializers  # 引入 DRF 序列化框架

from apps.student.models import BizStudent  # 引入学生信息表模型

COMMON_FIELDS = ['id', 'create_by', 'create_time', 'update_by', 'update_time']  # 公共字段：主键与创建/更新审计字段


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


class BizStudentCreateSerializer(serializers.ModelSerializer):  # 新增/编辑序列化器
    """新增 / 编辑序列化器"""

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
