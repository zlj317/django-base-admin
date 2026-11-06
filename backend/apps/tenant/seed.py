"""多租户种子：菜单 + 按钮权限（幂等）。"""
# 文件：apps/tenant/seed.py —— 多租户模块的菜单与按钮权限种子脚本
# 用途：创建"租户管理""租户套餐"两个页面菜单，并为租户管理挂上增删改查按钮权限。
# 对应表：写入 sys_menu（菜单与按钮）、sys_role_menu（角色-菜单授权）；不写 sys_tenant 等业务表。
# 路由前缀：菜单 path 为 tenant/tenant 与 tenant/package，对应后端 /api/tenant/tenant/、/api/tenant/package/。
# 调用方：core/management/commands/init_db.py 初始化数据库时调用 seed_tenant()。
# 幂等策略：菜单按"父级 + 名称 + 未删除"判重；授权使用 INSERT IGNORE 忽略重复行。
# 租户隔离：种子只负责建菜单与授权，不涉及租户数据过滤，也不按租户区分菜单。
# 生成 create_time/update_time 字符串，与手工建表 DATETIME 列对齐
import time

# 系统菜单模型与角色模型
from apps.system.models import SysMenu, SysRole

# 菜单定义：依次为（父级 key、本级 key、名称、路由 path、前端组件、权限标识、类型、图标、排序）
# 类型 C=菜单页面、F=按钮权限（见下方 BUTTONS）；父级 key='system' 表示挂到"系统管理"目录下
MENUS = [
    # 租户管理页：path=tenant，进入页面需要 tenant:tenant:list 权限
    ('system', 'tenant', '租户管理', 'tenant', 'tenant/tenant/index', 'tenant:tenant:list', 'C', 'OfficeBuilding', 7),
    # 租户套餐页：path=package；菜单权限沿用 tenant:tenant:list（与后端 tenant:package:* 并不一致）
    ('system', 'tenant_package', '租户套餐', 'package', 'tenant/package/index', 'tenant:tenant:list', 'C', 'Box', 8),
]

# 按钮权限定义：按页面 key 分组，每组为（按钮名称、权限标识）列表
BUTTONS = {
    # 仅租户管理页配置按钮：查询/新增/编辑/删除，对应后端 perm_prefix='tenant:tenant'
    'tenant': [('查询', 'tenant:tenant:list'), ('新增', 'tenant:tenant:create'),
               # 编辑与删除属于写操作，分别对应 update/delete 接口
               ('编辑', 'tenant:tenant:update'), ('删除', 'tenant:tenant:delete')],
    # 注意：tenant_package 未配置按钮，后端套餐接口所需的 tenant:package:* 权限不会由本脚本生成
}


# 幂等创建单条菜单（或按钮）：已存在直接复用，避免重复执行 init_db 产生重复菜单
def _ensure_menu(parent_id, name, path, component, perms, mtype, icon, order):
    # 以"父级 + 名称 + 未删除"作为幂等键查询现有记录
    row = SysMenu.objects.filter(parent_id=parent_id, menu_name=name, is_deleted=0).first()
    # 命中说明之前已初始化过，直接复用已有行（授权时也复用它的 ID）
    if row:
        # 已存在则返回原记录，保证重复执行不产生重复数据
        return row
    # 不存在才新建；统一使用字符串时间格式，与其它模块种子保持一致
    now = time.strftime('%Y-%m-%d %H:%M:%S')
    # 插入新菜单/按钮；id 由雪花算法字段在 create 时自动生成
    return SysMenu.objects.create(
        # 层级与展示属性：父级、名称、路由、前端组件、权限标识
        parent_id=parent_id, menu_name=name, path=path, component=component, perms=perms,
        # 类型（C 页面/F 按钮）、图标、排序；visible/status 为 '0' 表示显示且启用
        menu_type=mtype, icon=icon, order_num=order, visible='0', status='0',
        # 审计字段固定为 admin：种子数据没有真实操作人
        create_by='admin', create_time=now, update_by='admin', update_time=now, is_deleted=0)


# 初始化入口：创建菜单与按钮，并授权给所有未删除角色
def seed_tenant():
    # 延迟导入数据库连接：仅本函数需要原生游标做批量授权
    from django.db import connection
    # 查找"系统管理"目录作为这批菜单的父级；找不到时退化为顶级（parent_id=0）
    system_menu = SysMenu.objects.filter(menu_name='系统管理', is_deleted=0).first()
    # 父级 ID：存在则用其主键，否则 0 表示顶级节点
    system_id = system_menu.id if system_menu else 0
    # 记录 key → 菜单 ID，供后续菜单回填父级（当前 MENUS 都挂 system，保留通用能力）
    menu_ids = {}
    # 收集本次涉及的菜单/按钮 ID，最后统一授权
    created_ids = []
    # 按定义顺序创建，父级先于子级
    for parent_key, key, name, path, component, perms, mtype, icon, order in MENUS:
        # parent_key='system' 统一挂系统管理；其他 key 从 menu_ids 取父级，None 则作为顶级
        parent_id = system_id if parent_key == 'system' else (menu_ids.get(parent_key, 0) if parent_key else 0)
        # 幂等创建菜单本身
        row = _ensure_menu(parent_id, name, path, component, perms, mtype, icon, order)
        # 缓存本级 ID 供后续子级/按钮挂载
        menu_ids[key] = row.id
        # 菜单本身也要加入授权集合
        created_ids.append(row.id)
        # 为该页面创建按钮权限；套餐页没有 BUTTONS 定义，get 返回空列表直接跳过
        for btn_name, btn_perms in BUTTONS.get(key, []):
            # 按钮的父级是所属页面；类型 F、无路由与组件、排序 0
            btn = _ensure_menu(row.id, btn_name, '', '', btn_perms, 'F', '', 0)
            # 按钮同样需要授权，加入统一集合
            created_ids.append(btn.id)
    # 取出全部未删除角色 ID：种子默认给所有角色授权（含后续可用的自定义角色）
    role_ids = list(SysRole.objects.filter(is_deleted=0).values_list('id', flat=True))
    # 原生游标批量写入角色-菜单关联表，避免逐条 ORM 开销
    with connection.cursor() as cursor:
        # 外层遍历角色
        for role_id in role_ids:
            # 内层遍历本次创建的菜单与按钮
            for menu_id in created_ids:
                # INSERT IGNORE：重复执行时已有授权行被忽略，保证幂等且不报错
                cursor.execute('INSERT IGNORE INTO sys_role_menu (role_id, menu_id) VALUES (%s, %s)',
                               # 参数顺序必须与 SQL 占位符一致
                               [role_id, menu_id])
