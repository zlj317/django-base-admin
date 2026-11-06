"""报表管理种子：菜单 + 按钮权限（幂等）。"""
# 模块：apps/report/seed.py —— 报表模块的菜单与按钮权限初始化脚本
# 用途：创建"报表管理"目录及其四个页面菜单，并给每个页面挂上增删改查/生成按钮权限。
# 数据表：写入 sys_menu（菜单与按钮）、sys_role_menu（角色-菜单授权）。
# 调用方：core/management/commands/init_db.py 初始化数据库时调用 seed_report()。
# 幂等策略：菜单按"父级 + 名称 + 未删除"判重，授权用 INSERT IGNORE 忽略重复行。
import time  # 创建时间

from apps.system.models import SysMenu, SysRole  # 系统菜单与角色模型

# 菜单定义：每行依次为（父级 key、本级 key、菜单名、路由 path、前端组件、权限标识、类型、图标、排序）
# 类型 M=目录、C=菜单页面；父级 key 为 None 表示顶级目录
MENUS = [
    # 顶级目录：报表管理，作为四个子菜单的父节点
    (None, 'rp', '报表管理', 'rp', '', '', 'M', 'Histogram', 10),
    # 分类页：维护报表分类
    ('rp', 'rp_category', '报表分类', 'category', 'rp/category/index', 'rp:list', 'C', 'Collection', 1),
    # 数据源页：维护报表取数来源
    ('rp', 'rp_datasource', '数据源', 'datasource', 'rp/datasource/index', 'rp:list', 'C', 'Connection', 2),
    # 模板页：报表配置与预览入口
    ('rp', 'rp_template', '报表模板', 'template', 'rp/template/index', 'rp:list', 'C', 'Document', 3),
    # 生成记录页：查看历史生成结果
    ('rp', 'rp_record', '生成记录', 'gen', 'rp/gen/index', 'rp:list', 'C', 'Tickets', 4),
    # 四个子菜单共用 rp:list 权限标识，拥有该权限即可进入各页面
]

# 按钮权限定义：key 对应上面的菜单 key，值为（按钮名称、权限标识）列表
BUTTONS = {
    # 分类：标准增删改查
    'rp_category': [('查询', 'rp:list'), ('新增', 'rp:create'),
                     # 编辑与删除：写操作按钮
                     ('编辑', 'rp:update'), ('删除', 'rp:delete')],
    # 数据源：标准增删改查
    'rp_datasource': [('查询', 'rp:list'), ('新增', 'rp:create'),
                      # 编辑与删除：写操作按钮
                      ('编辑', 'rp:update'), ('删除', 'rp:delete')],
    # 模板：额外提供"生成"按钮，对应视图集的 generate 动作
    'rp_template': [('查询', 'rp:list'), ('新增', 'rp:create'),
                    # 编辑与删除：写操作按钮
                    ('编辑', 'rp:update'), ('删除', 'rp:delete'),
                    # 生成：手工触发一次报表导出并写入生成记录
                    ('生成', 'rp:generate')],
    # 记录：只读查询与清理，不提供新增/编辑
    'rp_record': [('查询', 'rp:list'), ('删除', 'rp:delete')],
    # 按钮权限按页面 key 分组，未列出的页面不生成按钮
}


# 幂等创建单条菜单：已存在直接复用，避免重复执行 init_db 产生重复菜单
def _ensure_menu(parent_id, name, path, component, perms, mtype, icon, order):
    # 以"父级 + 名称 + 未删除"作为幂等键查询现有记录
    row = SysMenu.objects.filter(parent_id=parent_id, menu_name=name, is_deleted=0).first()
    # 命中说明之前已初始化过，直接返回已有行（后续授权也复用它的 ID）
    if row:
        # 复用已有菜单，保证重复执行不产生重复数据
        return row
    # 不存在才新建；统一使用字符串时间格式，与其它模块种子保持一致
    now = time.strftime('%Y-%m-%d %H:%M:%S')
    # 插入新菜单，返回实例；其 id 由雪花算法字段生成
    return SysMenu.objects.create(
        # 基础属性：父级、名称、路由、前端组件与权限标识
        parent_id=parent_id, menu_name=name, path=path, component=component, perms=perms,
        # visible/status 为 '0' 表示显示且启用
        menu_type=mtype, icon=icon, order_num=order, visible='0', status='0',
        # 审计字段固定为 admin，种子数据无真实操作人
        create_by='admin', create_time=now, update_by='admin', update_time=now, is_deleted=0)


# 初始化入口：创建菜单、按钮并授权给所有有效角色
def seed_report():
    # 延迟导入数据库连接：仅本函数需要原生游标做批量授权
    from django.db import connection
    # 记录 key → 菜单 ID，供子菜单回填父级
    menu_ids = {}
    # 收集本次涉及的所有菜单/按钮 ID，统一授权
    created_ids = []
    # 按定义顺序创建，保证父菜单先于子菜单
    for parent_key, key, name, path, component, perms, mtype, icon, order in MENUS:
        # 顶级菜单父级为 0；子菜单从 menu_ids 取父级 ID（此时父级已创建）
        parent_id = menu_ids.get(parent_key, 0) if parent_key else 0
        # 幂等创建菜单本身
        row = _ensure_menu(parent_id, name, path, component, perms, mtype, icon, order)
        # 缓存本级 ID 供后续子级使用
        menu_ids[key] = row.id
        # 菜单本身也要加入授权集合
        created_ids.append(row.id)
        # 为该页面创建按钮权限；无定义的 key 返回空列表
        for btn_name, btn_perms in BUTTONS.get(key, []):
            # 按钮的父级是所属页面；类型 F 表示按钮权限，无路由与组件
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
