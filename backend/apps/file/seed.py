"""文件管理种子：菜单 + 按钮权限 + 超级管理员授权（幂等）。"""
# 部署后执行本文件的 seed_file()，即可把“附件管理”相关菜单补齐；
# “幂等”指重复执行不会产生重复菜单，也不会因唯一键冲突而报错。
import time  # 创建时间：格式化成 MySQL DATETIME 可接受的字符串

from apps.system.models import SysMenu, SysRole  # 系统菜单与角色模型

# 菜单定义：(父 key, key, 名称, 路由, 组件, 权限, 类型, 图标, 排序)
# 父级为 None 表示一级目录；menu_type 中 M=目录、C=菜单（对应前端页面）。
MENUS = [
    (None, 'file', '附件管理', 'file', '', '', 'M', 'Document', 5),  # 一级目录：附件管理
    ('file', 'file_list', '附件列表', '', 'file/index', 'file:list', 'C', 'Folder', 1),  # 附件列表页
    ('file', 'file_config', '上传配置', 'config', 'file/config/index', 'file:list', 'C', 'Setting', 2),  # 上传参数配置页
    ('file', 'file_recycle', '回收站', 'recycle', 'file/recycle/index', 'file:list', 'C', 'Delete', 3),  # 删除文件恢复页
]

# 按钮权限：菜单 key -> [(按钮名称, 权限标识)]
# 按钮以 F（功能点）类型挂在对应菜单下，只控制按钮显隐与后端鉴权，不在导航中展示。
BUTTONS = {
    'file_list': [('查询', 'file:list'), ('上传', 'file:upload'),  # 附件列表：查询/上传
                  ('编辑', 'file:update'), ('删除', 'file:delete')],  # 附件列表：编辑/删除
    'file_config': [('查询', 'file:list'), ('新增', 'file:create'),  # 上传配置：查询/新增
                    ('编辑', 'file:update'), ('删除', 'file:delete')],  # 上传配置：编辑/删除
    'file_recycle': [('查询', 'file:list'), ('恢复', 'file:restore'),  # 回收站：查询/恢复
                     ('彻底删除', 'file:hardDelete')],  # 回收站：物理删除
}


def _ensure_menu(parent_id, name, path, component, perms, mtype, icon, order):
    """按父级+名称幂等创建菜单。"""
    row = SysMenu.objects.filter(parent_id=parent_id, menu_name=name, is_deleted=0).first()  # 只认未删除的同名菜单
    if row:
        return row  # 已存在则直接复用，保留管理员后续改过的配置
    now = time.strftime('%Y-%m-%d %H:%M:%S')  # 统一时间字符串，避免格式差异
    return SysMenu.objects.create(  # 新建菜单记录
        parent_id=parent_id, menu_name=name, path=path, component=component, perms=perms,  # 归属、名称、路由、组件、权限标识
        menu_type=mtype, icon=icon, order_num=order, visible='0', status='0',  # 类型、图标、排序；'0' 表示显示且启用
        create_by='admin', create_time=now, update_by='admin', update_time=now, is_deleted=0)  # 审计字段与逻辑删除标记


def seed_file():
    """写入文件管理菜单与按钮权限并授权。"""
    from django.db import connection  # 延迟导入：只有真正执行种子时才依赖数据库连接
    menu_ids = {}  # key -> 数据库菜单 ID，供子菜单解析父级
    created_ids = []  # 本次涉及的全部菜单/按钮 ID，最后统一授权
    for parent_key, key, name, path, component, perms, mtype, icon, order in MENUS:  # 按定义顺序创建
        parent_id = menu_ids.get(parent_key, 0) if parent_key else 0  # 根节点父 ID 约定为 0
        row = _ensure_menu(parent_id, name, path, component, perms, mtype, icon, order)  # 幂等写入菜单
        menu_ids[key] = row.id  # 记录 ID，供后续子菜单使用
        created_ids.append(row.id)  # 收集待授权菜单
        for btn_name, btn_perms in BUTTONS.get(key, []):  # 遍历该菜单的按钮权限
            btn = _ensure_menu(row.id, btn_name, '', '', btn_perms, 'F', '', 0)  # 按钮 type=F，无需路由与组件
            created_ids.append(btn.id)  # 收集待授权按钮
    role_ids = list(SysRole.objects.filter(is_deleted=0).values_list('id', flat=True))  # 全部未删除角色
    with connection.cursor() as cursor:  # 原生游标执行批量授权
        for role_id in role_ids:  # 逐个角色授权
            for menu_id in created_ids:  # 逐条菜单/按钮授权
                cursor.execute('INSERT IGNORE INTO sys_role_menu (role_id, menu_id) VALUES (%s, %s)',  # 已存在则忽略，保证幂等
                               [role_id, menu_id])  # 参数化传值，避免 SQL 拼接
