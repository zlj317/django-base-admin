"""数据库初始化命令：

1. 创建业务数据库 gen_admin（utf8mb4）；
2. 执行 docs 目录下的初始化建表 SQL（全部 sys_ 系统表）；
3. 重置 admin 密码为 123456（bcrypt）；
4. 初始化系统菜单与管理员角色权限。

用法：python manage.py init_db
"""
import re

import pymysql
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection

SQL_FILE = r'd:\other\django-base-admin\docs\后台管理系统-初始化建表SQL.sql'

MENUS = [
    # (parent_key, key, menu_name, path, component, perms, type, icon, order)
    (None, 'dashboard', '首页', 'dashboard', 'dashboard/index', '', 'C', 'Odometer', 0),
    (None, 'system', '系统管理', 'system', '', '', 'M', 'Setting', 1),
    ('system', 'user', '用户管理', 'user', 'system/user/index', 'system:user:list', 'C', 'User', 1),
    ('system', 'role', '角色管理', 'role', 'system/role/index', 'system:role:list', 'C', 'UserFilled', 2),
    ('system', 'menu', '菜单管理', 'menu', 'system/menu/index', 'system:menu:list', 'C', 'Menu', 3),
    ('system', 'dept', '部门管理', 'dept', 'system/dept/index', 'system:dept:list', 'C', 'OfficeBuilding', 4),
    ('system', 'dict', '字典管理', 'dict', 'system/dict/index', 'system:dict:list', 'C', 'Collection', 5),
    ('system', 'config', '参数配置', 'config', 'system/config/index', 'system:config:list', 'C', 'Tools', 6),
    ('system', 'operlog', '操作日志', 'operlog', 'system/operlog/index', 'system:operlog:list', 'C', 'Document', 7),
    ('system', 'loginlog', '登录日志', 'loginlog', 'system/loginlog/index', 'system:loginlog:list', 'C', 'Key', 8),
    (None, 'gen', '系统工具', 'gen', '', '', 'M', 'MagicStick', 2),
    ('gen', 'gentable', '代码生成', 'table', 'gen/table/index', 'gen:table:list', 'C', 'Cpu', 1),
]

BUTTONS = {
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
    'operlog': [('查询', 'system:operlog:list'), ('删除', 'system:operlog:delete')],
    'loginlog': [('查询', 'system:loginlog:list'), ('删除', 'system:loginlog:delete')],
    'gentable': [('查询', 'gen:table:list'), ('导入', 'gen:table:import'), ('编辑', 'gen:table:update'),
                 ('删除', 'gen:table:delete'), ('预览', 'gen:table:preview'), ('下载', 'gen:table:download')],
}


class Command(BaseCommand):
    help = '初始化数据库：建库、建表、初始化菜单与管理员密码'

    def add_arguments(self, parser):
        parser.add_argument('--force-menus', action='store_true', help='清除旧菜单并重建')

    def handle(self, *args, **options):
        db = settings.DATABASES['default']
        self.stdout.write(f'连接数据库实例 {db["HOST"]}:{db["PORT"]} ...')

        # 1. 先不选库，创建业务数据库
        raw = pymysql.connect(host=db['HOST'], port=int(db['PORT']), user=db['USER'],
                              password=db['PASSWORD'], charset='utf8mb4')
        with raw.cursor() as cursor:
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{db['NAME']}` "
                f"DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci")
        raw.close()
        self.stdout.write(self.style.SUCCESS(f'数据库 {db["NAME"]} 就绪'))

        # 2. 执行建表 SQL
        self.exec_sql_file(SQL_FILE)
        self.stdout.write(self.style.SUCCESS('系统基础表创建完成'))

        # 3. admin 密码重置为 123456（bcrypt）
        from common.utils import hash_password
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE sys_user SET password = %s WHERE username = 'admin'",
                [hash_password('123456')])
        self.stdout.write(self.style.SUCCESS('admin 密码已重置为 123456'))

        # 4. 初始化菜单
        if options['force_menus']:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM sys_role_menu")
                cursor.execute("DELETE FROM sys_menu")
        self.init_menus()
        self.stdout.write(self.style.SUCCESS('初始化完成！默认账号 admin / 123456'))

    def exec_sql_file(self, path):
        with open(path, encoding='utf-8') as f:
            raw_sql = f.read()
        # 去掉注释行后按分号切分
        lines = [line for line in raw_sql.splitlines()
                 if not line.strip().startswith('--')]
        statements = [s.strip() for s in '\n'.join(lines).split(';') if s.strip()]
        with connection.cursor() as cursor:
            for sql in statements:
                cursor.execute(sql)

    def init_menus(self):
        from datetime import datetime

        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM sys_menu WHERE is_deleted = 0 LIMIT 1")
            if cursor.fetchone():
                self.stdout.write('菜单已存在，跳过初始化（可加 --force-menus 重建）')
                return

        def insert(parent_id, menu_name, path, component, perms, menu_type, icon, order):
            with connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO sys_menu (parent_id, menu_name, path, component, perms, "
                    "menu_type, icon, order_num, visible, status, create_by, create_time, is_deleted) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, '0', '0', 'admin', %s, 0)",
                    [parent_id, menu_name, path, component, perms, menu_type, icon,
                     order, datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
                cursor.execute("SELECT LAST_INSERT_ID()")
                return cursor.fetchone()[0]

        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        menu_ids = {}
        for parent_key, key, name, path, component, perms, mtype, icon, order in MENUS:
            parent_id = menu_ids.get(parent_key, 0) if parent_key else 0
            menu_ids[key] = insert(parent_id, name, path, component, perms, mtype, icon, order)
            for btn_name, btn_perms in BUTTONS.get(key, []):
                insert(menu_ids[key], btn_name, '', '', btn_perms, 'F', '', 0)

        # 全部菜单授予超级管理员角色
        with connection.cursor() as cursor:
            cursor.execute("INSERT IGNORE INTO sys_role_menu (role_id, menu_id) "
                           "SELECT 1, id FROM sys_menu")
        self.stdout.write(f'菜单初始化完成，共 {len(menu_ids)} 个菜单 + 按钮权限')
