# 文件：apps/cal/serializers.py —— 日历日程模块的序列化器
# 用途：在模型与 JSON 之间做转换，供视图集输出数据、校验前端入参。
# 对应表：cal_schedule、cal_reminder。
# 路由前缀：api/cal/schedule/、api/cal/reminder/。
# 关键约定：只用 ModelSerializer 直出全部字段，不做字段裁剪或改名，保证前端字段名与模型一致。
"""日历日程模块序列化器。"""
# DRF 序列化/反序列化组件，ModelSerializer 定义在此命名空间
from rest_framework import serializers  # DRF 序列化/反序列化组件

# 日程与提醒模型，供下方 Meta.model 引用
from apps.cal.models import CalReminder, CalSchedule  # 日程相关模型


# 日程序列化器：新增/编辑按模型字段自动生成校验规则，列表时直接输出整行数据
class CalScheduleSerializer(serializers.ModelSerializer):
    """日程序列化器：直接暴露全部字段。"""
    # 内部 Meta：绑定模型并声明输出字段集合
    class Meta:
        # 绑定日程模型：字段与校验规则由模型自动推导
        model = CalSchedule
        # 输出全部字段，含雪花 id 与审计字段
        fields = '__all__'


# 提醒序列化器：同理整表直出，避免前后端字段映射遗漏
class CalReminderSerializer(serializers.ModelSerializer):
    """日程提醒序列化器：直接暴露全部字段。"""
    # 内部 Meta：绑定提醒模型并输出全部字段
    class Meta:
        # 绑定提醒模型
        model = CalReminder
        # 输出全部字段，前端可直接展示提醒时间与状态
        fields = '__all__'
