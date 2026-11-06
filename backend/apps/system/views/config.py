"""系统参数配置。"""
# 模块用途：系统参数（键值配置）的查询、新增、修改与删除，供其它模块读取运行参数。
# 对应路由前缀：/api/system/config/（list/create/delete/update/<pk> 四条标准路由）。
# 权限要求：基类按 perm_prefix 生成 system:config:list/create/update/delete 四个权限点。
# 关键约定：列表统一过滤 is_deleted=0；审计字段由 CrudViewSet 统一写入，本文件不重复实现。
from apps.system.models import SysConfig  # 参数配置模型
from apps.system.serializers import ConfigSerializer  # 参数配置序列化器
from common.views import CrudViewSet  # 通用 CRUD 基类


class ConfigViewSet(CrudViewSet):
    """参数配置视图：仅需声明模型与筛选条件，CRUD 由基类提供。"""
    # 以下四个类属性就是接入通用基类的全部配置，不需要再重写列表/新增/修改/删除方法。
    model = SysConfig  # 目标模型
    serializer_class = ConfigSerializer  # 序列化器
    perm_prefix = 'system:config'  # 权限标识前缀
    module_name = '参数配置'  # 操作日志模块名
    # 只对白名单字段做模糊匹配；空值在基类中会被忽略，因此不会误过滤结果。
    filter_map = {'config_name': 'icontains', 'config_key': 'icontains'}  # 列表筛选字段
