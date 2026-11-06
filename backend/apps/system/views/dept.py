"""部门管理。"""
# 模块用途：部门（组织架构）的增删改查与部门树输出，部门树供用户表单级联选择。
# 对应路由前缀：/api/system/dept/（标准 CRUD + 自定义 /tree + 单条 /delete/<pk>）。
# 权限要求：CRUD 走基类 system:dept:*；tree 仅要求登录，方便用户表单引用。
# 关键约定：删除前校验下级部门与在职用户；部门记录统一逻辑删除，不做物理删除。
from apps.system.models import SysDept, SysUser  # 部门与用户模型
from apps.system.serializers import DeptSerializer  # 部门序列化器
from common.auth import LoginRequired  # 树查询只要求登录
from common.response import fail, ok  # 统一响应封装
from common.utils import build_tree  # 列表组装为树
from common.views import CrudViewSet  # 通用 CRUD 基类


class DeptViewSet(CrudViewSet):
    """部门管理视图：提供部门树与删除前的下级/人员占用校验。"""
    # 基础 CRUD 由基类提供，本类只额外实现树查询与带校验的删除。
    model = SysDept  # 目标模型
    serializer_class = DeptSerializer  # 序列化器
    perm_prefix = 'system:dept'  # 权限标识前缀
    module_name = '部门管理'  # 操作日志模块名

    @property  # 以属性形式按 action 动态返回权限类，供 DRF 在每次请求前装配
    def permission_classes(self):
        """树接口仅需登录，其余动作沿用基类的权限校验。"""
        # 覆盖基类属性：只有 tree 放宽到“登录即可”，其余动作仍按 perm_prefix 做细粒度校验。
        if self.action in ('tree',):  # 部门树供用户表单选择，登录即可
            # 用户新增/编辑弹窗需要读部门树；若要求 dept 权限，普通用户将无法选择部门。
            return [LoginRequired]  # 登录校验
        # 其余动作交回基类：它会把 perm_prefix 展开成 perm_map 并挂 PermissionCheck。
        return super().permission_classes  # 基类按 perm_prefix 校验

    # 部门树接口：一次性返回全部未删除部门，前端按 parent_id 渲染层级。
    def tree(self, request):
        """部门树（含停用部门），供部门管理与用户表单选择。"""
        # 复用 DeptSerializer，保证树节点与列表接口字段完全一致。
        rows = DeptSerializer(self.get_queryset(), many=True).data  # 序列化为字典列表
        # build_tree 以 parent_id 挂接子节点；根部门 parent_id=0，孤儿节点自动提升为根。
        return ok(build_tree(rows))  # 组装树返回

    # 覆盖基类单条删除：存在下级部门或在职用户时拒绝，避免产生孤儿数据。
    def delete(self, request, pk=None):
        """单删：存在下级部门或在职用户时禁止删除。"""
        # get_queryset 已过滤 is_deleted=0，因此查不到即视为不存在或已删除。
        dept = self.get_queryset().filter(pk=pk).first()  # 查未删除部门
        # 主键不存在或已被逻辑删除时返回 404，避免重复删除。
        if not dept:  # 未命中说明部门已被逻辑删除或主键不存在
            return fail('部门不存在', code=404)  # 部门不存在
        # 有子部门时先删父部门会让子部门失去挂载点，因此直接拒绝。
        if self.get_queryset().filter(parent_id=pk).exists():  # 是否有下级部门
            return fail('存在下级部门，不允许删除')  # 拒绝删除
        # 部门下仍有未删除用户时，删除会导致用户归属失效，同样拒绝。
        if SysUser.objects.filter(dept_id=pk, is_deleted=0).exists():  # 部门下是否还有用户
            return fail('部门下存在用户，不允许删除')  # 拒绝删除
        # 校验全部通过后只改删除标记，保留历史数据便于审计与恢复。
        dept.is_deleted = 1  # 逻辑删除
        # update_fields 限定只写这一列，避免误覆盖其它字段（也减少写库量）。
        dept.save(update_fields=['is_deleted'])  # 只更新删除标记
        # 不回传数据，前端按统一结构提示成功即可。
        return ok(None, '删除成功')  # 返回成功
