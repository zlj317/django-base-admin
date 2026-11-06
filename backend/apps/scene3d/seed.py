"""3D 可视化模块种子：菜单 + 按钮权限（幂等，可重复执行）。"""
# 模块：apps/scene3d/seed.py —— 3D 可视化模块的菜单与按钮权限种子脚本
# 用途：创建"3D可视化"顶级目录及其下 8 个页面菜单，并为各页面挂载增删改查、发布、巡检等按钮权限。
# 调用方：core/management/commands/init_db.py 初始化数据库时调用 seed_scene3d()。
# 幂等性：菜单按（父级 + 名称 + 未删除）判重，角色授权用 INSERT IGNORE 忽略重复行，可反复执行。
# 涉及表：sys_menu（菜单/按钮记录）、sys_role_menu（角色-菜单授权关系）。
import time  # 生成创建/更新时间字符串

from apps.system.models import SysMenu, SysRole  # 复用系统菜单与角色模型

# 菜单定义：(父 key, key, 名称, 路由, 组件, 权限, 类型, 图标, 排序, 是否可见)
# 字段说明：父 key 为 None 表示顶级目录；类型 M=目录、C=页面；可见 '0'=显示、'1'=隐藏（仅从列表跳转进入）
MENUS = [
    # 顶级目录：3D可视化，作为下面 8 个页面的父节点，路由 scene3d 由前端拼接子路径
    (None, 'scene3d', '3D可视化', 'scene3d', '', '', 'M', 'DataBoard', 16, '0'),  # 顶级目录
    # 场景分类页：维护机房/库房/园区等业务归类，路由 category，权限标识 scene3d:category:list
    ('scene3d', 'scene3d_category', '场景分类', 'category', 'scene3d/category/index', 'scene3d:category:list', 'C', 'Folder', 1, '0'),
    # 3D场景管理页：场景主表列表、新建、发布入口，路由 scene，权限标识 scene3d:scene:list
    ('scene3d', 'scene3d_scene', '3D场景管理', 'scene', 'scene3d/scene/index', 'scene3d:scene:list', 'C', 'Monitor', 2, '0'),
    # 场景编辑器页：路由带 :id 参数，供前端从场景列表点击"编辑"进入，故在导航中隐藏
    ('scene3d', 'scene3d_editor', '场景编辑器', 'editor/:id', 'scene3d/editor/index', 'scene3d:scene:update', 'C', 'Edit', 3, '1'),  # 隐藏菜单，从列表进入
    # 模型资源页：上传并维护 glTF/GLB 等 3D 模型素材，路由 model，权限标识 scene3d:model:list
    ('scene3d', 'scene3d_model', '模型资源', 'model', 'scene3d/model/index', 'scene3d:model:list', 'C', 'Box', 4, '0'),
    # 数据绑定页：把设备/指标数据点映射到场景中的对象属性，路由 binding，权限标识 scene3d:binding:list
    ('scene3d', 'scene3d_binding', '数据绑定', 'binding', 'scene3d/binding/index', 'scene3d:binding:list', 'C', 'Connection', 5, '0'),
    # 告警联动页：配置告警规则、查看并确认告警记录，路由 alarm，权限标识 scene3d:alarm:list
    ('scene3d', 'scene3d_alarm', '告警联动', 'alarm', 'scene3d/alarm/index', 'scene3d:alarm:list', 'C', 'Bell', 6, '0'),
    # 巡检路线页：维护巡检点位顺序并触发巡检动画，路由 route，权限标识 scene3d:route:list
    ('scene3d', 'scene3d_route', '巡检路线', 'route', 'scene3d/route/index', 'scene3d:route:list', 'C', 'Guide', 7, '0'),
    # 场景发布页：已发布场景的大屏入口，路由 screen，权限标识 scene3d:screen:view（只读查看）
    ('scene3d', 'scene3d_screen', '场景发布', 'screen', 'scene3d/screen/index', 'scene3d:screen:view', 'C', 'DataLine', 8, '0'),
]
# 以上 key 既用于父子关系解析，也是下方 BUTTONS 的挂载键；排序号决定同级菜单在左侧导航中的先后

# 按钮权限：与后端 @perm_map 中的权限标识逐一对齐
# 结构：key 为所属页面 key，值为（按钮名称, 权限标识）列表；前端按标识显隐按钮，后端按同一标识校验
BUTTONS = {
    # 场景分类：标准四个按钮，分别对应分页查询、新增、编辑、删除接口
    'scene3d_category': [('查询', 'scene3d:category:list'), ('新增', 'scene3d:category:create'),
                         ('编辑', 'scene3d:category:update'), ('删除', 'scene3d:category:delete')],
    # 场景管理：基础增删改查，外加发布、版本回滚、生成分享，以及场景访问授权的查询/新增/删除
    'scene3d_scene': [('查询', 'scene3d:scene:list'), ('新增', 'scene3d:scene:create'), ('编辑', 'scene3d:scene:update'),
                      ('删除', 'scene3d:scene:delete'), ('发布', 'scene3d:scene:publish'),
                      ('版本回滚', 'scene3d:scene:version'), ('生成分享', 'scene3d:scene:share'),
                      ('访问授权', 'scene3d:permission:list'), ('新增授权', 'scene3d:permission:create'),
                      ('删除授权', 'scene3d:permission:delete')],
    # 模型资源：模型文件通过上传接口入库，因此以"上传"替代"新增"，另有编辑与删除
    'scene3d_model': [('查询', 'scene3d:model:list'), ('上传', 'scene3d:model:upload'),
                      ('编辑', 'scene3d:model:update'), ('删除', 'scene3d:model:delete')],
    # 数据绑定：绑定关系（场景对象 ↔ 数据点）的查询、新增、编辑、删除
    'scene3d_binding': [('查询', 'scene3d:binding:list'), ('新增', 'scene3d:binding:create'),
                        ('编辑', 'scene3d:binding:update'), ('删除', 'scene3d:binding:delete')],
    # 告警联动：告警规则/记录共用的增删改查，另加"确认告警"表示人工处理完毕
    'scene3d_alarm': [('查询', 'scene3d:alarm:list'), ('新增', 'scene3d:alarm:create'), ('编辑', 'scene3d:alarm:update'),
                      ('删除', 'scene3d:alarm:delete'), ('确认告警', 'scene3d:alarm:confirm')],
    # 巡检路线：路线维护的增删改查，另加"开始巡检"用于触发沿路线的巡检动画/模拟
    'scene3d_route': [('查询', 'scene3d:route:list'), ('新增', 'scene3d:route:create'), ('编辑', 'scene3d:route:update'),
                      ('删除', 'scene3d:route:delete'), ('开始巡检', 'scene3d:route:play')],
    # 场景发布：大屏为只读展示入口，仅保留查看权限，不开放写操作
    'scene3d_screen': [('查看', 'scene3d:screen:view')],
}
# 未出现在上面的页面（编辑器、模板、场景对象、巡检记录、访问日志等）不单独生成按钮，沿用其所属页面的权限


# 幂等创建单条菜单或按钮：按"父级 + 名称 + 未删除"判重，命中则复用，避免 init_db 重复执行产生重复记录
def _ensure_menu(parent_id, name, path, component, perms, mtype, icon, order, visible='0'):
    """按（父级, 名称）查找菜单，存在则复用，否则新建。"""
    row = SysMenu.objects.filter(parent_id=parent_id, menu_name=name, is_deleted=0).first()  # 幂等查找
    if row:  # 已存在
        return row  # 直接复用，保留后台手工调整的排序等
    now = time.strftime('%Y-%m-%d %H:%M:%S')  # 统一时间
    return SysMenu.objects.create(  # 新建菜单
        # 基础属性：父级 ID、菜单名、前端路由、页面组件路径与后端权限标识
        parent_id=parent_id, menu_name=name, path=path, component=component, perms=perms,
        # 展示属性：类型（M 目录/C 页面/F 按钮）、图标、排序、是否可见；status='0' 表示启用
        menu_type=mtype, icon=icon, order_num=order, visible=visible, status='0',
        # 审计字段固定为 admin（种子数据无真实操作人），is_deleted=0 表示未删除
        create_by='admin', create_time=now, update_by='admin', update_time=now, is_deleted=0,
    )


# 初始化入口：写入菜单树与按钮权限，再把本次涉及的所有菜单项授权给全部有效角色
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
                # 逐角色逐菜单写入授权表；INSERT IGNORE 让重复执行时不报唯一键冲突，保持幂等
                cursor.execute('INSERT IGNORE INTO sys_role_menu (role_id, menu_id) VALUES (%s, %s)',
                               [role_id, menu_id])  # 幂等授权
