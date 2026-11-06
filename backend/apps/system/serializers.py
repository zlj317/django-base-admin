# 模块：apps/system/serializers.py —— 系统模块的 DRF 序列化器集合
# 用途：定义各模型的入参校验、出参字段与展示字段（部门名、角色列表、0/1 状态等）。
# 数据表：sys_user、sys_role、sys_menu、sys_dept、sys_dict_type、sys_dict_data、
#         sys_config、sys_oper_log、sys_login_log。
# 调用方：apps/system/views 下的 UserViewSet、RoleViewSet、MenuViewSet、DeptViewSet、
#         DictTypeViewSet、DictDataViewSet、ConfigViewSet、OperLogViewSet、LoginLogViewSet。
"""系统模块序列化器。"""
from rest_framework import serializers  # DRF 序列化/反序列化组件

from apps.system.models import (SysConfig, SysDept, SysDictData, SysDictType,  # 各业务模型
                                SysLoginLog, SysMenu, SysOperLog, SysRole,  # 续行：日志与角色等
                                SysUser)  # 用户模型
from common.utils import hash_password  # bcrypt 密码哈希


# 唯一性校验器：可复用于任意模型字段，核心是「只统计未逻辑删除记录，更新时排除自身」
class UniqueExcludingDeleted:
    """唯一性校验器：排除已逻辑删除记录后再判断字段值是否重复。"""

    def __init__(self, model, field_name, message='该值已存在'):
        """保存待校验的模型、字段名与自定义报错文案。"""
        self.model = model  # 目标模型类
        self.field_name = field_name  # 需要唯一的字段名
        self.message = message  # 校验失败提示

    def __call__(self, value):
        """执行校验：同名字段值存在即抛错，否则原样返回。"""
        serializer = serializers.CharField()  # 借用字符字段做类型/空值规范化
        value = serializer.to_internal_value(value)  # 转成内部字符串值
        qs = self.model.objects.filter(**{self.field_name: value}, is_deleted=0)  # 未删除记录
        if self.model.pk_value:  # 仅更新场景会预先暂存主键，用于排除自身
            qs = qs.exclude(pk=self.model.pk_value)  # 更新时排除自身
        if qs.exists():
            raise serializers.ValidationError(self.message)  # 已存在则校验失败
        return value  # 校验通过返回原值


# 辅助函数：把当前编辑对象的主键挂到模型类属性上，供 UniqueExcludingDeleted 读取并排除自身
def set_pk_value(model, pk):
    """把当前编辑记录的主键暂存到模型类上，供唯一性校验排除自身。"""
    model.pk_value = pk  # 以类属性传递当前对象主键


# 新增用户：password 只写不读，并对用户名做未删除范围的唯一性校验（对应 POST /api/system/user/create）
class UserCreateSerializer(serializers.ModelSerializer):
    """新增用户序列化器：密码只写不读，并做账号唯一性校验。"""
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)  # 只写字段

    class Meta:
        """声明模型与参与序列化的字段。"""
        model = SysUser  # 目标模型
        fields = ['id', 'username', 'password', 'nickname', 'phone', 'email',  # 字段清单
                  'avatar', 'dept_id', 'status']  # 续行：其余可写字段

    def validate_username(self, value):
        """校验用户名在未删除记录中唯一。"""
        if SysUser.objects.filter(username=value, is_deleted=0).exists():  # 已存在同名账号
            raise serializers.ValidationError('用户名已存在')  # 抛出字段校验错误
        return value  # 校验通过

    def validate_password(self, value):
        """密码统一走 bcrypt 哈希；为空时给默认密码。"""
        return hash_password(value) if value else hash_password('123456')  # 默认密码兜底

    def validate_status(self, value):
        """状态统一转为 0/1 整数，兼容前端布尔传值。"""
        return int(bool(value))  # 布尔转 0/1


# 编辑用户：不接收密码（改密走独立接口），用户名唯一校验时排除当前编辑对象（对应 PUT /api/system/user/update/<pk>）
class UserUpdateSerializer(serializers.ModelSerializer):
    """编辑用户序列化器：不含密码（改密走单独接口）。"""
    class Meta:
        """声明模型与参与序列化的字段。"""
        model = SysUser  # 目标模型
        fields = ['id', 'username', 'nickname', 'phone', 'email', 'avatar',  # 字段清单
                  'dept_id', 'status']  # 续行：其余可写字段

    def validate_username(self, value):
        """校验用户名唯一，更新时排除自身。"""
        qs = SysUser.objects.filter(username=value, is_deleted=0)  # 未删除的同名记录
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)  # 排除当前编辑对象
        if qs.exists():
            raise serializers.ValidationError('用户名已存在')  # 校验失败
        return value  # 校验通过

    def validate_status(self, value):
        """状态统一转为 0/1 整数。"""
        return int(bool(value))  # 布尔转 0/1


# 用户列表：在模型字段外补充部门名称、已分配角色与前端约定的 0/1 状态（对应 GET /api/system/user/list）
class UserListSerializer(serializers.ModelSerializer):
    """用户列表序列化器：补充部门名、角色与前端使用的 0/1 状态。"""
    dept_name = serializers.SerializerMethodField()  # 只读：部门名称
    roles = serializers.SerializerMethodField()  # 只读：已分配角色
    # 模型中 status 为 BooleanField（False=正常，True=停用），前端统一使用 0/1
    status = serializers.SerializerMethodField()  # 只读：转换后的状态值

    class Meta:
        """声明模型与列表展示字段。"""
        model = SysUser  # 目标模型
        fields = ['id', 'username', 'nickname', 'phone', 'email', 'avatar',  # 字段清单
                  'dept_id', 'dept_name', 'status', 'roles', 'create_time']  # 续行字段

    def get_status(self, obj):
        """把布尔状态转成前端约定的 0/1。"""
        return 1 if obj.status else 0  # True 视为 1

    def get_dept_name(self, obj):
        """按 dept_id 查询部门名称，未归属部门时返回空。"""
        if obj.dept_id:  # 仅当用户归属部门时才查询，避免空主键查询
            return SysDept.objects.filter(id=obj.dept_id).values_list('dept_name', flat=True).first()
        return None  # 无部门则返回空

    def get_roles(self, obj):
        """联表查询用户已分配的角色（过滤已删除角色）。"""
        from django.db import connection  # 延迟导入，避免模块加载期依赖
        with connection.cursor() as cursor:  # 原始 SQL 需要显式游标
            cursor.execute(  # 一条 SQL 联表取角色，过滤已删除角色
                "SELECT r.id, r.role_name FROM sys_user_role ur "
                "JOIN sys_role r ON r.id = ur.role_id AND r.is_deleted = 0 "
                "WHERE ur.user_id = %s", [obj.id])
            return [{'id': r[0], 'role_name': r[1]} for r in cursor.fetchall()]  # 整理为字典列表


# 角色：输出角色基础字段，role_key 做未删除范围的唯一性校验（对应 /api/system/role/*）
class RoleSerializer(serializers.ModelSerializer):
    """角色序列化器：角色编码唯一，状态统一为 0/1。"""
    class Meta:
        """声明模型与参与序列化的字段。"""
        model = SysRole  # 目标模型
        fields = ['id', 'role_name', 'role_key', 'role_sort', 'status',  # 字段清单
                  'data_scope', 'remark', 'create_time']  # 续行字段

    def validate_role_key(self, value):
        """校验角色编码唯一，更新时排除自身。"""
        qs = SysRole.objects.filter(role_key=value, is_deleted=0)  # 未删除的相同编码
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)  # 排除当前编辑对象
        if qs.exists():
            raise serializers.ValidationError('角色编码已存在')  # 校验失败
        return value  # 校验通过

    def validate_status(self, value):
        """状态统一转为 0/1 整数。"""
        return int(bool(value))  # 布尔转 0/1


# 菜单：输出菜单树节点字段，并阻止把菜单自身设为上级造成循环引用（对应 /api/system/menu/*）
class MenuSerializer(serializers.ModelSerializer):
    """菜单序列化器：防止把菜单自身设为上级造成环。"""
    class Meta:
        """声明模型与参与序列化的字段。"""
        model = SysMenu  # 目标模型
        fields = ['id', 'parent_id', 'menu_name', 'path', 'component', 'perms',  # 字段清单
                  'menu_type', 'icon', 'order_num', 'visible', 'status']  # 续行字段

    def validate(self, attrs):
        """对象级校验：上级菜单不能是当前菜单自己。"""
        instance = getattr(self, 'instance', None)  # 更新场景下的当前对象
        pk = instance.pk if instance else None  # 当前对象主键
        if attrs.get('parent_id') and attrs.get('parent_id') == pk:  # 上级等于自身
            raise serializers.ValidationError('上级菜单不能选择自己')  # 校验失败
        return attrs  # 校验通过


# 部门：输出部门树节点字段，并阻止把部门自身设为上级造成循环引用（对应 /api/system/dept/*）
class DeptSerializer(serializers.ModelSerializer):
    """部门序列化器：防止把部门自身设为上级造成环。"""
    class Meta:
        """声明模型与参与序列化的字段。"""
        model = SysDept  # 目标模型
        fields = ['id', 'parent_id', 'dept_name', 'order_num', 'leader', 'phone', 'status']  # 字段

    def validate(self, attrs):
        """对象级校验：上级部门不能是当前部门自己。"""
        instance = getattr(self, 'instance', None)  # 更新场景下的当前对象
        pk = instance.pk if instance else None  # 当前对象主键
        if attrs.get('parent_id') and attrs.get('parent_id') == pk:  # 上级等于自身
            raise serializers.ValidationError('上级部门不能选择自己')  # 校验失败
        return attrs  # 校验通过


# 字典类型：dict_type 编码唯一校验，状态归一为 0/1（对应 /api/system/dict/type/*）
class DictTypeSerializer(serializers.ModelSerializer):
    """字典类型序列化器：类型编码唯一，状态统一为 0/1。"""
    class Meta:
        """声明模型与参与序列化的字段。"""
        model = SysDictType  # 目标模型
        fields = ['id', 'dict_name', 'dict_type', 'status', 'remark', 'create_time']  # 字段清单

    def validate_dict_type(self, value):
        """校验字典类型编码唯一，更新时排除自身。"""
        qs = SysDictType.objects.filter(dict_type=value, is_deleted=0)  # 未删除的相同编码
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)  # 排除当前编辑对象
        if qs.exists():
            raise serializers.ValidationError('字典类型编码已存在')  # 校验失败
        return value  # 校验通过

    def validate_status(self, value):
        """状态统一转为 0/1 整数。"""
        return int(bool(value))  # 布尔转 0/1


# 字典项：输出标签/键值/排序等字段，仅做状态归一（对应 /api/system/dict/data/*）
class DictDataSerializer(serializers.ModelSerializer):
    """字典项序列化器：仅做状态归一化。"""
    class Meta:
        """声明模型与参与序列化的字段。"""
        model = SysDictData  # 目标模型
        fields = ['id', 'dict_type_id', 'dict_label', 'dict_value', 'dict_sort',  # 字段清单
                  'status', 'remark', 'create_time']  # 续行字段

    def validate_status(self, value):
        """状态统一转为 0/1 整数。"""
        return int(bool(value))  # 布尔转 0/1


# 参数配置：config_key 全局唯一校验，避免同键覆盖（对应 /api/system/config/*）
class ConfigSerializer(serializers.ModelSerializer):
    """参数配置序列化器：配置键全局唯一。"""
    class Meta:
        """声明模型与参与序列化的字段。"""
        model = SysConfig  # 目标模型
        fields = ['id', 'config_key', 'config_value', 'config_name', 'remark', 'create_time']  # 字段

    def validate_config_key(self, value):
        """校验配置键唯一，更新时排除自身。"""
        qs = SysConfig.objects.filter(config_key=value, is_deleted=0)  # 未删除的相同键
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)  # 排除当前编辑对象
        if qs.exists():
            raise serializers.ValidationError('配置键已存在')  # 校验失败
        return value  # 校验通过


# 操作日志：只读输出全部字段，供日志列表与详情展示（对应 GET /api/system/operlog/list）
class OperLogSerializer(serializers.ModelSerializer):
    """操作日志序列化器：直接暴露全部字段。"""
    class Meta:
        """声明模型与全部字段。"""
        model = SysOperLog  # 目标模型
        fields = '__all__'  # 全字段输出


# 登录日志：只读输出全部字段，供登录审计列表展示（对应 GET /api/system/loginlog/list）
class LoginLogSerializer(serializers.ModelSerializer):
    """登录日志序列化器：直接暴露全部字段。"""
    class Meta:
        """声明模型与全部字段。"""
        model = SysLoginLog  # 目标模型
        fields = '__all__'  # 全字段输出
