"""用户管理。"""
import time  # 生成更新时间字符串

from django.db import connection  # 用户-角色关联表使用原始 SQL
from rest_framework.decorators import action  # 声明自定义动作路由

from apps.system.models import SysUser  # 用户模型
from apps.system.serializers import (UserCreateSerializer, UserListSerializer,  # 新增/列表序列化器
                                     UserUpdateSerializer)  # 编辑序列化器
from common.auth import LoginRequired  # 登录校验（此处仅导入备用）
from common.response import fail, ok  # 统一响应封装
from common.utils import hash_password  # bcrypt 密码哈希
from common.views import CrudViewSet  # 通用 CRUD 基类


def save_user_roles(user_id, role_ids):
    """覆盖式保存用户角色：先清空旧关联再批量插入。"""
    with connection.cursor() as cursor:  # 原始 SQL 需显式游标
        cursor.execute("DELETE FROM sys_user_role WHERE user_id = %s", [user_id])  # 清除旧角色
        if role_ids:  # 有新角色才插入
            cursor.executemany(
                "INSERT INTO sys_user_role (user_id, role_id) VALUES (%s, %s)",
                [(user_id, rid) for rid in role_ids])  # 批量写入关联


class UserViewSet(CrudViewSet):
    """用户管理视图：按动作切换序列化器，并在增改后同步角色。"""
    model = SysUser  # 目标模型
    perm_prefix = 'system:user'  # 权限标识前缀
    module_name = '用户管理'  # 操作日志模块名
    filter_map = {'username': 'icontains', 'nickname': 'icontains',  # 列表筛选字段
                  'phone': 'icontains', 'status': 'exact', 'dept_id': 'exact'}  # 续行筛选

    def get_serializer_class(self):
        """按动作选择序列化器：列表/更新/新增各不相同。"""
        if self.action == 'list':
            return UserListSerializer  # 列表带部门与角色
        if self.action == 'update':
            return UserUpdateSerializer  # 编辑不含密码
        return UserCreateSerializer  # 新增含密码处理

    def after_create(self, request, instance):
        """新增成功后同步写入角色关联。"""
        role_ids = request.data.get('role_ids') or []  # 前端提交的角色ID
        save_user_roles(instance.id, role_ids)  # 保存角色关联

    def after_update(self, request, instance):
        """编辑后仅在显式提交 role_ids 时更新角色。"""
        role_ids = request.data.get('role_ids')  # 未提交则为 None
        if role_ids is not None:  # 区分“未传”与“清空”
            save_user_roles(instance.id, role_ids)  # 覆盖保存

    @action(detail=True, methods=['put'], url_path='reset_pwd')
    def reset_pwd(self, request, pk=None):
        """重置指定用户密码（仅更新密码与审计字段）。"""
        user = self.get_queryset().filter(pk=pk).first()  # 查未删除用户
        if not user:
            return fail('用户不存在', code=404)  # 用户不存在
        password = request.data.get('password')  # 新密码
        if not password:
            return fail('请输入新密码')  # 参数校验
        user.password = hash_password(password)  # 哈希后写入
        user.update_by = request.user_info.username  # 记录更新人
        user.update_time = time.strftime('%Y-%m-%d %H:%M:%S')  # 记录更新时间
        user.save(update_fields=['password', 'update_by', 'update_time'])  # 只更新这三列
        return ok(None, '密码重置成功')  # 返回成功

    @action(detail=True, methods=['put'])
    def status(self, request, pk=None):
        """启用/停用用户，禁止修改自己的状态。"""
        user = self.get_queryset().filter(pk=pk).first()  # 查未删除用户
        if not user:
            return fail('用户不存在', code=404)  # 用户不存在
        if int(user.id) == int(request.user_info.id):  # 防止把自己锁在系统外
            return fail('不能修改自己的状态', code=400)  # 拒绝操作
        user.status = 1 if str(request.data.get('status')) == '1' else 0  # 归一为 0/1
        user.update_by = request.user_info.username  # 记录更新人
        user.update_time = time.strftime('%Y-%m-%d %H:%M:%S')  # 记录更新时间
        user.save(update_fields=['status', 'update_by', 'update_time'])  # 只更新这三列
        return ok(None, '修改成功')  # 返回成功

    @action(detail=True, methods=['put'], url_path='assign_roles')
    def assign_roles(self, request, pk=None):
        """为指定用户重新分配角色（覆盖式）。"""
        if not self.get_queryset().filter(pk=pk).exists():  # 先校验用户存在
            return fail('用户不存在', code=404)  # 用户不存在
        save_user_roles(pk, request.data.get('role_ids') or [])  # 覆盖保存角色
        return ok(None, '分配角色成功')  # 返回成功
