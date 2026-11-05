"""首页聚合接口：overview + monitor。"""
import datetime
import os
import shutil

from rest_framework import viewsets
from rest_framework.response import Response

from common.response import ok


def _raw_count(table, where=''):
    """用原生 SQL 查某表的 count，失败返回 None。"""
    from django.db import connection
    try:
        with connection.cursor() as cursor:
            sql = f'SELECT COUNT(*) FROM {table}'
            if where:
                sql += f' WHERE {where}'
            cursor.execute(sql)
            row = cursor.fetchone()
            return row[0] if row else 0
    except Exception:
        return None


def _raw_query(sql, params=None, limit=None):
    """执行原生 SQL 并返回 dict 列表，失败返回空列表。"""
    from django.db import connection
    try:
        if limit:
            sql = f'{sql} LIMIT {int(limit)}'
        with connection.cursor() as cursor:
            cursor.execute(sql, params or [])
            columns = [col[0] for col in cursor.description] if cursor.description else []
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    except Exception:
        return []


def _short_time(value):
    """把时间字符串截断为 MM-DD HH:MM，首页展示更紧凑。"""
    text = str(value or '')
    return text[5:16] if len(text) >= 16 else text


def _memory_usage():
    """Windows 下取内存总量与使用率（GB / %），其他平台返回 None。"""
    try:
        import ctypes

        class MemoryStatus(ctypes.Structure):
            _fields_ = [
                ('dwLength', ctypes.c_ulong), ('dwMemoryLoad', ctypes.c_ulong),
                ('ullTotalPhys', ctypes.c_ulonglong), ('ullAvailPhys', ctypes.c_ulonglong),
                ('ullTotalPageFile', ctypes.c_ulonglong), ('ullAvailPageFile', ctypes.c_ulonglong),
                ('ullTotalVirtual', ctypes.c_ulonglong), ('ullAvailVirtual', ctypes.c_ulonglong),
                ('ullAvailExtendedVirtual', ctypes.c_ulonglong),
            ]

        status = MemoryStatus()
        status.dwLength = ctypes.sizeof(MemoryStatus)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status))  # 读取物理内存信息
        return round(status.ullTotalPhys / 1024 ** 3, 1), int(status.dwMemoryLoad)
    except Exception:
        return None, None


def _uptime_text():
    """取系统运行时长（天/小时），失败返回空字符串。"""
    try:
        import ctypes
        seconds = ctypes.windll.kernel32.GetTickCount64() / 1000  # 系统启动至今的秒数
        days, rest = divmod(int(seconds), 86400)
        hours = rest // 3600
        return f'{days}天{hours}小时' if days else f'{hours}小时'
    except Exception:
        return ''


class HomeViewSet(viewsets.ViewSet):
    """首页数据聚合。无权限校验，允许未登录访问概览。"""

    permission_classes = []  # 允许匿名访问，首页概览无需强制登录

    def overview(self, request):
        """首页概览：问候 + 模块统计 + 待办 + 最新公告/消息。"""
        now = datetime.datetime.now()
        user = getattr(request, 'user_info', None)

        # --- stats：各模块统计 ---
        stats = {}
        try:
            stats = {
                'user_count': _raw_count('sys_user', 'is_deleted=0'),
                'role_count': _raw_count('sys_role', 'is_deleted=0'),
                'menu_count': _raw_count('sys_menu', 'is_deleted=0'),
                'wf_task_count': _raw_count('wf_task', 'task_status=0'),
                'wf_instance_count': _raw_count('wf_instance', 'is_deleted=0'),
                'notice_unread': _raw_count('notice_info', 'status=0'),
                'msg_unread': _raw_count('msg_record', 'is_deleted=0 AND is_read=0'),
                'wf_file_count': _raw_count('wf_file'),
                'report_template_count': _raw_count('report_rp_template', 'is_deleted=0'),
                'report_generate_count': _raw_count('rp_generate_record'),
                # 首页卡片直接消费的四个指标，避免前端取不到值显示为 0/空白
                'todos': _raw_count('wf_task', 'task_status=0'),
                'messages': _raw_count('msg_record', 'is_deleted=0 AND is_read=0'),
                'workflows': _raw_count('wf_instance', 'is_deleted=0'),
                'new_users': _raw_count('sys_user', "is_deleted=0 AND DATE(create_time)=CURDATE()"),
            }
        except Exception:
            stats = {}

        # --- todos：待办事项 ---
        todos = []
        try:
            wf_todos = _raw_query(
                'SELECT id, task_name, task_type, create_time FROM wf_task WHERE task_status=0 ORDER BY id DESC',
                limit=5,
            )
            for t in wf_todos:
                todos.append({
                    'source': 'workflow',
                    'id': t.get('id'),
                    'title': t.get('task_name') or '待办审批',
                    'type': t.get('task_type') or '审批',
                    'typeLabel': '流程审批',
                    'path': '/workflow/todo',
                    'creator': '流程引擎',
                    'time': _short_time(t.get('create_time')),
                })
        except Exception:
            pass
        try:
            wo_todos = _raw_query(
                'SELECT id, title, status, create_time FROM work_order WHERE is_deleted=0 ORDER BY id DESC',
                limit=5,
            )
            for t in wo_todos:
                todos.append({
                    'source': 'work_order',
                    'id': t.get('id'),
                    'title': t.get('title') or '待处理工单',
                    'type': '工单',
                    'typeLabel': '工单处理',
                    'path': '/wo/mine',
                    'creator': '工单系统',
                    'time': _short_time(t.get('create_time')),
                })
        except Exception:
            pass
        try:
            today = now.strftime('%Y-%m-%d')
            cal_todos = _raw_query(
                "SELECT id, title, start_time, end_time FROM cal_schedule WHERE is_deleted=0 AND DATE(start_time)=%s ORDER BY start_time ASC",
                params=[today], limit=5,
            )
            for t in cal_todos:
                todos.append({
                    'source': 'cal_schedule',
                    'id': t.get('id'),
                    'title': t.get('title') or '今日日程',
                    'type': '日程',
                    'typeLabel': '今日日程',
                    'path': '/cal/schedule',
                    'creator': '日程管理',
                    'time': _short_time(t.get('start_time')),
                })
        except Exception:
            pass

        # --- latest_notice ---
        latest_notice = []
        try:
            latest_notice = _raw_query(
                'SELECT id, title, content, create_time FROM notice_info ORDER BY id DESC',
                limit=3,
            )
            latest_notice = [{
                'id': n.get('id'),
                'title': n.get('title'),
                'content': (n.get('content') or '')[:80],
                'time': str(n.get('create_time') or ''),
            } for n in latest_notice]
        except Exception:
            latest_notice = []

        # --- latest_msg ---
        latest_msg = []
        try:
            latest_msg = _raw_query(
                'SELECT id, title, content, is_read, create_time FROM msg_record WHERE is_deleted=0 ORDER BY id DESC',
                limit=3,
            )
            latest_msg = [{
                'id': m.get('id'),
                'title': m.get('title'),
                'content': (m.get('content') or '')[:80],
                'read': bool(m.get('is_read')),
                'time': str(m.get('create_time') or ''),
            } for m in latest_msg]
        except Exception:
            latest_msg = []

        # --- activities：最新动态（公告 + 消息拼装，供首页时间轴展示） ---
        activities = []
        for n in latest_notice:
            activities.append({'id': f'notice-{n["id"]}', 'typeLabel': '公告发布', 'text': n.get('title') or '',
                               'tagType': 'warning', 'time': _short_time(n.get('time'))})
        for m in latest_msg:
            activities.append({'id': f'msg-{m["id"]}', 'typeLabel': '站内消息', 'text': m.get('title') or '',
                               'tagType': 'primary', 'time': _short_time(m.get('time'))})
        activities.sort(key=lambda x: x.get('time') or '', reverse=True)  # 按时间倒序展示

        data = {
            'greeting': f'{now.strftime("%Y-%m-%d %H:%M:%S")} 欢迎回来，{user.username if user else "访客"}',
            'current_datetime': now.strftime('%Y-%m-%d %H:%M:%S'),
            'stats': {**stats, 'todos': len(todos[:5]), 'messages': stats.get('msg_unread') or 0},
            'todos': todos[:5],
            'activities': activities[:5],
            'latest_notice': latest_notice,
            'latest_msg': latest_msg,
        }
        return Response({'code': 200, 'msg': '获取成功', 'data': data})

    def rich(self, request):
        """首页增强聚合：在原有概览之上补充趋势、文件、任务、告警、用户、
        报表、BI、知识库、日程等数据块。

        设计原则：
        1. 只读接口，不写任何业务表；沿用首页的匿名只读策略（与 overview 一致），
           避免首页在登录态未就绪时整体 401。
        2. 所有查询都走 `_raw_query` / `_raw_count`，表或字段缺失时返回空值，
           保证某个模块未初始化时首页依然可以完整渲染。
        3. 不修改既有 overview / monitor 的返回结构，新接口仅被新首页调用。
        """
        now = datetime.datetime.now()          # 当前时间，用于统计“今日/昨日”
        today = now.date()                      # 今天的日期对象，用于“今日”统计
        # 最近 7 天的日期序列（含今天），趋势图固定展示 7 个点
        dates = [today - datetime.timedelta(days=6 - i) for i in range(7)]

        def _day_key(value):
            """把数据库返回的日期/时间值统一裁剪成 YYYY-MM-DD，便于做字典键。"""
            return str(value or '')[:10]

        def _trend(table, column, where=''):
            """统计最近 7 天某张表按 column 日期的记录数。

            - table/column 均来自本文件内的常量拼接，不接受用户输入，无注入风险；
            - 数据库返回的结果按日期聚合成字典，再按 dates 顺序补零，
              保证前端拿到的永远是 7 个点，不会因为某天没数据而断线。
            """
            start = dates[0].strftime('%Y-%m-%d')  # 7 天窗口的起始日期
            sql = f'SELECT DATE({column}) AS d, COUNT(*) AS c FROM {table} WHERE {column} >= %s'
            if where:
                sql += f' AND {where}'  # 追加业务过滤条件（如未删除）
            sql += f' GROUP BY DATE({column})'  # 按天聚合
            rows = _raw_query(sql, params=[start])
            bucket = {_day_key(r.get('d')): int(r.get('c') or 0) for r in rows}
            return [bucket.get(d.strftime('%Y-%m-%d'), 0) for d in dates]

        # ---------- 1. 7 日趋势 ----------
        # 先一次性算出五条趋势序列，既供趋势图使用，也供指标卡环比复用，避免重复查询数据库。
        wo_trend = _trend('work_order', 'create_time', 'is_deleted=0')   # 工单新增趋势
        wf_trend = _trend('wf_instance', 'start_time', 'is_deleted=0')   # 流程发起趋势
        msg_trend = _trend('msg_record', 'create_time', 'is_deleted=0')  # 消息新增趋势
        file_trend = _trend('wf_file', 'create_time')                    # 文件上传趋势
        user_trend = _trend('sys_user', 'create_time', 'is_deleted=0')   # 用户新增趋势
        # 键名与前端图表 legend 对应：wo=工单、wf=流程、msg=消息、file=文件、user=用户
        trends = {
            'dates': [d.strftime('%m-%d') for d in dates],  # 前端 X 轴标签，简化的月-日
            'wo': wo_trend,
            'wf': wf_trend,
            'msg': msg_trend,
            'file': file_trend,
            'user': user_trend,
        }

        # ---------- 2. 顶部指标卡 ----------
        # 待办 = 流程待办（wf_task.status=0，注意该表用 status 而非 task_status）
        #      + 未完成工单（status 0 待处理 / 1 处理中）
        wf_todo = _raw_count('wf_task', 'status=0') or 0
        wo_todo = _raw_count('work_order', 'is_deleted=0 AND status IN (0,1)') or 0
        todos_count = wf_todo + wo_todo
        # 今日新增待办（流程 + 工单）与昨日对比，得到环比差值
        todo_delta = (_raw_count('wf_task', 'DATE(create_time)=CURDATE()') or 0) \
            + (_raw_count('work_order', 'is_deleted=0 AND DATE(create_time)=CURDATE()') or 0) \
            - (_raw_count('wf_task', 'DATE(create_time)=DATE_SUB(CURDATE(), INTERVAL 1 DAY)') or 0) \
            - (_raw_count('work_order', 'is_deleted=0 AND DATE(create_time)=DATE_SUB(CURDATE(), INTERVAL 1 DAY)') or 0)
        # 未读站内消息
        msg_unread = _raw_count('msg_record', 'is_deleted=0 AND is_read=0') or 0
        # 运行中工作流实例（status=0 且未逻辑删除）
        wf_running = _raw_count('wf_instance', 'is_deleted=0 AND status=0') or 0
        # 今日新增用户
        user_today = _raw_count('sys_user', 'is_deleted=0 AND DATE(create_time)=CURDATE()') or 0
        # 文件总数与总字节
        file_rows = _raw_query('SELECT COUNT(*) AS c, COALESCE(SUM(file_size),0) AS s FROM wf_file', limit=1)
        file_count = int(file_rows[0].get('c') or 0) if file_rows else 0
        file_size = int(file_rows[0].get('s') or 0) if file_rows else 0
        # 未关闭告警数量
        alarm_open = _raw_count('monitor_alarm_record', 'handle_status=0') or 0

        stats = {
            'todos': todos_count,
            'messages': msg_unread,
            'workflows': wf_running,
            'new_users': user_today,
            'todo_delta': todo_delta,
            # 消息环比：趋势序列最后一个点（今天）减去倒数第二个点（昨天）
            'message_delta': msg_trend[-1] - msg_trend[-2],
            # 流程环比：趋势序列最后两个点相减
            'workflow_delta': wf_trend[-1] - wf_trend[-2],
            # 用户环比：今日新增用户数 - 昨日新增用户数
            'user_delta': user_today
                          - (_raw_count('sys_user', 'is_deleted=0 AND DATE(create_time)=DATE_SUB(CURDATE(), INTERVAL 1 DAY)') or 0),
            'file_count': file_count,       # 文件数量
            'file_size': file_size,         # 文件占用字节数
            'wo_open': wo_todo,             # 未完成工单数
            'alarm_open': alarm_open,       # 未处理告警数
        }

        # ---------- 3. 待办列表 ----------
        # 统一格式后再合并排序：sort_key 用于按真实时间倒序，避免不同来源时间格式不一致
        todos = []
        # 3.1 流程待办（联表取实例当前节点，便于前端展示上下文）
        wf_rows = _raw_query(
            'SELECT t.id, t.task_name, t.create_time, i.current_node '
            'FROM wf_task t LEFT JOIN wf_instance i ON i.id = t.instance_id '
            'WHERE t.status=0 ORDER BY t.id DESC',
            limit=6,
        )
        for t in wf_rows:
            todos.append({
                'source': 'workflow',                                  # 来源标识，前端据此选跳转路径
                'id': t.get('id'),
                'title': t.get('task_name') or '待办审批',              # 标题兜底
                'typeLabel': '流程审批',                                # 展示用类型标签
                'path': '/workflow/todo',                              # 点击后的业务页
                'creator': t.get('current_node') or '流程引擎',          # 副信息显示当前节点
                'time': _short_time(t.get('create_time')),
                'sort_key': str(t.get('create_time') or ''),
            })
        # 3.2 工单待办（只取未完成状态）
        wo_rows = _raw_query(
            'SELECT id, title, priority, create_time FROM work_order '
            'WHERE is_deleted=0 AND status IN (0,1) ORDER BY id DESC',
            limit=6,
        )
        for t in wo_rows:
            todos.append({
                'source': 'work_order',
                'id': t.get('id'),
                'title': t.get('title') or '待处理工单',
                'typeLabel': '工单处理',
                'path': '/wo/mine',
                'creator': ['低', '中', '高'][int(t.get('priority') or 2) - 1] + '优先级',  # 1低/2中/3高
                'time': _short_time(t.get('create_time')),
                'sort_key': str(t.get('create_time') or ''),
            })
        # 3.3 今日日程（作为第三类待办来源）
        cal_rows = _raw_query(
            'SELECT id, title, start_time FROM cal_schedule '
            'WHERE is_deleted=0 AND status=0 AND DATE(start_time)=%s ORDER BY start_time ASC',
            params=[today.strftime('%Y-%m-%d')], limit=4,
        )
        for t in cal_rows:
            todos.append({
                'source': 'cal_schedule',
                'id': t.get('id'),
                'title': t.get('title') or '今日日程',
                'typeLabel': '今日日程',
                'path': '/cal/schedule',
                'creator': '日程管理',
                'time': _short_time(t.get('start_time')),
                'sort_key': str(t.get('start_time') or ''),
            })
        # 按真实时间倒序，再截取前 8 条；sort_key 只在后端使用，输出前移除
        todos.sort(key=lambda x: x.get('sort_key') or '', reverse=True)
        todos = todos[:8]
        for item in todos:
            item.pop('sort_key', None)

        # ---------- 4. 公告 / 消息 ----------
        # 最新 4 条公告：正文截断 80 字，避免卡片被长文本撑高
        notices = _raw_query(
            'SELECT id, title, content, create_time FROM notice_info '
            'WHERE is_deleted=0 ORDER BY id DESC',
            limit=4,
        )
        notices = [{
            'id': n.get('id'),
            'title': n.get('title') or '未命名公告',
            'content': (n.get('content') or '')[:80],
            'time': _short_time(n.get('create_time')),
        } for n in notices]
        # 最新 4 条站内消息，read 标记供前端显示未读圆点
        messages = _raw_query(
            'SELECT id, title, content, is_read, create_time FROM msg_record '
            'WHERE is_deleted=0 ORDER BY id DESC',
            limit=4,
        )
        messages = [{
            'id': m.get('id'),
            'title': m.get('title') or '站内消息',
            'content': (m.get('content') or '')[:80],
            'read': bool(m.get('is_read')),
            'time': _short_time(m.get('create_time')),
        } for m in messages]

        # ---------- 5. 最近工作流实例 ----------
        # 联表取模型名称；status_label 在后端翻译，减少前端重复映射
        wf_status_text = {0: '运行中', 1: '已完成', 2: '已驳回', 3: '已终止'}
        workflows = _raw_query(
            'SELECT i.id, i.status, i.current_node, i.start_time, i.start_user_id, m.model_name '
            'FROM wf_instance i LEFT JOIN wf_model m ON m.id = i.model_id '
            'WHERE i.is_deleted=0 ORDER BY i.id DESC',
            limit=5,
        )
        workflows = [{
            'id': w.get('id'),
            'model_name': w.get('model_name') or '未命名流程',
            'node': w.get('current_node') or '—',
            'status': int(w.get('status') or 0),
            'status_label': wf_status_text.get(int(w.get('status') or 0), '未知'),
            'user_id': w.get('start_user_id'),
            'time': _short_time(w.get('start_time')),
        } for w in workflows]

        # ---------- 6. 文件与存储 ----------
        # 按扩展名分布取前 5，file_ext 为空的归入“其他”
        ext_rows = _raw_query(
            'SELECT file_ext AS ext, COUNT(*) AS c, COALESCE(SUM(file_size),0) AS s '
            'FROM wf_file GROUP BY file_ext ORDER BY c DESC',
            limit=6,
        )
        by_ext = [{
            'ext': (r.get('ext') or '其他').lower(),
            'count': int(r.get('c') or 0),
            'size': int(r.get('s') or 0),
        } for r in ext_rows[:5]]

        # ---------- 7. 定时任务 ----------
        task_total = _raw_count('task_info', 'is_deleted=0') or 0
        task_enabled = _raw_count('task_info', 'is_deleted=0 AND status=0') or 0
        # 最近 4 条执行日志；run_status 0/1/2 对应 运行中/成功/失败
        run_rows = _raw_query(
            'SELECT task_name, run_status, run_time, cost_time FROM task_log ORDER BY id DESC',
            limit=4,
        )
        run_status_text = {0: '运行中', 1: '成功', 2: '失败'}
        task_recent = [{
            'name': r.get('task_name') or '未命名任务',
            'status': int(r.get('run_status') or 0),
            'status_label': run_status_text.get(int(r.get('run_status') or 0), '未知'),
            'time': _short_time(r.get('run_time')),
            'cost_time': int(r.get('cost_time') or 0),
        } for r in run_rows]

        # ---------- 8. 监控告警 ----------
        alarm_total = _raw_count('monitor_alarm_record') or 0
        level_rows = _raw_query(
            'SELECT alarm_level AS l, COUNT(*) AS c FROM monitor_alarm_record '
            'WHERE handle_status=0 GROUP BY alarm_level ORDER BY alarm_level ASC'
        )
        # 级别语义：1 提示 / 2 警告 / 3 严重（与 monitor 模块保持一致）
        level_text = {1: '提示', 2: '警告', 3: '严重'}
        alarm_by_level = [{
            'level': int(r.get('l') or 1),
            'label': level_text.get(int(r.get('l') or 1), '提示'),
            'count': int(r.get('c') or 0),
        } for r in level_rows]
        alarm_rows = _raw_query(
            'SELECT id, alarm_level, alarm_content, alarm_time, handle_status '
            'FROM monitor_alarm_record ORDER BY id DESC',
            limit=4,
        )
        alarm_recent = [{
            'id': r.get('id'),
            'level': int(r.get('alarm_level') or 1),
            'level_label': level_text.get(int(r.get('alarm_level') or 1), '提示'),
            'content': (r.get('alarm_content') or '')[:60],
            'time': _short_time(r.get('alarm_time') or r.get('create_time')),
            'handled': bool(int(r.get('handle_status') or 0)),
        } for r in alarm_rows]

        # ---------- 9. 用户活跃 ----------
        user_total = _raw_count('sys_user', 'is_deleted=0') or 0
        # 按部门统计用户数，部门为空归入“未分配”
        dept_rows = _raw_query(
            'SELECT d.dept_name AS name, COUNT(u.id) AS c FROM sys_user u '
            'LEFT JOIN sys_dept d ON d.id = u.dept_id '
            'WHERE u.is_deleted=0 GROUP BY d.dept_name ORDER BY c DESC',
            limit=5,
        )
        users_by_dept = [{
            'name': r.get('name') or '未分配部门',
            'count': int(r.get('c') or 0),
        } for r in dept_rows]
        # 角色数与租户数：用于填充“用户与组织”卡片，避免只有两个数字显得单薄
        role_total = _raw_count('sys_role', 'is_deleted=0') or 0
        tenant_total = _raw_count('sys_tenant', 'is_deleted=0') or 0

        # ---------- 10. 报表 / BI ----------
        report_templates = _raw_count('rp_template', 'is_deleted=0') or 0
        report_generated = _raw_count('rp_generate_record') or 0
        gen_rows = _raw_query(
            'SELECT template_name, gen_status, gen_time FROM rp_generate_record ORDER BY id DESC',
            limit=4,
        )
        gen_status_text = {0: '生成中', 1: '成功', 2: '失败'}
        report_recent = [{
            'name': r.get('template_name') or '未命名报表',
            'status': int(r.get('gen_status') or 0),
            'status_label': gen_status_text.get(int(r.get('gen_status') or 0), '未知'),
            'time': _short_time(r.get('gen_time') or r.get('create_time')),
        } for r in gen_rows]

        bi_total = _raw_count('bi_screen', 'is_deleted=0') or 0
        bi_published = _raw_count('bi_screen', 'is_deleted=0 AND status=1') or 0
        bi_rows = _raw_query(
            'SELECT id, screen_name, status, refresh_sec FROM bi_screen '
            'WHERE is_deleted=0 ORDER BY id DESC',
            limit=4,
        )
        bi_status_text = {0: '草稿', 1: '已发布', 2: '已下线'}
        bi_list = [{
            'id': r.get('id'),
            'name': r.get('screen_name') or '未命名大屏',
            'status': int(r.get('status') or 0),
            'status_label': bi_status_text.get(int(r.get('status') or 0), '未知'),
            'refresh_sec': int(r.get('refresh_sec') or 0),
        } for r in bi_rows]

        # ---------- 11. 知识库 ----------
        kb_docs = _raw_count('kb_document', 'is_deleted=0') or 0
        kb_categories = _raw_count('kb_category', 'is_deleted=0') or 0
        kb_rows = _raw_query(
            'SELECT doc_title, read_count, create_time FROM kb_document '
            'WHERE is_deleted=0 AND status=1 ORDER BY read_count DESC',
            limit=4,
        )
        kb_hot = [{
            'title': r.get('doc_title') or '未命名文档',
            'read_count': int(r.get('read_count') or 0),
            'time': _short_time(r.get('create_time')),
        } for r in kb_rows]

        # ---------- 12. 今日日程 ----------
        cal_count = _raw_count('cal_schedule',
                               'is_deleted=0 AND status=0 AND DATE(start_time)=CURDATE()') or 0
        cal_rows = _raw_query(
            'SELECT id, title, start_time, end_time, all_day FROM cal_schedule '
            'WHERE is_deleted=0 AND status=0 AND DATE(start_time)=%s ORDER BY start_time ASC',
            params=[today.strftime('%Y-%m-%d')], limit=4,
        )
        cal_list = [{
            'id': r.get('id'),
            'title': r.get('title') or '日程',
            'start': _short_time(r.get('start_time')),
            'end': _short_time(r.get('end_time')),
            'all_day': bool(int(r.get('all_day') or 0)),
        } for r in cal_rows]
        # 未来 7 天日程：今日日程往往只有 1 条，补充未来安排可让卡片内容更完整
        week_rows = _raw_query(
            'SELECT id, title, start_time, end_time, all_day FROM cal_schedule '
            'WHERE is_deleted=0 AND status=0 AND DATE(start_time) > %s AND DATE(start_time) <= %s '
            'ORDER BY start_time ASC',
            params=[today.strftime('%Y-%m-%d'),
                    (today + datetime.timedelta(days=6)).strftime('%Y-%m-%d')], limit=8,
        )
        cal_week = [{
            'id': r.get('id'),
            'title': r.get('title') or '日程',
            'date': _day_key(r.get('start_time'))[5:],           # 只显示 MM-DD
            'start': _short_time(r.get('start_time')),
            'all_day': bool(int(r.get('all_day') or 0)),
        } for r in week_rows]

        # ---------- 13. 组装返回 ----------
        data = {
            'generated_at': now.strftime('%Y-%m-%d %H:%M:%S'),  # 前端显示“数据截至”
            'stats': stats,
            'trends': trends,
            'todos': todos,
            'notices': notices,
            'messages': messages,
            'workflows': workflows,
            'files': {'count': file_count, 'size': file_size, 'by_ext': by_ext},
            'tasks': {'total': task_total, 'enabled': task_enabled, 'recent': task_recent},
            'alarms': {'total': alarm_total, 'open': alarm_open,
                       'by_level': alarm_by_level, 'recent': alarm_recent},
            'users': {'total': user_total, 'today': user_today, 'by_dept': users_by_dept,
                      'roles': role_total, 'tenants': tenant_total},
            'reports': {'templates': report_templates, 'generated': report_generated,
                        'recent': report_recent},
            'bi': {'total': bi_total, 'published': bi_published, 'list': bi_list},
            'kb': {'docs': kb_docs, 'categories': kb_categories, 'hot': kb_hot},
            'cal': {'today': cal_count, 'list': cal_list, 'week': cal_week},
        }
        return Response({'code': 200, 'msg': '获取成功', 'data': data})

    def monitor(self, request):
        """系统监控：数据库连通 + 磁盘使用 + 服务状态。"""
        service_status = 'ok'
        db_status = 'ok'
        disk_info = {}
        db_info = {}

        # --- 数据库连通 ---
        from django.db import connection
        try:
            connection.ensure_connection()
            with connection.cursor() as cursor:
                cursor.execute('SELECT VERSION()')
                row = cursor.fetchone()
                db_info['version'] = row[0] if row else ''
                cursor.execute('SHOW DATABASES LIKE %s', [connection.settings_dict['NAME']])
                exists = cursor.fetchone() is not None
                db_info['database_name'] = connection.settings_dict['NAME']
                db_info['host'] = connection.settings_dict.get('HOST', '')
                db_info['connected'] = True
        except Exception as e:
            db_status = 'error'
            db_info = {'connected': False, 'error': str(e)}
            service_status = 'degraded'

        # --- 磁盘（优先用 / 或项目根） ---
        disk_info = {}
        try:
            target = os.path.expanduser('~')  # Windows 下即用户目录所在盘符
            usage = shutil.disk_usage(target)  # 跨平台兼容，Windows 也可用
            total_gb = usage.total / 1024 ** 3
            used_gb = usage.used / 1024 ** 3
            free_gb = usage.free / 1024 ** 3
            usage_pct = round(usage.used * 100 / usage.total, 1) if usage.total else 0
            disk_info = {
                'path': target,
                'total_mb': round(usage.total / 1024 ** 2, 2),
                'used_mb': round(usage.used / 1024 ** 2, 2),
                'free_mb': round(usage.free / 1024 ** 2, 2),
                'usage_pct': usage_pct,
                'disk_total': round(total_gb, 1),
                'disk_used': round(used_gb, 1),
                'disk_free': round(free_gb, 1),
                'disk_percent': usage_pct,
            }
        except Exception as e:
            disk_info = {'error': str(e)}

        mem_total, mem_percent = _memory_usage()  # 内存总量与使用率
        data = {
            'service_status': service_status,
            'db_status': db_status,
            'db': db_info,
            'disk': disk_info,
            'server_time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            # 以下为首页监控卡片直接读取的扁平字段
            'disk_total': disk_info.get('disk_total', 0),
            'disk_used': disk_info.get('disk_used', 0),
            'disk_free': disk_info.get('disk_free', 0),
            'disk_percent': disk_info.get('disk_percent', 0),
            'mem_total': mem_total,
            'mem_percent': mem_percent,
            'uptime': _uptime_text(),
        }
        return Response({'code': 200, 'msg': '获取成功', 'data': data})
