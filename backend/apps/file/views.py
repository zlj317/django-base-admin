"""文件模块视图集。"""
import hashlib  # MD5 去重用
import os  # 目录创建/文件删除
import time  # 时间戳与月份目录生成
from urllib.parse import quote  # kkFileView URL 编码

from rest_framework.decorators import action  # 自定义路由装饰器
from rest_framework.parsers import FormParser, MultiPartParser  # 解析 multipart 上传
from rest_framework.response import Response  # DRF 响应类

from common.response import fail, ok  # 统一响应封装
from common.views import CrudViewSet  # 通用 CRUD 基类
from django.conf import settings  # 读取 MEDIA_ROOT

from apps.file.models import WfFile, WfFileConfig, WfFileRecycle  # 文件相关模型
from apps.file.serializers import FileSerializer, FileConfigSerializer, FileRecycleSerializer  # 对应序列化器


class FileViewSet(CrudViewSet):
    """文件表 CRUD：管理上传文件元信息。"""
    model = WfFile  # 目标模型
    serializer_class = FileSerializer  # 序列化器
    perm_prefix = 'file'  # 权限前缀：file:list/create/update/delete
    filter_map = {  # 支持的查询参数与 ORM lookup 映射
        'file_name': 'icontains',  # 文件名模糊搜索
        'original_name': 'icontains',  # 原始文件名模糊搜索
        'biz_type': 'exact',  # 业务类型精确匹配
        'storage_type': 'exact',  # 存储类型精确匹配
    }
    order_by = '-id'  # 按主键倒序，最新上传在前
    module_name = '文件管理'  # 操作日志模块名

    @action(detail=False, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def upload(self, request):
        """多文件上传：保存到 MEDIA_ROOT/uploads/YYYYMM/，按 MD5 去重。"""
        f = request.FILES.get('file')
        if not f:
            return fail('请选择上传文件')
        # 计算 MD5（分块读防止大文件撑爆内存）
        md5 = hashlib.md5()
        for chunk in f.chunks(8192):
            md5.update(chunk)
        file_md5 = md5.hexdigest()
        # 秒传：已存在相同 MD5 则直接返回
        dup = WfFile.objects.filter(file_md5=file_md5, is_deleted=0).first()
        if dup:
            return ok({
                'id': dup.id, 'file_name': dup.file_name,
                'original_name': dup.original_name, 'file_size': dup.file_size,
                'url': f"/uploads/{dup.storage_path.replace(os.sep, '/')}" if dup.storage_path else '',
            }, '文件秒传')
        # 目录与随机文件名
        month_dir = time.strftime('%Y%m')
        upload_dir = os.path.join(settings.MEDIA_ROOT or 'media', 'uploads', month_dir)
        os.makedirs(upload_dir, exist_ok=True)
        ext = os.path.splitext(f.name)[1].lstrip('.')
        random_name = f"{int(time.time()*1000)}_{os.getpid()}_{hash(f.name) & 0xffffff:06x}"
        if ext:
            random_name += f'.{ext}'
        dest = os.path.join(upload_dir, random_name)
        storage_rel = os.path.join('uploads', month_dir, random_name)
        with open(dest, 'wb+') as out:
            for chunk in f.chunks(8192):
                out.write(chunk)
        user = getattr(request, 'user_info', None)
        now = time.strftime('%Y-%m-%d %H:%M:%S')
        row = WfFile.objects.create(
            file_name=random_name, original_name=f.name,
            file_ext=ext or '', mime_type=getattr(f, 'content_type', '') or '',
            file_size=f.size or 0, file_md5=file_md5,
            storage_type='local', storage_path=storage_rel,
            upload_user_id=getattr(user, 'id', None),
            create_by=user.username if user else '', create_time=now,
            update_by=user.username if user else '', update_time=now, is_deleted=0,
        )
        return ok({
            'id': row.id, 'file_name': row.file_name,
            'original_name': row.original_name, 'file_size': row.file_size,
            'url': f"/uploads/{storage_rel.replace(os.sep, '/')}",
        }, '上传成功')

    def delete(self, request):
        """删除文件：先写回收站再逻辑删除，保证可从回收站恢复。"""
        ids = request.data.get('ids') or []
        if not ids:
            return ok(None, '请选择要删除的数据')
        user = getattr(request, 'user_info', None)
        now = time.strftime('%Y-%m-%d %H:%M:%S')
        for f in WfFile.objects.filter(id__in=ids, is_deleted=0):
            WfFileRecycle.objects.create(
                file_id=f.id, file_name=f.original_name or f.file_name,
                delete_user_id=getattr(user, 'id', None),
                delete_time=now, create_time=now)
        return super().delete(request)

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """下载文件：以原始文件名流式返回本地存储的文件。"""
        from django.http import FileResponse
        row = WfFile.objects.filter(pk=pk, is_deleted=0).first()
        if not row:
            return fail('文件不存在', code=404)
        if not row.storage_path:
            return fail('文件未存储，无法下载')
        local_path = os.path.join(settings.MEDIA_ROOT or 'media', row.storage_path.replace('/', os.sep))
        if not os.path.isfile(local_path):
            return fail('物理文件不存在', code=404)
        return FileResponse(open(local_path, 'rb'), as_attachment=True,
                            filename=row.original_name or row.file_name)

    @action(detail=True, methods=['get'])
    def preview_url(self, request, pk=None):
        """返回 kkFileView 预览地址。"""
        row = WfFile.objects.filter(pk=pk, is_deleted=0).first()
        if not row:
            return fail('文件不存在', code=404)
        kk_url = 'http://localhost:8012/onlinePreview'
        storage_path = f"/uploads/{row.storage_path}" if row.storage_path else row.file_name
        return ok({'url': f"{kk_url}?url={quote(storage_path)}"})

    @action(detail=True, methods=['get'])
    def office_url(self, request, pk=None):
        """返回 onlyoffice 预览地址（占位）。"""
        row = WfFile.objects.filter(pk=pk, is_deleted=0).first()
        if not row:
            return fail('文件不存在', code=404)
        return ok({'url': f'/onlyoffice/editor?fileId={row.id}&fileName={quote(row.original_name or row.file_name)}'})

    @action(detail=True, methods=['put'])
    def save_config(self, request, pk=None):
        """保存文件配置项（按 pk 更新 WfFileConfig）。"""
        row = WfFileConfig.objects.filter(pk=pk, is_deleted=0).first()
        if not row:
            return fail('配置不存在', code=404)
        data = request.data or {}
        if 'config_value' in data:
            row.config_value = data['config_value']
        if 'config_name' in data:
            row.config_name = data['config_name']
        if 'remark' in data:
            row.remark = data['remark']
        row.save()
        return ok(WfFileConfigSerializer(row).data, '保存成功')


class FileConfigViewSet(CrudViewSet):
    """文件配置表 CRUD：管理文件相关参数。"""
    model = WfFileConfig  # 目标模型
    serializer_class = FileConfigSerializer  # 序列化器
    perm_prefix = 'file'  # 权限前缀
    filter_map = {  # 支持的查询参数
        'config_key': 'icontains',  # 配置键模糊搜索
        'config_type': 'exact',  # 配置类型精确匹配
    }
    order_by = '-id'  # 按主键倒序
    module_name = '文件配置'  # 操作日志模块名


class FileRecycleViewSet(CrudViewSet):
    """文件回收站表 CRUD：已删除文件记录。"""
    model = WfFileRecycle  # 目标模型
    serializer_class = FileRecycleSerializer  # 序列化器
    perm_prefix = 'file'  # 权限前缀
    filter_map = {  # 支持的查询参数
        'file_name': 'icontains',  # 文件名模糊搜索
    }
    order_by = '-id'  # 按主键倒序
    module_name = '文件回收站'  # 操作日志模块名

    def get_queryset(self):
        # 回收站记录不做逻辑删除过滤，直接按主键倒序返回全部快照
        return self.model.objects.order_by(self.order_by)

    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        """恢复回收站文件：把 wf_file.is_deleted 置回 0，删除回收站记录。"""
        recycle = WfFileRecycle.objects.filter(pk=pk).first()
        if not recycle:
            return fail('回收站记录不存在', code=404)
        user = getattr(request, 'user_info', None)
        now = time.strftime('%Y-%m-%d %H:%M:%S')
        affected = WfFile.objects.filter(pk=recycle.file_id).update(
            is_deleted=0, update_by=user.username if user else '', update_time=now)
        if not affected:
            return fail('原文件已不存在，无法恢复')
        recycle.delete()
        return ok(None, '恢复成功')

    @action(detail=True, methods=['delete'])
    def hard_delete(self, request, pk=None):
        """彻底删除：删回收站记录 + 删物理文件。"""
        recycle = WfFileRecycle.objects.filter(pk=pk).first()
        if not recycle:
            return fail('回收站记录不存在', code=404)
        # 尝试删物理文件
        wf = WfFile.objects.filter(pk=recycle.file_id).first()
        if wf and wf.storage_path:
            try:
                local_path = os.path.join(settings.MEDIA_ROOT or 'media', wf.storage_path.replace('/', os.sep))
                if os.path.isfile(local_path):
                    os.remove(local_path)
            except Exception:
                pass  # 物理文件不存在或权限不足时跳过
        recycle.delete()
        if wf:
            WfFile.objects.filter(pk=recycle.file_id).delete()
        return ok(None, '已彻底删除')
