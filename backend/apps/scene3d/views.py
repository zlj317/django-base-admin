"""3D 可视化模块视图：场景编辑/发布/分享、对象、绑定、告警、巡检、权限与访问日志。"""
import json  # 解析/序列化场景配置与路径点位
import os  # 拼接模型上传的存储路径
import time  # 统一生成 YYYY-MM-DD HH:MM:SS 时间字符串
import uuid  # 生成分享令牌与上传文件名
from datetime import datetime, timedelta  # 分享有效期计算

from django.conf import settings  # 读取 MEDIA_ROOT
from rest_framework import parsers, views, viewsets  # ViewSet / APIView / 文件解析器
from rest_framework.permissions import AllowAny  # 分享页免登录访问

from common.auth import LoginRequired  # 分享接口显式声明免登录
from common.pagination import StandardPagination  # 统一分页结构
from common.permissions import PermissionCheck  # 登录 + 按钮权限校验
from common.response import fail, ok  # 统一响应体
from common.snowflake import next_id  # 关联复制时手工生成雪花主键

from apps.file.models import WfFile  # 复用附件表登记模型文件

from .models import (  # 本模块 13 张表
    Scene3dAccessLog, Scene3dAlarmRecord, Scene3dAlarmRule, Scene3dCategory,
    Scene3dDataBind, Scene3dModelResource, Scene3dPatrolRecord, Scene3dPatrolRoute,
    Scene3dScene, Scene3dSceneObject, Scene3dScenePermission, Scene3dSceneVersion,
    Scene3dTemplate,
)
from .serializers import (  # 对应序列化器
    Scene3dAccessLogSerializer, Scene3dAlarmRecordSerializer, Scene3dAlarmRuleSerializer,
    Scene3dCategorySerializer, Scene3dDataBindSerializer, Scene3dModelResourceSerializer,
    Scene3dPatrolRecordSerializer, Scene3dPatrolRouteSerializer, Scene3dSceneObjectSerializer,
    Scene3dScenePermissionSerializer, Scene3dSceneSerializer, Scene3dSceneVersionSerializer,
    Scene3dTemplateSerializer,
)

# 允许上传的模型/贴图扩展名（服务端白名单，避免任意文件落盘）
UPLOAD_EXT = {'.glb', '.gltf', '.jpg', '.jpeg', '.png', '.webp', '.hdr'}  # 支持的主流 3D 与贴图格式
MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 单文件上限 50MB
MAX_CONFIG_SIZE = 2 * 1024 * 1024  # 场景配置快照上限 2MB
MAX_OBJECTS = 5000  # 单个场景对象上限，防止误传超大数组拖垮服务
ALLOWED_BIND_TABLES = {  # 数据绑定允许引用的表白名单（禁止用户输入任意 SQL）
    'wf_file',  # 文件附件
    'sys_user',  # 用户
    'scene3d_scene',  # 场景主表
    'scene3d_scene_object',  # 场景对象（用于演示读数）
    'scene3d_alarm_record',  # 告警记录
}


def _now():
    """返回当前时间字符串，与手工 SQL 的 datetime 写入格式一致。"""
    return time.strftime('%Y-%m-%d %H:%M:%S')  # 秒级精度足够


def _json(value, default=None):
    """把 JSON 字段入参统一转成 Python 对象；前端 textarea 可能传字符串。"""
    if value is None:  # 未传时使用默认值
        return default
    if isinstance(value, (dict, list)):  # 已经是对象/数组
        return value
    if isinstance(value, str):  # 字符串尝试解析
        try:
            return json.loads(value)  # 合法 JSON 正常解析
        except (ValueError, TypeError):
            return default  # 非法 JSON 回退默认值，由调用方决定是否报错
    return default  # 其他类型按默认值处理


def _vec(value, default=None):
    """校验并归一化三维向量，非法值回退默认向量。"""
    data = _json(value)  # 兼容字符串
    if not isinstance(data, dict):  # 必须是对象
        return default or {'x': 0, 'y': 0, 'z': 0}  # 兜底
    out = {}  # 只保留 x/y/z 三个分量
    for key in ('x', 'y', 'z'):  # 逐个分量校验
        try:
            out[key] = round(float(data.get(key, 0)), 4)  # 保留 4 位小数，避免浮点脏值
        except (TypeError, ValueError):
            out[key] = 0.0  # 非数字按 0 处理
    return out  # 返回归一化向量


def _user(request):
    """取当前登录用户对象，未登录返回 None。"""
    return getattr(request, 'user_info', None)  # 由 JWT 认证中间件挂载


def _username(request):
    """取当前用户名，供审计字段使用。"""
    user = _user(request)  # 复用取用户逻辑
    return user.username if user else ''  # 未登录留空


def _scene_payload(scene, request=None, access_type=None):
    """组装场景详情：主表 + 对象 + 数据绑定 + 告警规则 + 授权列表。"""
    objects = Scene3dSceneObject.objects.filter(scene_id=scene.id, is_deleted=False).order_by('sort', 'id')  # 场景对象
    binds = Scene3dDataBind.objects.filter(scene_id=scene.id, is_deleted=False).order_by('id')  # 数据绑定
    rules = Scene3dAlarmRule.objects.filter(is_deleted=False, bind_id__in=[b.id for b in binds] or [0])  # 关联规则
    perms = Scene3dScenePermission.objects.filter(scene_id=scene.id, is_deleted=False)  # 授权列表
    data = Scene3dSceneSerializer(scene).data  # 主表序列化
    data['scene_config'] = _json(data.get('scene_config'), {})  # 兼容历史上被存成字符串的配置，统一返回对象
    data['objects'] = Scene3dSceneObjectSerializer(objects, many=True).data  # 追加对象数组
    data['bindings'] = Scene3dDataBindSerializer(binds, many=True).data  # 追加绑定数组
    data['rules'] = Scene3dAlarmRuleSerializer(rules, many=True).data  # 追加规则数组
    data['permissions'] = Scene3dScenePermissionSerializer(perms, many=True).data  # 追加授权数组
    if request is not None:  # 需要记录访问日志时
        ip = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip() or request.META.get('REMOTE_ADDR', '')  # 取真实 IP
        user = _user(request)  # 访问用户
        Scene3dAccessLog.objects.create(  # 写入访问日志
            id=next_id(),  # 雪花主键
            scene_id=scene.id,  # 场景
            user_id=user.id if user else None,  # 匿名访问为空
            access_ip=ip[:50],  # 截断到列宽
            access_ua=(request.META.get('HTTP_USER_AGENT') or '')[:1000],  # 浏览器标识
            access_type=access_type or '系统登录',  # 访问方式
            stay_seconds=0,  # 初始停留时长，前端离开时不再回写（接口未提供上报）
            access_time=_now(),  # 访问时间
        )
    return data  # 返回完整详情


def _next_version(scene_id):
    """生成下一个版本号 vN，按现有版本数量递增。"""
    count = Scene3dSceneVersion.objects.filter(scene_id=scene_id, is_deleted=False).count()  # 统计已有版本
    return f'v{count + 1}'  # 版本号从 v1 开始


def _snapshot(scene, desc, is_publish=0, request=None):
    """把场景主配置与对象数组写入版本快照。"""
    objects = []  # 对象快照数组
    for row in Scene3dSceneObject.objects.filter(scene_id=scene.id, is_deleted=False).order_by('sort', 'id'):  # 逐条导出
        objects.append({
            'object_name': row.object_name, 'object_code': row.object_code, 'resource_id': row.resource_id,
            'parent_id': row.parent_id, 'position': row.position, 'rotation': row.rotation,
            'scale': row.scale, 'label_text': row.label_text, 'is_show_label': row.is_show_label,
            'sort': row.sort, 'remark': row.remark,
        })  # 只保留可回滚必要字段
    payload = {'scene_config': _json(scene.scene_config, {}), 'objects': objects}  # 快照结构（配置统一为对象）
    version = Scene3dSceneVersion.objects.create(  # 落库版本记录
        id=next_id(),  # 雪花主键
        scene_id=scene.id,  # 场景
        version_no=_next_version(scene.id),  # 版本号
        version_desc=desc[:500],  # 版本描述
        snapshot_config=payload,  # 全量快照
        is_publish=is_publish,  # 是否发布版本
        create_by=_username(request) if request else '',  # 操作人
        create_time=_now(),  # 生成时间
    )
    return version  # 返回版本对象


def _replace_objects(scene_id, rows, request):
    """用提交的 objects 数组整体替换场景对象：按 object_code 更新，缺失项逻辑删除。"""
    existing = {row.object_code: row for row in Scene3dSceneObject.objects.filter(scene_id=scene_id, is_deleted=False)}  # 现有对象索引
    keep_codes = set()  # 本次保留的编码
    for item in rows:  # 逐条处理
        code = str(item.get('object_code') or '').strip()[:50]  # 编码必填
        if not code:  # 缺少编码直接跳过
            continue
        resource_id = item.get('resource_id')  # 模型资源
        if not resource_id or not Scene3dModelResource.objects.filter(id=resource_id, is_deleted=False).exists():  # 资源必须存在
            continue  # 非法资源跳过，避免脏关联
        keep_codes.add(code)  # 记录保留编码
        row = existing.get(code)  # 已存在则更新
        if not row:  # 新对象
            row = Scene3dSceneObject(id=next_id(), scene_id=scene_id, object_code=code, create_by=_username(request), create_time=_now())  # 新建实例
        row.object_name = str(item.get('object_name') or code)[:100]  # 对象名称
        row.resource_id = resource_id  # 模型资源
        row.parent_id = item.get('parent_id') or None  # 父对象
        row.position = _vec(item.get('position'))  # 坐标
        row.rotation = _vec(item.get('rotation'))  # 旋转
        row.scale = _vec(item.get('scale'), {'x': 1, 'y': 1, 'z': 1})  # 缩放
        row.label_text = (item.get('label_text') or '')[:200]  # 标签
        row.is_show_label = 1 if item.get('is_show_label', 1) in (1, '1', True, 'true') else 0  # 标签开关
        row.sort = int(item.get('sort') or 0)  # 排序
        row.remark = (item.get('remark') or '')[:500]  # 备注
        row.update_by = _username(request)  # 更新人
        row.update_time = _now()  # 更新时间
        row.save()  # 写入数据库
    stale = [row for code, row in existing.items() if code not in keep_codes]  # 本次提交中不存在的对象
    for row in stale:  # 逐条逻辑删除
        row.is_deleted = 1
        row.update_by = _username(request)
        row.update_time = _now()
        row.save(update_fields=['is_deleted', 'update_by', 'update_time'])  # 只更新三个字段
    return len(keep_codes)  # 返回保留对象数量


class Scene3dCrudViewSet(viewsets.ViewSet):
    """3D 模块 CRUD 基类：在通用权限映射上追加自定义 action 的权限标识。"""

    model = None  # 子类指定模型
    serializer_class = None  # 子类指定序列化器
    perm_prefix = 'scene3d'  # 权限前缀
    filter_map = {}  # 查询参数映射
    order_by = '-id'  # 默认排序
    extra_perm_map = {}  # 自定义动作的权限标识

    @property
    def permission_classes(self):
        """按通用 CRUD + 自定义动作拼出 perm_map。"""
        prefix = self.perm_prefix  # 权限前缀
        self.perm_map = {
            'list': f'{prefix}:list',  # 列表
            'create': f'{prefix}:create',  # 新增
            'update': f'{prefix}:update',  # 编辑
            'delete': f'{prefix}:delete',  # 删除
        }
        self.perm_map.update(self.extra_perm_map)  # 合并自定义动作权限
        return [PermissionCheck]  # 统一使用登录 + 权限校验

    def get_queryset(self):
        """默认过滤逻辑删除并按 order_by 排序。"""
        return self.model.objects.filter(is_deleted=0).order_by(self.order_by)  # 统一收敛删除条件

    def get_serializer_class(self):
        """返回子类声明的序列化器。"""
        return self.serializer_class  # 不做动态切换

    def apply_filters(self, queryset, request):
        """按 filter_map 过滤。"""
        for param, lookup in self.filter_map.items():  # 逐项处理
            value = request.query_params.get(param)  # 取查询参数
            if value not in (None, ''):  # 空值忽略
                queryset = queryset.filter(**{f'{param}__{lookup}': value})  # 动态 lookup
        return queryset  # 返回过滤后的查询集

    def list(self, request):
        """标准分页列表。"""
        queryset = self.apply_filters(self.get_queryset(), request)  # 过滤
        return StandardPagination(request).paginate(queryset, self.get_serializer_class())  # 分页输出

    def create(self, request):
        """新增：校验唯一字段、补审计字段。"""
        for field in self.model._meta.fields:  # 遍历字段找唯一键
            if not field.unique or field.primary_key or not hasattr(self.model, 'is_deleted'):
                continue
            value = request.data.get(field.attname)  # 提交值
            if value in (None, ''):
                continue
            if self.model.objects.filter(**{field.attname: value, 'is_deleted': 0}).exists():  # 未删除记录占用唯一键
                return fail(f'{field.verbose_name}已存在', code=400)  # 明确提示
        serializer = self.serializer_class(data=request.data)  # 绑定入参
        serializer.is_valid(raise_exception=True)  # 字段校验
        now = _now()  # 统一时间
        instance = serializer.save(  # 落库并补审计字段
            create_by=_username(request), create_time=now, update_by=_username(request), update_time=now,
        )
        return ok(self.serializer_class(instance).data, '新增成功')  # 返回完整对象

    def update(self, request, pk=None):
        """部分更新：仅允许修改未删除记录。"""
        instance = self.get_queryset().filter(pk=pk).first()  # 定位记录
        if not instance:
            return fail('记录不存在', code=404)  # 业务 404
        serializer = self.serializer_class(instance, data=request.data, partial=True)  # 部分更新
        serializer.is_valid(raise_exception=True)  # 校验
        serializer.save(update_by=_username(request), update_time=_now())  # 补审计字段
        return ok(self.serializer_class(instance).data, '修改成功')  # 返回最新对象

    def delete(self, request):
        """批量逻辑删除。"""
        ids = request.data.get('ids') or []  # 兼容 null
        if not ids:
            return ok(None, '请选择要删除的数据')  # 未选择时提示
        self.get_queryset().filter(id__in=ids).update(is_deleted=1, update_by=_username(request), update_time=_now())  # 逻辑删除
        return ok(None, '删除成功')  # 完成

    def status(self, request, pk=None):
        """启用/停用。"""
        instance = self.get_queryset().filter(pk=pk).first()  # 定位记录
        if not instance:
            return fail('记录不存在', code=404)  # 业务 404
        if 'status' not in (request.data or {}):  # 必须传 status
            return fail('未提供状态字段', code=400)  # 明确提示
        instance.status = request.data.get('status')  # 赋值
        instance.update_by = _username(request)  # 更新人
        instance.update_time = _now()  # 更新时间
        instance.save()  # 保存
        return ok(self.serializer_class(instance).data, '状态更新成功')  # 返回最新对象


class Scene3dCategoryViewSet(Scene3dCrudViewSet):
    """场景分类管理。"""
    model = Scene3dCategory  # 分类模型
    serializer_class = Scene3dCategorySerializer  # 分类序列化器
    perm_prefix = 'scene3d:category'  # 权限前缀
    filter_map = {'category_name': 'icontains', 'status': 'exact'}  # 名称模糊 + 状态精确
    order_by = 'sort'  # 排序号升序
    extra_perm_map = {'status': 'scene3d:category:update'}  # 状态启停沿用编辑权限


class Scene3dTemplateViewSet(Scene3dCrudViewSet):
    """场景模板管理。"""
    model = Scene3dTemplate  # 模板模型
    serializer_class = Scene3dTemplateSerializer  # 模板序列化器
    perm_prefix = 'scene3d:template'  # 权限前缀
    filter_map = {'template_name': 'icontains', 'category_id': 'exact', 'status': 'exact'}  # 常用筛选
    order_by = 'sort'  # 排序号升序
    extra_perm_map = {'status': 'scene3d:template:update'}  # 状态启停沿用编辑权限


class Scene3dSceneViewSet(Scene3dCrudViewSet):
    """场景管理：详情、保存、发布/下线、复制、版本、回滚、分享、访问日志、导出。"""
    model = Scene3dScene  # 场景模型
    serializer_class = Scene3dSceneSerializer  # 场景序列化器
    perm_prefix = 'scene3d:scene'  # 权限前缀
    filter_map = {'scene_name': 'icontains', 'scene_code': 'icontains', 'category_id': 'exact',
                  'scene_status': 'exact', 'create_by': 'exact'}  # 列表筛选
    order_by = '-id'  # 最新创建在前
    extra_perm_map = {  # 自定义动作权限
        'detail_info': 'scene3d:scene:list',  # 查看详情沿用列表权限（动作名不可用 detail：DRF 会占用该类属性）
        'save': 'scene3d:scene:update',  # 保存草稿
        'publish': 'scene3d:scene:publish',  # 发布
        'offline': 'scene3d:scene:publish',  # 下线同发布权限
        'copy': 'scene3d:scene:create',  # 复制
        'rollback': 'scene3d:scene:version',  # 版本回滚
        'versions': 'scene3d:scene:list',  # 版本列表
        'share': 'scene3d:scene:share',  # 生成分享
        'visit_log': 'scene3d:scene:list',  # 访问日志
        'export_config': 'scene3d:scene:list',  # 配置导出
    }

    def detail_info(self, request, pk=None):
        """场景详情（含对象、绑定、规则、授权），并记录一次访问日志。

        注意：方法名不能叫 detail —— DRF ViewSetMixin.as_view 会执行 cls.detail = None，
        若同名会被覆盖成 None，导致分发时报 'NoneType' object is not callable。
        """
        scene = self.get_queryset().filter(pk=pk).first()  # 定位场景
        if not scene:
            return fail('场景不存在', code=404)  # 业务 404
        return ok(_scene_payload(scene, request), '查询成功')  # 返回完整详情

    def save(self, request, pk=None):
        """保存场景草稿：更新配置 + 整体替换对象 + 生成版本快照。"""
        scene = self.get_queryset().filter(pk=pk).first()  # 定位场景
        if not scene:
            return fail('场景不存在', code=404)  # 业务 404
        body = request.data or {}  # 请求体
        config = _json(body.get('scene_config'), None)  # 新配置
        if config is not None and not isinstance(config, dict):
            return fail('scene_config 必须是对象', code=400)  # 结构校验
        raw_objects = body.get('objects')  # 原始对象数组入参
        objects = _json(raw_objects, None)  # 解析对象数组
        if raw_objects is not None and (objects is None or not isinstance(objects, list) or len(objects) > MAX_OBJECTS):
            return fail(f'objects 必须是数组且不超过 {MAX_OBJECTS} 条', code=400)  # 先校验再落库，避免主表已改而对象失败
        base = dict(_json(scene.scene_config, {}))  # 以现有配置为底，保留分享令牌等隐藏字段
        if config is not None:
            config.pop('share', None)  # 分享令牌不可被前端覆盖
            base.update(config)  # 浅合并
        size = len(json.dumps(base, ensure_ascii=False).encode('utf-8'))  # 配置体积
        if size > MAX_CONFIG_SIZE:
            return fail('场景配置超过 2MB，请精简后再保存', code=400)  # 体积限制
        scene.scene_config = base  # 赋值
        if body.get('remark') is not None:
            scene.remark = str(body.get('remark'))[:1000]  # 描述可同步更新
        scene.update_by = _username(request)  # 更新人
        scene.update_time = _now()  # 更新时间
        scene.save()  # 保存主表
        if objects is not None:
            _replace_objects(scene.id, objects, request)  # 整体替换对象
        _snapshot(scene, body.get('version_desc') or '手动保存场景配置', 0, request)  # 生成版本
        return ok(_scene_payload(scene), '保存成功')  # 返回最新详情

    def publish(self, request, pk=None):
        """发布场景：校验对象与资源，写发布版本。"""
        scene = self.get_queryset().filter(pk=pk).first()  # 定位场景
        if not scene:
            return fail('场景不存在', code=404)  # 业务 404
        objects = list(Scene3dSceneObject.objects.filter(scene_id=scene.id, is_deleted=False))  # 场景对象
        if not objects:
            return fail('场景暂无对象，无法发布', code=400)  # 发布前置校验
        resource_ids = {obj.resource_id for obj in objects}  # 引用的资源集合
        valid = Scene3dModelResource.objects.filter(id__in=resource_ids, is_deleted=False).count()  # 有效资源数
        if valid < len(resource_ids):
            return fail('存在引用了已删除模型的场景对象，请先修复', code=400)  # 关联完整性校验
        scene.scene_status = 1  # 已发布
        scene.update_by = _username(request)  # 更新人
        scene.update_time = _now()  # 更新时间
        scene.save()  # 落库
        _snapshot(scene, '发布场景', 1, request)  # 发布版本快照
        return ok(self.serializer_class(scene).data, '发布成功')  # 返回场景

    def offline(self, request, pk=None):
        """下线场景：状态置为 2，保留已有版本。"""
        scene = self.get_queryset().filter(pk=pk).first()  # 定位场景
        if not scene:
            return fail('场景不存在', code=404)  # 业务 404
        scene.scene_status = 2  # 已下线
        scene.update_by = _username(request)  # 更新人
        scene.update_time = _now()  # 更新时间
        scene.save()  # 落库
        return ok(self.serializer_class(scene).data, '已下线')  # 返回场景

    def copy(self, request, pk=None):
        """复制场景：复制对象、绑定、规则，并重建对象间的关联关系。"""
        scene = self.get_queryset().filter(pk=pk).first()  # 源场景
        if not scene:
            return fail('场景不存在', code=404)  # 业务 404
        code = (request.data or {}).get('scene_code') or f"SC-{time.strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"  # 新编码
        if Scene3dScene.objects.filter(scene_code=code).exists():
            return fail('场景编码已存在（含已删除记录）', code=400)  # 唯一键提示
        new_scene = Scene3dScene.objects.create(  # 复制主表
            id=next_id(), scene_name=f"{scene.scene_name}-副本"[:100], scene_code=code[:50],
            category_id=scene.category_id, template_id=scene.template_id, scene_status=0,
            thumbnail_file_id=scene.thumbnail_file_id, scene_config=_json(scene.scene_config, {}),
            remark=f'复制自 {scene.scene_name}'[:1000], create_by=_username(request), create_time=_now(),
            update_by=_username(request), update_time=_now(),
        )
        id_map = {}  # 旧对象 ID -> 新对象 ID
        for obj in Scene3dSceneObject.objects.filter(scene_id=scene.id, is_deleted=False).order_by('sort', 'id'):  # 复制对象
            new_id = next_id()  # 预生成新主键
            id_map[obj.id] = new_id  # 记录映射
            Scene3dSceneObject.objects.create(  # 写入副本
                id=new_id, scene_id=new_scene.id, resource_id=obj.resource_id, object_name=obj.object_name,
                object_code=obj.object_code, parent_id=None, position=obj.position, rotation=obj.rotation,
                scale=obj.scale, label_text=obj.label_text, is_show_label=obj.is_show_label, sort=obj.sort,
                remark=obj.remark, create_by=_username(request), create_time=_now(), update_by=_username(request), update_time=_now(),
            )
        for obj in Scene3dSceneObject.objects.filter(scene_id=new_scene.id, is_deleted=False):  # 修正父对象映射
            if obj.parent_id in id_map:  # 父对象也复制了
                obj.parent_id = id_map[obj.parent_id]
                obj.save(update_fields=['parent_id'])
        bind_map = {}  # 旧绑定 ID -> 新绑定 ID
        for bind in Scene3dDataBind.objects.filter(scene_id=scene.id, is_deleted=False):  # 复制绑定
            new_id = next_id()  # 新主键
            bind_map[bind.id] = new_id  # 记录映射
            Scene3dDataBind.objects.create(  # 写入副本
                id=new_id, scene_id=new_scene.id, object_id=id_map.get(bind.object_id, bind.object_id),
                bind_name=bind.bind_name, data_source_type=bind.data_source_type, source_config=bind.source_config,
                refresh_interval=bind.refresh_interval, mapping_rule=bind.mapping_rule, status=bind.status,
                remark=bind.remark, create_by=_username(request), create_time=_now(), update_by=_username(request), update_time=_now(),
            )
        for rule in Scene3dAlarmRule.objects.filter(bind_id__in=list(bind_map.keys()) or [0], is_deleted=False):  # 复制规则
            Scene3dAlarmRule.objects.create(  # 规则绑定到新绑定
                id=next_id(), bind_id=bind_map[rule.bind_id], rule_name=rule.rule_name,
                compare_operator=rule.compare_operator, threshold_value=rule.threshold_value,
                alarm_level=rule.alarm_level, alarm_effect=rule.alarm_effect,
                is_auto_notice=rule.is_auto_notice, is_auto_workflow=rule.is_auto_workflow,
                workflow_def_id=rule.workflow_def_id, status=rule.status, remark=rule.remark,
                create_by=_username(request), create_time=_now(), update_by=_username(request), update_time=_now(),
            )
        return ok(self.serializer_class(new_scene).data, '复制成功')  # 返回新场景

    def versions(self, request, pk=None):
        """版本列表：倒序返回，剔除体积较大的快照内容。"""
        scene = self.get_queryset().filter(pk=pk).first()  # 定位场景
        if not scene:
            return fail('场景不存在', code=404)  # 业务 404
        rows = Scene3dSceneVersion.objects.filter(scene_id=scene.id, is_deleted=False).order_by('-create_time', '-id')  # 版本倒序
        data = []  # 输出去掉 snapshot_config 的数组
        for row in rows:  # 逐条处理
            item = Scene3dSceneVersionSerializer(row).data  # 序列化
            item.pop('snapshot_config', None)  # 列表不返回快照正文，避免响应过大
            data.append(item)  # 收集
        return ok({'list': data, 'total': len(data)}, '查询成功')  # 简化结构

    def rollback(self, request, pk=None):
        """回滚到指定版本：恢复配置与对象，并生成一条新版本记录。"""
        scene = self.get_queryset().filter(pk=pk).first()  # 定位场景
        if not scene:
            return fail('场景不存在', code=404)  # 业务 404
        version_id = (request.data or {}).get('version_id')  # 目标版本
        version = Scene3dSceneVersion.objects.filter(id=version_id, scene_id=scene.id, is_deleted=False).first()  # 精确定位
        if not version:
            return fail('版本不存在', code=404)  # 业务 404
        snapshot = _json(version.snapshot_config, {})  # 快照内容
        config = _json(snapshot.get('scene_config'), {})  # 场景配置
        if isinstance(config, dict):
            config.pop('share', None)  # 回滚不覆盖分享令牌
            scene.scene_config = config  # 恢复配置
        scene.update_by = _username(request)  # 更新人
        scene.update_time = _now()  # 更新时间
        scene.save()  # 保存
        _replace_objects(scene.id, _json(snapshot.get('objects'), []), request)  # 恢复对象
        _snapshot(scene, f"回滚至 {version.version_no}", 0, request)  # 记录回滚版本
        return ok(_scene_payload(scene), '回滚成功')  # 返回最新详情

    def share(self, request, pk=None):
        """生成分享链接：token 写入场景配置，有效期 1~30 天。"""
        scene = self.get_queryset().filter(pk=pk).first()  # 定位场景
        if not scene:
            return fail('场景不存在', code=404)  # 业务 404
        if scene.scene_status != 1:
            return fail('仅已发布场景支持分享', code=400)  # 状态校验
        try:
            days = int((request.data or {}).get('expire_days') or 7)  # 默认 7 天
        except (TypeError, ValueError):
            return fail('expire_days 必须是整数', code=400)  # 类型校验
        if days < 1 or days > 30:
            return fail('有效期需在 1~30 天之间', code=400)  # 范围校验
        token = uuid.uuid4().hex  # 随机令牌
        expire = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')  # 过期时间
        config = dict(_json(scene.scene_config, {}))  # 复制配置（兼容字符串历史值）
        config['share'] = {'token': token, 'expire': expire, 'create_by': _username(request)}  # 写入令牌
        scene.scene_config = config  # 赋值
        scene.update_by = _username(request)  # 更新人
        scene.update_time = _now()  # 更新时间
        scene.save()  # 保存
        return ok({'token': token, 'expire': expire, 'share_url': f'/scene3d/share/{token}'}, '分享链接已生成')  # 返回链接

    def visit_log(self, request, pk=None):
        """某场景的访问日志分页列表。"""
        scene = self.get_queryset().filter(pk=pk).first()  # 定位场景
        if not scene:
            return fail('场景不存在', code=404)  # 业务 404
        rows = Scene3dAccessLog.objects.filter(scene_id=scene.id, is_deleted=False).order_by('-access_time', '-id')  # 倒序
        return StandardPagination(request).paginate(rows, Scene3dAccessLogSerializer)  # 标准分页

    def export_config(self, request, pk=None):
        """导出场景配置 JSON，供归档或跨环境导入。"""
        scene = self.get_queryset().filter(pk=pk).first()  # 定位场景
        if not scene:
            return fail('场景不存在', code=404)  # 业务 404
        return ok(_scene_payload(scene), '导出成功')  # 返回完整配置


class Scene3dObjectViewSet(Scene3dCrudViewSet):
    """场景对象管理：支持按场景、名称筛选。"""
    model = Scene3dSceneObject  # 对象模型
    serializer_class = Scene3dSceneObjectSerializer  # 对象序列化器
    perm_prefix = 'scene3d:object'  # 权限前缀
    filter_map = {'scene_id': 'exact', 'object_name': 'icontains', 'object_code': 'exact'}  # 常用筛选
    order_by = 'sort'  # 排序号


class Scene3dBindingViewSet(Scene3dCrudViewSet):
    """数据绑定管理，含数值预览（白名单表的模拟读数，不执行任意 SQL）。"""
    model = Scene3dDataBind  # 绑定模型
    serializer_class = Scene3dDataBindSerializer  # 绑定序列化器
    perm_prefix = 'scene3d:binding'  # 权限前缀
    filter_map = {'scene_id': 'exact', 'object_id': 'exact', 'data_source_type': 'exact', 'status': 'exact'}  # 筛选
    order_by = '-id'  # 最新在前
    extra_perm_map = {'preview': 'scene3d:binding:list'}  # 预览沿用列表权限

    def create(self, request):
        """新增前校验表名白名单，避免绑定到任意表。"""
        config = _json((request.data or {}).get('source_config'), {})  # 数据源配置
        table = config.get('table') if isinstance(config, dict) else None  # 表名
        if table and table not in ALLOWED_BIND_TABLES:
            return fail(f'数据表不在白名单内：{table}', code=400)  # 白名单拦截
        return super().create(request)  # 复用通用新增

    def update(self, request, pk=None):
        """编辑同样做表名白名单校验。"""
        config = _json((request.data or {}).get('source_config'), None)  # 仅在提交时校验
        if isinstance(config, dict) and config.get('table') and config['table'] not in ALLOWED_BIND_TABLES:
            return fail(f'数据表不在白名单内：{config["table"]}', code=400)  # 白名单拦截
        return super().update(request, pk)  # 复用通用编辑

    def preview(self, request, pk=None):
        """返回模拟读数（真实接入需实现对应数据源适配器）。"""
        bind = self.get_queryset().filter(pk=pk).first()  # 定位绑定
        if not bind:
            return fail('绑定不存在', code=404)  # 业务 404
        config = _json(bind.source_config, {})  # 配置
        field = (config.get('field') if isinstance(config, dict) else '') or 'value'  # 字段名
        seed = int(str(bind.id)[-3:]) if str(bind.id).isdigit() else 0  # 用主键尾号构造稳定伪随机
        if field in ('temperature', 'temp'):  # 温度类
            value = round(25 + (seed % 90) / 10, 1)  # 25.0~33.9
            unit = '℃'  # 单位
        elif field in ('load', 'usage', 'percent', 'humidity'):  # 负载/百分比类
            value = round(30 + (seed % 60), 1)  # 30~89.9
            unit = '%'  # 单位
        else:  # 其他字段
            value = float(seed % 100)  # 0~99
            unit = ''  # 无单位
        return ok({  # 返回预览数据
            'bind_id': bind.id, 'bind_name': bind.bind_name, 'object_id': bind.object_id,
            'value': value, 'unit': unit, 'time': _now(), 'source': bind.data_source_type,
            'note': '模拟读数；真实值需接入对应数据源适配器',  # 明确标注模拟
        }, '预览成功')

    def after_update(self, request, instance):
        """编辑绑定后保持接口简洁，无需额外同步。"""
        pass  # 预留扩展点


class Scene3dAlarmRuleViewSet(Scene3dCrudViewSet):
    """告警规则管理。"""
    model = Scene3dAlarmRule  # 规则模型
    serializer_class = Scene3dAlarmRuleSerializer  # 规则序列化器
    perm_prefix = 'scene3d:alarm'  # 权限前缀
    filter_map = {'bind_id': 'exact', 'alarm_level': 'exact', 'status': 'exact'}  # 筛选
    order_by = '-id'  # 最新在前


class Scene3dAlarmRecordViewSet(Scene3dCrudViewSet):
    """告警记录：列表、统计与确认。"""
    model = Scene3dAlarmRecord  # 记录模型
    serializer_class = Scene3dAlarmRecordSerializer  # 记录序列化器
    perm_prefix = 'scene3d:alarm'  # 与规则共用模块权限
    filter_map = {'scene_id': 'exact', 'alarm_status': 'exact', 'alarm_level': 'exact'}  # 筛选
    order_by = '-create_time'  # 最新告警在前
    extra_perm_map = {'confirm': 'scene3d:alarm:confirm', 'stats': 'scene3d:alarm:list', 'records': 'scene3d:alarm:list'}  # 自定义动作

    def list(self, request):
        """记录列表，额外支持按告警级别排序。"""
        return super().list(request)  # 复用标准分页

    def stats(self, request):
        """统计近 N 天告警数量、未确认数与级别分布。"""
        try:
            days = int(request.query_params.get('days') or 7)  # 默认 7 天
        except (TypeError, ValueError):
            return fail('days 必须是整数', code=400)  # 类型校验
        days = min(max(days, 1), 90)  # 限制 1~90 天
        start = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')  # 起始时间
        qs = Scene3dAlarmRecord.objects.filter(is_deleted=False, create_time__gte=start)  # 时间范围
        scene_id = request.query_params.get('scene_id')  # 可选场景
        if scene_id:
            qs = qs.filter(scene_id=scene_id)  # 场景过滤
        by_level = {level: qs.filter(alarm_level=level).count() for level in (1, 2, 3)}  # 三级统计
        return ok({
            'days': days,  # 统计窗口
            'total': qs.count(),  # 总数
            'unconfirmed': qs.filter(alarm_status=0).count(),  # 未确认
            'confirmed': qs.filter(alarm_status=1).count(),  # 已确认
            'closed': qs.filter(alarm_status=2).count(),  # 已闭环
            'by_level': [  # 前端图表直接使用的数组
                {'level': 1, 'name': '提示', 'value': by_level[1]},
                {'level': 2, 'name': '警告', 'value': by_level[2]},
                {'level': 3, 'name': '严重', 'value': by_level[3]},
            ],
        }, '查询成功')

    def confirm(self, request, pk=None):
        """确认告警：记录确认人/时间与处置备注。"""
        row = self.get_queryset().filter(pk=pk).first()  # 定位记录
        if not row:
            return fail('告警记录不存在', code=404)  # 业务 404
        if row.alarm_status != 0:
            return fail('该告警已确认或已闭环', code=400)  # 重复确认拦截
        user = _user(request)  # 当前用户
        row.alarm_status = 1  # 已确认
        row.confirm_user_id = user.id if user else None  # 确认人
        row.confirm_time = _now()  # 确认时间
        if (request.data or {}).get('remark'):  # 处置备注可选
            row.remark = str(request.data.get('remark'))[:1000]  # 覆盖备注
        row.save()  # 保存
        return ok(self.serializer_class(row).data, '确认成功')  # 返回最新记录


class Scene3dPatrolRouteViewSet(Scene3dCrudViewSet):
    """巡检路线管理，含「开始巡检」生成记录。"""
    model = Scene3dPatrolRoute  # 路线模型
    serializer_class = Scene3dPatrolRouteSerializer  # 路线序列化器
    perm_prefix = 'scene3d:route'  # 权限前缀
    filter_map = {'scene_id': 'exact', 'route_name': 'icontains', 'status': 'exact'}  # 筛选
    order_by = '-id'  # 最新在前
    extra_perm_map = {'play': 'scene3d:route:play'}  # 开始巡检

    def play(self, request, pk=None):
        """开始巡检：生成一条进行中的巡检记录并返回路线点位。"""
        route = self.get_queryset().filter(pk=pk).first()  # 定位路线
        if not route:
            return fail('巡检路线不存在', code=404)  # 业务 404
        if route.status != 1:
            return fail('路线已停用', code=400)  # 状态校验
        points = _json(route.way_points, [])  # 点位
        if not isinstance(points, list) or not points:
            return fail('路线暂无有效点位，无法启动巡检', code=400)  # 点位校验
        user = _user(request)  # 巡检人
        code = f"XJ-{time.strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:3].upper()}"  # 巡检单号
        record = Scene3dPatrolRecord.objects.create(  # 生成巡检记录
            id=next_id(), scene_id=route.scene_id, route_id=route.id, patrol_code=code,
            patrol_user_id=user.id if user else 0, start_time=_now(), patrol_status=0,
            abnormal_count=0, remark='前端漫游巡检自动创建',
        )
        return ok({
            'record': Scene3dPatrolRecordSerializer(record).data,  # 记录
            'way_points': points,  # 路径点位
            'speed': float(route.speed),  # 漫游速度
            'cycle': route.cycle_flag,  # 是否循环
        }, '巡检已开始')


class Scene3dPatrolRecordViewSet(Scene3dCrudViewSet):
    """巡检记录：只读列表。"""
    model = Scene3dPatrolRecord  # 记录模型
    serializer_class = Scene3dPatrolRecordSerializer  # 记录序列化器
    perm_prefix = 'scene3d:route'  # 沿用巡检权限
    filter_map = {'scene_id': 'exact', 'route_id': 'exact', 'patrol_status': 'exact', 'patrol_code': 'icontains'}  # 筛选
    order_by = '-start_time'  # 最新在前


class Scene3dPermissionViewSet(Scene3dCrudViewSet):
    """场景访问权限管理。"""
    model = Scene3dScenePermission  # 权限模型
    serializer_class = Scene3dScenePermissionSerializer  # 权限序列化器
    perm_prefix = 'scene3d:permission'  # 权限前缀
    filter_map = {'scene_id': 'exact', 'target_type': 'exact', 'permission_type': 'exact'}  # 筛选
    order_by = '-id'  # 最新在前

    def create(self, request):
        """新增前校验授权对象类型与目标是否存在。"""
        target_type = (request.data or {}).get('target_type')  # role/user/dept
        target_id = (request.data or {}).get('target_id')  # 目标主键
        if target_type not in ('role', 'user', 'dept'):
            return fail('target_type 只能是 role/user/dept', code=400)  # 类型校验
        from apps.system.models import SysRole, SysUser, SysDept  # 延迟导入
        model = {'role': SysRole, 'user': SysUser, 'dept': SysDept}[target_type]  # 对应模型
        if not target_id or not model.objects.filter(id=target_id).exists():
            return fail('授权对象不存在', code=400)  # 目标校验
        return super().create(request)  # 复用通用新增


class Scene3dAccessLogViewSet(Scene3dCrudViewSet):
    """访问日志：只读分页。"""
    model = Scene3dAccessLog  # 日志模型
    serializer_class = Scene3dAccessLogSerializer  # 日志序列化器
    perm_prefix = 'scene3d:scene'  # 沿用场景查看权限
    filter_map = {'scene_id': 'exact', 'access_type': 'exact', 'username': 'exact'}  # 筛选
    order_by = '-access_time'  # 最新在前
    extra_perm_map = {'list': 'scene3d:scene:list'}  # 列表

    def delete(self, request):
        """访问日志不提供删除。"""
        return fail('访问日志不支持删除', code=403)  # 审计数据保护


class Scene3dModelResourceViewSet(Scene3dCrudViewSet):
    """模型资源管理：上传、预览、删除。"""
    model = Scene3dModelResource  # 模型资源
    serializer_class = Scene3dModelResourceSerializer  # 序列化器
    perm_prefix = 'scene3d:model'  # 权限前缀
    filter_map = {'model_name': 'icontains', 'model_type': 'exact', 'status': 'exact'}  # 筛选
    order_by = 'sort'  # 排序号
    extra_perm_map = {'upload': 'scene3d:model:upload', 'preview': 'scene3d:model:list'}  # 上传/预览
    parser_classes = [parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser]  # 支持文件表单

    def upload(self, request):
        """上传模型/贴图文件：扩展名白名单 + 50MB 限制，登记 wf_file 后写入资源表。"""
        upload = request.FILES.get('file')  # 文件对象
        if not upload:
            return fail('请选择要上传的文件', code=400)  # 必填校验
        ext = os.path.splitext(upload.name)[1].lower()  # 扩展名
        if ext not in UPLOAD_EXT:
            return fail(f'不支持的文件类型 {ext}，仅支持 {"/".join(sorted(UPLOAD_EXT))}', code=400)  # 白名单
        if upload.size > MAX_UPLOAD_SIZE:
            return fail('文件超过 50MB 限制', code=400)  # 大小限制
        rel_dir = os.path.join('uploads', 'scene3d', time.strftime('%Y'), time.strftime('%m'))  # 分年月存放
        abs_dir = os.path.join(settings.MEDIA_ROOT or 'media', rel_dir)  # 绝对目录
        os.makedirs(abs_dir, exist_ok=True)  # 确保目录存在
        safe_name = f'{uuid.uuid4().hex[:12]}_{os.path.basename(upload.name)}'  # 随机前缀防重名
        abs_path = os.path.join(abs_dir, safe_name)  # 目标绝对路径
        with open(abs_path, 'wb') as target:  # 流式写入磁盘
            for chunk in upload.chunks():  # 分块读取，避免大文件占满内存
                target.write(chunk)
        storage_rel = os.path.join(rel_dir, safe_name).replace(os.sep, '/')  # 存相对路径到数据库
        file_row = WfFile.objects.create(  # 复用附件表登记，便于统一下载/回收
            id=next_id(), file_name=upload.name[:255], storage_type='local',
            storage_path=storage_rel, file_size=upload.size, file_ext=ext.lstrip('.'),
            biz_type='scene3d_model', create_by=_username(request), create_time=_now(),
            update_by=_username(request), update_time=_now(),
        )
        model_code = (request.data.get('model_code') or f'MD-{time.strftime("%y%m%d%H%M%S")}').strip()[:50]  # 模型编码
        if Scene3dModelResource.objects.filter(model_code=model_code).exists():
            return fail('模型编码已存在（含已删除记录）', code=400)  # 唯一键提示
        resource = Scene3dModelResource.objects.create(  # 写入资源表
            id=next_id(), model_name=(request.data.get('model_name') or upload.name)[:100],
            model_code=model_code, model_type=(request.data.get('model_type') or 'model')[:30],
            file_id=file_row.id, triangle_count=int(request.data.get('triangle_count') or 0),
            file_size=upload.size, sort=int(request.data.get('sort') or 0), status=1,
            remark=(request.data.get('remark') or '')[:500],
            create_by=_username(request), create_time=_now(), update_by=_username(request), update_time=_now(),
        )
        return ok(self.serializer_class(resource).data, '上传成功')  # 返回资源

    def preview(self, request, pk=None):
        """返回模型文件地址，供前端加载/下载。"""
        row = self.get_queryset().filter(pk=pk).first()  # 定位资源
        if not row:
            return fail('模型资源不存在', code=404)  # 业务 404
        data = self.serializer_class(row).data  # 序列化
        data['file_url'] = f'/uploads/{data["file_url"]}' if data.get('file_url') else None  # 补全可访问地址
        return ok(data, '查询成功')  # 返回预览信息


class Scene3dScreenView(viewsets.ViewSet):
    """3D 大屏数据接口：已发布场景、资产统计与告警概况。"""

    @property
    def permission_classes(self):
        """只校验登录 + 大屏查看权限。"""
        self.perm_map = {'data': 'scene3d:screen:view'}  # 大屏数据权限
        return [PermissionCheck]  # 登录 + 权限

    def data(self, request):
        """返回大屏所需聚合数据（全部来自真实表）。"""
        scenes = list(Scene3dScene.objects.filter(is_deleted=False, scene_status=1).order_by('-update_time', '-id')[:8])  # 已发布场景
        scene_items = []  # 输出数组
        for scene in scenes:  # 逐场景补充对象数量
            item = Scene3dSceneSerializer(scene).data
            item['object_count'] = Scene3dSceneObject.objects.filter(scene_id=scene.id, is_deleted=False).count()
            scene_items.append(item)
        start = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')  # 近 7 天
        alarms = Scene3dAlarmRecord.objects.filter(is_deleted=False, create_time__gte=start)  # 近 7 天告警
        recent = Scene3dAlarmRecord.objects.filter(is_deleted=False).order_by('-create_time', '-id')[:5]  # 最新 5 条
        return ok({
            'scenes': scene_items,  # 场景卡片
            'metrics': {
                'scene_total': Scene3dScene.objects.filter(is_deleted=False).count(),  # 全部场景
                'published': Scene3dScene.objects.filter(is_deleted=False, scene_status=1).count(),  # 已发布
                'object_total': Scene3dSceneObject.objects.filter(is_deleted=False).count(),  # 对象总数
                'model_total': Scene3dModelResource.objects.filter(is_deleted=False).count(),  # 模型总数
                'alarm_unconfirmed': Scene3dAlarmRecord.objects.filter(is_deleted=False, alarm_status=0).count(),  # 未确认告警
            },
            'alarm_trend': [
                {'name': '提示', 'value': alarms.filter(alarm_level=1).count()},
                {'name': '警告', 'value': alarms.filter(alarm_level=2).count()},
                {'name': '严重', 'value': alarms.filter(alarm_level=3).count()},
            ],
            'recent_alarms': Scene3dAlarmRecordSerializer(recent, many=True).data,  # 最新告警
        }, '查询成功')


class Scene3dShareView(views.APIView):
    """分享页数据接口：免登录，凭 token 读取已发布场景。"""

    permission_classes = [AllowAny]  # 覆盖全局默认认证/登录要求
    authentication_classes = []  # 分享页不解析登录态，避免过期 token 导致 401

    def get(self, request, token):
        """按 token 返回场景详情，并校验有效期。"""
        scene = None  # 命中的场景
        for row in Scene3dScene.objects.filter(is_deleted=False, scene_status=1):  # 已发布场景数量有限，直接遍历
            config = _json(row.scene_config, {})  # 场景配置，兼容历史上被存成字符串的值
            share = _json(config.get('share'), {}) if isinstance(config, dict) else {}  # 分享配置
            share = share if isinstance(share, dict) else {}  # 兜底为对象
            if share.get('token') == token:  # 命中令牌
                scene = row  # 记录场景
                expire = share.get('expire')  # 过期时间
                if expire:  # 有有效期则校验
                    try:
                        if datetime.now() > datetime.strptime(expire, '%Y-%m-%d %H:%M:%S'):  # 已过期
                            return fail('分享链接已过期', code=410)  # 410 已失效
                    except ValueError:
                        pass  # 时间格式异常时按有效处理，避免锁定
                break  # 找到即停止
        if not scene:  # 未匹配
            return fail('分享链接无效或场景已下线', code=404)  # 统一提示
        return ok(_scene_payload(scene, request, '分享链接'), '查询成功')  # 免登录返回详情
