"""菜单管理。"""
# 模块用途：系统菜单/按钮的增删改查与菜单树输出，菜单树供角色授权页勾选权限点。
# 对应路由前缀：/api/system/menu/（标准 CRUD + /tree + 单条 /delete/<pk>）。
# 权限要求：CRUD 走基类 system:menu:*；tree 仅要求登录，方便角色授权页读取。
# 关键约定：删除前校验子菜单；菜单记录逻辑删除；tree 支持按名称/状态筛选并返回完整层级。
from rest_framework.decorators import action  # 声明自定义动作路由

from apps.system.models import SysMenu  # 菜单模型
from apps.system.serializers import MenuSerializer  # 菜单序列化器
from common.auth import LoginRequired  # 树查询只要求登录
from common.response import fail, ok  # 统一响应封装
from common.utils import build_tree  # 列表组装为树
from common.views import CrudViewSet  # 通用 CRUD 基类


class MenuViewSet(CrudViewSet):
    """菜单管理视图：提供菜单树与带子节点校验的单条删除。"""
    # 标准 CRUD 交给基类；本类额外实现树查询与带子节点校验的删除。
    model = SysMenu  # 目标模型
    serializer_class = MenuSerializer  # 序列化器
    perm_prefix = 'system:menu'  # 权限标识前缀
    module_name = '菜单管理'  # 操作日志模块名

    @property  # 以属性形式按 action 动态返回权限类，供 DRF 在每次请求前装配
    def permission_classes(self):
        """树接口仅需登录，其余动作沿用基类的权限校验。"""
        # 覆盖基类属性：tree 放宽为登录即可，其余动作仍按 perm_prefix 细粒度校验。
        if self.action in ('tree',):  # 菜单树用于角色授权页，登录即可
            # 角色授权页需要读取全部菜单/按钮，若要求 menu 权限会导致无权限角色无法配置。
            return [LoginRequired]  # 登录校验
        # 其余动作交还基类，由它展开 perm_map 并挂 PermissionCheck。
        return super().permission_classes  # 基类按 perm_prefix 校验

    # 菜单树接口：支持名称模糊/状态精确筛选，输出含按钮(F)的完整树，角色授权页需要按钮权限点。
    @action(detail=False, methods=['get'])  # 注册集合级自定义动作：GET /menu/tree
    def tree(self, request):
        """菜单树（含按钮），供菜单管理与角色授权使用。"""
        # 先取未删除菜单的查询集，后续按需追加筛选条件。
        queryset = self.get_queryset()  # 未删除菜单
        # 名称模糊查询用于管理页快速定位；状态用于只看启用/停用的菜单。
        menu_name = request.query_params.get('menu_name')  # 按名称模糊查询
        status = request.query_params.get('status')  # 按状态精确查询
        # 只在传了非空名称时才追加过滤，避免空串把结果集过滤为空。
        if menu_name:
            queryset = queryset.filter(menu_name__icontains=menu_name)  # 名称过滤
        # 空串与 None 同样视为未筛选，兼容前端下拉的“全部”选项。
        if status not in (None, ''):
            queryset = queryset.filter(status=status)  # 状态过滤
        # 序列化后交给 build_tree 组装，保持与列表接口一致的字段结构。
        rows = MenuSerializer(queryset, many=True).data  # 序列化为字典列表
        # 返回嵌套树；父节点缺失的孤儿节点会被 build_tree 提升为根，避免节点丢失。
        return ok(build_tree(rows))  # 组装树返回

    # 覆盖基类单条删除：有子菜单时拒绝，防止子节点失去父级挂载点而变成孤儿数据。
    def delete(self, request, pk=None):
        """单删：存在子菜单时禁止删除。"""
        # get_queryset 已过滤 is_deleted=0，查不到即视为不存在或已删除。
        menu = self.get_queryset().filter(pk=pk).first()  # 查未删除菜单
        # 主键不存在或已逻辑删除时返回 404，避免重复删除。
        if not menu:  # 未命中说明菜单已被逻辑删除或主键不存在
            return fail('菜单不存在', code=404)  # 菜单不存在
        # 子菜单仍引用本节点，先删父级会导致层级断裂，因此直接拒绝。
        if self.get_queryset().filter(parent_id=pk).exists():  # 是否有子菜单
            return fail('存在子菜单，不允许删除')  # 拒绝删除
        # 校验通过后只改删除标记，保留历史数据便于审计。
        menu.is_deleted = 1  # 逻辑删除
        # update_fields 限定只写一列，避免误覆盖名称/路径等字段。
        menu.save(update_fields=['is_deleted'])  # 只更新删除标记
        # 不回传数据，前端按统一结构提示成功即可。
        return ok(None, '删除成功')  # 返回成功
