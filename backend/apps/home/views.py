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
