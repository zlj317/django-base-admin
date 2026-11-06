# ----------------------------------------------------------------------------
# 数据库初始化命令 init_db（入口：python manage.py init_db）
# 用途：一键初始化全新环境 —— 建库(utf8mb4) → 执行 docs 下 4 个建表 SQL →
#       重置 admin 密码 → 写入系统菜单/按钮 → 调用各业务模块 seed() 写入种子数据。
# 调用：在 backend 目录执行 `python manage.py init_db`；
#       需要重建菜单时追加 `--force-menus`（先清空 sys_menu 与 sys_role_menu）。
#
# 依赖表：
#   sys_user / sys_menu / sys_role_menu —— 本文件直接读写（admin 账号需已存在）
#   docs/后台管理系统-初始化建表SQL.sql  创建的 sys_* 基础表
#   docs/后台管理系统-工作流建表SQL.sql  创建的 wf_* 工作流表
#   docs/new_features_init.sql           需求4/5/6 新增功能表
#   docs/scene3d_init.sql                需求7 3D 可视化相关表
#   各业务模块演示数据表（见 apps/*/seed.py，本文件只负责调用）
#
# 幂等性：建库/建表均使用 IF NOT EXISTS；菜单存在则跳过（除非 --force-menus）；
#         各 seed 函数内部使用 INSERT IGNORE 或存在性判断，可反复执行。
# ----------------------------------------------------------------------------
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
SQL_NEW_FEATURES = r'd:\other\django-base-admin\docs\new_features_init.sql'  # 需求4+5+6 新增功能建表脚本
SQL_SCENE3D = r'd:\other\django-base-admin\docs\scene3d_init.sql'  # 需求7 3D 可视化 13 张表（IF NOT EXISTS 幂等）

MENUS = [  # 菜单定义：(父 key, key, 名称, 路由, 组件, 权限, 类型, 图标, 排序)
    (None, 'dashboard', '首页', 'dashboard', 'dashboard/index', '', 'C', 'Odometer', 0),  # 首页看板，无需权限
    (None, 'system', '系统管理', 'system', '', '', 'M', 'Setting', 1),  # 系统管理目录（M 为目录类型）
    # 用户管理：C 表示页面菜单，perms 与后端接口的权限校验标识保持一致
    ('system', 'user', '用户管理', 'user', 'system/user/index', 'system:user:list', 'C', 'User', 1),
    # 角色管理：维护角色本身以及角色与菜单/数据权限的绑定关系
    ('system', 'role', '角色管理', 'role', 'system/role/index', 'system:role:list', 'C', 'UserFilled', 2),
    # 菜单管理：维护 sys_menu 自身，支持运行期动态增删页面与按钮
    ('system', 'menu', '菜单管理', 'menu', 'system/menu/index', 'system:menu:list', 'C', 'Menu', 3),
    # 部门管理：组织架构树，用户所属部门用于数据权限过滤
    ('system', 'dept', '部门管理', 'dept', 'system/dept/index', 'system:dept:list', 'C', 'OfficeBuilding', 4),
    # 字典管理：集中维护下拉选项等基础枚举，避免前端硬编码
    ('system', 'dict', '字典管理', 'dict', 'system/dict/index', 'system:dict:list', 'C', 'Collection', 5),
    # 参数配置：运行期可调参数（开关、阈值等），修改后无需重新发布
    ('system', 'config', '参数配置', 'config', 'system/config/index', 'system:config:list', 'C', 'Tools', 6),
    # 操作日志：记录写操作审计信息，通常只开放查询与删除
    ('system', 'operlog', '操作日志', 'operlog', 'system/operlog/index', 'system:operlog:list', 'C', 'Document', 7),
    # 登录日志：记录登录成功/失败明细，用于安全审计与异常排查
    ('system', 'loginlog', '登录日志', 'loginlog', 'system/loginlog/index', 'system:loginlog:list', 'C', 'Key', 8),
    (None, 'gen', '系统工具', 'gen', '', '', 'M', 'MagicStick', 2),  # 代码生成器入口目录
    # 代码生成：按数据库表结构生成前后端代码，path=table 与前端目录 gen/table 对应
    ('gen', 'gentable', '代码生成', 'table', 'gen/table/index', 'gen:table:list', 'C', 'Cpu', 1),
]

BUTTONS = {  # 各菜单下的按钮权限：中文名称 + 权限标识，供角色分配时勾选
    # 用户管理按钮组：查询/新增/编辑/删除，另加重置密码与分配角色两个扩展动作
    'user': [('查询', 'system:user:list'), ('新增', 'system:user:create'), ('编辑', 'system:user:update'),
             ('删除', 'system:user:delete'), ('重置密码', 'system:user:resetPwd'), ('分配角色', 'system:user:assignRoles')],
    # 角色管理按钮组：在基础增删改查之外，单独提供"分配权限"入口
    'role': [('查询', 'system:role:list'), ('新增', 'system:role:create'), ('编辑', 'system:role:update'),
             ('删除', 'system:role:delete'), ('分配权限', 'system:role:assignMenus')],
    # 菜单管理按钮组：仅覆盖基础增删改查，菜单树由页面内交互完成
    'menu': [('查询', 'system:menu:list'), ('新增', 'system:menu:create'), ('编辑', 'system:menu:update'),
             ('删除', 'system:menu:delete')],
    # 部门管理按钮组：与菜单一致的基础增删改查
    'dept': [('查询', 'system:dept:list'), ('新增', 'system:dept:create'), ('编辑', 'system:dept:update'),
             ('删除', 'system:dept:delete')],
    # 字典管理按钮组：基础增删改查，字典数据在子页面维护
    'dict': [('查询', 'system:dict:list'), ('新增', 'system:dict:create'), ('编辑', 'system:dict:update'),
             ('删除', 'system:dict:delete')],
    # 参数配置按钮组：基础增删改查
    'config': [('查询', 'system:config:list'), ('新增', 'system:config:create'), ('编辑', 'system:config:update'),
               ('删除', 'system:config:delete')],
    # 操作日志只保留查询与删除按钮，避免误操作篡改审计数据
    'operlog': [('查询', 'system:operlog:list'), ('删除', 'system:operlog:delete')],  # 日志只允许查询与删除
    # 登录日志同样只保留查询与删除，日志记录不允许编辑
    'loginlog': [('查询', 'system:loginlog:list'), ('删除', 'system:loginlog:delete')],  # 同上，避免误改日志
    # 代码生成按钮组：查询/导入表/编辑配置/删除，外加预览与下载生成代码
    'gentable': [('查询', 'gen:table:list'), ('导入', 'gen:table:import'), ('编辑', 'gen:table:update'),
                 ('删除', 'gen:table:delete'), ('预览', 'gen:table:preview'), ('下载', 'gen:table:download')],
}


# 管理命令类：文件名 init_db 即命令名，继承 BaseCommand 后才会被 manage.py 发现
class Command(BaseCommand):
    """init_db 管理命令：一键完成建库、建表、初始密码与菜单初始化。"""

    help = '初始化数据库：建库、建表、初始化菜单与管理员密码'  # manage.py help 中展示的一行说明

    # 声明命令参数：add_arguments 只负责注册参数，实际取值在 handle 的 options 中
    def add_arguments(self, parser):
        """声明 --force-menus 选项，用于清空并重建菜单。"""
        parser.add_argument('--force-menus', action='store_true', help='清除旧菜单并重建')  # 仅在需要重置菜单时使用

    # 命令入口：按"建库 → 建表 → 重置密码 → 初始化菜单与种子数据"四个阶段执行
    def handle(self, *args, **options):
        """按“建库 → 建表 → 重置密码 → 初始化菜单”顺序执行，可重复运行。"""
        db = settings.DATABASES['default']  # 复用项目配置，避免命令与 settings 两处不一致
        self.stdout.write(f'连接数据库实例 {db["HOST"]}:{db["PORT"]} ...')  # 输出进度，便于观察执行到哪一步

        # 1. 先不选库，创建业务数据库
        # 建库阶段：pymysql 直连 MySQL 实例，且不指定 db 名，因为目标库可能还不存在
        raw = pymysql.connect(host=db['HOST'], port=int(db['PORT']), user=db['USER'],
                              password=db['PASSWORD'], charset='utf8mb4')  # 不指定库名，因目标库可能尚不存在
        # 游标上下文管理：退出时自动关闭游标，异常场景也不会泄漏连接
        with raw.cursor() as cursor:
            # 建库语句：库名取自 settings，反引号包裹特殊字符；IF NOT EXISTS 保证可重复执行
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{db['NAME']}` "
                f"DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci")  # 已存在则跳过，支持反复执行
        raw.close()  # 建库完成即断开，后续统一交给 Django 连接
        self.stdout.write(self.style.SUCCESS(f'数据库 {db["NAME"]} 就绪'))  # 绿色成功提示

        # 2. 执行建表 SQL
        self.exec_sql_file(SQL_FILE)  # 全量创建系统基础表，脚本内均为 CREATE TABLE
        self.exec_sql_file(SQL_WORKFLOW_FILE)  # 创建工作流 11 张 wf_ 表（IF NOT EXISTS 幂等）
        self.exec_sql_file(SQL_NEW_FEATURES)  # 创建需求4+5+6 新增功能表（IF NOT EXISTS 幂等）
        self.exec_sql_file(SQL_SCENE3D)  # 创建需求7 3D 可视化 13 张表 + 样例数据（IF NOT EXISTS / INSERT IGNORE 幂等）
        self.stdout.write(self.style.SUCCESS('系统基础表、工作流表与新增功能表创建完成'))  # 提示建表完成

        # 3. admin 密码重置为 123456（bcrypt）
        from common.utils import hash_password  # 局部导入，确保 Django 配置已加载完毕
        # 重置密码阶段：回到 Django 默认连接，与项目其他代码共用同一份数据库配置
        with connection.cursor() as cursor:
            # 参数化 UPDATE：只匹配 admin 账号，哈希由 common.utils 统一生成（bcrypt）
            cursor.execute(
                "UPDATE sys_user SET password = %s WHERE username = 'admin'",
                [hash_password('123456')])  # 参数化传入哈希值，避免拼接 SQL
        self.stdout.write(self.style.SUCCESS('admin 密码已重置为 123456'))  # 重置为约定初始密码

        # 4. 初始化菜单
        # 菜单阶段：仅在显式传入 --force-menus 时先清空，避免日常执行误删线上菜单
        if options['force_menus']:
            # 同一个连接内先删关联表再删菜单主表，防止残留指向已删除菜单的授权记录
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM sys_role_menu")  # 先清角色-菜单关联，避免留下脏数据
                cursor.execute("DELETE FROM sys_menu")  # 再清菜单本体
        self.init_menus()  # 幂等：已有菜单时内部会自动跳过
        from apps.workflow.seed import seed_workflow  # 局部导入，避免命令加载期依赖工作流模型
        seed_workflow()  # 写入工作流程菜单、按钮权限与请假/报销演示数据（幂等）
        # ↓↓↓ 以下为业务模块菜单种子（幂等可重复执行） ↓↓↓
        from apps.file.seed import seed_file  # 文件管理
        # 文件管理模块：文件列表、回收站与存储配置等菜单及种子数据
        seed_file()
        from apps.msg.seed import seed_msg  # 消息中心
        # 消息中心：消息模板、会话与通知相关菜单种子
        seed_msg()
        from apps.notice.seed import seed_notice  # 公告通知
        # 公告通知：公告分类与通知方式相关菜单种子
        seed_notice()
        from apps.task_sched.seed import seed_task_sched  # 定时任务
        # 定时任务：任务列表、执行日志菜单与示例任务种子
        seed_task_sched()
        from apps.report.seed import seed_report  # 报表管理
        # 报表管理：报表模板与图表配置菜单种子
        seed_report()
        from apps.bi.seed import seed_bi  # 大屏BI
        # 大屏 BI：大屏、组件与数据源相关菜单种子
        seed_bi()
        from apps.outer.seed import seed_outer  # 外部对接
        # 外部对接：第三方应用与接口配置菜单种子
        seed_outer()
        # ↓↓↓ 需求4：通用标配功能 ↓↓↓
        from apps.sys_no.seed import seed_sys_no  # 编码规则
        # 编码规则：订单/发货单等单号生成规则（按日/月/年重置）种子
        seed_sys_no()
        from apps.imprint.seed import seed_imprint  # 导入模板 + 打印模板
        # 导入模板 + 打印模板：模板主表、导入列配置与打印模板种子
        seed_imprint()
        from apps.backup.seed import seed_backup  # 数据备份
        # 数据备份：历史备份记录与自动备份策略种子
        seed_backup()
        from apps.dp.seed import seed_dp  # 数据权限
        # 数据权限：全部/本部门/仅本人/指定角色四种范围及角色授权种子
        seed_dp()
        from apps.dsm.seed import seed_dsm  # 脱敏配置
        # 脱敏配置：手机号、身份证、银行卡等字段掩码规则种子
        seed_dsm()
        from apps.mon.seed import seed_mon  # 监控告警
        # 监控告警：告警规则与历史告警记录种子
        seed_mon()
        from apps.sec.seed import seed_sec  # 安全策略
        # 安全策略：IP 黑白名单、登录尝试记录与接口限流规则种子
        seed_sec()
        from apps.tenant.seed import seed_tenant  # 多租户
        # 多租户：租户主体、租户成员与可售套餐种子
        seed_tenant()
        # ↓↓↓ 需求5：高级可选功能 ↓↓↓
        from apps.wo.seed import seed_wo  # 工单
        # 工单：工单类型、工单主表与流转日志种子
        seed_wo()
        from apps.cal.seed import seed_cal  # 日历日程
        # 日历日程：日程主表与提醒记录种子
        seed_cal()
        from apps.kb.seed import seed_kb  # 知识库
        # 知识库：分类树与文档种子
        seed_kb()
        from apps.scene3d.seed import seed_scene3d  # 3D 可视化
        # 3D 可视化：场景、设备点位等 13 张表及样例数据种子
        seed_scene3d()
        self.stdout.write(self.style.SUCCESS('初始化完成！默认账号 admin / 123456'))  # 收尾提示

    # 建表脚本执行工具：读文件 → 过滤注释行 → 按分号拆分 → 逐条执行
    def exec_sql_file(self, path):
        """读取 SQL 脚本，去掉注释行后按分号逐条执行。"""
        # 以 UTF-8 读取脚本：文件中包含中文表注释，必须显式指定编码
        with open(path, encoding='utf-8') as f:
            raw_sql = f.read()  # 一次性读入，脚本体积较小
        # 去掉注释行后按分号切分
        # 丢弃以 -- 开头的整行注释，避免把注释文本当作 SQL 发送给 MySQL
        lines = [line for line in raw_sql.splitlines()
                 if not line.strip().startswith('--')]  # 跳过 -- 注释行，避免被当成语句执行
        statements = [s.strip() for s in '\n'.join(lines).split(';') if s.strip()]  # 按分号拆分并丢弃空语句
        # 复用 Django 连接执行：与后续种子数据写入保持同一套连接配置
        with connection.cursor() as cursor:
            # 逐条顺序执行：脚本内建表语句之间没有外键依赖，无需拆分批次
            for sql in statements:
                cursor.execute(sql)  # 顺序执行，建表语句之间无外键依赖

    # 菜单初始化：写入 sys_menu 菜单/按钮，并把全部菜单授权给内置超级管理员角色
    def init_menus(self):
        """按 MENUS/BUTTONS 写入菜单与按钮，并授予超级管理员全部权限。"""
        from datetime import datetime  # 局部导入，用于生成创建时间字符串

        # 幂等探测：只要存在任意一条未删除菜单，即认为菜单已初始化过
        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM sys_menu WHERE is_deleted = 0 LIMIT 1")  # 探测是否已有菜单数据
            # 已初始化则直接返回；确实需要重建时使用 --force-menus
            if cursor.fetchone():
                self.stdout.write('菜单已存在，跳过初始化（可加 --force-menus 重建）')  # 幂等保护，避免重复插入
                return  # 已有数据直接结束

        # 内部插入函数：封装雪花主键生成与固定审计字段，供菜单行和按钮行复用
        def insert(parent_id, menu_name, path, component, perms, menu_type, icon, order):
            """插入单条菜单/按钮并返回雪花主键，供子级挂载使用。"""
            from common.snowflake import next_id  # 局部导入雪花算法，与全站主键策略保持一致
            menu_id = next_id()  # 雪花 ID 需应用侧生成，表结构不含 AUTO_INCREMENT
            # 每次插入使用独立游标，函数返回时即释放，避免游标长期占用
            with connection.cursor() as cursor:
                # 菜单主表插入：parent_id 决定层级，menu_type 区分 M 目录 / C 页面 / F 按钮
                cursor.execute(
                    "INSERT INTO sys_menu (id, parent_id, menu_name, path, component, perms, "
                    "menu_type, icon, order_num, visible, status, create_by, create_time, is_deleted) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, '0', '0', 'admin', %s, 0)",
                    # 参数列表必须与上方占位符一一对应；create_time 统一为 DATETIME 文本
                    [menu_id, parent_id, menu_name, path, component, perms, menu_type, icon,
                     order, datetime.now().strftime('%Y-%m-%d %H:%M:%S')])  # 参数化写入，时间取本地当前值
            return menu_id  # 直接返回已生成的主键，无需再查 LAST_INSERT_ID

        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # 预留批次时间（当前未使用）
        menu_ids = {}  # key -> 菜单 id，用于解析父子关系
        # 遍历 MENUS：列表顺序保证父级先插入，子级才能取到已生成的 parent_id
        for parent_key, key, name, path, component, perms, mtype, icon, order in MENUS:
            parent_id = menu_ids.get(parent_key, 0) if parent_key else 0  # 无父级时作为顶级菜单
            menu_ids[key] = insert(parent_id, name, path, component, perms, mtype, icon, order)  # 先插菜单拿 id
            # 为当前菜单追加按钮权限行：类型 F，无路由、无组件、无图标
            for btn_name, btn_perms in BUTTONS.get(key, []):
                insert(menu_ids[key], btn_name, '', '', btn_perms, 'F', '', 0)  # 按钮行：类型 F，无路由与图标

        # 全部菜单授予超级管理员角色
        with connection.cursor() as cursor:
            # INSERT IGNORE 依赖关系表唯一键，重复执行不会产生重复授权也不会报错
            cursor.execute("INSERT IGNORE INTO sys_role_menu (role_id, menu_id) "
                           "SELECT 1, id FROM sys_menu")  # 角色 1 为内置超管，INSERT IGNORE 保证可重复执行
        self.stdout.write(f'菜单初始化完成，共 {len(menu_ids)} 个菜单 + 按钮权限')  # 统计菜单数量
