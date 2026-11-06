"""安全策略模块序列化器。"""
# 文件：apps/sec/serializers.py —— 安全策略模块的 DRF 序列化器
# 用途：把 SysIpControl / SysLoginAttempt / SysRateLimit 三个模型与 JSON 互转，
#       同时承担新增/编辑时的字段校验（字段类型、必填、长度、取值范围等）。
# 对应表：sys_ip_control、sys_login_attempt、sys_rate_limit（均为手工建表、managed=False）。
# 路由前缀：/api/sec/ip、/api/sec/login_attempt、/api/sec/rate_limit，由 apps/sec/views.py 的视图集调用。
# 生效范围：序列化器只做数据读写与校验，不做 IP 匹配/限流判定；规则是否被登录或接口链路真正执行，
#           以代码中的实际调用为准（当前以配置维护与演示为主）。
# 实现约定：三个模型字段较少且后台需要整表返回，因此统一使用 ModelSerializer + fields='__all__'，
#           避免逐个列字段造成漏列；新增字段时序列化器会自动跟随模型。
from rest_framework import serializers

# 上一行引入 DRF 序列化框架：ModelSerializer 提供按模型自动生成字段与校验规则的能力。
from apps.sec.models import SysIpControl, SysLoginAttempt, SysRateLimit


# IP 黑白名单序列化器：用于后台名单的列表/详情输出与新增、编辑校验
class SysIpControlSerializer(serializers.ModelSerializer):
    # Meta 声明绑定模型与字段范围，ModelSerializer 会自动按模型字段生成校验规则
    class Meta:
        # 绑定的模型：字段名、verbose_name、max_length、默认值均从模型元数据推导
        model = SysIpControl
        # '__all__' 表示输出模型全部字段（含雪花主键与审计字段），前端可直接整对象回显
        fields = '__all__'


# 登录尝试记录序列化器：用于登录流水的只读查询与后台删除操作
class SysLoginAttemptSerializer(serializers.ModelSerializer):
    # 绑定登录尝试模型；该模型不继承 BaseModel，因此没有 is_deleted 等审计字段
    class Meta:
        # 目标模型
        model = SysLoginAttempt
        # 全部字段：id/username/ip/attempt_time/success_flag/create_time
        fields = '__all__'


# 接口限流规则序列化器：用于限流规则的列表/详情输出与新增、编辑校验
class SysRateLimitSerializer(serializers.ModelSerializer):
    # 绑定限流规则模型，字段校验规则同样由模型定义自动生成
    class Meta:
        # 目标模型
        model = SysRateLimit
        # 全部字段：id/rule_name/limit_url/period_sec/max_count/status 及审计字段
        fields = '__all__'
