"""部门管理。"""
from apps.system.models import SysDept, SysUser  # 部门与用户模型
from apps.system.serializers import DeptSerializer  # 部门序列化器
from common.auth import LoginRequired  # 树查询只要求登录
from common.response import fail, ok  # 统一响应封装
from common.utils import build_tree  # 列表组装为树
from common.views import CrudViewSet  # 通用 CRUD 基类


class DeptViewSet(CrudViewSet):
    """部门管理视图：提供部门树与删除前的下级/人员占用校验。"""
    model = SysDept  # 目标模型
    serializer_class = DeptSerializer  # 序列化器
    perm_prefix = 'system:dept'  # 权限标识前缀
    module_name = '部门管理'  # 操作日志模块名

    @property
    def permission_classes(self):
        """树接口仅需登录，其余动作沿用基类的权限校验。"""
        if self.action in ('tree',):  # 部门树供用户表单选择，登录即可
            return [LoginRequired]  # 登录校验
        return super().permission_classes  # 基类按 perm_prefix 校验

    def tree(self, request):
        """部门树（含停用部门），供部门管理与用户表单选择。"""
        rows = DeptSerializer(self.get_queryset(), many=True).data  # 序列化为字典列表
        return ok(build_tree(rows))  # 组装树返回

    def delete(self, request, pk=None):
        """单删：存在下级部门或在职用户时禁止删除。"""
        dept = self.get_queryset().filter(pk=pk).first()  # 查未删除部门
        if not dept:
            return fail('部门不存在', code=404)  # 部门不存在
        if self.get_queryset().filter(parent_id=pk).exists():  # 是否有下级部门
            return fail('存在下级部门，不允许删除')  # 拒绝删除
        if SysUser.objects.filter(dept_id=pk, is_deleted=0).exists():  # 部门下是否还有用户
            return fail('部门下存在用户，不允许删除')  # 拒绝删除
        dept.is_deleted = 1  # 逻辑删除
        dept.save(update_fields=['is_deleted'])  # 只更新删除标记
        return ok(None, '删除成功')  # 返回成功
