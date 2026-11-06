"""大屏BI种子：菜单 + 按钮权限（幂等）。"""
# 文件：apps/bi/seed.py —— 大屏 BI 模块的菜单与按钮权限初始化脚本
# 用途：幂等创建“报表大屏”菜单树与按钮权限，并给现有角色授权，供部署/初始化时调用。
# 数据表：写 sys_menu（菜单）、sys_role_menu（角色-菜单关联）；读 sys_role。
# 路由前缀：本文件不注册路由；权限点对应 /api/bi/screen、/api/bi/dataset、/api/bi/visit。
# 说明：_ensure_menu 先查后建，重复执行不会产生重复菜单，授权用 INSERT IGNORE 保证幂等。
import time  # 创建时间

from apps.system.models import SysMenu, SysRole  # 系统菜单与角色模型

# 菜单定义：(父级 key, 自身 key, 名称, 路由 path, 组件路径, 权限标识, 类型, 图标, 排序)
# 第一条是顶级目录 bi，其余三条是挂在其下的大屏/数据集/访问记录菜单（C 表示菜单节点）
MENUS = [
    # 顶级目录：报表大屏，挂在根节点（parent_key 为 None）
    (None, 'bi', '报表大屏', 'bi', '', '', 'M', 'Monitor', 11),
    # 大屏管理菜单：挂在 bi 目录下，权限点 bi:list
    ('bi', 'bi_screen', '大屏管理', '', 'bi/screen/index', 'bi:list', 'C', 'Monitor', 1),
    # 数据集管理菜单：独立路由 dataset，权限点 bi:list
    ('bi', 'bi_dataset', '数据集管理', 'dataset', 'bi/dataset/index', 'bi:list', 'C', 'DataLine', 2),
    # 访问记录菜单：独立路由 visit，权限点 bi:list
    ('bi', 'bi_visit', '访问记录', 'visit', 'bi/visit/index', 'bi:list', 'C', 'Tickets', 3),
]

# 按钮定义：菜单 key → [(按钮名称, 权限标识)]，权限标识需与 ViewSet.perm_prefix 拼出的权限点一致
BUTTONS = {
    # 大屏管理支持增删改查与发布
    'bi_screen': [('查询', 'bi:list'), ('新增', 'bi:create'),
                  # 编辑与删除权限
                  ('编辑', 'bi:update'), ('删除', 'bi:delete'),
                  # 发布权限，对应 BiScreenViewSet.publish 动作
                  ('发布', 'bi:publish')],
    # 数据集管理支持增删改查
    'bi_dataset': [('查询', 'bi:list'), ('新增', 'bi:create'),
                   # 编辑与删除权限
                   ('编辑', 'bi:update'), ('删除', 'bi:delete')],
    # 访问记录只支持查询与删除
    'bi_visit': [('查询', 'bi:list'), ('删除', 'bi:delete')],
}


# 幂等创建单条菜单：已存在（同父级、同名、未删除）则直接复用，否则新建
def _ensure_menu(parent_id, name, path, component, perms, mtype, icon, order):
    # 先按父级 + 名称 + 未删除条件查找，保证重复执行不产生重复菜单
    row = SysMenu.objects.filter(parent_id=parent_id, menu_name=name, is_deleted=0).first()
    # 命中已有菜单即返回，不做任何写入
    if row:
        # 直接复用已有记录，不再重复创建
        return row
    # 统一时间格式，与库中其他记录保持一致
    now = time.strftime('%Y-%m-%d %H:%M:%S')
    # 新建菜单记录：visible/status 固定为 '0'（显示、正常），创建/更新人固定 admin
    return SysMenu.objects.create(
        # 基础字段：父级、名称、路由路径、组件路径与权限标识
        parent_id=parent_id, menu_name=name, path=path, component=component, perms=perms,
        # 菜单类型、图标、排序与显示/启用状态
        menu_type=mtype, icon=icon, order_num=order, visible='0', status='0',
        # 审计字段：创建/更新人固定 admin，并标记为未删除
        create_by='admin', create_time=now, update_by='admin', update_time=now, is_deleted=0)


# 种子入口：依次创建菜单 → 创建按钮 → 给所有未删除角色授权
def seed_bi():
    # 延迟导入 connection，避免模块加载阶段就要求数据库连接可用
    from django.db import connection
    # 记录 key → 菜单 ID 的映射，供子菜单定位父级
    menu_ids = {}
    # 本次涉及的全部菜单/按钮 ID，最后统一用于授权
    created_ids = []
    # 按定义顺序创建菜单：父级必须先于子级处理
    for parent_key, key, name, path, component, perms, mtype, icon, order in MENUS:
        # 顶级菜单 parent_id 取 0；子菜单从 menu_ids 取已建好的父级 ID
        parent_id = menu_ids.get(parent_key, 0) if parent_key else 0
        # 幂等创建（或复用）当前菜单
        row = _ensure_menu(parent_id, name, path, component, perms, mtype, icon, order)
        # 缓存当前菜单 ID 供后续子菜单使用
        menu_ids[key] = row.id
        # 收集菜单 ID 用于授权
        created_ids.append(row.id)
        # 遍历该菜单下的按钮权限定义
        for btn_name, btn_perms in BUTTONS.get(key, []):
            # 按钮作为子节点挂在当前菜单下（类型 F，无路由与组件）
            btn = _ensure_menu(row.id, btn_name, '', '', btn_perms, 'F', '', 0)
            # 按钮 ID 一并纳入授权范围
            created_ids.append(btn.id)
    # 取所有未逻辑删除的角色 ID，种子脚本默认给全部角色授权
    role_ids = list(SysRole.objects.filter(is_deleted=0).values_list('id', flat=True))
    # 用原生游标执行 INSERT IGNORE，MySQL 下可重复执行而不报主键冲突
    with connection.cursor() as cursor:
        # 角色 × 菜单 双重循环，逐条建立授权关系
        for role_id in role_ids:
            # 遍历本次创建/复用的全部菜单与按钮
            for menu_id in created_ids:
                # INSERT IGNORE：关联已存在时静默跳过，保证幂等
                cursor.execute('INSERT IGNORE INTO sys_role_menu (role_id, menu_id) VALUES (%s, %s)',
                               # 参数依次为角色 ID 与菜单 ID
                               [role_id, menu_id])
