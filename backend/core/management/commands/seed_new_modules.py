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


class Command(BaseCommand):
    # 管理命令类：python manage.py seed_new_modules 的入口，负责按模块顺序调度各 seed 函数
    help = '为新增模块填充演示数据'  # manage.py help 中展示的一行说明

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
    rows = [
        ('order_no', '订单编号', 'SO', 'YYYYMMDD', 6, 0, 1, '', 'day', None, 1, '订单主表编号') + base,
        ('delivery_no', '发货单号', 'DH', 'YYYYMM', 5, 0, 1, '-', 'month', None, 1, '发货单编号') + base,
        ('contract_no', '合同编号', 'HT', 'YYYY', 4, 0, 1, '/', 'year', None, 1, '销售合同编号') + base,
        ('invoice_no', '发票编号', 'FP', 'YYYYMMDD', 5, 0, 1, '', 'none', None, 1, '发票号') + base,
        ('ticket_no', '工单编号', 'WD', 'YYYYMMDD', 4, 0, 1, '', 'day', None, 1, '客服工单编号') + base,
    ]
    # 写入编码规则表：rows 元组顺序已与 columns 对齐，由 batch_insert 统一补主键
    batch_insert('sys_no_rule', ['rule_key', 'rule_name', 'prefix', 'date_format', 'seq_length', 'seq_current', 'step', 'separator', 'reset_type', 'reset_time', 'status', 'remark', 'create_by', 'create_time', 'update_by', 'update_time', 'is_deleted'], rows)
    print('  sys_no_rule OK')  # 输出该模块执行成功，便于按顺序核对日志


# 导入模板与打印模板演示数据：含模板主表、导入列配置与三套打印模板
def seed_imprint():
    base = ('admin', now, 'admin', now, 0)  # 统一审计字段，供下方三类模板数据复用
    batch_insert('imp_template', ['template_name', 'template_key', 'table_name', 'file_type', 'status', 'remark', 'create_by', 'create_time', 'update_by', 'update_time', 'is_deleted'], [
        ('员工信息导入', 'emp_import', 'sys_user', 'xlsx', 1, '批量导入员工') + base,
        ('商品清单导入', 'product_import', 'product', 'xlsx', 1, '批量导入商品') + base,
        ('客户信息导入', 'customer_import', 'customer', 'xlsx', 1, '批量导入客户') + base,
    ])
    # 导入模板列配置：template_id 对应上面三条模板，声明表头、类型与必填校验规则
    batch_insert('imp_template_column', ['template_id', 'column_name', 'column_header', 'is_required', 'data_type', 'max_length', 'sort', 'is_deleted'], [
        (1, 'username', '用户名', 1, 'string', 64, 1, 0),
        (1, 'nickname', '姓名', 1, 'string', 64, 2, 0),
        (1, 'phone', '手机号', 0, 'string', 15, 3, 0),
        (2, 'product_name', '商品名称', 1, 'string', 200, 1, 0),
        (2, 'price', '单价', 1, 'number', 12, 2, 0),
        (3, 'customer_name', '客户名称', 1, 'string', 200, 1, 0),
    ])
    # 打印模板 HTML：用 {{data}} 占位，运行时由后端替换成实际业务字段
    html = '<div style="padding:20px;font-family:SimSun;"><h2>订单打印</h2><table border="1"><thead><tr><th>编号</th><th>名称</th></tr></thead><tbody><tr><td colspan="2">{{data}}</td></tr></tbody></table></div>'
    # 打印模板主表：订单/发货单/合同三套模板，区分 A4/A5 纸张并标记默认模板
    batch_insert('print_template', ['template_name', 'template_key', 'biz_type', 'html_content', 'paper_size', 'is_default', 'status', 'remark', 'create_by', 'create_time', 'update_by', 'update_time', 'is_deleted'], [
        ('订单打印模板', 'order_print', 'order', html, 'A4', 1, 1, '标准订单打印') + base,
        ('发货单打印模板', 'delivery_print', 'delivery', html, 'A5', 0, 1, '发货单模板') + base,
        ('合同打印模板', 'contract_print', 'contract', html, 'A4', 0, 1, '合同模板') + base,
    ])
    print('  imprint OK')  # 输出该模块执行成功


# 数据备份演示数据：既包含历史备份记录，也包含自动备份策略（cron 表达式）
def seed_backup():
    base = ('admin', now, 'admin', now, 0)  # 两个备份表共用的审计字段
    batch_insert('backup_record', ['backup_name', 'backup_type', 'db_name', 'encrypt_flag', 'backup_status', 'backup_time', 'remark', 'create_by', 'create_time', 'update_by', 'update_time', 'is_deleted'], [
        ('全量数据备份_20261101', 'auto', 'gen_admin', 0, 1, '2026-11-01 02:00:00', '每日自动备份') + base,
        ('紧急数据备份_20261102', 'manual', 'gen_admin', 1, 1, '2026-11-02 15:30:00', '升级前手动备份') + base,
        ('月度归档备份_20261103', 'auto', 'gen_admin', 1, 1, '2026-11-03 00:10:00', '每月归档备份') + base,
    ])
    # 备份策略：用 cron 表达式描述每日/每周/每月的执行计划，并设置保留天数与加密标记
    batch_insert('backup_strategy', ['strategy_name', 'cron_expr', 'keep_days', 'encrypt_flag', 'status', 'remark', 'create_by', 'create_time', 'update_by', 'update_time', 'is_deleted'], [
        ('每日全量备份', '0 0 2 * * ?', 7, 0, 1, '每天凌晨2点') + base,
        ('每周增量备份', '0 0 3 ? * MON', 30, 1, 1, '每周一凌晨3点') + base,
        ('每月归档备份', '0 0 1 1 * ?', 365, 1, 1, '每月1号归档') + base,
    ])
    print('  backup OK')  # 输出该模块执行成功


# 数据权限演示数据：内置全部/本部门及下级/仅本人/指定角色四种常见数据范围
def seed_dp():
    base = ('admin', now, 'admin', now, 0)  # 数据权限表的公共审计字段
    batch_insert('sys_data_permission', ['permission_name', 'permission_type', 'scope_value', 'sort', 'status', 'remark', 'create_by', 'create_time', 'update_by', 'update_time', 'is_deleted'], [
        ('全部数据权限', 'all', None, 1, 1, '可查看所有数据') + base,
        ('本部门及下级', 'dept', 'self,children', 2, 1, '可查看本部门及下级部门数据') + base,
        ('仅本人数据', 'self', None, 3, 1, '仅可查看自己创建的数据') + base,
        ('指定角色可见', 'role', '1,2', 4, 1, '仅角色1和2可见') + base,
    ])
    # 角色与数据权限的授权关系：为角色 1/2/3 分配不同数据范围，演示最小授权模型
    batch_insert('sys_role_data_permission', ['role_id', 'permission_id', 'create_time'], [
        (1, 1, now), (1, 2, now), (2, 2, now), (3, 3, now),
    ])
    print('  dp OK')  # 输出该模块执行成功


# 脱敏规则演示数据：手机号、身份证、银行卡、邮箱、姓名五类常用敏感字段的掩码配置
def seed_dsm():
    base = ('admin', now, 'admin', now, 0)  # 脱敏规则表的公共审计字段
    batch_insert('desensitize_rule', ['rule_name', 'rule_type', 'mask_style', 'regular', 'status', 'remark', 'create_by', 'create_time', 'update_by', 'update_time', 'is_deleted'], [
        ('手机号脱敏', 'phone', '****', None, 1, '138****1234') + base,
        ('身份证号脱敏', 'idcard', '********', None, 1, '只显示前3后4位') + base,
        ('银行卡号脱敏', 'bank', '****', None, 1, '只显示后4位') + base,
        ('邮箱脱敏', 'email', '****', None, 1, '只显示首字符和域名') + base,
        ('姓名脱敏', 'custom', '*', None, 1, '张*、李**') + base,
    ])
    print('  dsm OK')  # 输出该模块执行成功


# 监控告警演示数据：包含 5 条告警规则与对应的历史告警记录，覆盖服务/磁盘/数据库/接口/任务
def seed_mon():
    base = ('admin', now, 'admin', now, 0)  # 告警规则表的公共审计字段
    batch_insert('monitor_alarm_rule', ['rule_name', 'monitor_type', 'compare_op', 'threshold', 'alarm_level', 'channel', 'status', 'remark', 'create_by', 'create_time', 'update_by', 'update_time', 'is_deleted'], [
        ('CPU 使用率超阈值', 'service', '>', '85', 2, 'site', 1, 'CPU 连续 3 分钟超 85%') + base,
        ('磁盘空间不足', 'disk', '>', '90', 3, 'site,email', 1, '磁盘使用超 90% 严重告警') + base,
        ('数据库连接数过高', 'db', '>', '80', 2, 'site', 1, '数据库连接数超 80%') + base,
        ('接口响应超时', 'api', '>', '3000', 1, 'site', 1, '接口平均响应超 3 秒提示') + base,
        ('定时任务失败', 'task', '==', '1', 2, 'site', 1, '定时任务执行失败告警') + base,
    ])
    # 历史告警记录：rule_id 关联上面的规则，handle_status 区分已处理/未处理，供列表页展示
    batch_insert('monitor_alarm_record', ['rule_id', 'alarm_level', 'alarm_content', 'alarm_time', 'handle_status', 'create_time'], [
        (1, 2, 'CPU 使用率达到 92%，持续 5 分钟', '2026-11-03 14:25:00', 1, '2026-11-03 14:25:00'),
        (2, 3, '磁盘 /data 使用 95%，剩余空间不足', '2026-11-02 08:10:00', 0, '2026-11-02 08:10:00'),
        (4, 1, '接口平均响应 3.5s', '2026-11-04 09:00:00', 0, '2026-11-04 09:00:00'),
        (5, 2, '每日数据备份定时任务执行失败', '2026-11-01 02:00:05', 1, '2026-11-01 02:00:05'),
    ])
    print('  mon OK')  # 输出该模块执行成功


# 安全策略演示数据：IP 黑白名单、登录尝试记录与接口限流规则
def seed_sec():
    base = ('admin', now, 'admin', now, 0)  # IP 管控与限流表共用的审计字段
    batch_insert('sys_ip_control', ['ip', 'control_type', 'reason', 'status', 'expire_time', 'create_by', 'create_time', 'update_by', 'update_time', 'is_deleted'], [
        ('192.168.1.100', 'black', '连续多次登录失败，已临时封禁', 1, '2026-11-10 00:00:00') + base,
        ('10.0.0.200', 'black', '异常高频请求', 1, '2026-11-15 00:00:00') + base,
        ('172.16.0.1', 'white', '内网服务器固定 IP', 1, None) + base,
        ('127.0.0.1', 'white', '本机白名单', 1, None) + base,
    ])
    # 登录尝试记录：用成功/失败标记支撑安全审计与暴力破解识别
    batch_insert('sys_login_attempt', ['username', 'ip', 'attempt_time', 'success_flag', 'create_time'], [
        ('admin', '192.168.1.100', '2026-11-04 10:30:00', 0, '2026-11-04 10:30:00'),
        ('admin', '192.168.1.100', '2026-11-04 10:30:15', 0, '2026-11-04 10:30:15'),
        ('user1', '10.0.0.50', '2026-11-04 09:15:00', 1, '2026-11-04 09:15:00'),
        ('user2', '10.0.0.51', '2026-11-04 09:20:00', 1, '2026-11-04 09:20:00'),
    ])
    # 接口限流规则：按时间窗口与最大次数限制登录、短信、导出等高风险接口
    batch_insert('sys_rate_limit', ['rule_name', 'limit_url', 'period_sec', 'max_count', 'status', 'create_by', 'create_time', 'update_by', 'update_time', 'is_deleted'], [
        ('登录接口限流', '/api/auth/login', 60, 5, 1) + base,
        ('短信发送限流', '/api/msg/**', 60, 10, 1) + base,
        ('导出接口限流', '/api/**/export', 3600, 20, 1) + base,
    ])
    print('  sec OK')  # 输出该模块执行成功


# 多租户演示数据：包含租户主体、租户成员关系与可售套餐，覆盖分公司/研发中心/合作伙伴场景
def seed_tenant():
    base = ('admin', now, 'admin', now, 0)  # 租户表与套餐表共用的审计字段
    batch_insert('sys_tenant', ['tenant_name', 'tenant_code', 'status', 'expire_time', 'max_user_count', 'max_storage_mb', 'remark', 'create_by', 'create_time', 'update_by', 'update_time', 'is_deleted'], [
        ('北京分公司', 'bj_branch', 1, '2027-12-31 23:59:59', 200, 10240, '北京地区分支机构') + base,
        ('上海分公司', 'sh_branch', 1, '2027-06-30 23:59:59', 100, 5120, '上海地区分支机构') + base,
        ('深圳研发中心', 'sz_rdc', 1, '2028-03-31 23:59:59', 300, 20480, '深圳研发中心') + base,
        ('合作伙伴A公司', 'partner_a', 1, '2026-12-31 23:59:59', 50, 2048, '合作方外部租户') + base,
    ])
    # 租户成员关系：标记每名用户在所属租户内是否为租户管理员，支撑租户内权限隔离
    batch_insert('sys_tenant_user', ['tenant_id', 'user_id', 'is_tenant_admin', 'join_time', 'create_time'], [
        (1, 1, 1, now, now), (1, 2, 0, now, now), (2, 3, 1, now, now), (3, 4, 1, now, now),
    ])
    # 租户套餐：按用户数/存储空间/价格划分标准版、专业版、企业版三档
    batch_insert('sys_tenant_package', ['package_name', 'max_user_count', 'max_storage_mb', 'price', 'status', 'remark', 'create_time', 'update_time', 'is_deleted'], [
        ('标准版-50用户', 50, 2048, 9999.00, 1, '适用于中小型团队', now, now, 0),
        ('专业版-200用户', 200, 10240, 29999.00, 1, '适用于成长型企业', now, now, 0),
        ('企业版-500用户', 500, 51200, 89999.00, 1, '适用于大型企业', now, now, 0),
    ])
    print('  tenant OK')  # 输出该模块执行成功


# 工单演示数据：5 个工单类型、10 条不同状态的工单，以及按规则生成的流转日志
def seed_wo():
    base = ('admin', now, 'admin', now, 0)  # 工单类型与工单表共用的审计字段
    batch_insert('work_order_type', ['type_name', 'sort', 'status', 'remark', 'create_by', 'create_time', 'update_by', 'update_time', 'is_deleted'], [
        ('Bug 反馈', 1, 1, '系统 Bug 反馈工单') + base,
        ('功能建议', 2, 1, '新功能需求工单') + base,
        ('账号权限', 3, 1, '账号/角色/权限相关') + base,
        ('数据问题', 4, 1, '数据修正/导入相关') + base,
        ('系统咨询', 5, 1, '使用咨询类工单') + base,
    ])
    # 工单标题池：按业务场景预置，循环取用即可得到贴近真实的演示列表
    titles = [
        '登录页面在 Safari 浏览器样式错乱',
        '希望增加批量导出 Excel 功能',
        '申请开通数据备份模块权限',
        '订单编号规则需要修改前缀',
        '如何配置定时任务执行时间？',
        '报表生成记录查询很慢',
        '大屏分享链接过期怎么重新生成？',
        '新增员工账号自动禁用问题',
        '上传大文件时偶尔失败',
        '字典管理缺少批量导入功能',
    ]
    order_types = [1, 2, 3, 4, 5, 1, 2, 3, 4, 5]  # 与标题池对应，轮流分配到 5 种工单类型
    statuses = [0, 0, 1, 1, 2, 2, 3, 0, 1, 2]  # 覆盖待处理/处理中/已完成/已关闭等多种状态
    priorities = [2, 3, 1, 3, 2, 3, 1, 2, 3, 2]  # 优先级混合分布，便于验证排序与筛选
    base_time = datetime.now()  # 以当前时间为基准，向前推算每条工单的期望完成时间
    rows = []  # 先收集全部工单行，再一次性交给 batch_insert
    for i in range(10):  # 循环生成 10 条工单，编号按 WD2026110xxx 规则递增
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
    batch_insert('kb_category', ['category_name', 'parent_id', 'sort', 'status', 'remark', 'create_by', 'create_time', 'update_by', 'update_time', 'is_deleted'], [
        ('产品手册', 0, 1, 1, '产品使用相关') + base,
        ('开发文档', 0, 2, 1, '开发对接') + base,
        ('运维手册', 0, 3, 1, '部署运维') + base,
        ('FAQ', 0, 4, 1, '常见问题') + base,
        ('快速上手', 1, 1, 1, None) + base,
        ('功能详解', 1, 2, 1, None) + base,
        ('API 文档', 2, 1, 1, None) + base,
        ('数据库设计', 2, 2, 1, None) + base,
    ])
    # 文档示例：category_id 指向上面的一级/二级分类，作者固定为 1 号用户
    docs = [
        (5, '快速上手-5 分钟入门 django-base-admin', '快速上手指南内容...', '快速入门,新手', 1),
        (6, '工作流审批模块功能详解', '工作流模块详解...', '工作流,审批,BPMN', 1),
        (7, 'RESTful API 接口规范', 'API 规范说明...', 'API,规范,RESTful', 1),
        (7, '统一响应结构与错误码', '错误码说明...', '错误码,响应', 1),
        (8, '数据库表结构总览', '数据库结构...', '数据库,表结构', 1),
        (3, '系统部署与运维手册', '部署运维...', '部署,运维', 1),
        (4, '如何重置 admin 密码', '密码重置方法...', '密码,重置,admin', 1),
        (4, '登录失败如何排查', '登录排查...', '登录,排查', 1),
    ]
    doc_rows = []  # 收集文档行数据
    for i, (cat_id, title, content, tags, author) in enumerate(docs, 1):  # 从 1 开始编号，用于生成阅读量与排序
        doc_rows.append((cat_id, title, content, None, tags, author, 'public', None, i * 17, 1, 1) + base)  # 阅读量按序号递增，权限为公开
    # 写入文档表：permission_type=public 表示所有登录用户可见
    batch_insert('kb_document', ['category_id', 'doc_title', 'doc_content', 'file_id', 'tags', 'author_id', 'permission_type', 'role_json', 'read_count', 'version', 'status', 'create_by', 'create_time', 'update_by', 'update_time', 'is_deleted'], doc_rows)
    print('  kb OK')  # 输出该模块执行成功
