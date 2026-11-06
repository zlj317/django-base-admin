"""数据备份模块种子：菜单 + 按钮权限。"""
# 文件：apps/backup/seed.py —— 数据备份模块的菜单与按钮权限初始化脚本
# 用途：创建“数据备份管理”“备份策略”两个页面菜单，并为备份记录页面挂上增删改查/手动备份按钮。
# 对应表：写入 sys_menu（菜单与按钮）、sys_role_menu（角色-菜单授权）；业务表 backup_record/backup_strategy 不在此写入。
# 路由前缀：菜单 path 对应前端路由 record / strategy，后端接口前缀为 /api/backup/record、/api/backup/strategy。
# 幂等性：菜单按“父级 + 名称 + 未删除”判重，按钮同样判重，授权用 INSERT IGNORE 忽略重复行，可重复执行。
# 时间模块：生成菜单创建/更新时间字符串
import time

# 系统菜单与角色模型：菜单落库到 sys_menu，授权需要读取所有角色
from apps.system.models import SysMenu, SysRole

# 菜单定义：每行依次为（父级菜单名、本级 key、菜单名、路由 path、前端组件、权限标识、类型、图标、排序）
# 父级用“系统管理”名称，运行时按 menu_name 查找其在 sys_menu 中的记录；类型 C=菜单页面
MENUS = [
    # 数据备份管理页：展示备份记录并支持手动备份、下载
    ('系统管理', 'backup_record', '数据备份管理', 'record', 'backup/record/index', 'backup:list', 'C', 'FolderChecked', 1),
    # 备份策略页：维护自动备份的 Cron 与保留天数等配置
    ('系统管理', 'backup_strategy', '备份策略', 'strategy', 'backup/strategy/index', 'backup:list', 'C', 'SetUp', 2),
]

# 按钮权限定义：key 对应上面菜单的 key，值为（按钮名称、权限标识）列表
BUTTONS = {
    # 备份记录页：查询/新增/编辑/删除 + 手动备份专用权限
    'backup_record': [('查询', 'backup:list'), ('新增', 'backup:create'),
                      # 编辑与删除：标准写操作按钮
                      ('编辑', 'backup:update'), ('删除', 'backup:delete'),
                      # 手动备份：对应视图集 manual_backup 自定义动作的权限点
                      ('手动备份', 'backup:manual')],
    # 说明：策略页未配置按钮权限，前端只能进入页面；如需增删改按钮应在此补充 backup_strategy 配置
}


# 幂等创建单条菜单：已存在则复用，避免重复执行 init_db 生成重复菜单
def _ensure_menu(parent_id, name, path, component, perms, mtype, icon, order):
    # 以“父级 + 名称 + 未删除”作为判重键，命中说明之前已初始化过
    row = SysMenu.objects.filter(parent_id=parent_id, menu_name=name, is_deleted=0).first()
    # 命中则直接返回已有记录，后续按钮授权复用它的 ID
    if row:
        return row
    # 不存在才新建；时间统一用字符串格式，与其它模块种子保持一致
    now = time.strftime('%Y-%m-%d %H:%M:%S')
    # 插入新菜单并返回实例；雪花 ID 由模型字段自动生成
    return SysMenu.objects.create(
        # 基础属性：父级、名称、路由、前端组件、权限标识
        parent_id=parent_id, menu_name=name, path=path, component=component, perms=perms,
        # menu_type=C/F 区分页面与按钮；visible/status 为 '0' 表示显示且启用
        menu_type=mtype, icon=icon, order_num=order, visible='0', status='0',
        # 审计字段固定为 admin，种子数据无真实操作人
        create_by='admin', create_time=now, update_by='admin', update_time=now, is_deleted=0)


# 初始化入口：由 init_db 或 seed_new_modules 命令调用，创建菜单、按钮并授权给所有有效角色
def seed_backup():
    # 延迟导入数据库连接：仅本函数需要原生游标做批量授权，避免顶层依赖
    from django.db import connection
    # 记录 key → 菜单 ID，供后续查找（当前仅父级按名称查找，保留该结构以便扩展子菜单）
    menu_ids = {}
    # 收集本次涉及的所有菜单/按钮 ID，最后统一授权
    created_ids = []
    # 按定义顺序创建菜单，先创建页面菜单，再为其挂按钮
    for parent_key, key, name, path, component, perms, mtype, icon, order in MENUS:
        # 按父级菜单名查出所属目录（如“系统管理”）；查不到时退化为顶级菜单 parent_id=0
        parent_row = SysMenu.objects.filter(menu_name=parent_key, is_deleted=0).first()
        # 父级存在取其 ID，否则挂到根级，保证菜单至少可见
        parent_id = parent_row.id if parent_row else 0
        # 幂等创建页面菜单（已存在则复用）
        row = _ensure_menu(parent_id, name, path, component, perms, mtype, icon, order)
        # 缓存本级 ID，便于后续扩展子级或调试
        menu_ids[key] = row.id
        # 页面菜单本身也要加入授权集合
        created_ids.append(row.id)
        # 为该页面创建按钮权限；无定义的 key 返回空列表
        for btn_name, btn_perms in BUTTONS.get(key, []):
            # 按钮父级为所属页面；类型 F 表示按钮权限，无路由与组件
            btn = _ensure_menu(row.id, btn_name, '', '', btn_perms, 'F', '', 0)
            # 按钮同样需要授权，加入统一集合
            created_ids.append(btn.id)
    # 取出全部未删除角色 ID，种子默认给所有角色授权，保证新菜单开箱可用
    role_ids = list(SysRole.objects.filter(is_deleted=0).values_list('id', flat=True))
    # 使用原生游标批量写入关联表，避免逐条 ORM 调用带来的开销
    with connection.cursor() as cursor:
        # 外层遍历角色
        for role_id in role_ids:
            # 内层遍历本次创建的菜单与按钮
            for menu_id in created_ids:
                # INSERT IGNORE 保证重复执行时已有授权行被忽略，既不报错也不产生重复数据
                cursor.execute('INSERT IGNORE INTO sys_role_menu (role_id, menu_id) VALUES (%s, %s)',
                               # 参数顺序必须与 SQL 占位符一致
                               [role_id, menu_id])
