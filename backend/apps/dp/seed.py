"""数据权限模块种子：菜单 + 按钮权限。"""
# 文件：backend/apps/dp/seed.py
# 用途：初始化数据权限模块的菜单与按钮权限，并把菜单授权给现有全部角色，保证配置页面可被访问。
# 写入表：sys_menu（菜单/按钮）、sys_role_menu（角色-菜单授权）。
# 数据权限业务表：本文件不写入 sys_data_permission / sys_role_data_permission；
#   规则与角色授权演示数据由 core/management/commands/seed_new_modules.py 的 seed_dp() 写入。
# 路由前缀：菜单指向前端页面 /dp/permission/index 与 /dp/role_perm/index，对应后端 /api/dp/。
# 数据范围生效方式：本文件只创建页面入口与按钮权限（功能权限），不参与数据范围计算；
#   实际数据权限规则在当前代码中仍为配置/预留，未被业务列表查询消费。
# 幂等策略：菜单按"父级 + 名称 + 未删除"判重；授权使用 INSERT IGNORE 忽略已存在关联。
# 生成 'YYYY-MM-DD HH:MM:SS' 格式的创建/更新时间，与手工建表 DATETIME 对齐
import time

# 系统菜单树与角色模型：用于创建菜单并给角色授权
from apps.system.models import SysMenu, SysRole

# 菜单定义：每行依次为（父级菜单名、菜单 key、菜单名、前端路由、前端组件、权限标识、类型、图标、排序）
# 类型 C=菜单页面；父级写"系统管理"表示挂在既有系统管理目录下，而非新建顶级目录
MENUS = [
    # 数据权限配置页：维护 sys_data_permission 中的规则（名称、范围类型、范围值、SQL 条件等）
    ('系统管理', 'sys_data_permission', '数据权限配置', 'permission', 'dp/permission/index', 'dp:list', 'C', 'Umbrella', 1),
    # 角色数据权限页：维护 sys_role_data_permission，把规则分配给角色
    ('系统管理', 'sys_role_data_permission', '角色数据权限', 'role_perm', 'dp/role_perm/index', 'dp:list', 'C', 'Avatar', 2),
]

# 按钮权限定义：key 为页面菜单 key，值为（按钮名称、权限标识）列表
# 仅规则配置页声明按钮；角色授权页未声明，意味着该页只做页面级 dp:list 控制，不细分按钮
BUTTONS = {
    # 规则页：标准增删改查四个按钮，权限标识与后端 perm_prefix='dp' 生成的标识一致
    'sys_data_permission': [('查询', 'dp:list'), ('新增', 'dp:create'),
                            # 编辑与删除：写操作按钮，分别对应 PUT /update 与 DELETE /delete
                            ('编辑', 'dp:update'), ('删除', 'dp:delete')],
}


# 幂等创建单条菜单/按钮：存在则复用，不存在才插入，避免重复执行种子脚本产生重复记录
def _ensure_menu(parent_id, name, path, component, perms, mtype, icon, order):
    # 以"父级 ID + 菜单名 + 未删除"作为幂等键；同名菜单在不同父级下是允许的
    row = SysMenu.objects.filter(parent_id=parent_id, menu_name=name, is_deleted=0).first()
    # 命中已有记录直接返回，后续授权复用其 ID，保证多次执行结果一致
    if row:
        return row
    # 未命中时生成统一格式的当前时间字符串，create_time/update_time 共用
    now = time.strftime('%Y-%m-%d %H:%M:%S')
    # 创建新菜单；id 由 SnowflakeIDField 自动生成，无需手工传入
    return SysMenu.objects.create(
        # 基础字段：父级、名称、路由、前端组件、权限标识，均由 MENUS/BUTTONS 定义传入
        parent_id=parent_id, menu_name=name, path=path, component=component, perms=perms,
        # 展示与启用状态：visible='0'、status='0' 按本项目约定表示显示且启用
        menu_type=mtype, icon=icon, order_num=order, visible='0', status='0',
        # 审计字段：种子数据无真实操作人，统一记为 admin；is_deleted=0 表示未删除
        create_by='admin', create_time=now, update_by='admin', update_time=now, is_deleted=0)


# 初始化入口：由 init_db 初始化数据库时调用，创建两页菜单、规则页按钮并授权给全部有效角色
def seed_dp():
    # 延迟导入 connection：只有批量授权需要原生游标，放函数内可避免模块导入即依赖数据库
    from django.db import connection
    # 记录 key → 菜单 ID；当前文件内未再读取，保留结构便于后续扩展子级菜单
    menu_ids = {}
    # 收集本次涉及的所有菜单/按钮 ID，最后统一给角色授权
    created_ids = []
    # 按定义顺序遍历菜单；先处理父级页面，再处理其按钮，保证 ID 可用
    for parent_key, key, name, path, component, perms, mtype, icon, order in MENUS:
        # 按名称查找父级目录"系统管理"；只取未删除记录，避免挂到已删除目录下
        parent_row = SysMenu.objects.filter(menu_name=parent_key, is_deleted=0).first()
        # 找到父级则用其 ID；未找到则退化为 0（顶级），保证脚本在缺少系统管理目录时也能执行
        parent_id = parent_row.id if parent_row else 0
        # 幂等创建页面菜单本身；已存在时返回原有记录
        row = _ensure_menu(parent_id, name, path, component, perms, mtype, icon, order)
        # 缓存页面 key 对应的菜单 ID（当前仅供潜在扩展使用）
        menu_ids[key] = row.id
        # 页面菜单也加入授权集合，否则角色登录后看不到该菜单
        created_ids.append(row.id)
        # 遍历该页面的按钮定义；未声明按钮的页面 get 返回空列表，不创建任何按钮
        for btn_name, btn_perms in BUTTONS.get(key, []):
            # 按钮挂在页面菜单下，类型 F 表示功能按钮；按钮无路由/组件/图标，排序固定 0
            btn = _ensure_menu(row.id, btn_name, '', '', btn_perms, 'F', '', 0)
            # 按钮权限也要授权给角色，否则前端按钮会被隐藏/后端校验失败
            created_ids.append(btn.id)
    # 取所有未删除角色的 ID；种子默认让所有角色都能访问数据权限配置页
    role_ids = list(SysRole.objects.filter(is_deleted=0).values_list('id', flat=True))
    # 使用原生游标批量授权，避免逐条 ORM create 带来的多次往返开销
    with connection.cursor() as cursor:
        # 外层遍历角色：每个角色都获得本模块的全部菜单/按钮权限
        for role_id in role_ids:
            # 内层遍历本次创建的菜单与按钮 ID
            for menu_id in created_ids:
                # INSERT IGNORE：若角色已拥有该菜单，重复执行不会报唯一键冲突，保证幂等
                cursor.execute('INSERT IGNORE INTO sys_role_menu (role_id, menu_id) VALUES (%s, %s)',
                               # 参数顺序与 SQL 占位符一致；使用参数化写法避免字符串拼接与注入
                               [role_id, menu_id])
