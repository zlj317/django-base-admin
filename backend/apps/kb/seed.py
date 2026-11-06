# 文件：apps/kb/seed.py —— 知识库模块的菜单与按钮权限种子脚本
# 用途：幂等创建"知识库"目录及"文档分类""文档列表"两个页面菜单，并挂上增删改查按钮权限。
# 对应表：sys_menu（菜单与按钮）、sys_role_menu（角色-菜单授权）。
# 路由前缀：后端接口 api/kb/；前端页面路由 kb/category、kb/document。
# 关键约定：按"父级 + 名称 + 未删除"判重，重复执行不会产生重复菜单；
#           授权用 INSERT IGNORE 忽略重复行；由 core/management/commands/init_db.py 调用 seed_kb()。
"""知识库模块种子：菜单 + 按钮权限（幂等）。"""
# 生成与库表 DATETIME 对齐的创建/更新时间字符串
import time

# 菜单模型（写菜单/按钮）与角色模型（读角色 ID 用于授权）
from apps.system.models import SysMenu, SysRole

# 菜单定义：每行依次为（父级 key、本级 key、菜单名、路由 path、前端组件、权限标识、类型、图标、排序）
# 类型 M=目录、C=菜单页面；父级 key 为 None 表示顶级目录
MENUS = [
    # 顶级目录：知识库，作为下面两个页面菜单的父节点，排序 15 表示在侧边栏中的位置
    (None, 'kb', '知识库', 'kb', '', '', 'M', 'CollectionTag', 15),
    # 文档分类页：分类树的维护入口，页面级权限统一为 kb:list
    ('kb', 'kb_category', '文档分类', 'category', 'kb/category/index', 'kb:list', 'C', 'Collection', 1),
    # 文档列表页：文档的增删改查与统计入口，权限标识同样复用 kb:list
    ('kb', 'kb_document', '文档列表', 'document', 'kb/document/index', 'kb:list', 'C', 'Document', 2),
]

# 按钮权限定义：键为菜单 key，值为（按钮名称、权限标识）列表；未列出的菜单不生成按钮
BUTTONS = {
    # 分类：标准增删改查四个按钮，对应基类的 list/create/update/delete 动作
    'kb_category': [('查询', 'kb:list'), ('新增', 'kb:create'),
                    ('编辑', 'kb:update'), ('删除', 'kb:delete')],
    # 文档：同样四个按钮，权限前缀与分类共用 kb，便于统一授权
    'kb_document': [('查询', 'kb:list'), ('新增', 'kb:create'),
                    ('编辑', 'kb:update'), ('删除', 'kb:delete')],
}


# 幂等创建单条菜单：存在则直接复用，避免重复执行 init_db 造成菜单重复
def _ensure_menu(parent_id, name, path, component, perms, mtype, icon, order):
    # 幂等键 = 父级 + 菜单名 + 未删除；命中说明此前已初始化过
    row = SysMenu.objects.filter(parent_id=parent_id, menu_name=name, is_deleted=0).first()
    # 已存在时返回原对象，后续按钮创建与授权复用它的 ID
    if row:
        return row
    # 不存在才新建；时间使用本地字符串格式，与其它模块的种子脚本保持一致
    now = time.strftime('%Y-%m-%d %H:%M:%S')
    # 插入菜单/按钮；id 由雪花算法字段的默认值生成，无需手工指定
    return SysMenu.objects.create(
        # 基础属性：父级、名称、路由 path、前端组件路径、权限标识
        parent_id=parent_id, menu_name=name, path=path, component=component, perms=perms,
        # 菜单类型（M 目录 / C 页面 / F 按钮）、图标、排序；visible/status='0' 表示显示且启用
        menu_type=mtype, icon=icon, order_num=order, visible='0', status='0',
        # 审计字段固定为 admin：种子数据由初始化脚本写入，没有真实操作人
        create_by='admin', create_time=now, update_by='admin', update_time=now, is_deleted=0)


# 初始化入口：创建菜单与按钮，并授权给所有未删除角色
def seed_kb():
    # 延迟导入连接对象：只有本函数需要原生游标做批量授权
    from django.db import connection
    # key → 菜单 ID 映射，供子菜单回填父级 ID
    menu_ids = {}
    # 收集本次创建的菜单与按钮 ID，最后统一授权
    created_ids = []
    # 按定义顺序创建，保证父级菜单先于子级菜单落库
    for parent_key, key, name, path, component, perms, mtype, icon, order in MENUS:
        # 顶级菜单父级为 0；子菜单从映射取父级 ID（此时父级已创建）
        parent_id = menu_ids.get(parent_key, 0) if parent_key else 0
        # 幂等创建菜单本身（目录或页面）
        row = _ensure_menu(parent_id, name, path, component, perms, mtype, icon, order)
        # 缓存本级 ID，供后续子菜单使用
        menu_ids[key] = row.id
        # 菜单本身也要纳入授权集合
        created_ids.append(row.id)
        # 为该页面创建按钮权限；无定义的 key 取到空列表，循环不执行
        for btn_name, btn_perms in BUTTONS.get(key, []):
            # 按钮父级是所属页面；类型 F 表示按钮，无路由与前端组件
            btn = _ensure_menu(row.id, btn_name, '', '', btn_perms, 'F', '', 0)
            # 按钮同样纳入授权集合
            created_ids.append(btn.id)
    # 取全部未删除角色 ID，种子默认给所有角色授权
    role_ids = list(SysRole.objects.filter(is_deleted=0).values_list('id', flat=True))
    # 用原生游标批量写关联表，避免逐条 ORM 往返带来的开销
    with connection.cursor() as cursor:
        # 外层：遍历每个角色
        for role_id in role_ids:
            # 内层：遍历本次涉及的菜单与按钮
            for menu_id in created_ids:
                # INSERT IGNORE：重复执行时已存在的授权行被忽略，保证幂等且不报唯一键错误
                cursor.execute('INSERT IGNORE INTO sys_role_menu (role_id, menu_id) VALUES (%s, %s)',
                               # 参数顺序必须与 SQL 占位符一一对应
                               [role_id, menu_id])
