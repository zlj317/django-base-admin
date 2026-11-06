"""安全策略种子：菜单 + 按钮权限（幂等）。"""
# 文件：apps/sec/seed.py —— 安全策略模块的菜单与按钮权限初始化脚本
# 用途：在“系统管理”目录下创建“安全策略”“登录尝试”“接口限流”三个页面菜单，
#       并为“安全策略”页面挂上查询/新增/编辑/删除四个按钮权限。
# 对应表：写入 sys_menu（菜单与按钮）、sys_role_menu（角色-菜单授权）；
#         业务表 sys_ip_control / sys_login_attempt / sys_rate_limit 本身不由本脚本初始化。
# 路由前缀：菜单 path 指向前端页面路由（sec、login_attempt、rate_limit），接口前缀为 /api/sec/。
# 调用方：core/management/commands/init_db.py 初始化数据库时调用 seed_sec()。
# 幂等策略：菜单按“父级 + 名称 + 未删除”判重；授权用 INSERT IGNORE，重复执行不会产生重复行。
# 生效范围：这里只创建菜单与权限数据，不写入任何 IP 规则或限流规则；
#           策略是否真正拦截请求以实际代码为准（当前以配置与演示为主）。
import time

# 上一行引入 time：用 strftime 生成与其它种子脚本一致的字符串时间格式。
from apps.system.models import SysMenu, SysRole

# 上一行引入菜单、角色模型：分别用于写入菜单/按钮与取出角色做授权。
# 菜单定义：每行依次为（父级 key、本级 key、菜单名、路由 path、前端组件、权限标识、类型、图标、排序）
# 三条均为 C 类页面菜单，父级 key 都是 'system'，表示挂在“系统管理”目录下
MENUS = [
    # 安全策略页：IP 黑白名单维护，默认落在 sec/ip/index 组件，排序 6
    ('system', 'sec', '安全策略', 'sec', 'sec/ip/index', 'sec:ip:list', 'C', 'Security', 6),
    # 登录尝试页：查看登录成功/失败流水；此处 perms 复用 sec:ip:list（与后端视图的 perm_prefix 不一致，仅为原样记录）
    ('system', 'sec_login_attempt', '登录尝试', 'login_attempt', 'sec/login_attempt/index', 'sec:ip:list', 'C', 'Timer', 7),
    # 接口限流页：维护限流规则，同样复用 sec:ip:list，排序 8
    ('system', 'sec_rate_limit', '接口限流', 'rate_limit', 'sec/rate_limit/index', 'sec:ip:list', 'C', 'Odometer', 8),
]

# 按钮权限定义：key 对应上面的菜单 key，值为（按钮名称、权限标识）列表
BUTTONS = {
    # 仅“安全策略”页配置了按钮；“登录尝试”“接口限流”未单独定义，页面级权限沿用 sec:ip:list
    'sec': [('查询', 'sec:ip:list'), ('新增', 'sec:ip:create'),
            # 编辑与删除：写操作按钮，对应视图集的 update/delete action
            ('编辑', 'sec:ip:update'), ('删除', 'sec:ip:delete')],
}


# 幂等创建单条菜单：已存在直接复用，避免重复执行 init_db 产生重复菜单
def _ensure_menu(parent_id, name, path, component, perms, mtype, icon, order):
    # 以“父级 + 名称 + 未删除”作为幂等键查询现有记录
    row = SysMenu.objects.filter(parent_id=parent_id, menu_name=name, is_deleted=0).first()
    # 命中说明之前已初始化过，直接返回已有行（后续授权也复用它的 ID）
    if row:
        # 复用已有菜单，保证重复执行不产生重复数据
        return row
    # 不存在才新建；统一使用字符串时间格式，与其它模块种子保持一致
    now = time.strftime('%Y-%m-%d %H:%M:%S')
    # 插入新菜单并返回实例；主键由雪花算法字段自动生成
    return SysMenu.objects.create(
        # 基础属性：父级、名称、前端路由、组件路径与权限标识
        parent_id=parent_id, menu_name=name, path=path, component=component, perms=perms,
        # visible/status 均为 '0'，按项目约定表示显示且启用
        menu_type=mtype, icon=icon, order_num=order, visible='0', status='0',
        # 审计字段固定写 admin：种子数据没有真实操作人；is_deleted=0 表示未删除
        create_by='admin', create_time=now, update_by='admin', update_time=now, is_deleted=0)


# 初始化入口：创建三个页面菜单及其按钮，并把本次涉及的菜单/按钮授权给所有有效角色
def seed_sec():
    # 延迟导入数据库连接：仅本函数需要原生游标做批量授权，避免模块加载期依赖数据库配置
    from django.db import connection
    # 先定位“系统管理”父菜单：三个页面都挂在该目录下
    system_menu = SysMenu.objects.filter(menu_name='系统管理', is_deleted=0).first()
    # 找不到父菜单时退化为 0（顶级），保证脚本不中断，但菜单层级会与预期不同
    system_id = system_menu.id if system_menu else 0
    # 记录 key → 菜单 ID，供子菜单回填父级（本模块暂未使用多级子菜单）
    menu_ids = {}
    # 收集本次涉及的所有菜单/按钮 ID，统一授权
    created_ids = []
    # 按定义顺序创建菜单；父菜单先建，子菜单后建
    for parent_key, key, name, path, component, perms, mtype, icon, order in MENUS:
        # 父级为 'system' 时用系统管理目录 ID；其它情况从 menu_ids 取，取不到则退化为 0（顶级）
        parent_id = system_id if parent_key == 'system' else (menu_ids.get(parent_key, 0) if parent_key else 0)
        # 幂等创建菜单本身（重复执行会复用旧记录）
        row = _ensure_menu(parent_id, name, path, component, perms, mtype, icon, order)
        # 缓存本级 ID，供后续可能出现的子菜单使用
        menu_ids[key] = row.id
        # 菜单本身也要加入授权集合
        created_ids.append(row.id)
        # 为该页面创建按钮权限；无定义的 key（登录尝试、接口限流）返回空列表
        for btn_name, btn_perms in BUTTONS.get(key, []):
            # 按钮的父级是所属页面；类型 F 表示按钮权限，无路由、组件与图标，排序 0
            btn = _ensure_menu(row.id, btn_name, '', '', btn_perms, 'F', '', 0)
            # 按钮同样需要授权，加入统一授权集合
            created_ids.append(btn.id)
    # 取出全部未删除角色 ID：种子默认给所有角色授权，避免新菜单对已有角色不可见
    role_ids = list(SysRole.objects.filter(is_deleted=0).values_list('id', flat=True))
    # 用原生游标批量写入关联表，减少逐条 ORM 的往返开销
    with connection.cursor() as cursor:
        # 外层遍历角色，内层遍历菜单/按钮，生成所有“角色-菜单”组合
        for role_id in role_ids:
            for menu_id in created_ids:
                # INSERT IGNORE：重复执行时已存在的授权行被数据库忽略，保证幂等且不报错
                cursor.execute('INSERT IGNORE INTO sys_role_menu (role_id, menu_id) VALUES (%s, %s)',
                               # 参数顺序必须与 SQL 中的占位符一致，避免角色与菜单错配
                               [role_id, menu_id])
