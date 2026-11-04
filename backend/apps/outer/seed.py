"""外部对接种子：菜单 + 按钮权限（幂等）。"""
import time  # 创建时间

from apps.system.models import SysMenu, SysRole  # 系统菜单与角色模型

MENUS = [
    (None, 'outer', '外部对接', 'outer', '', '', 'M', 'Link', 12),
    ('outer', 'outer_api', '外部接口', 'api', 'outer/api/index', 'outer:list', 'C', 'Link', 1),
    ('outer', 'outer_log', '请求日志', 'log', 'outer/log/index', 'outer:list', 'C', 'Tickets', 2),
    ('outer', 'outer_sync', '同步任务', 'sync', 'outer/sync/index', 'outer:list', 'C', 'Refresh', 3),
]

BUTTONS = {
    'outer_api': [('查询', 'outer:list'), ('新增', 'outer:create'),
                  ('编辑', 'outer:update'), ('删除', 'outer:delete'),
                  ('测试', 'outer:test'), ('调用', 'outer:call')],
    'outer_log': [('查询', 'outer:list'), ('删除', 'outer:delete')],
    'outer_sync': [('查询', 'outer:list'), ('新增', 'outer:create'),
                   ('编辑', 'outer:update'), ('删除', 'outer:delete'),
                   ('手动执行', 'outer:runOnce')],
}


def _ensure_menu(parent_id, name, path, component, perms, mtype, icon, order):
    row = SysMenu.objects.filter(parent_id=parent_id, menu_name=name, is_deleted=0).first()
    if row:
        return row
    now = time.strftime('%Y-%m-%d %H:%M:%S')
    return SysMenu.objects.create(
        parent_id=parent_id, menu_name=name, path=path, component=component, perms=perms,
        menu_type=mtype, icon=icon, order_num=order, visible='0', status='0',
        create_by='admin', create_time=now, update_by='admin', update_time=now, is_deleted=0)


def seed_outer():
    from django.db import connection
    menu_ids = {}
    created_ids = []
    for parent_key, key, name, path, component, perms, mtype, icon, order in MENUS:
        parent_id = menu_ids.get(parent_key, 0) if parent_key else 0
        row = _ensure_menu(parent_id, name, path, component, perms, mtype, icon, order)
        menu_ids[key] = row.id
        created_ids.append(row.id)
        for btn_name, btn_perms in BUTTONS.get(key, []):
            btn = _ensure_menu(row.id, btn_name, '', '', btn_perms, 'F', '', 0)
            created_ids.append(btn.id)
    role_ids = list(SysRole.objects.filter(is_deleted=0).values_list('id', flat=True))
    with connection.cursor() as cursor:
        for role_id in role_ids:
            for menu_id in created_ids:
                cursor.execute('INSERT IGNORE INTO sys_role_menu (role_id, menu_id) VALUES (%s, %s)',
                               [role_id, menu_id])
