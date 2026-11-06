"""公告通知种子：菜单 + 按钮权限（幂等）。"""
# 模块：apps/notice/seed.py —— 公告模块的菜单与按钮权限初始化脚本
# 用途：首次部署或新增角色后执行 seed_notice()，把公告菜单树与按钮权限写入 sys_menu，并授权给所有有效角色。
# 对应表：sys_menu（菜单/按钮定义）、sys_role_menu（角色-菜单授权关系）、sys_role（角色）
# 路由前缀：菜单 path 供前端动态路由使用（notice/category/index、notice/info/index）
# 关键约定：以「父级 ID + 菜单名」作为幂等键，重复执行不产生重复菜单；授权 SQL 用 INSERT IGNORE 防重。
import time  # 创建时间

from apps.system.models import SysMenu, SysRole  # 系统菜单与角色模型

# 菜单定义：(父级 key, 本菜单 key, 名称, 路由 path, 前端组件 path, 权限标识, 类型, 图标, 排序)
# 类型 M=目录、C=菜单、F=按钮；顶级目录「公告通知」下挂分类与公告管理两个页面。
MENUS = [
    # 顶级目录：parent_key 为 None 表示根菜单，排序 7 决定它在侧边栏中的位置。
    (None, 'notice', '公告通知', 'notice', '', '', 'M', 'Reading', 7),
    # 公告分类菜单：父级为 notice，组件路径指向前端页面，权限标识 notice:list 控制可见性。
    ('notice', 'notice_category', '公告分类', 'category', 'notice/category/index', 'notice:list', 'C', 'Collection', 1),
    # 公告管理菜单：公告正文的列表与编辑入口，同为 notice:list 权限。
    ('notice', 'notice_info', '公告管理', '', 'notice/info/index', 'notice:list', 'C', 'Document', 2),
]

# 按钮权限定义：菜单 key -> [(按钮显示名, 权限标识)]，最终以 menu_type='F' 的菜单行落库。
BUTTONS = {
    # 公告分类页：标准增删改查四个按钮。
    'notice_category': [('查询', 'notice:list'), ('新增', 'notice:create'),
                        ('编辑', 'notice:update'), ('删除', 'notice:delete')],
    # 公告信息页：同样提供增删改查按钮；发布/下线由后端动作接口控制，不单独建按钮。
    'notice_info': [('查询', 'notice:list'), ('新增', 'notice:create'),
                    ('编辑', 'notice:update'), ('删除', 'notice:delete')],
}


# 幂等创建单个菜单/按钮：同父级同名且未删除的记录已存在则直接复用，否则插入新记录。
def _ensure_menu(parent_id, name, path, component, perms, mtype, icon, order):
    # 幂等键：父级 ID + 菜单名；is_deleted=0 保证只命中有效记录。
    row = SysMenu.objects.filter(parent_id=parent_id, menu_name=name, is_deleted=0).first()
    if row:
        return row
    # 统一时间字符串，与手工建表 SQL 的 DATETIME 格式保持一致。
    now = time.strftime('%Y-%m-%d %H:%M:%S')
    # 不存在才插入；visible/status 的 '0' 表示显示/启用，is_deleted=0 表示未删除。
    return SysMenu.objects.create(
        parent_id=parent_id, menu_name=name, path=path, component=component, perms=perms,
        menu_type=mtype, icon=icon, order_num=order, visible='0', status='0',
        create_by='admin', create_time=now, update_by='admin', update_time=now, is_deleted=0)


# 种子入口：由初始化命令或运维脚本调用，可重复执行。
def seed_notice():
    # 延迟导入 connection：只有执行原生批量授权 SQL 时才需要，避免模块加载即依赖数据库连接。
    from django.db import connection
    # key -> 菜单 ID 映射，供子菜单回填父级 ID。
    menu_ids = {}
    # 本次创建或复用的全部菜单/按钮 ID，最后统一授权给角色。
    created_ids = []
    # 按 MENUS 定义顺序创建，保证父级先于子级存在。
    for parent_key, key, name, path, component, perms, mtype, icon, order in MENUS:
        # 顶级菜单父级为 0；子菜单从映射中取已创建好的父级 ID。
        parent_id = menu_ids.get(parent_key, 0) if parent_key else 0
        # 幂等创建当前菜单。
        row = _ensure_menu(parent_id, name, path, component, perms, mtype, icon, order)
        # 记录当前菜单 ID，供后续子菜单使用。
        menu_ids[key] = row.id
        # 收集授权目标。
        created_ids.append(row.id)
        # 当前菜单若配置了按钮，则逐个创建 F 类型（按钮）记录。
        for btn_name, btn_perms in BUTTONS.get(key, []):
            # 按钮无独立路由与组件，path/component 传空串。
            btn = _ensure_menu(row.id, btn_name, '', '', btn_perms, 'F', '', 0)
            created_ids.append(btn.id)
    # 取出所有未删除角色的 ID；flat=True 直接返回 ID 值而非元组。
    role_ids = list(SysRole.objects.filter(is_deleted=0).values_list('id', flat=True))
    # 使用原生游标批量授权，避免逐条走 ORM 产生大量 SQL。
    with connection.cursor() as cursor:
        # 每个有效角色都授予本次全部菜单与按钮。
        for role_id in role_ids:
            # 菜单与按钮逐个授权。
            for menu_id in created_ids:
                # INSERT IGNORE：唯一键冲突时静默跳过，保证脚本可重复执行。
                cursor.execute('INSERT IGNORE INTO sys_role_menu (role_id, menu_id) VALUES (%s, %s)',
                               [role_id, menu_id])
