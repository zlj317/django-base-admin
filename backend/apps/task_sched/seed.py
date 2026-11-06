"""定时任务种子：菜单 + 按钮权限（幂等）。"""
# 本文件在系统初始化/升级时被调用，负责把“定时任务”相关菜单写进 sys_menu 并授权给已有角色。
# 幂等的含义：重复执行不会产生重复菜单，也不会报错，便于每次部署后安全地补齐菜单数据。
import time  # 创建时间：手工拼成 MySQL DATETIME 可接受的字符串

from apps.system.models import SysMenu, SysRole  # 系统菜单与角色模型

# 菜单定义：(父菜单 key, 菜单 key, 名称, 路由 path, 前端组件, 权限标识, 类型 M 目录/C 菜单, 图标, 排序)
# 顺序即写入顺序；父菜单 key 依赖本列表前面已处理的项，因此顺序不能随意调整。
MENUS = [
    # 一级目录“定时任务”，父级为 None 表示顶级菜单，menu_type=M（目录，不对应具体页面）
    (None, 'task', '定时任务', 'task', '', '', 'M', 'Timer', 9),
    # 二级菜单“任务信息”：对应 crontab 任务的新增/编辑/启停页面
    ('task', 'task_info', '任务信息', '', 'task/info/index', 'task:list', 'C', 'Setting', 1),
    # 二级菜单“任务日志”：查看每次调度的成功/失败与耗时
    ('task', 'task_log', '任务日志', 'log', 'task/log/index', 'task:list', 'C', 'Tickets', 2),
]

# 按钮权限：菜单 key -> [(按钮名称, 权限标识)]
# 按钮在菜单树中作为 F 类型（功能点）子节点存在，只控制前端按钮显隐与后端接口鉴权，不在导航中展示。
BUTTONS = {
    # 任务信息支持增删改查 + 手动执行一次
    'task_info': [('查询', 'task:list'), ('新增', 'task:create'),
                  ('编辑', 'task:update'), ('删除', 'task:delete'),
                  ('手动执行', 'task:runOnce')],
    # 日志页只允许查询与删除（日志由调度器写入，不提供人工新增/编辑）
    'task_log': [('查询', 'task:list'), ('删除', 'task:delete')],
}


def _ensure_menu(parent_id, name, path, component, perms, mtype, icon, order):
    # 按“父级 + 名称”判断菜单是否已存在（软删除的菜单不算存在），已存在直接复用，保证幂等
    row = SysMenu.objects.filter(parent_id=parent_id, menu_name=name, is_deleted=0).first()
    if row:
        # 已存在：返回原记录，不覆盖管理员后来改过的名称/排序等配置
        return row
    # 统一用字符串时间写入，避免时区/格式差异导致数据库 DATETIME 解析失败
    now = time.strftime('%Y-%m-%d %H:%M:%S')
    # 新建菜单：visible='0' 表示显示，status='0' 表示启用；'F' 类型按钮的 path/component 留空
    return SysMenu.objects.create(
        parent_id=parent_id, menu_name=name, path=path, component=component, perms=perms,
        menu_type=mtype, icon=icon, order_num=order, visible='0', status='0',
        create_by='admin', create_time=now, update_by='admin', update_time=now, is_deleted=0)


def seed_task_sched():
    # 延迟导入数据库连接：只在真正执行种子时依赖 Django 配置，避免模块被提前导入时报错
    from django.db import connection
    menu_ids = {}  # key -> 数据库菜单 ID，供子菜单解析父级 ID
    created_ids = []  # 本次涉及的菜单/按钮 ID，最后统一授权给所有角色
    # 按 MENUS 顺序创建：父菜单一定排在子菜单之前，因此可以从 menu_ids 取到 parent_id
    for parent_key, key, name, path, component, perms, mtype, icon, order in MENUS:
        # 顶级菜单 parent_key 为 None，父 ID 用 0（项目约定根节点 parent_id=0）
        parent_id = menu_ids.get(parent_key, 0) if parent_key else 0
        row = _ensure_menu(parent_id, name, path, component, perms, mtype, icon, order)
        menu_ids[key] = row.id
        created_ids.append(row.id)
        # 为该菜单创建按钮权限节点；没有配置按钮的菜单跳过
        for btn_name, btn_perms in BUTTONS.get(key, []):
            # 按钮挂在当前菜单下（parent_id=row.id），类型固定 F，path/component/排序留空
            btn = _ensure_menu(row.id, btn_name, '', '', btn_perms, 'F', '', 0)
            created_ids.append(btn.id)
    # 授权范围：所有未删除角色。工作流任务属于基础能力，业务账号也需要看到任务日志
    role_ids = list(SysRole.objects.filter(is_deleted=0).values_list('id', flat=True))
    with connection.cursor() as cursor:
        # 角色-菜单关系表用 INSERT IGNORE 避免重复授权报唯一键冲突（幂等的关键）
        for role_id in role_ids:
            for menu_id in created_ids:
                cursor.execute('INSERT IGNORE INTO sys_role_menu (role_id, menu_id) VALUES (%s, %s)',
                               [role_id, menu_id])
