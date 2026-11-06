# 文件：apps/cal/views.py —— 日历日程模块的视图集
# 用途：暴露日程（cal_schedule）与提醒（cal_reminder）的增删改查接口。
# 对应表：cal_schedule、cal_reminder（均由手工 SQL 建表，ORM 侧 managed=False）。
# 路由前缀：api/cal/schedule/、api/cal/reminder/（路径由 apps/cal/urls.py 生成）。
# 关键约定：增删改查全部复用 common.views.CrudViewSet，基类统一做权限、分页、筛选与逻辑删除；
#           权限标识以 cal 为前缀（cal:list/create/update/delete）；
#           CalReminder 不继承 BaseModel、没有 is_deleted 列，所以必须覆写 get_queryset 去掉过滤。
"""日历日程模块视图集。"""
# 通用 CRUD 基类：统一分页/筛选/增删改 + 权限校验
from common.views import CrudViewSet  # 通用 CRUD 基类

# 日程与提醒模型
from apps.cal.models import CalReminder, CalSchedule  # 日程相关模型
# 对应的序列化器
from apps.cal.serializers import CalReminderSerializer, CalScheduleSerializer  # 对应序列化器


# 日程视图集：标准 CRUD，筛选条件围绕"按标题搜、按归属人过滤"
class ScheduleViewSet(CrudViewSet):
    """日程 CRUD。"""
    # 目标模型：基类据此构建查询集并做唯一性预检
    model = CalSchedule
    # 序列化器：列表输出、新增/编辑校验共用
    serializer_class = CalScheduleSerializer
    # 权限前缀：基类会拼成 cal:list / cal:create / cal:update / cal:delete
    perm_prefix = 'cal'
    # 查询参数白名单：只允许这三个参数参与过滤，字段名不受用户控制
    filter_map = {
        # 标题模糊搜索，便于按关键字定位日程
        'title': 'icontains',
        # 按所有者精确过滤，前端据此实现"我的日程"
        'owner_id': 'exact',
        # 按状态精确过滤（0 正常 / 1 取消）
        'status': 'exact',
    }
    # 默认排序：开始时间倒序，最新日程排在最前
    order_by = '-start_time'
    # 操作日志中展示的模块名
    module_name = '日程管理'


# 提醒视图集：结构同日程，但模型没有逻辑删除列，需要覆写查询集
class ReminderViewSet(CrudViewSet):
    """日程提醒 CRUD（不继承 BaseModel，覆写 get_queryset）。"""
    # 目标模型：提醒表（纯记录表，无审计字段与 is_deleted）
    model = CalReminder
    # 序列化器：直出提醒表全部字段
    serializer_class = CalReminderSerializer
    # 权限前缀与日程共用 cal，避免为提醒单独配一套权限点
    perm_prefix = 'cal'
    # 查询参数白名单：按所属日程、按提醒状态过滤
    filter_map = {
        # 精确匹配日程，查看某条日程产生的全部提醒
        'schedule_id': 'exact',
        # 精确匹配提醒状态，便于筛出待发送记录
        'remind_status': 'exact',
    }
    # 默认排序：主键倒序，最新生成的提醒在前
    order_by = '-id'
    # 操作日志模块名
    module_name = '日程提醒'

    # 覆写查询集：CalReminder 没有 is_deleted 列，不能沿用基类默认的 is_deleted=0 过滤
    def get_queryset(self):
        """CalReminder 无 is_deleted 字段，直接返回全部。"""
        # 直接按排序字段取全表；删除时基类会因缺少 is_deleted 转为物理删除
        return CalReminder.objects.order_by(self.order_by)
