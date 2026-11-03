"""用户管理。"""
import time

from django.db import connection
from rest_framework.decorators import action

from apps.system.models import SysUser
from apps.system.serializers import (UserCreateSerializer, UserListSerializer,
                                     UserUpdateSerializer)
from common.auth import LoginRequired
from common.response import fail, ok
from common.utils import hash_password
from common.views import CrudViewSet


def save_user_roles(user_id, role_ids):
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM sys_user_role WHERE user_id = %s", [user_id])
        if role_ids:
            cursor.executemany(
                "INSERT INTO sys_user_role (user_id, role_id) VALUES (%s, %s)",
                [(user_id, rid) for rid in role_ids])


class UserViewSet(CrudViewSet):
    model = SysUser
    perm_prefix = 'system:user'
    module_name = '用户管理'
    filter_map = {'username': 'icontains', 'nickname': 'icontains',
                  'phone': 'icontains', 'status': 'exact', 'dept_id': 'exact'}

    def get_serializer_class(self):
        if self.action == 'list':
            return UserListSerializer
        if self.action == 'update':
            return UserUpdateSerializer
        return UserCreateSerializer

    def after_create(self, request, instance):
        role_ids = request.data.get('role_ids') or []
        save_user_roles(instance.id, role_ids)

    def after_update(self, request, instance):
        role_ids = request.data.get('role_ids')
        if role_ids is not None:
            save_user_roles(instance.id, role_ids)

    @action(detail=True, methods=['put'], url_path='reset_pwd')
    def reset_pwd(self, request, pk=None):
        user = self.get_queryset().filter(pk=pk).first()
        if not user:
            return fail('用户不存在', code=404)
        password = request.data.get('password')
        if not password:
            return fail('请输入新密码')
        user.password = hash_password(password)
        user.update_by = request.user_info.username
        user.update_time = time.strftime('%Y-%m-%d %H:%M:%S')
        user.save(update_fields=['password', 'update_by', 'update_time'])
        return ok(None, '密码重置成功')

    @action(detail=True, methods=['put'])
    def status(self, request, pk=None):
        user = self.get_queryset().filter(pk=pk).first()
        if not user:
            return fail('用户不存在', code=404)
        if int(user.id) == int(request.user_info.id):
            return fail('不能修改自己的状态', code=400)
        user.status = 1 if str(request.data.get('status')) == '1' else 0
        user.update_by = request.user_info.username
        user.update_time = time.strftime('%Y-%m-%d %H:%M:%S')
        user.save(update_fields=['status', 'update_by', 'update_time'])
        return ok(None, '修改成功')

    @action(detail=True, methods=['put'], url_path='assign_roles')
    def assign_roles(self, request, pk=None):
        if not self.get_queryset().filter(pk=pk).exists():
            return fail('用户不存在', code=404)
        save_user_roles(pk, request.data.get('role_ids') or [])
        return ok(None, '分配角色成功')
