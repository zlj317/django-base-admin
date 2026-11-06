"""角色管理。"""
# 模块用途：角色增删改查、角色已授权菜单查询与覆盖式菜单授权保存。
# 对应路由前缀：/api/system/role/（标准 CRUD + /menu_ids/<pk> + /assign_menus/<pk>）。
# 权限要求：基类按 perm_prefix='system:role' 生成权限点；两个授权接口同样受该前缀保护。
# 关键约定：角色-菜单关系存中间表 sys_role_menu，用原生 SQL 覆盖式写入；内置管理员角色(id=1)禁止删除。
from django.db import connection  # 角色-菜单关联表使用原始 SQL

from apps.system.models import SysRole  # 角色模型
from apps.system.serializers import RoleSerializer  # 角色序列化器
from common.response import fail, ok  # 统一响应封装
from common.views import CrudViewSet  # 通用 CRUD 基类


# 内部工具：覆盖式保存角色菜单授权，供 assign_menus 调用。
# 覆盖式语义：先删旧关联再插新关联，前端无需计算增删差集，提交完整列表即可。
def save_role_menus(role_id, menu_ids):
    """覆盖式保存角色菜单授权：先清空旧关联再批量插入。"""
    # 游标上下文自动关闭连接资源；事务由请求层/数据库自动提交控制。
    with connection.cursor() as cursor:  # 原始 SQL 需显式游标
        # 先清空该角色的全部旧授权，保证最终结果与前端提交的列表完全一致。
        cursor.execute("DELETE FROM sys_role_menu WHERE role_id = %s", [role_id])  # 清除旧授权
        # 新列表为空表示清空全部授权，此时跳过 INSERT，避免执行空批量语句。
        if menu_ids:  # 有授权项才插入
            # executemany 一次提交多条 INSERT，比逐条 execute 减少网络往返。
            cursor.executemany(
                "INSERT INTO sys_role_menu (role_id, menu_id) VALUES (%s, %s)",
                [(role_id, mid) for mid in menu_ids])  # 批量写入关联


class RoleViewSet(CrudViewSet):
    """角色管理视图：列表可全量返回，内置管理员角色禁止删除。"""
    # 标准增删改查由基类提供；本类只覆盖 list（可选全量）与 delete（保护内置角色）。
    model = SysRole  # 目标模型
    serializer_class = RoleSerializer  # 序列化器
    perm_prefix = 'system:role'  # 权限标识前缀
    module_name = '角色管理'  # 操作日志模块名
    # 角色名称模糊搜索 + 状态精确筛选；不支持的参数会被基类忽略。
    filter_map = {'role_name': 'icontains', 'status': 'exact'}  # 列表筛选字段

    # 角色数量通常很少，默认全量返回便于前端下拉；显式传 page 时才启用分页。
    def list(self, request):
        """不分页：角色数量有限，直接全量返回便于下拉选择。"""
        # 只要带 page 参数就交回基类，复用统一分页结构，兼容管理页表格。
        if request.query_params.get('page'):  # 显式要求分页时走基类逻辑
            return super().list(request)  # 分页返回
        # 不分页时仍需应用筛选条件，保持与分页列表一致的搜索体验。
        queryset = self.apply_filters(self.get_queryset(), request)  # 应用筛选条件
        # 全量序列化后直接放进 data；前端下拉无需再处理分页字段。
        return ok(RoleSerializer(queryset, many=True).data)  # 全量返回

    # 覆盖基类批量删除：内置管理员角色是系统兜底账号的权限来源，必须禁止删除。
    def delete(self, request):
        """删除角色：内置管理员角色（id=1）不允许删除。"""
        # 与基类一致，前端批量删除提交 {"ids": [...]}；缺省为空列表。
        ids = request.data.get('ids') or []  # 待删除角色ID
        # 逐个转 int 后判断是否包含 1；兼容前端传字符串 ID 的情况。
        if any(int(i) == 1 for i in ids):  # 含内置管理员角色
            return fail('内置管理员角色不允许删除')  # 拒绝删除
        # 不含内置角色时交回基类，复用统一逻辑删除与审计处理。
        return super().delete(request)  # 走基类逻辑删除

    # 查询某角色已授权的菜单 ID 列表，供授权弹窗回填勾选状态。
    def menu_ids(self, request, pk=None):
        """查询角色已授权的菜单ID列表。"""
        # 直接查中间表，比 ORM 多对多查询更直接，也不依赖模型是否声明 M2M。
        with connection.cursor() as cursor:  # 原始 SQL 需显式游标
            # 按 role_id 查询；未授权时返回空列表，前端默认全部不勾选。
            cursor.execute("SELECT menu_id FROM sys_role_menu WHERE role_id = %s", [pk])  # 查角色-菜单中间表
            # 只取第一列（menu_id），组装成前端可直接消费的 ID 数组。
            return ok({'menu_ids': [r[0] for r in cursor.fetchall()]})  # 返回ID数组

    # 覆盖式保存角色菜单授权：提交完整 menu_ids，服务端先清后插。
    def assign_menus(self, request, pk=None):
        """为指定角色保存菜单授权（覆盖式）。"""
        # 先校验角色存在且未删除，避免向不存在的角色写入脏关联。
        if not self.get_queryset().filter(pk=pk).exists():  # 先校验角色存在
            return fail('角色不存在', code=404)  # 角色不存在
        # 未传 menu_ids 视为清空授权，与“提交空列表”语义一致。
        save_role_menus(pk, request.data.get('menu_ids') or [])  # 覆盖保存授权
        # 不回传授权结果，前端保存成功后可重新拉取或直接使用本地勾选状态。
        return ok(None, '分配菜单权限成功')  # 返回成功
