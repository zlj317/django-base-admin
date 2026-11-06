"""脱敏配置种子：菜单 + 按钮权限（幂等）。"""
# 模块：apps/dsm/seed.py —— 脱敏配置模块的菜单/按钮权限初始化
# 用途：在"系统管理"目录下创建"脱敏规则配置"页面菜单，并挂上查询/新增/编辑/删除四个按钮权限。
# 对应表：写入 sys_menu（菜单与按钮）、sys_role_menu（角色-菜单授权）。
# 调用方：core/management/commands/init_db.py 初始化数据库时调用 seed_dsm()。
# 路由前缀：菜单 route=dsm、component=dsm/rule/index，对应后端 /api/dsm/rule/*（apps/dsm/urls.py）。
# 脱敏策略：本脚本只初始化配置页面的入口与按钮，不写入任何脱敏规则数据；
#   规则数据由 seed_new_modules.py 内置的 seed_dsm()（另一份实现）插入，且脱敏不会自动作用于接口输出。
# 幂等策略：菜单按"父级 + 名称 + 未删除"判重；授权用 INSERT IGNORE 忽略重复行，重复执行不会产生重复数据。
# 生成统一的创建/更新时间字符串，与手工建表 SQL 的 datetime 列对齐
import time

# 菜单模型（sys_menu）与角色模型（sys_role），用于创建菜单并批量授权
from apps.system.models import SysMenu, SysRole

# 菜单定义：每行依次为（父级 key、本级 key、菜单名、路由 path、前端组件、权限标识、类型、图标、排序）
# 父级 key='system' 表示挂在"系统管理"目录下；类型 C=菜单页面（M=目录、F=按钮）
MENUS = [
    # 唯一菜单：脱敏规则配置页；route=dsm、组件=dsm/rule/index，权限标识决定进入页面所需的权限
    ('system', 'dsm', '脱敏规则配置', 'dsm', 'dsm/rule/index', 'dsm:rule:list', 'C', 'Lock', 4),
]

# 按钮权限定义：key 为上面对应菜单的 key（dsm），值为（按钮名称、权限标识）列表
# 注意：这里只建了规则表的四个权限；field/role 视图集使用的 dsm:field:*、dsm:role:* 没有对应按钮，
#   种子执行后普通角色无法获得这两组权限（疑似遗漏，仅记录不改）
BUTTONS = {
    # 脱敏规则页面：标准增删改查按钮，权限标识与 DesensitizeRuleViewSet.perm_prefix 生成的值一致
    'dsm': [('查询', 'dsm:rule:list'), ('新增', 'dsm:rule:create'),
            ('编辑', 'dsm:rule:update'), ('删除', 'dsm:rule:delete')],
}


# 幂等创建单条菜单/按钮：已存在直接复用，避免重复执行 init_db 产生重复菜单
def _ensure_menu(parent_id, name, path, component, perms, mtype, icon, order):
    # 以"父级 + 名称 + 未删除"作为幂等键查询；名称在同一个父级下唯一，足以区分菜单/按钮
    row = SysMenu.objects.filter(parent_id=parent_id, menu_name=name, is_deleted=0).first()
    # 命中说明之前已初始化过，直接返回已有行，后续授权复用它的 ID
    if row:
        # 复用已有记录，保证脚本可重复执行
        return row
    # 不存在才新建；统一使用字符串时间，与其它模块的种子写入方式保持一致
    now = time.strftime('%Y-%m-%d %H:%M:%S')
    # 插入新菜单/按钮并返回实例；雪花主键由 SysMenu.id 字段的默认值自动生成
    return SysMenu.objects.create(
        # 基础属性：父级、名称、前端路由、组件路径、权限标识
        parent_id=parent_id, menu_name=name, path=path, component=component, perms=perms,
        # visible/status 为 '0' 表示显示且启用；order_num 控制同级菜单排序
        menu_type=mtype, icon=icon, order_num=order, visible='0', status='0',
        # 审计字段固定 admin：种子数据没有真实操作人；is_deleted=0 表示未删除
        create_by='admin', create_time=now, update_by='admin', update_time=now, is_deleted=0)


# 初始化入口：创建菜单、按钮，并把本次涉及的菜单/按钮授权给所有未删除角色
def seed_dsm():
    # 延迟导入数据库连接：只有批量授权需要原生游标，放在函数内可避免模块加载期依赖数据库
    from django.db import connection
    # 按名称找到"系统管理"目录作为父级；若目录尚未创建则 system_id=0，此时菜单会变成顶级菜单
    system_menu = SysMenu.objects.filter(menu_name='系统管理', is_deleted=0).first()
    # 取父级 ID；找不到时退化到 0，保证脚本不报错（但菜单层级可能与预期不符）
    system_id = system_menu.id if system_menu else 0
    # 记录 key → 菜单 ID，供后续子菜单回填父级（本模块只有一层，实际未用到）
    menu_ids = {}
    # 收集本次创建的菜单与按钮 ID，统一做角色授权
    created_ids = []
    # 按定义顺序创建：父级先于子级，便于子菜单取到父级 ID
    for parent_key, key, name, path, component, perms, mtype, icon, order in MENUS:
        # 父级解析：'system' 用上面查到的系统管理目录 ID；其它情况按 key 从 menu_ids 取，未指定则为 0
        parent_id = system_id if parent_key == 'system' else (menu_ids.get(parent_key, 0) if parent_key else 0)
        # 幂等创建菜单本身（已存在则复用）
        row = _ensure_menu(parent_id, name, path, component, perms, mtype, icon, order)
        # 缓存本级 ID，供（潜在的）子菜单使用
        menu_ids[key] = row.id
        # 菜单本身也要加入授权集合
        created_ids.append(row.id)
        # 为该页面创建按钮：按钮的父级是所属页面，类型 F=按钮，无路由与组件
        for btn_name, btn_perms in BUTTONS.get(key, []):
            # 幂等创建按钮，perms 即按钮权限标识，order 固定 0（按钮不参与排序展示）
            btn = _ensure_menu(row.id, btn_name, '', '', btn_perms, 'F', '', 0)
            # 按钮同样要授权，加入统一授权集合
            created_ids.append(btn.id)
    # 取出全部未删除角色的 ID，种子默认给所有角色授予这些菜单/按钮权限
    role_ids = list(SysRole.objects.filter(is_deleted=0).values_list('id', flat=True))
    # 使用原生游标批量写关联表：比逐条 ORM 创建开销更小，也便于使用 INSERT IGNORE
    with connection.cursor() as cursor:
        # 外层：遍历每个角色
        for role_id in role_ids:
            # 内层：遍历本次涉及的菜单与按钮
            for menu_id in created_ids:
                # INSERT IGNORE：重复执行时已存在的授权行被忽略，保证幂等且不抛唯一键冲突
                cursor.execute('INSERT IGNORE INTO sys_role_menu (role_id, menu_id) VALUES (%s, %s)',
                               # 参数顺序必须与 SQL 占位符一致：先角色、后菜单
                               [role_id, menu_id])
