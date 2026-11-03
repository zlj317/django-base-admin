"""系统参数配置。"""
from apps.system.models import SysConfig  # 参数配置模型
from apps.system.serializers import ConfigSerializer  # 参数配置序列化器
from common.views import CrudViewSet  # 通用 CRUD 基类


class ConfigViewSet(CrudViewSet):
    """参数配置视图：仅需声明模型与筛选条件，CRUD 由基类提供。"""
    model = SysConfig  # 目标模型
    serializer_class = ConfigSerializer  # 序列化器
    perm_prefix = 'system:config'  # 权限标识前缀
    module_name = '参数配置'  # 操作日志模块名
    filter_map = {'config_name': 'icontains', 'config_key': 'icontains'}  # 列表筛选字段
