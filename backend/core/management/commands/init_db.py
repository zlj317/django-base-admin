"""数据库初始化命令：

1. 创建业务数据库 gen_admin（utf8mb4）；
2. 执行 docs 目录下的初始化建表 SQL（全部 sys_ 系统表）；
3. 重置 admin 密码为 123456（bcrypt）；
4. 初始化系统菜单与管理员角色权限。

用法：python manage.py init_db
"""
import re  # 文本/正则处理工具（建表 SQL 预处理预留）

import pymysql  # 直连 MySQL，用于执行 Django 连接之外的建库语句
from django.conf import settings  # 读取数据库连接配置，避免命令内重复维护
from django.core.management.base import BaseCommand  # 管理命令基类
from django.db import connection  # 复用 Django 连接执行建表与初始化 SQL

SQL_FILE = r'd:\other\django-base-admin\docs\后台管理系统-初始化建表SQL.sql'  # 初始化建表脚本路径（原始字符串避免转义）
SQL_WORKFLOW_FILE = r'd:\other\django-base-admin\docs\后台管理系统-工作流建表SQL.sql'  # 工作流 11 张表建表脚本

MENUS = [  # 菜单定义：(父 key, key, 名称, 路由, 组件, 权限, 类型, 图标, 排序)
    (None, 'dashboard', '首页', 'dashboard', 'dashboard/index', '', 'C', 'Odometer', 0),  # 首页看板，无需权限
    (None, 'system', '系统管理', 'system', '', '', 'M', 'Setting', 1),  # 系统管理目录（M 为目录类型）
    ('system', 'user', '用户管理', 'user', 'system/user/index', 'system:user:list', 'C', 'User', 1),
    ('system', 'role', '角色管理', 'role', 'system/role/index', 'system:role:list', 'C', 'UserFilled', 2),
    ('system', 'menu', '菜单管理', 'menu', 'system/menu/index', 'system:menu:list', 'C', 'Menu', 3),
    ('system', 'dept', '部门管理', 'dept', 'system/dept/index', 'system:dept:list', 'C', 'OfficeBuilding', 4),
    ('system', 'dict', '字典管理', 'dict', 'system/dict/index', 'system:dict:list', 'C', 'Collection', 5),
    ('system', 'config', '参数配置', 'config', 'system/config/index', 'system:config:list', 'C', 'Tools', 6),
    ('system', 'operlog', '操作日志', 'operlog', 'system/operlog/index', 'system:operlog:list', 'C', 'Document', 7),
    ('system', 'loginlog', '登录日志', 'loginlog', 'system/loginlog/index', 'system:loginlog:list', 'C', 'Key', 8),
    (None, 'gen', '系统工具', 'gen', '', '', 'M', 'MagicStick', 2),  # 代码生成器入口目录
    ('gen', 'gentable', '代码生成', 'table', 'gen/table/index', 'gen:table:list', 'C', 'Cpu', 1),
]

BUTTONS = {  # 各菜单下的按钮权限：中文名称 + 权限标识，供角色分配时勾选
    'user': [('查询', 'system:user:list'), ('新增', 'system:user:create'), ('编辑', 'system:user:update'),
             ('删除', 'system:user:delete'), ('重置密码', 'system:user:resetPwd'), ('分配角色', 'system:user:assignRoles')],
    'role': [('查询', 'system:role:list'), ('新增', 'system:role:create'), ('编辑', 'system:role:update'),
             ('删除', 'system:role:delete'), ('分配权限', 'system:role:assignMenus')],
    'menu': [('查询', 'system:menu:list'), ('新增', 'system:menu:create'), ('编辑', 'system:menu:update'),
             ('删除', 'system:menu:delete')],
    'dept': [('查询', 'system:dept:list'), ('新增', 'system:dept:create'), ('编辑', 'system:dept:update'),
             ('删除', 'system:dept:delete')],
    'dict': [('查询', 'system:dict:list'), ('新增', 'system:dict:create'), ('编辑', 'system:dict:update'),
             ('删除', 'system:dict:delete')],
    'config': [('查询', 'system:config:list'), ('新增', 'system:config:create'), ('编辑', 'system:config:update'),
               ('删除', 'system:config:delete')],
    'operlog': [('查询', 'system:operlog:list'), ('删除', 'system:operlog:delete')],  # 日志只允许查询与删除
    'loginlog': [('查询', 'system:loginlog:list'), ('删除', 'system:loginlog:delete')],  # 同上，避免误改日志
    'gentable': [('查询', 'gen:table:list'), ('导入', 'gen:table:import'), ('编辑', 'gen:table:update'),
                 ('删除', 'gen:table:delete'), ('预览', 'gen:table:preview'), ('下载', 'gen:table:download')],
}


class Command(BaseCommand):
    """init_db 管理命令：一键完成建库、建表、初始密码与菜单初始化。"""

    help = '初始化数据库：建库、建表、初始化菜单与管理员密码'  # manage.py help 中展示的一行说明

    def add_arguments(self, parser):
        """声明 --force-menus 选项，用于清空并重建菜单。"""
        parser.add_argument('--force-menus', action='store_true', help='清除旧菜单并重建')  # 仅在需要重置菜单时使用

    def handle(self, *args, **options):
        """按“建库 → 建表 → 重置密码 → 初始化菜单”顺序执行，可重复运行。"""
        db = settings.DATABASES['default']  # 复用项目配置，避免命令与 settings 两处不一致
        self.stdout.write(f'连接数据库实例 {db["HOST"]}:{db["PORT"]} ...')  # 输出进度，便于观察执行到哪一步

        # 1. 先不选库，创建业务数据库
        raw = pymysql.connect(host=db['HOST'], port=int(db['PORT']), user=db['USER'],
                              password=db['PASSWORD'], charset='utf8mb4')  # 不指定库名，因目标库可能尚不存在
        with raw.cursor() as cursor:
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{db['NAME']}` "
                f"DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci")  # 已存在则跳过，支持反复执行
        raw.close()  # 建库完成即断开，后续统一交给 Django 连接
        self.stdout.write(self.style.SUCCESS(f'数据库 {db["NAME"]} 就绪'))  # 绿色成功提示

        # 2. 执行建表 SQL
        self.exec_sql_file(SQL_FILE)  # 全量创建系统基础表，脚本内均为 CREATE TABLE
        self.exec_sql_file(SQL_WORKFLOW_FILE)  # 创建工作流 11 张 wf_ 表（IF NOT EXISTS 幂等）
        self.stdout.write(self.style.SUCCESS('系统基础表与工作流表创建完成'))  # 提示建表完成

        # 3. admin 密码重置为 123456（bcrypt）
        from common.utils import hash_password  # 局部导入，确保 Django 配置已加载完毕
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE sys_user SET password = %s WHERE username = 'admin'",
                [hash_password('123456')])  # 参数化传入哈希值，避免拼接 SQL
        self.stdout.write(self.style.SUCCESS('admin 密码已重置为 123456'))  # 重置为约定初始密码

        # 4. 初始化菜单
        if options['force_menus']:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM sys_role_menu")  # 先清角色-菜单关联，避免留下脏数据
                cursor.execute("DELETE FROM sys_menu")  # 再清菜单本体
        self.init_menus()  # 幂等：已有菜单时内部会自动跳过
        from apps.workflow.seed import seed_workflow  # 局部导入，避免命令加载期依赖工作流模型
        seed_workflow()  # 写入工作流程菜单、按钮权限与请假/报销演示数据（幂等）
        self.stdout.write(self.style.SUCCESS('初始化完成！默认账号 admin / 123456'))  # 收尾提示

    def exec_sql_file(self, path):
        """读取 SQL 脚本，去掉注释行后按分号逐条执行。"""
        with open(path, encoding='utf-8') as f:
            raw_sql = f.read()  # 一次性读入，脚本体积较小
        # 去掉注释行后按分号切分
        lines = [line for line in raw_sql.splitlines()
                 if not line.strip().startswith('--')]  # 跳过 -- 注释行，避免被当成语句执行
        statements = [s.strip() for s in '\n'.join(lines).split(';') if s.strip()]  # 按分号拆分并丢弃空语句
        with connection.cursor() as cursor:
            for sql in statements:
                cursor.execute(sql)  # 顺序执行，建表语句之间无外键依赖

    def init_menus(self):
        """按 MENUS/BUTTONS 写入菜单与按钮，并授予超级管理员全部权限。"""
        from datetime import datetime  # 局部导入，用于生成创建时间字符串

        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM sys_menu WHERE is_deleted = 0 LIMIT 1")  # 探测是否已有菜单数据
            if cursor.fetchone():
                self.stdout.write('菜单已存在，跳过初始化（可加 --force-menus 重建）')  # 幂等保护，避免重复插入
                return  # 已有数据直接结束

        def insert(parent_id, menu_name, path, component, perms, menu_type, icon, order):
            """插入单条菜单/按钮并返回自增主键，供子级挂载使用。"""
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO sys_menu (parent_id, menu_name, path, component, perms, "
                    "menu_type, icon, order_num, visible, status, create_by, create_time, is_deleted) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, '0', '0', 'admin', %s, 0)",
                    [parent_id, menu_name, path, component, perms, menu_type, icon,
                     order, datetime.now().strftime('%Y-%m-%d %H:%M:%S')])  # 参数化写入，时间取本地当前值
                cursor.execute("SELECT LAST_INSERT_ID()")  # 会话级自增 ID，紧接着取才准确
                return cursor.fetchone()[0]  # 返回新菜单主键

        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # 预留批次时间（当前未使用）
        menu_ids = {}  # key -> 菜单 id，用于解析父子关系
        for parent_key, key, name, path, component, perms, mtype, icon, order in MENUS:
            parent_id = menu_ids.get(parent_key, 0) if parent_key else 0  # 无父级时作为顶级菜单
            menu_ids[key] = insert(parent_id, name, path, component, perms, mtype, icon, order)  # 先插菜单拿 id
            for btn_name, btn_perms in BUTTONS.get(key, []):
                insert(menu_ids[key], btn_name, '', '', btn_perms, 'F', '', 0)  # 按钮行：类型 F，无路由与图标

        # 全部菜单授予超级管理员角色
        with connection.cursor() as cursor:
            cursor.execute("INSERT IGNORE INTO sys_role_menu (role_id, menu_id) "
                           "SELECT 1, id FROM sys_menu")  # 角色 1 为内置超管，INSERT IGNORE 保证可重复执行
        self.stdout.write(f'菜单初始化完成，共 {len(menu_ids)} 个菜单 + 按钮权限')  # 统计菜单数量
