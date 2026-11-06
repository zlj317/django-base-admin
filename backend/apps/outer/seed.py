"""外部对接种子：菜单 + 按钮权限（幂等）。"""
# 模块用途：写入外部对接模块的菜单与按钮权限，供前端 outer/api、outer/log、outer/sync 三个页面展示。
# 对应表：sys_menu（菜单与按钮记录）、sys_role_menu（角色-菜单授权关系）。
# 幂等策略：_ensure_menu 以「父级 + 菜单名」为键先查后插；授权用 INSERT IGNORE，重复执行不报错。
# 调用入口：core/management/commands/init_db.py 初始化菜单后调用 seed_outer()。
# 现状：本文件只处理菜单权限，不创建 outer_api_config 等三张业务表（表由 docs SQL 手工建）。
import time  # 创建时间

from apps.system.models import SysMenu, SysRole  # 系统菜单与角色模型

# 菜单元组字段：父级 key、菜单 key、菜单名称、前端路径、组件路径、权限标识、类型(M 目录/C 菜单)、图标、排序。
MENUS = [
    # 顶级目录：无父级；component 为空表示仅作为分组，不渲染具体页面。
    (None, 'outer', '外部对接', 'outer', '', '', 'M', 'Link', 12),
    # 外部接口页：挂在 outer 目录下，列表权限 outer:list。
    ('outer', 'outer_api', '外部接口', 'api', 'outer/api/index', 'outer:list', 'C', 'Link', 1),
    # 请求日志页：只读为主，复用列表权限 outer:list。
    ('outer', 'outer_log', '请求日志', 'log', 'outer/log/index', 'outer:list', 'C', 'Tickets', 2),
    # 同步任务页：管理任务定义，列表权限 outer:list。
    ('outer', 'outer_sync', '同步任务', 'sync', 'outer/sync/index', 'outer:list', 'C', 'Refresh', 3),
    # 菜单清单结束：1 个顶级目录 + 3 个页面菜单。
]

# 按钮权限：按菜单 key 分组，每项为（按钮名称, 权限标识），写入 sys_menu 的 F 类型记录。
BUTTONS = {
    # 接口配置页：标准增删改查之外，额外提供“测试”和“调用”两个动作权限。
    'outer_api': [('查询', 'outer:list'), ('新增', 'outer:create'),
                  # 编辑/删除是通用按钮，权限标识与基类标准动作一一对应。
                  ('编辑', 'outer:update'), ('删除', 'outer:delete'),
                  # 测试与调用会让后端真实出网，单独授权便于按角色收紧。
                  ('测试', 'outer:test'), ('调用', 'outer:call')],
    # 日志页只允许查询与清理，不提供新增/编辑（日志由后端自动写入）。
    'outer_log': [('查询', 'outer:list'), ('删除', 'outer:delete')],
    # 同步任务页：标准增删改查 + 手动执行按钮（对应 run_once 动作）。
    'outer_sync': [('查询', 'outer:list'), ('新增', 'outer:create'),
                   # 编辑/删除沿用标准动作权限。
                   ('编辑', 'outer:update'), ('删除', 'outer:delete'),
                   # 手动执行对应 run_once；当前是演示实现，不会真正同步数据。
                   ('手动执行', 'outer:runOnce')],
    # BUTTONS 结束：三个菜单各自绑定一组按钮权限。
}


# 幂等写入单条菜单：以「父级 + 名称」为键判断是否已存在，存在则直接复用，避免重复执行产生重复菜单。
def _ensure_menu(parent_id, name, path, component, perms, mtype, icon, order):
    # 以「父级 + 菜单名」为幂等键查询，is_deleted=0 表示只认有效记录。
    row = SysMenu.objects.filter(parent_id=parent_id, menu_name=name, is_deleted=0).first()
    # 已初始化过：不再插入，直接返回原记录，保证脚本可重复执行。
    if row:
        # 直接复用已有记录，避免同一菜单出现多条。
        return row
    # 统一时间字符串格式，与手工建表 SQL 的 DATETIME 约定一致。
    now = time.strftime('%Y-%m-%d %H:%M:%S')
    # 只有不存在时才插入；audit 字段固定为 admin，保证初始化脚本可脱离登录上下文执行。
    return SysMenu.objects.create(
        # 层级、前端路径、组件路径与权限标识决定菜单位置与可访问接口。
        parent_id=parent_id, menu_name=name, path=path, component=component, perms=perms,
        # 类型/图标/排序控制展示形态与同级顺序；'0' 表示显示且启用。
        menu_type=mtype, icon=icon, order_num=order, visible='0', status='0',
        # 审计字段固定 admin 与当前时间，is_deleted=0 表示有效记录。
        create_by='admin', create_time=now, update_by='admin', update_time=now, is_deleted=0)


# 种子主流程：按 MENUS 顺序创建目录/菜单，再为每个菜单补按钮权限，最后给所有角色授权。
def seed_outer():
    # 延迟导入：授权需要原生游标执行 INSERT IGNORE，避免模块顶层加载数据库连接。
    from django.db import connection
    # 菜单 key -> 数据库主键，供子菜单回填 parent_id。
    menu_ids = {}
    # 本次触及的全部菜单/按钮 ID，用于统一授权。
    created_ids = []
    # 第一遍：逐条写入菜单；MENUS 中父级在前，保证 parent_key 一定能取到主键。
    for parent_key, key, name, path, component, perms, mtype, icon, order in MENUS:
        # 父级 key 已在上一轮写入 menu_ids；顶级目录固定 parent_id=0。
        parent_id = menu_ids.get(parent_key, 0) if parent_key else 0
        # 幂等创建当前菜单，返回已有或新建的记录。
        row = _ensure_menu(parent_id, name, path, component, perms, mtype, icon, order)
        # 记录本菜单主键，供后续子菜单/按钮使用。
        menu_ids[key] = row.id
        # 收集菜单 ID，稍后统一授权。
        created_ids.append(row.id)
        # 第二遍（内层）：为当前菜单写入其按钮权限，类型固定为 F，无组件/图标/排序。
        for btn_name, btn_perms in BUTTONS.get(key, []):
            # 按钮作为菜单的子记录写入，parent_id 指向当前菜单。
            btn = _ensure_menu(row.id, btn_name, '', '', btn_perms, 'F', '', 0)
            # 收集按钮 ID，与菜单一起授权。
            created_ids.append(btn.id)
    # 取全部未删除角色，给每个角色授权本次涉及的所有菜单/按钮（演示环境默认全量授权）。
    role_ids = list(SysRole.objects.filter(is_deleted=0).values_list('id', flat=True))
    # 复用 Django 连接执行原生 SQL，避免为纯关联表引入模型。
    with connection.cursor() as cursor:
        # 嵌套写入授权关系；INSERT IGNORE 依赖 sys_role_menu 的唯一索引，重复执行自动跳过。
        for role_id in role_ids:
            # 内层遍历本次全部菜单/按钮 ID。
            for menu_id in created_ids:
                # 参数化传值，避免拼接 SQL 造成注入。
                cursor.execute('INSERT IGNORE INTO sys_role_menu (role_id, menu_id) VALUES (%s, %s)',
                               # 第二个占位符：菜单/按钮主键。
                               [role_id, menu_id])
