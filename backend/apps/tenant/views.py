"""多租户模块视图集。"""
from common.pagination import StandardPagination
from common.views import CrudViewSet

from apps.tenant.models import SysTenant, SysTenantPackage, SysTenantUser
from apps.tenant.serializers import SysTenantPackageSerializer, SysTenantSerializer, SysTenantUserSerializer


class SysTenantViewSet(CrudViewSet):
    """租户 CRUD。"""
    model = SysTenant
    serializer_class = SysTenantSerializer
    perm_prefix = 'tenant:tenant'
    filter_map = {
        'tenant_name': 'icontains',
        'tenant_code': 'icontains',
        'status': 'exact',
    }
    order_by = '-id'
    module_name = '租户管理'


class SysTenantUserViewSet(CrudViewSet):
    """租户用户关联 CRUD。"""
    model = SysTenantUser
    serializer_class = SysTenantUserSerializer
    perm_prefix = 'tenant:tenant_user'
    filter_map = {
        'tenant_id': 'exact',
        'user_id': 'exact',
    }
    order_by = '-id'
    module_name = '租户用户'

    def get_queryset(self):
        return self.model.objects.order_by(self.order_by)

    def list(self, request):
        queryset = self.apply_filters(self.get_queryset(), request)
        return StandardPagination(request).paginate(queryset, self.get_serializer_class())


class SysTenantPackageViewSet(CrudViewSet):
    """租户套餐 CRUD。"""
    model = SysTenantPackage
    serializer_class = SysTenantPackageSerializer
    perm_prefix = 'tenant:package'
    filter_map = {
        'package_name': 'icontains',
        'status': 'exact',
    }
    order_by = '-id'
    module_name = '租户套餐'

    def get_queryset(self):
        return self.model.objects.filter(is_deleted=0).order_by(self.order_by)
