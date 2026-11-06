"""消息中心种子：菜单 + 按钮权限（幂等）。"""
import time  # 创建时间

from apps.system.models import SysMenu, SysRole  # 系统菜单与角色模型

MENUS = [
    (None, 'msg', '消息中心', 'msg', '', '', 'M', 'Bell', 6),
    ('msg', 'msg_template', '消息模板', 'template', 'msg/template/index', 'msg:list', 'C', 'Collection', 1),
    ('msg', 'msg_record', '站内消息', '', 'msg/record/index', 'msg:list', 'C', 'Message', 2),
    ('msg', 'msg_log', '推送记录', 'log', 'msg/log/index', 'msg:list', 'C', 'Tickets', 3),
    ('msg', 'msg_config', '推送渠道', 'config', 'msg/config/index', 'msg:list', 'C', 'Connection', 4),
]

BUTTONS = {
    'msg_template': [('查询', 'msg:list'), ('新增', 'msg:create'),
                     ('编辑', 'msg:update'), ('删除', 'msg:delete')],
    'msg_record': [('查询', 'msg:list'), ('删除', 'msg:delete'),
                   ('全部已读', 'msg:readAll')],
    'msg_log': [('查询', 'msg:list'), ('删除', 'msg:delete')],
    'msg_config': [('查询', 'msg:list'), ('新增', 'msg:create'),
                   ('编辑', 'msg:update'), ('删除', 'msg:delete')],
}


def _ensure_menu(parent_id, name, path, component, perms, mtype, icon, order):
    # 以"父级+名称"作为幂等键，已存在则直接复用
    row = SysMenu.objects.filter(parent_id=parent_id, menu_name=name, is_deleted=0).first()
    if row:
        return row
    now = time.strftime('%Y-%m-%d %H:%M:%S')
    return SysMenu.objects.create(
        parent_id=parent_id, menu_name=name, path=path, component=component, perms=perms,
        menu_type=mtype, icon=icon, order_num=order, visible='0', status='0',
        create_by='admin', create_time=now, update_by='admin', update_time=now, is_deleted=0)


def seed_msg():
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
