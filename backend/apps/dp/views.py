"""数据权限模块视图集。"""
from common.views import CrudViewSet

from apps.dp.models import SysDataPermission, SysRoleDataPermission
from apps.dp.serializers import SysDataPermissionSerializer, SysRoleDataPermissionSerializer


class SysDataPermissionViewSet(CrudViewSet):
    """数据权限表 CRUD。"""
    model = SysDataPermission
    serializer_class = SysDataPermissionSerializer
    perm_prefix = 'dp'
    filter_map = {
        'permission_name': 'icontains',
        'permission_type': 'exact',
        'status': 'exact',
    }
    order_by = '-id'
    module_name = '数据权限配置'


class SysRoleDataPermissionViewSet(CrudViewSet):
    """角色-数据权限关联表 CRUD（无 BaseModel）。"""
    model = SysRoleDataPermission
    serializer_class = SysRoleDataPermissionSerializer
    perm_prefix = 'dp'
    filter_map = {
        'role_id': 'exact',
        'permission_id': 'exact',
    }
    order_by = '-id'
    module_name = '角色数据权限关联'

    def get_queryset(self):
        return self.model.objects.order_by(self.order_by)
