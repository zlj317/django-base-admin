"""学生信息表 序列化器（由代码生成器生成，可二次修改）。"""
from rest_framework import serializers

from apps.student.models import BizStudent

COMMON_FIELDS = ['id', 'create_by', 'create_time', 'update_by', 'update_time']


class BizStudentSerializer(serializers.ModelSerializer):
    """详情 / 响应序列化器"""

    class Meta:
        model = BizStudent
        fields = ['id'] + [
            'name',
            'age',
            'gender',
            'phone',
            'email',
            'enroll_date',
            'score',
            'address',
        ] + COMMON_FIELDS


class BizStudentCreateSerializer(serializers.ModelSerializer):
    """新增 / 编辑序列化器"""

    def to_internal_value(self, data):
        # 前端未选择的下拉/数值/日期传空串，统一转为 None
        data = dict(data)
        for key, value in data.items():
            if value == '':
                data[key] = None
        return super().to_internal_value(data)

    class Meta:
        model = BizStudent
        fields = [
            'name',
            'age',
            'gender',
            'phone',
            'email',
            'enroll_date',
            'score',
            'address',
        ]
        extra_kwargs = {
            'name': {'required': True},
            'age': {'required': False, 'allow_null': True},
            'gender': {'required': False, 'allow_null': True},
            'phone': {'required': False, 'allow_blank': True, 'allow_null': True},
            'email': {'required': False, 'allow_blank': True, 'allow_null': True},
            'enroll_date': {'required': False, 'allow_null': True},
            'score': {'required': False, 'allow_null': True},
            'address': {'required': False, 'allow_blank': True, 'allow_null': True},
        }


class BizStudentListSerializer(serializers.ModelSerializer):
    """列表序列化器"""

    class Meta:
        model = BizStudent
        fields = ['id'] + [
            'name',
            'age',
            'gender',
            'phone',
            'email',
            'enroll_date',
            'score',
            'address',
            'create_time',
        ]
