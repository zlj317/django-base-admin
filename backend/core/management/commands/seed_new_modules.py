"""为需求4/5/6新增功能模块批量填充演示数据。幂等：已存在则跳过。"""
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand
from django.db import connection


now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def batch_insert(table, columns, rows):
    """批量 INSERT，主键由雪花算法生成，列名加反引号避免保留字冲突。"""
    from common.snowflake import next_id  # 主键统一由后端生成，不依赖数据库自增
    all_columns = ['id'] + list(columns)
    placeholders = ', '.join(['%s'] * len(all_columns))
    cols = ', '.join([f'`{c}`' for c in all_columns])
    sql = f"INSERT IGNORE INTO `{table}` ({cols}) VALUES ({placeholders})"
    with connection.cursor() as cur:
        for row in rows:
            cur.execute(sql, [next_id()] + list(row))


class Command(BaseCommand):
    help = '为新增模块填充演示数据'

    def handle(self, *args, **options):
        self.stdout.write('开始填充演示数据...')
        seed_no()
        seed_imprint()
        seed_backup()
        seed_dp()
        seed_dsm()
        seed_mon()
        seed_sec()
        seed_tenant()
        seed_wo()
        seed_cal()
        seed_kb()
        self.stdout.write(self.style.SUCCESS('全部演示数据填充完成'))


def seed_no():
    base = ('admin', now, 'admin', now, 0)
    rows = [
        ('order_no', '订单编号', 'SO', 'YYYYMMDD', 6, 0, 1, '', 'day', None, 1, '订单主表编号') + base,
        ('delivery_no', '发货单号', 'DH', 'YYYYMM', 5, 0, 1, '-', 'month', None, 1, '发货单编号') + base,
        ('contract_no', '合同编号', 'HT', 'YYYY', 4, 0, 1, '/', 'year', None, 1, '销售合同编号') + base,
        ('invoice_no', '发票编号', 'FP', 'YYYYMMDD', 5, 0, 1, '', 'none', None, 1, '发票号') + base,
        ('ticket_no', '工单编号', 'WD', 'YYYYMMDD', 4, 0, 1, '', 'day', None, 1, '客服工单编号') + base,
    ]
    batch_insert('sys_no_rule', ['rule_key', 'rule_name', 'prefix', 'date_format', 'seq_length', 'seq_current', 'step', 'separator', 'reset_type', 'reset_time', 'status', 'remark', 'create_by', 'create_time', 'update_by', 'update_time', 'is_deleted'], rows)
    print('  sys_no_rule OK')


def seed_imprint():
    base = ('admin', now, 'admin', now, 0)
    batch_insert('imp_template', ['template_name', 'template_key', 'table_name', 'file_type', 'status', 'remark', 'create_by', 'create_time', 'update_by', 'update_time', 'is_deleted'], [
        ('员工信息导入', 'emp_import', 'sys_user', 'xlsx', 1, '批量导入员工') + base,
        ('商品清单导入', 'product_import', 'product', 'xlsx', 1, '批量导入商品') + base,
        ('客户信息导入', 'customer_import', 'customer', 'xlsx', 1, '批量导入客户') + base,
    ])
    batch_insert('imp_template_column', ['template_id', 'column_name', 'column_header', 'is_required', 'data_type', 'max_length', 'sort', 'is_deleted'], [
        (1, 'username', '用户名', 1, 'string', 64, 1, 0),
        (1, 'nickname', '姓名', 1, 'string', 64, 2, 0),
        (1, 'phone', '手机号', 0, 'string', 15, 3, 0),
        (2, 'product_name', '商品名称', 1, 'string', 200, 1, 0),
        (2, 'price', '单价', 1, 'number', 12, 2, 0),
        (3, 'customer_name', '客户名称', 1, 'string', 200, 1, 0),
    ])
    html = '<div style="padding:20px;font-family:SimSun;"><h2>订单打印</h2><table border="1"><thead><tr><th>编号</th><th>名称</th></tr></thead><tbody><tr><td colspan="2">{{data}}</td></tr></tbody></table></div>'
    batch_insert('print_template', ['template_name', 'template_key', 'biz_type', 'html_content', 'paper_size', 'is_default', 'status', 'remark', 'create_by', 'create_time', 'update_by', 'update_time', 'is_deleted'], [
        ('订单打印模板', 'order_print', 'order', html, 'A4', 1, 1, '标准订单打印') + base,
        ('发货单打印模板', 'delivery_print', 'delivery', html, 'A5', 0, 1, '发货单模板') + base,
        ('合同打印模板', 'contract_print', 'contract', html, 'A4', 0, 1, '合同模板') + base,
    ])
    print('  imprint OK')


def seed_backup():
    base = ('admin', now, 'admin', now, 0)
    batch_insert('backup_record', ['backup_name', 'backup_type', 'db_name', 'encrypt_flag', 'backup_status', 'backup_time', 'remark', 'create_by', 'create_time', 'update_by', 'update_time', 'is_deleted'], [
        ('全量数据备份_20261101', 'auto', 'gen_admin', 0, 1, '2026-11-01 02:00:00', '每日自动备份') + base,
        ('紧急数据备份_20261102', 'manual', 'gen_admin', 1, 1, '2026-11-02 15:30:00', '升级前手动备份') + base,
        ('月度归档备份_20261103', 'auto', 'gen_admin', 1, 1, '2026-11-03 00:10:00', '每月归档备份') + base,
    ])
    batch_insert('backup_strategy', ['strategy_name', 'cron_expr', 'keep_days', 'encrypt_flag', 'status', 'remark', 'create_by', 'create_time', 'update_by', 'update_time', 'is_deleted'], [
        ('每日全量备份', '0 0 2 * * ?', 7, 0, 1, '每天凌晨2点') + base,
        ('每周增量备份', '0 0 3 ? * MON', 30, 1, 1, '每周一凌晨3点') + base,
        ('每月归档备份', '0 0 1 1 * ?', 365, 1, 1, '每月1号归档') + base,
    ])
    print('  backup OK')


def seed_dp():
    base = ('admin', now, 'admin', now, 0)
    batch_insert('sys_data_permission', ['permission_name', 'permission_type', 'scope_value', 'sort', 'status', 'remark', 'create_by', 'create_time', 'update_by', 'update_time', 'is_deleted'], [
        ('全部数据权限', 'all', None, 1, 1, '可查看所有数据') + base,
        ('本部门及下级', 'dept', 'self,children', 2, 1, '可查看本部门及下级部门数据') + base,
        ('仅本人数据', 'self', None, 3, 1, '仅可查看自己创建的数据') + base,
        ('指定角色可见', 'role', '1,2', 4, 1, '仅角色1和2可见') + base,
    ])
    batch_insert('sys_role_data_permission', ['role_id', 'permission_id', 'create_time'], [
        (1, 1, now), (1, 2, now), (2, 2, now), (3, 3, now),
    ])
    print('  dp OK')


def seed_dsm():
    base = ('admin', now, 'admin', now, 0)
    batch_insert('desensitize_rule', ['rule_name', 'rule_type', 'mask_style', 'regular', 'status', 'remark', 'create_by', 'create_time', 'update_by', 'update_time', 'is_deleted'], [
        ('手机号脱敏', 'phone', '****', None, 1, '138****1234') + base,
        ('身份证号脱敏', 'idcard', '********', None, 1, '只显示前3后4位') + base,
        ('银行卡号脱敏', 'bank', '****', None, 1, '只显示后4位') + base,
        ('邮箱脱敏', 'email', '****', None, 1, '只显示首字符和域名') + base,
        ('姓名脱敏', 'custom', '*', None, 1, '张*、李**') + base,
    ])
    print('  dsm OK')


def seed_mon():
    base = ('admin', now, 'admin', now, 0)
    batch_insert('monitor_alarm_rule', ['rule_name', 'monitor_type', 'compare_op', 'threshold', 'alarm_level', 'channel', 'status', 'remark', 'create_by', 'create_time', 'update_by', 'update_time', 'is_deleted'], [
        ('CPU 使用率超阈值', 'service', '>', '85', 2, 'site', 1, 'CPU 连续 3 分钟超 85%') + base,
        ('磁盘空间不足', 'disk', '>', '90', 3, 'site,email', 1, '磁盘使用超 90% 严重告警') + base,
        ('数据库连接数过高', 'db', '>', '80', 2, 'site', 1, '数据库连接数超 80%') + base,
        ('接口响应超时', 'api', '>', '3000', 1, 'site', 1, '接口平均响应超 3 秒提示') + base,
        ('定时任务失败', 'task', '==', '1', 2, 'site', 1, '定时任务执行失败告警') + base,
    ])
    batch_insert('monitor_alarm_record', ['rule_id', 'alarm_level', 'alarm_content', 'alarm_time', 'handle_status', 'create_time'], [
        (1, 2, 'CPU 使用率达到 92%，持续 5 分钟', '2026-11-03 14:25:00', 1, '2026-11-03 14:25:00'),
        (2, 3, '磁盘 /data 使用 95%，剩余空间不足', '2026-11-02 08:10:00', 0, '2026-11-02 08:10:00'),
        (4, 1, '接口平均响应 3.5s', '2026-11-04 09:00:00', 0, '2026-11-04 09:00:00'),
        (5, 2, '每日数据备份定时任务执行失败', '2026-11-01 02:00:05', 1, '2026-11-01 02:00:05'),
    ])
    print('  mon OK')


def seed_sec():
    base = ('admin', now, 'admin', now, 0)
    batch_insert('sys_ip_control', ['ip', 'control_type', 'reason', 'status', 'expire_time', 'create_by', 'create_time', 'update_by', 'update_time', 'is_deleted'], [
        ('192.168.1.100', 'black', '连续多次登录失败，已临时封禁', 1, '2026-11-10 00:00:00') + base,
        ('10.0.0.200', 'black', '异常高频请求', 1, '2026-11-15 00:00:00') + base,
        ('172.16.0.1', 'white', '内网服务器固定 IP', 1, None) + base,
        ('127.0.0.1', 'white', '本机白名单', 1, None) + base,
    ])
    batch_insert('sys_login_attempt', ['username', 'ip', 'attempt_time', 'success_flag', 'create_time'], [
        ('admin', '192.168.1.100', '2026-11-04 10:30:00', 0, '2026-11-04 10:30:00'),
        ('admin', '192.168.1.100', '2026-11-04 10:30:15', 0, '2026-11-04 10:30:15'),
        ('user1', '10.0.0.50', '2026-11-04 09:15:00', 1, '2026-11-04 09:15:00'),
        ('user2', '10.0.0.51', '2026-11-04 09:20:00', 1, '2026-11-04 09:20:00'),
    ])
    batch_insert('sys_rate_limit', ['rule_name', 'limit_url', 'period_sec', 'max_count', 'status', 'create_by', 'create_time', 'update_by', 'update_time', 'is_deleted'], [
        ('登录接口限流', '/api/auth/login', 60, 5, 1) + base,
        ('短信发送限流', '/api/msg/**', 60, 10, 1) + base,
        ('导出接口限流', '/api/**/export', 3600, 20, 1) + base,
    ])
    print('  sec OK')


def seed_tenant():
    base = ('admin', now, 'admin', now, 0)
    batch_insert('sys_tenant', ['tenant_name', 'tenant_code', 'status', 'expire_time', 'max_user_count', 'max_storage_mb', 'remark', 'create_by', 'create_time', 'update_by', 'update_time', 'is_deleted'], [
        ('北京分公司', 'bj_branch', 1, '2027-12-31 23:59:59', 200, 10240, '北京地区分支机构') + base,
        ('上海分公司', 'sh_branch', 1, '2027-06-30 23:59:59', 100, 5120, '上海地区分支机构') + base,
        ('深圳研发中心', 'sz_rdc', 1, '2028-03-31 23:59:59', 300, 20480, '深圳研发中心') + base,
        ('合作伙伴A公司', 'partner_a', 1, '2026-12-31 23:59:59', 50, 2048, '合作方外部租户') + base,
    ])
    batch_insert('sys_tenant_user', ['tenant_id', 'user_id', 'is_tenant_admin', 'join_time', 'create_time'], [
        (1, 1, 1, now, now), (1, 2, 0, now, now), (2, 3, 1, now, now), (3, 4, 1, now, now),
    ])
    batch_insert('sys_tenant_package', ['package_name', 'max_user_count', 'max_storage_mb', 'price', 'status', 'remark', 'create_time', 'update_time', 'is_deleted'], [
        ('标准版-50用户', 50, 2048, 9999.00, 1, '适用于中小型团队', now, now, 0),
        ('专业版-200用户', 200, 10240, 29999.00, 1, '适用于成长型企业', now, now, 0),
        ('企业版-500用户', 500, 51200, 89999.00, 1, '适用于大型企业', now, now, 0),
    ])
    print('  tenant OK')


def seed_wo():
    base = ('admin', now, 'admin', now, 0)
    batch_insert('work_order_type', ['type_name', 'sort', 'status', 'remark', 'create_by', 'create_time', 'update_by', 'update_time', 'is_deleted'], [
        ('Bug 反馈', 1, 1, '系统 Bug 反馈工单') + base,
        ('功能建议', 2, 1, '新功能需求工单') + base,
        ('账号权限', 3, 1, '账号/角色/权限相关') + base,
        ('数据问题', 4, 1, '数据修正/导入相关') + base,
        ('系统咨询', 5, 1, '使用咨询类工单') + base,
    ])
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
    order_types = [1, 2, 3, 4, 5, 1, 2, 3, 4, 5]
    statuses = [0, 0, 1, 1, 2, 2, 3, 0, 1, 2]
    priorities = [2, 3, 1, 3, 2, 3, 1, 2, 3, 2]
    base_time = datetime.now()
    rows = []
    for i in range(10):
        rows.append((
            f'WD2026110{i+1:03d}', order_types[i], titles[i],
            '详细描述内容示例', '', priorities[i], statuses[i],
            1, 2,
            (base_time - timedelta(hours=(i + 1) * 2)).strftime('%Y-%m-%d %H:%M:%S'),
            None if statuses[i] != 3 else (base_time - timedelta(hours=i + 1)).strftime('%Y-%m-%d %H:%M:%S')
        ) + base)
    batch_insert('work_order', ['order_no', 'order_type_id', 'title', 'content', 'attachment_ids', 'priority', 'status', 'creator_id', 'assignee_id', 'expect_time', 'close_time', 'create_by', 'create_time', 'update_by', 'update_time', 'is_deleted'], rows)
    log_rows = []
    for i in range(1, 11):
        log_rows.append((i, 1, 'create', '工单创建', now))
        if i % 3 == 0:
            log_rows.append((i, 2, 'assign', '已指派给处理人', now))
        if i % 4 == 0:
            log_rows.append((i, 2, 'solve', '问题已定位并修复', now))
    batch_insert('work_order_log', ['order_id', 'operator_id', 'action', 'comment', 'create_time'], log_rows)
    print('  wo OK')


def seed_cal():
    rows = []
    today = datetime.now()
    base = ('admin', now, 'admin', now, 0)
    for i in range(-3, 8):
        dt = today + timedelta(days=i)
        rows.append((
            f'日程示例{i+1}', '简要描述',
            f'{dt.strftime("%Y-%m-%d")} 09:00:00', f'{dt.strftime("%Y-%m-%d")} 10:00:00',
            0, 1, 15, 0, None, 0
        ) + base)
    batch_insert('cal_schedule', ['title', 'content', 'start_time', 'end_time', 'all_day', 'owner_id', 'reminder_minutes', 'remind_status', 'shared_json', 'status', 'create_by', 'create_time', 'update_by', 'update_time', 'is_deleted'], rows)

    # 日程提醒：仅在表为空时补充演示数据，保证重复执行不产生脏数据
    with connection.cursor() as cur:
        cur.execute('SELECT COUNT(*) FROM cal_reminder')
        if cur.fetchone()[0] == 0:
            cur.execute("SELECT id FROM cal_schedule WHERE is_deleted=0 ORDER BY id LIMIT 3")
            schedule_ids = [r[0] for r in cur.fetchall()]
            remind_rows = []
            for index, schedule_id in enumerate(schedule_ids):
                remind_time = (today + timedelta(days=index)).strftime('%Y-%m-%d 08:30:00')
                remind_rows.append((schedule_id, 1, remind_time, index % 2, now))
            batch_insert('cal_reminder', ['schedule_id', 'remind_user_id', 'remind_time', 'remind_status', 'create_time'], remind_rows)
    print('  cal OK')


def seed_kb():
    base = ('admin', now, 'admin', now, 0)
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
    doc_rows = []
    for i, (cat_id, title, content, tags, author) in enumerate(docs, 1):
        doc_rows.append((cat_id, title, content, None, tags, author, 'public', None, i * 17, 1, 1) + base)
    batch_insert('kb_document', ['category_id', 'doc_title', 'doc_content', 'file_id', 'tags', 'author_id', 'permission_type', 'role_json', 'read_count', 'version', 'status', 'create_by', 'create_time', 'update_by', 'update_time', 'is_deleted'], doc_rows)
    print('  kb OK')
