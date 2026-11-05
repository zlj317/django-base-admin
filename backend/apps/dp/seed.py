"""数据权限模块种子：菜单 + 按钮权限。"""
import time

from apps.system.models import SysMenu, SysRole

MENUS = [
    ('系统管理', 'sys_data_permission', '数据权限配置', 'permission', 'dp/permission/index', 'dp:list', 'C', 'Umbrella', 1),
    ('系统管理', 'sys_role_data_permission', '角色数据权限', 'role_perm', 'dp/role_perm/index', 'dp:list', 'C', 'Avatar', 2),
]

BUTTONS = {
    'sys_data_permission': [('查询', 'dp:list'), ('新增', 'dp:create'),
                            ('编辑', 'dp:update'), ('删除', 'dp:delete')],
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


def seed_dp():
    from django.db import connection
    menu_ids = {}
    created_ids = []
    for parent_key, key, name, path, component, perms, mtype, icon, order in MENUS:
        parent_row = SysMenu.objects.filter(menu_name=parent_key, is_deleted=0).first()
        parent_id = parent_row.id if parent_row else 0
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
