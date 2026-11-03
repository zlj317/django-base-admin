"""统一响应封装：所有接口返回 {"code": ..., "msg": ..., "data": ...}。"""
from rest_framework.response import Response  # 使用 DRF 响应类，自动按 Accept 协商渲染


def ok(data=None, msg='success'):
    """成功响应：业务码固定 200，data 可以是对象、列表或 None。"""
    return Response({'code': 200, 'msg': msg, 'data': data})  # HTTP 状态保持 200，业务码由 body 承载


def fail(msg='error', code=500, data=None):
    """失败响应：自定义业务码与提示文案，便于前端按 code 分支处理。"""
    return Response({'code': code, 'msg': msg, 'data': data})  # 同样不改 HTTP 状态，保持统一解析方式
