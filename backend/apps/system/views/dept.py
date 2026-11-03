"""部门管理。"""
from apps.system.models import SysDept, SysUser
from apps.system.serializers import DeptSerializer
from common.auth import LoginRequired
from common.response import fail, ok
from common.utils import build_tree
from common.views import CrudViewSet


class DeptViewSet(CrudViewSet):
    model = SysDept
    serializer_class = DeptSerializer
    perm_prefix = 'system:dept'
    module_name = '部门管理'

    @property
    def permission_classes(self):
        if self.action in ('tree',):
            return [LoginRequired]
        return super().permission_classes

    def tree(self, request):
        """部门树（含停用部门），供部门管理与用户表单选择。"""
        rows = DeptSerializer(self.get_queryset(), many=True).data
        return ok(build_tree(rows))

    def delete(self, request, pk=None):
        dept = self.get_queryset().filter(pk=pk).first()
        if not dept:
            return fail('部门不存在', code=404)
        if self.get_queryset().filter(parent_id=pk).exists():
            return fail('存在下级部门，不允许删除')
        if SysUser.objects.filter(dept_id=pk, is_deleted=0).exists():
            return fail('部门下存在用户，不允许删除')
        dept.is_deleted = 1
        dept.save(update_fields=['is_deleted'])
        return ok(None, '删除成功')
