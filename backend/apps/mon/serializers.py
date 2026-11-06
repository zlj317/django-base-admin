"""监控告警模块序列化器。"""
# 模块：apps/mon/serializers.py —— 监控告警模块的 DRF 序列化器
# 用途：把 monitor_alarm_rule / monitor_alarm_record 模型实例与 JSON 互相转换，并承担入参字段校验。
# 对应表：monitor_alarm_rule（规则）、monitor_alarm_record（告警记录）。
# 路由前缀：/api/mon/（rule/* 与 record/*），由 apps/mon/views.py 的视图集使用。
# 告警生命周期：规则序列化用于创建/修改触发条件；记录序列化用于输出告警并把处理结果回写。
# DRF 序列化器基类
from rest_framework import serializers

# 需要映射的两个模型
from apps.mon.models import MonitorAlarmRecord, MonitorAlarmRule


# 规则序列化器：ModelSerializer 自动按模型字段生成校验与输出
class MonitorAlarmRuleSerializer(serializers.ModelSerializer):
    # 通过 Meta 声明模型即可，字段规则与模型字段定义保持一致
    class Meta:
        # 绑定的模型类
        model = MonitorAlarmRule
        # 输出/接收全部字段；id 因 SnowflakeIDField 设为 editable=False，不会由前端传入
        fields = '__all__'


# 记录序列化器：输出告警历史，也用于通用 update 回写处理状态
class MonitorAlarmRecordSerializer(serializers.ModelSerializer):
    # 通过 Meta 声明模型即可，字段规则与模型字段定义保持一致
    class Meta:
        # 绑定的模型类
        model = MonitorAlarmRecord
        # 输出/接收全部字段；handle_status/handler_id/handle_time 可经更新接口回写
        fields = '__all__'
