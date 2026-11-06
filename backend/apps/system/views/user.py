"""用户管理。"""
# 模块用途：系统用户的增删改查、详情回填、密码重置、启停切换与角色分配。
# 对应路由前缀：/api/system/user/（标准 CRUD + /<pk> 详情 + reset_pwd/status/assign_roles）。
# 权限要求：基类按 perm_prefix='system:user' 生成权限点，所有动作均受该前缀保护。
# 关键约定：用户-角色关系存中间表 sys_user_role，用原生 SQL 覆盖式写入；密码统一 bcrypt 哈希后入库。
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


# 内部工具：覆盖式保存用户角色，供新增后钩子与角色分配接口复用。
# 覆盖式语义：先清空该用户的全部旧角色，再按提交列表批量插入，避免残留历史授权。
def save_user_roles(user_id, role_ids):
    """覆盖式保存用户角色：先清空旧关联再批量插入。"""
    # 游标上下文负责资源释放；写操作随请求事务一起提交/回滚。
    with connection.cursor() as cursor:  # 原始 SQL 需显式游标
        # 先删除旧关联，保证最终角色集合与前端提交完全一致。
        cursor.execute("DELETE FROM sys_user_role WHERE user_id = %s", [user_id])  # 清除旧角色
        # 空列表表示清空角色，此时跳过 INSERT，避免执行空批量语句。
        if role_ids:  # 有新角色才插入
            # executemany 批量插入，减少与数据库的交互次数。
            cursor.executemany(
                "INSERT INTO sys_user_role (user_id, role_id) VALUES (%s, %s)",
                [(user_id, rid) for rid in role_ids])  # 批量写入关联


class UserViewSet(CrudViewSet):
    """用户管理视图：按动作切换序列化器，并在增改后同步角色。"""
    # 用户模块没有把 serializer_class 固定成单一类，而是在 get_serializer_class 中按 action 动态选择。
    model = SysUser  # 目标模型
    perm_prefix = 'system:user'  # 权限标识前缀
    module_name = '用户管理'  # 操作日志模块名
    # 用户名/昵称/手机号模糊搜索，状态与部门精确匹配；字段名即查询参数名。
    filter_map = {'username': 'icontains', 'nickname': 'icontains',  # 列表筛选字段
                  'phone': 'icontains', 'status': 'exact', 'dept_id': 'exact'}  # 续行筛选

    # 不同动作的字段集合差异较大（列表要部门/角色、编辑不能改密码），因此按 action 分流。
    def get_serializer_class(self):
        """按动作选择序列化器：列表/更新/新增各不相同。"""
        # 列表接口输出带部门名称与角色信息，方便表格直接展示。
        if self.action == 'list':
            return UserListSerializer  # 列表带部门与角色
        # 编辑接口不接收密码字段，密码只能走 reset_pwd 单独重置。
        if self.action == 'update':
            return UserUpdateSerializer  # 编辑不含密码
        # create 及其它动作默认走新增序列化器，内部负责密码哈希等处理。
        return UserCreateSerializer  # 新增含密码处理

    # 基类钩子：用户主体落库后，再同步写入角色关联（角色在中间表，需单独写）。
    def after_create(self, request, instance):
        """新增成功后同步写入角色关联。"""
        # 未选择角色时按空列表处理，允许创建无角色用户。
        role_ids = request.data.get('role_ids') or []  # 前端提交的角色ID
        # instance 是基类 save 后返回的已落库对象，id 已生成，可直接作为用户主键。
        save_user_roles(instance.id, role_ids)  # 保存角色关联

    # 基类钩子：编辑用户后同步角色；只有显式提交 role_ids 才更新，避免误清空。
    def after_update(self, request, instance):
        """编辑后仅在显式提交 role_ids 时更新角色。"""
        # 用 None 区分“未提交该字段”和“提交了空列表（清空角色）”。
        role_ids = request.data.get('role_ids')  # 未提交则为 None
        # 仅当字段存在时才覆盖，普通信息编辑不会影响角色配置。
        if role_ids is not None:  # 区分“未传”与“清空”
            save_user_roles(instance.id, role_ids)  # 覆盖保存

    # 详情接口：列表字段 + 角色 ID 列表，供编辑弹窗回填角色多选框。
    def retrieve(self, request, pk=None):
        """查询单个用户详情：列表字段 + 角色ID，供编辑弹窗回填。"""
        # 从 get_queryset 取，自动排除已逻辑删除用户。
        user = self.get_queryset().filter(pk=pk).first()  # 查未删除用户
        # 主键不存在或已删除时返回 404，避免前端拿到残缺数据。
        if not user:  # 详情查询未命中说明已被删除或主键不存在
            return fail('用户不存在', code=404)  # 用户不存在
        # 复用列表序列化器，保证详情与列表字段一致；dict() 转成可变字典以便追加字段。
        data = dict(UserListSerializer(user).data)  # 复用列表序列化字段
        # 角色关系在中间表，序列化器不直接输出，这里补查一次用于回填。
        with connection.cursor() as cursor:  # 角色关联存于中间表
            # 按用户主键查询其全部角色 ID。
            cursor.execute("SELECT role_id FROM sys_user_role WHERE user_id = %s", [pk])  # 查角色ID
            # 只取第一列，组装成前端多选框可直接使用的数组。
            data['role_ids'] = [row[0] for row in cursor.fetchall()]  # 供前端多选回填
        # 返回完整详情对象。
        return ok(data)  # 返回用户详情

    # 重置密码动作：只改 password 与审计字段，不做全量字段校验。
    @action(detail=True, methods=['put'], url_path='reset_pwd')  # 注册单条动作：PUT /user/reset_pwd/<pk>
    def reset_pwd(self, request, pk=None):
        """重置指定用户密码（仅更新密码与审计字段）。"""
        # 先确认用户存在且未删除，避免向已删除账号写密码。
        user = self.get_queryset().filter(pk=pk).first()  # 查未删除用户
        # 不存在直接返回 404，前端可提示“用户已被删除”。
        if not user:  # 重置密码前先确认用户仍存在
            return fail('用户不存在', code=404)  # 用户不存在
        # 新密码为必填参数，空值不写入，避免把账号密码重置为空。
        password = request.data.get('password')  # 新密码
        # 空字符串与 None 都视为未提供，给出明确提示。
        if not password:
            return fail('请输入新密码')  # 参数校验
        # 统一走 bcrypt 哈希，保证与登录校验使用的算法一致。
        user.password = hash_password(password)  # 哈希后写入
        # 记录操作人，便于审计“谁重置了谁的密码”。
        user.update_by = request.user_info.username  # 记录更新人
        # 与全站时间格式保持一致，便于前端统一展示。
        user.update_time = time.strftime('%Y-%m-%d %H:%M:%S')  # 记录更新时间
        # update_fields 限定三列，避免把请求中的其它字段一并写入。
        user.save(update_fields=['password', 'update_by', 'update_time'])  # 只更新这三列
        # 不回传新密码，避免敏感信息出现在响应中。
        return ok(None, '密码重置成功')  # 返回成功

    # 启停切换动作：只改 status 与审计字段；禁止操作自己，防止把自己锁在系统外。
    @action(detail=True, methods=['put'])  # 注册单条动作：PUT /user/status/<pk>
    def status(self, request, pk=None):
        """启用/停用用户，禁止修改自己的状态。"""
        # 只处理未删除用户，避免对历史账号做状态变更。
        user = self.get_queryset().filter(pk=pk).first()  # 查未删除用户
        # 不存在返回 404，提示前端数据已失效。
        if not user:  # 切换状态前先确认用户仍存在
            return fail('用户不存在', code=404)  # 用户不存在
        # 当前登录用户不能修改自己的状态，否则可能立即失去后台访问能力。
        if int(user.id) == int(request.user_info.id):  # 防止把自己锁在系统外
            return fail('不能修改自己的状态', code=400)  # 拒绝操作
        # 把任意入参归一为 0/1：仅字符串 '1' 视为禁用，其余（含缺省）一律按启用处理。
        user.status = 1 if str(request.data.get('status')) == '1' else 0  # 归一为 0/1
        # 记录操作人，便于审计状态变更来源。
        user.update_by = request.user_info.username  # 记录更新人
        # 统一时间格式，便于列表展示与排序。
        user.update_time = time.strftime('%Y-%m-%d %H:%M:%S')  # 记录更新时间
        # 只更新状态与审计列，避免误改用户其它资料。
        user.save(update_fields=['status', 'update_by', 'update_time'])  # 只更新这三列
        # 不回传用户对象，前端本地更新状态即可。
        return ok(None, '修改成功')  # 返回成功

    # 角色分配动作：覆盖式保存，提交的 role_ids 即为最终角色集合。
    @action(detail=True, methods=['put'], url_path='assign_roles')  # 注册单条动作：PUT /user/assign_roles/<pk>
    def assign_roles(self, request, pk=None):
        """为指定用户重新分配角色（覆盖式）。"""
        # 先校验用户存在且未删除，避免给已删除账号挂角色。
        if not self.get_queryset().filter(pk=pk).exists():  # 先校验用户存在
            return fail('用户不存在', code=404)  # 用户不存在
        # 未传 role_ids 视为清空角色，与“提交空列表”语义一致。
        save_user_roles(pk, request.data.get('role_ids') or [])  # 覆盖保存角色
        # 不回传授权结果，前端保存成功后可重新拉取角色列表。
        return ok(None, '分配角色成功')  # 返回成功
