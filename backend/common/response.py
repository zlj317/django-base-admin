"""统一响应封装：所有接口返回 {"code": ..., "msg": ..., "data": ...}。"""
from rest_framework.renderers import JSONRenderer  # 复用 DRF 的 JSON 渲染能力
from rest_framework.response import Response  # 使用 DRF 响应类，自动按 Accept 协商渲染

MAX_SAFE_INTEGER = 2 ** 53 - 1  # JavaScript Number 可精确表示的最大整数


def stringify_big_int(value):
    """递归把超出 JS 安全范围的整数转成字符串，避免雪花主键在前端丢失精度。"""
    if isinstance(value, bool):  # bool 是 int 子类，需先排除
        return value
    if isinstance(value, int):
        return str(value) if abs(value) > MAX_SAFE_INTEGER else value  # 小整数保持原样
    if isinstance(value, dict):
        return {key: stringify_big_int(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [stringify_big_int(item) for item in value]
    return value


class BigIntJSONRenderer(JSONRenderer):
    """全局 JSON 渲染器：雪花主键以字符串输出，前端回传时不再丢精度。"""

    def render(self, data, accepted_media_type=None, renderer_context=None):
        """渲染前统一处理大整数。"""
        return super().render(stringify_big_int(data), accepted_media_type, renderer_context)


def ok(data=None, msg='success'):
    """成功响应：业务码固定 200，data 可以是对象、列表或 None。"""
    return Response({'code': 200, 'msg': msg, 'data': data})  # HTTP 状态保持 200，业务码由 body 承载


def fail(msg='error', code=500, data=None):
    """失败响应：自定义业务码与提示文案，便于前端按 code 分支处理。"""
    return Response({'code': code, 'msg': msg, 'data': data})  # 同样不改 HTTP 状态，保持统一解析方式
