"""数据备份模块视图集。"""
# 文件：apps/backup/views.py —— 数据备份模块的 HTTP 接口层
# 用途：提供备份记录的 CRUD、手动备份、下载，以及备份策略的 CRUD 与启停接口。
# 对应表：backup_record（备份记录）、backup_strategy（备份策略）。
# 路由前缀：/api/backup/record/、/api/backup/strategy/（具体映射见 apps/backup/urls.py）。
# 幂等性：查询/列表天然幂等；manual_backup 每次 POST 都会新增一条记录，因此并非幂等接口；
#         下载接口只读，重复调用结果一致；策略 status 接口按 pk 覆盖状态，重复提交结果一致。
# 时间模块：用于生成备份时间戳与格式化输出
import datetime
# JSON 模块：把备份元信息序列化为文本，作为“下载内容”返回
import json
# 别名导入 time：本文件当前未直接使用，保留原有导入顺序以维持代码风格一致
import time as _time

# HttpResponse：构造以附件形式下载的纯文本/JSON 响应
from django.http import HttpResponse
# action 装饰器：把非标准 REST 动作（manual_backup/download）注册为额外路由
from rest_framework.decorators import action

# 统一成功响应封装：返回 {code, msg, data} 结构
from common.response import ok
# 通用 CRUD 基类：提供 list/create/update/delete 与权限校验、日志记录
from common.views import CrudViewSet

# 备份相关模型
from apps.backup.models import BackupRecord, BackupStrategy
# 备份相关序列化器：用于输出记录/策略的完整字段
from apps.backup.serializers import BackupRecordSerializer, BackupStrategySerializer


# 备份记录视图集：标准 CRUD 之外，增加“手动备份”和“下载备份”两个动作
class BackupRecordViewSet(CrudViewSet):
    """备份记录表 CRUD。"""
    # 目标模型：基类据此构建查询集、执行新增/更新/逻辑删除
    model = BackupRecord
    # 序列化器：列表与详情输出、写入校验都使用它
    serializer_class = BackupRecordSerializer
    # 权限前缀：生成 backup:list/create/update/delete 权限点，由权限中间件校验
    perm_prefix = 'backup'
    # 查询参数到 ORM lookup 的白名单映射，基类据此动态拼接过滤条件
    filter_map = {
        # 备份名称支持模糊搜索，便于按时间戳/策略名检索
        'backup_name': 'icontains',
        # 备份类型精确匹配（manual/auto 等）
        'backup_type': 'exact',
        # 备份状态精确匹配（0/1/2 等）
        'backup_status': 'exact',
    }
    # 默认排序：雪花 ID 倒序，最新的备份记录排在前面
    order_by = '-id'
    # 操作日志模块名：写日志时用于区分业务模块
    module_name = '备份记录管理'

    # 自定义动作：detail=False 表示不依赖单条记录，路径为 /record/manual，仅接受 POST
    @action(detail=False, methods=['post'])
    def manual_backup(self, request):
        """手动触发一次备份（模拟）：新增一条手动备份记录。"""
        # 延迟导入配置：仅本动作需要读取数据库名，减少模块顶层导入的耦合
        from django.conf import settings
        # 取当前本地时间，既作为备份时间也用于拼接备份名称
        now = datetime.datetime.now()
        # 落库一条备份记录；演示实现不生成真实备份文件，只写元信息
        row = BackupRecord.objects.create(
            # 备份名称：以“手动备份_年月日时分秒”命名，保证同一秒内重名概率极低且可读
            backup_name=f'手动备份_{now.strftime("%Y%m%d%H%M%S")}',
            # 备份类型固定为 manual，与自动备份区分
            backup_type='manual',
            # 记录当前默认数据库名；未配置时退化为空串，避免写入 None 造成展示为空
            db_name=settings.DATABASES['default'].get('NAME') or '',
            # 备份状态固定写 1（成功），因为这里是模拟备份，没有真实执行过程
            backup_status=1,  # 模拟备份直接标记成功
            # 备份时间写入当前时刻，供列表排序与保留策略判断
            backup_time=now,
            # 备注明确标注为模拟备份，提醒使用者未生成真实文件
            remark='手动触发的模拟备份',
        )
        # 返回新记录的完整字段，并附带成功提示，前端可直接刷新列表
        return ok(BackupRecordSerializer(row).data, '手动备份成功')

    # 自定义动作：detail=True 表示按 pk 操作单条记录，路径为 /record/download/<pk>，仅接受 GET
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """下载备份文件（模拟）：输出该备份记录的元信息 JSON。"""
        # 只查未逻辑删除的记录，避免已删除的备份仍可被下载
        row = self.get_queryset().filter(pk=pk).first()  # 查未删除的备份记录
        # 记录不存在时走统一 404 业务响应
        if not row:
            return self._not_found()  # 记录不存在
        # 组装下载内容：把记录的关键字段整理成可读的 JSON 结构
        payload = {
            # 备份名称
            'backup_name': row.backup_name,
            # 备份类型（手动/自动）
            'backup_type': row.backup_type,
            # 来源数据库名
            'db_name': row.db_name,
            # 备份状态（1 表示成功）
            'backup_status': row.backup_status,
            # 备份时间：DateTime 转字符串，空值统一输出空串，避免前端解析 null
            'backup_time': str(row.backup_time) if row.backup_time else '',
            # 文件大小（字节）：演示环境下通常为空
            'file_size': row.file_size,
            # 备注说明
            'remark': row.remark,
            # 显式告知调用方这是演示数据，未生成真实备份文件，避免误解
            'notice': '演示环境未生成真实备份文件，此处返回备份元信息',
        }
        # 构造 JSON 下载响应：ensure_ascii=False 保留中文，indent=2 便于人工查看
        resp = HttpResponse(json.dumps(payload, ensure_ascii=False, indent=2),
                            # 声明 UTF-8 JSON 类型，避免浏览器按默认编码解析
                            content_type='application/json; charset=utf-8')
        # 设置附件下载头；文件名使用记录 ID 兜底，避免中文名在部分浏览器下乱码
        resp['Content-Disposition'] = f'attachment; filename="backup_{row.id}.json"'  # 浏览器下载文件名兜底
        # 返回响应对象（此处不是统一 ok 封装，因为需要触发文件下载）
        return resp


# 备份策略视图集：仅使用通用 CRUD，启停动作复用基类 status 方法（见 urls.py）
class BackupStrategyViewSet(CrudViewSet):
    """备份策略表 CRUD。"""
    # 目标模型：备份策略表
    model = BackupStrategy
    # 序列化器：输出/校验策略的全部字段
    serializer_class = BackupStrategySerializer
    # 权限前缀：生成 backup:list/create/update/delete 权限点，与记录模块共用
    perm_prefix = 'backup'
    # 查询参数到 ORM lookup 的白名单映射
    filter_map = {
        # 策略名称模糊搜索
        'strategy_name': 'icontains',
        # 状态精确匹配（1=启用，0=停用）
        'status': 'exact',
    }
    # 默认排序：主键倒序，最新策略在前
    order_by = '-id'
    # 操作日志模块名：用于记录日志时区分“备份策略管理”业务
    module_name = '备份策略管理'
