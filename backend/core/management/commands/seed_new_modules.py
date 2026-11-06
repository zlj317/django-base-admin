# ----------------------------------------------------------------------------
# 演示数据填充命令 seed_new_modules（入口：python manage.py seed_new_modules）
# 用途：为需求4/5/6 新增模块批量写入演示数据，便于前端页面开箱即有内容；
#       全部使用 INSERT IGNORE 且字段值固定，天然幂等，可以反复执行。
# 调用：在 backend 目录执行 `python manage.py seed_new_modules`；
#       init_db 在菜单初始化后也会逐模块调用同名的 seed() 函数。
#
# 依赖表（由 docs/new_features_init.sql 等建表脚本创建）：
#   sys_no_rule、imp_template / imp_template_column、print_template、
#   backup_record / backup_strategy、sys_data_permission / sys_role_data_permission、
#   desensitize_rule、monitor_alarm_rule / monitor_alarm_record、
#   sys_ip_control / sys_login_attempt / sys_rate_limit、
#   sys_tenant / sys_tenant_user / sys_tenant_package、
#   work_order_type / work_order / work_order_log、
#   cal_schedule / cal_reminder、kb_category / kb_document
# 注意：模板/角色/工单等关联字段写的是固定 id，依赖首次插入的自增顺序，
#       因此应在空表或已知数据状态下执行，否则演示数据可能关联错位。
# ----------------------------------------------------------------------------
# 命令模块：为需求4/5/6新增的功能模块批量填充演示数据，可重复执行（INSERT IGNORE 保证幂等）。
"""为需求4/5/6新增功能模块批量填充演示数据。幂等：已存在则跳过。"""
from datetime import datetime, timedelta  # datetime 生成审计时间，timedelta 构造工单/日程的相对时间

from django.core.management.base import BaseCommand  # 管理命令基类，提供 stdout 与 style 输出
from django.db import connection  # 直接复用 Django 连接执行原生 SQL，避免为演示表维护模型


now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # 模块加载时取一次当前时间，各 seed 函数统一作为审计时间


# 通用批量写入工具：统一补齐雪花主键、拼装参数化 SQL，供下方各 seed 函数复用
def batch_insert(table, columns, rows):
    """批量 INSERT，主键由雪花算法生成，列名加反引号避免保留字冲突。"""
    from common.snowflake import next_id  # 主键统一由后端生成，不依赖数据库自增
    all_columns = ['id'] + list(columns)  # 首列固定为主键 id，其余为传入的业务列
    placeholders = ', '.join(['%s'] * len(all_columns))  # 生成与列数相等的占位符，避免拼接值导致 SQL 注入
    cols = ', '.join([f'`{c}`' for c in all_columns])  # 列名加反引号，规避 order/status 等 MySQL 保留字冲突
    sql = f"INSERT IGNORE INTO `{table}` ({cols}) VALUES ({placeholders})"  # 表名由内部常量传入，IGNORE 用于重复执行时跳过
    with connection.cursor() as cur:  # 复用项目连接，游标用完后自动关闭
        for row in rows:  # 逐行执行，便于单行失败时定位是哪条演示数据
            cur.execute(sql, [next_id()] + list(row))  # 每行实时生成雪花 ID，参数化传入业务字段


# 管理命令类：命令名由模块文件名决定，继承 BaseCommand 后由 manage.py 自动扫描
class Command(BaseCommand):
    # 管理命令类：python manage.py seed_new_modules 的入口，负责按模块顺序调度各 seed 函数
    help = '为新增模块填充演示数据'  # manage.py help 中展示的一行说明

    # 命令入口：本命令无自定义参数，只按模块顺序调度各 seed 函数
    def handle(self, *args, **options):
        # 命令主流程：依次写入各模块演示数据，每个 seed 函数内部均保证幂等
        self.stdout.write('开始填充演示数据...')  # 开始提示，方便观察长任务的执行进度
        seed_no()  # 编码规则 sys_no_rule
        seed_imprint()  # 导入模板 / 打印模板
        seed_backup()  # 数据备份记录与策略
        seed_dp()  # 数据权限与角色授权
        seed_dsm()  # 脱敏规则
        seed_mon()  # 监控告警规则与告警记录
        seed_sec()  # IP 管控 / 登录尝试 / 接口限流
        seed_tenant()  # 多租户、租户成员与套餐
        seed_wo()  # 工单类型、工单与流转日志
        seed_cal()  # 日历日程与提醒
        seed_kb()  # 知识库分类与文档
        self.stdout.write(self.style.SUCCESS('全部演示数据填充完成'))  # 全部成功时输出绿色完成提示


# 编码规则演示数据：覆盖按日/按月/按年重置与不重置四种策略，用于验证编号生成配置
def seed_no():
    base = ('admin', now, 'admin', now, 0)  # 公共审计字段：创建人/创建时间/更新人/更新时间/逻辑删除
    # 编码规则清单：规则键/名称/前缀/日期格式/序号位数/当前序号/步长/分隔符/重置方式/重置时间/状态/备注
    rows = [
        # 订单编号：按天重置，前缀 SO，日期 8 位 + 流水 6 位
        ('order_no', '订单编号', 'SO', 'YYYYMMDD', 6, 0, 1, '', 'day', None, 1, '订单主表编号') + base,
        # 发货单号：按月重置，前缀 DH，分隔符为 -
        ('delivery_no', '发货单号', 'DH', 'YYYYMM', 5, 0, 1, '-', 'month', None, 1, '发货单编号') + base,
        # 合同编号：按年重置，前缀 HT，分隔符为 /
        ('contract_no', '合同编号', 'HT', 'YYYY', 4, 0, 1, '/', 'year', None, 1, '销售合同编号') + base,
        # 发票编号：不重置，流水持续递增
        ('invoice_no', '发票编号', 'FP', 'YYYYMMDD', 5, 0, 1, '', 'none', None, 1, '发票号') + base,
        # 工单编号：按天重置，格式与 work_order.order_no 保持一致
        ('ticket_no', '工单编号', 'WD', 'YYYYMMDD', 4, 0, 1, '', 'day', None, 1, '客服工单编号') + base,
    ]
    # 写入编码规则表：rows 元组顺序已与 columns 对齐，由 batch_insert 统一补主键
    batch_insert('sys_no_rule', ['rule_key', 'rule_name', 'prefix', 'date_format', 'seq_length', 'seq_current', 'step', 'separator', 'reset_type', 'reset_time', 'status', 'remark', 'create_by', 'create_time', 'update_by', 'update_time', 'is_deleted'], rows)
    print('  sys_no_rule OK')  # 输出该模块执行成功，便于按顺序核对日志


# 导入模板与打印模板演示数据：含模板主表、导入列配置与三套打印模板
def seed_imprint():
    base = ('admin', now, 'admin', now, 0)  # 统一审计字段，供下方三类模板数据复用
    # 导入模板主表：table_name 指向导入落库的目标表，file_type 限定为 xlsx
    batch_insert('imp_template', ['template_name', 'template_key', 'table_name', 'file_type', 'status', 'remark', 'create_by', 'create_time', 'update_by', 'update_time', 'is_deleted'], [
        # 员工信息导入模板：目标表 sys_user
        ('员工信息导入', 'emp_import', 'sys_user', 'xlsx', 1, '批量导入员工') + base,
        # 商品清单导入模板：目标表 product
        ('商品清单导入', 'product_import', 'product', 'xlsx', 1, '批量导入商品') + base,
        # 客户信息导入模板：目标表 customer
        ('客户信息导入', 'customer_import', 'customer', 'xlsx', 1, '批量导入客户') + base,
    ])
    # 导入模板列配置：template_id 对应上面三条模板，声明表头、类型与必填校验规则
    batch_insert('imp_template_column', ['template_id', 'column_name', 'column_header', 'is_required', 'data_type', 'max_length', 'sort', 'is_deleted'], [
        # 用户名列：必填、字符串、最长 64 字符，排序第 1
        (1, 'username', '用户名', 1, 'string', 64, 1, 0),
        # 姓名列：必填，排序第 2
        (1, 'nickname', '姓名', 1, 'string', 64, 2, 0),
        # 手机号列：非必填，最长 15 位（预留国家码）
        (1, 'phone', '手机号', 0, 'string', 15, 3, 0),
        # 商品名称列：归属模板 2，必填
        (2, 'product_name', '商品名称', 1, 'string', 200, 1, 0),
        # 单价列：数值型，最大 12 位，支持两位小数
        (2, 'price', '单价', 1, 'number', 12, 2, 0),
        # 客户名称列：归属模板 3，必填
        (3, 'customer_name', '客户名称', 1, 'string', 200, 1, 0),
    ])
    # 打印模板 HTML：用 {{data}} 占位，运行时由后端替换成实际业务字段
    html = '<div style="padding:20px;font-family:SimSun;"><h2>订单打印</h2><table border="1"><thead><tr><th>编号</th><th>名称</th></tr></thead><tbody><tr><td colspan="2">{{data}}</td></tr></tbody></table></div>'
    # 打印模板主表：订单/发货单/合同三套模板，区分 A4/A5 纸张并标记默认模板
    batch_insert('print_template', ['template_name', 'template_key', 'biz_type', 'html_content', 'paper_size', 'is_default', 'status', 'remark', 'create_by', 'create_time', 'update_by', 'update_time', 'is_deleted'], [
        # 订单打印模板：A4 纸张、默认模板，业务类型 order
        ('订单打印模板', 'order_print', 'order', html, 'A4', 1, 1, '标准订单打印') + base,
        # 发货单打印模板：A5 纸张、非默认模板
        ('发货单打印模板', 'delivery_print', 'delivery', html, 'A5', 0, 1, '发货单模板') + base,
        # 合同打印模板：A4 纸张、非默认模板
        ('合同打印模板', 'contract_print', 'contract', html, 'A4', 0, 1, '合同模板') + base,
    ])
    print('  imprint OK')  # 输出该模块执行成功


# 数据备份演示数据：既包含历史备份记录，也包含自动备份策略（cron 表达式）
def seed_backup():
    base = ('admin', now, 'admin', now, 0)  # 两个备份表共用的审计字段
    # 历史备份记录：backup_type 为 auto/manual，backup_status=1 表示成功
    batch_insert('backup_record', ['backup_name', 'backup_type', 'db_name', 'encrypt_flag', 'backup_status', 'backup_time', 'remark', 'create_by', 'create_time', 'update_by', 'update_time', 'is_deleted'], [
        # 每日自动备份：未加密，凌晨 2 点执行成功
        ('全量数据备份_20261101', 'auto', 'gen_admin', 0, 1, '2026-11-01 02:00:00', '每日自动备份') + base,
        # 升级前手动备份：已加密，用于保留升级现场
        ('紧急数据备份_20261102', 'manual', 'gen_admin', 1, 1, '2026-11-02 15:30:00', '升级前手动备份') + base,
        # 月度归档备份：已加密，每月 1 号归档
        ('月度归档备份_20261103', 'auto', 'gen_admin', 1, 1, '2026-11-03 00:10:00', '每月归档备份') + base,
    ])
    # 备份策略：用 cron 表达式描述每日/每周/每月的执行计划，并设置保留天数与加密标记
    batch_insert('backup_strategy', ['strategy_name', 'cron_expr', 'keep_days', 'encrypt_flag', 'status', 'remark', 'create_by', 'create_time', 'update_by', 'update_time', 'is_deleted'], [
        # 每日全量：cron 0 0 2 * * ? 表示每天 02:00，保留 7 天
        ('每日全量备份', '0 0 2 * * ?', 7, 0, 1, '每天凌晨2点') + base,
        # 每周增量：Quartz cron 表示每周一 03:00，保留 30 天
        ('每周增量备份', '0 0 3 ? * MON', 30, 1, 1, '每周一凌晨3点') + base,
        # 每月归档：每月 1 号 00:00 执行，保留 365 天
        ('每月归档备份', '0 0 1 1 * ?', 365, 1, 1, '每月1号归档') + base,
    ])
    print('  backup OK')  # 输出该模块执行成功


# 数据权限演示数据：内置全部/本部门及下级/仅本人/指定角色四种常见数据范围
def seed_dp():
    base = ('admin', now, 'admin', now, 0)  # 数据权限表的公共审计字段
    # 数据权限范围：permission_type 决定过滤策略，scope_value 存部门/角色等参数
    batch_insert('sys_data_permission', ['permission_name', 'permission_type', 'scope_value', 'sort', 'status', 'remark', 'create_by', 'create_time', 'update_by', 'update_time', 'is_deleted'], [
        # 全部数据权限：不做过滤，适用于超管或全局统计口径
        ('全部数据权限', 'all', None, 1, 1, '可查看所有数据') + base,
        # 本部门及下级：scope_value 声明"本部门 + 子部门"
        ('本部门及下级', 'dept', 'self,children', 2, 1, '可查看本部门及下级部门数据') + base,
        # 仅本人：按数据创建人过滤
        ('仅本人数据', 'self', None, 3, 1, '仅可查看自己创建的数据') + base,
        # 指定角色：scope_value 列出可见的角色 id
        ('指定角色可见', 'role', '1,2', 4, 1, '仅角色1和2可见') + base,
    ])
    # 角色与数据权限的授权关系：为角色 1/2/3 分配不同数据范围，演示最小授权模型
    batch_insert('sys_role_data_permission', ['role_id', 'permission_id', 'create_time'], [
        # 角色授权关系：角色 1/2 可见部门数据，角色 3 仅本人，角色 1 另含全部数据
        (1, 1, now), (1, 2, now), (2, 2, now), (3, 3, now),
    ])
    print('  dp OK')  # 输出该模块执行成功


# 脱敏规则演示数据：手机号、身份证、银行卡、邮箱、姓名五类常用敏感字段的掩码配置
def seed_dsm():
    base = ('admin', now, 'admin', now, 0)  # 脱敏规则表的公共审计字段
    # 脱敏规则：mask_style 为替换字符，regular 预留自定义正则（演示数据留空）
    batch_insert('desensitize_rule', ['rule_name', 'rule_type', 'mask_style', 'regular', 'status', 'remark', 'create_by', 'create_time', 'update_by', 'update_time', 'is_deleted'], [
        # 手机号：中间四位替换为 ****
        ('手机号脱敏', 'phone', '****', None, 1, '138****1234') + base,
        # 身份证：保留前 3 位与后 4 位，中间 8 位掩码
        ('身份证号脱敏', 'idcard', '********', None, 1, '只显示前3后4位') + base,
        # 银行卡：仅保留后 4 位
        ('银行卡号脱敏', 'bank', '****', None, 1, '只显示后4位') + base,
        # 邮箱：保留首字符与域名部分
        ('邮箱脱敏', 'email', '****', None, 1, '只显示首字符和域名') + base,
        # 姓名：保留姓氏，名字逐字替换为 *
        ('姓名脱敏', 'custom', '*', None, 1, '张*、李**') + base,
    ])
    print('  dsm OK')  # 输出该模块执行成功


# 监控告警演示数据：包含 5 条告警规则与对应的历史告警记录，覆盖服务/磁盘/数据库/接口/任务
def seed_mon():
    base = ('admin', now, 'admin', now, 0)  # 告警规则表的公共审计字段
    # 告警规则：monitor_type 区分监控对象，channel 为通知渠道（逗号分隔多选）
    batch_insert('monitor_alarm_rule', ['rule_name', 'monitor_type', 'compare_op', 'threshold', 'alarm_level', 'channel', 'status', 'remark', 'create_by', 'create_time', 'update_by', 'update_time', 'is_deleted'], [
        # 服务监控：CPU 使用率 > 85% 触发中级告警
        ('CPU 使用率超阈值', 'service', '>', '85', 2, 'site', 1, 'CPU 连续 3 分钟超 85%') + base,
        # 磁盘监控：使用率 > 90% 触发严重告警，站内信 + 邮件通知
        ('磁盘空间不足', 'disk', '>', '90', 3, 'site,email', 1, '磁盘使用超 90% 严重告警') + base,
        # 数据库监控：连接数 > 80% 触发中级告警
        ('数据库连接数过高', 'db', '>', '80', 2, 'site', 1, '数据库连接数超 80%') + base,
        # 接口监控：平均响应 > 3000ms 触发提示级告警
        ('接口响应超时', 'api', '>', '3000', 1, 'site', 1, '接口平均响应超 3 秒提示') + base,
        # 定时任务监控：执行失败（==1）触发中级告警
        ('定时任务失败', 'task', '==', '1', 2, 'site', 1, '定时任务执行失败告警') + base,
    ])
    # 历史告警记录：rule_id 关联上面的规则，handle_status 区分已处理/未处理，供列表页展示
    batch_insert('monitor_alarm_record', ['rule_id', 'alarm_level', 'alarm_content', 'alarm_time', 'handle_status', 'create_time'], [
        # CPU 告警记录：已处理，供列表页展示处理状态
        (1, 2, 'CPU 使用率达到 92%，持续 5 分钟', '2026-11-03 14:25:00', 1, '2026-11-03 14:25:00'),
        # 磁盘告警记录：未处理，用于演示待办提醒
        (2, 3, '磁盘 /data 使用 95%，剩余空间不足', '2026-11-02 08:10:00', 0, '2026-11-02 08:10:00'),
        # 接口超时记录：提示级、未处理
        (4, 1, '接口平均响应 3.5s', '2026-11-04 09:00:00', 0, '2026-11-04 09:00:00'),
        # 定时任务失败记录：已处理
        (5, 2, '每日数据备份定时任务执行失败', '2026-11-01 02:00:05', 1, '2026-11-01 02:00:05'),
    ])
    print('  mon OK')  # 输出该模块执行成功


# 安全策略演示数据：IP 黑白名单、登录尝试记录与接口限流规则
def seed_sec():
    base = ('admin', now, 'admin', now, 0)  # IP 管控与限流表共用的审计字段
    # IP 管控：black 拒绝访问 / white 放行，expire_time 为空表示永久生效
    batch_insert('sys_ip_control', ['ip', 'control_type', 'reason', 'status', 'expire_time', 'create_by', 'create_time', 'update_by', 'update_time', 'is_deleted'], [
        # 连续登录失败来源，临时封禁到 11-10
        ('192.168.1.100', 'black', '连续多次登录失败，已临时封禁', 1, '2026-11-10 00:00:00') + base,
        # 异常高频请求来源，封禁到 11-15
        ('10.0.0.200', 'black', '异常高频请求', 1, '2026-11-15 00:00:00') + base,
        # 内网服务器固定 IP 加入白名单
        ('172.16.0.1', 'white', '内网服务器固定 IP', 1, None) + base,
        # 本机回环地址白名单，避免本地调试被拦截
        ('127.0.0.1', 'white', '本机白名单', 1, None) + base,
    ])
    # 登录尝试记录：用成功/失败标记支撑安全审计与暴力破解识别
    batch_insert('sys_login_attempt', ['username', 'ip', 'attempt_time', 'success_flag', 'create_time'], [
        # admin 第一次登录失败：用于验证暴力破解识别
        ('admin', '192.168.1.100', '2026-11-04 10:30:00', 0, '2026-11-04 10:30:00'),
        # admin 第二次失败（间隔 15 秒）
        ('admin', '192.168.1.100', '2026-11-04 10:30:15', 0, '2026-11-04 10:30:15'),
        # user1 登录成功
        ('user1', '10.0.0.50', '2026-11-04 09:15:00', 1, '2026-11-04 09:15:00'),
        # user2 登录成功
        ('user2', '10.0.0.51', '2026-11-04 09:20:00', 1, '2026-11-04 09:20:00'),
    ])
    # 接口限流规则：按时间窗口与最大次数限制登录、短信、导出等高风险接口
    batch_insert('sys_rate_limit', ['rule_name', 'limit_url', 'period_sec', 'max_count', 'status', 'create_by', 'create_time', 'update_by', 'update_time', 'is_deleted'], [
        # 登录接口：60 秒窗口内最多 5 次
        ('登录接口限流', '/api/auth/login', 60, 5, 1) + base,
        # 消息接口：60 秒内最多 10 次，路径使用通配符
        ('短信发送限流', '/api/msg/**', 60, 10, 1) + base,
        # 导出接口：1 小时内最多 20 次，防止批量导出拖垮服务
        ('导出接口限流', '/api/**/export', 3600, 20, 1) + base,
    ])
    print('  sec OK')  # 输出该模块执行成功


# 多租户演示数据：包含租户主体、租户成员关系与可售套餐，覆盖分公司/研发中心/合作伙伴场景
def seed_tenant():
    base = ('admin', now, 'admin', now, 0)  # 租户表与套餐表共用的审计字段
    # 租户主体：status=1 启用，配额含最大用户数与存储空间（MB）
    batch_insert('sys_tenant', ['tenant_name', 'tenant_code', 'status', 'expire_time', 'max_user_count', 'max_storage_mb', 'remark', 'create_by', 'create_time', 'update_by', 'update_time', 'is_deleted'], [
        # 北京分公司：200 用户 / 10GB，有效期至 2027 年底
        ('北京分公司', 'bj_branch', 1, '2027-12-31 23:59:59', 200, 10240, '北京地区分支机构') + base,
        # 上海分公司：100 用户 / 5GB
        ('上海分公司', 'sh_branch', 1, '2027-06-30 23:59:59', 100, 5120, '上海地区分支机构') + base,
        # 深圳研发中心：300 用户 / 20GB
        ('深圳研发中心', 'sz_rdc', 1, '2028-03-31 23:59:59', 300, 20480, '深圳研发中心') + base,
        # 合作伙伴 A：50 用户 / 2GB，外部租户
        ('合作伙伴A公司', 'partner_a', 1, '2026-12-31 23:59:59', 50, 2048, '合作方外部租户') + base,
    ])
    # 租户成员关系：标记每名用户在所属租户内是否为租户管理员，支撑租户内权限隔离
    batch_insert('sys_tenant_user', ['tenant_id', 'user_id', 'is_tenant_admin', 'join_time', 'create_time'], [
        # 成员关系：1/3/4 号用户分别是所属租户的管理员
        (1, 1, 1, now, now), (1, 2, 0, now, now), (2, 3, 1, now, now), (3, 4, 1, now, now),
    ])
    # 租户套餐：按用户数/存储空间/价格划分标准版、专业版、企业版三档
    batch_insert('sys_tenant_package', ['package_name', 'max_user_count', 'max_storage_mb', 'price', 'status', 'remark', 'create_time', 'update_time', 'is_deleted'], [
        # 标准版：50 用户 / 2GB / 9999 元
        ('标准版-50用户', 50, 2048, 9999.00, 1, '适用于中小型团队', now, now, 0),
        # 专业版：200 用户 / 10GB / 29999 元
        ('专业版-200用户', 200, 10240, 29999.00, 1, '适用于成长型企业', now, now, 0),
        # 企业版：500 用户 / 50GB / 89999 元
        ('企业版-500用户', 500, 51200, 89999.00, 1, '适用于大型企业', now, now, 0),
    ])
    print('  tenant OK')  # 输出该模块执行成功


# 工单演示数据：5 个工单类型、10 条不同状态的工单，以及按规则生成的流转日志
def seed_wo():
    base = ('admin', now, 'admin', now, 0)  # 工单类型与工单表共用的审计字段
    # 工单类型：sort 控制下拉顺序，5 类覆盖反馈/建议/权限/数据/咨询
    batch_insert('work_order_type', ['type_name', 'sort', 'status', 'remark', 'create_by', 'create_time', 'update_by', 'update_time', 'is_deleted'], [
        # Bug 反馈类工单
        ('Bug 反馈', 1, 1, '系统 Bug 反馈工单') + base,
        # 功能建议类工单
        ('功能建议', 2, 1, '新功能需求工单') + base,
        # 账号权限类工单
        ('账号权限', 3, 1, '账号/角色/权限相关') + base,
        # 数据问题类工单
        ('数据问题', 4, 1, '数据修正/导入相关') + base,
        # 系统咨询类工单
        ('系统咨询', 5, 1, '使用咨询类工单') + base,
    ])
    # 工单标题池：按业务场景预置，循环取用即可得到贴近真实的演示列表
    titles = [
        # 下标 0：Safari 浏览器样式问题
        '登录页面在 Safari 浏览器样式错乱',
        # 下标 1：批量导出 Excel 需求
        '希望增加批量导出 Excel 功能',
        # 下标 2：备份模块权限申请
        '申请开通数据备份模块权限',
        # 下标 3：编号规则前缀调整
        '订单编号规则需要修改前缀',
        # 下标 4：定时任务配置咨询
        '如何配置定时任务执行时间？',
        # 下标 5：报表查询性能问题
        '报表生成记录查询很慢',
        # 下标 6：大屏分享链接过期
        '大屏分享链接过期怎么重新生成？',
        # 下标 7：员工账号被自动禁用
        '新增员工账号自动禁用问题',
        # 下标 8：大文件上传偶发失败
        '上传大文件时偶尔失败',
        # 下标 9：字典批量导入缺失
        '字典管理缺少批量导入功能',
    ]
    order_types = [1, 2, 3, 4, 5, 1, 2, 3, 4, 5]  # 与标题池对应，轮流分配到 5 种工单类型
    statuses = [0, 0, 1, 1, 2, 2, 3, 0, 1, 2]  # 覆盖待处理/处理中/已完成/已关闭等多种状态
    priorities = [2, 3, 1, 3, 2, 3, 1, 2, 3, 2]  # 优先级混合分布，便于验证排序与筛选
    base_time = datetime.now()  # 以当前时间为基准，向前推算每条工单的期望完成时间
    rows = []  # 先收集全部工单行，再一次性交给 batch_insert
    for i in range(10):  # 循环生成 10 条工单，编号按 WD2026110xxx 规则递增
        # 组装工单行：(编号, 类型, 标题, 内容, 附件, 优先级, 状态, 创建人, 处理人, 期望完成时间, 关闭时间)
        rows.append((
            f'WD2026110{i+1:03d}', order_types[i], titles[i],
            '详细描述内容示例', '', priorities[i], statuses[i],
            1, 2,
            (base_time - timedelta(hours=(i + 1) * 2)).strftime('%Y-%m-%d %H:%M:%S'),
            None if statuses[i] != 3 else (base_time - timedelta(hours=i + 1)).strftime('%Y-%m-%d %H:%M:%S')
        ) + base)
    # 写入工单主表：creator_id 固定为 1、assignee_id 固定为 2，对应 admin 与处理人账号
    batch_insert('work_order', ['order_no', 'order_type_id', 'title', 'content', 'attachment_ids', 'priority', 'status', 'creator_id', 'assignee_id', 'expect_time', 'close_time', 'create_by', 'create_time', 'update_by', 'update_time', 'is_deleted'], rows)
    log_rows = []  # 收集工单流转日志，每张工单至少有一条创建记录
    for i in range(1, 11):  # 工单主键从 1 到 10，与上面插入的顺序一致
        log_rows.append((i, 1, 'create', '工单创建', now))  # 创建动作固定由用户 1 发起
        if i % 3 == 0:  # 每 3 张工单模拟一次指派动作
            log_rows.append((i, 2, 'assign', '已指派给处理人', now))  # 指派动作由处理人 2 执行
        if i % 4 == 0:  # 每 4 张工单模拟一次解决动作，制造不同处理进度
            log_rows.append((i, 2, 'solve', '问题已定位并修复', now))  # 解决动作记录处理说明
    # 写入流转日志表：order_id 关联工单主键，用于详情页展示时间线
    batch_insert('work_order_log', ['order_id', 'operator_id', 'action', 'comment', 'create_time'], log_rows)
    print('  wo OK')  # 输出该模块执行成功


# 日历日程演示数据：以今天为中心前后各若干天的日程，并为部分日程补充提醒记录
def seed_cal():
    rows = []  # 收集日程行数据
    today = datetime.now()  # 以当前时间为基准，保证演示日程落在日历可见范围内
    base = ('admin', now, 'admin', now, 0)  # 日程表的公共审计字段
    for i in range(-3, 8):  # 生成过去 3 天到未来 7 天共 11 条日程，覆盖月视图前后翻页
        dt = today + timedelta(days=i)  # 按天偏移得到每条日程的日期
        # 组装日程行：(标题, 内容, 开始时间, 结束时间, 全天标记, 负责人, 提前提醒分钟, 提醒状态, 共享配置, 状态)
        rows.append((
            f'日程示例{i+1}', '简要描述',
            f'{dt.strftime("%Y-%m-%d")} 09:00:00', f'{dt.strftime("%Y-%m-%d")} 10:00:00',
            0, 1, 15, 0, None, 0
        ) + base)
    # 写入日程主表：owner_id 为 1，提醒提前 15 分钟，shared_json 留空表示未共享
    batch_insert('cal_schedule', ['title', 'content', 'start_time', 'end_time', 'all_day', 'owner_id', 'reminder_minutes', 'remind_status', 'shared_json', 'status', 'create_by', 'create_time', 'update_by', 'update_time', 'is_deleted'], rows)

    # 日程提醒：仅在表为空时补充演示数据，保证重复执行不产生脏数据
    with connection.cursor() as cur:  # 直接查原生 SQL，避免为演示脚本引入模型依赖
        cur.execute('SELECT COUNT(*) FROM cal_reminder')  # 统计现有提醒数量，作为幂等判断依据
        if cur.fetchone()[0] == 0:  # 表为空时才写入，重复执行不会产生重复提醒
            cur.execute("SELECT id FROM cal_schedule WHERE is_deleted=0 ORDER BY id LIMIT 3")  # 取前 3 条日程作为提醒对象
            schedule_ids = [r[0] for r in cur.fetchall()]  # 提取主键列表
            remind_rows = []  # 收集提醒行数据
            for index, schedule_id in enumerate(schedule_ids):  # 为每条日程生成一条提醒
                remind_time = (today + timedelta(days=index)).strftime('%Y-%m-%d 08:30:00')  # 提醒时间设为对应日期的 08:30
                remind_rows.append((schedule_id, 1, remind_time, index % 2, now))  # 用 index 奇偶交替提醒状态
            batch_insert('cal_reminder', ['schedule_id', 'remind_user_id', 'remind_time', 'remind_status', 'create_time'], remind_rows)  # 批量写入提醒
    print('  cal OK')  # 输出该模块执行成功


# 知识库演示数据：两级分类树 + 8 篇文档，覆盖产品/开发/运维/FAQ 等常见知识库栏目
def seed_kb():
    base = ('admin', now, 'admin', now, 0)  # 分类与文档表共用的审计字段
    # 知识库分类：parent_id=0 为一级分类，其余挂在一级分类下形成两级树
    batch_insert('kb_category', ['category_name', 'parent_id', 'sort', 'status', 'remark', 'create_by', 'create_time', 'update_by', 'update_time', 'is_deleted'], [
        # 一级分类：产品手册
        ('产品手册', 0, 1, 1, '产品使用相关') + base,
        # 一级分类：开发文档
        ('开发文档', 0, 2, 1, '开发对接') + base,
        # 一级分类：运维手册
        ('运维手册', 0, 3, 1, '部署运维') + base,
        # 一级分类：FAQ
        ('FAQ', 0, 4, 1, '常见问题') + base,
        # 产品手册下的二级分类：快速上手
        ('快速上手', 1, 1, 1, None) + base,
        # 产品手册下的二级分类：功能详解
        ('功能详解', 1, 2, 1, None) + base,
        # 开发文档下的二级分类：API 文档
        ('API 文档', 2, 1, 1, None) + base,
        # 开发文档下的二级分类：数据库设计
        ('数据库设计', 2, 2, 1, None) + base,
    ])
    # 文档示例：category_id 指向上面的一级/二级分类，作者固定为 1 号用户
    docs = [
        # 快速上手指南：归入二级分类 5，作者 1，阅读量按序号递增
        (5, '快速上手-5 分钟入门 django-base-admin', '快速上手指南内容...', '快速入门,新手', 1),
        # 工作流模块详解：标签含工作流/审批/BPMN
        (6, '工作流审批模块功能详解', '工作流模块详解...', '工作流,审批,BPMN', 1),
        # RESTful API 规范：标签 API/规范
        (7, 'RESTful API 接口规范', 'API 规范说明...', 'API,规范,RESTful', 1),
        # 统一响应结构与错误码说明
        (7, '统一响应结构与错误码', '错误码说明...', '错误码,响应', 1),
        # 数据库表结构总览：归入数据库设计分类
        (8, '数据库表结构总览', '数据库结构...', '数据库,表结构', 1),
        # 系统部署与运维手册：归入运维手册分类
        (3, '系统部署与运维手册', '部署运维...', '部署,运维', 1),
        # admin 密码重置方法 FAQ
        (4, '如何重置 admin 密码', '密码重置方法...', '密码,重置,admin', 1),
        # 登录失败排查 FAQ
        (4, '登录失败如何排查', '登录排查...', '登录,排查', 1),
    ]
    doc_rows = []  # 收集文档行数据
    for i, (cat_id, title, content, tags, author) in enumerate(docs, 1):  # 从 1 开始编号，用于生成阅读量与排序
        doc_rows.append((cat_id, title, content, None, tags, author, 'public', None, i * 17, 1, 1) + base)  # 阅读量按序号递增，权限为公开
    # 写入文档表：permission_type=public 表示所有登录用户可见
    batch_insert('kb_document', ['category_id', 'doc_title', 'doc_content', 'file_id', 'tags', 'author_id', 'permission_type', 'role_json', 'read_count', 'version', 'status', 'create_by', 'create_time', 'update_by', 'update_time', 'is_deleted'], doc_rows)
    print('  kb OK')  # 输出该模块执行成功
