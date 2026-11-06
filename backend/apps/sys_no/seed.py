"""编码规则模块种子：菜单 + 按钮权限。"""
# 模块：apps/sys_no/seed.py —— 编码规则模块的菜单与按钮权限初始化脚本
# 用途：创建"编码规则管理"页面菜单，并挂上查询/新增/编辑/删除/生成编号五个按钮权限。
# 数据表：写入 sys_menu（菜单与按钮）、sys_role_menu（角色-菜单授权）。
# 调用方：core/management/commands/init_db.py 初始化数据库时调用 seed_sys_no()。
# 幂等策略：菜单按"父级 + 名称 + 未删除"判重；授权用 INSERT IGNORE 忽略已存在的角色-菜单关联。
import time

from apps.system.models import SysMenu, SysRole

# 菜单定义：每行依次为（父级菜单名、本级 key、菜单名、路由 path、前端组件、权限标识、类型、图标、排序）
# 类型 C=菜单页面；父级用"菜单名"文本解析为父菜单 ID（与报表模块用 key 解析的方式不同）
MENUS = [
    # 编码规则管理页面：挂在"系统管理"目录下，路由 rule，前端组件 sys_no/rule/index
    ('系统管理', 'sys_no_rule', '编码规则管理', 'rule', 'sys_no/rule/index', 'sys_no:list', 'C', 'Tickets', 1),
]

# 按钮权限定义：key 对应上面的菜单 key，值为（按钮名称、权限标识）列表
BUTTONS = {
    # 规则页面：标准增删改查 + 生成编号；generate 对应视图集的 generate 动作
    'sys_no_rule': [('查询', 'sys_no:list'), ('新增', 'sys_no:create'),
                    # 编辑与删除：写操作按钮
                    ('编辑', 'sys_no:update'), ('删除', 'sys_no:delete'),
                    # 生成编号：调用 POST /sys_no/rule/generate/<pk>，每次会递增流水并写日志
                    ('生成编号', 'sys_no:generate')],
}


# 幂等创建单条菜单：已存在直接复用，避免重复执行 init_db 产生重复菜单
def _ensure_menu(parent_id, name, path, component, perms, mtype, icon, order):
    # 以"父级 + 名称 + 未删除"作为幂等键查询现有记录
    row = SysMenu.objects.filter(parent_id=parent_id, menu_name=name, is_deleted=0).first()
    # 命中说明之前已初始化过，直接返回已有行，后续授权复用其 ID
    if row:
        # 复用已有菜单，保证重复执行不产生重复数据
        return row
    # 不存在才新建；统一使用字符串时间格式，与其它模块种子保持一致
    now = time.strftime('%Y-%m-%d %H:%M:%S')
    # 插入新菜单并返回实例；主键由雪花算法字段自动生成
    return SysMenu.objects.create(
        # 基础属性：父级、名称、路由、前端组件与权限标识
        parent_id=parent_id, menu_name=name, path=path, component=component, perms=perms,
        # visible/status 为 '0' 表示显示且启用
        menu_type=mtype, icon=icon, order_num=order, visible='0', status='0',
        # 审计字段固定为 admin，种子数据没有真实操作人
        create_by='admin', create_time=now, update_by='admin', update_time=now, is_deleted=0)


# 初始化入口：创建菜单、按钮并授权给所有有效角色
def seed_sys_no():
    # 延迟导入数据库连接：仅本函数需要原生游标做批量授权
    from django.db import connection
    # 记录 key → 菜单 ID（当前只有一个页面，保留该结构便于后续扩展子菜单）
    menu_ids = {}
    # 收集本次涉及的所有菜单/按钮 ID，最后统一授权
    created_ids = []
    # 按定义顺序创建菜单（父菜单先于子菜单）
    for parent_key, key, name, path, component, perms, mtype, icon, order in MENUS:
        # 父级按"菜单名"查找：找到则取其 ID，找不到时兜底 0（顶级菜单）
        parent_row = SysMenu.objects.filter(menu_name=parent_key, is_deleted=0).first()
        # 父菜单存在用其主键，否则置 0，避免因父级缺失导致 seed 失败
        parent_id = parent_row.id if parent_row else 0
        # 幂等创建菜单本身
        row = _ensure_menu(parent_id, name, path, component, perms, mtype, icon, order)
        # 缓存本级 ID，方便后续按钮挂载与扩展子菜单
        menu_ids[key] = row.id
        # 菜单本身也要加入授权集合
        created_ids.append(row.id)
        # 为该页面创建按钮权限；无定义的 key 返回空列表
        for btn_name, btn_perms in BUTTONS.get(key, []):
            # 按钮父级为所属页面；类型 F 表示按钮权限，无路由与组件
            btn = _ensure_menu(row.id, btn_name, '', '', btn_perms, 'F', '', 0)
            # 按钮同样需要授权，加入统一授权集合
            created_ids.append(btn.id)
    # 取出全部未删除角色 ID，种子默认给所有角色授权
    role_ids = list(SysRole.objects.filter(is_deleted=0).values_list('id', flat=True))
    # 用原生游标批量写入关联表，减少逐条 ORM 开销
    with connection.cursor() as cursor:
        # 外层：遍历每个角色
        for role_id in role_ids:
            # 内层：遍历本次创建的菜单与按钮
            for menu_id in created_ids:
                # INSERT IGNORE：重复执行时已有授权行被忽略，保证幂等且不报错
                cursor.execute('INSERT IGNORE INTO sys_role_menu (role_id, menu_id) VALUES (%s, %s)',
                               # 参数顺序必须与 SQL 占位符一致
                               [role_id, menu_id])
