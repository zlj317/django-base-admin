"""文件管理种子：菜单 + 按钮权限 + 超级管理员授权（幂等）。"""
import time  # 创建时间

from apps.system.models import SysMenu, SysRole  # 系统菜单与角色模型

# 菜单定义：(父 key, key, 名称, 路由, 组件, 权限, 类型, 图标, 排序)
MENUS = [
    (None, 'file', '附件管理', 'file', '', '', 'M', 'Document', 5),
    ('file', 'file_list', '附件列表', '', 'file/index', 'file:list', 'C', 'Folder', 1),
    ('file', 'file_config', '上传配置', 'config', 'file/config/index', 'file:list', 'C', 'Setting', 2),
    ('file', 'file_recycle', '回收站', 'recycle', 'file/recycle/index', 'file:list', 'C', 'Delete', 3),
]

# 按钮权限
BUTTONS = {
    'file_list': [('查询', 'file:list'), ('上传', 'file:upload'),
                  ('编辑', 'file:update'), ('删除', 'file:delete')],
    'file_config': [('查询', 'file:list'), ('新增', 'file:create'),
                    ('编辑', 'file:update'), ('删除', 'file:delete')],
    'file_recycle': [('查询', 'file:list'), ('恢复', 'file:restore'),
                     ('彻底删除', 'file:hardDelete')],
}


def _ensure_menu(parent_id, name, path, component, perms, mtype, icon, order):
    """按父级+名称幂等创建菜单。"""
    row = SysMenu.objects.filter(parent_id=parent_id, menu_name=name, is_deleted=0).first()
    if row:
        return row
    now = time.strftime('%Y-%m-%d %H:%M:%S')
    return SysMenu.objects.create(
        parent_id=parent_id, menu_name=name, path=path, component=component, perms=perms,
        menu_type=mtype, icon=icon, order_num=order, visible='0', status='0',
        create_by='admin', create_time=now, update_by='admin', update_time=now, is_deleted=0)


def seed_file():
    """写入文件管理菜单与按钮权限并授权。"""
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
