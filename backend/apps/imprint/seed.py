"""导入模板 + 打印模板模块种子：菜单 + 按钮权限。"""
# 模块：apps/imprint/seed.py —— 导入模板 / 打印模板模块的菜单与按钮权限初始化脚本。
# 用途：在“系统管理”目录下创建三个页面菜单，并为导入模板、打印模板挂上增删改查按钮权限。
# 对应表：写入 sys_menu（菜单与按钮）、sys_role_menu（角色-菜单授权），不写业务表本身。
# 路由前缀：菜单 path 与 /api/imprint/ 下的 template、column、print 一一对应。
# 幂等性：菜单按“父级 + 名称 + 未删除”判重；授权 SQL 使用 INSERT IGNORE，可重复执行。
import time

# 菜单模型（含按钮）与角色模型，用于建菜单并授权
from apps.system.models import SysMenu, SysRole

# 菜单定义：每行依次为（父级菜单名、本级 key、菜单名、路由 path、前端组件、权限标识、类型、图标、排序）
# 首列为父级“菜单名”而非 key，故 seed_imprint 中需按 menu_name 反查父级 ID。
MENUS = [
    # 导入模板页：C 表示菜单页面，路由 /api/imprint/template，前端页面 imprint/template/index
    ('系统管理', 'imp_template', '导入模板管理', 'template', 'imprint/template/index', 'imprint:list', 'C', 'Upload', 1),
    # 模板列页：排序列 3，前端页面 imprint/column/index
    ('系统管理', 'imp_column', '导入模板列', 'column', 'imprint/column/index', 'imprint:list', 'C', 'Grid', 3),
    # 打印模板页：排序列 2，前端页面 imprint/print/index
    ('系统管理', 'print_template', '打印模板管理', 'print', 'imprint/print/index', 'imprint:list', 'C', 'Printer', 2),
]

# 按钮权限定义：key 为上面的本级 key，值为（按钮名称、权限标识）列表
BUTTONS = {
    # 导入模板：标准增删改查四个按钮，权限标识与视图集 perm_prefix 的拼接规则一致
    'imp_template': [('查询', 'imprint:list'), ('新增', 'imprint:create'),
                     # 编辑/删除属写操作按钮
                     ('编辑', 'imprint:update'), ('删除', 'imprint:delete')],
    # 打印模板：同为标准增删改查
    'print_template': [('查询', 'imprint:list'), ('新增', 'imprint:create'),
                       # 编辑/删除属写操作按钮
                       ('编辑', 'imprint:update'), ('删除', 'imprint:delete')],
}


# 幂等创建单条菜单/按钮：已存在则复用，避免重复执行初始化产生重复记录。
def _ensure_menu(parent_id, name, path, component, perms, mtype, icon, order):
    # 幂等键为“父级 + 名称 + 未删除”，与其它模块种子的判重口径一致
    row = SysMenu.objects.filter(parent_id=parent_id, menu_name=name, is_deleted=0).first()
    # 命中说明此前已创建过，直接复用其 ID，后续授权也随之幂等
    if row:
        # 已存在不重复插入
        return row
    # 仅在需要新建时才生成时间串，减少无谓的字符串开销
    now = time.strftime('%Y-%m-%d %H:%M:%S')
    # 新建菜单/按钮；返回实例，id 由雪花算法生成
    return SysMenu.objects.create(
        # 基础属性：父级、名称、路由、前端组件与权限标识
        parent_id=parent_id, menu_name=name, path=path, component=component, perms=perms,
        # '0' 表示显示且启用
        menu_type=mtype, icon=icon, order_num=order, visible='0', status='0',
        # 种子数据固定操作人，时间串与库表 DATETIME 格式一致
        create_by='admin', create_time=now, update_by='admin', update_time=now, is_deleted=0)


# 初始化入口：建菜单、建按钮，并把它们授权给所有未删除角色。
def seed_imprint():
    # 延迟导入：仅此处需要原生游标做批量 INSERT IGNORE
    from django.db import connection
    # 记录 key → 菜单 ID，便于后续扩展父子关系
    menu_ids = {}
    # 收集本次涉及的所有菜单与按钮 ID，最后统一授权
    created_ids = []
    # 按定义顺序创建；每次循环都会按菜单名反查一次父级（父级不存在时退化为顶级 0）
    for parent_key, key, name, path, component, perms, mtype, icon, order in MENUS:
        # 按名称查“系统管理”父菜单
        parent_row = SysMenu.objects.filter(menu_name=parent_key, is_deleted=0).first()
        # 父级缺失时挂到根节点，保证菜单仍能创建成功
        parent_id = parent_row.id if parent_row else 0
        # 幂等创建页面菜单
        row = _ensure_menu(parent_id, name, path, component, perms, mtype, icon, order)
        # 缓存本级 ID（当前未被读取，保留供扩展）
        menu_ids[key] = row.id
        # 菜单本身也要参与授权
        created_ids.append(row.id)
        # 为该页面创建按钮权限；未定义按钮的 key 返回空列表，循环自然跳过
        for btn_name, btn_perms in BUTTONS.get(key, []):
            # F=按钮权限，无路由与组件
            btn = _ensure_menu(row.id, btn_name, '', '', btn_perms, 'F', '', 0)
            # 按钮同样加入授权集合
            created_ids.append(btn.id)
    # 取出全部未删除角色，种子默认把所有菜单/按钮授权给每个角色
    role_ids = list(SysRole.objects.filter(is_deleted=0).values_list('id', flat=True))
    # 原生游标批量写入关联表，避免逐条 ORM 的开销
    with connection.cursor() as cursor:
        # 外层遍历角色
        for role_id in role_ids:
            # 内层遍历本次涉及的菜单与按钮
            for menu_id in created_ids:
                # INSERT IGNORE：重复授权行被数据库忽略，保证脚本可重复执行且不报错；
                # 参数顺序必须与 SQL 占位符一致
                cursor.execute('INSERT IGNORE INTO sys_role_menu (role_id, menu_id) VALUES (%s, %s)',
                               [role_id, menu_id])
