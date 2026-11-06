"""中间件：操作日志记录 + token 静默续期。"""
# 模块定位：请求/响应链路上的两个横切能力，避免每个视图重复写日志或续期逻辑。
# 调用登记：config/settings.py 的 MIDDLEWARE 注册了 OperLogMiddleware 与 TokenRefreshMiddleware。
# 执行顺序：按 settings 中的顺序先记日志再续期；两者都在响应阶段操作 response。
# 关键约定：日志只覆盖 /api/ 前缀下的 POST/PUT/DELETE 且排除登录登出；
# 续期仅在 token 剩余有效期低于 JWT_CONFIG['REFRESH_THRESHOLD'] 时通过响应头下发新 token。
# 稳定性要求：日志与续期任何异常都不得影响业务响应，失败时记录日志后继续返回。
import json  # 预留 JSON 解析能力，当前日志按原文记录请求体
import logging  # 日志对象，用于记录保存操作日志失败的情况
import time  # 统计接口耗时并生成操作时间字符串
# 标准库结束；以下为项目内模型，导入期即依赖 Django ORM

from apps.system.models import SysOperLog  # 操作日志模型，直接落库

logger = logging.getLogger(__name__)  # 模块级 logger，异常按模块归类

# 操作类型推断表：按顺序匹配 URL 关键字，先命中者生效，因此更具体的关键字要排在前面
OPER_TYPE_MAP = [  # 按 URL 关键字推断操作类型，兼容现有接口路径命名
    ('importTemplate', '导入'),  # 模板下载也归为导入类操作
    ('importData', '导入'),  # 批量导入数据
    ('import', '导入'),  # 兜底匹配其余导入路径
    ('export', '导出'),  # 导出接口
    ('create', '新增'),  # 新增接口
    ('update', '编辑'),  # 编辑接口
    ('delete', '删除'),  # 删除接口
    ('assign', '编辑'),  # 分配角色/权限，业务上归为编辑
    ('reset_pwd', '编辑'),  # 重置密码归为编辑
    ('status', '编辑'),  # 状态启停归为编辑
]

SKIP_PATHS = ('/api/auth/login', '/api/auth/logout')  # 登录/登出不记日志，避免产生噪音数据
# 说明：SKIP_PATHS 采用前缀匹配（startswith），因此带查询串或尾斜杠的同名路径也会被跳过


# 通用工具：从请求头还原客户端 IP，登录日志与操作日志都依赖它
def get_client_ip(request):
    """取真实客户端 IP：优先 X-Forwarded-For 首段，其次 REMOTE_ADDR。"""
    xff = request.META.get('HTTP_X_FORWARDED_FOR')  # 经过代理时真实 IP 位于首段
    return xff.split(',')[0].strip() if xff else request.META.get('REMOTE_ADDR', '')  # 无代理时退回直连地址


# 操作日志中间件：包住整个请求，在响应返回前把写操作落库
class OperLogMiddleware:
    """记录写操作到 sys_oper_log。"""

    # Django 中间件协议要求保存下一层调用链，缺省实现会直接 500
    def __init__(self, get_response):
        """Django 中间件约定：保存下一层调用链。"""
        self.get_response = get_response  # 由 Django 注入，调用它才会继续处理请求

    # 中间件主流程：请求前记录起始时间与请求体，响应后补记状态与耗时
    def __call__(self, request):
        """请求前后打点，仅对写接口落库，异常不影响主业务流程。"""
        # 阶段一：请求进入视图前，先抓取请求体（读取后 DRF 仍可正常解析）
        started = time.time()  # 记录开始时间，用于计算耗时
        body = b''  # 先占位，GET 等请求无需读取请求体
        if request.method in ('POST', 'PUT', 'DELETE') and not request.path.startswith(SKIP_PATHS):
            # 只对写操作且非登录登出读取 body，减少无意义的 IO
            try:
                body = request.body[:2000]  # 截断请求体，防止大字段撑爆日志表
            # 请求体可能已被其他中间件/DRF 消费，读取失败时降级为空而不中断请求
            except Exception:
                body = b''  # 读取 body 失败（如流已被消费）时降级为空
        # 阶段二：调用下一层（即真正执行视图），拿到响应后补记日志
        response = self.get_response(request)  # 继续执行视图并拿到响应
        # 阶段三：只对 /api/ 下的写操作落库；登录/登出路径排除，避免日志噪音
        if request.method in ('POST', 'PUT', 'DELETE') and request.path.startswith('/api/') \
                and not request.path.startswith(SKIP_PATHS):  # 只记录 API 前缀下的写操作
            # 日志写入失败不能影响业务响应，因此整体包在 try 中
            try:
                self.save_log(request, response, body, int((time.time() - started) * 1000))  # 耗时换算为毫秒
            # 数据库/模型异常时仅记录应用日志，绝不改变已生成的响应
            except Exception:
                logger.exception('记录操作日志失败: %s %s', request.method, request.path)  # 日志失败不得影响响应
        return response  # 原样返回响应

    # 日志落库细节：把请求元信息、出入参与耗时整理成一条 sys_oper_log
    def save_log(self, request, response, body, cost_ms):
        """解析操作类型、用户与出入参，写入一条 sys_oper_log 记录。"""
        # 1) 操作类型：按 URL 关键字顺序匹配，未命中统一记为「其他」
        oper_type = '其他'  # 未命中关键字时的默认类型
        path = request.path.rstrip('/')  # 去掉尾部斜杠，避免关键字匹配受格式影响
        # 顺序遍历关键字表，命中第一个即确定操作类型（表项已按优先级排序）
        for keyword, label in OPER_TYPE_MAP:
            # URL 里包含关键字即视为对应操作，如 /api/system/user/create
            if keyword in path:
                oper_type = label  # 命中即取对应中文类型
                break  # 按优先级排列，命中后不再继续
        # 2) 请求体：按 UTF-8 解码，遇到非法字节直接忽略，保证能落库
        try:
            param = body.decode('utf-8', errors='ignore') if body else ''  # 非法编码字符忽略，保证能落库
        # 理论上 errors='ignore' 不会抛出，此处兜底防止非常规 bytes 子类
        except Exception:
            param = ''  # 解码异常时降级为空字符串
        # 3) 响应体：同样截断后解码；流式响应没有 content 时跳过
        try:
            # 普通 DRF/Django 响应带 content 且为 bytes，截断后再解码
            if isinstance(response.content, bytes):
                result = response.content[:2000].decode('utf-8', errors='ignore')  # 响应体同样截断，避免超长
            # StreamingHttpResponse/FileResponse 没有可读的 content，直接跳过记录
            else:
                result = ''  # 流式响应没有 content，跳过记录
        # 访问 content 可能触发流式读取异常，失败时降级为空
        except Exception:
            result = ''  # 读取响应内容失败时降级为空

        # 4) 操作人：认证类已把用户挂在 request 上，未登录时为 None
        user = getattr(request, 'user_info', None)  # 认证类已挂用户，未登录时为 None
        # 未认证的写请求（401）不记录
        if user is None and getattr(response, 'status_code', 200) != 200:
            return  # 未登录且响应异常，属无效操作，不写日志
        module_name = ''  # 默认模块名，取不到视图时留空
        # 5) 模块名：通过路由解析结果找到视图类，再读视图声明的中文模块名
        match = getattr(request, 'resolver_match', None)  # 路由解析结果，可定位到具体视图
        func = getattr(match, 'func', None) if match else None  # 视图可调用对象，可能是函数或 as_view 包装
        # Django View 设置 view_class；DRF ViewSet 只设置 cls
        view_class = getattr(func, 'view_class', None) or getattr(func, 'cls', None)  # 两种属性都尝试，兼容不同视图
        # 能定位到视图类才读取 module_name，函数视图或解析失败时保持空值
        if view_class is not None:
            module_name = getattr(view_class, 'module_name', '')  # 视图声明的中文模块名，便于按模块检索
        # 6) 落库：一次 ORM create 写入全部字段，字段内容均已在前面做截断/降级处理
        SysOperLog.objects.create(
            oper_user=user.username if user else '',  # 未登录的写操作记空账号
            module_name=module_name,  # 模块中文名
            oper_type=oper_type,  # 操作类型
            request_url=request.path,  # 原始请求路径
            request_param=param,  # 请求体原文（已截断）
            response_result=result,  # 响应体原文（已截断）
            cost_time=cost_ms,  # 耗时毫秒数
            oper_time=time.strftime('%Y-%m-%d %H:%M:%S'),  # 本地时间字符串，与 USE_TZ=False 一致
        )


# token 续期中间件：不改动业务响应，只在响应头上追加新 token，前端无感续期
class TokenRefreshMiddleware:
    """token 剩余有效期不足阈值时，在响应头下发新 token（X-Refresh-Token）。"""

    # 同样遵循 Django 中间件协议，保存下一层调用链
    def __init__(self, get_response):
        """保存下一层调用链，符合 Django 中间件协议。"""
        self.get_response = get_response  # 调用它才会进入视图

    # 必须在视图执行之后才能拿到认证类挂载的 jwt_payload
    def __call__(self, request):
        """响应返回前判断剩余有效期，必要时续期并写入响应头。"""
        response = self.get_response(request)  # 先让业务处理完，确保 jwt_payload 已挂载
        payload = getattr(request, 'jwt_payload', None)  # 认证类挂载的载荷，未登录时为 None
        # 只有通过 JWT 认证且载荷含过期时间的请求才需要考虑续期
        if payload and 'exp' in payload:
            # 只有在携带有效载荷时才导入依赖，减少每次请求的额外开销
            from datetime import datetime, timedelta  # 局部导入：计算剩余时长（当前只用到 datetime）
            from django.conf import settings  # 局部导入：只在需要续期时读取配置
            from common.auth import create_token  # 延迟导入，规避 auth 与中间件的循环依赖

            # 剩余有效期 = token 过期时刻 - 当前本地时间（项目 USE_TZ=False）
            remain = datetime.fromtimestamp(payload['exp']) - datetime.now()  # 本地时间下的剩余有效期
            threshold = settings.JWT_CONFIG['REFRESH_THRESHOLD']  # 配置的续期阈值
            # 两个条件同时满足才续期：已进入阈值窗口，且 token 尚未真正过期
            if remain < threshold and remain.total_seconds() > 0:
                user = getattr(request, 'user_info', None)  # 已过期的 token 不会走到这里，此处仅做兜底
                # 极端情况下认证结果未挂载时跳过续期，避免签出 uid 为空的 token
                if user is not None:
                    response['X-Refresh-Token'] = create_token(user)  # 前端读取该头后替换本地 token
        return response  # 处理完毕，返回响应
