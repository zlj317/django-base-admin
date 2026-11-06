"""监控告警种子：菜单 + 按钮权限（幂等）。"""
# 模块：apps/mon/seed.py —— 监控告警模块的菜单与按钮权限初始化脚本
# 用途：在“系统管理”下创建“监控告警”“告警记录”两个页面菜单，并给规则页挂增删改查按钮权限。
# 对应表：写入 sys_menu（菜单与按钮权限）、sys_role_menu（角色-菜单授权）。
# 调用方：core/management/commands/init_db.py 初始化数据库时调用 seed_mon()。
# 路由前缀：前端页面路径 mon/rule/index、mon/record/index，对应后端 /api/mon/rule、/api/mon/record。
# 告警生命周期：菜单只负责入口与权限，不参与告警判定；生命周期见 apps/mon/models.py。
# 幂等策略：菜单按“父级 + 名称 + 未删除”判重，授权用 INSERT IGNORE 忽略重复行。
# 生成创建时间字符串，与库表 DATETIME 约定一致
import time

# 系统菜单与角色模型
from apps.system.models import SysMenu, SysRole

# 菜单定义：(父级 key、本级 key、菜单名、路由 path、前端组件、权限标识、类型、图标、排序)
# 两条菜单都挂在“系统管理”目录下（父级 key=system）；类型 C 表示菜单页面
MENUS = [
    # 规则页：告警规则的维护入口，权限文案 mon:rule:list
    ('system', 'mon', '监控告警', 'mon', 'mon/rule/index', 'mon:rule:list', 'C', 'Warning', 5),
    # 记录页：告警记录的查询入口；沿用现有权限标识 mon:rule:list
    ('system', 'mon_record', '告警记录', 'mon_record', 'mon/record/index', 'mon:rule:list', 'C', 'Bell', 6),
]

# 按钮权限定义：key 对应上面的菜单 key，值为（按钮名称、权限标识）列表
BUTTONS = {
    # 规则页：标准增删改查四个按钮；记录页未配置按钮，保持只读入口
    'mon': [('查询', 'mon:rule:list'), ('新增', 'mon:rule:create'),
            # 编辑与删除：写操作按钮
            ('编辑', 'mon:rule:update'), ('删除', 'mon:rule:delete')],
}


# 幂等创建单条菜单：已存在直接复用，避免重复执行 init_db 产生重复菜单
def _ensure_menu(parent_id, name, path, component, perms, mtype, icon, order):
    # 以“父级 + 名称 + 未删除”作为幂等键查询现有记录
    row = SysMenu.objects.filter(parent_id=parent_id, menu_name=name, is_deleted=0).first()
    # 命中说明之前已初始化过，直接复用已有行（后续授权也复用它的 ID）
    if row:
        # 复用已有菜单，保证重复执行不产生重复数据
        return row
    # 不存在才新建；统一使用字符串时间格式，与其它模块种子保持一致
    now = time.strftime('%Y-%m-%d %H:%M:%S')
    # 插入新菜单并返回实例；id 由雪花算法字段生成
    return SysMenu.objects.create(
        # 基础属性：父级、名称、路由、前端组件与权限标识
        parent_id=parent_id, menu_name=name, path=path, component=component, perms=perms,
        # visible/status 为 '0' 表示显示且启用
        menu_type=mtype, icon=icon, order_num=order, visible='0', status='0',
        # 审计字段固定为 admin，种子数据无真实操作人；初始未删除
        create_by='admin', create_time=now, update_by='admin', update_time=now, is_deleted=0)


# 初始化入口：创建菜单、按钮并授权给所有有效角色
def seed_mon():
    # 延迟导入数据库连接：仅本函数需要原生游标做批量授权
    from django.db import connection
    # 两个菜单都挂在“系统管理”目录下，先查出该目录的主键
    system_menu = SysMenu.objects.filter(menu_name='系统管理', is_deleted=0).first()
    # 目录不存在时退化为 0（顶级菜单），保证初始化不因缺少父级而失败
    system_id = system_menu.id if system_menu else 0
    # 记录 key → 菜单 ID，供子级回填父级
    menu_ids = {}
    # 收集本次涉及的所有菜单/按钮 ID，统一授权
    created_ids = []
    # 按定义顺序创建，保证父级先于子级
    for parent_key, key, name, path, component, perms, mtype, icon, order in MENUS:
        # 父级为 system 时用系统管理目录 ID，其余按 key 从已建菜单中取
        parent_id = system_id if parent_key == 'system' else (menu_ids.get(parent_key, 0) if parent_key else 0)
        # 幂等创建菜单本身
        row = _ensure_menu(parent_id, name, path, component, perms, mtype, icon, order)
        # 缓存本级 ID 供后续子级使用
        menu_ids[key] = row.id
        # 菜单本身也要加入授权集合
        created_ids.append(row.id)
        # 为该页面创建按钮权限；无定义的 key 返回空列表
        for btn_name, btn_perms in BUTTONS.get(key, []):
            # 按钮父级是所属页面；类型 F 表示按钮权限，无路由与组件
            btn = _ensure_menu(row.id, btn_name, '', '', btn_perms, 'F', '', 0)
            # 按钮也要授权，加入统一授权集合
            created_ids.append(btn.id)
    # 取出全部未删除角色 ID，种子默认给所有角色授权
    role_ids = list(SysRole.objects.filter(is_deleted=0).values_list('id', flat=True))
    # 用原生游标批量写入关联表，避免逐条 ORM 开销
    with connection.cursor() as cursor:
        # 外层：遍历每个角色
        for role_id in role_ids:
            # 内层：遍历本次创建的菜单与按钮
            for menu_id in created_ids:
                # INSERT IGNORE：重复执行时已有授权行被忽略，保证幂等且不报错
                cursor.execute('INSERT IGNORE INTO sys_role_menu (role_id, menu_id) VALUES (%s, %s)',
                               # 参数顺序必须与 SQL 占位符一致
                               [role_id, menu_id])
