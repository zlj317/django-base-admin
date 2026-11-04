"""日历日程模块种子：菜单 + 按钮权限（幂等）。"""
import time

from apps.system.models import SysMenu, SysRole

MENUS = [
    (None, 'cal', '日历日程', 'cal', '', '', 'M', 'Calendar', 14),
    ('cal', 'cal_schedule', '我的日程', 'schedule', 'cal/schedule/index', 'cal:list', 'C', 'Calendar', 1),
    ('cal', 'cal_reminder', '日程提醒', 'reminder', 'cal/reminder/index', 'cal:list', 'C', 'AlarmClock', 2),
]

BUTTONS = {
    'cal_schedule': [('查询', 'cal:list'), ('新增', 'cal:create'),
                     ('编辑', 'cal:update'), ('删除', 'cal:delete')],
    'cal_reminder': [('查询', 'cal:list'), ('新增', 'cal:create'),
                     ('编辑', 'cal:update'), ('删除', 'cal:delete')],
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


def seed_cal():
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
