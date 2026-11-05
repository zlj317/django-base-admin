"""3D 可视化模块种子：菜单 + 按钮权限（幂等，可重复执行）。"""
import time  # 生成创建/更新时间字符串

from apps.system.models import SysMenu, SysRole  # 复用系统菜单与角色模型

# 菜单定义：(父 key, key, 名称, 路由, 组件, 权限, 类型, 图标, 排序, 是否可见)
MENUS = [
    (None, 'scene3d', '3D可视化', 'scene3d', '', '', 'M', 'DataBoard', 16, '0'),  # 顶级目录
    ('scene3d', 'scene3d_category', '场景分类', 'category', 'scene3d/category/index', 'scene3d:category:list', 'C', 'Folder', 1, '0'),
    ('scene3d', 'scene3d_scene', '3D场景管理', 'scene', 'scene3d/scene/index', 'scene3d:scene:list', 'C', 'Monitor', 2, '0'),
    ('scene3d', 'scene3d_editor', '场景编辑器', 'editor/:id', 'scene3d/editor/index', 'scene3d:scene:update', 'C', 'Edit', 3, '1'),  # 隐藏菜单，从列表进入
    ('scene3d', 'scene3d_model', '模型资源', 'model', 'scene3d/model/index', 'scene3d:model:list', 'C', 'Box', 4, '0'),
    ('scene3d', 'scene3d_binding', '数据绑定', 'binding', 'scene3d/binding/index', 'scene3d:binding:list', 'C', 'Connection', 5, '0'),
    ('scene3d', 'scene3d_alarm', '告警联动', 'alarm', 'scene3d/alarm/index', 'scene3d:alarm:list', 'C', 'Bell', 6, '0'),
    ('scene3d', 'scene3d_route', '巡检路线', 'route', 'scene3d/route/index', 'scene3d:route:list', 'C', 'Guide', 7, '0'),
    ('scene3d', 'scene3d_screen', '场景发布', 'screen', 'scene3d/screen/index', 'scene3d:screen:view', 'C', 'DataLine', 8, '0'),
]

# 按钮权限：与后端 @perm_map 中的权限标识逐一对齐
BUTTONS = {
    'scene3d_category': [('查询', 'scene3d:category:list'), ('新增', 'scene3d:category:create'),
                         ('编辑', 'scene3d:category:update'), ('删除', 'scene3d:category:delete')],
    'scene3d_scene': [('查询', 'scene3d:scene:list'), ('新增', 'scene3d:scene:create'), ('编辑', 'scene3d:scene:update'),
                      ('删除', 'scene3d:scene:delete'), ('发布', 'scene3d:scene:publish'),
                      ('版本回滚', 'scene3d:scene:version'), ('生成分享', 'scene3d:scene:share'),
                      ('访问授权', 'scene3d:permission:list'), ('新增授权', 'scene3d:permission:create'),
                      ('删除授权', 'scene3d:permission:delete')],
    'scene3d_model': [('查询', 'scene3d:model:list'), ('上传', 'scene3d:model:upload'),
                      ('编辑', 'scene3d:model:update'), ('删除', 'scene3d:model:delete')],
    'scene3d_binding': [('查询', 'scene3d:binding:list'), ('新增', 'scene3d:binding:create'),
                        ('编辑', 'scene3d:binding:update'), ('删除', 'scene3d:binding:delete')],
    'scene3d_alarm': [('查询', 'scene3d:alarm:list'), ('新增', 'scene3d:alarm:create'), ('编辑', 'scene3d:alarm:update'),
                      ('删除', 'scene3d:alarm:delete'), ('确认告警', 'scene3d:alarm:confirm')],
    'scene3d_route': [('查询', 'scene3d:route:list'), ('新增', 'scene3d:route:create'), ('编辑', 'scene3d:route:update'),
                      ('删除', 'scene3d:route:delete'), ('开始巡检', 'scene3d:route:play')],
    'scene3d_screen': [('查看', 'scene3d:screen:view')],
}


def _ensure_menu(parent_id, name, path, component, perms, mtype, icon, order, visible='0'):
    """按（父级, 名称）查找菜单，存在则复用，否则新建。"""
    row = SysMenu.objects.filter(parent_id=parent_id, menu_name=name, is_deleted=0).first()  # 幂等查找
    if row:  # 已存在
        return row  # 直接复用，保留后台手工调整的排序等
    now = time.strftime('%Y-%m-%d %H:%M:%S')  # 统一时间
    return SysMenu.objects.create(  # 新建菜单
        parent_id=parent_id, menu_name=name, path=path, component=component, perms=perms,
        menu_type=mtype, icon=icon, order_num=order, visible=visible, status='0',
        create_by='admin', create_time=now, update_by='admin', update_time=now, is_deleted=0,
    )


def seed_scene3d():
    """写入 3D 模块菜单/按钮，并把新增项授予全部未删除角色。"""
    from django.db import connection  # 局部导入，避免应用加载期访问数据库

    menu_ids = {}  # key -> 菜单主键
    created_ids = []  # 本次涉及的菜单/按钮主键（含已存在的）
    for parent_key, key, name, path, component, perms, mtype, icon, order, visible in MENUS:  # 逐条菜单
        parent_id = menu_ids.get(parent_key, 0) if parent_key else 0  # 解析父级
        row = _ensure_menu(parent_id, name, path, component, perms, mtype, icon, order, visible)  # 幂等写入
        menu_ids[key] = row.id  # 记录主键
        created_ids.append(row.id)  # 收集，后续统一授权
        for btn_name, btn_perms in BUTTONS.get(key, []):  # 挂按钮
            btn = _ensure_menu(row.id, btn_name, '', '', btn_perms, 'F', '', 0)  # 按钮无路由
            created_ids.append(btn.id)  # 收集
    role_ids = list(SysRole.objects.filter(is_deleted=0).values_list('id', flat=True))  # 全部有效角色
    with connection.cursor() as cursor:  # 使用游标批量授权
        for role_id in role_ids:  # 每个角色
            for menu_id in created_ids:  # 每个菜单项
                cursor.execute('INSERT IGNORE INTO sys_role_menu (role_id, menu_id) VALUES (%s, %s)',
                               [role_id, menu_id])  # 幂等授权
