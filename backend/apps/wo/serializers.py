"""工单模块序列化器。"""
# 文件：apps/wo/serializers.py —— 工单模块的 DRF 序列化器
# 用途：定义工单类型、工单主体、工单日志三类模型的读写转换规则，供视图集完成
#       list 输出、create/update 校验与动作接口回写完整对象。
# 对应表：work_order_type、work_order、work_order_log（均由建表 SQL 手工创建）。
# 路由前缀：/api/wo/type/、/api/wo/order/、/api/wo/log/，接口响应中的字段结构由本文件决定。
# 设计取舍：三个模型字段简单且无关联嵌套，统一使用 ModelSerializer + fields='__all__'，
#           让新增/编辑接口直接接收模型字段，避免为每个字段重复声明导致与表结构不一致。
from rest_framework import serializers  # DRF 序列化/反序列化组件

from apps.wo.models import WorkOrder, WorkOrderLog, WorkOrderType  # 工单相关模型


# 工单类型序列化器：工单类型增删改查接口的输入输出结构
class WorkOrderTypeSerializer(serializers.ModelSerializer):
    # 类型表字段较少且无敏感信息，全部可读写，无需隐藏或额外映射
    """工单类型序列化器：直接暴露全部字段。"""
    # 内部 Meta 声明绑定的模型与字段范围
    class Meta:
        # 绑定模型：字段名、verbose_name、默认值都从该模型推导
        model = WorkOrderType
        # 全字段暴露：包含雪花主键、类型名称、排序、状态、备注及 BaseModel 审计字段
        fields = '__all__'


# 工单序列化器：工单列表/详情/新增/编辑以及 assign/solve/close 回写共用的结构
class WorkOrderSerializer(serializers.ModelSerializer):
    # 全字段开放：前端新增/编辑直接提交后端字段，动作接口也据此回写完整对象
    """工单序列化器：直接暴露全部字段。"""
    # 内部 Meta 声明绑定的模型与字段范围
    class Meta:
        # 绑定工单主体模型
        model = WorkOrder
        # 全字段暴露：id、order_no、类型、标题、内容、附件串、优先级、状态、处理人、时间字段等
        fields = '__all__'


# 工单日志序列化器：日志查询接口与动作日志回显使用
class WorkOrderLogSerializer(serializers.ModelSerializer):
    # 日志表只读为主，全字段输出便于前端直接渲染时间线节点
    """工单日志序列化器：直接暴露全部字段。"""
    # 内部 Meta 声明绑定的模型与字段范围
    class Meta:
        # 绑定工单日志模型（不继承 BaseModel，字段较少）
        model = WorkOrderLog
        # 全字段暴露：id、order_id、operator_id、action、comment、create_time
        fields = '__all__'
