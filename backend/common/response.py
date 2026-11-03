"""统一响应封装：所有接口返回 {"code": ..., "msg": ..., "data": ...}。"""
from rest_framework.response import Response


def ok(data=None, msg='success'):
    return Response({'code': 200, 'msg': msg, 'data': data})


def fail(msg='error', code=500, data=None):
    return Response({'code': code, 'msg': msg, 'data': data})
