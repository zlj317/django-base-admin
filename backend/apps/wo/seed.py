"""工单模块种子：菜单 + 按钮权限（幂等）。"""
# 文件：apps/wo/seed.py —— 工单模块的菜单与按钮权限初始化脚本
# 用途：创建"工单管理"目录及其三个页面菜单（工单类型、工单列表、我的工单），并为页面挂上增删改查与流转按钮权限。
# 对应表：写入 sys_menu（菜单与按钮）、sys_role_menu（角色-菜单授权）；业务表 work_order/work_order_type/work_order_log 不在此初始化。
# 路由前缀：菜单 path 与前端路由对应，接口侧由 /api/wo/ 提供（见 apps/wo/urls.py）。
# 调用方：core/management/commands/init_db.py 初始化数据库时调用 seed_wo()。
# 幂等策略：菜单按"父级 + 名称 + 未删除"判重，授权使用 INSERT IGNORE 忽略重复行，可重复执行。
import time

# SysMenu 负责菜单/按钮落库与判重，SysRole 用于查询需要授权的角色集合
from apps.system.models import SysMenu, SysRole

# 菜单定义：每行依次为（父级 key、本级 key、菜单名、路由 path、前端组件、权限标识、类型、图标、排序）
# 类型 M=目录、C=菜单页面；父级 key 为 None 表示顶级目录，子菜单通过 menu_ids 回填父级 ID
MENUS = [
    # 顶级目录：工单管理，作为三个子页面的父节点；排序 13 决定其在左侧菜单中的位置
    (None, 'wo', '工单管理', 'wo', '', '', 'M', 'Tickets', 13),
    # 工单类型页：维护工单分类，前端组件 wo/type/index
    ('wo', 'wo_type', '工单类型', 'type', 'wo/type/index', 'wo:list', 'C', 'Tickets', 1),
    # 工单列表页：全部工单的查询与流转入口
    ('wo', 'wo_order', '工单列表', 'order', 'wo/order/index', 'wo:list', 'C', 'Tickets', 2),
    # 我的工单页：按 creator_id/assignee_id 过滤的个性化视图
    ('wo', 'wo_mine', '我的工单', 'mine', 'wo/mine/index', 'wo:list', 'C', 'Tickets', 3),
# 菜单定义结束：顺序即创建顺序，父级目录必须排在子页面之前
]

# 按钮权限定义：key 对应上面的菜单 key，值为（按钮名称、权限标识）列表
BUTTONS = {
    # 工单类型：标准增删改查四个按钮
    'wo_type': [('查询', 'wo:list'), ('新增', 'wo:create'),
                # 编辑与删除：写操作按钮，对应 update/delete 接口
                ('编辑', 'wo:update'), ('删除', 'wo:delete')],
    # 工单列表：增删改查之外，追加指派/解决/关闭三个流转按钮
    'wo_order': [('查询', 'wo:list'), ('新增', 'wo:create'),
                 # 编辑与删除：维护工单基础信息
                 ('编辑', 'wo:update'), ('删除', 'wo:delete'),
                 # 指派：对应 PUT /api/wo/order/assign/<pk>，指定处理人
                 ('指派', 'wo:assign'), ('解决', 'wo:solve'), ('关闭', 'wo:close')],
    # 我的工单：只读页面，仅保留查询按钮
    'wo_mine': [('查询', 'wo:list')],
# 按钮权限定义结束：未列出的页面不会生成按钮，只保留页面本身的访问权限
}


# 幂等创建单条菜单：已存在直接复用，避免重复执行 init_db 产生重复菜单或重复授权
def _ensure_menu(parent_id, name, path, component, perms, mtype, icon, order):
    # 以"父级 + 名称 + 未删除"作为幂等键查询现有记录；逻辑删除的旧菜单不算命中，会重新创建
    row = SysMenu.objects.filter(parent_id=parent_id, menu_name=name, is_deleted=0).first()
    # 命中说明此前已初始化过，直接返回已有行，后续授权复用它的 ID
    if row:
        # 复用已有菜单，保证重复执行不产生重复数据
        return row
    # 统一时间字符串，与其它模块种子的时间格式保持一致
    now = time.strftime('%Y-%m-%d %H:%M:%S')
    # 不存在才新建：parent_id 决定层级，perms 为按钮/页面权限标识，mtype 区分目录/页面/按钮
    return SysMenu.objects.create(
        # 层级与展示属性：父级、名称、前端路由、组件路径、权限标识
        parent_id=parent_id, menu_name=name, path=path, component=component, perms=perms,
        # 类型与外观：menu_type（M/C/F）、图标、排序；visible/status 为 '0' 表示显示且启用
        menu_type=mtype, icon=icon, order_num=order, visible='0', status='0',
        # 审计字段固定为 admin（种子数据无真实操作人），初始未删除
        create_by='admin', create_time=now, update_by='admin', update_time=now, is_deleted=0)


# 初始化入口：创建工单菜单、按钮并把它们授权给全部有效角色
def seed_wo():
    # 延迟导入数据库连接：仅本函数需要原生游标做批量授权，避免模块加载期依赖数据库
    from django.db import connection
    # 记录 菜单 key → 菜单 ID，供子菜单回填 parent_id
    menu_ids = {}
    # 收集本次涉及的全部菜单与按钮 ID，最后统一授权
    created_ids = []
    # 按定义顺序遍历，保证父级目录先于子页面创建
    for parent_key, key, name, path, component, perms, mtype, icon, order in MENUS:
        # 顶级菜单父级为 0；子菜单从 menu_ids 取父级 ID（此时父级已创建完成）
        parent_id = menu_ids.get(parent_key, 0) if parent_key else 0
        # 幂等创建菜单本身（已存在则复用）
        row = _ensure_menu(parent_id, name, path, component, perms, mtype, icon, order)
        # 缓存本级 ID，供后续子级回填父级
        menu_ids[key] = row.id
        # 菜单本身也要加入授权集合
        created_ids.append(row.id)
        # 为该页面创建按钮权限；未在 BUTTONS 中定义的 key 返回空列表直接跳过
        for btn_name, btn_perms in BUTTONS.get(key, []):
            # 按钮的父级是所属页面；类型 F 表示按钮权限，无独立路由与组件
            btn = _ensure_menu(row.id, btn_name, '', '', btn_perms, 'F', '', 0)
            # 按钮权限同样需要授权，加入统一集合
            created_ids.append(btn.id)
    # 取出全部未删除角色 ID：种子默认给所有角色授予工单菜单，便于演示与回归
    role_ids = list(SysRole.objects.filter(is_deleted=0).values_list('id', flat=True))
    # 用原生游标批量写入关联表，避免逐条 ORM 调用的开销
    with connection.cursor() as cursor:
        # 外层遍历角色
        for role_id in role_ids:
            # 内层遍历本次创建的菜单与按钮
            for menu_id in created_ids:
                # INSERT IGNORE：重复执行时已存在的授权行被忽略，保证幂等且不报错
                cursor.execute('INSERT IGNORE INTO sys_role_menu (role_id, menu_id) VALUES (%s, %s)',
                               # 参数顺序必须与 SQL 占位符一致
                               [role_id, menu_id])
