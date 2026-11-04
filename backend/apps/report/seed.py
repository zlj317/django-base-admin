"""报表管理种子：菜单 + 按钮权限（幂等）。"""
import time  # 创建时间

from apps.system.models import SysMenu, SysRole  # 系统菜单与角色模型

MENUS = [
    (None, 'rp', '报表管理', 'rp', '', '', 'M', 'Histogram', 10),
    ('rp', 'rp_category', '报表分类', 'category', 'rp/category/index', 'rp:list', 'C', 'Collection', 1),
    ('rp', 'rp_datasource', '数据源', 'datasource', 'rp/datasource/index', 'rp:list', 'C', 'Connection', 2),
    ('rp', 'rp_template', '报表模板', 'template', 'rp/template/index', 'rp:list', 'C', 'Document', 3),
    ('rp', 'rp_record', '生成记录', 'gen', 'rp/gen/index', 'rp:list', 'C', 'Tickets', 4),
]

BUTTONS = {
    'rp_category': [('查询', 'rp:list'), ('新增', 'rp:create'),
                     ('编辑', 'rp:update'), ('删除', 'rp:delete')],
    'rp_datasource': [('查询', 'rp:list'), ('新增', 'rp:create'),
                      ('编辑', 'rp:update'), ('删除', 'rp:delete')],
    'rp_template': [('查询', 'rp:list'), ('新增', 'rp:create'),
                    ('编辑', 'rp:update'), ('删除', 'rp:delete'),
                    ('生成', 'rp:generate')],
    'rp_record': [('查询', 'rp:list'), ('删除', 'rp:delete')],
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


def seed_report():
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
