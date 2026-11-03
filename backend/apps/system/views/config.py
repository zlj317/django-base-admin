"""系统参数配置。"""
from apps.system.models import SysConfig
from apps.system.serializers import ConfigSerializer
from common.views import CrudViewSet


class ConfigViewSet(CrudViewSet):
    model = SysConfig
    serializer_class = ConfigSerializer
    perm_prefix = 'system:config'
    module_name = '参数配置'
    filter_map = {'config_name': 'icontains', 'config_key': 'icontains'}
