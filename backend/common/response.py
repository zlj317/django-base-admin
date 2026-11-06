"""统一响应封装：所有接口返回 {"code": ..., "msg": ..., "data": ...}。"""
# 模块定位：common 层响应约定，所有业务视图都用 ok/fail 组装返回体，前端只解析这一种结构。
# 调用方：apps/*/views.py 大量导入 ok/fail；settings.REST_FRAMEWORK 注册 BigIntJSONRenderer 作为全局渲染器。
# 关键约定：HTTP 状态码恒为 200，真实业务结果放在 body 的 code 字段；
# 雪花主键可能超出 JS Number 安全范围，渲染前统一转字符串，避免前端精度丢失。
from rest_framework.renderers import JSONRenderer  # 复用 DRF 的 JSON 渲染能力
from rest_framework.response import Response  # 使用 DRF 响应类，自动按 Accept 协商渲染

# JS 的 Number.MAX_SAFE_INTEGER；超过该值的整数在浏览器里会丢精度
MAX_SAFE_INTEGER = 2 ** 53 - 1  # JavaScript Number 可精确表示的最大整数


# 递归转换函数：只处理容器与整数，其他类型原样返回，保证输出仍是可序列化的普通结构
def stringify_big_int(value):
    """递归把超出 JS 安全范围的整数转成字符串，避免雪花主键在前端丢失精度。"""
    # bool 必须先判断：Python 中 True/False 是 int 的子类，否则会被误转成字符串
    if isinstance(value, bool):  # bool 是 int 子类，需先排除
        return value
    # 整数：安全范围内保留数字类型（便于前端做运算），超出范围转字符串保全精度
    if isinstance(value, int):
        return str(value) if abs(value) > MAX_SAFE_INTEGER else value  # 小整数保持原样
    # 字典：逐值递归，保持原有键顺序
    if isinstance(value, dict):
        return {key: stringify_big_int(item) for key, item in value.items()}
    # 列表/元组：逐项递归，统一输出为 list（JSON 不区分元组）
    if isinstance(value, (list, tuple)):
        return [stringify_big_int(item) for item in value]
    # 其余类型（字符串、None、日期等）不在本函数职责内，原样交给 DRF 序列化
    return value


# 全局渲染器：被 settings 的 DEFAULT_RENDERER_CLASSES 引用，覆盖所有 DRF 响应
class BigIntJSONRenderer(JSONRenderer):
    """全局 JSON 渲染器：雪花主键以字符串输出，前端回传时不再丢精度。"""

    # 在父类真正序列化前先做一次递归转换，其余渲染参数原样透传
    def render(self, data, accepted_media_type=None, renderer_context=None):
        """渲染前统一处理大整数。"""
        # 先转换再交给父类序列化，保证 JSON 中的大整数已是字符串
        return super().render(stringify_big_int(data), accepted_media_type, renderer_context)


# 成功响应快捷函数：业务码固定 200，HTTP 状态保持默认 200
def ok(data=None, msg='success'):
    """成功响应：业务码固定 200，data 可以是对象、列表或 None。"""
    return Response({'code': 200, 'msg': msg, 'data': data})  # HTTP 状态保持 200，业务码由 body 承载


# 失败响应快捷函数：调用方显式传入业务码，便于前端按 code 分支处理
def fail(msg='error', code=500, data=None):
    """失败响应：自定义业务码与提示文案，便于前端按 code 分支处理。"""
    return Response({'code': code, 'msg': msg, 'data': data})  # 同样不改 HTTP 状态，保持统一解析方式
